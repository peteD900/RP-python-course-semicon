"""Tests for ElectricalDB (Day 1).

All tests are self-contained: a tiny SQLite DB is created in pytest's tmp_path
fixture, so no dependency on data/generate.py being run first.
"""

import sqlite3

import pandas as pd
import pytest

from fab_toolkit.electrical_db import ElectricalDB


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def test_db(tmp_path):
    """Four-row SQLite database covering three lots and two device types."""
    db = tmp_path / "test_electrical.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE electrical ("
            "lot_id, wafer_id, site_id, x, y, "
            "device_type, vth, idsat, ioff, rsheet, temp_c)"
        )
        conn.executemany(
            "INSERT INTO electrical VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [
                ("L001", "W01", "S01", -60, -60, "TFT",      0.42, 500.0, 1e-10, 150.0, 25.0),
                ("L001", "W01", "S04", -60,   0, "resistor", 0.40, 300.0, 1e-10, 148.0, 25.0),
                ("L002", "W01", "S01", -60, -60, "TFT",      0.43, 510.0, 1e-10, 151.0, 25.0),
                ("L003", "W10", "S01", -60, -60, "TFT",      0.47, 490.0, 1e-10, 150.0, 25.0),
            ],
        )
    return db


# ---------------------------------------------------------------------------
# Construction and repr
# ---------------------------------------------------------------------------

def test_init_succeeds(test_db) -> None:
    db = ElectricalDB(test_db)
    assert db.db_path == test_db


def test_init_bad_path_raises() -> None:
    with pytest.raises(Exception):
        ElectricalDB("/no/such/file.db")


def test_repr_shows_db_name(test_db) -> None:
    db = ElectricalDB(test_db)
    r = repr(db)
    assert "test_electrical" in r
    assert "cached=0" in r


# ---------------------------------------------------------------------------
# fetch() — SQL-level filtering
# ---------------------------------------------------------------------------

def test_fetch_no_filter_returns_all_rows(test_db) -> None:
    assert len(ElectricalDB(test_db).fetch()) == 4


def test_fetch_lots_filters_at_sql_level(test_db) -> None:
    df = ElectricalDB(test_db).fetch(lots=["L001"])
    assert len(df) == 2
    assert set(df["lot_id"]) == {"L001"}


def test_fetch_device_types_filter(test_db) -> None:
    df = ElectricalDB(test_db).fetch(device_types=["TFT"])
    assert len(df) == 3
    assert (df["device_type"] == "TFT").all()


# ---------------------------------------------------------------------------
# fetch_device() — fetch + processing
# ---------------------------------------------------------------------------

def test_fetch_device_tft_adds_vth_columns(test_db) -> None:
    df = ElectricalDB(test_db).fetch_device("TFT")
    assert "vth_zscore" in df.columns
    assert "vth_flag" in df.columns


def test_fetch_device_resistor_adds_rsheet_zscore(test_db) -> None:
    df = ElectricalDB(test_db).fetch_device("resistor")
    assert "rsheet_zscore" in df.columns


def test_fetch_device_unknown_raises(test_db) -> None:
    with pytest.raises(ValueError, match="Unknown device_type"):
        ElectricalDB(test_db).fetch_device("unknown_device")


# ---------------------------------------------------------------------------
# Parquet cache
# ---------------------------------------------------------------------------

def test_save_and_load_parquet_roundtrip(test_db, tmp_path) -> None:
    db = ElectricalDB(test_db)
    df = db.fetch(lots=["L001"])
    cache = tmp_path / "cache" / "l001.parquet"
    db.save_parquet(df, cache)
    df2 = ElectricalDB.load_parquet(cache)
    assert len(df2) == len(df)
    assert list(df2.columns) == list(df.columns)


# ---------------------------------------------------------------------------
# Mutable class-attribute trap (prove cache is per-instance)
# ---------------------------------------------------------------------------

def test_cache_is_per_instance_not_shared(test_db) -> None:
    db1 = ElectricalDB(test_db)
    db2 = ElectricalDB(test_db)
    db1._cache["sentinel"] = pd.DataFrame()
    assert "sentinel" not in db2._cache
