"""DataSource ABC and concrete sources for electrical and process databases.

Introduced in Day 3. The ABC defines the interface; concrete classes plug in.
Swapping SQLite for a real database later means writing a new subclass — the
Pipeline and everything above it stay untouched.
"""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol

import pandas as pd

from fab_toolkit.electrical_db import ElectricalDB

__all__ = ["DataSource", "ElectricalSource", "ProcessSource", "DataSourceProto"]


class DataSource(ABC):
    """Abstract base: anything that can fetch fab data as a DataFrame.

    Subclass and implement ``fetch()`` to plug a new backend into the Pipeline
    without touching any downstream code.
    """

    @abstractmethod
    def fetch(
        self,
        lots: list[str] | None = None,
        since: str | None = None,
    ) -> pd.DataFrame:
        """Return a DataFrame of records, optionally filtered by lot or date."""
        ...


class ElectricalSource(DataSource):
    """DataSource for the PCM electrical database.

    Wraps ElectricalDB (Day 1) via composition: ElectricalSource *has* an
    ElectricalDB rather than inheriting from it. The ABC interface is what
    Pipeline depends on; ElectricalDB is an implementation detail.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db = ElectricalDB(db_path)   # composition: has-a, not is-a

    def __repr__(self) -> str:
        return f"ElectricalSource(db={self._db.db_path.name!r})"

    def fetch(
        self,
        lots: list[str] | None = None,
        since: str | None = None,     # electrical rows have no timestamp; ignored
    ) -> pd.DataFrame:
        return self._db.fetch(lots=lots)


class ProcessSource(DataSource):
    """DataSource for the process step timing database."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    def __repr__(self) -> str:
        return f"ProcessSource(db={self.db_path.name!r})"

    def fetch(
        self,
        lots: list[str] | None = None,
        since: str | None = None,
    ) -> pd.DataFrame:
        clauses: list[str] = []
        params: list = []

        if lots:
            clauses.append(f"lot_id IN ({','.join('?' * len(lots))})")
            params.extend(lots)
        if since:
            clauses.append("start_time >= ?")
            params.append(since)

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql(
                f"SELECT * FROM process_steps {where}", conn, params=params
            )


# ---------------------------------------------------------------------------
# Protocol alternative: structural subtyping — no inheritance required.
# Any class with a matching fetch() signature satisfies this automatically.
# ---------------------------------------------------------------------------

class DataSourceProto(Protocol):
    """Lighter alternative to DataSource ABC for dependency inversion.

    A class satisfies this Protocol if it has a compatible ``fetch()``
    method — no explicit inheritance needed. Useful for testing (mock
    objects, simple lambdas) where inheriting from an ABC is overkill.
    """

    def fetch(
        self,
        lots: list[str] | None = None,
        since: str | None = None,
    ) -> pd.DataFrame:
        ...
