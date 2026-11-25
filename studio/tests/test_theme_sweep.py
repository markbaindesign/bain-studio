"""Tests for studio/theme-review/theme-sweep.py - the file-reading half.

The DDEV half (fetch, reset, crawl, Theme Check) is exercised by running the sweep on
a real zip in the review install, not here. The themes below are fictional.
"""
import importlib.util
from pathlib import Path

_PATH = Path(__file__).parent.parent / "theme-review" / "theme-sweep.py"
_spec = importlib.util.spec_from_file_location("theme_sweep", _PATH)
sweep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sweep)


def make_theme(tmp_path, files, slug="quill-press"):
    root = tmp_path / slug
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return root


STYLE = """/*
Theme Name: Quill Press
Text Domain: quill-press
Version: 1.2.0
Tags: blog, custom-logo
*/
body {}
"""


def test_parse_header(tmp_path):
    t = make_theme(tmp_path, {"style.css": STYLE})
    h = sweep.parse_header(t / "style.css")
    assert h["theme name"] == "Quill Press"
    assert h["text domain"] == "quill-press"
    assert h["tags"] == "blog, custom-logo"


def test_theme_shape_block_vs_classic(tmp_path):
    block = make_theme(tmp_path, {"style.css": STYLE, "templates/index.html": "",
                                  "theme.json": '{"version": 3}'}, slug="b")
    classic = make_theme(tmp_path, {"style.css": STYLE, "index.php": "<?php"}, slug="c")
    assert sweep.theme_shape(block)["block"] is True
    assert sweep.theme_shape(block)["theme_json"] == {"version": 3}
    assert sweep.theme_shape(classic)["block"] is False


def test_theme_shape_reports_bad_theme_json(tmp_path):
    t = make_theme(tmp_path, {"style.css": STYLE, "theme.json": "{nope"})
    assert "_parse_error" in sweep.theme_shape(t)["theme_json"]


def test_prefix_report_multi_segment_slug(tmp_path):
    t = make_theme(tmp_path, {"style.css": STYLE, "functions.php": (
        "<?php\nfunction quill_press_setup() {}\nfunction setup() {}\n"
        "function other_vendor_thing() {}\n")})
    funcs, unprefixed, offslug = sweep.prefix_report(t, sweep.parse_header(t / "style.css"))
    names = {n for n, _ in funcs}
    assert names == {"quill_press_setup", "setup", "other_vendor_thing"}
    assert [n for n, _ in unprefixed] == ["setup"]
    assert [n for n, _ in offslug] == ["other_vendor_thing"]


def test_prefix_report_ignores_inline_js(tmp_path):
    t = make_theme(tmp_path, {"style.css": STYLE, "footer.php": (
        "<?php ?>\n<script>\nfunction toggle() {}\n</script>\n")})
    funcs, _, _ = sweep.prefix_report(t, sweep.parse_header(t / "style.css"))
    assert funcs == []


def test_text_domains_counts(tmp_path):
    t = make_theme(tmp_path, {"style.css": STYLE, "index.php": (
        "<?php esc_html_e( 'Hi', 'quill-press' ); __( 'x', 'quill-press' ); _e( 'y', 'wrong' );")})
    assert sweep.text_domains(t) == {"quill-press": 2, "wrong": 1}


def test_remote_hosts_skips_header_and_allowlisted_hosts(tmp_path):
    t = make_theme(tmp_path, {
        "style.css": STYLE + "/* https://header.example.com */",
        "functions.php": "<?php // https://cdn.example.net/x.js https://wordpress.org/",
        "assets/x.css": "@import url(https://fonts.googleapis.com/css2);"})
    hosts = sweep.remote_hosts(t)
    assert "cdn.example.net" in hosts
    assert "header.example.com" not in hosts
    assert "wordpress.org" not in hosts
    assert "fonts.googleapis.com" in hosts  # reported; the report marks the exception
