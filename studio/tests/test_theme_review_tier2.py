"""Tests for studio/theme-review/tier2.py and the gate's reading of its results.

Every theme here is fictional ("Lantern Row", block and classic), built in memory.
"""
import importlib.util
import json
import struct
import zipfile
from pathlib import Path

import pytest

_DIR = Path(__file__).parent.parent / "theme-review"


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, _DIR / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tier2 = _load("tier2", "tier2.py")
gate = _load("review_gate_t2", "review-gate.py")


def png(w, h, extra=b""):
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", w, h) + b"\x08\x02\x00\x00\x00" + extra


def b(s):
    return s.encode() if isinstance(s, str) else s


BLOCK = {
    "style.css": "/*\nTheme Name: Lantern Row\nVersion: 1.0.0\n*/",
    "readme.txt": "=== Lantern Row ===\nA quiet blog theme.\n",
    "theme.json": json.dumps({"settings": {"typography": {"fontFamilies": [
        {"fontFamily": "Serif", "fontFace": [{"src": ["file:./assets/fonts/serif.woff2"]}]}]}}}),
    "assets/fonts/serif.woff2": "x",
    "templates/index.html": '<!-- wp:template-part {"slug":"header"} /-->\n'
                            '<!-- wp:group {"tagName":"main"} --><main class="wp-block-group">'
                            '<!-- wp:paragraph --><p>x</p><!-- /wp:paragraph --></main><!-- /wp:group -->',
    "templates/home.html": '<!-- wp:template-part {"slug":"header"} /-->\n<!-- wp:pattern {"slug":"lantern-row/body"} /-->',
    "parts/header.html": "<!-- wp:site-title /-->",
    "patterns/body.php": "<?php\n/**\n * Title: Body\n * Slug: lantern-row/body\n */\n?>\n"
                         '<!-- wp:group {"tagName":"main"} --><main></main><!-- /wp:group -->',
    "screenshot.png": png(1200, 900),
}
CLASSIC = {
    "style.css": "/*\nTheme Name: Lantern Row Classic\nVersion: 1.0.0\n*/",
    "readme.txt": "Classic.\n",
    "index.php": "<?php get_header(); ?><main id='main'></main>",
    "header.php": "<html>",
    "screenshot.png": png(1200, 900),
}


def files(base, **edits):
    """`base` as bytes, with `edits` applied (path: content, or None to remove)."""
    out = {k: b(v) for k, v in base.items()}
    for k, v in edits.items():
        if v is None:
            out.pop(k, None)
        else:
            out[k] = b(v)
    return out


def test_block_theme_passes_every_check():
    res = tier2.run_checks(files(BLOCK), msgfmt="")
    assert {k: r["pass"] for k, r in res.items()} == {
        "main-landmark": True, "local-fonts": True, "msgfmt": True, "images": True,
        "block-delimiters": True, "print-stylesheet": None}
    assert res["print-stylesheet"]["claimed"] is False
    assert res["print-stylesheet"]["applicable"] is False


def test_main_found_through_a_pattern_and_missing_reported():
    res = tier2.check_main_landmark(files(BLOCK, **{"templates/single.html": "<!-- wp:post-content /-->"}))
    assert res["pass"] is False
    assert res["findings"] == ["templates/single.html has no <main> (nor any part or pattern it "
                               "uses): core adds no skip link"]


@pytest.mark.parametrize("markup,problem", [
    ("<!-- wp:group --><div>", "never closed"),
    ("<!-- /wp:group -->", "nothing open"),
    ("<!-- wp:group --><!-- wp:columns --><!-- /wp:group -->", "while wp:columns"),
])
def test_unbalanced_delimiters(markup, problem):
    assert any(problem in p for p in tier2.delimiter_problems(markup))


def test_balanced_with_nested_json_and_namespaced_blocks():
    markup = ('<!-- wp:group {"style":{"spacing":{"padding":"1rem"}}} --><!-- wp:acme/card {"a":{"b":1}} -->'
              '<!-- /wp:acme/card --><!-- wp:spacer /--><!-- /wp:group -->')
    assert tier2.delimiter_problems(markup) == []


def test_remote_fonts_found_in_theme_json_and_css():
    res = tier2.check_local_fonts(files(BLOCK, **{
        "theme.json": json.dumps({"x": {"fontFace": [{"src": "https://fonts.example.test/a.woff2"}]}}),
        "assets/css/x.css": "@import url('https://fonts.googleapis.com/css2?family=A');"}))
    assert res["pass"] is False
    assert any("remote" in f for f in res["findings"])
    assert any("@import" in f for f in res["findings"])


def test_missing_local_font_file():
    res = tier2.check_local_fonts(files(BLOCK, **{"assets/fonts/serif.woff2": None}))
    assert any("not in the zip" in f for f in res["findings"])


def test_images_screenshot_and_gps():
    jpeg = b"\xff\xd8\xff\xe1\x00\x10Exif\x00\x00GPS\x00\x00\x00\x00\x00\xff\xc0\x00\x11\x08\x00\x20\x00\x40" + b"\x00" * 20
    res = tier2.check_images(files(BLOCK, **{
        "screenshot.png": png(1300, 900), "assets/images/a.jpg": jpeg}))
    joined = " ".join(res["findings"])
    assert "larger than 1200x900" in joined and "not 4:3" in joined and "GPS" in joined
    assert any("a.jpg 64x32" in d for d in res["checked"])


def test_no_screenshot_is_a_finding():
    res = tier2.check_images(files(BLOCK, **{"screenshot.png": None}))
    assert "no screenshot.png" in res["findings"][0]


def test_msgfmt_missing_tool_is_reported_not_passed():
    res = tier2.check_msgfmt(files(BLOCK, **{"languages/x.po": "msgid \"\"\nmsgstr \"\"\n"}), msgfmt="")
    assert res["pass"] is False and "msgfmt is not installed" in res["findings"][0]


def test_bad_mo_magic():
    res = tier2.check_msgfmt(files(BLOCK, **{"languages/x.mo": "notmo"}), msgfmt="")
    assert res["pass"] is False and "bad magic" in res["findings"][0]


def test_print_claim_without_print_styles_is_a_finding():
    res = tier2.check_print_stylesheet(files(BLOCK, **{"readme.txt": "Includes a print stylesheet.\n"}))
    assert res["claimed"] and res["applicable"] and res["pass"] is False


def test_print_claim_with_media_print():
    res = tier2.check_print_stylesheet(files(BLOCK, **{
        "readme.txt": "Print-friendly.\n", "assets/css/print.css": "@media print { a { color: #000 } }"}))
    assert res["pass"] is True and "assets/css/print.css" in res["checked"]


def test_classic_theme_block_delimiters_and_main_not_applicable():
    res = tier2.run_checks(files(CLASSIC), msgfmt="")
    assert res["block-delimiters"]["applicable"] is False
    assert res["main-landmark"]["applicable"] is False
    assert "index.php" in res["main-landmark"]["note"]


def test_writer_and_gate_rows(tmp_path):
    zpath = tmp_path / "lantern-row.1.0.0.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        for k, v in files(BLOCK).items():
            z.writestr("lantern-row/" + k, v)
    notes = tmp_path / "lantern-row-1.0.0.md"
    notes.write_text("# notes")
    ev = tmp_path / "evidence"
    assert tier2.main([str(notes), "--zip", str(zpath), "--evidence", str(ev)]) == 0
    assert sorted(p.name for p in ev.iterdir()) == sorted(
        "lantern-row-1.0.0-%s.json" % c for c in tier2.CHECKS)
    rows = gate.check_tier2(ev, "lantern-row-1.0.0", gate.zip_files(zpath))
    assert all(r.ok for r in rows)
    assert [r.detail for r in rows if "print" in r.name][0].startswith("n/a")


def test_gate_classic_theme_block_delimiters_na_without_file(tmp_path):
    ev = tmp_path / "ev"
    ev.mkdir()
    for name in gate.TIER2:
        if name != "block-delimiters":
            (ev / ("x-1.0-%s.json" % name)).write_text("{}")
    rows = gate.check_tier2(ev, "x-1.0", files(CLASSIC))
    row = [r for r in rows if "delimiters" in r.name][0]
    assert row.ok and row.detail.startswith("n/a")


def test_gate_still_fails_a_missing_result(tmp_path):
    rows = gate.check_tier2(tmp_path, "x-1.0", files(BLOCK))
    assert not any(r.ok for r in rows)


def test_gate_counts_findings_as_done(tmp_path):
    (tmp_path / "x-1.0-images.json").write_text(json.dumps(
        {"applicable": True, "pass": False, "findings": ["a", "b"]}))
    row = [r for r in gate.check_tier2(tmp_path, "x-1.0", files(BLOCK)) if "image" in r.name][0]
    assert row.ok and "2 finding(s)" in row.detail


def test_site_editor_summary_counts_and_database_copies():
    import sys
    sys.path.insert(0, str(_DIR / "cdp"))
    se = _load("cdp_site_editor", "cdp/cdp_site_editor.py")
    out = se.summarise({
        "templates_and_parts": [
            {"id": "lantern-row//index", "source": "theme", "has_theme_file": True, "invalid": 2, "blocks": []},
            {"id": "lantern-row//home", "source": "custom", "has_theme_file": True, "invalid": 0, "blocks": []}],
        "patterns": [{"name": "lantern-row/body", "invalid": 1, "blocks": []}],
        "controls": {"separator_invalid": True, "heading_level_invalid": True}}, "lantern-row", "1.0.0")
    assert out["invalid_total"] == 3
    assert out["database_copies"] == ["lantern-row//home"]
    assert out["tool"] == "cdp_site_editor.py" and out["version"] == "1.0.0"
