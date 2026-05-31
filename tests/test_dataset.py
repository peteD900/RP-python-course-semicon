"""Tests for WaferDataset (Day 1).

All fixtures are in-memory DataFrames — no SQLite databases required.
"""

from datetime import datetime

import pandas as pd
import pytest

from fab_toolkit.dataset import WaferDataset


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "lot_id": ["L001"] * 6,
            "wafer_id": ["W01"] * 6,
            "device_type": [
                "TFT",
                "TFT",
                "resistor",
                "resistor",
                "capacitor",
                "capacitor",
            ],
            "vth": [0.42, 0.43, 0.40, 0.41, 0.39, 0.44],
            "idsat": [500.0, 510.0, 300.0, 310.0, 400.0, 410.0],
        }
    )


@pytest.fixture
def dataset(sample_df: pd.DataFrame) -> WaferDataset:
    return WaferDataset(
        data=sample_df, source="sqlite:electrical.db", lot_id="L001"
    )


def test_wafer_dataset_init(dataset: WaferDataset, sample_df: pd.DataFrame) -> None:
    assert len(dataset.data) == len(sample_df)
    assert dataset.source == "sqlite:electrical.db"
    assert dataset.lot_id == "L001"
    assert isinstance(dataset.fetched_at, datetime)


def test_wafer_dataset_repr(dataset: WaferDataset) -> None:
    r = repr(dataset)
    assert "L001" in r
    assert "6" in r
    assert "sqlite:electrical.db" in r


def test_filter_device_returns_subset(dataset: WaferDataset) -> None:
    tft_ds = dataset.filter_device("TFT")
    assert len(tft_ds.data) == 2
    assert (tft_ds.data["device_type"] == "TFT").all()


def test_filter_device_immutable(dataset: WaferDataset) -> None:
    original_len = len(dataset.data)
    _ = dataset.filter_device("TFT")
    assert len(dataset.data) == original_len


def test_summary_returns_dataframe(dataset: WaferDataset) -> None:
    result = dataset.summary()
    assert isinstance(result, pd.DataFrame)
    assert "vth" in result.columns
    assert "idsat" in result.columns


@pytest.fixture
def multi_lot_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "lot_id": ["L001", "L001", "L002", "L003", "L003"],
            "wafer_id": ["W01", "W02", "W01", "W01", "W02"],
            "device_type": ["TFT"] * 5,
            "vth": [0.42, 0.43, 0.41, 0.47, 0.48],
        }
    )


def test_filter_lots_returns_only_requested(multi_lot_df: pd.DataFrame) -> None:
    ds = WaferDataset(multi_lot_df, source="sqlite:electrical.db")
    sub = ds.filter_lots(["L001", "L003"])
    assert set(sub.data["lot_id"].unique()) == {"L001", "L003"}
    assert len(sub.data) == 4


def test_filter_lots_single_lot_sets_lot_id(multi_lot_df: pd.DataFrame) -> None:
    ds = WaferDataset(multi_lot_df, source="sqlite:electrical.db")
    sub = ds.filter_lots(["L002"])
    assert sub.lot_id == "L002"


def test_filter_lots_multi_lot_keeps_lot_id_none(multi_lot_df: pd.DataFrame) -> None:
    ds = WaferDataset(multi_lot_df, source="sqlite:electrical.db")
    sub = ds.filter_lots(["L001", "L002"])
    assert sub.lot_id is None


def test_filter_lots_preserves_provenance(multi_lot_df: pd.DataFrame) -> None:
    ds = WaferDataset(multi_lot_df, source="sqlite:electrical.db", lot_id=None)
    sub = ds.filter_lots(["L001"])
    assert sub.source == "sqlite:electrical.db"
    assert sub.fetched_at == ds.fetched_at
