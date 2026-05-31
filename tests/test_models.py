"""Tests for SpecLimits, KpiSpec, PrepConfig, VthAnalysis."""

import pandas as pd
import pytest

from fab_toolkit.models import KpiSpec, PrepConfig, SpecLimits, VthAnalysis


# ---------------------------------------------------------------------------
# SpecLimits
# ---------------------------------------------------------------------------

def test_spec_limits_in_spec() -> None:
    spec = SpecLimits("vth", lower=0.40, upper=0.46)
    s = pd.Series([0.40, 0.42, 0.52])
    assert list(spec.in_spec(s)) == [True, True, False]


def test_spec_limits_yield_pct() -> None:
    spec = SpecLimits("vth", lower=0.40, upper=0.46)
    s = pd.Series([0.40, 0.42, 0.52, 0.60])
    assert spec.yield_pct(s) == pytest.approx(50.0)


def test_spec_limits_bad_range_raises() -> None:
    with pytest.raises(ValueError, match="strictly less than"):
        SpecLimits("vth", lower=0.50, upper=0.38)


def test_spec_limits_frozen() -> None:
    spec = SpecLimits("vth", lower=0.40, upper=0.46)
    with pytest.raises(Exception):   # FrozenInstanceError
        spec.lower = 0.30  # type: ignore[misc]


# ---------------------------------------------------------------------------
# KpiSpec
# ---------------------------------------------------------------------------

def test_kpi_spec_defaults() -> None:
    spec = KpiSpec("vth_check", SpecLimits("vth", 0.40, 0.46))
    assert spec.device_type == "TFT"


# ---------------------------------------------------------------------------
# PrepConfig (mutable — field(default_factory=...) demo)
# ---------------------------------------------------------------------------

def test_prep_config_defaults_are_independent() -> None:
    a = PrepConfig()
    b = PrepConfig()
    a.lots.append("L001")
    assert b.lots == []    # separate list per instance — factory worked


def test_prep_config_device_types_default() -> None:
    cfg = PrepConfig()
    assert cfg.device_types == ["TFT"]


# ---------------------------------------------------------------------------
# VthAnalysis
# ---------------------------------------------------------------------------

@pytest.fixture
def vth_data() -> pd.DataFrame:
    # 4 values in [0.40, 0.46], 1 above — gives 80% yield, 1 fail with vth_spec
    return pd.DataFrame({"vth": [0.41, 0.42, 0.43, 0.44, 0.50]})


@pytest.fixture
def vth_spec() -> SpecLimits:
    return SpecLimits("vth", lower=0.40, upper=0.46)


def test_vth_yield_pct(vth_data: pd.DataFrame, vth_spec: SpecLimits) -> None:
    analysis = VthAnalysis(vth_data, vth_spec)
    assert analysis.yield_pct == pytest.approx(80.0)   # 4/5 in spec


def test_vth_n_fails(vth_data: pd.DataFrame, vth_spec: SpecLimits) -> None:
    analysis = VthAnalysis(vth_data, vth_spec)
    assert analysis.n_fails == 1


def test_vth_yield_updates_when_bounds_change(vth_data: pd.DataFrame, vth_spec: SpecLimits) -> None:
    analysis = VthAnalysis(vth_data, vth_spec)
    old_yield = analysis.yield_pct
    analysis.upper = 0.52          # widen spec — yield should increase
    assert analysis.yield_pct > old_yield


def test_vth_lower_setter_rejects_invalid(vth_data: pd.DataFrame, vth_spec: SpecLimits) -> None:
    analysis = VthAnalysis(vth_data, vth_spec)
    with pytest.raises(ValueError):
        analysis.lower = 0.60   # >= upper — should raise


def test_vth_upper_setter_rejects_invalid(vth_data: pd.DataFrame, vth_spec: SpecLimits) -> None:
    analysis = VthAnalysis(vth_data, vth_spec)
    with pytest.raises(ValueError):
        analysis.upper = 0.30   # <= lower — should raise


def test_vth_repr(vth_data: pd.DataFrame, vth_spec: SpecLimits) -> None:
    analysis = VthAnalysis(vth_data, vth_spec)
    r = repr(analysis)
    assert "VthAnalysis" in r
    assert "yield=" in r
