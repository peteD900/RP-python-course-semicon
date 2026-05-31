"""WaferDataset: a lightweight result container.

Day 1 introduces ElectricalDB (the query interface).
Day 2 rebuilds WaferDataset here with @classmethod alternate constructors
(from_db, from_parquet, from_csv) and data-model dunders.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

__all__ = ["WaferDataset"]


class WaferDataset:
    """A pandas DataFrame with a human-readable source label.

    Intentionally minimal in Day 1 — Day 2 adds alternate constructors
    and data-model dunders to make this feel like a native Python container.
    """

    def __init__(
        self,
        data: pd.DataFrame,
        source: str = "unknown",
    ) -> None:
        self.data = data
        self.source = source
        self.fetched_at = datetime.now()

    def __repr__(self) -> str:
        return (
            f"WaferDataset("
            f"rows={len(self.data)}, "
            f"source={self.source!r})"
        )

    def summary(self) -> pd.DataFrame:
        """Descriptive statistics of all numeric columns."""
        return self.data.describe()
