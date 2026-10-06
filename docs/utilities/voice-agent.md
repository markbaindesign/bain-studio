---
tags: [tool, voice, agent]
god: hermes
invoke: studio/voice/agent.py
command: /voice-agent
description: Hands-free spoken front desk - an OpenAI Realtime voice that hands studio work to background Claude sessions and reads the results back
---

# voice-agent

Talk to the studio without a screen. An OpenAI Realtime voice listens on the mic, decides what
needs doing, and hands each piece of real work to a background `claude -p` session with full
studio access. When a task finishes, the voice reads its result back. The voice itself does no
studio work and never answers from its own knowledge - it is a front desk, Claude is the back office.

## Usage

```bash
python3 studio/voice/agent.py            # gpt-realtime-mini (default)
python3 studio/voice/agent.py --full     # gpt-realtime: better at deciding when to start tasks, ~4x cost
python3 studio/voice/agent.py --duplex   # mic stays live while it speaks, so Mark can interrupt. Headphones only
```

`/voice-agent` opens it in a new Terminator tab. Ctrl+C ends the session; any running tasks
are terminated with it.

Without `--duplex`, the mic is gated while the agent is speaking (plus a 250ms tail), so the
speakers don't feed the voice back into itself.

## Setup

- `OPENAI_API_KEY` in the environment or in `studio/.env`
- Python packages: `numpy`, `sounddevice`, `websockets`
- `claude` on `PATH`

## How it works

| File | Role |
|------|------|
| `studio/voice/agent.py` | Audio in/out, the Realtime websocket session, the voice's tools |
| `studio/voice/tasks.py` | `TaskRunner`: spawns and tracks the headless Claude sessions |
| `studio/voice/system-prompt.md` | The voice's instructions: when to start a task, how to speak |

The voice has five tools: `start_task`, `list_tasks`, `get_task_result`, `follow_up` and
`cancel_task`.

- **Tasks** run as `claude -p --permission-mode auto --output-format json`, at most 3 at once.
  A task given a project prefix (e.g. `BD`) runs in that project's repo, resolved from
  `docs/projects/`; otherwise it runs in bain-studio.
- **Follow-ups** resume the same Claude session (`--resume`), so Mark can answer a task's
  question or tell it to carry on.
- **Results** are spoken only when nobody is talking, and trimmed to 1,500 characters. The full
  result stays available via `get_task_result`.
- **Reconnects:** a Realtime session is capped at about 60 minutes, so the agent reconnects at 55
  and hands the new session the current task list. Three disconnects within a minute of
  connecting in a row (bad key, no quota) stop it rather than loop.

## Safety: outward actions need a spoken yes

Every task runs with outward tools blocked (`--disallowedTools`): Gmail send/reply/forward,
Calendar writes, Drive share/trash, Dropbox share/delete/move, Asana MCP writes, Artifact
publishing, and `git push`, `git merge`, `git flow ... finish`. The task prompt also tells Claude
to draft rather than send, and to end with a `NEEDS CONFIRMATION:` line describing the action it
would take.

The voice reads that line out and asks Mark. Only after a clear yes does it call `follow_up`
with `confirm_outward: true`, which resumes the session with the block lifted for that one turn.
The list lives in `OUTWARD_TOOLS` in `tasks.py` - add to it when a new outward-facing tool
appears.

## Output

- **Transcript:** each session is saved on exit to
  `/media/data/Dropbox/Work/Studio/context/voice-agent/YYYY-MM-DD-HHMM.md`, with Mark's words,
  the voice's replies and every task result.
- **Task state:** `~/.claude/voice-agent/tasks.json`. Each run starts with an empty list; the
  previous run's file is archived alongside it as `tasks-<timestamp>.json`.

## Testing without audio

`tasks.py` runs on its own as a text harness, which is the quickest way to check task
dispatch and follow-ups:

```bash
python3 studio/voice/tasks.py "List the active studio projects" --project BD
python3 studio/voice/tasks.py "Draft a reply to the last NORE email" --project NORE --follow-up "Make it shorter"
```

Unit tests use a fake `claude` binary and cover the runner: `pytest studio/tests/test_voice_agent.py`.
