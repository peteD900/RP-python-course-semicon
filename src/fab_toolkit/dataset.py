"""WaferDataset: a result container with alternate constructors and data-model dunders.

Day 1 introduced ElectricalDB (query interface).
Day 2 builds this class: @classmethod constructors and dunders that make
WaferDataset feel like a native Python container on top of pandas.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from fab_toolkit.electrical_db import ElectricalDB

__all__ = ["WaferDataset"]


class WaferDataset:
    """A pandas DataFrame with a source label and native container behaviour.

    Construct via the @classmethod factories rather than directly:
      WaferDataset.from_db(db, lots=[...], device_type="TFT")
      WaferDataset.from_parquet("cache/tft.parquet")
      WaferDataset.from_csv("export.csv")
    """

    def __init__(self, data: pd.DataFrame, source: str = "unknown") -> None:
        self.data = data
        self.source = source
        self.fetched_at = datetime.now()

    # ------------------------------------------------------------------
    # @classmethod alternate constructors (Day 2)
    # ------------------------------------------------------------------

    @classmethod
    def from_db(
        cls,
        db: ElectricalDB,
        lots: list[str] | None = None,
        device_type: str | None = None,
    ) -> WaferDataset:
        """Construct from an ElectricalDB query.

        Uses fetch_device() when device_type is given (adds processing columns);
        falls back to a plain fetch() for mixed-device datasets.
        """
        from fab_toolkit.electrical_db import ElectricalDB  # runtime import

        if device_type:
            df = db.fetch_device(device_type, lots=lots)
            label = f"ElectricalDB:{db.db_path.name}[{device_type}]"
        else:
            df = db.fetch(lots=lots)
            label = f"ElectricalDB:{db.db_path.name}"
        return cls(df, source=label)

    @classmethod
    def from_parquet(cls, path: str | Path) -> WaferDataset:
        """Load from a parquet file (e.g. a cached query result)."""
        p = Path(path)
        return cls(pd.read_parquet(p), source=f"parquet:{p.name}")

    @classmethod
    def from_csv(cls, path: str | Path, **kwargs) -> WaferDataset:
        """Load from a CSV file. Extra kwargs are forwarded to pd.read_csv."""
        p = Path(path)
        return cls(pd.read_csv(p, **kwargs), source=f"csv:{p.name}")

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        lots = (
            sorted(self.data["lot_id"].unique())
            if "lot_id" in self.data.columns
            else "?"
        )
        return (
            f"WaferDataset("
            f"rows={len(self.data)}, lots={lots}, source={self.source!r})"
        )

    # ------------------------------------------------------------------
    # Data model dunders (Day 2)
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        """Number of measurement rows."""
        return len(self.data)

    def __getitem__(self, key):
        """Delegate all indexing to the underlying DataFrame.

        ds["vth"]            → Series (single column)
        ds[["vth", "idsat"]] → DataFrame (multiple columns)
        ds[bool_mask]        → filtered DataFrame
        """
        return self.data[key]

    def __iter__(self):
        """Iterate over per-wafer sub-DataFrames.

        This is a deliberate design choice: the natural unit of iteration
        for a WaferDataset is a wafer, not an individual row.  Use
        ``ds.data.itertuples()`` if you need row-level iteration.
        """
        for _, group in self.data.groupby(
            ["lot_id", "wafer_id"], sort=False, observed=True
        ):
            yield group.reset_index(drop=True)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WaferDataset):
            return NotImplemented
        return self.data.equals(other.data) and self.source == other.source

    def __contains__(self, lot_id: str) -> bool:
        """``"L001" in ds`` — True if that lot_id appears in the data."""
        return (
            "lot_id" in self.data.columns
            and lot_id in self.data["lot_id"].values
        )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def summary(self) -> pd.DataFrame:
        """Descriptive statistics of all numeric columns."""
        return self.data.describe()

    def lots(self) -> list[str]:
        """Sorted list of lot IDs present in the dataset."""
        if "lot_id" not in self.data.columns:
            return []
        return sorted(self.data["lot_id"].unique())
