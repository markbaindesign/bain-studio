import os
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import sync
from sync import (
    ProjectConfig,
    _fmt_refs,
    _fmt_task_refs,
    _extract_gids,
    _is_junk,
    _next_lid,
    _push_simple_fields,
    _push_set_field,
    _push_section,
    _task_lines,
    build_mirror,
    fetch_sections,
    fetch_tasks,
    parse_existing_mirror,
    priorities_table,
    sync_project,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def proj(tmp_path):
    p = ProjectConfig(name="Test Project", root=tmp_path, gid="proj_gid_123", prefix="TEST")
    p.claude_dir.mkdir()
    return p


@pytest.fixture
def mirror_text():
    return """\
# Bot Asana Task Mirror
Last synced: 2026-05-20
Workspace GID: 512209774840
Assignee GID: 1209202434387214

## Test Project

### TEST-001 — Fix the bug
- **Local ID:** TEST-001
- **Asana ID:** 111222333
- **Section:** DOING
- **Due:** 2026-05-25
- **Start:** none
- **Assignee:** Bot (999888777)
- **Assignee Status:** today
- **Tags:** design (tag_gid_1)
- **Followers:** Mark (follower_gid_1)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Some notes here.
- **Blockers:** None identified.
- **Progress:** Checked 2026-05-20.
- **Modified:** 2026-05-20T10:00:00
- **URL:** https://app.asana.com/0/proj/111222333

### TEST-002 — Write the docs
- **Local ID:** TEST-002
- **Asana ID:** 444555666
- **Section:** NEXT UP
- **Due:** none
- **Start:** 2026-06-01
- **Assignee:** none
- **Assignee Status:** upcoming
- **Tags:** none
- **Followers:** none
- **Dependencies:** TEST-001 (111222333)
- **Dependents:** none
- **Notes:** No notes.
- **Blockers:** Waiting on design sign-off.
- **Progress:** In progress — 50% done.
- **Modified:** 2026-05-19T08:00:00
- **URL:** https://app.asana.com/0/proj/444555666

"""


@pytest.fixture
def sample_task():
    return {
        "gid": "111222333",
        "_local_id": "TEST-001",
        "_section": "DOING",
        "_section_gid": "section_gid_doing",
        "name": "Fix the bug",
        "notes": "Some notes here.",
        "due_on": "2026-05-25",
        "due_at": None,
        "start_on": None,
        "completed": False,
        "modified_at": "2026-05-20T10:00:00.000Z",
        "permalink_url": "https://app.asana.com/0/proj/111222333",
        "assignee": {"gid": "999888777", "name": "Bot"},
        "assignee_status": "today",
        "tags": [{"gid": "tag_gid_1", "name": "design"}],
        "followers": [{"gid": "follower_gid_1", "name": "Mark"}],
        "dependencies": [],
        "dependents": [],
        "custom_fields": [{"gid": "local_id_field", "text_value": "TEST-001"}],
        "memberships": [{"project": {"gid": "proj_gid_123"}, "section": {"gid": "section_gid_doing", "name": "DOING"}}],
    }


# ---------------------------------------------------------------------------
# ProjectConfig — mirror/ids paths
# ---------------------------------------------------------------------------

def test_mirror_and_ids_paths_are_not_under_claude_dir(tmp_path):
    # Regression guard: asana-mirror.md and asana-ids.json moved out of .claude/ to the
    # project root on 2026-07-22 (ADR 011) because Claude Code hard-prompts on any write
    # under .claude/ regardless of permission mode, which broke unattended looper runs.
    # This doesn't re-test the prompt itself (there's no more .claude/ mirror to hang on)
    # — it just catches a future edit to ProjectConfig silently reverting the path.
    p = ProjectConfig(name="Test Project", root=tmp_path, gid="proj_gid_123", prefix="TEST")
    assert ".claude" not in str(p.mirror_file)
    assert ".claude" not in str(p.ids_file)
    assert p.mirror_file == tmp_path / "asana-mirror.md"
    assert p.ids_file == tmp_path / "asana-ids.json"


# ---------------------------------------------------------------------------
# _fmt_refs
# ---------------------------------------------------------------------------

def test_fmt_refs_empty():
    assert _fmt_refs([]) == "none"


def test_fmt_refs_single():
    assert _fmt_refs([{"name": "design", "gid": "123"}]) == "design (123)"


def test_fmt_refs_multiple():
    result = _fmt_refs([{"name": "a", "gid": "1"}, {"name": "b", "gid": "2"}])
    assert result == "a (1), b (2)"


# ---------------------------------------------------------------------------
# _fmt_task_refs
# ---------------------------------------------------------------------------

def test_fmt_task_refs_uses_local_id():
    result = _fmt_task_refs([{"gid": "123", "name": "Some Task"}], {"123": "PIPE-001"})
    assert result == "PIPE-001 (123)"


def test_fmt_task_refs_falls_back_to_name():
    result = _fmt_task_refs([{"gid": "999", "name": "Unknown Task"}], {})
    assert result == "Unknown Task (999)"


def test_fmt_task_refs_empty():
    assert _fmt_task_refs([], {}) == "none"


# ---------------------------------------------------------------------------
# _extract_gids
# ---------------------------------------------------------------------------

def test_extract_gids_basic():
    assert _extract_gids("design (123), client (456)") == ["123", "456"]


def test_extract_gids_none_string():
    assert _extract_gids("none") == []


def test_extract_gids_empty_string():
    assert _extract_gids("") == []


def test_extract_gids_single():
    assert _extract_gids("PIPE-001 (987654321)") == ["987654321"]


# ---------------------------------------------------------------------------
# _is_junk
# ---------------------------------------------------------------------------

def test_is_junk_emoji():
    assert _is_junk({"name": "😍 Great", "projects": []}) is True


def test_is_junk_product_update():
    assert _is_junk({"name": "[Product Update] v2", "projects": []}) is True


def test_is_junk_normal_task_with_project():
    assert _is_junk({"name": "Fix the bug", "projects": [{"gid": "1"}]}) is False


def test_is_junk_normal_task_no_project():
    assert _is_junk({"name": "Fix the bug", "projects": []}) is False


def test_is_junk_long_name_no_project():
    assert _is_junk({"name": "x" * 121, "projects": []}) is True


def test_is_junk_long_name_with_project():
    assert _is_junk({"name": "x" * 121, "projects": [{"gid": "1"}]}) is False


# ---------------------------------------------------------------------------
# _next_lid
# ---------------------------------------------------------------------------

def test_next_lid_increments():
    state = {"next_seq": 1}
    assert _next_lid(state, "MCF") == "MCF-001"
    assert _next_lid(state, "MCF") == "MCF-002"
    assert state["next_seq"] == 3


def test_next_lid_zero_pads():
    state = {"next_seq": 9}
    assert _next_lid(state, "TEST") == "TEST-009"


# ---------------------------------------------------------------------------
# parse_existing_mirror
# ---------------------------------------------------------------------------

def test_parse_existing_mirror_missing_file(proj):
    assert parse_existing_mirror(proj) == {}


def test_parse_existing_mirror_parses_tasks(proj, mirror_text):
    proj.mirror_file.write_text(mirror_text)
    carried = parse_existing_mirror(proj)

    assert "111222333" in carried
    assert "444555666" in carried

    t = carried["111222333"]
    assert t["local_id"] == "TEST-001"
    assert t["section"] == "DOING"
    assert t["due"] == "2026-05-25"
    assert t["start"] == "none"
    assert t["notes"] == "Some notes here."
    assert t["assignee"] == "Bot (999888777)"
    assert t["assignee_status"] == "today"
    assert t["tags"] == "design (tag_gid_1)"
    assert t["followers"] == "Mark (follower_gid_1)"
    assert t["dependencies"] == "none"
    assert t["blockers"] == "None identified."
    assert t["modified"] == "2026-05-20T10:00:00"


def test_parse_existing_mirror_overdue_stripped(proj, mirror_text):
    mirror_text = mirror_text.replace("2026-05-25", "2020-01-01 **(OVERDUE)**")
    proj.mirror_file.write_text(mirror_text)
    carried = parse_existing_mirror(proj)
    assert carried["111222333"]["due"] == "2020-01-01"


def test_parse_existing_mirror_preserves_blockers(proj, mirror_text):
    proj.mirror_file.write_text(mirror_text)
    carried = parse_existing_mirror(proj)
    assert carried["444555666"]["blockers"] == "Waiting on design sign-off."


def test_parse_existing_mirror_preserves_progress(proj, mirror_text):
    proj.mirror_file.write_text(mirror_text)
    carried = parse_existing_mirror(proj)
    assert carried["444555666"]["progress"] == "In progress — 50% done."


def test_parse_existing_mirror_done_section(proj, mirror_text):
    done_block = """\

## DONE

### TEST-003 — Old task
- **Local ID:** TEST-003
- **Asana ID:** 777888999
- **Section:** DONE
- **Due:** none
- **Start:** none
- **Assignee:** none
- **Assignee Status:** none
- **Tags:** none
- **Followers:** none
- **Dependencies:** none
- **Dependents:** none
- **Notes:** No notes.
- **Blockers:** None identified.
- **Progress:** Checked 2026-05-01.
- **Modified:** 2026-05-01T09:00:00
- **URL:** https://app.asana.com/0/proj/777888999

"""
    proj.mirror_file.write_text(mirror_text + done_block)
    carried = parse_existing_mirror(proj)
    assert "777888999" in carried
    assert carried["777888999"]["section"] == "DONE"


# ---------------------------------------------------------------------------
# priorities_table
# ---------------------------------------------------------------------------

def test_priorities_table_empty_when_all_done():
    tasks = [{"completed": True, "due_on": "2020-01-01", "_local_id": "T-001", "name": "Done"}]
    assert priorities_table(tasks) == ""


def test_priorities_table_shows_overdue(monkeypatch):
    monkeypatch.setattr(sync, "TODAY", "2026-05-20")
    tasks = [{"completed": False, "due_on": "2026-05-01", "_local_id": "T-001", "name": "Overdue task", "modified_at": ""}]
    result = priorities_table(tasks)
    assert "OVERDUE" in result
    assert "T-001" in result


def test_priorities_table_shows_no_due_date():
    tasks = [{"completed": False, "due_on": None, "_local_id": "T-001", "name": "No due date task", "modified_at": ""}]
    result = priorities_table(tasks)
    assert "no due date" in result


# ---------------------------------------------------------------------------
# _push_simple_fields
# ---------------------------------------------------------------------------

def test_push_simple_fields_no_changes(sample_task):
    prev = {
        "notes": "Some notes here.",
        "due": "2026-05-25",
        "start": "none",
        "assignee_status": "today",
    }
    result = _push_simple_fields(sample_task, prev, dry_run=False, prefix="TEST")
    assert result is False


def test_push_simple_fields_never_pushes_notes(sample_task):
    # Notes are mirror-read-only by design (commit 484dae2, "Stop BainBot overwriting
    # Asana task notes") — the mirror parser is single-line, so pushing notes back would
    # silently truncate any multi-line content a human wrote in Asana. A differing
    # mirror-side "notes" value must never reach the API, even when it's the only diff.
    prev = {
        "notes": "This differs from Asana and should never be pushed.",
        "due": "2026-05-25",
        "start": "none",
        "assignee": "Bot (999888777)",
        "assignee_status": "today",
    }
    with patch("sync._put") as mock_put:
        result = _push_simple_fields(sample_task, prev, dry_run=False, prefix="TEST")
    assert result is False
    mock_put.assert_not_called()


def test_push_simple_fields_due_changed(sample_task):
    prev = {
        "notes": "Some notes here.",
        "due": "2026-06-01",
        "start": "none",
        "assignee_status": "today",
    }
    with patch("sync._put") as mock_put:
        mock_put.return_value = {"data": {}}
        result = _push_simple_fields(sample_task, prev, dry_run=False, prefix="TEST")
    assert result is True
    mock_put.assert_called_once()
    assert mock_put.call_args[0][1]["data"]["due_on"] == "2026-06-01"


def test_push_simple_fields_dry_run(sample_task):
    prev = {"notes": "Different notes.", "due": "none", "start": "none", "assignee_status": "today"}
    with patch("sync._put") as mock_put:
        _push_simple_fields(sample_task, prev, dry_run=True, prefix="TEST")
    mock_put.assert_not_called()


def test_push_simple_fields_due_cleared(sample_task):
    sample_task["due_on"] = "2026-05-25"
    prev = {"notes": "Some notes here.", "due": "none", "start": "none", "assignee_status": "today"}
    with patch("sync._put") as mock_put:
        mock_put.return_value = {"data": {}}
        _push_simple_fields(sample_task, prev, dry_run=False, prefix="TEST")
    assert mock_put.call_args[0][1]["data"]["due_on"] is None


# ---------------------------------------------------------------------------
# _push_set_field
# ---------------------------------------------------------------------------

def test_push_set_field_no_changes():
    result = _push_set_field(
        "task_gid", "T-001",
        "design (tag_gid_1)", [{"gid": "tag_gid_1", "name": "design"}],
        "/tasks/{task_gid}/addTag", "/tasks/{task_gid}/removeTag", "tag",
        False, "TEST", "tags",
    )
    assert result is False


def test_push_set_field_adds_new():
    with patch("sync._post") as mock_post:
        mock_post.return_value = {"data": {}}
        result = _push_set_field(
            "task_gid", "T-001",
            "design (1001001001), urgent (1002002002)",
            [{"gid": "1001001001", "name": "design"}],
            "/tasks/{task_gid}/addTag", "/tasks/{task_gid}/removeTag", "tag",
            False, "TEST", "tags",
        )
    assert result is True
    paths = [call[0][0] for call in mock_post.call_args_list]
    assert "/tasks/task_gid/addTag" in paths


def test_push_set_field_removes_old():
    with patch("sync._post") as mock_post:
        mock_post.return_value = {"data": {}}
        _push_set_field(
            "task_gid", "T-001",
            "none",
            [{"gid": "1001001001", "name": "design"}],
            "/tasks/{task_gid}/addTag", "/tasks/{task_gid}/removeTag", "tag",
            False, "TEST", "tags",
        )
    paths = [call[0][0] for call in mock_post.call_args_list]
    assert "/tasks/task_gid/removeTag" in paths


def test_push_set_field_dry_run():
    with patch("sync._post") as mock_post:
        _push_set_field(
            "task_gid", "T-001",
            "new (new_gid)", [],
            "/tasks/{task_gid}/addTag", "/tasks/{task_gid}/removeTag", "tag",
            True, "TEST", "tags",
        )
    mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# _push_section
# ---------------------------------------------------------------------------

def test_push_section_unknown_section(sample_task):
    result = _push_section(sample_task, "NONEXISTENT", {}, dry_run=False, prefix="TEST")
    assert result is False


def test_push_section_moves_task(sample_task):
    with patch("sync._post") as mock_post, patch("sync._put") as mock_put:
        mock_post.return_value = {"data": {}}
        mock_put.return_value = {"data": {}}
        result = _push_section(sample_task, "NEXT UP", {"NEXT UP": "section_gid_next"}, dry_run=False, prefix="TEST")
    assert result is True
    mock_post.assert_called_once_with(
        "/sections/section_gid_next/addTask",
        {"data": {"task": "111222333"}},
    )
    assert sample_task["_section"] == "NEXT UP"
    mock_put.assert_not_called()


def test_push_section_to_done_completes_task(sample_task):
    with patch("sync._post") as mock_post, patch("sync._put") as mock_put:
        mock_post.return_value = {"data": {}}
        mock_put.return_value = {"data": {}}
        _push_section(sample_task, "DONE", {"DONE": "done_gid"}, dry_run=False, prefix="TEST")
    mock_put.assert_called_once_with("/tasks/111222333", {"data": {"completed": True}})
    assert sample_task["completed"] is True


def test_push_section_from_done_uncompletes_task(sample_task):
    sample_task["completed"] = True
    with patch("sync._post") as mock_post, patch("sync._put") as mock_put:
        mock_post.return_value = {"data": {}}
        mock_put.return_value = {"data": {}}
        _push_section(sample_task, "DOING", {"DOING": "doing_gid"}, dry_run=False, prefix="TEST")
    mock_put.assert_called_once_with("/tasks/111222333", {"data": {"completed": False}})
    assert sample_task["completed"] is False


def test_push_section_dry_run(sample_task):
    with patch("sync._post") as mock_post:
        _push_section(sample_task, "NEXT UP", {"NEXT UP": "gid"}, dry_run=True, prefix="TEST")
    mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# fetch_sections (mocked HTTP)
# ---------------------------------------------------------------------------

def test_fetch_sections(proj):
    with patch("sync.requests.get") as mock_get:
        resp = MagicMock()
        resp.json.return_value = {"data": [
            {"gid": "s1", "name": "DOING"},
            {"gid": "s2", "name": "NEXT UP"},
            {"gid": "s3", "name": "DONE"},
        ]}
        mock_get.return_value = resp
        sections = fetch_sections(proj)
    assert sections == {"DOING": "s1", "NEXT UP": "s2", "DONE": "s3"}


# ---------------------------------------------------------------------------
# fetch_tasks (mocked HTTP)
# ---------------------------------------------------------------------------

def test_fetch_tasks_does_not_filter_by_assignee(proj):
    # Assignee filtering was intentionally removed (commit 0a5097b, "sync all project
    # tasks, not just BainBot-assigned") — tasks pass between Mark and BainBot during the
    # workflow (Blocked -> reassigned to Mark, Review -> Mark), and filtering to bot-only
    # silently dropped a task out of the mirror the moment it got reassigned. fetch_tasks
    # must return every non-junk task in the project regardless of who it's assigned to.
    with patch("sync.requests.get") as mock_get, \
         patch.object(sync, "BAINBOT_GID", "bot_gid"):
        task_mine = {
            "gid": "t1", "name": "My task", "notes": "", "due_on": None, "due_at": None,
            "start_on": None, "completed": False, "modified_at": "2026-05-20T10:00:00.000Z",
            "permalink_url": "", "assignee": {"gid": "bot_gid", "name": "Bot"},
            "assignee_status": "today", "tags": [], "followers": [], "dependencies": [],
            "dependents": [], "custom_fields": [], "memberships": [],
        }
        task_other = {**task_mine, "gid": "t2", "assignee": {"gid": "other_user", "name": "Other"}}
        task_unassigned = {**task_mine, "gid": "t3", "assignee": None}
        resp = MagicMock()
        resp.json.return_value = {"data": [task_mine, task_other, task_unassigned]}
        mock_get.return_value = resp
        tasks = fetch_tasks(proj, "local_id_field_gid")

    assert {t["gid"] for t in tasks} == {"t1", "t2", "t3"}


def test_fetch_tasks_extracts_section(proj):
    task = {
        "gid": "t1", "name": "Task", "notes": "", "due_on": None, "due_at": None,
        "start_on": None, "completed": False, "modified_at": "2026-05-20T10:00:00.000Z",
        "permalink_url": "", "assignee": {"gid": "bot_gid", "name": "Bot"},
        "assignee_status": "today", "tags": [], "followers": [], "dependencies": [],
        "dependents": [], "custom_fields": [],
        "memberships": [
            {"project": {"gid": "proj_gid_123"}, "section": {"gid": "s1", "name": "DOING"}},
        ],
    }
    with patch("sync.requests.get") as mock_get, \
         patch.object(sync, "BAINBOT_GID", "bot_gid"):
        resp = MagicMock()
        resp.json.return_value = {"data": [task]}
        mock_get.return_value = resp
        tasks = fetch_tasks(proj, "field_gid")

    assert tasks[0]["_section"] == "DOING"
    assert tasks[0]["_section_gid"] == "s1"


def test_fetch_tasks_extracts_local_id(proj):
    task = {
        "gid": "t1", "name": "Task", "notes": "", "due_on": None, "due_at": None,
        "start_on": None, "completed": False, "modified_at": "2026-05-20T10:00:00.000Z",
        "permalink_url": "", "assignee": {"gid": "bot_gid", "name": "Bot"},
        "assignee_status": "today", "tags": [], "followers": [], "dependencies": [],
        "dependents": [], "memberships": [],
        "custom_fields": [{"gid": "field_gid", "text_value": "TEST-007"}],
    }
    with patch("sync.requests.get") as mock_get, \
         patch.object(sync, "BAINBOT_GID", "bot_gid"):
        resp = MagicMock()
        resp.json.return_value = {"data": [task]}
        mock_get.return_value = resp
        tasks = fetch_tasks(proj, "field_gid")

    assert tasks[0]["_local_id"] == "TEST-007"


# ---------------------------------------------------------------------------
# sync_project — conflict resolution
# ---------------------------------------------------------------------------

def _make_asana_responses(proj, tasks, sections):
    """Build the sequence of mock HTTP responses for a full sync_project run."""
    ids_state = {"custom_field_gid": "cf_gid", "last_synced_field_gid": "ls_gid",
                 "tasks": {}, "next_seq": 1, "posted_progress": {}}
    proj.ids_file.write_text(json.dumps(ids_state))

    task_resp = MagicMock()
    task_resp.json.return_value = {"data": tasks}
    task_resp.raise_for_status = MagicMock()

    section_resp = MagicMock()
    section_resp.json.return_value = {"data": [{"gid": g, "name": n} for n, g in sections.items()]}
    section_resp.raise_for_status = MagicMock()

    return [task_resp, section_resp]


def test_sync_project_no_push_when_asana_newer(proj, sample_task, monkeypatch):
    monkeypatch.setattr(sync, "BAINBOT_GID", "bot_gid")
    sample_task["assignee"]["gid"] = "bot_gid"

    # Write a mirror with old mtime and different section in carried
    proj.mirror_file.write_text(
        "### TEST-001 — Fix the bug\n"
        "- **Local ID:** TEST-001\n"
        "- **Asana ID:** 111222333\n"
        "- **Section:** NEXT UP\n"  # differs from Asana's DOING
        "- **Due:** 2026-05-25\n"
        "- **Start:** none\n"
        "- **Assignee:** Bot (bot_gid)\n"
        "- **Assignee Status:** today\n"
        "- **Tags:** none\n"
        "- **Followers:** none\n"
        "- **Dependencies:** none\n"
        "- **Dependents:** none\n"
        "- **Notes:** Some notes here.\n"
        "- **Blockers:** None identified.\n"
        "- **Progress:** Checked 2026-05-20.\n"
        "- **Modified:** 2026-05-20T10:00:00\n"
        "- **URL:** https://app.asana.com/0/proj/111222333\n\n"
    )
    # Make mirror older than Asana's modified_at
    old_time = datetime(2026, 5, 19, 0, 0, 0).timestamp()
    os.utime(proj.mirror_file, (old_time, old_time))

    # Asana modified_at is 2026-05-20 — newer than mirror mtime 2026-05-19
    sample_task["modified_at"] = "2026-05-20T10:00:00.000Z"

    ids_state = {"custom_field_gid": "cf_gid", "last_synced_field_gid": "ls_gid",
                 "tasks": {"111222333": "TEST-001"}, "next_seq": 2, "posted_progress": {}}
    proj.ids_file.write_text(json.dumps(ids_state))

    put_calls = []
    post_calls = []

    with patch("sync.requests.get") as mock_get, \
         patch("sync.requests.put") as mock_put, \
         patch("sync.requests.post") as mock_post:

        task_resp = MagicMock()
        task_resp.json.return_value = {"data": [sample_task]}
        task_resp.raise_for_status = MagicMock()
        section_resp = MagicMock()
        section_resp.json.return_value = {"data": [{"gid": "s1", "name": "DOING"}, {"gid": "s2", "name": "NEXT UP"}]}
        section_resp.raise_for_status = MagicMock()
        mock_get.side_effect = [task_resp, section_resp]

        put_resp = MagicMock()
        put_resp.json.return_value = {"data": {}}
        put_resp.raise_for_status = MagicMock()
        mock_put.return_value = put_resp

        sync_project(proj, dry_run=False)

        # No PUT at all should have fired: no field pushes because Asana is
        # newer, and no Last Synced stamp because the task is neither new nor
        # written to. Idle tasks are left completely untouched so they stop
        # accreting one Asana activity story per sync run.
        put_paths = [call[0][0] for call in mock_put.call_args_list]
        assert put_paths == []
        # No section move POST should have fired
        post_paths = [call[0][0] for call in mock_post.call_args_list]
        assert not any("addTask" in p for p in post_paths)


# ---------------------------------------------------------------------------
# Story paging and comment dedupe
# ---------------------------------------------------------------------------

def _story(subtype, gid, name, text, created="2026-08-24T09:00:00.000Z"):
    return {
        "resource_subtype": subtype,
        "created_by": {"gid": gid, "name": name},
        "text": text,
        "created_at": created,
    }


def test_fetch_stories_pages_past_the_first_page(monkeypatch):
    """Asana serves stories oldest-first with no reverse ordering, so a human
    comment on a busy task lands on a later page. Reading only page 1 made
    sync.py miss re-queue instructions entirely (PIPE-028, 2026-08)."""
    page1 = {
        "data": [_story("text_custom_field_changed", "bot_gid", "BainBot", "")
                 for _ in range(sync.COMMENT_PAGE_LIMIT)],
        "next_page": {"offset": "page2"},
    }
    page2 = {
        "data": [_story("comment_added", "human_gid", "Mark Bain", "merge branch")],
        "next_page": None,
    }
    calls = []

    def fake_get(path, params=None):
        calls.append((params or {}).get("offset"))
        return page1 if len(calls) == 1 else page2

    monkeypatch.setattr(sync, "_get", fake_get)

    stories = sync.fetch_stories("111")
    assert calls == [None, "page2"]
    assert len(stories) == sync.COMMENT_PAGE_LIMIT + 1

    comments = sync.human_comments(stories)
    assert [c["text"] for c in comments] == ["merge branch"]


def test_fetch_stories_stops_at_page_cap(monkeypatch):
    """A task whose stories never stop paging must not spin forever."""
    monkeypatch.setattr(
        sync, "_get",
        lambda path, params=None: {"data": [], "next_page": {"offset": "more"}},
    )
    with patch.object(sync, "COMMENT_MAX_PAGES", 3):
        sync.fetch_stories("111")


def test_human_comments_keeps_only_the_most_recent(monkeypatch):
    stories = [
        _story("comment_added", "human_gid", "Mark Bain", f"note {i}")
        for i in range(sync.COMMENT_KEEP + 5)
    ]
    texts = [c["text"] for c in sync.human_comments(stories)]
    assert len(texts) == sync.COMMENT_KEEP
    assert texts[-1] == f"note {sync.COMMENT_KEEP + 4}"


def test_bot_comment_texts_separates_bot_from_human(monkeypatch):
    """The bot's own comments are excluded from the mirror but collected for
    dedupe: a task multi-homed into its home board and Studio Looper is synced
    once per project, each with its own posted_progress state, so only Asana's
    story list can tell the second sync the comment already exists."""
    monkeypatch.setattr(sync, "BAINBOT_GID", "bot_gid")
    stories = [
        _story("comment_added", "bot_gid", "BainBot", "Blocked 2026-08-25. Research findings missing."),
        _story("comment_added", "human_gid", "Mark Bain", "where is it?"),
        _story("assigned", "bot_gid", "BainBot", "assigned to Mark"),
    ]
    assert sync.bot_comment_texts(stories) == {"Blocked 2026-08-25. Research findings missing."}
    assert [c["text"] for c in sync.human_comments(stories)] == ["where is it?"]
