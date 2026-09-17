---
tags: [tool, collector, voice]
god: hermes
command: python3 studio/collectors/audio_notes.py
description: Transcribes voice memos recorded in the Obsidian vault into transcript notes, with the checklist item each memo was recorded against; unreviewed ones appear in the Daily Brief
---

# Audio notes

Record a voice memo in Obsidian and it gets heard. A morning job finds new recordings in the
Work Notes vault, transcribes them with OpenAI, and writes one note per memo to
`Work Notes/Transcripts/`. The Daily Brief lists every transcript still marked
`reviewed: false` under **Voice notes**.

## Recording

Obsidian core plugin **Audio recorder** (Settings > Core plugins). Desktop: microphone icon in
the ribbon, or Ctrl+P > "Audio recorder: Start recording". Mobile: command palette, or add the
command to the mobile toolbar. Recordings land in the attachment folder (`Work Notes/Assets/`)
and are embedded at the cursor.

**Record against the item.** Put the cursor on the line after a checklist item (e.g. in a
manual tasks note) before recording. The transcript takes that line as its context, and a task
linked on it (`[BTF-032](https://app.asana.com/...)`) becomes the memo's task. Saying a task ID
out loud ("BSTD 788") also links it.

Short memos, one per item, beat one long recording: the cost is the same (billed per minute of
audio), each memo keeps its context, and one bad take doesn't spoil the rest.

## Run

```bash
python3 studio/collectors/audio_notes.py              # transcribe new recordings
python3 studio/collectors/audio_notes.py --dry-run    # list what would be transcribed
python3 studio/collectors/audio_notes.py --file PATH  # (re)transcribe one file
```

Cron (ops worktree, before the Obsidian collector and the Daily Brief):

```
15 8 * * * cd /home/bain/ops/bain-studio && python3 studio/collectors/audio_notes.py >> studio/collectors/audio_notes.log 2>&1
```

## How it works

- Watches the vault root, `Assets/` and `Audio/` (override: `AUDIO_NOTES_DIRS`). Files modified in
  the last 2 minutes are left for the next run (still recording or syncing).
- Audio is **never moved or renamed**, because that would break the embed in the note. Progress
  lives in `studio/collectors/audio_notes_state.json` (gitignored).
- Recordings under 1.5 s or with mean volume below -55 dB are not sent for transcription; the
  Daily Brief reports them as silent (usually the wrong mic input).
- Model: `whisper-1` ($0.006/minute when built; override with `AUDIO_NOTES_MODEL`, e.g.
  `gpt-4o-mini-transcribe`). A prompt of studio vocabulary and project prefixes keeps names like
  Bain Design, bainbot and Jetpack spelled right. Files over 24 MB are re-encoded to mono MP3.
- Spoken "hashtag idea" becomes `#idea` in the transcript.
- **Nothing is posted to Asana.** Client projects can have client members, and a memo isn't meant
  for them. Act on transcripts in a Claude session, then set `reviewed: true`.

## Transcript note

Frontmatter: `recorded`, `duration_seconds`, `audio`, `recorded_in`, `tasks`, `reviewed`. Body:
what it was about (the item above the embed and its section), where it was recorded, the audio
embed, task links, then the transcript.

## Related

- [daily-brief.md](daily-brief.md) — lists unreviewed transcripts and silent recordings
- `bain-tools/transcribe` — the manual CLI this grew out of
