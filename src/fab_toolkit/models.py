"""Dataclasses, spec objects, and analysis classes with @property.

Introduced in Day 4. Demonstrates:
  - @dataclass(frozen=True) for immutable config objects
  - field(default_factory=...) for mutable defaults (ties back to Day 1 trap)
  - @property for computed values and validated setters
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

__all__ = ["SpecLimits", "KpiSpec", "PrepConfig", "VthAnalysis"]


@dataclass(frozen=True)
class SpecLimits:
    """Immutable spec window for a single electrical parameter.

    ``frozen=True`` makes instances hashable and prevents accidental mutation —
    the right choice for a spec that should be set once and trusted everywhere.
    """

    parameter: str
    lower: float
    upper: float

    def __post_init__(self) -> None:
        if self.lower >= self.upper:
            raise ValueError(
                f"lower ({self.lower}) must be strictly less than upper ({self.upper})"
            )

    def in_spec(self, series: pd.Series) -> pd.Series:
        """Boolean mask: True where values fall within [lower, upper]."""
        return series.between(self.lower, self.upper)

    def yield_pct(self, series: pd.Series) -> float:
        """Percentage of values within spec."""
        return 100.0 * self.in_spec(series).mean()


@dataclass(frozen=True)
class KpiSpec:
    """Links a KPI name to its spec limits and the device type it applies to."""

    name: str
    spec: SpecLimits
    device_type: str = "TFT"


@dataclass
class PrepConfig:
    """Mutable configuration for a data preparation job.

    Uses ``field(default_factory=...)`` for list defaults — the @dataclass
    equivalent of the mutable class-attribute trap from Day 1.  Without it,
    every PrepConfig instance would share the *same* list object.
    """

    lots: list[str] = field(default_factory=list)
    device_types: list[str] = field(default_factory=lambda: ["TFT"])
    since: str | None = None


class VthAnalysis:
    """Vth spec analysis with computed properties and validated bound setters.

    Introduced in Day 4 to demonstrate @property: ``yield_pct`` and
    ``n_fails`` are *computed* (no stored value to go stale); ``lower``
    and ``upper`` use setters that reject invalid ranges immediately.
    """

    def __init__(self, data: pd.DataFrame, spec: SpecLimits) -> None:
        self._data = data
        self._lower = spec.lower
        self._upper = spec.upper

    def __repr__(self) -> str:
        return (
            f"VthAnalysis("
            f"lower={self._lower}, upper={self._upper}, "
            f"yield={self.yield_pct:.1f}%)"
        )

    # ------------------------------------------------------------------
    # Computed properties — derived from data + current bounds on access
    # ------------------------------------------------------------------

    @property
    def yield_pct(self) -> float:
        """Percentage of Vth measurements within [lower, upper]."""
        return 100.0 * self._data["vth"].between(self._lower, self._upper).mean()

    @property
    def n_fails(self) -> int:
        """Count of measurements outside spec."""
        return int((~self._data["vth"].between(self._lower, self._upper)).sum())

    # ------------------------------------------------------------------
    # Validated bound accessors
    # ------------------------------------------------------------------

    @property
    def lower(self) -> float:
        return self._lower

    @lower.setter
    def lower(self, value: float) -> None:
        if value >= self._upper:
            raise ValueError(f"lower ({value}) must be < upper ({self._upper})")
        self._lower = value

    @property
    def upper(self) -> float:
        return self._upper

    @upper.setter
    def upper(self, value: float) -> None:
        if value <= self._lower:
            raise ValueError(f"upper ({value}) must be > lower ({self._lower})")
        self._upper = value
