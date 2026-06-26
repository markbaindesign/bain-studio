#!/usr/bin/env python3
"""
Bain Studio Performance Audit
Usage: python3 perf_audit.py <base_url> [--pages /,/path/] [--output report.md] [--api-key KEY] [--mobile-only] [--desktop-only]
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

UA = "Mozilla/5.0 (compatible; BainDesignPerfAudit/1.0)"
PSI_BASE = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

# Priority weights: impact on score × frequency of fix = rank
AUDIT_PRIORITY = {
    # P1 — direct LCP / score killers
    "render-blocking-resources":     1,
    "unused-javascript":             1,
    "unused-css-rules":              1,
    "largest-contentful-paint-element": 1,
    "lcp-lazy-loaded":               1,
    "efficient-animated-content":    1,
    # P2 — significant gains
    "uses-optimized-images":         2,
    "uses-webp-images":              2,
    "uses-responsive-images":        2,
    "offscreen-images":              2,
    "total-byte-weight":             2,
    "uses-text-compression":         2,
    "server-response-time":          2,
    "redirects":                     2,
    # P3 — good practice
    "uses-long-cache-ttl":           3,
    "dom-size":                      3,
    "critical-request-chains":       3,
    "third-party-summary":           3,
    "bootup-time":                   3,
    "mainthread-work-breakdown":     3,
    "font-display":                  3,
    # P4 — minor / informational
    "preload-lcp-image":             4,
    "uses-rel-preconnect":           4,
    "uses-rel-preload":              4,
    "resource-summary":              4,
}

CWV_KEYS = [
    ("first-contentful-paint",    "FCP"),
    ("largest-contentful-paint",  "LCP"),
    ("total-blocking-time",       "TBT"),
    ("cumulative-layout-shift",   "CLS"),
    ("speed-index",               "Speed Index"),
    ("interactive",               "TTI"),
]

# Thresholds for CWV rating
CWV_THRESHOLDS = {
    "first-contentful-paint":   (1800, 3000),   # good < 1.8s, poor > 3s
    "largest-contentful-paint": (2500, 4000),
    "total-blocking-time":      (200, 600),      # ms
    "cumulative-layout-shift":  (0.1, 0.25),
    "speed-index":              (3400, 5800),
    "interactive":              (3800, 7300),
}


def err(msg):
    print(f"  {msg}", file=sys.stderr)


def status(msg):
    print(f"-> {msg}", file=sys.stderr)


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace"), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:
        return None, str(e)


def call_psi(url, strategy, api_key=None):
    params = {
        "url": url,
        "strategy": strategy,
        "category": ["performance", "accessibility", "best-practices", "seo"],
    }
    qs = urllib.parse.urlencode(params, doseq=True)
    if api_key:
        qs += f"&key={urllib.parse.quote(api_key)}"
    full_url = f"{PSI_BASE}?{qs}"
    status(f"PSI {strategy} -> {url}")
    raw, error = fetch(full_url)
    if error or not raw:
        return None, error
    try:
        return json.loads(raw), None
    except json.JSONDecodeError as e:
        return None, f"JSON error: {e}"


def cwv_rating(key, numeric_value):
    thresholds = CWV_THRESHOLDS.get(key)
    if thresholds is None or numeric_value is None:
        return ""
    good, poor = thresholds
    if numeric_value <= good:
        return "GOOD"
    if numeric_value <= poor:
        return "NEEDS IMPROVEMENT"
    return "POOR"


def extract_results(data):
    if not data:
        return {}

    lr = data.get("lighthouseResult", {})
    cats = lr.get("categories", {})
    audits = lr.get("audits", {})

    # Category scores
    scores = {}
    for k, v in cats.items():
        s = v.get("score")
        scores[k] = round(s * 100) if s is not None else None

    # Core Web Vitals
    cwv = []
    for audit_key, label in CWV_KEYS:
        audit = audits.get(audit_key, {})
        display = audit.get("displayValue", "-")
        numeric = audit.get("numericValue")
        score = audit.get("score")
        rating = cwv_rating(audit_key, numeric)
        if score is not None:
            if score >= 0.9:
                rating = "GOOD"
            elif score >= 0.5:
                rating = "NEEDS IMPROVEMENT"
            else:
                rating = "POOR"
        cwv.append({"key": audit_key, "label": label, "display": display, "rating": rating})

    # Opportunities and diagnostics — flatten into a prioritised list
    opportunities = []
    for audit_key, audit in audits.items():
        if audit.get("score") in (None, 1):
            continue  # passed or not applicable
        score = audit.get("score", 1)
        if score >= 0.9:
            continue
        display = audit.get("displayValue", "")
        title = audit.get("title", audit_key)
        description = audit.get("description", "")
        # Extract estimated savings if present
        savings_ms = None
        savings_bytes = None
        details = audit.get("details", {})
        if details.get("type") == "opportunity":
            savings_ms = details.get("overallSavingsMs")
            savings_bytes = details.get("overallSavingsBytes")

        priority = AUDIT_PRIORITY.get(audit_key, 3)
        # Boost priority for audits with large savings
        if savings_ms and savings_ms > 1000:
            priority = max(1, priority - 1)
        elif savings_ms and savings_ms > 500:
            priority = max(1, priority - 1) if priority > 2 else priority

        opportunities.append({
            "key": audit_key,
            "title": title,
            "display": display,
            "score": score,
            "priority": priority,
            "savings_ms": savings_ms,
            "savings_bytes": savings_bytes,
            "description": description[:200] if description else "",
        })

    # Sort: priority asc, then score asc (worst first within same priority)
    opportunities.sort(key=lambda x: (x["priority"], x["score"]))

    return {
        "scores": scores,
        "cwv": cwv,
        "opportunities": opportunities,
    }


def score_label(score):
    if score is None:
        return "-"
    if score >= 90:
        return f"{score} PASS"
    if score >= 50:
        return f"{score} WARN"
    return f"{score} FAIL"


def savings_label(opp):
    parts = []
    if opp.get("savings_ms") and opp["savings_ms"] > 50:
        parts.append(f"~{opp['savings_ms'] / 1000:.1f}s")
    if opp.get("savings_bytes") and opp["savings_bytes"] > 1024:
        kb = opp["savings_bytes"] / 1024
        parts.append(f"~{kb:.0f} KB")
    return " / ".join(parts) if parts else ""


def render_report(base_url, pages, results_by_url):
    lines = []
    today = date.today().isoformat()

    lines += [
        f"# Performance Audit — {base_url}",
        f"**Date:** {today}  ",
        f"**Pages audited:** {len(pages)}  ",
        "",
        "---",
        "",
    ]

    # --- Summary scores table ---
    lines += [
        "## Scores",
        "",
        "| Page | Device | Perf | A11y | Best Practices | SEO |",
        "|---|---|---|---|---|---|",
    ]
    for url in pages:
        label = url.replace(base_url, "") or "/"
        for strategy in ("mobile", "desktop"):
            r = results_by_url.get(url, {}).get(strategy)
            if not r:
                lines.append(f"| `{label}` | {strategy} | - | - | - | - |")
                continue
            s = r["scores"]
            lines.append(
                f"| `{label}` | {strategy} "
                f"| {score_label(s.get('performance'))} "
                f"| {score_label(s.get('accessibility'))} "
                f"| {score_label(s.get('best-practices'))} "
                f"| {score_label(s.get('seo'))} |"
            )

    lines += ["", "---", ""]

    # --- Core Web Vitals per page ---
    lines += ["## Core Web Vitals", ""]
    for url in pages:
        label = url.replace(base_url, "") or "/"
        lines += [f"### `{label}`", ""]
        for strategy in ("mobile", "desktop"):
            r = results_by_url.get(url, {}).get(strategy)
            if not r:
                continue
            lines += [
                f"**{strategy.capitalize()}**",
                "",
                "| Metric | Value | Rating |",
                "|---|---|---|",
            ]
            for cwv in r["cwv"]:
                lines.append(f"| {cwv['label']} | {cwv['display']} | {cwv['rating']} |")
            lines.append("")

    lines += ["---", ""]

    # --- Prioritised fix list ---
    # Aggregate opportunities across all pages+strategies, deduplicate by key,
    # keep worst instance per key
    all_opps = {}
    for url in pages:
        label = url.replace(base_url, "") or "/"
        for strategy in ("mobile", "desktop"):
            r = results_by_url.get(url, {}).get(strategy)
            if not r:
                continue
            for opp in r["opportunities"]:
                key = opp["key"]
                existing = all_opps.get(key)
                if not existing or opp["score"] < existing["score"]:
                    all_opps[key] = dict(opp, pages=[f"`{label}` ({strategy})"])
                elif existing:
                    existing["pages"].append(f"`{label}` ({strategy})")

    sorted_opps = sorted(all_opps.values(), key=lambda x: (x["priority"], x["score"]))

    lines += [
        "## Prioritised Fixes",
        "",
        "Ordered by impact. P1 = fix immediately, P4 = nice to have.",
        "",
    ]

    current_p = None
    for opp in sorted_opps:
        p = opp["priority"]
        if p != current_p:
            labels = {1: "P1 — Critical", 2: "P2 — High Impact", 3: "P3 — Medium", 4: "P4 — Low"}
            lines += ["", f"### {labels.get(p, f'P{p}')}", ""]
            current_p = p

        saving = savings_label(opp)
        saving_str = f" *(saves {saving})*" if saving else ""
        pages_str = ", ".join(opp["pages"][:3])
        if len(opp["pages"]) > 3:
            pages_str += f" +{len(opp['pages']) - 3} more"

        lines += [
            f"**{opp['title']}**{saving_str}  ",
            f"Pages: {pages_str}  ",
        ]
        if opp["description"]:
            lines.append(f"{opp['description']}  ")
        lines.append("")

    if not sorted_opps:
        lines += ["No issues found — all audits passed.", ""]

    lines += ["---", ""]

    # --- Per-page detail ---
    lines += ["## Per-Page Detail", ""]
    for url in pages:
        label = url.replace(base_url, "") or "/"
        lines += [f"### `{label}`", ""]
        for strategy in ("mobile", "desktop"):
            r = results_by_url.get(url, {}).get(strategy)
            if not r:
                lines += [f"**{strategy.capitalize()}** — no data", ""]
                continue
            opps = r["opportunities"]
            lines += [f"**{strategy.capitalize()}** — {len(opps)} issue(s)", ""]
            if opps:
                lines += ["| Priority | Issue | Saving |", "|---|---|---|"]
                for opp in opps[:10]:
                    lines.append(
                        f"| P{opp['priority']} | {opp['title']} | {savings_label(opp) or '-'} |"
                    )
                lines.append("")

    lines += [
        "---",
        "",
        f"*Generated by Bain Studio Performance Audit · {today}*",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Bain Studio Performance Audit")
    parser.add_argument("base_url", nargs="?", help="Base URL e.g. https://example.com")
    parser.add_argument("--pages", help="Comma-separated paths e.g. /,/about/,/services/")
    parser.add_argument("--output", help="Save report to this file path")
    parser.add_argument("--api-key", help="Google API key for PSI")
    parser.add_argument("--mobile-only", action="store_true")
    parser.add_argument("--desktop-only", action="store_true")
    args = parser.parse_args()

    if not args.base_url:
        parser.print_help()
        sys.exit(0)

    base_url = args.base_url.rstrip("/")
    paths = [p.strip() for p in args.pages.split(",")] if args.pages else ["/"]
    pages = [base_url + (p if p.startswith("/") else "/" + p) for p in paths]

    if args.mobile_only:
        strategies = ["mobile"]
    elif args.desktop_only:
        strategies = ["desktop"]
    else:
        strategies = ["mobile", "desktop"]

    status(f"Auditing {base_url} — {len(pages)} page(s), {strategies}")

    results_by_url = {}
    for url in pages:
        results_by_url[url] = {}
        for strategy in strategies:
            data, error = call_psi(url, strategy, api_key=args.api_key)
            if error:
                err(f"PSI error ({strategy}): {error}")
                results_by_url[url][strategy] = None
            else:
                results_by_url[url][strategy] = extract_results(data)
            if len(pages) * len(strategies) > 1:
                time.sleep(3)

    status("Rendering report...")
    report = render_report(base_url, pages, results_by_url)

    if args.output:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w") as f:
            f.write(report)
        err(f"Report saved to {args.output}")

    print(report)


if __name__ == "__main__":
    main()
