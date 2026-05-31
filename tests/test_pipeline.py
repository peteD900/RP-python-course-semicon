"""Tests for Pipeline — composition of two DataSources."""

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from fab_toolkit.pipeline import Pipeline
from fab_toolkit.sources import ElectricalSource, ProcessSource


@pytest.fixture
def sources(tmp_path: Path):
    """Create minimal electrical + process DBs and return both sources."""
    elec = tmp_path / "electrical.db"
    with sqlite3.connect(elec) as conn:
        conn.execute(
            "CREATE TABLE electrical "
            "(lot_id, wafer_id, site_id, x, y, device_type, vth, idsat, ioff, rsheet, temp_c)"
        )
        conn.executemany(
            "INSERT INTO electrical VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [
                # L001/W01: two TFT sites
                ("L001", "W01", "S01", -60, -60, "TFT", 0.42, 500.0, 1e-10, 150.0, 25.0),
                ("L001", "W01", "S02",   0, -60, "TFT", 0.43, 505.0, 1e-10, 150.0, 25.0),
                # L002/W01: two TFT sites (higher Vth = simulated defect)
                ("L002", "W01", "S01", -60, -60, "TFT", 0.47, 490.0, 1e-10, 150.0, 25.0),
                ("L002", "W01", "S02",   0, -60, "TFT", 0.48, 495.0, 1e-10, 150.0, 25.0),
            ],
        )

    proc = tmp_path / "process.db"
    with sqlite3.connect(proc) as conn:
        conn.execute(
            "CREATE TABLE process_steps "
            "(lot_id, wafer_id, tool_id, recipe_step, step_seconds, "
            "chamber, start_time, temp_c, pressure)"
        )
        conn.executemany(
            "INSERT INTO process_steps VALUES (?,?,?,?,?,?,?,?,?)",
            [
                ("L001", "W01", "TOOL_A", "ETCH_GATE", 200.0, "C1", "2024-01-01 01:00:00", 20.0, 0.01),
                ("L002", "W01", "TOOL_B", "ETCH_GATE", 225.0, "C2", "2024-01-08 01:00:00", 20.0, 0.01),
            ],
        )

    return ElectricalSource(elec), ProcessSource(proc)


def test_pipeline_repr(sources) -> None:
    elec, proc = sources
    p = Pipeline(elec, proc)
    r = repr(p)
    assert "Pipeline" in r
    assert "ElectricalSource" in r


def test_pipeline_run_returns_dataframe(sources) -> None:
    elec, proc = sources
    result = Pipeline(elec, proc).run()
    assert isinstance(result, pd.DataFrame)


def test_pipeline_run_one_row_per_wafer(sources) -> None:
    elec, proc = sources
    result = Pipeline(elec, proc).run()
    assert len(result) == 2    # L001/W01 and L002/W01


def test_pipeline_run_has_expected_columns(sources) -> None:
    elec, proc = sources
    result = Pipeline(elec, proc).run()
    assert "mean_tft_vth" in result.columns
    assert "etch_gate_s" in result.columns


def test_pipeline_run_aggregates_vth(sources) -> None:
    elec, proc = sources
    result = Pipeline(elec, proc).run()
    l001 = result[result["lot_id"] == "L001"].iloc[0]
    assert abs(l001["mean_tft_vth"] - 0.425) < 0.001  # mean of 0.42, 0.43


def test_pipeline_run_lots_filter(sources) -> None:
    elec, proc = sources
    result = Pipeline(elec, proc).run(lots=["L001"])
    assert len(result) == 1
    assert result.iloc[0]["lot_id"] == "L001"


def test_pipeline_accepts_any_datasource(sources) -> None:
    """Pipeline works with any object satisfying the DataSource interface."""
    import pandas as pd

    class StubElectrical:
        def fetch(self, lots=None, since=None):
            return pd.DataFrame({
                "lot_id": ["L001"], "wafer_id": ["W01"],
                "device_type": ["TFT"], "vth": [0.42],
            })

    class StubProcess:
        def fetch(self, lots=None, since=None):
            return pd.DataFrame({
                "lot_id": ["L001"], "wafer_id": ["W01"],
                "recipe_step": ["ETCH_GATE"], "step_seconds": [200.0],
            })

    result = Pipeline(StubElectrical(), StubProcess()).run()
    assert len(result) == 1
