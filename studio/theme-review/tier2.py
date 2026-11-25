#!/usr/bin/env python3
"""Tier 2 of a wordpress.org theme review: the scripted structural checks.

Runs the six checks the review template's tier 2 names against the submitted zip
and writes one result per check where the review gate reads them:

    <evidence>/<slug>-<version>-<check>.json

    main-landmark     a <main> in every block template (parts and patterns expanded)
    local-fonts       every font source ships with the theme
    msgfmt            `msgfmt --check` on every .po, magic number on every .mo
    images            dimensions and metadata of every image, screenshot size
    block-delimiters  `wp:` comment delimiters balance in every template, part, pattern
    print-stylesheet  `@media print` present, when the readme claims a print stylesheet

Usage:
    tier2.py <notes.md> [--zip FILE] [--evidence DIR] [--project DIR]

Same defaults as review-gate.py: the zip is <project>/review-zips/<slug>.<version>.zip,
the evidence folder <reports>/evidence/, the project the current directory.

It records facts, not verdicts. Each file says what was checked, whether the check
applies, whether it passed, and the findings. Whether a finding is a required item
stays with the reviewer, so the gate counts a check as done when its file exists,
whatever it found. A check that does not apply (no block markup in a classic theme,
no print claim in the readme) is still written, with "applicable": false.

Stdlib only, plus `msgfmt` from gettext when the theme ships a .po file.
"""
import argparse
import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from datetime import date
from pathlib import Path, PurePosixPath

TOOL = "tier2.py"
CHECKS = ("main-landmark", "local-fonts", "msgfmt", "images", "block-delimiters",
          "print-stylesheet")
BLOCK_DIRS = ("templates/", "parts/", "patterns/")
SCREENSHOT_MAX = (1200, 900)


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


def text(data):
    return data.decode("utf-8", "replace")


def result(check, applicable, ok, checked, findings, note=""):
    return {"check": check, "tool": TOOL, "date": date.today().isoformat(),
            "applicable": applicable, "pass": ok if applicable else None,
            "checked": checked, "findings": findings, "note": note}


def block_markup_files(files):
    return sorted(p for p in files
                  if p.startswith(BLOCK_DIRS) and p.endswith((".html", ".php")))


# --------------------------------------------------------------------------
# block-delimiters
# --------------------------------------------------------------------------

DELIM_RE = re.compile(r"<!--\s*(/)?wp:([a-z][a-z0-9_-]*(?:/[a-z][a-z0-9_-]*)?)(\s+\{.*?\})?\s*(/)?-->", re.S)


def delimiter_problems(markup):
    """Unbalanced `wp:` comments in one file, as readable strings. [] when balanced."""
    stack, problems = [], []
    for m in DELIM_RE.finditer(markup):
        closing, name, self_closing = m.group(1), m.group(2), m.group(4)
        line = markup.count("\n", 0, m.start()) + 1
        if self_closing:
            continue
        if not closing:
            stack.append((name, line))
        elif not stack:
            problems.append("line %d: closing wp:%s with nothing open" % (line, name))
        elif stack[-1][0] != name:
            problems.append("line %d: closing wp:%s while wp:%s (line %d) is open"
                            % (line, name, stack[-1][0], stack[-1][1]))
            # Recover: drop back to the matching opener if there is one.
            names = [n for n, _ in stack]
            if name in names:
                while stack and stack[-1][0] != name:
                    stack.pop()
                stack.pop()
        else:
            stack.pop()
    problems += ["line %d: wp:%s never closed" % (line, name) for name, line in stack]
    return problems


def check_block_delimiters(files):
    paths = block_markup_files(files)
    if not paths:
        return result("block-delimiters", False, None, [], [],
                      "no templates, parts or patterns: a classic theme has no block markup")
    findings = []
    for p in paths:
        findings += ["%s %s" % (p, prob) for prob in delimiter_problems(text(files[p]))]
    return result("block-delimiters", True, not findings, paths, findings)


# --------------------------------------------------------------------------
# main-landmark
# --------------------------------------------------------------------------

PART_RE = re.compile(r"<!--\s*wp:template-part\s+(\{.*?\})\s*/?-->", re.S)
PATTERN_RE = re.compile(r"<!--\s*wp:pattern\s+(\{.*?\})\s*/?-->", re.S)
MAIN_RE = re.compile(r"<main[\s>]|\"tagName\"\s*:\s*\"main\"", re.I)
PATTERN_SLUG_RE = re.compile(r"^\s*\*\s*Slug:\s*(\S+)", re.M | re.I)


def pattern_index(files):
    """{pattern slug: file path} from the Slug: header of each patterns/*.php."""
    out = {}
    for p in files:
        if p.startswith("patterns/") and p.endswith(".php"):
            m = PATTERN_SLUG_RE.search(text(files[p]))
            if m:
                out[m.group(1)] = p
    return out


def _attrs(raw):
    try:
        return json.loads(raw)
    except ValueError:
        return {}


def expanded(files, path, patterns, seen=None):
    """A template's markup with the parts and patterns it references inlined, as the
    rendered page would hold them, so a <main> inside a part counts."""
    seen = set() if seen is None else seen
    if path in seen or path not in files:
        return ""
    seen.add(path)
    markup = text(files[path])
    out = [markup]
    for m in PART_RE.finditer(markup):
        slug = _attrs(m.group(1)).get("slug", "")
        out.append(expanded(files, "parts/%s.html" % slug, patterns, seen))
    for m in PATTERN_RE.finditer(markup):
        slug = _attrs(m.group(1)).get("slug", "")
        if slug in patterns:
            out.append(expanded(files, patterns[slug], patterns, seen))
    return "\n".join(out)


def check_main_landmark(files):
    templates = sorted(p for p in files if p.startswith("templates/") and p.endswith(".html"))
    if not templates:
        php = sorted(p for p in files if "/" not in p and p.endswith(".php"))
        with_main = [p for p in php if MAIN_RE.search(text(files[p]))]
        return result("main-landmark", False, None, php, [],
                      "classic theme: no block templates. <main> found in: %s"
                      % (", ".join(with_main) or "no top-level PHP file")
                      + ". Check the rendered templates in tier 3.")
    patterns = pattern_index(files)
    missing = [t for t in templates if not MAIN_RE.search(expanded(files, t, patterns))]
    findings = ["%s has no <main> (nor any part or pattern it uses): core adds no skip link"
                % t for t in missing]
    return result("main-landmark", True, not missing, templates, findings)


# --------------------------------------------------------------------------
# local-fonts
# --------------------------------------------------------------------------

REMOTE_RE = re.compile(r"^(?:https?:)?//", re.I)
CSS_URL_RE = re.compile(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", re.I)
FONT_FACE_RE = re.compile(r"@font-face\s*\{(.*?)\}", re.S | re.I)
IMPORT_RE = re.compile(r"@import\s+(?:url\()?\s*['\"]?([^'\")\s;]+)", re.I)
FONT_HOSTS_RE = re.compile(r"fonts\.(?:googleapis|gstatic|bunny)\.|use\.typekit|fonts\.adobe", re.I)


def _font_srcs(node):
    if isinstance(node, dict):
        if "fontFace" in node and isinstance(node["fontFace"], list):
            for face in node["fontFace"]:
                src = face.get("src") if isinstance(face, dict) else None
                for s in ([src] if isinstance(src, str) else src or []):
                    yield s
        for v in node.values():
            yield from _font_srcs(v)
    elif isinstance(node, list):
        for v in node:
            yield from _font_srcs(v)


def check_local_fonts(files):
    checked, findings, sources = [], [], 0
    for p in sorted(files):
        if p == "theme.json" or (p.startswith("styles/") and p.endswith(".json")):
            checked.append(p)
            try:
                data = json.loads(text(files[p]))
            except ValueError as e:
                findings.append("%s is not JSON (%s)" % (p, e))
                continue
            for src in _font_srcs(data):
                sources += 1
                if REMOTE_RE.match(src):
                    findings.append("%s: font source %s is remote" % (p, src))
                elif src.startswith("file:./"):
                    rel = src[len("file:./"):]
                    if rel not in files:
                        findings.append("%s: font source %s is not in the zip" % (p, src))
        elif p.endswith(".css"):
            css = text(files[p])
            faces = FONT_FACE_RE.findall(css)
            imports = [u for u in IMPORT_RE.findall(css) if FONT_HOSTS_RE.search(u)]
            if faces or imports:
                checked.append(p)
            for face in faces:
                for u in CSS_URL_RE.findall(face):
                    sources += 1
                    if REMOTE_RE.match(u):
                        findings.append("%s: @font-face source %s is remote" % (p, u))
            findings += ["%s: @import of %s" % (p, u) for u in imports]
        elif p.endswith(".php"):
            for m in FONT_HOSTS_RE.finditer(text(files[p])):
                findings.append("%s: references a font host (%s)" % (p, m.group(0)))
                break
    note = "%d font source(s)" % sources
    return result("local-fonts", True, not findings, checked, findings, note)


# --------------------------------------------------------------------------
# msgfmt
# --------------------------------------------------------------------------

MO_MAGIC = (b"\xde\x12\x04\x95", b"\x95\x04\x12\xde")


def check_msgfmt(files, msgfmt=None):
    msgfmt = msgfmt if msgfmt is not None else shutil.which("msgfmt")
    po = sorted(p for p in files if p.endswith(".po"))
    mo = sorted(p for p in files if p.endswith(".mo"))
    pot = sorted(p for p in files if p.endswith(".pot"))
    checked, findings = po + mo + pot, []
    if not checked:
        return result("msgfmt", True, True, [], [], "no translation catalogue in the zip")
    if (po or pot) and not msgfmt:
        return result("msgfmt", True, False, checked,
                      ["msgfmt is not installed: apt install gettext, then run tier2.py again"])
    for p in mo:
        if files[p][:4] not in MO_MAGIC:
            findings.append("%s is not a compiled .mo file (bad magic number)" % p)
    with tempfile.TemporaryDirectory() as tmp:
        for p in po + pot:
            src = Path(tmp) / PurePosixPath(p).name
            src.write_bytes(files[p])
            if not msgfmt:
                continue
            r = subprocess.run([msgfmt, "--check-format", "--check-header", "-o", "/dev/null",
                                str(src)] if p.endswith(".pot") else
                               [msgfmt, "--check", "-o", "/dev/null", str(src)],
                               capture_output=True, text=True)
            if r.returncode != 0:
                msg = " | ".join(l.replace(str(src), p) for l in r.stderr.strip().splitlines()[:5])
                findings.append("%s: %s" % (p, msg))
    return result("msgfmt", True, not findings, checked, findings,
                  "%d .po, %d .mo, %d .pot checked" % (len(po), len(mo), len(pot)))


# --------------------------------------------------------------------------
# images
# --------------------------------------------------------------------------

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp")


def image_size(data):
    """(width, height) from the file header, or None when it cannot be read."""
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        return struct.unpack("<HH", data[6:10])
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        kind = data[12:16]
        if kind == b"VP8X" and len(data) >= 30:
            w = int.from_bytes(data[24:27], "little") + 1
            h = int.from_bytes(data[27:30], "little") + 1
            return w, h
        if kind == b"VP8 " and len(data) >= 30:
            w, h = struct.unpack("<HH", data[26:30])
            return w & 0x3FFF, h & 0x3FFF
        if kind == b"VP8L" and len(data) >= 25:
            b = data[21:25]
            w = 1 + (((b[1] & 0x3F) << 8) | b[0])
            h = 1 + (((b[3] & 0xF) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
            return w, h
        return None
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            length = struct.unpack(">H", data[i + 2:i + 4])[0]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            i += 2 + length
    return None


def image_metadata(data):
    """Metadata blocks worth a look: EXIF (and GPS inside it), XMP, IPTC, PNG text."""
    found = []
    if data[:2] == b"\xff\xd8":
        if b"Exif\x00\x00" in data[:65536]:
            found.append("EXIF")
            if b"GPS" in data[:65536]:
                found.append("GPS")
        if b"http://ns.adobe.com/xap/1.0/" in data[:65536]:
            found.append("XMP")
        if b"Photoshop 3.0" in data[:65536]:
            found.append("IPTC")
    elif data[:8] == b"\x89PNG\r\n\x1a\n":
        for chunk in (b"tEXt", b"iTXt", b"zTXt", b"eXIf"):
            if chunk in data:
                found.append(chunk.decode())
    elif data[:4] == b"RIFF":
        for chunk in (b"EXIF", b"XMP "):
            if chunk in data[:65536]:
                found.append(chunk.decode().strip())
    return found


def check_images(files):
    images = sorted(p for p in files if p.lower().endswith(IMAGE_EXT))
    findings, details = [], []
    for p in images:
        data = files[p]
        size = image_size(data)
        meta = image_metadata(data)
        details.append("%s %s %d bytes%s" % (p, "%dx%d" % size if size else "?x?", len(data),
                                            " meta: " + ",".join(meta) if meta else ""))
        if not size:
            findings.append("%s: dimensions unreadable (corrupt, or not the format its name says)" % p)
        if "GPS" in meta:
            findings.append("%s: carries GPS location in its EXIF" % p)
        if PurePosixPath(p).name.lower().startswith("screenshot.") and "/" not in p and size:
            w, h = size
            if w > SCREENSHOT_MAX[0] or h > SCREENSHOT_MAX[1]:
                findings.append("%s is %dx%d, larger than %dx%d" % ((p, w, h) + SCREENSHOT_MAX))
            if w * 3 != h * 4:
                findings.append("%s is %dx%d, not 4:3" % (p, w, h))
    if not any(PurePosixPath(p).name.lower().startswith("screenshot.") and "/" not in p
               for p in images):
        findings.append("no screenshot.png or screenshot.jpg at the theme root")
    return result("images", True, not findings, details, findings,
                  "%d image(s)" % len(images))


# --------------------------------------------------------------------------
# print-stylesheet
# --------------------------------------------------------------------------

PRINT_CLAIM_RE = re.compile(r"\bprint(?:-friendly|\s+(?:style|stylesheet|styles|css|friendly|ready)\b)"
                            r"|\bprinter[- ]friendly\b", re.I)
PRINT_MEDIA_RE = re.compile(r"@media\s+[^{]*\bprint\b", re.I)
ENQUEUE_PRINT_RE = re.compile(r"wp_(?:enqueue|register)_style\s*\([^;]*['\"]print['\"]", re.I | re.S)


def check_print_stylesheet(files):
    readmes = sorted(p for p in files if "/" not in p and p.lower() in ("readme.txt", "readme.md"))
    claims = []
    for p in readmes:
        for i, line in enumerate(text(files[p]).splitlines(), 1):
            if PRINT_CLAIM_RE.search(line):
                claims.append("%s line %d: %s" % (p, i, line.strip()[:120]))
    out_files = []
    for p in sorted(files):
        if p.endswith(".css") and PRINT_MEDIA_RE.search(text(files[p])):
            out_files.append(p)
        elif p.endswith(".php") and ENQUEUE_PRINT_RE.search(text(files[p])):
            out_files.append(p)
        elif p == "theme.json" and PRINT_MEDIA_RE.search(text(files[p])):
            out_files.append(p)
    r = result("print-stylesheet", bool(claims), bool(out_files) if claims else None,
               readmes + out_files,
               [] if out_files or not claims else
               ["the readme claims a print stylesheet but no @media print or print-media "
                "stylesheet ships"],
               ("readme claims print styles; " if claims else "readme makes no print-stylesheet claim; ")
               + (("print styles in: %s" % ", ".join(out_files)) if out_files else "no @media print"))
    r["claimed"] = bool(claims)
    r["claims"] = claims
    return r


# --------------------------------------------------------------------------

def run_checks(files, msgfmt=None):
    return {
        "main-landmark": check_main_landmark(files),
        "local-fonts": check_local_fonts(files),
        "msgfmt": check_msgfmt(files, msgfmt),
        "images": check_images(files),
        "block-delimiters": check_block_delimiters(files),
        "print-stylesheet": check_print_stylesheet(files),
    }


def write_results(results, evidence, stem, slug, version):
    evidence.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, res in results.items():
        res = dict(res, theme=slug, version=version)
        path = evidence / ("%s-%s.json" % (stem, name))
        path.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
        paths.append(path)
    return paths


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("notes", help="<reports>/<slug>-<version>.md (the name gives slug and version)")
    ap.add_argument("--project", default=".", help="DDEV review install (default: cwd)")
    ap.add_argument("--zip")
    ap.add_argument("--evidence")
    a = ap.parse_args(argv)

    notes = Path(a.notes)
    m = re.fullmatch(r"(.+)-(\d+(?:\.\d+)*)", notes.stem)
    if not m:
        print("notes must be named <slug>-<version>.md: %s" % notes, file=sys.stderr)
        return 2
    slug, version = m.groups()
    zip_path = Path(a.zip) if a.zip else Path(a.project) / "review-zips" / ("%s.%s.zip" % (slug, version))
    if not zip_path.is_file():
        print("no zip at %s (pass --zip, or run from the review install)" % zip_path, file=sys.stderr)
        return 2
    evidence = Path(a.evidence) if a.evidence else notes.parent / "evidence"

    results = run_checks(zip_files(zip_path))
    write_results(results, evidence, notes.stem, slug, version)
    print("tier 2: %s %s -> %s" % (slug, version, evidence))
    for name, res in results.items():
        state = "n/a " if not res["applicable"] else ("pass" if res["pass"] else "FIND")
        print("%s  %-17s %s" % (state, name, res["note"] or ""))
        for f in res["findings"]:
            print("        - %s" % f)
    print("Findings are facts for the reviewer to judge; the gate counts each check as done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
