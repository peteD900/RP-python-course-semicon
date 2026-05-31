"""Tests for WaferDataset — Day 2 (alternate constructors + dunders)."""

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from fab_toolkit.dataset import WaferDataset
from fab_toolkit.electrical_db import ElectricalDB


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "lot_id":      ["L001", "L001", "L002", "L002"],
            "wafer_id":    ["W01",  "W01",  "W01",  "W02"],
            "device_type": ["TFT",  "TFT",  "TFT",  "TFT"],
            "vth":         [0.42,   0.43,   0.41,   0.44],
            "idsat":       [500.0,  510.0,  495.0,  505.0],
        }
    )


@pytest.fixture
def dataset(sample_df: pd.DataFrame) -> WaferDataset:
    return WaferDataset(sample_df, source="test")


@pytest.fixture
def elec_db(tmp_path) -> ElectricalDB:
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
                ("L001", "W01", "S04", -60,   0, "resistor", 0.40, 300.0, 1e-10, 148.0, 25.0),
                ("L002", "W01", "S01", -60, -60, "TFT", 0.47, 490.0, 1e-10, 150.0, 25.0),
            ],
        )
    return ElectricalDB(db)


# ---------------------------------------------------------------------------
# Day 1 carryover
# ---------------------------------------------------------------------------

def test_init_stores_data(dataset: WaferDataset, sample_df: pd.DataFrame) -> None:
    assert len(dataset.data) == len(sample_df)
    assert dataset.source == "test"


def test_repr_contains_key_info(dataset: WaferDataset) -> None:
    r = repr(dataset)
    assert "4" in r          # row count
    assert "L001" in r
    assert "test" in r


def test_summary_returns_dataframe(dataset: WaferDataset) -> None:
    result = dataset.summary()
    assert isinstance(result, pd.DataFrame)
    assert "vth" in result.columns


# ---------------------------------------------------------------------------
# @classmethod constructors
# ---------------------------------------------------------------------------

def test_from_db_returns_wafer_dataset(elec_db: ElectricalDB) -> None:
    ds = WaferDataset.from_db(elec_db, lots=["L001"])
    assert isinstance(ds, WaferDataset)
    assert set(ds.data["lot_id"]) == {"L001"}


def test_from_db_with_device_type_adds_processing(elec_db: ElectricalDB) -> None:
    ds = WaferDataset.from_db(elec_db, device_type="TFT")
    assert "vth_flag" in ds.data.columns


def test_from_db_source_label(elec_db: ElectricalDB) -> None:
    ds = WaferDataset.from_db(elec_db, device_type="TFT")
    assert "electrical.db" in ds.source
    assert "TFT" in ds.source


def test_from_parquet_roundtrip(dataset: WaferDataset, tmp_path: Path) -> None:
    pq = tmp_path / "ds.parquet"
    dataset.data.to_parquet(pq)
    ds2 = WaferDataset.from_parquet(pq)
    assert len(ds2) == len(dataset)
    assert "parquet" in ds2.source


def test_from_csv_roundtrip(dataset: WaferDataset, tmp_path: Path) -> None:
    csv = tmp_path / "ds.csv"
    dataset.data.to_csv(csv, index=False)
    ds2 = WaferDataset.from_csv(csv)
    assert len(ds2) == len(dataset)
    assert "csv" in ds2.source


# ---------------------------------------------------------------------------
# Data model dunders
# ---------------------------------------------------------------------------

def test_len_returns_row_count(dataset: WaferDataset) -> None:
    assert len(dataset) == 4


def test_getitem_column(dataset: WaferDataset) -> None:
    col = dataset["vth"]
    assert isinstance(col, pd.Series)
    assert len(col) == 4


def test_getitem_multi_column(dataset: WaferDataset) -> None:
    sub = dataset[["vth", "idsat"]]
    assert isinstance(sub, pd.DataFrame)
    assert list(sub.columns) == ["vth", "idsat"]


def test_iter_yields_per_wafer_groups(dataset: WaferDataset) -> None:
    wafers = list(dataset)
    # sample_df has 2 wafers: L001/W01 (2 rows) and L002/W01 (1 row) and L002/W02 (1 row)
    assert len(wafers) == 3
    assert all(isinstance(w, pd.DataFrame) for w in wafers)


def test_eq_same_data(dataset: WaferDataset, sample_df: pd.DataFrame) -> None:
    ds2 = WaferDataset(sample_df.copy(), source="test")
    assert dataset == ds2


def test_eq_different_source(dataset: WaferDataset, sample_df: pd.DataFrame) -> None:
    ds2 = WaferDataset(sample_df.copy(), source="other")
    assert dataset != ds2


def test_contains_present_lot(dataset: WaferDataset) -> None:
    assert "L001" in dataset


def test_contains_absent_lot(dataset: WaferDataset) -> None:
    assert "L999" not in dataset


def test_lots_returns_sorted_list(dataset: WaferDataset) -> None:
    assert dataset.lots() == ["L001", "L002"]
