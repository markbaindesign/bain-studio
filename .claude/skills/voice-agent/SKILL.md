---
name: voice-agent
description: Hands-free spoken studio agent. Opens a terminal tab running an OpenAI Realtime voice that hands work to background Claude sessions with full studio access and reads results back. Trigger phrases: "voice agent", "talk to the studio", "/voice-agent".
---

Launch the voice agent in a new Terminator tab:

```bash
terminator --new-tab -e "bash -c 'cd /media/data/dev/bain-studio && python3 studio/voice/agent.py; exec bash'"
```

Flags, added after `agent.py` when asked:
- `--full`: gpt-realtime instead of gpt-realtime-mini. Better at deciding when to start tasks, ~4x cost.
- `--duplex`: mic stays live while the agent speaks, so Mark can interrupt. Headphones only.

Then tell Mark it is running in the new tab. Ctrl+C ends it; the transcript is saved to `/media/data/Dropbox/Work/Studio/context/voice-agent/`.

All behaviour lives in `/media/data/dev/bain-studio/studio/voice/` (agent.py, tasks.py, system-prompt.md). Do not add logic here.
