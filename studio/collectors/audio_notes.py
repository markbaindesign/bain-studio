#!/usr/bin/env python3
"""
Audio notes — transcribe voice memos recorded into the Obsidian vault.

Finds new audio files (Obsidian's audio recorder saves them to the vault's attachment folder,
currently Work Notes/Assets), skips silent recordings, transcribes the rest with OpenAI, and
writes one transcript note per recording into $OBSIDIAN_VAULT/Transcripts/. The Daily Brief
lists every transcript still marked `reviewed: false`.

Audio files are never moved or renamed: Obsidian embeds each recording in the note that was
open when it was made, and moving the file outside Obsidian would break that embed. Progress
is tracked in studio/collectors/audio_notes_state.json instead (gitignored).

Each transcript note has:
  - frontmatter: recorded, duration, audio file, notes that embed it, task IDs,
    `reviewed: false` (set it to true, or delete the note, once acted on)
  - what it was about: Obsidian inserts the recording at the cursor, so the nearest line above
    the embed (e.g. a checklist item) and its section heading are the memo's context; a task
    linked on that line becomes the memo's task
  - links to any other Asana task spoken by ID ("FOOB-001", "foob 1", "BSTD 788")
  - the transcript, with spoken "hashtag idea" turned into #idea

Nothing is posted to Asana automatically: client projects can have client members, and a
voice memo is not meant for them.

Usage:
  python3 studio/collectors/audio_notes.py              # transcribe new recordings
  python3 studio/collectors/audio_notes.py --dry-run    # list what would be transcribed
  python3 studio/collectors/audio_notes.py --file PATH  # (re)transcribe one file

Env: OPENAI_API_KEY (required), OBSIDIAN_VAULT, AUDIO_NOTES_DIRS (colon-separated folders to
watch; default: the vault root, Assets/ and Audio/), AUDIO_NOTES_MODEL (default whisper-1).

Cron (ops worktree, before the Obsidian collector and the Daily Brief):
  15 8 * * * cd /home/bain/ops/bain-studio && python3 studio/collectors/audio_notes.py >> studio/collectors/audio_notes.log 2>&1
"""

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

COLLECTORS_DIR = Path(__file__).resolve().parent
STUDIO_DIR = COLLECTORS_DIR.parent
load_dotenv(STUDIO_DIR / ".env")

STATE_FILE = COLLECTORS_DIR / "audio_notes_state.json"
PROJECTS_FILE = STUDIO_DIR / "projects.json"
AUDIO_EXTS = {".m4a", ".mp3", ".mp4", ".wav", ".webm", ".ogg", ".flac", ".opus"}
SETTLE_SECONDS = 120          # skip files still being written or synced
SILENT_MEAN_DB = -55.0        # mean volume below this: a mic problem, not a memo
MIN_DURATION_S = 1.5
MAX_UPLOAD_BYTES = 24 * 1024 * 1024
MAX_ATTEMPTS = 3
LOG_PREFIX = "[audio_notes]"


def log(msg):
    print(f"{LOG_PREFIX} {dt.datetime.now():%Y-%m-%d %H:%M:%S} {msg}")


# ---------------------------------------------------------------------------
# Paths and state
# ---------------------------------------------------------------------------

def vault():
    v = os.getenv("OBSIDIAN_VAULT")
    return Path(v) if v else None


def watch_dirs():
    env = os.getenv("AUDIO_NOTES_DIRS")
    if env:
        return [Path(p) for p in env.split(":") if p]
    v = vault()
    return [v, v / "Assets", v / "Audio"] if v else []


def transcripts_dir():
    return vault() / "Transcripts"


def load_state():
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True))


def find_new_audio(state, now=None):
    """Audio files (non-recursive per watched folder) not yet handled, or changed since."""
    now = now or dt.datetime.now().timestamp()
    found = []
    for d in watch_dirs():
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if not p.is_file() or p.suffix.lower() not in AUDIO_EXTS:
                continue
            st = p.stat()
            if now - st.st_mtime < SETTLE_SECONDS:
                continue
            entry = state.get(str(p))
            if entry and entry.get("size") == st.st_size and entry.get("status") in ("transcribed", "silent"):
                continue
            if entry and entry.get("status") == "failed" and entry.get("attempts", 0) >= MAX_ATTEMPTS:
                continue
            found.append(p)
    return found


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------

def probe(path):
    """(duration seconds, mean volume dB) via ffmpeg; (None, None) if ffmpeg is unavailable."""
    try:
        dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "csv=p=0", str(path)], capture_output=True, text=True, timeout=60)
        vol = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "volumedetect",
                              "-f", "null", "-"], capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        return None, None
    m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", vol.stderr)
    try:
        duration = float(dur.stdout.strip())
    except ValueError:
        duration = None
    return duration, (float(m.group(1)) if m else None)


def upload_copy(path):
    """Whisper accepts up to 25 MB: long recordings are re-encoded to small mono MP3 first."""
    if path.stat().st_size <= MAX_UPLOAD_BYTES:
        return path, None
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", "16000",
                    "-b:a", "32k", tmp.name], check=True, timeout=900)
    return Path(tmp.name), Path(tmp.name)


# Names speech recognition otherwise mishears ("Bane Design", "BFT031 JPEG"). Whisper's prompt
# biases spelling towards these; project prefixes are appended at runtime.
VOCABULARY = ("Bain Design, Mark Bain, bainbot, Asana, looper, Obsidian, WordPress, Gutenberg, "
              "Jetpack, Playwright, GnuCash, Cloudways, WP Engine, Upwork, Claude, Ipsum, theme.json")


def transcribe(path, prefixes=()):
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    upload, cleanup = upload_copy(path)
    prompt = VOCABULARY + (". Task IDs like " + ", ".join(f"{p}-001" for p in sorted(prefixes)) if prefixes else "")
    try:
        with open(upload, "rb") as f:
            result = client.audio.transcriptions.create(
                model=os.getenv("AUDIO_NOTES_MODEL", "whisper-1"), file=f, response_format="text",
                prompt=prompt[:800])
    finally:
        if cleanup:
            cleanup.unlink(missing_ok=True)
    return str(result).strip()


# ---------------------------------------------------------------------------
# Transcript processing
# ---------------------------------------------------------------------------

def recorded_at(path):
    """Obsidian names recordings 'Recording YYYYMMDDHHMMSS'; otherwise use the file time."""
    m = re.search(r"(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})", path.stem)
    if m:
        try:
            return dt.datetime(*map(int, m.groups()))
        except ValueError:
            pass
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})[ T_](\d{2})[.:](\d{2})[.:](\d{2})", path.stem)
    if m:
        return dt.datetime(*map(int, m.groups()))
    return dt.datetime.fromtimestamp(path.stat().st_mtime)


def spoken_hashtags(text):
    """'hashtag project' / 'hash tag idea' -> '#project' / '#idea'."""
    return re.sub(r"\bhash[\s-]?tag\s+([A-Za-z][\w-]*)", lambda m: "#" + m.group(1).lower(), text, flags=re.I)


def task_prefixes():
    """Asana task prefixes of registered projects, from their CLAUDE.md."""
    prefixes = set()
    try:
        registry = json.loads(PROJECTS_FILE.read_text())
    except (OSError, ValueError):
        return prefixes
    for entry in registry:
        try:
            text = (Path(entry["path"]).expanduser() / "CLAUDE.md").read_text(errors="replace")
        except OSError:
            continue
        m = re.search(r"ASANA_TASK_PREFIX:\s*(\S+)", text)
        if m:
            prefixes.add(m.group(1))
    return prefixes


def task_ids(text, prefixes):
    """Task IDs as speech recognition writes them: 'FOOB-001', 'foob 1', 'KF web 120', 'BSTD 788'."""
    hits = []
    for prefix in prefixes:
        spoken = r"[\s-]*".join(re.escape(part) for part in prefix.split("-"))
        for m in re.finditer(rf"\b{spoken}[\s-]*(?:number\s+)?0*(\d{{1,4}})\b", text, flags=re.I):
            hits.append((m.start(), f"{prefix}-{int(m.group(1)):03d}"))
    found = []
    for _, lid in sorted(hits):  # in the order they were spoken
        if lid not in found:
            found.append(lid)
    return found


def task_urls(ids):
    """Local ID -> Asana URL, from the project mirrors."""
    wanted, urls = set(ids), {}
    if not wanted:
        return urls
    try:
        registry = json.loads(PROJECTS_FILE.read_text())
    except (OSError, ValueError):
        return urls
    for entry in registry:
        mirror = Path(entry["path"]).expanduser() / "asana-mirror.md"
        if not mirror.exists():
            continue
        for block in re.split(r"\n(?=### )", mirror.read_text(errors="replace")):
            head = re.match(r"### (\S+) — (.*)", block)
            url = re.search(r"- \*\*URL:\*\* (\S+)", block)
            if head and url and head.group(1) in wanted:
                urls.setdefault(head.group(1), (head.group(2).strip(), url.group(1)))
    return urls


LINKED_TASK_RE = re.compile(r"\[([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+)\]\((https?://[^)\s]+)\)")


def embed_context(lines, index):
    """What a recording was about: the nearest non-blank, non-embed line above it, the section
    heading it sits under, and any task linked on that line."""
    context, heading = "", ""
    for line in reversed(lines[:index]):
        stripped = line.strip()
        if not context and stripped and not stripped.startswith("![["):
            context = stripped
        if stripped.startswith("#") and re.match(r"#+\s", stripped):
            heading = re.sub(r"^#+\s*", "", stripped)
            break
    tasks = [(lid, url) for lid, url in LINKED_TASK_RE.findall(context)]
    text = LINKED_TASK_RE.sub(lambda m: m.group(1), context)
    text = re.sub(r"^[-*]\s*(\[[ xX]\]\s*)?", "", text)
    return {"context": text, "heading": heading, "tasks": tasks}


def embeddings(audio):
    """Every place in the vault that embeds this recording, with the item it was recorded against.
    Obsidian inserts ![[file]] at the cursor, so a memo recorded under a checklist item is about it."""
    v = vault()
    found = []
    for md in sorted(v.rglob("*.md")):
        if transcripts_dir() in md.parents or "processed" in md.parts:
            continue
        try:
            lines = md.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines):
            if f"![[{audio.name}" in line:
                found.append({"note": md.relative_to(v).with_suffix("").as_posix(), **embed_context(lines, i)})
    return found


def transcript_path(audio, when):
    base = transcripts_dir() / f"{when:%Y-%m-%d %H.%M} voice note"
    path = Path(str(base) + ".md")
    n = 2
    while path.exists() and f"audio: \"{audio.name}\"" not in path.read_text(errors="replace"):
        path = Path(f"{base} {n}.md")
        n += 1
    return path


def render_note(audio, when, duration, text, ids, urls, places):
    fm = [
        "---",
        "tags: [voice-note, transcript]",
        f"recorded: {when:%Y-%m-%dT%H:%M:%S}",
        f"duration_seconds: {round(duration) if duration else 'unknown'}",
        f"audio: \"{audio.name}\"",
        f"recorded_in: [{', '.join(json.dumps(pl['note']) for pl in places)}]",
        f"tasks: [{', '.join(ids)}]",
        "reviewed: false",
        "---",
        "",
        f"# Voice note - {when:%Y-%m-%d %H:%M}",
        "",
    ]
    for pl in places:
        where = f"[[{pl['note']}]]" + (f" > {pl['heading']}" if pl["heading"] else "")
        fm.append(f"**About:** {pl['context']}" if pl["context"] else f"**Recorded in:** {where}")
        if pl["context"]:
            fm.append(f"**Recorded in:** {where}")
        fm.append("")
    fm += [f"![[{audio.name}]]", ""]
    if ids:
        fm += ["## Tasks", ""]
        for lid in ids:
            name, url = urls.get(lid, ("not found in the mirrors", ""))
            fm.append(f"- [{lid}]({url}) {name}" if url else f"- {lid} ({name})")
        fm.append("")
    fm += ["## Transcript", "", text, "", "---", "",
           "Set `reviewed: true` once acted on; the Daily Brief lists unreviewed voice notes."]
    return "\n".join(fm) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def process(audio, state, dry_run=False):
    st = audio.stat()
    entry = state.get(str(audio), {})
    duration, mean_db = probe(audio)
    if duration is not None and duration < MIN_DURATION_S or mean_db is not None and mean_db < SILENT_MEAN_DB:
        log(f"silent or too short, not transcribed: {audio.name} (duration {duration}s, mean {mean_db} dB)")
        if not dry_run:
            state[str(audio)] = {"size": st.st_size, "status": "silent", "mean_db": mean_db,
                                 "duration": duration, "checked": dt.date.today().isoformat()}
        return "silent"
    if dry_run:
        log(f"would transcribe: {audio} ({duration}s, mean {mean_db} dB)")
        return "dry-run"
    try:
        prefixes = task_prefixes()
        text = spoken_hashtags(transcribe(audio, prefixes))
    except Exception as e:
        attempts = entry.get("attempts", 0) + 1
        state[str(audio)] = {"size": st.st_size, "status": "failed", "attempts": attempts, "error": str(e)[:300]}
        log(f"FAILED ({attempts}/{MAX_ATTEMPTS}) {audio.name}: {e}")
        return "failed"
    when = recorded_at(audio)
    places = embeddings(audio)
    # Tasks the memo was recorded against come first, then any spoken by ID
    ids = [lid for pl in places for lid, _ in pl["tasks"]]
    ids += [lid for lid in task_ids(text, prefixes) if lid not in ids]
    urls = task_urls(ids)
    for pl in places:
        for lid, url in pl["tasks"]:
            urls.setdefault(lid, (pl["context"], url))
    out = transcript_path(audio, when)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_note(audio, when, duration, text, ids, urls, places))
    state[str(audio)] = {"size": st.st_size, "status": "transcribed", "duration": duration,
                         "transcript": out.name, "tasks": ids, "checked": dt.date.today().isoformat()}
    log(f"transcribed {audio.name} -> {out.name} ({len(text)} chars{', tasks ' + ', '.join(ids) if ids else ''})")
    return "transcribed"


def main():
    ap = argparse.ArgumentParser(description="Transcribe voice memos in the Obsidian vault")
    ap.add_argument("--dry-run", action="store_true", help="list what would be transcribed")
    ap.add_argument("--file", help="(re)transcribe one audio file")
    args = ap.parse_args()

    if not vault():
        sys.exit(f"{LOG_PREFIX} OBSIDIAN_VAULT is not set")
    if not args.dry_run and not os.getenv("OPENAI_API_KEY"):
        sys.exit(f"{LOG_PREFIX} OPENAI_API_KEY is not set")

    state = load_state()
    files = [Path(args.file)] if args.file else find_new_audio(state)
    if not files:
        log("no new recordings")
        return
    results = [process(f, state, args.dry_run) for f in files]
    if not args.dry_run:
        save_state(state)
    log(f"done: {len(files)} file(s), " + ", ".join(f"{results.count(r)} {r}" for r in sorted(set(results))))


if __name__ == "__main__":
    main()
