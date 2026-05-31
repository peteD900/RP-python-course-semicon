"""Pipeline: composes two DataSources and joins their output on lot + wafer.

Introduced in Day 3 as the primary composition example. The Pipeline *has*
an electrical source and a process source — it does not inherit from either.
Depends on the DataSource ABC (or Protocol), not on concrete DB classes.
"""

from __future__ import annotations

import pandas as pd

from fab_toolkit.sources import DataSource

__all__ = ["Pipeline"]


class Pipeline:
    """Fetch from both sources, aggregate per-wafer, and join on lot + wafer.

    Parameters
    ----------
    electrical:
        Any DataSource that returns rows from an electrical measurement table.
    process:
        Any DataSource that returns rows from a process step timing table.

    Swapping out a source for a different backend (real DB, mock, flat file)
    requires no changes here — only the source object changes.
    """

    def __init__(self, electrical: DataSource, process: DataSource) -> None:
        self.electrical = electrical
        self.process = process

    def __repr__(self) -> str:
        return f"Pipeline(electrical={self.electrical!r}, process={self.process!r})"

    def run(
        self,
        lots: list[str] | None = None,
        since: str | None = None,
    ) -> pd.DataFrame:
        """Fetch, aggregate, and join.

        Returns one row per (lot_id, wafer_id) with:
          - ``mean_tft_vth``: mean TFT threshold voltage across PCM sites
          - ``etch_gate_s``:  ETCH_GATE step duration in seconds
        """
        elec = self.electrical.fetch(lots=lots)
        proc = self.process.fetch(lots=lots, since=since)

        # Per-wafer mean Vth (TFT only; other device types handled separately).
        elec_agg = (
            elec.loc[elec["device_type"] == "TFT"]
            .groupby(["lot_id", "wafer_id"], as_index=False)["vth"]
            .mean()
            .rename(columns={"vth": "mean_tft_vth"})
        )

        # Per-wafer ETCH_GATE step duration (one step per wafer by design).
        proc_agg = (
            proc.loc[proc["recipe_step"] == "ETCH_GATE"]
            .groupby(["lot_id", "wafer_id"], as_index=False)["step_seconds"]
            .mean()
            .rename(columns={"step_seconds": "etch_gate_s"})
        )

        return elec_agg.merge(proc_agg, on=["lot_id", "wafer_id"], how="inner")
