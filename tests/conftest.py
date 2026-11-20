"""Session fixture: run the full pipeline once, then all tests read its output.

This keeps the suite fast (one ~10s run) and honest: tests assert on
the artefacts the real CLI produces, not on hand-built fixtures.
"""

from __future__ import annotations

import pytest

from dat_gov.cli import cmd_all


@pytest.fixture(scope="session", autouse=True)
def _pipeline():
    assert cmd_all() == 0
