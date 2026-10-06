import asyncio
import json
import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "voice"))
import tasks  # noqa: E402

FAKE_CLAUDE = """#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
resume = args[args.index("--resume") + 1] if "--resume" in args else None
blocked = "--disallowedTools" in args
print(json.dumps({
    "session_id": resume or "sess-1",
    "result": f"prompt={args[1]} resumed={bool(resume)} blocked={blocked}",
    "is_error": False,
}))
"""


@pytest.fixture
def fake_claude(tmp_path):
    path = tmp_path / "claude"
    path.write_text(FAKE_CLAUDE)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def make_runner(fake_claude, tmp_path, finished):
    async def on_finish(task):
        finished.append(task)
    return tasks.TaskRunner(claude_bin=fake_claude, state_path=tmp_path / "tasks.json",
                            on_finish=on_finish)


async def wait_for(finished, n):
    for _ in range(200):
        if len(finished) >= n:
            return
        await asyncio.sleep(0.05)
    raise AssertionError("task did not finish")


def test_start_and_follow_up(fake_claude, tmp_path, monkeypatch):
    monkeypatch.setattr(tasks, "resolve_project", lambda prefix: tmp_path)
    finished = []
    runner = make_runner(fake_claude, tmp_path, finished)

    async def scenario():
        task = await runner.start("hello")
        await wait_for(finished, 1)
        assert task.status == "done"
        assert task.session_id == "sess-1"
        assert task.result == "prompt=hello resumed=False blocked=True"

        await runner.follow_up(task.id, "send it", allow_outward=True)
        await wait_for(finished, 2)
        assert task.result == "prompt=send it resumed=True blocked=False"

    run(scenario())
    saved = json.loads((tmp_path / "tasks.json").read_text())
    assert saved[0]["status"] == "done"


def test_concurrency_cap(fake_claude, tmp_path, monkeypatch):
    monkeypatch.setattr(tasks, "resolve_project", lambda prefix: tmp_path)
    runner = make_runner(fake_claude, tmp_path, [])
    for i in range(tasks.MAX_CONCURRENT):
        runner.tasks[i + 1] = tasks.Task(id=i + 1, prompt="x", cwd=str(tmp_path))
    with pytest.raises(RuntimeError):
        run(runner.start("one too many"))


def test_previous_run_archived(tmp_path):
    state = tmp_path / "tasks.json"
    state.write_text(json.dumps([{"id": 1, "prompt": "x", "cwd": "/", "status": "running"}]))
    runner = tasks.TaskRunner(state_path=state)
    assert runner.tasks == {}
    assert not state.exists()
    assert len(list(tmp_path.glob("tasks-*.json"))) == 1


def test_resolve_project_by_prefix():
    assert tasks.resolve_project(None) == tasks.STUDIO_ROOT
    assert tasks.resolve_project("bd") == Path("/media/data/dev/bain/www/bain.design")
    with pytest.raises(ValueError):
        tasks.resolve_project("NOPE")
