#!/usr/bin/env python3
"""Review gate for a wordpress.org theme review: is it FULL or PARTIAL, and may it post?

Reads a review's notes, the theme zip, the Trac comment, the evidence folder and the
review project's Asana mirror, prints one PASS/FAIL row per check like a unit-test
run, and ends on FULL or PARTIAL.

Usage:
    review-gate.py <notes.md> [--zip FILE] [--comment FILE] [--evidence DIR]
                   [--project DIR] [--mirror FILE]
                   [--handover-json FILE] [--handover PAGE.html]

<notes.md> is `<reports>/<slug>-<version>.md`; the slug and version come from its
name. Defaults, all overridable:

    --zip       <project>/review-zips/<slug>.<version>.zip
    --comment   <reports>/<slug>-<version>-trac-comment.txt
    --evidence  <reports>/evidence/
    --mirror    <project>/asana-mirror.md
    --project   the current directory (the DDEV review install), as for theme-sweep

Two questions, kept apart:

- **Review type.** FULL only when every check in the five-point definition passes
  (ledger, functions and hooks, requirements read at review time, tiers 2 and 3,
  notes complete with Not done empty). Anything else is PARTIAL, and the failing
  rows are its gaps.
- **Ready to post.** The notes' header and the comment both claim the type the gate
  found, and the sign-off and posting task exists. A partial review that says it is
  partial is postable; a review that calls itself full when it is not, is not.

Exit status: 0 ready to post (FULL or PARTIAL), 1 not ready, 2 could not run.

Every check is an exact match against keys the review template prescribes: a
handbook section by its number, an accessibility guideline by its URL slug, a ledger
row by file path. A page that cannot be fetched is a FAIL row, never a skipped one:
a gate that passes what it could not check is worse than no gate.

`--handover-json` writes the handover page's JSON fragment built from these results
(review type, review note, the definition group, the gate group). `--handover`
writes the same fragment into an existing handover page's `handover-data` block,
replacing those keys and leaving everything else on the page alone.
"""
import argparse
import fnmatch
import html
import json
import re
import sys
import urllib.request
import zipfile
from datetime import date
from pathlib import Path, PurePosixPath

HANDBOOK_URL = "https://make.wordpress.org/themes/handbook/review/required/"
GUIDELINES_URL = "https://wpaccessibility.org/docs/topics/theme-guidelines/"
USER_AGENT = "theme-review-gate/1.0"

# Notes sections the template prescribes, in order. Matched on the start of an `## `
# heading, so "## Handbook required, by section" satisfies "Handbook required".
SECTIONS = [
    "Verdict",
    "Handbook required",
    "Tags",
    "Functions and hooks",
    "File ledger",
    "Other checks",
    "Not done",
    "Outcome",
]
GUIDELINES_SECTION = "Accessibility guidelines"  # accessibility-ready themes only

# Evidence contract. Every file is <evidence>/<slug>-<version>-<name>.json, so one
# folder holds several versions without one standing in for another. The tier 2 names
# are this gate's; the scripts that write them are to follow (see the docs page).
TIER2 = {
    "main-landmark": "<main> in every template",
    "local-fonts": "font sources local",
    "msgfmt": "msgfmt on every catalogue",
    "images": "image dimensions and metadata",
    "block-delimiters": "wp: block delimiters balanced",
    "print-stylesheet": "@media print, when the readme claims one",
}
CDP = "cdp"                    # cdp/cdp_check.py --long-title --json
SITE_EDITOR = "site-editor"    # Site Editor block validation, block themes only
PHONE = 390
DESKTOP_MIN = 1280

# "Nothing." alone, or followed by a new sentence about an optional step not run.
# "None of the tier 3 checks were run." is not empty.
NOTHING = re.compile(r"^\s*(nothing|none)\s*(?:\.|$)", re.I)


# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------

class Row:
    def __init__(self, group, name, ok, detail=""):
        self.group, self.name, self.ok, self.detail = group, name, ok, detail

    def line(self):
        return "%s  %-11s %s%s" % ("PASS" if self.ok else "FAIL", self.group, self.name,
                                   " - " + self.detail if self.detail else "")


# Groups that decide the review type, mapped to the five-point definition.
DEFINITION = [
    ("files", "Every file read line by line in this version"),
    ("functions", "Every function and hook has a verdict"),
    ("requirements", "Requirements read at review time"),
    ("tiers", "Tiers 2 and 3 results present (tier 1 is the sweep, not checked)"),
    ("notes", "Notes complete, Not done empty"),
]
POSTING = ("claims", "posting")


# --------------------------------------------------------------------------
# Notes parsing
# --------------------------------------------------------------------------

def sections(text):
    """{heading: body} for every `## ` heading. The body runs to the next `## `."""
    out, name, buf = {}, None, []
    in_fence = False
    for line in text.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("## "):
            if name is not None:
                out[name] = "\n".join(buf).strip()
            name, buf = line[3:].strip(), []
        elif name is not None:
            buf.append(line)
    if name is not None:
        out[name] = "\n".join(buf).strip()
    return out


def find_section(secs, prefix):
    for name, body in secs.items():
        if name.lower().startswith(prefix.lower()):
            return name, body
    return None, None


def header_block(text):
    """Everything before the first `## ` heading."""
    return text.split("\n## ", 1)[0]


def split_row(line):
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def tables(body):
    """Every markdown table in body, as (header cells, [row cells])."""
    found, cur = [], None
    for line in (body or "").splitlines():
        s = line.strip()
        if s.startswith("|"):
            cells = split_row(s)
            if cur is None:
                cur = (cells, [])
            elif all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            else:
                cur[1].append(cells)
        elif cur is not None:
            found.append(cur)
            cur = None
    if cur is not None:
        found.append(cur)
    return found


def table_with(body, header):
    want = [h.lower() for h in header]
    for head, rows in tables(body):
        if [h.lower() for h in head] == want:
            return rows
    return None


def strip_md(s):
    # Backticks and bold only: a single `*` is a glob in a ledger cell.
    return s.replace("`", "").replace("**", "").strip()


def claim(text):
    """'full', 'partial', 'both' or None, from 'full review' / 'partial review'."""
    t = text.lower()
    full = re.search(r"\bfull review\b", t) is not None
    part = re.search(r"\bpartial review\b", t) is not None
    if full and part:
        return "both"
    return "full" if full else "partial" if part else None


# --------------------------------------------------------------------------
# Zip
# --------------------------------------------------------------------------

def zip_files(zip_path):
    """{relative path: bytes} for every file in the zip, the top folder removed."""
    out = {}
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            parts = PurePosixPath(info.filename).parts
            rel = "/".join(parts[1:]) if len(parts) > 1 else parts[0]
            out[rel] = z.read(info)
    return out


def style_header(files):
    css = files.get("style.css", b"").decode("utf-8", "replace")
    m = re.search(r"/\*(.*?)\*/", css, re.S)
    head = {}
    for line in (m.group(1) if m else "").splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            head[k.strip().lower()] = v.strip()
    return head


def is_accessibility_ready(header):
    return "accessibility-ready" in [t.strip().lower() for t in header.get("tags", "").split(",")]


def is_block_theme(files):
    return "templates/index.html" in files


FUNC_RE = re.compile(r"^\s*(?:(?:public|private|protected|static|final|abstract)\s+)*"
                     r"function\s+&?\s*([A-Za-z_]\w*)\s*\(", re.M)
HOOK_RE = re.compile(r"\badd_(?:action|filter)\s*\(\s*['\"]([^'\"]+)['\"]")


def functions_and_hooks(files):
    funcs, hooks = set(), set()
    for rel, data in files.items():
        if not rel.endswith(".php"):
            continue
        src = data.decode("utf-8", "replace")
        funcs.update(FUNC_RE.findall(src))
        hooks.update(HOOK_RE.findall(src))
    return sorted(funcs), sorted(hooks)


# --------------------------------------------------------------------------
# Ledger
# --------------------------------------------------------------------------

COUNT_RE = re.compile(r"\s*\((\d+)\)\s*$")


def expand_cell(cell, paths):
    """Resolve a ledger File cell to the zip paths it names.

    A cell is one path, a comma list (later items inherit the first item's folder
    when they have none of their own), or a glob with its count in brackets:
    `assets/fonts/*.woff2 (8)`. Returns (matched paths, problems)."""
    problems, matched = [], []
    base = ""
    for i, item in enumerate(strip_md(cell).split(",")):
        item = item.strip()
        if not item:
            continue
        count = None
        m = COUNT_RE.search(item)
        if m:
            count, item = int(m.group(1)), item[:m.start()].strip()
        if i == 0:
            base = item.rsplit("/", 1)[0] + "/" if "/" in item else ""
        elif "/" not in item:
            item = base + item
        if any(ch in item for ch in "*?["):
            hits = sorted(p for p in paths if fnmatch.fnmatchcase(p, item))
            if count is None:
                problems.append("glob `%s` has no (count)" % item)
            elif count != len(hits):
                problems.append("glob `%s` says %d, zip has %d" % (item, count, len(hits)))
            if not hits:
                problems.append("glob `%s` matches nothing in the zip" % item)
            matched += hits
        elif item in paths:
            matched.append(item)
        else:
            problems.append("`%s` is not in the zip" % item)
    return matched, problems


def check_ledger(notes_secs, files):
    rows = []
    _, body = find_section(notes_secs, "File ledger")
    table = table_with(body, ["File", "Lines", "Verdict"]) if body else None
    if table is None:
        rows.append(Row("files", "ledger table", False,
                        "no `## File ledger` with a File | Lines | Verdict table"))
        return rows
    paths = set(files)
    covered, bad = set(), []
    for cells in table:
        if len(cells) < 3:
            bad.append("short row: %s" % " | ".join(cells))
            continue
        hit, problems = expand_cell(cells[0], paths)
        if not cells[1]:
            problems.append("no line ranges")
        if not cells[2]:
            problems.append("no verdict")
        if problems:
            bad.append("%s: %s" % (strip_md(cells[0]), "; ".join(problems)))
        else:
            covered.update(hit)
    missing = sorted(paths - covered)
    rows.append(Row("files", "every zip file has a ledger row", not missing,
                    "%d of %d covered%s" % (len(paths) - len(missing), len(paths),
                                            "; missing: " + ", ".join(missing[:12]) +
                                            (" ..." if len(missing) > 12 else "")
                                            if missing else "")))
    rows.append(Row("files", "every ledger row has lines and a verdict", not bad,
                    "; ".join(bad[:6]) + (" ..." if len(bad) > 6 else "")))
    return rows


# --------------------------------------------------------------------------
# Functions and hooks
# --------------------------------------------------------------------------

def check_functions(notes_secs, files):
    funcs, hooks = functions_and_hooks(files)
    _, body = find_section(notes_secs, "Functions and hooks")
    table = table_with(body, ["Name", "Verdict"]) if body else None
    if table is None:
        return [Row("functions", "inventory table", False,
                    "no `## Functions and hooks` with a Name | Verdict table")]
    names = " ".join(strip_md(c[0]) for c in table if len(c) >= 2 and c[1])

    def has(word):
        return re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(word), names) is not None

    rows = []
    for kind, items in (("function", funcs), ("hook", hooks)):
        missing = [w for w in items if not has(w)]
        rows.append(Row("functions", "every %s has a verdict" % kind, not missing,
                        "%d of %d%s" % (len(items) - len(missing), len(items),
                                        "; missing: " + ", ".join(missing) if missing else "")))
    return rows


# --------------------------------------------------------------------------
# Requirements, read at review time
# --------------------------------------------------------------------------

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def handbook_sections(page):
    """{number: title} from the handbook page's `<h3>N. Title</h3>` headings."""
    out = {}
    for m in re.finditer(r"<h3[^>]*>(.*?)</h3>", page, re.S):
        t = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
        n = re.match(r"(\d+)\.\s*(.+)", t)
        if n:
            out[int(n.group(1))] = n.group(2).strip()
    return out


def guideline_slugs(page):
    path = re.escape("/docs/topics/theme-guidelines/")
    return sorted(set(re.findall(r'href="[^"]*%s([a-z0-9-]+)/?"' % path, page)))


def dated(body, url):
    return url.rstrip("/") in (body or "") and re.search(r"\b\d{4}-\d{2}-\d{2}\b", body or "")


def check_handbook(notes_secs, get):
    rows = []
    try:
        wanted = handbook_sections(get(HANDBOOK_URL))
    except Exception as e:  # any failure to read the page is a failing row
        return [Row("requirements", "handbook page fetched", False, "%s: %s" % (HANDBOOK_URL, e))]
    if not wanted:
        return [Row("requirements", "handbook page fetched", False,
                    "no numbered sections found on %s" % HANDBOOK_URL)]
    rows.append(Row("requirements", "handbook page fetched", True,
                    "%d sections, %s" % (len(wanted), date.today().isoformat())))
    _, body = find_section(notes_secs, "Handbook required")
    table = table_with(body, ["§", "Verdict"]) if body else None
    if table is None:
        rows.append(Row("requirements", "handbook verdict table", False,
                        "no `## Handbook required` with a § | Verdict table"))
        return rows
    rows.append(Row("requirements", "handbook page cited with its read date", bool(dated(body, HANDBOOK_URL)),
                    "" if dated(body, HANDBOOK_URL) else "the section must name %s and the date it was read" % HANDBOOK_URL))
    got = {}
    for cells in table:
        m = re.match(r"(\d+)\b", strip_md(cells[0]))
        if m and len(cells) >= 2 and cells[1]:
            got[int(m.group(1))] = cells[1]
    missing = ["%d %s" % (n, wanted[n]) for n in sorted(wanted) if n not in got]
    rows.append(Row("requirements", "every handbook section has a verdict", not missing,
                    "%d of %d%s" % (len(wanted) - len(missing), len(wanted),
                                    "; missing: " + ", ".join(missing) if missing else "")))
    return rows


def check_guidelines(notes_secs, get):
    try:
        slugs = guideline_slugs(get(GUIDELINES_URL))
    except Exception as e:
        return [Row("requirements", "guideline index fetched", False, "%s: %s" % (GUIDELINES_URL, e))]
    if not slugs:
        return [Row("requirements", "guideline index fetched", False,
                    "no guideline pages linked from %s" % GUIDELINES_URL)]
    rows = [Row("requirements", "guideline index fetched", True, "%d guidelines" % len(slugs))]
    _, body = find_section(notes_secs, GUIDELINES_SECTION)
    table = table_with(body, ["Guideline", "Verdict"]) if body else None
    if table is None:
        rows.append(Row("requirements", "guideline verdict table", False,
                        "accessibility-ready: no `## %s` with a Guideline | Verdict table" % GUIDELINES_SECTION))
        return rows
    rows.append(Row("requirements", "guideline index cited with its read date", bool(dated(body, GUIDELINES_URL)),
                    "" if dated(body, GUIDELINES_URL) else "the section must name %s and the date it was read" % GUIDELINES_URL))
    got = set()
    for cells in table:
        if len(cells) < 2 or not cells[1]:
            continue
        key = strip_md(cells[0]).rstrip("/").rsplit("/", 1)[-1]
        got.add(key)
    missing = [s for s in slugs if s not in got]
    rows.append(Row("requirements", "every guideline has a verdict, keyed by slug", not missing,
                    "%d of %d%s" % (len(slugs) - len(missing), len(slugs),
                                    "; missing: " + ", ".join(missing) if missing else "")))
    return rows


# --------------------------------------------------------------------------
# Evidence
# --------------------------------------------------------------------------

def load_json(path):
    try:
        return json.loads(path.read_text()), None
    except FileNotFoundError:
        return None, "missing %s" % path.name
    except ValueError as e:
        return None, "%s is not JSON (%s)" % (path.name, e)


def check_tier2(evidence, stem):
    rows = []
    for name, label in TIER2.items():
        data, err = load_json(evidence / ("%s-%s.json" % (stem, name)))
        rows.append(Row("tiers", "tier 2: %s" % label, data is not None, err or ""))
    return rows


def check_tier3(evidence, stem, block):
    rows = []
    rec, err = load_json(evidence / ("%s-%s.json" % (stem, CDP)))
    if rec is None:
        rows.append(Row("tiers", "tier 3: cdp_check result", False, err))
    else:
        pages = rec.get("pages") or []
        widths = {p.get("width") for p in pages if p.get("status") != "abort"}
        phone = PHONE in widths
        desk = any(isinstance(w, int) and w >= DESKTOP_MIN for w in widths)
        kbd = {p.get("width") for p in pages if p.get("keyboard") and p.get("status") != "abort"}
        rows.append(Row("tiers", "tier 3: running site at %d and desktop" % PHONE, phone and desk,
                        "widths measured: %s" % sorted(w for w in widths if w is not None)))
        rows.append(Row("tiers", "tier 3: keyboard pass at both widths",
                        PHONE in kbd and any(isinstance(w, int) and w >= DESKTOP_MIN for w in kbd),
                        "keyboard at: %s" % sorted(w for w in kbd if w is not None)))
        long_ok = bool(rec.get("long_title")) and any(p.get("title") == "long" for p in pages)
        rows.append(Row("tiers", "tier 3: long site title", long_ok,
                        "" if long_ok else "run cdp_check with --long-title"))
        rows.append(Row("tiers", "tier 3: no aborted page", not rec.get("aborted"),
                        "%s aborted" % rec.get("aborted") if rec.get("aborted") else ""))
    shots = {int(m.group(1)) for p in evidence.glob("%s-*.png" % stem)
             for m in [re.search(r"-(\d{3,4})\.png$", p.name)] if m}
    ok = PHONE in shots and any(w >= DESKTOP_MIN for w in shots)
    rows.append(Row("tiers", "tier 3: screenshots at %d and desktop" % PHONE, ok,
                    "widths: %s" % sorted(shots) if shots else "no %s-*-<width>.png" % stem))
    if block:
        data, err = load_json(evidence / ("%s-%s.json" % (stem, SITE_EDITOR)))
        rows.append(Row("tiers", "tier 3: Site Editor block validation", data is not None, err or ""))
    return rows


# --------------------------------------------------------------------------
# Notes and claims
# --------------------------------------------------------------------------

def check_notes(notes_secs, a11y):
    want = SECTIONS + ([GUIDELINES_SECTION] if a11y else [])
    missing = [s for s in want if find_section(notes_secs, s)[0] is None]
    rows = [Row("notes", "every template section present", not missing,
                "missing: " + ", ".join(missing) if missing else "")]
    _, body = find_section(notes_secs, "Not done")
    if body is None:
        rows.append(Row("notes", "Not done is empty", False, "no `## Not done` section"))
    else:
        ok = not body.strip() or NOTHING.match(body) is not None
        first = body.strip().splitlines()[0] if body.strip() else ""
        rows.append(Row("notes", "Not done is empty", ok, "" if ok else "lists: %s" % first[:120]))
    return rows


def check_claims(notes_text, comment_path, granted):
    rows = []
    head = claim(header_block(notes_text))
    rows.append(Row("claims", "notes header claims %s" % granted, head == granted,
                    "claims %s" % (head or "neither")))
    try:
        comment = comment_path.read_text()
    except FileNotFoundError:
        rows.append(Row("claims", "comment claims %s" % granted, False, "missing %s" % comment_path.name))
        return rows
    said = claim(comment)
    rows.append(Row("claims", "comment claims %s" % granted, said == granted,
                    "claims %s" % (said or "neither")))
    return rows


def check_posting(mirror, theme_name, version):
    try:
        text = mirror.read_text()
    except FileNotFoundError:
        return [Row("posting", "sign-off and posting task", False, "no mirror at %s" % mirror)]
    want = "%s: sign off the %s review" % (theme_name, version)
    hit = None
    for line in text.splitlines():
        if line.startswith("### ") and want.lower() in line.lower():
            hit = line[4:].split(" ", 1)[0]
            break
    return [Row("posting", "sign-off and posting task", hit is not None,
                hit or "no task titled '%s ...'" % want)]


# --------------------------------------------------------------------------
# Gate
# --------------------------------------------------------------------------

def run_gate(notes_path, zip_path, comment_path, evidence, mirror, get=fetch):
    notes_path = Path(notes_path)
    stem = notes_path.stem
    notes_text = notes_path.read_text()
    secs = sections(notes_text)
    files = zip_files(zip_path)
    header = style_header(files)
    a11y = is_accessibility_ready(header)
    block = is_block_theme(files)
    version = header.get("version") or stem.rsplit("-", 1)[-1]

    rows = []
    rows += check_ledger(secs, files)
    rows += check_functions(secs, files)
    rows += check_handbook(secs, get)
    if a11y:
        rows += check_guidelines(secs, get)
    rows += check_tier2(Path(evidence), stem)
    rows += check_tier3(Path(evidence), stem, block)
    rows += check_notes(secs, a11y)
    granted = "full" if all(r.ok for r in rows) else "partial"
    rows += check_claims(notes_text, Path(comment_path), granted)
    rows += check_posting(Path(mirror), header.get("theme name", ""), version)
    postable = all(r.ok for r in rows if r.group in POSTING)
    return {
        "theme": header.get("theme name", ""),
        "version": version,
        "shape": "block" if block else "classic",
        "accessibility_ready": a11y,
        "review": granted,
        "postable": postable,
        "rows": rows,
    }


def handover_fragment(result):
    def status(ok):
        return "pass" if ok else "fail"

    gaps = [r for r in result["rows"] if not r.ok and r.group not in POSTING]
    definition = []
    for group, label in DEFINITION:
        g = [r for r in result["rows"] if r.group == group]
        bad = [r for r in g if not r.ok]
        definition.append({"label": label, "status": status(not bad),
                           "note": "; ".join(r.name for r in bad)})
    if result["review"] == "full":
        note = "Review gate: all five points of the full-review definition pass."
    else:
        note = "Review gate: %d gap%s - %s." % (len(gaps), "" if len(gaps) == 1 else "s",
                                               "; ".join(r.name for r in gaps[:4]) +
                                               (" ..." if len(gaps) > 4 else ""))
    return {
        "review": result["review"],
        "review_note": note,
        "postable": result["postable"],
        "groups": [
            {"name": "Full-review definition", "items": definition},
            {"name": "Review gate (%s)" % date.today().isoformat(),
             "items": [{"label": r.name, "status": status(r.ok), "note": r.detail}
                       for r in result["rows"]]},
        ],
    }


HANDOVER_RE = re.compile(r'(<script type="application/json" id="handover-data">)(.*?)(</script>)', re.S)


def write_handover(page, fragment):
    text = page.read_text()
    m = HANDOVER_RE.search(text)
    if not m:
        raise ValueError("%s has no handover-data block" % page)
    data = json.loads(m.group(2))
    data["review"] = fragment["review"]  # "postable" is the gate's, not the page's
    data["review_note"] = fragment["review_note"]
    keep = [g for g in data.get("groups", [])
            if g.get("name") != "Full-review definition" and not g.get("name", "").startswith("Review gate")]
    for g in keep:
        for item in g.get("items", []):
            if item.get("label") == "Review gate run":
                item["status"] = "pass" if fragment["postable"] else "fail"
                item["note"] = "%s, ready to post: %s, %s" % (
                    fragment["review"].upper(), "yes" if fragment["postable"] else "no",
                    date.today().isoformat())
    data["groups"] = [fragment["groups"][0]] + keep + [fragment["groups"][1]]
    body = "\n" + json.dumps(data, indent=1, ensure_ascii=False) + "\n"
    page.write_text(text[:m.start(2)] + body + text[m.end(2):])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("notes", help="<reports>/<slug>-<version>.md")
    ap.add_argument("--project", default=".", help="DDEV review install (default: cwd)")
    ap.add_argument("--zip")
    ap.add_argument("--comment")
    ap.add_argument("--evidence")
    ap.add_argument("--mirror")
    ap.add_argument("--handover-json", help="write the handover JSON fragment here")
    ap.add_argument("--handover", help="update this handover page's data block in place")
    a = ap.parse_args(argv)

    notes = Path(a.notes)
    m = re.fullmatch(r"(.+)-(\d+(?:\.\d+)*)", notes.stem)
    if not notes.is_file() or not m:
        print("notes must be an existing <slug>-<version>.md: %s" % notes, file=sys.stderr)
        return 2
    slug, version = m.groups()
    project = Path(a.project)
    reports = notes.parent
    zip_path = Path(a.zip) if a.zip else project / "review-zips" / ("%s.%s.zip" % (slug, version))
    if not zip_path.is_file():
        print("no zip at %s (pass --zip, or run from the review install)" % zip_path, file=sys.stderr)
        return 2
    comment = Path(a.comment) if a.comment else reports / ("%s-trac-comment.txt" % notes.stem)
    evidence = Path(a.evidence) if a.evidence else reports / "evidence"
    mirror = Path(a.mirror) if a.mirror else project / "asana-mirror.md"

    result = run_gate(notes, zip_path, comment, evidence, mirror)
    print("review gate: %s %s (%s%s)" % (result["theme"], result["version"], result["shape"],
                                         ", accessibility-ready" if result["accessibility_ready"] else ""))
    for r in result["rows"]:
        print(r.line())
    gaps = sum(1 for r in result["rows"] if not r.ok and r.group not in POSTING)
    print()
    print("%s%s" % (result["review"].upper(), " (%d gap%s)" % (gaps, "" if gaps == 1 else "s") if gaps else ""))
    print("ready to post: %s" % ("yes" if result["postable"] else "no"))

    fragment = handover_fragment(result)
    if a.handover_json:
        Path(a.handover_json).write_text(json.dumps(fragment, indent=1, ensure_ascii=False) + "\n")
        print("handover json written to %s" % a.handover_json)
    if a.handover:
        write_handover(Path(a.handover), fragment)
        print("handover page updated: %s" % a.handover)
    return 0 if result["postable"] else 1


if __name__ == "__main__":
    sys.exit(main())
