"""fab_toolkit — semiconductor OOP course utilities.

Day 1: ElectricalDB        — query interface, SQL filter building, device dispatch
Day 2: WaferDataset        — result container, @classmethod constructors, dunders
Day 3: DataSource / Pipeline — ABC, composition, Protocol
Day 4: SpecLimits / VthAnalysis / ReportRenderer — dataclasses, @property, SOLID
Day 5: capstone wires it all together
"""

from fab_toolkit.dataset import WaferDataset
from fab_toolkit.electrical_db import ElectricalDB
from fab_toolkit.models import KpiSpec, PrepConfig, SpecLimits, VthAnalysis
from fab_toolkit.pipeline import Pipeline
from fab_toolkit.reports import HTMLRenderer, MarkdownRenderer, ReportRenderer
from fab_toolkit.sources import DataSource, DataSourceProto, ElectricalSource, ProcessSource

__all__ = [
    # Day 1
    "ElectricalDB",
    # Day 2
    "WaferDataset",
    # Day 3
    "DataSource",
    "DataSourceProto",
    "ElectricalSource",
    "ProcessSource",
    "Pipeline",
    # Day 4
    "SpecLimits",
    "KpiSpec",
    "PrepConfig",
    "VthAnalysis",
    "ReportRenderer",
    "HTMLRenderer",
    "MarkdownRenderer",
]
