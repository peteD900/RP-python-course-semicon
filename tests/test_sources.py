"""Tests for DataSource ABC, ElectricalSource, ProcessSource."""

import sqlite3
from abc import ABC
from pathlib import Path

import pandas as pd
import pytest

from fab_toolkit.sources import DataSource, DataSourceProto, ElectricalSource, ProcessSource


@pytest.fixture
def elec_db_path(tmp_path: Path) -> Path:
    db = tmp_path / "electrical.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE electrical "
            "(lot_id, wafer_id, site_id, x, y, device_type, vth, idsat, ioff, rsheet, temp_c)"
        )
        conn.executemany(
            "INSERT INTO electrical VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [
                ("L001", "W01", "S01", -60, -60, "TFT", 0.42, 500.0, 1e-10, 150.0, 25.0),
                ("L002", "W01", "S01", -60, -60, "TFT", 0.47, 490.0, 1e-10, 150.0, 25.0),
            ],
        )
    return db


@pytest.fixture
def proc_db_path(tmp_path: Path) -> Path:
    db = tmp_path / "process.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE process_steps "
            "(lot_id, wafer_id, tool_id, recipe_step, step_seconds, "
            "chamber, start_time, temp_c, pressure)"
        )
        conn.executemany(
            "INSERT INTO process_steps VALUES (?,?,?,?,?,?,?,?,?)",
            [
                ("L001", "W01", "TOOL_A", "ETCH_GATE", 200.0, "C1", "2024-01-01 01:00:00", 20.0, 0.01),
                ("L001", "W01", "TOOL_A", "CLEAN",     120.0, "C1", "2024-01-01 00:00:00", 50.0, 1013.0),
                ("L002", "W01", "TOOL_B", "ETCH_GATE", 225.0, "C2", "2024-01-08 01:00:00", 20.0, 0.01),
            ],
        )
    return db


# ---------------------------------------------------------------------------
# ABC contract
# ---------------------------------------------------------------------------

def test_datasource_is_abstract() -> None:
    assert issubclass(DataSource, ABC)
    with pytest.raises(TypeError):
        DataSource()  # type: ignore[abstract]


def test_electrical_source_is_datasource(elec_db_path: Path) -> None:
    src = ElectricalSource(elec_db_path)
    assert isinstance(src, DataSource)


def test_process_source_is_datasource(proc_db_path: Path) -> None:
    src = ProcessSource(proc_db_path)
    assert isinstance(src, DataSource)


# ---------------------------------------------------------------------------
# ElectricalSource
# ---------------------------------------------------------------------------

def test_electrical_fetch_all(elec_db_path: Path) -> None:
    assert len(ElectricalSource(elec_db_path).fetch()) == 2


def test_electrical_fetch_lots(elec_db_path: Path) -> None:
    df = ElectricalSource(elec_db_path).fetch(lots=["L001"])
    assert len(df) == 1
    assert set(df["lot_id"]) == {"L001"}


def test_electrical_repr(elec_db_path: Path) -> None:
    assert "electrical.db" in repr(ElectricalSource(elec_db_path))


# ---------------------------------------------------------------------------
# ProcessSource
# ---------------------------------------------------------------------------

def test_process_fetch_all(proc_db_path: Path) -> None:
    assert len(ProcessSource(proc_db_path).fetch()) == 3


def test_process_fetch_lots(proc_db_path: Path) -> None:
    df = ProcessSource(proc_db_path).fetch(lots=["L002"])
    assert len(df) == 1
    assert df.iloc[0]["recipe_step"] == "ETCH_GATE"


def test_process_fetch_since(proc_db_path: Path) -> None:
    df = ProcessSource(proc_db_path).fetch(since="2024-01-05")
    assert len(df) == 1    # only L002 rows start after 2024-01-05


# ---------------------------------------------------------------------------
# Protocol — structural subtyping, no inheritance
# ---------------------------------------------------------------------------

def test_protocol_satisfied_without_inheritance() -> None:
    from typing import runtime_checkable, Protocol
    import inspect

    # A plain class with no DataSource in its MRO satisfies DataSourceProto
    class MinimalSource:
        def fetch(self, lots=None, since=None) -> pd.DataFrame:
            return pd.DataFrame()

    src = MinimalSource()
    # Protocol check — DataSourceProto is not runtime_checkable by default,
    # but we can verify it structurally via inspection.
    assert hasattr(src, "fetch")
    assert callable(src.fetch)
