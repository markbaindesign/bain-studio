import os
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import sync
from sync import (
    ProjectConfig,
    assign_ids,
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
    create_subtasks,
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
# assign_ids - adopted IDs and the counter
# ---------------------------------------------------------------------------

def _task(gid, local_id=""):
    return {"gid": gid, "name": f"task {gid}", "_local_id": local_id}


def test_assign_ids_adopted_id_moves_counter_past_it(proj):
    state = {"next_seq": 1, "tasks": {}}
    tasks = [_task("1", "TEST-012")]
    assign_ids(proj, tasks, state, "field_gid", dry_run=True)
    assert state["tasks"]["1"] == "TEST-012"
    assert state["next_seq"] == 13


def test_assign_ids_new_task_after_adopted_id_does_not_collide(proj):
    state = {"next_seq": 1, "tasks": {}}
    tasks = [_task("1", "TEST-005"), _task("2")]
    assign_ids(proj, tasks, state, "field_gid", dry_run=True)
    assert tasks[1]["_local_id"] == "TEST-006"


def test_assign_ids_adopted_id_below_counter_leaves_it_alone(proj):
    state = {"next_seq": 20, "tasks": {}}
    assign_ids(proj, [_task("1", "TEST-003")], state, "field_gid", dry_run=True)
    assert state["next_seq"] == 20


def test_assign_ids_new_task_listed_before_adopted_id_does_not_collide(proj):
    state = {"next_seq": 1, "tasks": {}}
    tasks = [_task("2"), _task("1", "TEST-001")]
    assign_ids(proj, tasks, state, "field_gid", dry_run=True)
    ids = [t["_local_id"] for t in tasks]
    assert len(set(ids)) == 2, ids


# ---------------------------------------------------------------------------
# assign_ids - multi-homed tasks keep the ID of the project they still belong to
# ---------------------------------------------------------------------------

def _homed_task(gid, local_id, *project_gids):
    return {"gid": gid, "name": f"task {gid}", "_local_id": local_id,
            "memberships": [{"project": {"gid": g}} for g in project_gids]}


def test_assign_ids_keeps_foreign_id_while_task_is_still_in_owning_project(proj):
    # KF-WEB-239 is in both KF (owner) and this project: syncing this project must not
    # re-home it, or KF and this project hand it a new ID on every run (BSTD 2026-10-20).
    state = {"next_seq": 1, "tasks": {}}
    tasks = [_homed_task("1", "KF-WEB-239", "kf_gid", proj.gid)]
    assign_ids(proj, tasks, state, "field_gid", dry_run=True, prefix_owners={"KF-WEB": "kf_gid"})
    assert tasks[0]["_local_id"] == "KF-WEB-239"
    assert state["tasks"]["1"] == "KF-WEB-239"
    assert state["next_seq"] == 1


def test_assign_ids_rehomes_foreign_id_once_task_has_left_owning_project(proj):
    state = {"next_seq": 1, "tasks": {}}
    tasks = [_homed_task("1", "KF-WEB-239", proj.gid)]
    assign_ids(proj, tasks, state, "field_gid", dry_run=True, prefix_owners={"KF-WEB": "kf_gid"})
    assert tasks[0]["_local_id"] == "TEST-001"


def test_assign_ids_rehomes_id_from_unknown_prefix(proj):
    state = {"next_seq": 1, "tasks": {}}
    tasks = [_homed_task("1", "GONE-007", "gone_gid", proj.gid)]
    assign_ids(proj, tasks, state, "field_gid", dry_run=True, prefix_owners={"KF-WEB": "kf_gid"})
    assert tasks[0]["_local_id"] == "TEST-001"


def test_assign_ids_without_prefix_owners_keeps_old_rehoming(proj):
    state = {"next_seq": 1, "tasks": {}}
    tasks = [_homed_task("1", "KF-WEB-239", "kf_gid", proj.gid)]
    assign_ids(proj, tasks, state, "field_gid", dry_run=True)
    assert tasks[0]["_local_id"] == "TEST-001"


def test_prefix_owners_skips_aggregators_and_includes_paused(tmp_path, monkeypatch):
    # Looper-created tasks (SL-NNN) must still re-home into a real project, so aggregators
    # never count as owners; a paused project still owns its prefix.
    def project(name, gid, prefix, extra=""):
        root = tmp_path / name
        root.mkdir()
        (root / "CLAUDE.md").write_text(
            f"ASANA_PROJECT_GID: {gid}\nASANA_TASK_PREFIX: {prefix}\n{extra}")
        return root
    registry = [
        {"path": str(project("kf", "kf_gid", "KF-WEB")), "status": "active"},
        {"path": str(project("asp", "asp_gid", "ASP")), "status": "paused"},
        {"path": str(project("sl", "sl_gid", "SL", "PRESERVE_FOREIGN_IDS: true\n")), "status": "active"},
    ]
    monkeypatch.setattr(sync, "load_projects_registry", lambda: registry)
    assert sync.prefix_owners() == {"KF-WEB": "kf_gid", "ASP": "asp_gid"}



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


# ---------------------------------------------------------------------------
# --get-task
# ---------------------------------------------------------------------------

def _registry(tmp_path, monkeypatch, projects):
    """projects: {dirname: {gid: local_id}}"""
    entries = []
    for name, tasks in projects.items():
        d = tmp_path / name
        d.mkdir()
        (d / "asana-ids.json").write_text(json.dumps({"tasks": tasks, "posted_progress": {"9": "Blocked 2026-08-25"}}))
        entries.append({"path": str(d), "status": "archived"})
    reg = tmp_path / "projects.json"
    reg.write_text(json.dumps(entries))
    monkeypatch.setattr(sync, "PROJECTS_FILE", reg)


def test_resolve_task_ref_url_gid_and_local_id(tmp_path, monkeypatch):
    _registry(tmp_path, monkeypatch, {"bd": {"1217094791482756": "BD-152"}})
    assert sync.resolve_task_ref("https://app.asana.com/1/512209774840/task/1217094791482756?focus=true") == "1217094791482756"
    assert sync.resolve_task_ref("https://app.asana.com/1/512/project/99/task/42") == "42"
    assert sync.resolve_task_ref(" 1217094791482756 ") == "1217094791482756"
    assert sync.resolve_task_ref("bd-152") == "1217094791482756"
    assert sync.resolve_task_ref("BD-999") is None
    assert sync.resolve_task_ref("nonsense") is None


def test_local_id_maps_includes_archived_and_ignores_non_ids(tmp_path, monkeypatch):
    _registry(tmp_path, monkeypatch, {"a": {"1": "KF-WEB-005"}, "b": {"2": "PIPE-063", "3": "garbage"}})
    gid_to_lid, lid_to_gid = sync._local_id_maps()
    assert gid_to_lid == {"1": "KF-WEB-005", "2": "PIPE-063"}
    assert lid_to_gid["KF-WEB-005"] == "1"


def test_format_task_includes_notes_bot_comments_and_local_id(monkeypatch):
    monkeypatch.setattr(sync, "LOOPER_STATUS_FIELD_GID", "ls_gid")
    task = {"gid": "7", "name": "Perf audit", "notes": "See roadmap", "completed": True,
            "projects": [{"name": "BDW"}], "assignee": {"name": "Mark"},
            "custom_fields": [{"gid": "ls_gid", "display_value": "Blocked"}],
            "permalink_url": "https://x/7"}
    stories = [
        {"resource_subtype": "comment_added", "text": "Blocked: file missing", "created_at": "2026-08-25T10:00",
         "created_by": {"gid": sync.BAINBOT_GID, "name": "BainBot"}},
        {"resource_subtype": "assigned", "text": "assigned to Mark"},
    ]
    out = sync.format_task(task, stories, {"7": "BD-152"})
    assert "### BD-152 — Perf audit" in out
    assert "**Completed:** yes" in out
    assert "**Looper Status:** Blocked" in out
    assert "See roadmap" in out
    assert "BainBot: Blocked: file missing" in out
    assert "assigned to Mark" not in out


def test_get_task_reports_unresolvable_ref(tmp_path, monkeypatch, capsys):
    _registry(tmp_path, monkeypatch, {})
    assert sync.get_task("BD-404") == 1
    assert "could not resolve" in capsys.readouterr().err


def test_get_task_reports_http_error(tmp_path, monkeypatch, capsys):
    _registry(tmp_path, monkeypatch, {})
    resp = MagicMock(status_code=404)
    def boom(*a, **k):
        raise sync.requests.HTTPError(response=resp)
    monkeypatch.setattr(sync, "_get", boom)
    assert sync.get_task("123") == 1
    assert "HTTP 404" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# create_subtasks
# ---------------------------------------------------------------------------

def test_create_subtasks_posts_in_order_and_returns_gids():
    with patch("sync._post") as mock_post:
        mock_post.side_effect = [{"data": {"gid": "s1"}}, {"data": {"gid": "s2"}}, {"data": {"gid": "s3"}}]
        gids = create_subtasks("parent_gid", ["first", "second", "third"])
    assert gids == ["s1", "s2", "s3"]
    assert [c[0][0] for c in mock_post.call_args_list] == ["/tasks/parent_gid/subtasks"] * 3
    assert [c[0][1] for c in mock_post.call_args_list] == [
        {"data": {"name": "first"}}, {"data": {"name": "second"}}, {"data": {"name": "third"}},
    ]


def test_create_subtasks_dry_run_posts_nothing():
    with patch("sync._post") as mock_post:
        gids = create_subtasks("parent_gid", ["a", "b"], dry_run=True)
    mock_post.assert_not_called()
    assert len(gids) == 2


def test_create_subtasks_no_names_posts_nothing():
    with patch("sync._post") as mock_post:
        assert create_subtasks("parent_gid", []) == []
    mock_post.assert_not_called()


def _run_main(monkeypatch, *argv):
    # main() bails with exit 2 before reaching any command if the Asana settings are
    # missing, so give it dummies - otherwise these tests depend on the developer's .env
    monkeypatch.setattr(sync, "ASANA_PAT", "pat")
    monkeypatch.setattr(sync, "WORKSPACE_GID", "ws_gid")
    monkeypatch.setattr(sync, "BAINBOT_GID", "bot_gid")
    with patch("sys.argv", ["sync.py", *argv]):
        with pytest.raises(SystemExit) as exc:
            sync.main()
    return exc.value.code


def test_cli_create_subtask_requires_task_gid(monkeypatch, capsys):
    with patch("sync.create_subtasks") as mock_create:
        assert _run_main(monkeypatch, "--create-subtask", "--subtask-name", "A") == 2
    assert "--create-subtask requires --task-gid" in capsys.readouterr().err
    mock_create.assert_not_called()


def test_cli_create_subtask_requires_a_name(monkeypatch, capsys):
    with patch("sync.create_subtasks") as mock_create:
        assert _run_main(monkeypatch, "--create-subtask", "--task-gid", "123") == 2
    assert "--create-subtask requires at least one --subtask-name" in capsys.readouterr().err
    mock_create.assert_not_called()


def test_cli_create_subtask_passes_names_in_order_and_prints_gids(monkeypatch, capsys):
    with patch("sync.create_subtasks", return_value=["s1", "s2"]) as mock_create:
        code = _run_main(monkeypatch, "--create-subtask", "--task-gid", "123",
                         "--subtask-name", "B", "--subtask-name", "A")
    assert code == 0
    mock_create.assert_called_once_with("123", ["B", "A"], dry_run=False)
    assert capsys.readouterr().out.split() == ["s1", "s2"]


# ---------------------------------------------------------------------------
# Pagination and follower flip-flop (NORE, 2026-09-24)
# ---------------------------------------------------------------------------

def test_fetch_tasks_follows_next_page(proj):
    def page(n, more):
        return {"data": [{"gid": f"{n}-{i}", "name": "t", "memberships": [],
                          "custom_fields": []} for i in range(2)],
                "next_page": {"offset": "o%d" % n} if more else None}
    pages = [page(1, True), page(2, False)]
    with patch("sync._get", side_effect=pages) as get:
        tasks = fetch_tasks(proj, "field")
    assert [t["gid"] for t in tasks] == ["1-0", "1-1", "2-0", "2-1"]
    assert get.call_args_list[1].args[1]["offset"] == "o1"


def test_push_set_field_updates_task_to_post_push_state():
    """The mirror is rebuilt from the task after a push, so it must reflect it."""
    task = {"followers": [{"gid": "1", "name": "Me"}, {"gid": "2", "name": "BainBot"}]}
    with patch("sync._post"):
        changed = _push_set_field(
            "t", "T-1", "Me (1)", task["followers"], "/add", "/remove", "follower",
            False, "T", "followers", task=task, task_key="followers")
    assert changed
    assert [f["gid"] for f in task["followers"]] == ["1"]


def test_push_set_field_adds_carry_the_mirror_name():
    task = {"followers": []}
    with patch("sync._post"):
        _push_set_field("t", "T-1", "BainBot (2)", [], "/add", "/remove",
                        "follower", False, "T", "followers",
                        task=task, task_key="followers")
    assert task["followers"] == [{"gid": "2", "name": "BainBot"}]


def test_push_set_field_failed_write_is_not_recorded():
    task = {"followers": [{"gid": "2", "name": "BainBot"}]}
    with patch("sync._post", side_effect=RuntimeError("no")):
        _push_set_field("t", "T-1", "none", task["followers"], "/add",
                        "/remove", "follower", False, "T", "followers",
                        task=task, task_key="followers")
    assert [f["gid"] for f in task["followers"]] == ["2"]


# ---------------------------------------------------------------------------
# create_task_full: assignee and dependency (BSTD-819)
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_asana(monkeypatch, proj):
    """Record Asana writes made by create_task_full; the task gets gid new_gid."""
    proj.mirror_file.write_text("# Bot Asana Task Mirror\n\n## Test Project\n")
    posts, puts = [], []

    def fake_post(path, body):
        posts.append((path, body))
        return {"data": {"gid": "new_gid"}}

    monkeypatch.setattr(sync, "fetch_sections", lambda p: {"NEXT UP": "sec_gid"})
    monkeypatch.setattr(sync, "_post", fake_post)
    monkeypatch.setattr(sync, "_put", lambda path, body: puts.append((path, body)))
    monkeypatch.setattr(sync, "_get", lambda path, params=None: {"data": {"name": "Mark Bain"}})
    monkeypatch.setattr(sync, "BAINBOT_GID", "bot_gid")
    return posts


def test_create_task_full_defaults_to_bainbot(proj, fake_asana):
    sync.create_task_full(proj, "Do it")
    assert fake_asana[0][0] == "/tasks"
    assert fake_asana[0][1]["data"]["assignee"] == "bot_gid"
    assert not any("addDependencies" in path for path, _ in fake_asana)


def test_create_task_full_assignee_and_dependency(proj, fake_asana):
    lid = sync.create_task_full(proj, "Do it", assignee="mark_gid", depends_on="blocked_gid")
    assert fake_asana[0][1]["data"]["assignee"] == "mark_gid"
    assert ("/tasks/blocked_gid/addDependencies",
            {"data": {"dependencies": ["new_gid"]}}) in fake_asana
    block = proj.mirror_file.read_text().split(f"### {lid} ")[1]
    assert "- **Assignee:** Mark Bain (mark_gid)" in block
    assert "- **Dependents:** blocked_gid (blocked_gid)" in block


def test_create_task_full_dependency_failure_is_loud(proj, fake_asana, monkeypatch):
    real_post = sync._post

    def failing_post(path, body):
        if "addDependencies" in path:
            raise Exception("403")
        return real_post(path, body)

    monkeypatch.setattr(sync, "_post", failing_post)
    with pytest.raises(RuntimeError, match="could not make it block blocked_gid"):
        sync.create_task_full(proj, "Do it", depends_on="blocked_gid")


# ---------------------------------------------------------------------------
# assign_ids - tasks carrying another project's ID
# ---------------------------------------------------------------------------

def _homed(gid, local_id, *project_gids):
    t = _task(gid, local_id)
    t["memberships"] = [{"project": {"gid": g}} for g in project_gids]
    return t


def test_assign_ids_multihomed_task_keeps_issuing_projects_id(proj):
    state = {"next_seq": 40, "tasks": {"1": "TEST-031"}}
    tasks = [_homed("1", "OTHER-007", "proj_gid_123", "other_gid")]
    assign_ids(proj, tasks, state, "field_gid", dry_run=True,
               prefix_owners={"TEST": "proj_gid_123", "OTHER": "other_gid"})
    assert tasks[0]["_local_id"] == "OTHER-007"
    assert state["tasks"]["1"] == "OTHER-007"
    assert state["next_seq"] == 40


def test_assign_ids_task_moved_out_of_issuing_project_is_rehomed(proj):
    state = {"next_seq": 40, "tasks": {}}
    tasks = [_homed("1", "OTHER-007", "proj_gid_123")]
    assign_ids(proj, tasks, state, "field_gid", dry_run=True,
               prefix_owners={"TEST": "proj_gid_123", "OTHER": "other_gid"})
    assert tasks[0]["_local_id"] == "TEST-040"


def test_assign_ids_unregistered_prefix_is_rehomed(proj):
    state = {"next_seq": 40, "tasks": {}}
    tasks = [_homed("1", "GONE-007", "proj_gid_123", "gone_gid")]
    assign_ids(proj, tasks, state, "field_gid", dry_run=True,
               prefix_owners={"TEST": "proj_gid_123"})
    assert tasks[0]["_local_id"] == "TEST-040"


def test_assign_ids_multihomed_pair_stops_flipping(tmp_path):
    a = ProjectConfig(name="A", root=tmp_path / "a", gid="a_gid", prefix="KF-WEB")
    b = ProjectConfig(name="B", root=tmp_path / "b", gid="b_gid", prefix="TARA")
    prefix_gids = {"KF-WEB": "a_gid", "TARA": "b_gid"}
    task = _homed("1", "TARA-134", "a_gid", "b_gid")
    for _ in range(3):
        for p in (a, b):
            t = dict(task)
            assign_ids(p, [t], {"next_seq": 500, "tasks": {}}, "f", dry_run=True,
                       prefix_owners=prefix_gids)
            assert t["_local_id"] == "TARA-134"


# ---------------------------------------------------------------------------
# Review comment rendering (looper review notes)
# ---------------------------------------------------------------------------

REVIEW_NOTE = (
    "@mark Review: header & nav fix || "
    "Where: looper/a3f2c1 · 2252ad1 || "
    "Check: || 1. Resize 375px -> 1400px || 2. [menu] toggle at <1000px || "
    "Gaps: 320px only — hero overflows 7px"
)


def test_progress_plain_expands_block_separator_and_strips_mention():
    plain = sync._progress_plain(REVIEW_NOTE)
    lines = plain.split("\n")
    assert lines[0] == "Review: header & nav fix"
    assert lines[1] == "Where: looper/a3f2c1 · 2252ad1"
    assert lines[-1] == "Gaps: 320px only — hero overflows 7px"
    assert "||" not in plain
    assert "@mark" not in plain


def test_render_progress_adds_mention_and_escapes_html():
    with patch.object(sync, "USER_GID", "507443625075"):
        html, wants = sync._render_progress(REVIEW_NOTE)
    assert wants is True
    assert html.startswith('<body><a data-asana-gid="507443625075"/> ')
    assert html.endswith("</body>")
    # Asana rejects bare &, < and > in html_text with a 400.
    assert "&amp;" in html and "&lt;1000px" in html and "-&gt;" in html
    assert "<menu>" not in html


def test_render_progress_leaves_quotes_and_apostrophes_alone():
    # Asana does not decode the numeric entity Python emits for an apostrophe:
    # escaping quotes put a literal "&#x27;" in the comment (verified against
    # SLT-001, 2026-11-05). Only & < > may be escaped.
    html, _ = sync._render_progress("""Review: Mark's "quoted" & <tag> test""")
    assert "&#x27;" not in html and "&quot;" not in html
    assert "Mark's" in html and '"quoted"' in html
    assert "&amp;" in html and "&lt;tag&gt;" in html


def test_render_progress_without_token_posts_no_mention():
    # Mark's Asana inbox is filtered to "Mentioned": a note without the token
    # must still post, but it must NOT mention him.
    html, wants = sync._render_progress("Checked 2026-11-05.")
    assert wants is False
    assert "data-asana-gid" not in html
    assert html == "<body>Checked 2026-11-05.</body>"


def test_render_progress_empty_note_renders_nothing():
    assert sync._render_progress("") == (None, False)
    assert sync._render_progress("   ") == (None, False)


def test_comment_matches_ignores_asanas_rendered_mention():
    # Asana returns the mention as a display name, so the posted comment never
    # equals the mirror text that produced it. Matching is by suffix.
    plain = sync._progress_plain(REVIEW_NOTE)
    assert sync._comment_matches("@Mark Bain " + plain, plain)
    assert sync._comment_matches(plain, plain)
    assert not sync._comment_matches("@Mark Bain Review: something else", plain)
    assert not sync._comment_matches(plain, "")


def test_leave_progress_comment_edits_existing_story_in_place():
    with patch.object(sync, "_put") as put, patch.object(sync, "_post") as post:
        got = sync.leave_progress_comment("TASK1", REVIEW_NOTE, story_gid="STORY9")
    assert got == "STORY9"
    put.assert_called_once()
    assert put.call_args[0][0] == "/stories/STORY9"
    assert "html_text" in put.call_args[0][1]["data"]
    post.assert_not_called()


def test_leave_progress_comment_falls_back_to_new_post_when_edit_fails():
    # A deleted or foreign story must not swallow the note.
    with patch.object(sync, "_put", side_effect=RuntimeError("404")), \
         patch.object(sync, "_post", return_value={"data": {"gid": "NEW1"}}) as post:
        got = sync.leave_progress_comment("TASK1", REVIEW_NOTE, story_gid="GONE")
    assert got == "NEW1"
    assert post.call_args[0][0] == "/tasks/TASK1/stories"


def test_bot_comment_stories_returns_gid_and_timestamp():
    stories = [
        {"resource_subtype": "comment_added", "gid": "S1", "text": " hello ",
         "created_at": "2026-11-05T10:00:00.000Z",
         "created_by": {"gid": sync.BAINBOT_GID}},
        {"resource_subtype": "comment_added", "gid": "S2", "text": "from Mark",
         "created_at": "2026-11-05T11:00:00.000Z", "created_by": {"gid": "999"}},
        {"resource_subtype": "assigned", "gid": "S3",
         "created_by": {"gid": sync.BAINBOT_GID}},
    ]
    got = sync.bot_comment_stories(stories)
    assert got == [{"gid": "S1", "text": "hello",
                    "created_at": "2026-11-05T10:00:00.000Z"}]


def test_comment_matches_rejects_a_tail_of_a_longer_comment():
    # A short note that happens to be the tail of an older, longer comment is
    # not a duplicate of it — only a rendered mention may precede the body.
    older = ("Review: header fix\nWhere: looper/a3f2c1\n"
             + "x" * 200 + "\nGaps: 320px only")
    assert not sync._comment_matches(older, "Gaps: 320px only")


# ---------------------------------------------------------------------------
# Note validation — a wall of text is not posted at all
# ---------------------------------------------------------------------------

# The comment that prompted all of this, from a real bain.design session.
REAL_WALL = (
    "Correction 2026-11-05, replacing my earlier note, which contradicted itself "
    "and was based on a scan of three pages. Commits 2252ad1 and 38cf615. The "
    "clients index itself was already responsive; the sideways scroll came from "
    "the site header, which only fits on one line from 1000px up. Below that it "
    "wrapped to two and three lines, and under about 720px the nav ran past the "
    "page edge, so every template scrolled sideways between 641px and 720px."
)


def test_validate_rejects_the_wall_of_text_that_prompted_this():
    assert "200-char limit" in sync.validate_progress_note(REAL_WALL)


def test_validate_passes_a_templated_review_note():
    assert sync.validate_progress_note(REVIEW_NOTE) == ""


def test_validate_passes_heartbeats_and_short_free_form_notes():
    # Other skills (studio-delivery-gate, feature, end-session) write their own
    # short formats. A note under every limit passes whatever its shape.
    assert sync.validate_progress_note("Checked 2026-11-05.") == ""
    assert sync.validate_progress_note("") == ""
    assert sync.validate_progress_note(
        "Blocked 2026-11-05. Gravity Forms licence key missing.") == ""


def test_validate_rejects_too_many_blocks():
    note = "@mark Review 2026-11-05: x || " + " || ".join(
        f"{i}. do a thing" for i in range(1, 10))
    assert "block limit" in sync.validate_progress_note(note)


def test_validate_rejects_an_overlong_note_under_the_block_limit():
    note = " || ".join(["x" * 150] * 7)   # each block legal, total is not
    assert "exceeds the 900-char limit" in sync.validate_progress_note(note)


# ---------------------------------------------------------------------------
# Task descriptions — a wall of text is not written at all (BSTD-864)
# ---------------------------------------------------------------------------

# Trimmed from BSTD-856's real description: the brief, then a history of how the
# problem arose, which is what the limit exists to keep out of a task.
REAL_DESCRIPTION_WALL = (
    "brand-voice.md is the single source of truth for all writing rules and it is "
    "not in version control. It lives in Dropbox at Work/Content/Brand Voice/.\n\n"
    "Why it matters now: on 2026-11-04 it went from 1,618 to ~3,890 words in one "
    "session - typography.md folded in, the VOICE DNA doc folded in, the "
    "passive-voice rule rewritten, the paragraph-length rule removed, rules added "
    "from Wikipedia Signs of AI writing, and seven words taken off the banned "
    "list. Dropbox has file history but no commit log, no diff and no message "
    "explaining any of it.\n\n" + "Padding that stands in for the rest of it. " * 20
)


def test_description_limit_rejects_the_wall_of_text_that_prompted_this():
    assert len(REAL_DESCRIPTION_WALL) > sync.DESCRIPTION_MAX_CHARS
    assert "over the 1200-char limit" in sync.validate_task_description(REAL_DESCRIPTION_WALL)


def test_description_limit_passes_a_normal_description():
    # The studio median is ~500 chars; the limit must not bite one of those.
    assert sync.validate_task_description("x" * 500) == ""
    assert sync.validate_task_description("") == ""
    assert sync.validate_task_description(None) == ""
    assert sync.validate_task_description(
        "Severity: Medium | Area: Contact form\n\n"
        "The partner enquiry form redirects to the thank-you page for the wrong "
        "form.\n\nScreenshot: /home/bain/Pictures/shot.png") == ""


def test_create_task_full_refuses_an_overlong_description_before_any_write(proj, fake_asana):
    with pytest.raises(ValueError, match="over the 1200-char limit"):
        sync.create_task_full(proj, "Do it", notes=REAL_DESCRIPTION_WALL)
    assert fake_asana == []   # nothing reached Asana


def test_create_task_refuses_an_overlong_description(proj, fake_asana):
    with pytest.raises(ValueError, match="over the 1200-char limit"):
        sync.create_task("proj_gid_123", "Do it", notes=REAL_DESCRIPTION_WALL)
    assert fake_asana == []


def test_update_task_refuses_a_description_no_shorter_than_the_one_it_replaces(monkeypatch):
    puts = []
    monkeypatch.setattr(sync, "_put", lambda path, body: puts.append((path, body)))
    monkeypatch.setattr(sync, "_get", lambda path, params=None: {"data": {"notes": "Short."}})
    with pytest.raises(ValueError, match="over the 1200-char limit"):
        sync.update_task("111222333", notes=REAL_DESCRIPTION_WALL)
    assert puts == []


def test_update_task_allows_an_overlong_but_shorter_correction(monkeypatch):
    # The escape hatch: a wrong 3,500-char description must be correctable to
    # 1,400 chars, even though 1,400 is over the limit. Refusing that would
    # leave the misleading text in place, which is the opposite of the point.
    puts = []
    monkeypatch.setattr(sync, "_put", lambda path, body: puts.append((path, body)))
    monkeypatch.setattr(sync, "_get",
                        lambda path, params=None: {"data": {"notes": "x" * 3500}})
    sync.update_task("111222333", notes="y" * 1400)
    assert puts[0][1]["data"]["notes"] == "y" * 1400


def test_dry_run_still_refuses_an_overlong_description(proj, fake_asana):
    # A caller must be able to find out with --dry-run that the description fails.
    with pytest.raises(ValueError):
        sync.create_task_full(proj, "Do it", notes=REAL_DESCRIPTION_WALL, dry_run=True)


def test_update_task_allows_a_short_description(monkeypatch):
    puts = []
    monkeypatch.setattr(sync, "_put", lambda path, body: puts.append((path, body)))
    sync.update_task("111222333", notes="Corrected: the form redirects to /thanks.")
    assert puts[0][1]["data"]["notes"].startswith("Corrected:")


# ---------------------------------------------------------------------------
# Descriptions stay read-only in the mirror, but an edit is not swallowed
# ---------------------------------------------------------------------------

def test_mirror_description_edit_is_not_pushed_but_is_reported(sample_task, caplog):
    prev = {"notes": "Rewritten in the mirror.", "due": "2026-05-25", "start": "none",
            "assignee": "Bot (999888777)", "assignee_status": "today"}
    with caplog.at_level("WARNING"):
        pushed = _push_simple_fields(sample_task, prev, dry_run=True, prefix="TEST")
    assert pushed is False
    assert "description edited in the mirror" in caplog.text
    assert "--update-task" in caplog.text


def test_unedited_description_is_silent(sample_task, caplog):
    prev = {"notes": "Some notes here.", "due": "2026-05-25", "start": "none",
            "assignee": "Bot (999888777)", "assignee_status": "today"}
    with caplog.at_level("WARNING"):
        _push_simple_fields(sample_task, prev, dry_run=True, prefix="TEST")
    assert "description edited" not in caplog.text


# ---------------------------------------------------------------------------
# Generic custom fields — mirrored and pushed by name
# ---------------------------------------------------------------------------

def _cf_priority(value=None):
    return {
        "gid": "1155368350785978", "name": "Priority", "resource_subtype": "enum",
        "enum_value": {"gid": "1155368350785979", "name": value} if value else None,
        "enum_options": [
            {"gid": "1155368350785979", "name": "High"},
            {"gid": "1155368350785980", "name": "Medium"},
            {"gid": "1155368350785981", "name": "Low"},
        ],
    }


def _cf_features(*values):
    opts = [
        {"gid": "1216075949558841", "name": "Greenhouse"},
        {"gid": "1220254742605531", "name": "Security"},
        {"gid": "1216075949558848", "name": "Dev Ops"},
    ]
    by_name = {o["name"]: o for o in opts}
    return {
        "gid": "1215208851588973", "name": "Features", "resource_subtype": "multi_enum",
        "multi_enum_values": [by_name[v] for v in values],
        "enum_options": opts,
    }


@pytest.fixture
def cf_env(monkeypatch):
    monkeypatch.setattr(sync, "PRIORITY_FIELD_GID", "1155368350785978")
    monkeypatch.setattr(sync, "LOOPER_STATUS_FIELD_GID", "looper_field")
    monkeypatch.setattr(sync, "SHARED_FIELD_GID", "local_id_field")
    monkeypatch.setattr(sync, "LAST_SYNCED_FIELD_GID", "last_synced_field")
    monkeypatch.setattr(sync, "_ENUM_OPTIONS", {})
    monkeypatch.setattr(sync, "_FIELD_WARNED", set())


def test_cf_mirror_value_covers_every_value_shape():
    assert sync._cf_mirror_value(_cf_priority("High")) == "High"
    assert sync._cf_mirror_value(_cf_priority()) == "none"
    assert sync._cf_mirror_value(_cf_features("Greenhouse", "Security")) == "Greenhouse, Security"
    assert sync._cf_mirror_value(_cf_features()) == "none"
    assert sync._cf_mirror_value(
        {"gid": "n", "name": "Score", "resource_subtype": "number", "number_value": 7.0}) == "7"
    assert sync._cf_mirror_value(
        {"gid": "n", "name": "Score", "resource_subtype": "number", "number_value": 7.5}) == "7.5"
    assert sync._cf_mirror_value(
        {"gid": "n", "name": "Score", "resource_subtype": "number", "number_value": None}) == "none"
    assert sync._cf_mirror_value(
        {"gid": "d", "name": "Shipped", "resource_subtype": "date",
         "date_value": {"date": "2026-11-05"}}) == "2026-11-05"
    assert sync._cf_mirror_value(
        {"gid": "t", "name": "Ref", "resource_subtype": "text", "text_value": " ABC "}) == "ABC"
    # A type the mirror cannot express is still shown, using Asana's own rendering.
    assert sync._cf_mirror_value(
        {"gid": "m", "name": "Milestone", "resource_subtype": "reference",
         "display_value": "Launch"}) == "Launch"


def test_custom_field_lines_skip_managed_and_built_in_fields(cf_env):
    t = {"custom_fields": [
        {"gid": "local_id_field", "name": "Local ID", "resource_subtype": "text",
         "text_value": "TEST-001"},
        {"gid": "last_synced_field", "name": "Last Synced", "resource_subtype": "text",
         "text_value": "2026-11-05"},
        _cf_priority("High"),
        {"gid": "looper_field", "name": "Looper Status", "resource_subtype": "enum",
         "enum_value": {"gid": "q", "name": "Queue"}},
        _cf_features("Security"),
        {"gid": "rev", "name": "Review Status", "resource_subtype": "enum",
         "enum_value": {"gid": "r1", "name": "Needs review"}},
    ]}
    lines = sync._custom_field_lines(t)
    # Local ID and Last Synced belong to the sync; Priority and Looper Status
    # already have their own mirror lines.
    assert lines == ["- **Features:** Security", "- **Review Status:** Needs review"]


def test_task_lines_render_custom_fields_after_looper_status(cf_env, sample_task):
    sample_task["custom_fields"] = [_cf_features("Security"), _cf_priority("High")]
    sample_task["_priority"] = "High"
    lines = _task_lines(sample_task, {}, {})
    assert "- **Priority:** High" in lines
    assert "- **Features:** Security" in lines
    assert lines.index("- **Features:** Security") == lines.index("- **Looper Status:** none") + 1


def test_parse_existing_mirror_carries_every_parsed_field(proj, mirror_text):
    proj.mirror_file.write_text(mirror_text.replace(
        "- **Section:** DOING", "- **Section:** DOING\n- **Features:** Security"))
    carried = parse_existing_mirror(proj)
    assert carried["111222333"]["_raw"]["features"] == "Security"


def test_push_custom_fields_sets_a_changed_enum(cf_env, monkeypatch, sample_task):
    puts = []
    monkeypatch.setattr(sync, "_put", lambda path, body: puts.append((path, body)))
    sample_task["custom_fields"] = [_cf_priority(None)]
    prev = {"_raw": {"priority": "High"}}
    assert sync._push_custom_fields(sample_task, prev, dry_run=False, prefix="TEST") is True
    assert puts == [("/tasks/111222333",
                     {"data": {"custom_fields": {"1155368350785978": "1155368350785979"}}})]
    # Reflected on the task, so the mirror written later this run shows High and
    # the next run does not push a stale "none" back over it.
    assert sample_task["_priority"] == "High"
    assert sync._cf_mirror_value(sample_task["custom_fields"][0]) == "High"


def test_push_custom_fields_matches_enum_options_case_insensitively(cf_env, monkeypatch, sample_task):
    puts = []
    monkeypatch.setattr(sync, "_put", lambda path, body: puts.append((path, body)))
    sample_task["custom_fields"] = [_cf_priority(None)]
    sync._push_custom_fields(sample_task, {"_raw": {"priority": "high"}},
                             dry_run=False, prefix="TEST")
    assert puts[0][1]["data"]["custom_fields"]["1155368350785978"] == "1155368350785979"


def test_push_custom_fields_skips_an_unknown_enum_value_loudly(cf_env, monkeypatch, sample_task, caplog):
    puts = []
    monkeypatch.setattr(sync, "_put", lambda path, body: puts.append((path, body)))
    sample_task["custom_fields"] = [_cf_priority("High")]
    with caplog.at_level("WARNING"):
        changed = sync._push_custom_fields(sample_task, {"_raw": {"priority": "Urgent"}},
                                           dry_run=False, prefix="TEST")
    assert changed is False
    assert puts == []   # a bad value never goes in a PUT: Asana 400s the whole thing
    assert "'Urgent' is not an option of 'Priority'" in caplog.text


def test_push_custom_fields_writes_a_multi_enum_as_the_whole_set(cf_env, monkeypatch, sample_task):
    puts = []
    monkeypatch.setattr(sync, "_put", lambda path, body: puts.append((path, body)))
    sample_task["custom_fields"] = [_cf_features("Greenhouse")]
    sync._push_custom_fields(sample_task, {"_raw": {"features": "Greenhouse, Security"}},
                             dry_run=False, prefix="TEST")
    assert puts[0][1]["data"]["custom_fields"]["1215208851588973"] == [
        "1216075949558841", "1220254742605531"]


def test_push_custom_fields_clears_a_field_set_to_none(cf_env, monkeypatch, sample_task):
    puts = []
    monkeypatch.setattr(sync, "_put", lambda path, body: puts.append((path, body)))
    sample_task["custom_fields"] = [_cf_priority("High"), _cf_features("Security")]
    sync._push_custom_fields(sample_task, {"_raw": {"priority": "none", "features": "none"}},
                             dry_run=False, prefix="TEST")
    fields = puts[0][1]["data"]["custom_fields"]
    assert fields["1155368350785978"] is None
    assert fields["1215208851588973"] == []


def test_push_custom_fields_leaves_looper_status_to_push_simple_fields(cf_env, monkeypatch, sample_task):
    puts = []
    monkeypatch.setattr(sync, "_put", lambda path, body: puts.append((path, body)))
    sample_task["custom_fields"] = [
        {"gid": "looper_field", "name": "Looper Status", "resource_subtype": "enum",
         "enum_value": None, "enum_options": [{"gid": "q", "name": "Queue"}]}]
    assert sync._push_custom_fields(sample_task, {"_raw": {"looper_status": "Queue"}},
                                    dry_run=False, prefix="TEST") is False
    assert puts == []


def test_push_custom_fields_ignores_a_field_absent_from_the_mirror(cf_env, monkeypatch, sample_task):
    # A mirror written by an older sync.py has no line for the field. There is
    # nothing to compare against, so it must not be read as "cleared".
    puts = []
    monkeypatch.setattr(sync, "_put", lambda path, body: puts.append((path, body)))
    sample_task["custom_fields"] = [_cf_priority("High")]
    assert sync._push_custom_fields(sample_task, {"_raw": {"due": "2026-05-25"}},
                                    dry_run=False, prefix="TEST") is False
    assert puts == []


def test_push_custom_fields_dry_run_writes_nothing(cf_env, monkeypatch, sample_task, caplog):
    puts = []
    monkeypatch.setattr(sync, "_put", lambda path, body: puts.append((path, body)))
    sample_task["custom_fields"] = [_cf_priority(None)]
    with caplog.at_level("INFO"):
        assert sync._push_custom_fields(sample_task, {"_raw": {"priority": "High"}},
                                        dry_run=True, prefix="TEST") is False
    assert puts == []
    assert "Would set custom fields" in caplog.text


def test_push_custom_fields_skips_a_read_only_field_type(cf_env, monkeypatch, sample_task):
    puts = []
    monkeypatch.setattr(sync, "_put", lambda path, body: puts.append((path, body)))
    sample_task["custom_fields"] = [
        {"gid": "m", "name": "Milestone", "resource_subtype": "reference",
         "display_value": "Launch"}]
    assert sync._push_custom_fields(sample_task, {"_raw": {"milestone": "Something else"}},
                                    dry_run=False, prefix="TEST") is False
    assert puts == []


def test_push_custom_fields_rejects_a_non_numeric_number(cf_env, monkeypatch, sample_task, caplog):
    puts = []
    monkeypatch.setattr(sync, "_put", lambda path, body: puts.append((path, body)))
    sample_task["custom_fields"] = [
        {"gid": "n", "name": "Score", "resource_subtype": "number", "number_value": 7.0}]
    with caplog.at_level("WARNING"):
        sync._push_custom_fields(sample_task, {"_raw": {"score": "high-ish"}},
                                 dry_run=False, prefix="TEST")
    assert puts == []
    assert "is not a number" in caplog.text


def test_push_custom_fields_rejects_a_non_iso_date(cf_env, monkeypatch, sample_task, caplog):
    puts = []
    monkeypatch.setattr(sync, "_put", lambda path, body: puts.append((path, body)))
    sample_task["custom_fields"] = [
        {"gid": "d", "name": "Shipped", "resource_subtype": "date",
         "date_value": {"date": "2026-11-05"}}]
    with caplog.at_level("WARNING"):
        sync._push_custom_fields(sample_task, {"_raw": {"shipped": "05/11/2026"}},
                                 dry_run=False, prefix="TEST")
    assert puts == []
    assert "is not an ISO date" in caplog.text


def test_custom_field_colliding_with_a_built_in_line_is_warned_once(cf_env, caplog):
    t = {"custom_fields": [
        {"gid": "x", "name": "Blockers", "resource_subtype": "text", "text_value": "hi"}]}
    with caplog.at_level("WARNING"):
        assert sync._custom_field_lines(t) == []
        sync._custom_field_lines(t)
    assert caplog.text.count("collides with the built-in mirror field") == 1


def test_a_description_cannot_overwrite_a_real_field(proj, mirror_text):
    # A description is free text and routinely contains its own bold bullets —
    # the walls of text that prompted the limit were written in this style, and
    # an emailed one is untrusted input. Collected into the same field map, the
    # last match for a key won, so these lines replaced the real values and were
    # then pushed to Asana on the next mirror-newer run.
    poisoned = mirror_text.replace(
        "- **Notes:** Some notes here.",
        "- **Notes:** Pasted from the vendor email:\n"
        "- **Priority:** none\n"
        "- **Section:** DONE\n"
        "- **Due:** none\n"
        "- **Features:** none\n"
        "- **Blockers:** quoted, not the real line\n")
    proj.mirror_file.write_text(
        poisoned.replace("- **Section:** DOING",
                         "- **Section:** DOING\n- **Priority:** High\n- **Features:** Security"))
    prev = parse_existing_mirror(proj)["111222333"]
    assert prev["section"] == "DOING"
    assert prev["due"] == "2026-05-25"
    assert prev["_raw"]["priority"] == "High"
    assert prev["_raw"]["features"] == "Security"
    assert prev["blockers"] == "None identified."
    # Only the description's first line is kept — enough to notice an edit.
    assert prev["notes"] == "Pasted from the vendor email:"


def test_a_foreign_priority_field_is_never_pushed_by_name(cf_env, monkeypatch, sample_task, caplog):
    # The built-in Priority line renders from PRIORITY_FIELD_GID only. A project
    # whose own "Priority" field has a different GID therefore shows `none` in
    # the mirror while Asana holds a value: pushing by name would clear it on
    # every task, every run.
    other = _cf_priority("High")
    other["gid"] = "9999999999"
    sample_task["custom_fields"] = [other]
    puts = []
    monkeypatch.setattr(sync, "_put", lambda path, body: puts.append((path, body)))
    with caplog.at_level("WARNING"):
        assert sync._push_custom_fields(sample_task, {"_raw": {"priority": "none"}},
                                        dry_run=False, prefix="TEST") is False
        assert sync._custom_field_lines(sample_task) == []
    assert puts == []
    assert "collides with the built-in mirror field" in caplog.text


def test_push_custom_fields_sends_a_date_as_an_object(cf_env, monkeypatch, sample_task):
    # A date custom field takes {"date": "YYYY-MM-DD"}, not the bare string a
    # text field takes. Every field goes in one PUT, so the wrong shape would
    # 400 the whole write and lose the other fields with it.
    puts = []
    monkeypatch.setattr(sync, "_put", lambda path, body: puts.append((path, body)))
    sample_task["custom_fields"] = [
        {"gid": "d", "name": "Shipped", "resource_subtype": "date", "date_value": None}]
    sync._push_custom_fields(sample_task, {"_raw": {"shipped": "2026-11-05"}},
                             dry_run=False, prefix="TEST")
    assert puts[0][1]["data"]["custom_fields"]["d"] == {"date": "2026-11-05"}


def test_field_regex_only_matches_a_top_level_bullet():
    assert sync.FIELD_RE.findall("- **Priority:** High") == [("Priority", "High")]
    assert sync.FIELD_RE.findall("  - **Priority:** High") == []
    assert sync.FIELD_RE.findall("see - **Priority:** High inline") == []
