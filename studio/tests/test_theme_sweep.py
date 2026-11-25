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


# --- install-zip (BSTD-916): a local zip, installed as fetch installs a download ---

import zipfile  # noqa: E402

import pytest  # noqa: E402


def local_zip(where, slug="quill-press", style=STYLE, name="build.zip", extra=None):
    path = where / name
    with zipfile.ZipFile(path, "w") as z:
        if style is not None:
            z.writestr(f"{slug}/style.css", style)
        z.writestr(f"{slug}/index.php", "<?php\n")
        for rel, text in (extra or {}).items():
            z.writestr(rel, text)
    return path


def review_project(tmp_path):
    project = tmp_path / "site"
    (project / "wp-content" / "themes").mkdir(parents=True)
    return project


def test_zip_identity_reads_slug_and_version(tmp_path):
    assert sweep.zip_identity(local_zip(tmp_path)) == ("quill-press", "1.2.0")
    assert sweep.zip_identity(local_zip(tmp_path), "2.0.0") == ("quill-press", "2.0.0")


def test_zip_identity_needs_one_top_folder(tmp_path):
    with pytest.raises(ValueError, match="one top-level"):
        sweep.zip_identity(local_zip(tmp_path, extra={"other/x.txt": "x"}))


def test_zip_identity_ignores_macos_folder(tmp_path):
    z = local_zip(tmp_path, extra={"__MACOSX/quill-press/._style.css": "x"})
    assert sweep.zip_identity(z) == ("quill-press", "1.2.0")


def test_zip_identity_without_version_asks_for_one(tmp_path):
    with pytest.raises(ValueError, match="--version"):
        sweep.zip_identity(local_zip(tmp_path, style="/*\nTheme Name: Quill Press\n*/\n"))
    assert sweep.zip_identity(local_zip(tmp_path, style=None), "0.1.0") == ("quill-press", "0.1.0")


def test_install_zip_copies_and_extracts(tmp_path):
    project = review_project(tmp_path)
    old = project / "wp-content" / "themes" / "quill-press"
    old.mkdir()
    (old / "stale.php").write_text("old")
    slug = sweep.cmd_install_zip(project, local_zip(tmp_path))
    assert slug == "quill-press"
    assert (project / "review-zips" / "quill-press.1.2.0.zip").is_file()
    theme = project / "wp-content" / "themes" / "quill-press"
    assert (theme / "style.css").is_file() and (theme / "index.php").is_file()
    assert not (theme / "stale.php").exists()
    assert not list((project / "review-zips").glob(".extract-*"))


def test_install_zip_from_review_zips_itself(tmp_path):
    project = review_project(tmp_path)
    (project / "review-zips").mkdir()
    z = local_zip(project / "review-zips", name="quill-press.1.2.0.zip")
    assert sweep.cmd_install_zip(project, z) == "quill-press"
    assert (project / "wp-content" / "themes" / "quill-press" / "style.css").is_file()


def test_install_zip_missing_file_exits(tmp_path):
    with pytest.raises(SystemExit):
        sweep.cmd_install_zip(review_project(tmp_path), tmp_path / "nope.zip")
