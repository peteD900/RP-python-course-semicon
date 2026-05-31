"""ElectricalDB: a query interface for the PCM electrical test database.

Introduced in Day 1. Shows why a class earns its keep over raw sqlite3 calls:
connection management, parameterised SQL filter building, device-type-specific
processing, and local parquet caching all belong together.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

__all__ = ["ElectricalDB"]

# Device types present in the electrical table.
DEVICE_TYPES = {"TFT", "resistor", "capacitor"}


class ElectricalDB:
    """Query interface for the PCM electrical test SQLite database.

    Parameters
    ----------
    db_path:
        Path to the SQLite file produced by ``data/generate.py``.

    The connection is tested on construction so a bad path fails immediately,
    not mid-notebook when you try to fetch data.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._cache: dict[str, pd.DataFrame] = {}   # per-instance; see Day 1 §4
        # fail-fast: verify the file is reachable and is a valid SQLite DB
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("SELECT 1")

    def __repr__(self) -> str:
        return (
            f"ElectricalDB("
            f"db={self.db_path.name!r}, "
            f"cached={len(self._cache)} queries)"
        )

    # ------------------------------------------------------------------
    # Core fetch
    # ------------------------------------------------------------------

    def fetch(
        self,
        lots: list[str] | None = None,
        device_types: list[str] | None = None,
        since: str | None = None,
    ) -> pd.DataFrame:
        """Query the electrical table with SQL-level filtering.

        Filters are pushed into the WHERE clause so only the requested rows
        are transferred from disk. On a production fab DB with millions of rows
        you never want ``SELECT *`` followed by in-process filtering.

        Parameters
        ----------
        lots:
            Restrict to these lot IDs, e.g. ``["L001", "L003"]``.
        device_types:
            Restrict to these device types, e.g. ``["TFT"]``.
        since:
            ISO date string; rows with ``lot_id`` alphabetically >= this value
            are returned. (Electrical rows have no timestamp; this is a
            placeholder for the join with process.db in Day 5.)
        """
        clauses: list[str] = []
        params: list = []

        if lots:
            placeholders = ",".join("?" * len(lots))
            clauses.append(f"lot_id IN ({placeholders})")
            params.extend(lots)

        if device_types:
            placeholders = ",".join("?" * len(device_types))
            clauses.append(f"device_type IN ({placeholders})")
            params.extend(device_types)

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM electrical {where}"

        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql(sql, conn, params=params)

    # ------------------------------------------------------------------
    # Device-type-aware fetch + processing
    # ------------------------------------------------------------------

    def fetch_device(
        self,
        device_type: str,
        lots: list[str] | None = None,
        since: str | None = None,
    ) -> pd.DataFrame:
        """Fetch rows for one device type and apply its specific processing.

        Each device type has different columns that matter and different QC
        checks, so it makes sense to bundle fetch + munge into one call.
        """
        if device_type not in DEVICE_TYPES:
            raise ValueError(
                f"Unknown device_type {device_type!r}. "
                f"Expected one of {sorted(DEVICE_TYPES)}."
            )
        df = self.fetch(lots=lots, device_types=[device_type], since=since)
        return self._process(df, device_type)

    def _process(self, df: pd.DataFrame, device_type: str) -> pd.DataFrame:
        """Dispatch to the device-specific processor."""
        processors = {
            "TFT":       self._process_tft,
            "resistor":  self._process_resistor,
            "capacitor": self._process_capacitor,
        }
        return processors[device_type](df)

    def _process_tft(self, df: pd.DataFrame) -> pd.DataFrame:
        """TFT-specific QC: z-score Vth and flag statistical outliers."""
        df = df.copy()
        mu, sigma = df["vth"].mean(), df["vth"].std()
        df["vth_zscore"] = (df["vth"] - mu) / sigma
        df["vth_flag"] = df["vth_zscore"].abs() > 2.5
        return df

    def _process_resistor(self, df: pd.DataFrame) -> pd.DataFrame:
        """Resistor-specific QC: z-score sheet resistance."""
        df = df.copy()
        mu, sigma = df["rsheet"].mean(), df["rsheet"].std()
        df["rsheet_zscore"] = (df["rsheet"] - mu) / sigma
        return df

    def _process_capacitor(self, df: pd.DataFrame) -> pd.DataFrame:
        """Capacitor rows: placeholder, extended in later days."""
        return df.copy()

    # ------------------------------------------------------------------
    # Local parquet cache
    # ------------------------------------------------------------------

    def save_parquet(self, df: pd.DataFrame, path: str | Path) -> None:
        """Persist a query result to parquet for fast reload next session."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(p, index=False)

    @staticmethod
    def load_parquet(path: str | Path) -> pd.DataFrame:
        """Load a previously saved parquet file.

        This is a ``@staticmethod`` because it doesn't need to know anything
        about the database — it's a convenience loader namespaced to the class.
        Day 2 will show ``@classmethod`` for constructors that *do* need the
        class itself.
        """
        return pd.read_parquet(path)
