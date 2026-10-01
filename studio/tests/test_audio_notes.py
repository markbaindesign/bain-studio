import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "collectors"))

import audio_notes as a
import daily_brief as b


def test_recorded_at_parses_obsidian_and_phone_names(tmp_path):
    f = tmp_path / "Recording 20260917172812.m4a"; f.write_bytes(b"x")
    assert a.recorded_at(f) == dt.datetime(2026, 9, 17, 17, 28, 12)
    g = tmp_path / "Audio 2026-09-14 10.40.47.m4a"; g.write_bytes(b"x")
    assert a.recorded_at(g) == dt.datetime(2026, 9, 14, 10, 40, 47)


def test_spoken_hashtags():
    assert a.spoken_hashtags("Hashtag Project a new idea, hash tag skill too") == "#project a new idea, #skill too"


def test_task_ids_tolerate_speech_formatting():
    prefixes = {"FOOB", "KF-WEB", "BSTD", "BD"}
    text = "About FOOB-001, then kf web 120 and BSTD 788, also foob one hundred and BD-7."
    assert a.task_ids(text, prefixes) == ["FOOB-001", "KF-WEB-120", "BSTD-788", "BD-007"]


def test_embed_context_uses_nearest_item_and_heading():
    lines = [
        "## Decisions",
        "",
        "- [ ] [BTF-046](https://app.asana.com/x/46) Allow pattern variants?",
        "- [ ] [BTF-041](https://app.asana.com/x/41) Self-hosted font-loading convention ",
        "![[Recording 20260917173944.m4a]]",
    ]
    ctx = a.embed_context(lines, 4)
    assert ctx["context"] == "BTF-041 Self-hosted font-loading convention"
    assert ctx["heading"] == "Decisions"
    assert ctx["tasks"] == [("BTF-041", "https://app.asana.com/x/41")]


def test_embed_context_skips_other_embeds_and_blank_lines():
    lines = ["- [ ] [SL-1](https://x/1) Item", "", "![[Recording 1.m4a]]", "", "![[Recording 2.m4a]]"]
    assert a.embed_context(lines, 4)["tasks"] == [("SL-1", "https://x/1")]


def test_find_new_audio_skips_done_unsettled_and_non_audio(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIO_NOTES_DIRS", str(tmp_path))
    done, new, fresh, other = (tmp_path / n for n in ("done.m4a", "new.m4a", "fresh.webm", "pic.jpg"))
    for f in (done, new, fresh, other):
        f.write_bytes(b"abc")
    now = dt.datetime.now().timestamp()
    import os
    for f in (done, new, other):
        os.utime(f, (now - 600, now - 600))
    state = {str(done): {"size": 3, "status": "transcribed"}}
    assert a.find_new_audio(state, now=now) == [new]


def test_render_note_marks_unreviewed_and_links_task(tmp_path):
    audio = tmp_path / "Recording 20260917172812.m4a"
    places = [{"note": "2026-09-17-manual-tasks", "context": "BTF-032 Consistent ID", "heading": "Decisions",
               "tasks": [("BTF-032", "https://x/32")]}]
    note = a.render_note(audio, dt.datetime(2026, 9, 17, 17, 28), 58.4, "hello", ["BTF-032"],
                         {"BTF-032": ("Use consistent ID", "https://x/32")}, places)
    assert "reviewed: false" in note and "tasks: [BTF-032]" in note
    assert "**About:** BTF-032 Consistent ID" in note
    assert "[[2026-09-17-manual-tasks]] > Decisions" in note
    assert "- [BTF-032](https://x/32) Use consistent ID" in note


def test_daily_brief_lists_unreviewed_voice_notes(tmp_path, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT", str(tmp_path))
    t = tmp_path / "Transcripts"; t.mkdir()
    (t / "2026-09-05 09.00 voice note.md").write_text(
        "---\nrecorded: 2026-09-05T09:00:00\ntasks: [BTF-032]\nreviewed: false\n---\n\n**About:** BTF-032 Thing\n")
    (t / "2026-09-11 09.00 voice note.md").write_text("---\nrecorded: 2026-09-11T09:00:00\nreviewed: true\n---\n")
    monkeypatch.setattr(b, "COLLECTORS_DIR", tmp_path)
    (tmp_path / "audio_notes_state.json").write_text(json.dumps(
        {"/v/Assets/Recording 1.m4a": {"status": "silent", "mean_db": -64.7, "checked": "2026-09-16"}}))
    found = b.check_voice_notes(dt.date(2026, 9, 17))
    assert [f["title"] for f in found] == ["2026-09-05 09.00 voice note", "Recording 1.m4a was silent"]
    assert found[0]["severity"] == "high" and found[0]["detail"] == "BTF-032 Thing"
