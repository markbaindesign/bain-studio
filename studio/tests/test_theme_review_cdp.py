"""Tests for studio/theme-review/cdp/cdp_check.py - the pure summaries only.

The browser half needs Chromium and a running review site, so it is exercised by
running the script against the review install, not here.
"""
import importlib.util
import json
from pathlib import Path

import pytest

_PATH = Path(__file__).parent.parent / "theme-review" / "cdp" / "cdp_check.py"
_spec = importlib.util.spec_from_file_location("cdp_check", _PATH)
cdp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cdp)


def stop(txt, x=0, y=0, w=80, h=20, ow=2, os="solid", vis=True, obscured=False, key=None):
    return {"tag": "A", "txt": txt, "x": x, "y": y, "w": w, "h": h, "ow": ow, "os": os,
            "vis": vis, "obscured": obscured, "key": key or "<a>%s</a>" % txt}


def test_import_does_not_launch_anything():
    # The old script ran at import: read argv and started Chromium. The gate imports it.
    assert hasattr(cdp, "main") and hasattr(cdp, "page_pass_summary")


def test_parse_widths_default_and_custom():
    assert cdp.parse_widths("390,1440") == [390, 1440]
    assert cdp.parse_widths(" 320 , 768,") == [320, 768]


@pytest.mark.parametrize("bad", ["", ",", "0", "-5", "abc"])
def test_parse_widths_rejects(bad):
    with pytest.raises(ValueError):
        cdp.parse_widths(bad)


def test_default_widths_are_phone_and_desktop():
    assert cdp.DEFAULT_WIDTHS == (390, 1440)


def test_page_pass_exact_reverse_when_back_mirrors_forward():
    fwd = [stop("a", y=0), stop("b", y=30), stop("c", y=60)]
    r = cdp.page_pass_summary(fwd, fwd[::-1], 5, "focus left the page")
    assert r["shift_tab_exact_reverse"] is True
    assert r["stops"] == 3 and r["focusable_in_dom"] == 5 and r["first"] == "a"
    assert r["ended"] == "focus left the page"


def test_page_pass_reverse_false_when_order_differs():
    fwd = [stop("a"), stop("b", y=30), stop("c", y=60)]
    back = [fwd[2], fwd[0], fwd[1]]
    assert cdp.page_pass_summary(fwd, back, 3, "focus left the page")["shift_tab_exact_reverse"] is False


def test_page_pass_reverse_false_when_back_pass_short():
    fwd = [stop("a"), stop("b", y=30), stop("c", y=60)]
    assert cdp.page_pass_summary(fwd, [fwd[2]], 3, "focus left the page")["shift_tab_exact_reverse"] is False


def test_page_pass_guard_end_expects_reverse_without_last_stop():
    fwd = [stop("a"), stop("b", y=30), stop("c", y=60)]
    ended = "hit the 600-stop runaway guard"
    assert cdp.page_pass_summary(fwd, [fwd[1], fwd[0]], 3, ended)["shift_tab_exact_reverse"] is True


def test_page_pass_empty_is_never_a_pass():
    r = cdp.page_pass_summary([], [], 0, "focus left the page")
    assert r["shift_tab_exact_reverse"] is False and r["first"] is None and r["stops"] == 0


def test_page_pass_flags_thin_invisible_obscured():
    fwd = [stop("thin", ow=1), stop("none", os="none", y=30), stop("ghost", vis=False, y=60),
           stop("under", obscured=True, y=90)]
    r = cdp.page_pass_summary(fwd, fwd[::-1], 4, "focus left the page")
    assert r["outline_lt_2px"] == ["thin", "none"]
    assert r["invisible"] == ["ghost"]
    assert r["obscured"] == ["under"]


def test_page_pass_order_inversion_same_column_only():
    # b sits above a in the same column: an inversion. c jumps up but in another column.
    fwd = [stop("a", x=10, y=200), stop("b", x=20, y=100), stop("c", x=400, y=50)]
    r = cdp.page_pass_summary(fwd, fwd[::-1], 3, "focus left the page")
    assert r["order_inversions"] == [["a", "b"]]


def test_menu_pass_counts_links_and_missing():
    r = cdp.menu_pass_summary("nav", "button", ["Home", "About", "Close"], [],
                              ["Home", "About", "Blog"], "focus left the nav", True)
    assert r["stops"] == 3 and r["links_in_nav"] == 3 and r["links_reached"] == 2
    assert r["never_focused"] == ["Blog"]
    assert r["escape_returns_to_opener"] is True


def test_page_line_abort_reports_no_measurement():
    line = cdp.page_line({"path": "/", "width": 390, "title": "default",
                          "status": "abort", "reason": "theme=other innerWidth=690"})
    assert "ABORT" in line and "scrollWidth" not in line


def test_page_line_reports_skipped_menu_without_concluding():
    fwd = [stop("a")]
    rec = {"path": "/", "width": 1440, "title": "long", "status": "ok", "theme": "t",
           "inner_width": 1440, "scroll_width": 1440, "past_edge": [],
           "keyboard": cdp.page_pass_summary(fwd, fwd, 1, "focus left the page"),
           "menu": {"skipped": "using nav / button: opener never took focus in 60 Tab presses"}}
    out = cdp.page_line(rec)
    assert "[long title]" in out and "opener never took focus in 60 Tab presses" in out


def test_run_record_counts_aborts_and_is_json():
    pages = [{"status": "ok"}, {"status": "abort"}, {"status": "abort"}]
    rec = cdp.run_record("https://x.test", "t", [390, 1440], ["/"], True, pages)
    assert rec["aborted"] == 2 and rec["tool"] == "cdp_check" and rec["long_title"] is True
    json.dumps(rec)


def test_main_restores_title_when_sweep_fails(monkeypatch, tmp_path):
    calls = []

    def fake_wp(project, *args):
        calls.append(args)
        return "Original Title" if args[0] == "get" else ""

    class Boom:
        def __init__(self, width):
            if calls:  # the default-title sweep passes, the long-title one fails
                raise RuntimeError("chromium died")
            self.width = width

        def close(self):
            pass

    monkeypatch.setattr(cdp, "wp_option", fake_wp)
    monkeypatch.setattr(cdp, "Browser", Boom)
    monkeypatch.setattr(cdp, "check_page", lambda b, base, theme, path, kind: {
        "path": path, "width": b.width, "title": kind, "status": "abort", "reason": "x"})
    with pytest.raises(RuntimeError):
        cdp.main(["https://x.test", "t", "--long-title", "--project", str(tmp_path)])
    assert calls[-1] == ("update", "blogname", "Original Title")
