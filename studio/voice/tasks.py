#!/usr/bin/env python3
"""
Task runner for the voice agent: each task is a headless `claude -p` session.

The voice layer calls start/list/result/follow_up/cancel; this module owns the
subprocesses and persists their state so a voice reconnect does not lose them.

Usage (text harness, no audio):
    python3 studio/voice/tasks.py "List the active studio projects" --project BD
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

STUDIO_ROOT = Path("/media/data/dev/bain-studio")
PROJECT_DOCS = STUDIO_ROOT / "docs" / "projects"
STATE_PATH = Path.home() / ".claude" / "voice-agent" / "tasks.json"

MAX_CONCURRENT = 3

# Outward-facing actions a hands-free task must never take on its own. A task
# that needs one says so in its result; a confirmed follow-up lifts the block.
OUTWARD_TOOLS = [
    "mcp__claude_ai_Gmail__send_message",
    "mcp__claude_ai_Gmail__reply",
    "mcp__claude_ai_Gmail__forward",
    "mcp__claude_ai_Google_Calendar__create_event",
    "mcp__claude_ai_Google_Calendar__update_event",
    "mcp__claude_ai_Google_Calendar__delete_event",
    "mcp__claude_ai_Google_Calendar__respond_to_event",
    "mcp__claude_ai_Google_Drive__share_file",
    "mcp__claude_ai_Google_Drive__trash_file",
    "mcp__claude_ai_Dropbox__create_shared_link",
    "mcp__claude_ai_Dropbox__create_file_request",
    "mcp__claude_ai_Dropbox__delete",
    "mcp__claude_ai_Dropbox__move",
    # Asana changes go through sync.py, never the MCP.
    "mcp__claude_ai_Asana__create_tasks",
    "mcp__claude_ai_Asana__update_tasks",
    "mcp__claude_ai_Asana__delete_task",
    "mcp__claude_ai_Asana__add_comment",
    "mcp__claude_ai_Asana__create_project",
    "mcp__claude_ai_Asana__update_project",
    "mcp__claude_ai_Asana__create_project_status_update",
    "Artifact",
    "Bash(git push *)",
    "Bash(git merge *)",
    "Bash(git flow * finish *)",
]

TASK_PROMPT = """You are running hands-free for Mark, who is talking to a voice assistant and cannot see your screen.
- Never send, publish, push or merge anything. Draft instead.
- If the task needs an outward action (sending an email, pushing, merging, posting), stop before it and end your reply with a line starting "NEEDS CONFIRMATION:" saying exactly what you would do.
- Your final reply is read aloud. Keep it to two or three plain sentences: what you did and what Mark needs to know. No markdown, no file paths unless essential."""


@dataclass
class Task:
    id: int
    prompt: str
    cwd: str
    status: str = "running"  # running | done | failed | cancelled
    session_id: str = ""
    result: str = ""
    started: float = field(default_factory=time.time)
    finished: float = 0.0
    pid: int = 0


def resolve_project(prefix: str | None) -> Path:
    """Map a studio prefix (e.g. "BD") to its repo path; default to bain-studio."""
    if not prefix:
        return STUDIO_ROOT
    wanted = prefix.strip().upper()
    for doc in PROJECT_DOCS.glob("*.md"):
        text = doc.read_text()
        head = text.split("---", 2)[1] if text.startswith("---") else ""
        p = re.search(r"^prefix:\s*(\S+)", head, re.M)
        path = re.search(r"^path:\s*(.+)$", head, re.M)
        if p and path and p.group(1).upper() == wanted:
            return Path(path.group(1).strip())
    raise ValueError(f"No studio project with prefix {prefix}")


class TaskRunner:
    def __init__(self, claude_bin: str = "claude", state_path: Path = STATE_PATH,
                 on_finish=None):
        self.claude_bin = claude_bin
        self.state_path = state_path
        self.on_finish = on_finish  # async callable(Task), e.g. to speak the result
        self.tasks: dict[int, Task] = {}
        self._procs: dict[int, asyncio.subprocess.Process] = {}
        self._load()

    # --- persistence -------------------------------------------------------

    def _load(self):
        """Start each run with an empty task list, archiving the previous run's
        record so old tasks are neither read out nor renumbered past."""
        if self.state_path.exists():
            stamp = time.strftime("%Y-%m-%d-%H%M%S", time.localtime(self.state_path.stat().st_mtime))
            self.state_path.rename(self.state_path.with_name(f"tasks-{stamp}.json"))

    def _save(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps([asdict(t) for t in self.tasks.values()], indent=2))

    # --- public API --------------------------------------------------------

    def running(self) -> list[Task]:
        return [t for t in self.tasks.values() if t.status == "running"]

    async def start(self, prompt: str, project: str | None = None) -> Task:
        if len(self.running()) >= MAX_CONCURRENT:
            raise RuntimeError(f"Already running {MAX_CONCURRENT} tasks. Wait or cancel one.")
        cwd = resolve_project(project)
        task = Task(id=max(self.tasks, default=0) + 1, prompt=prompt, cwd=str(cwd))
        self.tasks[task.id] = task
        await self._spawn(task, prompt, resume=None, allow_outward=False)
        return task

    async def follow_up(self, task_id: int, message: str, allow_outward: bool = False) -> Task:
        """Continue a finished task's session, e.g. to answer it or confirm an action."""
        task = self._get(task_id)
        if task.status == "running":
            raise RuntimeError(f"Task {task_id} is still running.")
        if not task.session_id:
            raise RuntimeError(f"Task {task_id} has no session to continue.")
        task.status, task.result, task.finished = "running", "", 0.0
        task.prompt += f"\n[follow-up] {message}"
        await self._spawn(task, message, resume=task.session_id, allow_outward=allow_outward)
        return task

    async def cancel(self, task_id: int) -> Task:
        task = self._get(task_id)
        proc = self._procs.get(task_id)
        if proc and proc.returncode is None:
            proc.terminate()
        task.status, task.finished = "cancelled", time.time()
        self._save()
        return task

    def summary(self) -> list[dict]:
        return [{"id": t.id, "status": t.status, "prompt": t.prompt[:120],
                 "minutes": round(((t.finished or time.time()) - t.started) / 60, 1)}
                for t in self.tasks.values()]

    def result(self, task_id: int) -> Task:
        return self._get(task_id)

    # --- internals ---------------------------------------------------------

    def _get(self, task_id: int) -> Task:
        if task_id not in self.tasks:
            raise KeyError(f"No task {task_id}")
        return self.tasks[task_id]

    async def _spawn(self, task: Task, prompt: str, resume: str | None, allow_outward: bool):
        args = [self.claude_bin, "-p", prompt, "--output-format", "json",
                "--permission-mode", "auto", "--append-system-prompt", TASK_PROMPT]
        if resume:
            args += ["--resume", resume]
        if not allow_outward:
            args += ["--disallowedTools", *OUTWARD_TOOLS]
        proc = await asyncio.create_subprocess_exec(
            *args, cwd=task.cwd, stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        task.pid = proc.pid
        self._procs[task.id] = proc
        self._save()
        asyncio.create_task(self._wait(task, proc))

    async def _wait(self, task: Task, proc: asyncio.subprocess.Process):
        stdout, stderr = await proc.communicate()
        self._procs.pop(task.id, None)
        if task.status == "cancelled":
            return
        task.finished = time.time()
        try:
            out = json.loads(stdout.decode())
            task.session_id = out.get("session_id", task.session_id)
            task.result = (out.get("result") or "").strip()
            task.status = "failed" if out.get("is_error") else "done"
        except json.JSONDecodeError:
            task.status = "failed"
            task.result = (stderr.decode() or stdout.decode()).strip()[-1000:] or f"Exited {proc.returncode}"
        self._save()
        if self.on_finish:
            await self.on_finish(task)


async def _harness(prompt: str, project: str | None, follow: str | None):
    done = asyncio.Event()

    async def on_finish(task: Task):
        print(f"\n[task {task.id} {task.status}] session={task.session_id}\n{task.result}\n")
        done.set()

    runner = TaskRunner(on_finish=on_finish)
    task = await runner.start(prompt, project)
    print(f"Started task {task.id} in {task.cwd}")
    await done.wait()
    if follow:
        done.clear()
        await runner.follow_up(task.id, follow)
        print(f"Follow-up sent to task {task.id}")
        await done.wait()


def main():
    parser = argparse.ArgumentParser(description="Run one voice-agent task from the terminal")
    parser.add_argument("prompt")
    parser.add_argument("--project", help="Studio prefix, e.g. BD. Default: bain-studio")
    parser.add_argument("--follow-up", help="Message to send to the same session afterwards")
    args = parser.parse_args()
    asyncio.run(_harness(args.prompt, args.project, args.follow_up))


if __name__ == "__main__":
    main()
