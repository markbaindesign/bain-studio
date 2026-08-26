#!/usr/bin/env python3
"""
WP Pulse — WordPress dev ecosystem digest.

Collates new posts across a registry of WordPress development blogs, summarises
them in a single headless Claude call, writes a dated markdown digest into the
Obsidian vault, and pings Slack with the headlines.

Registry: studio/collectors/wp_pulse_sources.json
  [{"name": "GeneratePress", "slug": "generatepress", "feed": "https://..."}, ...]

State: studio/collectors/wp_pulse_state/{slug}.json (gitignored)
  Per-source list of previously-seen entry ids, so each post is summarised once.

Digests: $OBSIDIAN_VAULT/WP Pulse/YYYY-MM-DD-wp-pulse.md
  Override the destination with WP_PULSE_DIGEST_DIR.

Usage:
  python3 wp_pulse.py                      # collect, summarise, write digest, notify
  python3 wp_pulse.py --dry-run            # list what's new, no Claude call, no writes
  python3 wp_pulse.py --no-notify          # write the digest but skip the Slack ping
  python3 wp_pulse.py --since-days 30      # widen the lookback window for this run
  python3 wp_pulse.py --add "Name" "URL"   # add a feed to the registry
  python3 wp_pulse.py --list               # print the registry with last-checked state
  python3 wp_pulse.py --remove SLUG        # remove a feed

Run on cron, twice weekly:
  0 8 * * 1,4 cd /media/data/dev/bain-studio && python3 studio/collectors/wp_pulse.py >> studio/collectors/wp_pulse.log 2>&1

Feeds are parsed with the standard library (RSS 2.0 and Atom both handled), so
this adds no dependency beyond `requests`, which the other collectors already use.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

STUDIO_DIR = Path(__file__).parent.parent
COLLECTORS_DIR = Path(__file__).parent
PROJECT_ROOT = STUDIO_DIR.parent
REGISTRY_FILE = COLLECTORS_DIR / "wp_pulse_sources.json"
STATE_DIR = COLLECTORS_DIR / "wp_pulse_state"
NOTIFIER = STUDIO_DIR / "notifier.py"
LOG_PREFIX = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] wp_pulse"

load_dotenv(STUDIO_DIR / ".env")

# Posts older than this are marked seen without being summarised. Keeps the very
# first run (empty state) from digesting a decade of back-catalogue.
DEFAULT_LOOKBACK_DAYS = 14
# Guard against a single source flooding one digest (e.g. after a long outage).
MAX_ENTRIES_PER_SOURCE = 12
# Excerpt length passed to Claude per post — enough to summarise, cheap to send.
EXCERPT_CHARS = 700

ATOM_NS = "{http://www.w3.org/2005/Atom}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

DEFAULT_SOURCES = [
    ("GeneratePress", "https://generatepress.com/blog/feed/"),
    ("WP Tavern", "https://wptavern.com/feed"),
    ("WordPress News", "https://wordpress.org/news/feed/"),
    ("Make WordPress Core", "https://make.wordpress.org/core/feed/"),
    ("Make WordPress Design", "https://make.wordpress.org/design/feed/"),
    ("WordPress Developer Blog", "https://developer.wordpress.org/news/feed/"),
    ("Post Status", "https://poststatus.com/feed/"),
    ("Advanced Custom Fields", "https://www.advancedcustomfields.com/blog/feed/"),
    ("Elegant Themes (Divi)", "https://www.elegantthemes.com/blog/feed"),
    ("Kinsta", "https://kinsta.com/blog/feed/"),
    ("Delicious Brains", "https://deliciousbrains.com/feed/"),
    ("WP Mayor", "https://wpmayor.com/feed/"),
    ("Smashing Magazine (WordPress)", "https://www.smashingmagazine.com/category/wordpress/feed/"),
]


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def load_registry():
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text())
    sources = [
        {"name": name, "slug": slugify(name), "feed": feed}
        for name, feed in DEFAULT_SOURCES
    ]
    save_registry(sources)
    print(f"{LOG_PREFIX} seeded registry with {len(sources)} default sources")
    return sources


def save_registry(sources):
    REGISTRY_FILE.write_text(json.dumps(sources, indent=2) + "\n")


def load_state(slug):
    f = STATE_DIR / f"{slug}.json"
    if f.exists():
        return json.loads(f.read_text())
    return {"seen_ids": [], "last_checked": None}


def save_state(slug, state):
    STATE_DIR.mkdir(exist_ok=True)
    # Unbounded growth is pointless — a feed only ever serves its recent window.
    state["seen_ids"] = state["seen_ids"][-500:]
    (STATE_DIR / f"{slug}.json").write_text(json.dumps(state, indent=2))


def strip_html(text):
    if not text:
        return ""
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;?", " ", text)
    text = re.sub(r"&amp;?", "&", text)
    text = re.sub(r"&#8217;|&rsquo;", "'", text)
    text = re.sub(r"&#8220;|&#8221;|&ldquo;|&rdquo;", '"', text)
    return re.sub(r"\s+", " ", text).strip()


def parse_date(raw):
    """Feeds mix RFC 822 (RSS) and ISO 8601 (Atom). Return an aware datetime or None."""
    if not raw:
        return None
    raw = raw.strip()
    try:
        dt = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        try:
            dt = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def _text(el):
    return el.text.strip() if el is not None and el.text else ""


def parse_feed(xml_text):
    """Extract entries from an RSS 2.0 or Atom feed. Returns a list of dicts."""
    root = ET.fromstring(xml_text.encode("utf-8"))
    entries = []

    # RSS 2.0
    for item in root.findall(".//item"):
        link = _text(item.find("link"))
        entries.append({
            "title": _text(item.find("title")) or "(untitled)",
            "link": link,
            "id": _text(item.find("guid")) or link,
            "published": parse_date(
                _text(item.find("pubDate"))
                or _text(item.find("{http://purl.org/dc/elements/1.1/}date"))
            ),
            "summary": strip_html(
                _text(item.find("description"))
                or _text(item.find("{http://purl.org/rss/1.0/modules/content/}encoded"))
            ),
        })

    # Atom
    for entry in root.findall(f".//{ATOM_NS}entry"):
        link = ""
        for link_el in entry.findall(f"{ATOM_NS}link"):
            rel = link_el.get("rel", "alternate")
            if rel == "alternate":
                link = link_el.get("href", "")
                break
        entries.append({
            "title": _text(entry.find(f"{ATOM_NS}title")) or "(untitled)",
            "link": link,
            "id": _text(entry.find(f"{ATOM_NS}id")) or link,
            "published": parse_date(
                _text(entry.find(f"{ATOM_NS}published"))
                or _text(entry.find(f"{ATOM_NS}updated"))
            ),
            "summary": strip_html(
                _text(entry.find(f"{ATOM_NS}summary"))
                or _text(entry.find(f"{ATOM_NS}content"))
            ),
        })

    return [e for e in entries if e["link"]]


def collect_source(source, lookback_days, dry_run):
    """Return the list of unseen, in-window entries for one source."""
    slug = source["slug"]
    name = source["name"]
    state = load_state(slug)
    seen = set(state.get("seen_ids", []))
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=lookback_days)

    try:
        resp = requests.get(source["feed"], headers=HEADERS, timeout=25)
        resp.raise_for_status()
        entries = parse_feed(resp.text)
    except requests.RequestException as e:
        print(f"{LOG_PREFIX} ERROR fetching {name}: {e}")
        return []
    except ET.ParseError as e:
        print(f"{LOG_PREFIX} ERROR parsing {name} feed (not valid XML?): {e}")
        return []

    if not entries:
        print(f"{LOG_PREFIX} WARN {name}: feed parsed but contained no entries")
        return []

    fresh = []
    for entry in entries:
        if entry["id"] in seen:
            continue
        # An undated entry is treated as current rather than dropped — some feeds
        # omit pubDate entirely, and silently skipping them would hide a source.
        if entry["published"] and entry["published"] < cutoff:
            seen.add(entry["id"])  # too old to be news; never summarise it
            continue
        entry["source"] = name
        fresh.append(entry)

    fresh.sort(key=lambda e: e["published"] or datetime.datetime.min.replace(
        tzinfo=datetime.timezone.utc), reverse=True)
    if len(fresh) > MAX_ENTRIES_PER_SOURCE:
        print(f"{LOG_PREFIX} {name}: {len(fresh)} new, capping at {MAX_ENTRIES_PER_SOURCE}")
        fresh = fresh[:MAX_ENTRIES_PER_SOURCE]

    print(f"{LOG_PREFIX} {name}: {len(fresh)} new post(s) of {len(entries)} in feed")

    if not dry_run:
        # Mark everything returned as seen now. A crash mid-summarise loses one
        # digest rather than replaying the same posts on every subsequent run.
        state["seen_ids"] = sorted(seen | {e["id"] for e in fresh})
        state["last_checked"] = datetime.datetime.now().isoformat()
        save_state(slug, state)

    return fresh


def build_prompt(entries):
    blocks = []
    for i, e in enumerate(entries, 1):
        date = e["published"].strftime("%Y-%m-%d") if e["published"] else "undated"
        blocks.append(
            f"{i}. [{e['source']}] {e['title']} ({date})\n"
            f"   {e['link']}\n"
            f"   {e['summary'][:EXCERPT_CHARS]}"
        )
    posts = "\n\n".join(blocks)

    return f"""You are writing a WordPress-ecosystem digest for Mark Bain, who runs a
one-person web design studio. His work is client WordPress sites: Divi child themes,
FSE/block themes, ACF Pro, custom plugins, WooCommerce, Cloudways hosting, DDEV and
VVV local dev, plus theme-scaffolding tooling of his own.

Below are {len(entries)} new blog posts. Write a markdown digest.

Rules:
- Group posts under a `## {{Source name}}` heading, sources in the order given.
- For each post: `### [Title](url)` then a 2-3 sentence summary of what the post
  actually says, then a line starting `**Why it matters:**` explaining the relevance
  to Mark's work specifically. If a post is not relevant to him, say so plainly in
  that line - do not manufacture relevance.
- Base summaries only on the excerpt provided. Where an excerpt is too thin to
  summarise, say "Excerpt too short to summarise - see the post." rather than guessing.
- Open the digest with a `## At a glance` section: 3-5 bullets naming the genuinely
  important developments of this batch. If nothing is important, say that.
- Never use m-dashes. Use a single hyphen sparingly if a dash is needed.
- Use ISO dates (YYYY-MM-DD).
- Output only the markdown digest. No preamble, no closing commentary.

Posts:

{posts}"""


def summarise(entries):
    """One headless Claude call for the whole batch. Returns (markdown, cost, error)."""
    result = subprocess.run(
        ["claude", "-p", build_prompt(entries), "--output-format", "json"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )

    if result.returncode != 0:
        return None, 0, f"claude exited {result.returncode}: {result.stderr[:200]}"

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None, 0, "could not parse claude output"

    if data.get("is_error"):
        return None, 0, f"claude error: {str(data.get('result', ''))[:200]}"

    body = (data.get("result") or "").strip()
    if not body:
        return None, 0, "claude returned an empty digest"

    return body, data.get("total_cost_usd", 0), None


def digest_dir():
    override = os.getenv("WP_PULSE_DIGEST_DIR")
    if override:
        return Path(override)
    vault = os.getenv("OBSIDIAN_VAULT")
    if vault:
        return Path(vault) / "WP Pulse"
    return COLLECTORS_DIR / "wp_pulse_digests"


def write_digest(body, entries, cost):
    today = datetime.date.today().isoformat()
    out_dir = digest_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{today}-wp-pulse.md"

    sources = sorted({e["source"] for e in entries})
    frontmatter = (
        "---\n"
        "tags: [wp-pulse, digest, wordpress]\n"
        f"date: {today}\n"
        f"posts: {len(entries)}\n"
        f"sources: [{', '.join(json.dumps(s) for s in sources)}]\n"
        f"cost_usd: {cost:.4f}\n"
        "---\n\n"
        f"# WP Pulse - {today}\n\n"
        f"{len(entries)} new post(s) across {len(sources)} source(s).\n\n"
    )

    # Same-day reruns append rather than clobbering the earlier digest.
    if path.exists():
        path.write_text(path.read_text() + f"\n\n---\n\n## Later run - "
                        f"{datetime.datetime.now().strftime('%H:%M')}\n\n" + body + "\n")
    else:
        path.write_text(frontmatter + body + "\n")

    return path


def notify(message, details=None, priority="low"):
    cmd = [
        "python3", str(NOTIFIER), message,
        "--project", "BSTD", "--priority", priority, "--sender", "wp-pulse",
    ]
    if details:
        cmd += ["--details", details]
    subprocess.run(cmd, check=False)


def cmd_add(name, feed):
    sources = load_registry()
    slug = slugify(name)
    if any(s["slug"] == slug for s in sources):
        print(f"{name} is already in the registry (slug: {slug})")
        return
    sources.append({"name": name, "slug": slug, "feed": feed})
    save_registry(sources)
    print(f"Added {name} ({slug}) - {feed}")


def cmd_remove(slug):
    sources = load_registry()
    remaining = [s for s in sources if s["slug"] != slug]
    if len(remaining) == len(sources):
        print(f"No source with slug '{slug}' found")
        return
    save_registry(remaining)
    state_file = STATE_DIR / f"{slug}.json"
    if state_file.exists():
        state_file.unlink()
    print(f"Removed {slug}")


def cmd_list():
    sources = load_registry()
    if not sources:
        print("No sources registered yet.")
        return
    for s in sources:
        state = load_state(s["slug"])
        last = state.get("last_checked") or "never"
        print(f"{s['name']:32s} {s['slug']:28s} last checked: {last}")
        print(f"  {s['feed']}")


def main():
    parser = argparse.ArgumentParser(
        description="Collate new WordPress dev blog posts into a summarised digest")
    parser.add_argument("--add", nargs=2, metavar=("NAME", "FEED_URL"))
    parser.add_argument("--remove", metavar="SLUG")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="list new posts without calling Claude or writing state")
    parser.add_argument("--no-notify", action="store_true", help="skip the Slack ping")
    parser.add_argument("--since-days", type=int, default=DEFAULT_LOOKBACK_DAYS,
                        help=f"lookback window in days (default {DEFAULT_LOOKBACK_DAYS})")
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

    sources = load_registry()
    if not sources:
        print(f"{LOG_PREFIX} No sources registered. Use --add \"Name\" \"FEED_URL\" first.")
        return

    entries = []
    for source in sources:
        entries.extend(collect_source(source, args.since_days, args.dry_run))

    if not entries:
        print(f"{LOG_PREFIX} nothing new across {len(sources)} source(s), no digest written")
        return

    if args.dry_run:
        for e in entries:
            date = e["published"].strftime("%Y-%m-%d") if e["published"] else "undated"
            print(f"  [{e['source']}] {date}  {e['title']}\n    {e['link']}")
        print(f"{LOG_PREFIX} dry run: {len(entries)} post(s) would be summarised")
        return

    body, cost, error = summarise(entries)
    if error:
        print(f"{LOG_PREFIX} ERROR summarising: {error}")
        notify(f"WP Pulse failed to summarise {len(entries)} new post(s)",
               details=error, priority="normal")
        sys.exit(1)

    path = write_digest(body, entries, cost)
    print(f"{LOG_PREFIX} wrote digest: {path} ({len(entries)} posts, ${cost:.4f})")

    if not args.no_notify:
        by_source = {}
        for e in entries:
            by_source.setdefault(e["source"], []).append(e["title"])
        details = "\n".join(
            f"*{src}*\n" + "\n".join(f"- {t}" for t in titles)
            for src, titles in by_source.items()
        )
        details += f"\n\nFull digest: {path}"
        notify(
            f"WP Pulse: {len(entries)} new post(s) across {len(by_source)} source(s)",
            details=details,
        )


if __name__ == "__main__":
    main()
