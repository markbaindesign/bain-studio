#!/usr/bin/env python3
"""
Careers page watcher.

Tracks a list of target companies' careers pages and creates an Asana task in
the Prospecting project, assigned to Mark, when a new job posting appears. State
is a per-company snapshot of previously-seen posting links; a task is created
only for a genuinely new posting, not on every page edit.

Registry: ~/.config/bain-studio/careers_watch_companies.json (outside the repo,
  which is public: the list of companies Mark is watching is his business)
  [{"name": "Acme Inc", "slug": "acme", "url": "https://acme.com/careers"}, ...]
  Override with CAREERS_WATCH_REGISTRY.

  An entry can also be a saved search on Workable's cross-company job board,
  with a regex every matching title must contain:
  {"name": "Workable WordPress search", "slug": "workable-wordpress",
   "url": "https://jobs.workable.com/search?query=Wordpress+Developer&workplace=remote&day_range=7",
   "title_match": "wordpress"}
  The board lists one job once per country; a search entry counts a company and
  title once, so those copies become one task.

State: studio/collectors/careers_watch_state/{slug}.json (gitignored)
  Override with CAREERS_WATCH_STATE_DIR (tests, dry runs).

Asana destination, from studio/.env:
  CAREERS_WATCH_PROJECT_GID     the Prospecting project
  CAREERS_WATCH_SECTION_GID     the section new tasks land in (NEXT UP)
  CAREERS_WATCH_CATEGORY_FIELD  Prospect Category custom field
  CAREERS_WATCH_CATEGORY_OPTION its "Real Jobs" option
  CAREERS_WATCH_URL_FIELD       Job URL custom field
Tasks are written through sync.py's create_task (bainbot token).

Usage:
  python3 careers_watch.py                       # check all companies, create tasks for new postings
  python3 careers_watch.py --dry-run             # report what would be created, change nothing
  python3 careers_watch.py --add "Name" "URL"     # add a company to the registry
  python3 careers_watch.py --add "Name" "URL" --title-match REGEX   # add a saved search
  python3 careers_watch.py --list                 # print the registry
  python3 careers_watch.py --remove SLUG          # remove a company

Run on cron, e.g. twice daily:
  0 9,17 * * * cd /media/data/dev/bain-studio && python3 studio/collectors/careers_watch.py >> studio/collectors/careers_watch.log 2>&1

Source resolution: Greenhouse, Lever, and Workable URLs are detected automatically
and read via their public JSON job-board APIs (no auth needed) rather than scraped
as HTML — this is more reliable and works even when the company's own careers page
is a JS-rendered SPA (the API is unaffected by that). Any other URL falls back to a
plain HTTP fetch + heuristic HTML link extraction, which WILL fail silently
(zero postings found) on client-rendered pages with no server-rendered content.
"""

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urljoin

import requests
from bs4 import BeautifulSoup

STUDIO_DIR = Path(__file__).resolve().parent.parent
COLLECTORS_DIR = Path(__file__).resolve().parent
REGISTRY_FILE = Path(os.getenv(
    "CAREERS_WATCH_REGISTRY",
    Path.home() / ".config" / "bain-studio" / "careers_watch_companies.json",
))
STATE_DIR = Path(os.getenv("CAREERS_WATCH_STATE_DIR", COLLECTORS_DIR / "careers_watch_state"))
LOG_PREFIX = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] careers_watch"

# Known ATS URL patterns -> (kind, slug-extraction regex)
ATS_PATTERNS = [
    ("workable-search", re.compile(r"jobs\.workable\.com/search\?(.*)")),
    ("greenhouse", re.compile(r"(?:boards|job-boards)\.greenhouse\.io/([^/?#]+)")),
    ("lever", re.compile(r"jobs\.lever\.co/([^/?#]+)")),
    ("workable", re.compile(r"apply\.workable\.com/([^/?#]+)")),
    ("workable", re.compile(r"([^./]+)\.workable\.com")),
]

# Words that suggest a link is a job posting rather than nav/footer chrome
JOB_LINK_HINTS = re.compile(
    r"(job|career|position|opening|role|vacan|apply)", re.IGNORECASE
)
NAV_NOISE = re.compile(
    r"(privacy|terms|cookie|login|sign.?in|contact|about|home)$", re.IGNORECASE
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def load_registry():
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text())
    return []


def save_registry(companies):
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(json.dumps(companies, indent=2) + "\n")


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def load_state(slug):
    f = STATE_DIR / f"{slug}.json"
    if f.exists():
        return json.loads(f.read_text())
    return {"seen_links": [], "last_checked": None}


def save_state(slug, state):
    STATE_DIR.mkdir(exist_ok=True)
    f = STATE_DIR / f"{slug}.json"
    f.write_text(json.dumps(state, indent=2))


def extract_postings(html, base_url):
    """Best-effort extraction of job-posting-like links from a careers page."""
    soup = BeautifulSoup(html, "html.parser")
    postings = {}
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        if not text or len(text) < 3:
            continue
        if NAV_NOISE.search(text):
            continue
        full_url = urljoin(base_url, href)
        # Heuristic: either the link text or the URL path looks job-related
        if JOB_LINK_HINTS.search(text) or JOB_LINK_HINTS.search(href):
            postings[full_url] = text
    return postings


def detect_ats(url):
    """Return (kind, slug) if the URL matches a known ATS pattern, else None."""
    for kind, pattern in ATS_PATTERNS:
        m = pattern.search(url)
        if m:
            return kind, m.group(1)
    return None


def _posting(title, url, company=None):
    return {"title": title, "url": url, "company": company}


def fetch_greenhouse(slug):
    r = requests.get(
        f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
        headers=HEADERS, timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    if "jobs" not in data:
        raise ValueError(f"unexpected Greenhouse response: {data}")
    return {j["absolute_url"]: _posting(j["title"], j["absolute_url"]) for j in data["jobs"]}


def fetch_lever(slug):
    r = requests.get(
        f"https://api.lever.co/v0/postings/{slug}?mode=json",
        headers=HEADERS, timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise ValueError(f"unexpected Lever response: {data}")
    return {j["hostedUrl"]: _posting(j["text"], j["hostedUrl"]) for j in data}


def fetch_workable(slug):
    r = requests.get(
        f"https://www.workable.com/api/accounts/{slug}?details=true",
        headers=HEADERS, timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    if "jobs" not in data:
        raise ValueError(f"unexpected Workable response: {data}")
    return {j["shortlink"]: _posting(j["title"], j["shortlink"]) for j in data["jobs"]}


def fetch_workable_search(query_string, title_match=None, max_pages=10):
    """Read a saved search on jobs.workable.com through the API behind it.

    Keyed by company and title, not URL: the board lists one job once per
    country, and those copies should make one task, not six.
    """
    params = dict(parse_qsl(query_string))
    pattern = re.compile(title_match, re.IGNORECASE) if title_match else None
    postings = {}
    token = None
    for _ in range(max_pages):
        page = dict(params, **({"pageToken": token} if token else {}))
        r = requests.get("https://jobs.workable.com/api/v1/jobs",
                         params=page, headers=HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
        if "jobs" not in data:
            raise ValueError(f"unexpected Workable search response: {str(data)[:200]}")
        for j in data["jobs"]:
            title = j.get("title") or ""
            if pattern and not pattern.search(title):
                continue
            company = (j.get("company") or {}).get("title") or "unknown company"
            key = f"{company.strip().lower()}|{title.strip().lower()}"
            postings.setdefault(key, _posting(title, j.get("url"), company))
        token = data.get("nextPageToken")
        if not token or not data["jobs"]:
            break
    return postings


ATS_FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "workable": fetch_workable,
}


def fetch_postings(url, title_match=None):
    """Fetch current postings, via ATS API if detected, else HTML scrape.

    Returns ({key: {"title", "url", "company"}}, source).
    """
    ats = detect_ats(url)
    if ats:
        kind, slug = ats
        if kind == "workable-search":
            return fetch_workable_search(slug, title_match), kind
        postings = ATS_FETCHERS[kind](slug)
    else:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        postings = {link: _posting(text, link)
                    for link, text in extract_postings(resp.text, url).items()}
        kind = "html-scrape"
    if title_match:
        pattern = re.compile(title_match, re.IGNORECASE)
        postings = {k: v for k, v in postings.items() if pattern.search(v["title"])}
    return postings, kind


def _sync():
    """Import sync.py lazily: it loads studio/.env and the Asana token."""
    sys.path.insert(0, str(STUDIO_DIR))
    import sync
    return sync


def create_posting_task(company_name, title, link, dry_run=False):
    """Create one Prospecting task for a new posting. Returns its GID."""
    sync = _sync()
    cfg = {k: os.getenv(f"CAREERS_WATCH_{k}") for k in (
        "PROJECT_GID", "SECTION_GID", "CATEGORY_FIELD", "CATEGORY_OPTION", "URL_FIELD")}
    missing = [k for k, v in cfg.items() if not v]
    if missing:
        raise RuntimeError(f"studio/.env is missing CAREERS_WATCH_{', CAREERS_WATCH_'.join(missing)}")

    name = f"Apply for the {title} role at {company_name}"
    notes = (
        f"New opening at {company_name}: {title}.\n\n"
        f"Done: applied, or decided not to.\n\n"
        f"Posting: {link}"
    )
    if dry_run:
        print(f"{LOG_PREFIX} [DRY-RUN] would create task: {name!r}")
        return "dry-run-gid"

    gid = sync.create_task(cfg["PROJECT_GID"], name, notes, assignee_gid=sync.USER_GID)
    sync._post(f"/sections/{cfg['SECTION_GID']}/addTask", {"data": {"task": gid}})
    sync._put(f"/tasks/{gid}", {"data": {"custom_fields": {
        cfg["CATEGORY_FIELD"]: cfg["CATEGORY_OPTION"],
        cfg["URL_FIELD"]: link,
    }}})
    return gid


def check_company(company, dry_run=False):
    slug = company["slug"]
    name = company["name"]
    url = company["url"]
    state = load_state(slug)
    prev_links = set(state.get("seen_links", []))
    # First run is "never checked", not "nothing seen": a company whose board
    # emptied must still raise a task for the next posting.
    first_run = state.get("last_checked") is None

    try:
        postings, source = fetch_postings(url, company.get("title_match"))
    except (requests.RequestException, ValueError) as e:
        print(f"{LOG_PREFIX} ERROR fetching {name} ({url}): {e}")
        return

    current_links = set(postings.keys())

    if not current_links:
        note = "page may be JS-rendered" if source == "html-scrape" else "ATS board may be empty"
        print(f"{LOG_PREFIX} WARN {name}: no postings found via {source} — {note}")

    new_links = sorted(current_links - prev_links)
    seen = set(prev_links & current_links)

    if first_run:
        seen = set(current_links)
        print(f"{LOG_PREFIX} {name}: baseline established ({len(current_links)} postings), no tasks")
    elif new_links:
        for link in new_links:
            try:
                p = postings[link]
                gid = create_posting_task(p["company"] or name, p["title"], p["url"] or link,
                                          dry_run=dry_run)
            except Exception as e:  # leave it unseen so the next run retries
                print(f"{LOG_PREFIX} ERROR creating task for {name} {link}: {e}")
                continue
            seen.add(link)
            print(f"{LOG_PREFIX} {name}: new posting {postings[link]['title']!r} -> task {gid}")
    else:
        print(f"{LOG_PREFIX} {name}: no change ({len(current_links)} postings)")

    if dry_run:
        return
    state["seen_links"] = sorted(seen)
    state["last_checked"] = datetime.datetime.now().isoformat()
    save_state(slug, state)


def cmd_add(name, url, title_match=None):
    companies = load_registry()
    slug = slugify(name)
    if any(c["slug"] == slug for c in companies):
        print(f"{name} is already in the registry (slug: {slug})")
        return
    entry = {"name": name, "slug": slug, "url": url}
    if title_match:
        entry["title_match"] = title_match
    companies.append(entry)
    save_registry(companies)
    print(f"Added {name} ({slug}) — {url}")


def cmd_remove(slug):
    companies = load_registry()
    remaining = [c for c in companies if c["slug"] != slug]
    if len(remaining) == len(companies):
        print(f"No company with slug '{slug}' found")
        return
    save_registry(remaining)
    state_file = STATE_DIR / f"{slug}.json"
    if state_file.exists():
        state_file.unlink()
    print(f"Removed {slug}")


def cmd_list():
    companies = load_registry()
    if not companies:
        print("No companies registered yet.")
        return
    for c in companies:
        state = load_state(c["slug"])
        last = state.get("last_checked") or "never"
        n = len(state.get("seen_links", []))
        print(f"{c['name']:30s} {c['slug']:20s} {n:3d} postings  last checked: {last}")
        print(f"  {c['url']}")


def main():
    parser = argparse.ArgumentParser(description="Watch target company careers pages for new postings")
    parser.add_argument("--add", nargs=2, metavar=("NAME", "URL"))
    parser.add_argument("--title-match", metavar="REGEX",
                        help="with --add: only titles matching this (case-insensitive)")
    parser.add_argument("--remove", metavar="SLUG")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would be created; create nothing, save no state")
    args = parser.parse_args()

    if args.add:
        cmd_add(*args.add, title_match=args.title_match)
        return
    if args.remove:
        cmd_remove(args.remove)
        return
    if args.list:
        cmd_list()
        return

    companies = load_registry()
    if not companies:
        print(f"{LOG_PREFIX} No companies registered. Use --add \"Name\" \"URL\" first.")
        return
    for company in companies:
        check_company(company, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
