"""Behavioral evals for studio-looper, wired into the normal pytest run.

Unlike test_looper_logic.py (pure functions, instant, free), these invoke the actual
`claude -p '/studio-looper --test ...'` CLI headless against the SLT sandbox project —
real tokens, real (harmless) Asana calls against SLT. That's deliberate: SLT exists only
for this, is never SL or a client repo, and the whole point is catching drift between
what SKILL.md says an agent should do and what a real invocation actually does — a unit
test on the extracted logic alone can't catch that. See studio/evals/studio_looper/README.md.

Each test takes ~30-150s. Run just this file to iterate without the rest of the suite:
    pytest studio/tests/test_looper_evals.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "evals" / "studio_looper"))

from run_evals import (
    eval_concurrency_live_blocks_second_run,
    eval_concurrency_stale_cleared_and_proceeds,
)


def test_concurrency_live_blocks_second_run():
    result = eval_concurrency_live_blocks_second_run()
    assert result.passed, result.detail


def test_concurrency_stale_cleared_and_proceeds():
    result = eval_concurrency_stale_cleared_and_proceeds()
    assert result.passed, result.detail
