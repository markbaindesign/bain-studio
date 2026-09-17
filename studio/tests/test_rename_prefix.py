import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from rename_prefix import rename_id, rewrite_ids_file, rewrite_mirror


def test_rename_id_keeps_number_and_ignores_other_prefixes():
    assert rename_id("PIPE-063", "PIPE", "UAP") == "UAP-063"
    assert rename_id("PIPE-1000", "PIPE", "UAP") == "UAP-1000"
    assert rename_id("BD-152", "PIPE", "UAP") == "BD-152"
    assert rename_id("PIPELINE-1", "PIPE", "UAP") == "PIPELINE-1"
    assert rename_id(None, "PIPE", "UAP") is None


def test_rewrite_ids_file_only_touches_task_ids(tmp_path):
    f = tmp_path / "asana-ids.json"
    f.write_text(json.dumps({"tasks": {"1": "PIPE-001", "2": "SL-009"},
                             "posted_progress": {"1": "Blocked, see PIPE-001"}, "next_seq": 2}))
    n, data = rewrite_ids_file(f, "PIPE", "UAP")
    assert n == 1
    assert data["tasks"] == {"1": "UAP-001", "2": "SL-009"}
    assert data["posted_progress"] == {"1": "Blocked, see PIPE-001"}
    assert data["next_seq"] == 2


def test_rewrite_mirror_only_headings_and_local_id_lines():
    text = ("### PIPE-057 — Follow up on \"PIPE-046\"\n"
            "- **Local ID:** PIPE-057\n"
            "- **Progress:** Linked to PIPE-046\n"
            "### BD-157 — Perf\n"
            "- **Local ID:** BD-157\n")
    out, n = rewrite_mirror(text, "PIPE", "UAP")
    assert n == 2
    assert "### UAP-057 — Follow up on \"PIPE-046\"" in out
    assert "- **Local ID:** UAP-057" in out
    assert "- **Progress:** Linked to PIPE-046" in out
    assert "### BD-157" in out
