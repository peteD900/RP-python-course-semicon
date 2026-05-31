"""Tests for WaferDataset (Day 1 stub; extended in Day 2).

WaferDataset is intentionally minimal in Day 1 — Day 2 adds alternate
constructors and data-model dunders. These tests cover only what exists now.
"""

import pandas as pd
import pytest

from fab_toolkit.dataset import WaferDataset


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "lot_id": ["L001"] * 6,
            "wafer_id": ["W01"] * 6,
            "device_type": ["TFT", "TFT", "resistor", "resistor", "capacitor", "capacitor"],
            "vth": [0.42, 0.43, 0.40, 0.41, 0.39, 0.44],
            "idsat": [500.0, 510.0, 300.0, 310.0, 400.0, 410.0],
        }
    )


@pytest.fixture
def dataset(sample_df: pd.DataFrame) -> WaferDataset:
    return WaferDataset(data=sample_df, source="sqlite:electrical.db")


def test_wafer_dataset_init(dataset: WaferDataset, sample_df: pd.DataFrame) -> None:
    assert len(dataset.data) == len(sample_df)
    assert dataset.source == "sqlite:electrical.db"


def test_wafer_dataset_repr(dataset: WaferDataset) -> None:
    r = repr(dataset)
    assert "6" in r
    assert "sqlite:electrical.db" in r


def test_summary_returns_dataframe(dataset: WaferDataset) -> None:
    result = dataset.summary()
    assert isinstance(result, pd.DataFrame)
    assert "vth" in result.columns
    assert "idsat" in result.columns
