import re
import sys
from pathlib import Path

import pytest

pytest.importorskip("reportlab")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "brand-doc"))
import brand_doc  # noqa: E402


@pytest.fixture(scope="module")
def styles():
    F = brand_doc.register_fonts()
    return brand_doc.build_styles(F), F


def texts(md, styles):
    ST, F = styles
    return [f.text for f in brand_doc.md_to_story(md, ST, F) if hasattr(f, "text")]


def test_wrapped_lines_join_into_one_paragraph(styles):
    out = texts("one\ntwo\nthree\n", styles)
    assert out == ["one two three"]


def test_blank_line_still_separates_paragraphs(styles):
    assert texts("one\ntwo\n\nthree\n", styles) == ["one two", "three"]


def test_two_trailing_spaces_is_a_hard_break(styles):
    out = texts("Bain Design  \nCalle Ejemplo 1  \nMadrid\n", styles)
    assert out == ["Bain Design<br/>Calle Ejemplo 1<br/>Madrid"]


def test_trailing_backslash_is_a_hard_break(styles):
    out = texts("first\\\nsecond\n", styles)
    assert out == ["first<br/>second"]


def test_hard_break_mixed_with_soft_wrap(styles):
    out = texts("a  \nb\nc\n", styles)
    assert out == ["a<br/>b c"]


def test_bold_spanning_a_soft_wrap_still_renders(styles):
    (out,) = texts("some **bold\ntext** here\n", styles)
    assert "bold text" in out and "**" not in out


def test_list_item_continuation_line_joins_the_item(styles):
    out = texts("- first item\n  wrapped on\n- second\n", styles)
    assert len(out) == 2
    assert "first item wrapped on" in out[0]


def test_numbered_list_counts_up(styles):
    out = texts("1. one\n   more\n2. two\n3. three\n", styles)
    assert [re.search(r">(\d+\.)</font></bullet>", t).group(1) for t in out] == ["1.", "2.", "3."]
    assert "one more" in out[0]


def test_block_start_ends_a_running_paragraph(styles):
    out = texts("intro line\n- bullet\n", styles)
    assert out[0] == "intro line" and "bullet" in out[1]
