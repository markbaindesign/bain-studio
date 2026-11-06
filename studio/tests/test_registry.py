"""studio/registry.py — project identity resolution.

The point of these: the registry lives outside the repo, so the fallback is
what runs on a machine that has not been migrated yet, and both paths have to
give the same answer for a project that exists in both.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import registry


def _write_registry(tmp_path, data):
    p = tmp_path / "registry.json"
    p.write_text(json.dumps(data))
    return p


def _fake_repo(tmp_path, files=None, projects_json=None):
    docs = tmp_path / "repo" / "docs" / "projects"
    docs.mkdir(parents=True)
    for name, body in (files or {}).items():
        (docs / name).write_text(body)
    if projects_json is not None:
        studio = tmp_path / "repo" / "studio"
        studio.mkdir(parents=True, exist_ok=True)
        (studio / "projects.json").write_text(json.dumps(projects_json))
    return tmp_path / "repo"


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """Never let a test be answered from the real registry."""
    monkeypatch.setenv("BAIN_REGISTRY", str(tmp_path / "absent.json"))
    monkeypatch.delenv("BAIN_PROJECTS_JSON", raising=False)


def test_registry_is_preferred_over_the_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("BAIN_REGISTRY", str(_write_registry(tmp_path, {
        "kf": {"prefix": "KF-WEB", "path": "/from/registry", "status": "active"}})))
    repo = _fake_repo(tmp_path, {"kf.md": "---\nprefix: KF-WEB\npath: /from/fallback\n---\n"})
    entries, source = registry.load(repo_root=repo)
    assert source == registry.SOURCE_REGISTRY
    assert registry.path_for("KF-WEB", entries) == Path("/from/registry")


def test_fallback_used_when_the_registry_is_absent(tmp_path):
    repo = _fake_repo(tmp_path, {"kf.md": "---\nprefix: KF-WEB\npath: /from/fallback\n---\n"})
    entries, source = registry.load(repo_root=repo)
    assert source == registry.SOURCE_FALLBACK
    assert registry.path_for("KF-WEB", entries) == Path("/from/fallback")


def test_malformed_registry_falls_back_rather_than_raising(tmp_path, monkeypatch, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    monkeypatch.setenv("BAIN_REGISTRY", str(bad))
    repo = _fake_repo(tmp_path, {"x.md": "---\nprefix: X\npath: /p\n---\n"})
    entries, source = registry.load(repo_root=repo)
    assert source == registry.SOURCE_FALLBACK
    assert "unreadable" in capsys.readouterr().err


def test_empty_registry_falls_back(tmp_path, monkeypatch):
    monkeypatch.setenv("BAIN_REGISTRY", str(_write_registry(tmp_path, {})))
    repo = _fake_repo(tmp_path, {"x.md": "---\nprefix: X\npath: /p\n---\n"})
    _, source = registry.load(repo_root=repo)
    assert source == registry.SOURCE_FALLBACK


def test_fallback_picks_up_projects_json_entries_with_no_project_file(tmp_path):
    """Two projects existed only in projects.json and had no project file."""
    repo = _fake_repo(
        tmp_path,
        {"kf.md": "---\nprefix: KF-WEB\npath: /kf\n---\n"},
        projects_json=[{"prefix": "PSK", "path": "/media/psk", "gid": "99", "status": "paused"}],
    )
    entries, _ = registry.load(repo_root=repo)
    assert registry.path_for("PSK", entries) == Path("/media/psk")
    assert registry.resolve("PSK", entries)["gid"] == "99"


def test_projects_json_does_not_override_a_project_file(tmp_path):
    repo = _fake_repo(
        tmp_path,
        {"kf.md": "---\nprefix: KF-WEB\npath: /from/file\n---\n"},
        projects_json=[{"prefix": "KF-WEB", "path": "/from/json"}],
    )
    entries, _ = registry.load(repo_root=repo)
    assert registry.path_for("KF-WEB", entries) == Path("/from/file")


def test_prefix_resolution_is_case_insensitive(tmp_path):
    repo = _fake_repo(tmp_path, {"kf.md": "---\nprefix: KF-WEB\npath: /kf\n---\n"})
    entries, _ = registry.load(repo_root=repo)
    for variant in ("KF-WEB", "kf-web", " Kf-Web "):
        assert registry.resolve(variant, entries) is not None, variant


def test_unknown_and_blank_prefixes_return_none(tmp_path):
    repo = _fake_repo(tmp_path, {"kf.md": "---\nprefix: KF-WEB\npath: /kf\n---\n"})
    entries, _ = registry.load(repo_root=repo)
    assert registry.resolve("NOPE", entries) is None
    assert registry.resolve("", entries) is None
    assert registry.resolve(None, entries) is None
    assert registry.path_for("NOPE", entries) is None


def test_entry_without_a_path_resolves_but_has_no_path(tmp_path, monkeypatch):
    monkeypatch.setenv("BAIN_REGISTRY", str(_write_registry(tmp_path, {
        "x": {"prefix": "X", "path": "", "status": "active"}})))
    entries, _ = registry.load()
    assert registry.resolve("X", entries) is not None
    assert registry.path_for("X", entries) is None


def test_active_omits_paused_and_archived(tmp_path, monkeypatch):
    monkeypatch.setenv("BAIN_REGISTRY", str(_write_registry(tmp_path, {
        "a": {"prefix": "A", "status": "active", "path": "/a"},
        "b": {"prefix": "B", "status": "paused", "path": "/b"},
        "c": {"prefix": "C", "status": "archived", "path": "/c"},
        "d": {"prefix": "D", "path": "/d"},
    })))
    entries, _ = registry.load()
    assert sorted(e["prefix"] for e in registry.active(entries).values()) == ["A", "D"]


def test_frontmatter_without_a_prefix_is_skipped(tmp_path):
    repo = _fake_repo(tmp_path, {
        "good.md": "---\nprefix: G\npath: /g\n---\n",
        "nofm.md": "no frontmatter here\n",
        "noprefix.md": "---\nname: Thing\npath: /t\n---\n",
    })
    entries, _ = registry.load(repo_root=repo)
    assert [e["prefix"] for e in entries.values()] == ["G"]


def test_quoted_frontmatter_values_are_unquoted(tmp_path):
    repo = _fake_repo(tmp_path, {
        "k.md": '---\nprefix: "K"\npath: "/p"\nasana_project_gid: "123"\n---\n'})
    entries, _ = registry.load(repo_root=repo)
    entry = registry.resolve("K", entries)
    assert entry["gid"] == "123"
    assert registry.path_for("K", entries) == Path("/p")


def test_type_client_sets_kind(tmp_path):
    repo = _fake_repo(tmp_path, {
        "c.md": "---\nprefix: C\ntype: client\npath: /c\n---\n",
        "i.md": "---\nprefix: I\ntype: internal\npath: /i\n---\n",
    })
    entries, _ = registry.load(repo_root=repo)
    assert registry.resolve("C", entries)["kind"] == "client"
    assert registry.resolve("I", entries)["kind"] == "internal"


def test_nothing_anywhere_yields_empty(tmp_path):
    repo = tmp_path / "bare"
    repo.mkdir()
    entries, _ = registry.load(repo_root=repo)
    assert entries == {}
