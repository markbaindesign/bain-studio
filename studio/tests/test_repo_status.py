import importlib.machinery
import importlib.util
import json
import time
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "repo-status"
_loader = importlib.machinery.SourceFileLoader("repo_status", str(SCRIPT))
_spec = importlib.util.spec_from_loader("repo_status", _loader)
s = importlib.util.module_from_spec(_spec)
_loader.exec_module(s)


# --- reading the registry --------------------------------------------------

def test_registry_takes_active_paths_in_order(tmp_path, monkeypatch):
    registry = tmp_path / "projects.json"
    registry.write_text(json.dumps([
        {"path": "/a", "status": "active"},
        {"path": "/b", "status": "archived"},
        "/c",
    ]))
    monkeypatch.setattr(s, "REGISTRY", registry)
    # A bare string is the pre-migration format and means active.
    assert s.registry_paths() == ["/a", "/c"]


def test_a_missing_registry_is_empty_not_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(s, "REGISTRY", tmp_path / "nothing.json")
    assert s.registry_paths() == []


# --- parsing git status ----------------------------------------------------

STATUS = """# branch.oid abc
# branch.head develop
# branch.upstream origin/develop
# branch.ab +2 -1
1 .M N... 100644 100644 100644 aaa bbb theme/style.css
1 M. N... 100644 100644 100644 aaa bbb theme/functions.php
? .claude/
? .ddev/
"""


def test_status_reads_branch_upstream_and_ahead():
    state = s.parse_status(STATUS)
    assert state["branch"] == "develop"
    assert state["upstream"] == "origin/develop"
    assert state["ahead"] == 2


def test_tracked_and_untracked_are_counted_apart():
    """A repo whose only changes are an untracked .claude/ and .ddev/ is not
    work in progress. Counting them together put most of the list permanently
    at the top."""
    state = s.parse_status(STATUS)
    assert state["tracked"] == 2
    assert state["untracked"] == 2


def test_conflicts_are_counted_separately():
    state = s.parse_status("u UU N... 1 1 1 aaa bbb ccc theme/style.css\n")
    assert state["conflicts"] == 1 and state["tracked"] == 0


def test_a_branch_without_an_upstream_has_no_ab_line():
    state = s.parse_status("# branch.head feature/thing\n")
    assert state["upstream"] == "" and state["ahead"] == 0


def test_a_detached_head_is_read_as_such():
    # The ops worktree is detached, so this is not a rare case here.
    assert s.parse_status("# branch.head (detached)\n")["branch"] == "(detached)"


# --- worktrees -------------------------------------------------------------

WORKTREES = """worktree /media/data/dev/bain-studio
HEAD abc
branch refs/heads/develop

worktree /home/bain/ops/bain-studio
HEAD def
detached

worktree /media/data/dev/bain-studio/.worktrees/gone
HEAD ghi
branch refs/heads/feature/gone
prunable gitdir file points to non-existent location
"""


def test_worktrees_are_counted_including_the_main_one():
    assert s.parse_worktrees(WORKTREES) == 2


def test_a_prunable_worktree_is_not_counted():
    """git lists a worktree whose directory has gone until someone prunes it;
    counting it would report work that is not there."""
    assert "gone" in WORKTREES
    assert s.parse_worktrees(WORKTREES) == 2


# --- the integration branch and unmerged work ------------------------------

def test_integration_branch_prefers_develop():
    assert s.pick_integration(["main", "develop", "feature/x"]) == "develop"


def test_integration_branch_falls_back_to_main_then_master():
    assert s.pick_integration(["main", "feature/x"]) == "main"
    assert s.pick_integration(["master"]) == "master"
    assert s.pick_integration(["feature/x"]) == ""


def test_unmerged_ignores_the_integration_branches_themselves():
    """main not being merged into develop is the normal state of a git-flow
    repo, not unfinished work."""
    assert s.unmerged_count(["main", "develop", "feature/x"], "develop") == 1


def test_an_unmerged_looper_branch_counts():
    # Unattended work parked on a branch is exactly what the column is for.
    assert s.unmerged_count(["looper/14802d54"], "develop") == 1


# --- which state a repo is in ----------------------------------------------

def repo(**kwargs):
    base = {"state": "", "branch": "develop", "upstream": "origin/develop",
            "ahead": 0, "tracked": 0, "untracked": 0, "conflicts": 0}
    base.update(kwargs)
    return base


def test_tracked_changes_are_dirty():
    assert s.classify(repo(tracked=2)) == "dirty"
    assert s.classify(repo(conflicts=1)) == "dirty"


def test_untracked_only_is_its_own_state_below_dirty():
    assert s.classify(repo(untracked=3)) == "untracked"
    assert s.STATUS_ORDER["untracked"] > s.STATUS_ORDER["dirty"]


def test_commits_ahead_of_the_upstream_are_unpushed():
    assert s.classify(repo(ahead=2)) == "ahead"


def test_no_upstream_at_all_counts_as_unpushed():
    """The branch exists on this machine and nowhere else, which is the same
    exposure as commits ahead of an upstream - and easy to miss, because
    nothing on the row would otherwise say so."""
    assert s.classify(repo(upstream="", branch="develop")) == "ahead"


def test_a_clean_repo_parked_on_a_feature_branch_is_flagged():
    assert s.classify(repo(branch="feature/thing")) == "branch"


def test_a_clean_integration_branch_is_ok():
    assert s.classify(repo()) == "ok"


def test_missing_and_nogit_keep_the_state_they_arrived_with():
    assert s.classify(repo(state="missing", upstream="")) == "missing"
    assert s.classify(repo(state="nogit", upstream="")) == "nogit"


def test_nothing_sorts_below_nogit_and_ok_asks_for_nothing():
    assert max(s.STATUS_ORDER.values()) == s.STATUS_ORDER["nogit"]
    assert s.STATUS_ORDER["ok"] < s.STATUS_ORDER["nogit"]


# --- one row per repo ------------------------------------------------------

def test_paths_inside_one_repo_collapse_to_a_single_row():
    """SL and SLT are directories inside bain-studio, so three registry paths
    resolve to one repo and would otherwise be listed three times."""
    rows = [{"path": "/dev/bain-studio", "top": "/dev/bain-studio"},
            {"path": "/dev/bain-studio/studio/looper", "top": "/dev/bain-studio"},
            {"path": "/dev/bain-studio/studio/looper-test", "top": "/dev/bain-studio"}]
    assert [r["path"] for r in s.dedupe(rows)] == ["/dev/bain-studio"]


# --- the ops line ----------------------------------------------------------

def test_ops_says_current_when_it_holds_the_newest_tag():
    text, wants = s.ops_text({"tag": "1.18.0", "head": "abc", "newest": "1.18.0",
                              "tracked": 0, "note": ""})
    assert text == "ops 1.18.0 current" and not wants


def test_ops_behind_a_newer_tag_asks_to_be_deployed():
    """A tagged release is not done until ops is deployed (ADR 014)."""
    text, wants = s.ops_text({"tag": "1.17.0", "head": "abc", "newest": "1.18.0",
                              "tracked": 0, "note": ""})
    assert "1.17.0" in text and "1.18.0" in text and "deploy" in text
    assert wants


def test_local_changes_in_ops_are_drift_too():
    # ops-deploy.sh refuses to deploy over local changes to tracked files.
    text, wants = s.ops_text({"tag": "1.18.0", "head": "abc", "newest": "1.18.0",
                              "tracked": 2, "note": ""})
    assert "2 local changes" in text and wants


def test_untagged_ops_is_shown_by_its_commit():
    text, _ = s.ops_text({"tag": "", "head": "dcdb759", "newest": "1.18.0",
                          "tracked": 0, "note": ""})
    assert "@dcdb759" in text


def test_a_missing_ops_worktree_says_so():
    text, wants = s.ops_text({"note": "no ops worktree"})
    assert text == "ops no ops worktree" and wants


# --- fitting the row to the pane -------------------------------------------

ROW = {"state": "dirty", "name": "middlewayeducation", "branch": "develop",
       "note": "", "upstream": "origin/develop", "ahead": 2, "tracked": 3,
       "untracked": 2, "conflicts": 0, "worktrees": 2, "unmerged": 2,
       "committed": time.time() - 15 * 86400, "subject": "chore: sync Asana mirror",
       "path": "/media/data/dev/vvv/clients/www/middlewayeducation"}


def test_row_never_exceeds_the_pane():
    for width in range(30, 200):
        assert len(s.row_text(ROW, width)) < width


def test_narrow_row_keeps_the_state_name_and_counts():
    text = s.row_text(ROW, 70)
    assert "dirty" in text and "middlewayeducation" in text and "3M 2?" in text


def test_subject_goes_before_the_parked_work_counts():
    assert "chore: sync Asana mirror" in s.row_text(ROW, 132)
    assert "chore: sync Asana mirror" not in s.row_text(ROW, 96)
    assert "2ub" in s.row_text(ROW, 96)
    assert "2ub" not in s.row_text(ROW, 70)


def test_the_working_tree_column_separates_tracked_from_untracked():
    assert s.counts_text(ROW) == "3M 2?"
    assert s.counts_text(dict(ROW, tracked=0, untracked=0)) == ""
    assert s.counts_text(dict(ROW, tracked=0, conflicts=1, untracked=0)) == "1M"


def test_a_branch_with_no_upstream_reads_local_rather_than_zero():
    assert s.ahead_text(dict(ROW, upstream="", ahead=0)) == "local"
    assert s.ahead_text(dict(ROW, ahead=0)) == ""
    assert s.ahead_text(dict(ROW, ahead=14)) == "↑14"


def test_behind_is_never_shown():
    """Nothing is fetched, so a behind count would be a stale number dressed
    as a fact. parse_status does not even keep it."""
    assert "behind" not in s.parse_status(STATUS)
    assert "↓" not in s.row_text(ROW, 132)


def test_extras_count_only_the_extra_worktrees():
    assert s.extras_text(dict(ROW, worktrees=1, unmerged=0)) == ""
    assert s.extras_text(dict(ROW, worktrees=8, unmerged=5)) == "7wt 5ub"


def test_a_repo_with_no_commits_shows_no_age():
    assert s.ago_or_note(dict(ROW, committed=0)) == "-"
