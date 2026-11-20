"""Session fixture: run the full pipeline once in a temp directory."""

from __future__ import annotations

import shutil

import pytest

from dat_gov.cli import cmd_all
from dat_gov.config import PROJECT_ROOT


@pytest.fixture(scope="session")
def pipeline_root(tmp_path_factory):
    root = tmp_path_factory.mktemp("datgov")
    shutil.copytree(PROJECT_ROOT / "governance", root / "governance")
    assert cmd_all(root) == 0
    return root


@pytest.fixture(scope="session")
def project_root():
    return PROJECT_ROOT
