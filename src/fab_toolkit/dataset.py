"""WaferDataset: a DataFrame wrapper with fab metadata.

Introduced in Day 1. Extended with alternate constructors in Day 2.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

__all__ = ["WaferDataset"]


class WaferDataset:
    """A pandas DataFrame paired with metadata about its fab origin.

    Parameters
    ----------
    data:
        The measurement DataFrame (rows = individual measurements).
    source:
        Human-readable origin string, e.g. ``'sqlite:electrical.db'``.
    lot_id:
        Optional lot identifier; ``None`` when the dataset spans multiple lots.
    fetched_at:
        Timestamp of retrieval; defaults to ``datetime.now()`` at construction.
    """

    def __init__(
        self,
        data: pd.DataFrame,
        source: str,
        lot_id: str | None = None,
        fetched_at: datetime | None = None,
    ) -> None:
        self.data = data
        self.source = source
        self.lot_id = lot_id
        self.fetched_at = fetched_at if fetched_at is not None else datetime.now()

    def __repr__(self) -> str:
        return (
            f"WaferDataset("
            f"lot={self.lot_id!r}, "
            f"rows={len(self.data)}, "
            f"source={self.source!r})"
        )

    def summary(self) -> pd.DataFrame:
        """Descriptive statistics of all numeric columns."""
        return self.data.describe()

    def filter_device(self, device_type: str) -> WaferDataset:
        """Return a new WaferDataset containing only rows for *device_type*.

        The original dataset is never modified.
        """
        mask = self.data["device_type"] == device_type
        return WaferDataset(
            data=self.data.loc[mask].copy(),
            source=self.source,
            lot_id=self.lot_id,
            fetched_at=self.fetched_at,
        )

    def filter_lots(self, lot_ids: list[str]) -> WaferDataset:
        """Return a new WaferDataset containing only rows for the given lots.

        Useful when a dataset spans many lots and a review narrows to a subset,
        e.g. ``ds.filter_lots(["L001", "L003"])``. The returned dataset carries
        a concrete ``lot_id`` only when a single lot remains; otherwise it stays
        ``None`` to signal a multi-lot dataset. Provenance (``source``,
        ``fetched_at``) is preserved so the subset never loses track of where it
        came from.
        """
        mask = self.data["lot_id"].isin(lot_ids)
        remaining_lot = lot_ids[0] if len(lot_ids) == 1 else None
        return WaferDataset(
            data=self.data.loc[mask].copy(),
            source=self.source,
            lot_id=remaining_lot,
            fetched_at=self.fetched_at,
        )
