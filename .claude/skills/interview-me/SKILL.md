---
name: interview-me
description: Real-time voice interview using the grill-me persona. Launches OpenAI Realtime API session. Takes a topic arg.
---

Launch a real-time voice interview session.

### Usage
/interview-me {topic}

### Steps

1. Parse the topic from the user's message (everything after `/interview-me`).
   If no topic given, ask: "What do you want to be interviewed on?"

2. Open a new Terminator tab and run the script there:
   ```bash
   terminator --new-tab -e "bash -c 'python3 ~/bin/interview_me.py --topic \"{topic}\"; exec bash'"
   ```
   Add `--full` before the closing quote for a more rigorous session (uses gpt-realtime, ~4x cost).

   The `exec bash` keeps the tab open after the script exits so the user can see any output.

3. Tell the user the session is running in the new terminal tab. The transcript will be saved to `~/.claude/transcripts/interview-{topic}-{date}.md` on exit (Ctrl+C).
