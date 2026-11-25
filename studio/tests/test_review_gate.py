"""Tests for studio/theme-review/review-gate.py.

Every review here is synthetic: a fictional block theme, "Quill Press", built in a temp
folder, with notes, comment, evidence and mirror written to match. The handbook and
guideline pages are stubbed, so nothing is fetched.
"""
import importlib.util
import json
import re
import zipfile
from pathlib import Path

import pytest

_DIR = Path(__file__).parent.parent / "theme-review"
_spec = importlib.util.spec_from_file_location("review_gate", _DIR / "review-gate.py")
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

SLUG, VERSION = "quill-press", "1.2.0"
STEM = "%s-%s" % (SLUG, VERSION)

STYLE = """/*
Theme Name: Quill Press
Version: 1.2.0
Tags: blog, full-site-editing{extra}
*/
"""
FUNCTIONS = """<?php
function quill_press_setup() {}
add_action( 'after_setup_theme', 'quill_press_setup' );
function quill_press_assets() {}
add_action( 'wp_enqueue_scripts', 'quill_press_assets' );
"""
THEME_FILES = {
    "style.css": None,  # filled per test
    "functions.php": FUNCTIONS,
    "templates/index.html": "<!-- wp:group {\"tagName\":\"main\"} --><main></main><!-- /wp:group -->",
    "parts/header.html": "<!-- wp:site-title /-->",
    "assets/fonts/a.woff2": "x",
    "assets/fonts/b.woff2": "x",
}

HANDBOOK = "".join("<h3>%d. Section %d</h3>" % (n, n) for n in (1, 2, 3))
GUIDES = ('<a href="/docs/topics/theme-guidelines/skip-to-content/">a</a>'
          '<a href="/docs/topics/theme-guidelines/sufficient-color-contrast/">b</a>')


def stub(url):
    return GUIDES if "wpaccessibility" in url else HANDBOOK


def failing(url):
    raise OSError("network down")


NOTES = """# Quill Press 1.2.0 - review notes

Ticket #1. Reviewed 2026-01-02.

**{claim} review** under the project definition.

## Verdict

0 required.

## Handbook required

Page https://make.wordpress.org/themes/handbook/review/required/, fetched and read 2026-01-02.

| § | Verdict |
|---|---|
| 1 Licensing | Pass |
| 2 Privacy | Pass |
| 3 Accessibility | Pass |
{guides}
## Tags

| Tag | Evidence |
|---|---|
| blog | posts |

## Functions and hooks

| Name | Verdict |
|---|---|
| `quill_press_setup()` on `after_setup_theme` | OK |
| `quill_press_assets()` on `wp_enqueue_scripts` | OK |

## File ledger

| File | Lines | Verdict |
|---|---|---|
| style.css | 1-5 | OK |
| functions.php | 1-6 | OK |
| templates/index.html, parts/header.html | 1 each | OK |
| `assets/fonts/*.woff2` (2) | binary: name tables | OK |

## Other checks

Theme Check clean.

## Not done

{not_done}

## Outcome

Pending.
"""
GUIDE_SECTION = """
## Accessibility guidelines

Index https://wpaccessibility.org/docs/topics/theme-guidelines/, read 2026-01-02.

| Guideline | Verdict |
|---|---|
| skip-to-content | pass |
| sufficient-color-contrast | pass |
"""


def evidence_files(ev):
    ev.mkdir(parents=True, exist_ok=True)
    for name in list(gate.TIER2) + [gate.SITE_EDITOR]:
        (ev / ("%s-%s.json" % (STEM, name))).write_text("{}")
    pages = [{"path": "/", "width": w, "title": t, "status": "ok", "keyboard": {"stops": 3}}
             for w in (390, 1440) for t in ("default", "long")]
    (ev / ("%s-cdp.json" % STEM)).write_text(json.dumps(
        {"tool": "cdp_check", "long_title": True, "aborted": 0, "pages": pages}))
    for w in (390, 1440):
        (ev / ("%s-home-%d.png" % (STEM, w))).write_bytes(b"png")


def build(tmp_path, claim="Full", comment_claim="full", not_done="Nothing.",
          a11y=False, evidence=True, posting=True, notes_edit=None, files_edit=None):
    files = dict(THEME_FILES)
    files["style.css"] = STYLE.format(extra=", accessibility-ready" if a11y else "")
    files.update(files_edit or {})
    zpath = tmp_path / ("%s.%s.zip" % (SLUG, VERSION))
    with zipfile.ZipFile(zpath, "w") as z:
        for rel, text in files.items():
            if text is not None:
                z.writestr("%s/%s" % (SLUG, rel), text)
    reports = tmp_path / "reports"
    reports.mkdir()
    notes = NOTES.format(claim=claim, guides=GUIDE_SECTION if a11y else "", not_done=not_done)
    if notes_edit:
        notes = notes_edit(notes)
    (reports / ("%s.md" % STEM)).write_text(notes)
    (reports / ("%s-trac-comment.txt" % STEM)).write_text(
        "Hi,\n\nI did a %s review of Quill Press 1.2.0.\n" % comment_claim)
    if evidence:
        evidence_files(reports / "evidence")
    mirror = tmp_path / "asana-mirror.md"
    mirror.write_text("## TO DO\n\n" + (
        "### WPTR-900 — Quill Press: sign off the 1.2.0 review and post the comment on Trac\n"
        if posting else ""))
    return reports / ("%s.md" % STEM), zpath, reports / ("%s-trac-comment.txt" % STEM), \
        reports / "evidence", mirror


def run(tmp_path, get=stub, **kw):
    notes, z, comment, ev, mirror = build(tmp_path, **kw)
    return gate.run_gate(notes, z, comment, ev, mirror, get=get)


def failed(result):
    return [r.name for r in result["rows"] if not r.ok]


def test_complete_review_is_full_and_postable(tmp_path):
    r = run(tmp_path)
    assert failed(r) == []
    assert r["review"] == "full" and r["postable"]


def test_accessibility_ready_needs_every_guideline_by_slug(tmp_path):
    r = run(tmp_path, a11y=True)
    assert r["review"] == "full"


def test_guideline_named_not_slugged_fails(tmp_path):
    r = run(tmp_path, a11y=True,
            notes_edit=lambda n: n.replace("| skip-to-content |", "| Skip link |"))
    assert "every guideline has a verdict, keyed by slug" in failed(r)
    assert r["review"] == "partial"


def test_missing_guideline_section_on_accessibility_ready(tmp_path):
    r = run(tmp_path, a11y=True, notes_edit=lambda n: n.replace(GUIDE_SECTION, ""))
    assert "guideline verdict table" in failed(r)


def test_partial_that_says_partial_is_postable(tmp_path):
    r = run(tmp_path, evidence=False, claim="Partial", comment_claim="partial")
    assert r["review"] == "partial"
    assert r["postable"]


def test_partial_that_claims_full_is_not_postable(tmp_path):
    r = run(tmp_path, evidence=False)
    assert r["review"] == "partial"
    assert not r["postable"]
    assert "notes header claims partial" in failed(r)
    assert "comment claims partial" in failed(r)


def test_full_comment_claim_on_full_review_with_partial_header(tmp_path):
    r = run(tmp_path, claim="Partial")
    assert r["review"] == "full"
    assert not r["postable"]


def test_file_missing_from_ledger(tmp_path):
    r = run(tmp_path, files_edit={"assets/js/extra.js": "x"})
    assert "every zip file has a ledger row" in failed(r)
    row = [x for x in r["rows"] if x.name == "every zip file has a ledger row"][0]
    assert "assets/js/extra.js" in row.detail


def test_glob_count_must_match(tmp_path):
    r = run(tmp_path, files_edit={"assets/fonts/c.woff2": "x"})
    row = [x for x in r["rows"] if x.name == "every ledger row has lines and a verdict"][0]
    assert not row.ok and "says 2, zip has 3" in row.detail


def test_ledger_row_needs_lines(tmp_path):
    r = run(tmp_path, notes_edit=lambda n: n.replace("| functions.php | 1-6 | OK |",
                                                     "| functions.php |  | OK |"))
    assert "every ledger row has lines and a verdict" in failed(r)
    assert "every zip file has a ledger row" in failed(r)


def test_ledger_names_a_file_not_in_the_zip(tmp_path):
    r = run(tmp_path, notes_edit=lambda n: n.replace("| style.css | 1-5 | OK |",
                                                     "| style.css | 1-5 | OK |\n| gone.php | 1-2 | OK |"))
    row = [x for x in r["rows"] if x.name == "every ledger row has lines and a verdict"][0]
    assert "`gone.php` is not in the zip" in row.detail


def test_two_column_ledger_is_rejected(tmp_path):
    r = run(tmp_path, notes_edit=lambda n: n.replace("| File | Lines | Verdict |", "| File | Verdict |"))
    assert "ledger table" in failed(r)


def test_hook_without_verdict(tmp_path):
    r = run(tmp_path, files_edit={"functions.php": FUNCTIONS + "add_filter( 'body_class', 'x' );\n"})
    row = [x for x in r["rows"] if x.name == "every hook has a verdict"][0]
    assert not row.ok and "body_class" in row.detail


def test_function_prefix_does_not_count_as_another(tmp_path):
    r = run(tmp_path, files_edit={"functions.php": FUNCTIONS + "function quill_press() {}\n"})
    row = [x for x in r["rows"] if x.name == "every function has a verdict"][0]
    assert not row.ok and "quill_press" in row.detail


def test_handbook_section_missing(tmp_path):
    r = run(tmp_path, notes_edit=lambda n: n.replace("| 3 Accessibility | Pass |\n", ""))
    row = [x for x in r["rows"] if x.name == "every handbook section has a verdict"][0]
    assert not row.ok and "3 Section 3" in row.detail


def test_handbook_must_be_cited_with_date(tmp_path):
    r = run(tmp_path, notes_edit=lambda n: n.replace(", fetched and read 2026-01-02", ""))
    assert "handbook page cited with its read date" in failed(r)


def test_fetch_failure_is_a_fail_not_a_skip(tmp_path):
    r = run(tmp_path, get=failing, a11y=True)
    assert "handbook page fetched" in failed(r)
    assert "guideline index fetched" in failed(r)
    assert r["review"] == "partial"


def test_not_done_listing_makes_partial(tmp_path):
    r = run(tmp_path, not_done="Keyboard pass at 390.")
    assert "Not done is empty" in failed(r)


def test_not_done_nothing_with_optional_step_note_passes(tmp_path):
    r = run(tmp_path, not_done="Nothing. No screen reader run; the guideline calls it optional.")
    assert "Not done is empty" not in failed(r)


def test_missing_section(tmp_path):
    r = run(tmp_path, notes_edit=lambda n: n.replace("## Other checks", "## Extra checks"))
    row = [x for x in r["rows"] if x.name == "every template section present"][0]
    assert not row.ok and "Other checks" in row.detail


def test_evidence_needs_both_widths_and_long_title(tmp_path):
    notes, z, comment, ev, mirror = build(tmp_path)
    cdp = ev / ("%s-cdp.json" % STEM)
    rec = json.loads(cdp.read_text())
    rec["pages"] = [p for p in rec["pages"] if p["width"] == 1440 and p["title"] == "default"]
    rec["long_title"] = False
    cdp.write_text(json.dumps(rec))
    (ev / ("%s-home-390.png" % STEM)).unlink()
    r = gate.run_gate(notes, z, comment, ev, mirror, get=stub)
    f = failed(r)
    assert "tier 3: running site at 390 and desktop" in f
    assert "tier 3: keyboard pass at both widths" in f
    assert "tier 3: long site title" in f
    assert "tier 3: screenshots at 390 and desktop" in f


def test_other_versions_evidence_does_not_count(tmp_path):
    notes, z, comment, ev, mirror = build(tmp_path)
    for p in ev.iterdir():
        p.rename(ev / p.name.replace(VERSION, "1.1.0"))
    r = gate.run_gate(notes, z, comment, ev, mirror, get=stub)
    assert r["review"] == "partial"
    assert "tier 2: <main> in every template" in failed(r)


def test_classic_theme_needs_no_site_editor_result(tmp_path):
    notes, z, comment, ev, mirror = build(tmp_path, notes_edit=lambda n: n.replace(
        "| templates/index.html, parts/header.html | 1 each | OK |\n", ""),
        files_edit={"templates/index.html": None, "parts/header.html": None})
    (ev / ("%s-%s.json" % (STEM, gate.SITE_EDITOR))).unlink()
    r = gate.run_gate(notes, z, comment, ev, mirror, get=stub)
    assert r["shape"] == "classic" and r["review"] == "full"


def test_posting_task_required(tmp_path):
    r = run(tmp_path, posting=False)
    assert r["review"] == "full"
    assert not r["postable"]
    assert "sign-off and posting task" in failed(r)


def test_template_skeleton_has_every_section():
    text = (_DIR / "review-template.md").read_text()
    m = re.search(r"## Internal notes.*?```\n(.*?)```", text, re.S)
    secs = gate.sections(m.group(1))
    for s in gate.SECTIONS + [gate.GUIDELINES_SECTION]:
        assert gate.find_section(secs, s)[0] is not None, s
    _, body = gate.find_section(secs, "File ledger")
    assert gate.table_with(body, ["File", "Lines", "Verdict"]) is not None
    _, body = gate.find_section(secs, "Handbook required")
    assert gate.table_with(body, ["§", "Verdict"]) is not None
    _, body = gate.find_section(secs, "Functions and hooks")
    assert gate.table_with(body, ["Name", "Verdict"]) is not None
    _, body = gate.find_section(secs, gate.GUIDELINES_SECTION)
    assert gate.table_with(body, ["Guideline", "Verdict"]) is not None


def test_handover_fragment_and_page(tmp_path):
    r = run(tmp_path, evidence=False, claim="Partial", comment_claim="partial")
    frag = gate.handover_fragment(r)
    assert frag["review"] == "partial"
    statuses = {i["status"] for g in frag["groups"] for i in g["items"]}
    assert statuses <= {"pass", "fail", "todo", "na"}
    tiers = [i for i in frag["groups"][0]["items"] if i["label"].startswith("Tiers 2 and 3")][0]
    assert tiers["status"] == "fail"
    page = tmp_path / "page.html"
    data = {"theme": "Quill Press", "review": "full", "review_note": "old",
            "groups": [{"name": "Full-review definition", "items": []},
                       {"name": "Workflow", "items": [{"label": "Review gate run", "status": "na", "note": ""}]}]}
    page.write_text('<p>keep</p><script type="application/json" id="handover-data">%s</script><p>tail</p>'
                    % json.dumps(data))
    gate.write_handover(page, frag)
    text = page.read_text()
    assert text.startswith("<p>keep</p>") and text.endswith("<p>tail</p>")
    new = json.loads(gate.HANDOVER_RE.search(text).group(2))
    assert new["review"] == "partial" and new["theme"] == "Quill Press"
    names = [g["name"] for g in new["groups"]]
    assert names[0] == "Full-review definition" and names[1] == "Workflow"
    assert names[2].startswith("Review gate")
    assert new["groups"][1]["items"][0]["status"] == "pass"  # partial, but postable
    assert "ready to post: yes" in new["groups"][1]["items"][0]["note"]
    gate.write_handover(page, frag)  # idempotent: no second gate group
    again = json.loads(gate.HANDOVER_RE.search(page.read_text()).group(2))
    assert len(again["groups"]) == 3


def test_cli_exit_status(tmp_path, monkeypatch):
    notes, z, comment, ev, mirror = build(tmp_path)
    monkeypatch.setattr(gate, "fetch", stub)
    monkeypatch.setattr(gate.run_gate, "__defaults__", (stub, False))
    assert gate.main([str(notes), "--zip", str(z), "--mirror", str(mirror)]) == 0
    (ev / ("%s-msgfmt.json" % STEM)).unlink()
    assert gate.main([str(notes), "--zip", str(z), "--mirror", str(mirror)]) == 1
    assert gate.main([str(tmp_path / "nope.md")]) == 2


@pytest.mark.parametrize("text", ["None of the tier 3 checks were run.",
                                  "Nothing beyond tier 1 was checked."])
def test_not_done_sentence_starting_none_is_not_empty(tmp_path, text):
    r = run(tmp_path, not_done=text)
    assert "Not done is empty" in failed(r)


def test_handover_gate_item_fails_when_not_postable(tmp_path):
    r = run(tmp_path, evidence=False)  # partial, claims full
    frag = gate.handover_fragment(r)
    page = tmp_path / "page.html"
    data = {"groups": [{"name": "Workflow", "items": [{"label": "Review gate run", "status": "na"}]}]}
    page.write_text('<script type="application/json" id="handover-data">%s</script>' % json.dumps(data))
    gate.write_handover(page, frag)
    new = json.loads(gate.HANDOVER_RE.search(page.read_text()).group(2))
    item = new["groups"][1]["items"][0]
    assert item["status"] == "fail" and "ready to post: no" in item["note"]


# --- Pre-submission reviews (BSTD-916): the studio's own theme, no Trac ticket ---

def test_pre_submission_posting_row_is_na_and_ready_to_submit(tmp_path):
    notes, z, comment, ev, mirror = build(tmp_path, posting=False)
    r = gate.run_gate(notes, z, comment, ev, mirror, get=stub, pre_submission=True)
    row = [x for x in r["rows"] if x.group == "posting"][0]
    assert row.na and row.ok and row.line().startswith("N/A ")
    assert r["review"] == "full" and r["postable"]
    assert gate.readiness(r) == "ready to submit"


def test_pre_submission_leaves_every_other_row_alone(tmp_path):
    notes, z, comment, ev, mirror = build(tmp_path, evidence=False)
    normal = gate.run_gate(notes, z, comment, ev, mirror, get=stub)
    pre = gate.run_gate(notes, z, comment, ev, mirror, get=stub, pre_submission=True)

    def strip(res):
        return [(x.group, x.name, x.ok) for x in res["rows"] if x.group != "posting"]

    assert strip(normal) == strip(pre)
    assert pre["review"] == "partial" and not pre["postable"]  # still claims full


def test_pre_submission_handover_has_no_ticket(tmp_path):
    notes, z, comment, ev, mirror = build(tmp_path, posting=False)
    r = gate.run_gate(notes, z, comment, ev, mirror, get=stub, pre_submission=True)
    frag = gate.handover_fragment(r)
    assert frag["ticket"] == 0
    posting = [i for i in frag["groups"][1]["items"] if i["label"] == "sign-off and posting task"][0]
    assert posting["status"] == "na"
    page = tmp_path / "page.html"
    data = {"ticket": 4242, "groups": [{"name": "Workflow",
                                        "items": [{"label": "Review gate run", "status": "na"}]}]}
    page.write_text('<script type="application/json" id="handover-data">%s</script>' % json.dumps(data))
    gate.write_handover(page, frag)
    new = json.loads(gate.HANDOVER_RE.search(page.read_text()).group(2))
    assert new["ticket"] == 0
    assert "ready to submit: yes" in new["groups"][1]["items"][0]["note"]


def test_normal_review_handover_keeps_its_ticket(tmp_path):
    frag = gate.handover_fragment(run(tmp_path))
    assert "ticket" not in frag and frag["readiness"] == "ready to post"


def test_cli_pre_submission(tmp_path, monkeypatch, capsys):
    notes, z, comment, ev, mirror = build(tmp_path, posting=False)
    monkeypatch.setattr(gate.run_gate, "__defaults__", (stub, False))
    assert gate.main([str(notes), "--zip", str(z), "--mirror", str(mirror)]) == 1
    assert "ready to post: no" in capsys.readouterr().out
    assert gate.main([str(notes), "--zip", str(z), "--mirror", str(mirror), "--pre-submission"]) == 0
    out = capsys.readouterr().out
    assert "ready to submit: yes" in out and "N/A   posting" in out


def test_pre_submission_needs_no_trac_comment(tmp_path):
    rows = gate.check_claims("", tmp_path / "missing-trac-comment.txt", "partial", pre_submission=True)
    comment = [r for r in rows if r.name.startswith("comment claims")][0]
    assert comment.na and comment.ok


def test_a_missing_comment_still_fails_a_normal_review(tmp_path):
    rows = gate.check_claims("", tmp_path / "missing-trac-comment.txt", "partial")
    comment = [r for r in rows if r.name.startswith("comment claims")][0]
    assert not comment.ok and not comment.na
