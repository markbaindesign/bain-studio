#!/usr/bin/env python3
"""
Careers page watcher.

Tracks a dynamic list of target companies' careers pages and alerts via Slack
(studio notifier) when a new job posting link appears. State is a per-company
snapshot of previously-seen posting links; alerts fire only on genuinely new
entries, not on every page edit.

Registry: studio/collectors/careers_watch_companies.json
  [{"name": "Acme Inc", "slug": "acme", "url": "https://acme.com/careers"}, ...]

State: studio/collectors/careers_watch_state/{slug}.json (gitignored)

Usage:
  python3 careers_watch.py                       # check all companies, alert on new postings
  python3 careers_watch.py --add "Name" "URL"     # add a company to the registry
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
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

STUDIO_DIR = Path(__file__).parent.parent
COLLECTORS_DIR = Path(__file__).parent
REGISTRY_FILE = COLLECTORS_DIR / "careers_watch_companies.json"
STATE_DIR = COLLECTORS_DIR / "careers_watch_state"
NOTIFIER = STUDIO_DIR / "notifier.py"
LOG_PREFIX = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] careers_watch"

# Known ATS URL patterns -> (kind, slug-extraction regex)
ATS_PATTERNS = [
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


def fetch_greenhouse(slug):
    r = requests.get(
        f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
        headers=HEADERS, timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    if "jobs" not in data:
        raise ValueError(f"unexpected Greenhouse response: {data}")
    return {j["absolute_url"]: j["title"] for j in data["jobs"]}


def fetch_lever(slug):
    r = requests.get(
        f"https://api.lever.co/v0/postings/{slug}?mode=json",
        headers=HEADERS, timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise ValueError(f"unexpected Lever response: {data}")
    return {j["hostedUrl"]: j["text"] for j in data}


def fetch_workable(slug):
    r = requests.get(
        f"https://www.workable.com/api/accounts/{slug}?details=true",
        headers=HEADERS, timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    if "jobs" not in data:
        raise ValueError(f"unexpected Workable response: {data}")
    return {j["shortlink"]: j["title"] for j in data["jobs"]}


ATS_FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "workable": fetch_workable,
}


def fetch_postings(url):
    """Fetch current postings for a company, via ATS API if detected, else HTML scrape."""
    ats = detect_ats(url)
    if ats:
        kind, slug = ats
        return ATS_FETCHERS[kind](slug), kind
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return extract_postings(resp.text, url), "html-scrape"


def notify(message, details=None, priority="normal"):
    cmd = [
        "python3", str(NOTIFIER), message,
        "--project", "PIPE", "--priority", priority, "--sender", "careers-watch",
    ]
    if details:
        cmd += ["--details", details]
    subprocess.run(cmd, check=False)


def check_company(company):
    slug = company["slug"]
    name = company["name"]
    url = company["url"]
    state = load_state(slug)
    prev_links = set(state.get("seen_links", []))

    try:
        postings, source = fetch_postings(url)
    except (requests.RequestException, ValueError) as e:
        print(f"{LOG_PREFIX} ERROR fetching {name} ({url}): {e}")
        return

    current_links = set(postings.keys())

    if not current_links:
        note = "page may be JS-rendered" if source == "html-scrape" else "ATS board may be empty"
        print(f"{LOG_PREFIX} WARN {name}: no postings found via {source} — {note}")

    new_links = current_links - prev_links

    # Only alert once the baseline is established, to avoid a noisy first run
    if prev_links and new_links:
        new_titles = [postings[link] for link in new_links]
        details = "\n".join(f"- {title}\n  {link}" for link, title in
                             ((l, postings[l]) for l in new_links))
        notify(
            f"New posting(s) at {name}: {', '.join(new_titles[:5])}",
            details=details,
            priority="normal",
        )
        print(f"{LOG_PREFIX} {name}: {len(new_links)} new posting(s)")
    elif not prev_links:
        print(f"{LOG_PREFIX} {name}: baseline established ({len(current_links)} postings), no alert")
    else:
        print(f"{LOG_PREFIX} {name}: no change ({len(current_links)} postings)")

    state["seen_links"] = sorted(current_links)
    state["last_checked"] = datetime.datetime.now().isoformat()
    save_state(slug, state)


def cmd_add(name, url):
    companies = load_registry()
    slug = slugify(name)
    if any(c["slug"] == slug for c in companies):
        print(f"{name} is already in the registry (slug: {slug})")
        return
    companies.append({"name": name, "slug": slug, "url": url})
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
    parser.add_argument("--remove", metavar="SLUG")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.add:
        cmd_add(*args.add)
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
        check_company(company)


if __name__ == "__main__":
    main()
