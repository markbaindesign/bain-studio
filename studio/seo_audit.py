#!/usr/bin/env python3
"""
Bain Studio SEO Audit
Usage: python3 seo_audit.py <base_url> [--pages /,/path/] [--output report.md] [--api-key KEY] [--no-psi]
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from html.parser import HTMLParser


UA = "Mozilla/5.0 (compatible; BainDesignSEOAudit/1.0)"
PSI_BASE = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


def err(msg):
    print(f"  {msg}", file=sys.stderr)


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace"), r.geturl(), None
    except urllib.error.HTTPError as e:
        return None, url, f"HTTP {e.code}"
    except Exception as e:
        return None, url, str(e)


def status(msg):
    print(f"-> {msg}", file=sys.stderr)


class HeadParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_head = False
        self.title_text = ""
        self._in_title = False
        self.description = None
        self.canonical = None
        self.robots_meta = None
        self.og = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "head":
            self.in_head = True
        if not self.in_head:
            return
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = attrs.get("name", "").lower()
            prop = attrs.get("property", "").lower()
            content = attrs.get("content", "")
            if name == "description":
                self.description = content
            elif name == "robots":
                self.robots_meta = content
            elif prop in ("og:title", "og:description", "og:image"):
                self.og[prop] = content
        elif tag == "link":
            if attrs.get("rel", "").lower() == "canonical":
                self.canonical = attrs.get("href", "")

    def handle_endtag(self, tag):
        if tag == "head":
            self.in_head = False
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title_text += data


class BodyParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.h1s = []
        self._in_h1 = False
        self._h1_buf = ""
        self._in_jsonld = False
        self._jsonld_buf = ""
        self.jsonld_types = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h1":
            self._in_h1 = True
            self._h1_buf = ""
        if tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
            self._in_jsonld = True
            self._jsonld_buf = ""

    def handle_endtag(self, tag):
        if tag == "h1":
            self._in_h1 = False
            text = self._h1_buf.strip()
            if text:
                self.h1s.append(text)
        if tag == "script" and self._in_jsonld:
            self._in_jsonld = False
            try:
                raw = self._jsonld_buf.strip()
                data = json.loads(raw)
                if isinstance(data, list):
                    for item in data:
                        t = item.get("@type")
                        if t:
                            self.jsonld_types.append(t if isinstance(t, str) else ", ".join(t))
                elif isinstance(data, dict):
                    t = data.get("@type")
                    if t:
                        self.jsonld_types.append(t if isinstance(t, str) else ", ".join(t))
            except Exception:
                pass

    def handle_data(self, data):
        if self._in_h1:
            self._h1_buf += data
        if self._in_jsonld:
            self._jsonld_buf += data


def check_robots(base_url):
    url = base_url.rstrip("/") + "/robots.txt"
    status(f"Checking robots.txt -> {url}")
    html, final_url, error = fetch(url)
    result = {"url": url, "error": error, "disallow_all": False, "sitemap_url": None, "raw": ""}
    if error or not html:
        result["error"] = error or "Empty response"
        return result
    result["raw"] = html
    for line in html.splitlines():
        line = line.strip()
        if line.lower().startswith("disallow:") and line.split(":", 1)[1].strip() == "/":
            result["disallow_all"] = True
        if line.lower().startswith("sitemap:"):
            result["sitemap_url"] = line.split(":", 1)[1].strip()
    return result


def check_sitemap(sitemap_url, base_url):
    if not sitemap_url:
        sitemap_url = base_url.rstrip("/") + "/sitemap.xml"
    status(f"Checking sitemap -> {sitemap_url}")
    html, _, error = fetch(sitemap_url)
    result = {"url": sitemap_url, "error": error, "is_index": False, "url_count": 0}
    if error or not html:
        result["error"] = error or "Empty response"
        return result
    try:
        root = ET.fromstring(html)
        ns_match = re.match(r"\{.*?\}", root.tag)
        ns = ns_match.group(0) if ns_match else ""
        if "sitemapindex" in root.tag:
            result["is_index"] = True
            result["url_count"] = len(root.findall(f"{ns}sitemap"))
        else:
            result["url_count"] = len(root.findall(f"{ns}url"))
    except ET.ParseError as e:
        result["error"] = f"XML parse error: {e}"
    return result


def check_page_meta(url):
    status(f"Fetching page -> {url}")
    html, final_url, error = fetch(url)
    result = {"url": url, "final_url": final_url, "error": error}
    if error or not html:
        return result

    head_parser = HeadParser()
    head_parser.feed(html)
    body_parser = BodyParser()
    body_parser.feed(html)

    title = head_parser.title_text.strip()
    desc = head_parser.description
    canonical = head_parser.canonical
    robots_meta = head_parser.robots_meta
    og = head_parser.og
    h1s = body_parser.h1s
    jsonld_types = body_parser.jsonld_types

    result.update({
        "title": title,
        "title_len": len(title),
        "description": desc,
        "desc_len": len(desc) if desc is not None else None,
        "canonical": canonical,
        "robots_meta": robots_meta,
        "noindex": robots_meta is not None and "noindex" in robots_meta.lower(),
        "og_title": og.get("og:title"),
        "og_description": og.get("og:description"),
        "og_image": og.get("og:image"),
        "h1s": h1s,
        "h1_count": len(h1s),
        "jsonld_types": jsonld_types,
    })
    return result


def call_psi(url, strategy, api_key=None):
    params = {"url": url, "strategy": strategy,
              "category": ["performance", "seo", "accessibility", "best-practices"]}
    qs = urllib.parse.urlencode(params, doseq=True)
    if api_key:
        qs += f"&key={urllib.parse.quote(api_key)}"
    full_url = f"{PSI_BASE}?{qs}"
    err(f"  PSI {strategy} -> {url}")
    raw, _, error = fetch(full_url, timeout=60)
    if error or not raw:
        return None, error
    try:
        return json.loads(raw), None
    except json.JSONDecodeError as e:
        return None, f"JSON error: {e}"


def extract_psi_scores(data):
    if not data:
        return {}
    cats = data.get("categories", {})
    audits = data.get("lighthouseResult", {}).get("audits", {})
    scores = {}
    for k, v in cats.items():
        s = v.get("score")
        scores[k] = round(s * 100) if s is not None else None

    def dv(key):
        return audits.get(key, {}).get("displayValue", "-")

    scores["fcp"] = dv("first-contentful-paint")
    scores["lcp"] = dv("largest-contentful-paint")
    scores["tbt"] = dv("total-blocking-time")
    scores["cls"] = dv("cumulative-layout-shift")
    scores["tti"] = dv("interactive")
    return scores


def psi_score_emoji(score):
    if score is None:
        return "-"
    if score >= 90:
        return f"{score} OK"
    if score >= 50:
        return f"{score} WARN"
    return f"{score} FAIL"


def render_report(base_url, pages, robots, sitemap, meta_results, psi_results):
    lines = []
    today = date.today().isoformat()

    lines += [
        f"# SEO Audit — {base_url}",
        f"**Date:** {today}  ",
        f"**Pages audited:** {len(pages)}  ",
        "",
        "---",
        "",
        "## Site-Level Checks",
        "",
        "| Check | Result |",
        "|---|---|",
    ]

    if robots["error"]:
        lines.append(f"| robots.txt | FAIL: {robots['error']} |")
    elif robots["disallow_all"]:
        lines.append("| robots.txt | FAIL: `Disallow: /` — site blocked from crawlers |")
    else:
        lines.append("| robots.txt | PASS: Crawlable |")

    sitemap_directive = robots.get("sitemap_url", "")
    lines.append(f"| Sitemap in robots.txt | {'PASS: ' + sitemap_directive if sitemap_directive else 'WARN: Not declared'} |")

    if sitemap["error"]:
        lines.append(f"| sitemap.xml | FAIL: {sitemap['error']} |")
    else:
        kind = "Index" if sitemap["is_index"] else "Standard"
        lines.append(f"| sitemap.xml | PASS: {kind} — {sitemap['url_count']} URLs |")

    lines += ["", "---", ""]

    if psi_results:
        lines += [
            "## PageSpeed Insights Scores",
            "",
            "| Page | Device | Perf | SEO | A11y | Best Practices | LCP | CLS | TBT |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for url in pages:
            label = url.replace(base_url, "") or "/"
            for strategy in ("mobile", "desktop"):
                scores = psi_results.get(url, {}).get(strategy, {})
                if not scores:
                    lines.append(f"| `{label}` | {strategy} | - | - | - | - | - | - | - |")
                else:
                    lines.append(
                        f"| `{label}` | {strategy} "
                        f"| {psi_score_emoji(scores.get('performance'))} "
                        f"| {psi_score_emoji(scores.get('seo'))} "
                        f"| {psi_score_emoji(scores.get('accessibility'))} "
                        f"| {psi_score_emoji(scores.get('best-practices'))} "
                        f"| {scores.get('lcp', '-')} "
                        f"| {scores.get('cls', '-')} "
                        f"| {scores.get('tbt', '-')} |"
                    )
        lines += ["", "---", ""]

    lines += ["## Per-Page Metadata", ""]

    for r in meta_results:
        url = r["url"]
        label = url.replace(base_url, "") or "/"
        lines += [f"### `{label}`", ""]

        if r.get("error"):
            lines += [f"FAIL — Fetch error: {r['error']}", ""]
            continue

        if r.get("noindex"):
            lines.append("WARN: noindex detected — page excluded from search engines.\n")

        lines += ["| Field | Value | Status |", "|---|---|---|"]

        title = r.get("title", "")
        tlen = r.get("title_len", 0)
        if not title:
            tstatus = "FAIL: Missing"
        elif tlen < 30:
            tstatus = f"WARN: Too short ({tlen} chars)"
        elif tlen > 60:
            tstatus = f"WARN: Too long ({tlen} chars)"
        else:
            tstatus = f"PASS: {tlen} chars"
        safe_title = title[:80].replace("|", "/") if title else "-"
        lines.append(f"| Title | {safe_title} | {tstatus} |")

        desc = r.get("description")
        dlen = r.get("desc_len")
        if desc is None:
            dstatus = "FAIL: Missing"
        elif dlen < 120:
            dstatus = f"WARN: Too short ({dlen} chars)"
        elif dlen > 160:
            dstatus = f"WARN: Too long ({dlen} chars)"
        else:
            dstatus = f"PASS: {dlen} chars"
        safe_desc = (desc[:80] + "...").replace("|", "/") if desc else "-"
        lines.append(f"| Meta description | {safe_desc} | {dstatus} |")

        canon = r.get("canonical")
        lines.append(f"| Canonical | {canon or '-'} | {'PASS' if canon else 'WARN: Missing'} |")

        h1s = r.get("h1s", [])
        h1_count = r.get("h1_count", 0)
        h1_preview = " / ".join(h1s[:2])[:80].replace("|", "/") if h1s else "-"
        if h1_count == 0:
            h1status = "FAIL: Missing"
        elif h1_count > 1:
            h1status = f"WARN: {h1_count} H1s"
        else:
            h1status = "PASS"
        lines.append(f"| H1 | {h1_preview} | {h1status} |")

        jt = r.get("jsonld_types", [])
        lines.append(f"| JSON-LD | {', '.join(jt) if jt else '-'} | {'PASS' if jt else 'WARN: None'} |")

        og_title = r.get("og_title")
        og_desc = r.get("og_description")
        og_img = r.get("og_image")
        og_present = [t for t, v in [("title", og_title), ("description", og_desc), ("image", og_img)] if v]
        og_missing = [t for t, v in [("title", og_title), ("description", og_desc), ("image", og_img)] if not v]
        og_ok = not og_missing
        og_status = "PASS" if og_ok else ("WARN: missing " + ", ".join(og_missing))
        lines.append(f"| Open Graph | {', '.join(og_present) if og_present else '-'} | {og_status} |")

        lines.append("")

    lines += ["---", "", "## Issues Summary", ""]

    blocking = []
    warnings = []

    if robots.get("error"):
        blocking.append(f"robots.txt unreachable: {robots['error']}")
    if robots.get("disallow_all"):
        blocking.append("robots.txt has `Disallow: /` — entire site blocked from crawlers")
    if sitemap.get("error"):
        warnings.append(f"sitemap.xml error: {sitemap['error']}")
    if not robots.get("sitemap_url"):
        warnings.append("Sitemap URL not declared in robots.txt")

    for r in meta_results:
        if r.get("error"):
            blocking.append(f"`{r['url']}` — fetch failed: {r['error']}")
            continue
        label = r["url"].replace(base_url, "") or "/"
        if r.get("noindex"):
            blocking.append(f"`{label}` — noindex tag; page excluded from search")
        if not r.get("title"):
            blocking.append(f"`{label}` — missing title tag")
        if r.get("description") is None:
            blocking.append(f"`{label}` — missing meta description")
        if r.get("h1_count", 0) == 0:
            blocking.append(f"`{label}` — no H1 tag")
        if r.get("title_len", 0) > 60:
            warnings.append(f"`{label}` — title too long ({r['title_len']} chars; target <=60)")
        if 0 < r.get("title_len", 0) < 30:
            warnings.append(f"`{label}` — title too short ({r['title_len']} chars; target >=30)")
        if r.get("desc_len") is not None and r["desc_len"] > 160:
            warnings.append(f"`{label}` — meta description too long ({r['desc_len']} chars)")
        if r.get("desc_len") is not None and r["desc_len"] < 120:
            warnings.append(f"`{label}` — meta description too short ({r['desc_len']} chars)")
        if not r.get("canonical"):
            warnings.append(f"`{label}` — no canonical tag")
        if r.get("h1_count", 0) > 1:
            warnings.append(f"`{label}` — {r['h1_count']} H1 tags (should be 1)")
        if not r.get("jsonld_types"):
            warnings.append(f"`{label}` — no JSON-LD structured data")
        og_missing = [t for t, v in [("og:title", r.get("og_title")), ("og:description", r.get("og_description")), ("og:image", r.get("og_image"))] if not v]
        if og_missing:
            warnings.append(f"`{label}` — Open Graph missing: {', '.join(og_missing)}")

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

    lines += ["---", "", f"*Generated by Bain Studio SEO Audit · {today}*", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Bain Studio SEO Audit")
    parser.add_argument("base_url", nargs="?", help="Base URL e.g. https://example.com")
    parser.add_argument("--pages", help="Comma-separated paths e.g. /,/about/,/contact/")
    parser.add_argument("--output", help="Save report to this file path")
    parser.add_argument("--api-key", help="Google API key for PSI (optional)")
    parser.add_argument("--no-psi", action="store_true", help="Skip PageSpeed Insights")
    args = parser.parse_args()

    if not args.base_url:
        parser.print_help()
        sys.exit(0)

    base_url = args.base_url.rstrip("/")
    paths = [p.strip() for p in args.pages.split(",")] if args.pages else ["/"]
    pages = [base_url + (p if p.startswith("/") else "/" + p) for p in paths]

    status(f"Auditing {base_url} — {len(pages)} page(s)")

    robots = check_robots(base_url)
    sitemap = check_sitemap(robots.get("sitemap_url"), base_url)

    meta_results = [check_page_meta(url) for url in pages]

    psi_results = {}
    if not args.no_psi:
        status("Running PageSpeed Insights (2-5 min for 5 pages)...")
        for url in pages:
            psi_results[url] = {}
            for strategy in ("mobile", "desktop"):
                data, error = call_psi(url, strategy, api_key=args.api_key)
                if error:
                    err(f"PSI error ({strategy}): {error}")
                    psi_results[url][strategy] = {}
                else:
                    psi_results[url][strategy] = extract_psi_scores(data)
                time.sleep(3)
    else:
        status("Skipping PSI (--no-psi)")

    status("Rendering report...")
    report = render_report(base_url, pages, robots, sitemap, meta_results, psi_results)

    if args.output:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w") as f:
            f.write(report)
        err(f"Report saved to {args.output}")

    print(report)


if __name__ == "__main__":
    main()
