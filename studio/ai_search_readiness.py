#!/usr/bin/env python3
"""
Bain Studio AI Search Readiness Audit
Checks a site's readiness for AI crawlers and answer engines (ChatGPT, Perplexity,
Google AI Overviews, Claude, etc.) — distinct from traditional technical SEO.

Usage: python3 ai_search_readiness.py <base_url> [--pages /,/path/] [--output report.md]
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from html.parser import HTMLParser


UA = "Mozilla/5.0 (compatible; BainDesignAIReadiness/1.0)"

# Known AI crawler user-agents worth checking for explicit robots.txt rules
AI_BOTS = [
    "GPTBot",           # OpenAI (ChatGPT browsing/training)
    "ChatGPT-User",     # OpenAI (live ChatGPT browsing)
    "ClaudeBot",        # Anthropic
    "Claude-Web",       # Anthropic (legacy)
    "anthropic-ai",     # Anthropic
    "PerplexityBot",    # Perplexity
    "Google-Extended",  # Google (Gemini/AI Overviews training)
    "Applebot-Extended",# Apple Intelligence
    "CCBot",            # Common Crawl (feeds many AI training sets)
    "Bytespider",       # ByteDance
    "Amazonbot",        # Amazon (Alexa/AI)
]


def err(msg):
    print(f"  {msg}", file=sys.stderr)


def status(msg):
    print(f"-> {msg}", file=sys.stderr)


def fetch(url, timeout=15, headers=None):
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace"), r.getcode(), None
    except urllib.error.HTTPError as e:
        return None, e.code, f"HTTP {e.code}"
    except Exception as e:
        return None, None, str(e)


def check_robots_ai_bots(base_url):
    """Parse robots.txt and determine, per known AI bot, whether it is explicitly
    disallowed, explicitly allowed, or falls under the generic wildcard rule."""
    url = base_url.rstrip("/") + "/robots.txt"
    status(f"Checking robots.txt for AI bot rules -> {url}")
    html, code, error = fetch(url)
    result = {"url": url, "error": error, "wildcard_disallow_all": False,
              "per_bot": {}, "raw_found": False}
    if error or not html:
        return result
    result["raw_found"] = True

    # Parse into blocks keyed by user-agent
    blocks = {}
    current_agents = []
    for line in html.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().lower()
        val = val.strip()
        if key == "user-agent":
            if current_agents and current_agents[-1] not in blocks:
                pass
            current_agents = [val]
            blocks.setdefault(val, [])
        elif key == "disallow" and current_agents:
            for a in current_agents:
                blocks.setdefault(a, []).append(("disallow", val))
        elif key == "allow" and current_agents:
            for a in current_agents:
                blocks.setdefault(a, []).append(("allow", val))

    wildcard_rules = blocks.get("*", [])
    result["wildcard_disallow_all"] = any(v == "/" for k, v in wildcard_rules if k == "disallow")

    for bot in AI_BOTS:
        matched_block = None
        for agent in blocks:
            if agent.lower() == bot.lower():
                matched_block = blocks[agent]
                break
        if matched_block is None:
            result["per_bot"][bot] = {"explicit": False, "blocked": result["wildcard_disallow_all"],
                                       "note": "No explicit rule — inherits wildcard" if not result["wildcard_disallow_all"]
                                               else "No explicit rule — blocked by wildcard Disallow: /"}
        else:
            blocked_all = any(k == "disallow" and v == "/" for k, v in matched_block)
            result["per_bot"][bot] = {"explicit": True, "blocked": blocked_all,
                                       "note": "Explicitly blocked" if blocked_all else "Explicitly allowed"}
    return result


def check_llms_txt(base_url):
    url = base_url.rstrip("/") + "/llms.txt"
    status(f"Checking llms.txt -> {url}")
    html, code, error = fetch(url)
    return {"url": url, "present": html is not None and code == 200, "code": code}


class StructuredDataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._in_jsonld = False
        self._buf = ""
        self.jsonld_types = []
        self.jsonld_raw_count = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
            self._in_jsonld = True
            self._buf = ""

    def handle_endtag(self, tag):
        if tag == "script" and self._in_jsonld:
            self._in_jsonld = False
            self.jsonld_raw_count += 1
            try:
                data = json.loads(self._buf.strip())
                items = data if isinstance(data, list) else [data]
                for item in items:
                    t = item.get("@type") if isinstance(item, dict) else None
                    if t:
                        self.jsonld_types.append(t if isinstance(t, str) else ", ".join(t))
            except Exception:
                pass

    def handle_data(self, data):
        if self._in_jsonld:
            self._buf += data


def check_structured_data(url):
    status(f"Checking structured data -> {url}")
    html, code, error = fetch(url)
    if error or not html:
        return {"url": url, "error": error, "types": [], "raw_count": 0}
    p = StructuredDataParser()
    p.feed(html)
    return {"url": url, "error": None, "types": p.jsonld_types, "raw_count": p.jsonld_raw_count}


def check_js_dependency(url):
    """Rough heuristic: fetch raw HTML (no JS execution) and check how much
    real text content is present, plus common SPA framework markers."""
    status(f"Checking JS-rendering dependency -> {url}")
    html, code, error = fetch(url)
    if error or not html:
        return {"url": url, "error": error, "text_length": 0, "spa_markers": []}

    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    markers = []
    if re.search(r'id=["\']__next["\']', html):
        markers.append("Next.js (#__next)")
    if re.search(r'id=["\']root["\'][^>]*>\s*</div>\s*<script', html):
        markers.append("React root with no server-rendered content")
    if "ng-app" in html or "ng-version" in html:
        markers.append("Angular")
    if "window.__NUXT__" in html:
        markers.append("Nuxt")
    if 'data-reactroot' in html:
        markers.append("React (data-reactroot)")

    return {"url": url, "error": None, "text_length": len(text), "spa_markers": markers}


def render_report(base_url, pages, robots_ai, llms, structured_data, js_checks, meta_note):
    lines = []
    today = date.today().isoformat()

    lines += [
        f"# AI Search Readiness Audit — {base_url}",
        f"**Date:** {today}  ",
        f"**Pages audited:** {len(pages)}  ",
        "",
        "---",
        "",
        "## AI Bot Crawl Access (robots.txt)",
        "",
    ]

    if robots_ai["error"]:
        lines.append(f"FAIL: robots.txt unreachable — {robots_ai['error']}")
    else:
        lines += ["| Bot | Status | Note |", "|---|---|---|"]
        for bot, info in robots_ai["per_bot"].items():
            status_label = "FAIL: Blocked" if info["blocked"] else "PASS: Allowed"
            lines.append(f"| {bot} | {status_label} | {info['note']} |")

    lines += ["", "---", "", "## llms.txt", ""]
    if llms["present"]:
        lines.append(f"PASS: Found at {llms['url']}")
    else:
        lines.append(f"WARN: Not found ({llms['url']} returned {llms.get('code', 'no response')})")

    lines += ["", "---", "", "## Structured Data (JSON-LD)", "", "| Page | Blocks | Types | Status |", "|---|---|---|---|"]
    for sd in structured_data:
        label = sd["url"].replace(base_url, "") or "/"
        if sd.get("error"):
            lines.append(f"| {label} | - | - | FAIL: {sd['error']} |")
            continue
        types = ", ".join(sd["types"]) if sd["types"] else "-"
        sd_status = "PASS" if sd["types"] else "WARN: None"
        lines.append(f"| {label} | {sd['raw_count']} | {types} | {sd_status} |")

    lines += ["", "---", "", "## JS-Rendering Dependency", "",
              "Content AI crawlers can read without executing JavaScript:", "",
              "| Page | Text length (chars) | SPA markers | Status |", "|---|---|---|---|"]
    for js in js_checks:
        label = js["url"].replace(base_url, "") or "/"
        if js.get("error"):
            lines.append(f"| {label} | - | - | FAIL: {js['error']} |")
            continue
        markers = ", ".join(js["spa_markers"]) if js["spa_markers"] else "-"
        if js["spa_markers"] or js["text_length"] < 500:
            js_status = "WARN: Likely JS-dependent"
        else:
            js_status = "PASS"
        lines.append(f"| {label} | {js['text_length']} | {markers} | {js_status} |")

    lines += ["", "---", "", "## Issues Summary", ""]

    blocking = []
    warnings = []

    if robots_ai.get("error"):
        blocking.append(f"robots.txt unreachable: {robots_ai['error']}")
    else:
        for bot, info in robots_ai["per_bot"].items():
            if info["blocked"]:
                blocking.append(f"{bot} is blocked from crawling this site")

    if not llms["present"]:
        warnings.append("No llms.txt found — AI crawlers have no curated content summary to work from")

    for sd in structured_data:
        label = sd["url"].replace(base_url, "") or "/"
        if not sd.get("error") and not sd["types"]:
            warnings.append(f"`{label}` — no JSON-LD structured data (reduces AI answer-engine citation reliability)")

    for js in js_checks:
        label = js["url"].replace(base_url, "") or "/"
        if not js.get("error") and (js["spa_markers"] or js["text_length"] < 500):
            blocking.append(f"`{label}` — content likely requires JavaScript to render; many AI crawlers won't see it")

    if blocking:
        lines.append(f"### Blocking Issues ({len(blocking)})\n")
        for i, b in enumerate(blocking, 1):
            lines.append(f"{i}. {b}")
        lines.append("")
    else:
        lines.append("### Blocking Issues\n\nNone.\n")

    if warnings:
        lines.append(f"### Warnings ({len(warnings)})\n")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")
    else:
        lines.append("### Warnings\n\nNone.\n")

    lines += ["---", "", "## Action Points", "",
              "{Populate with 3-6 prioritised, specific recommendations based on the findings above.",
              "Label each [HIGH]/[MEDIUM]/[LOW]. See skill instructions for the priority framework.}",
              ""]

    if meta_note:
        lines += ["---", "", meta_note, ""]

    lines += ["---", "", f"*Generated by Bain Studio AI Search Readiness Audit · {today}*", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Bain Studio AI Search Readiness Audit")
    parser.add_argument("base_url", nargs="?", help="Base URL e.g. https://example.com")
    parser.add_argument("--pages", help="Comma-separated paths e.g. /,/about/,/blog/")
    parser.add_argument("--output", help="Save report to this file path")
    args = parser.parse_args()

    if not args.base_url:
        parser.print_help()
        sys.exit(0)

    base_url = args.base_url.rstrip("/")
    paths = [p.strip() for p in args.pages.split(",")] if args.pages else ["/"]
    pages = [base_url + (p if p.startswith("/") else "/" + p) for p in paths]

    status(f"Auditing {base_url} — {len(pages)} page(s)")

    robots_ai = check_robots_ai_bots(base_url)
    llms = check_llms_txt(base_url)
    structured_data = [check_structured_data(url) for url in pages]
    js_checks = [check_js_dependency(url) for url in pages]

    status("Rendering report...")
    report = render_report(base_url, pages, robots_ai, llms, structured_data, js_checks, meta_note=None)

    if args.output:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
        with open(args.output, "w") as f:
            f.write(report)
        err(f"Report saved to {args.output}")

    print(report)


if __name__ == "__main__":
    main()
