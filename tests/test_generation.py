"""Generation: counts, determinism, and dirty rows present in raw."""

from __future__ import annotations

import csv
from pathlib import Path

from dat_gov.config import RAW_DIR
from dat_gov.generate import generate_all


def _rows(name: str) -> list[dict]:
    with (RAW_DIR / f"{name}.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_counts_are_in_the_right_ballpark():
    assert len(_rows("departments")) == 8
    assert len(_rows("courses")) == 41  # 40 clean + 1 duplicate
    assert len(_rows("faculty")) == 82
    assert len(_rows("sections")) == 123
    assert len(_rows("applicants")) == 5120
    assert len(_rows("students")) == 3090
    assert 11_500 <= len(_rows("enrollments")) <= 12_500
    assert 9_500 <= len(_rows("tuition_charges")) <= 11_000
    assert len(_rows("payments")) == 6150
    assert len(_rows("financial_aid")) == 2060
    assert len(_rows("applications")) == 5330


def test_generation_is_deterministic(tmp_path: Path):
    a, b = tmp_path / "a", tmp_path / "b"
    generate_all(a)
    generate_all(b)
    for name in ("applicants", "enrollments", "tuition_charges", "students"):
        assert (a / f"{name}.csv").read_bytes() == (b / f"{name}.csv").read_bytes()


def test_dirty_rows_present_in_raw():
    apps = _rows("applicants")
    assert any(r["email"] == "not-an-email" for r in apps)
    assert any(r["email"] == "" for r in apps)
    assert any(r["date_of_birth"] == "2031-01-15" for r in apps)
    assert len(apps) - len({r["applicant_id"] for r in apps}) >= 40  # duplicates
    assert any(float(r["amount"]) < 0 for r in _rows("tuition_charges"))
    assert any(r["course_id"] == "XX999" for r in _rows("enrollments"))
    assert any(r["term"] == "2099-Winter" for r in _rows("applications"))
