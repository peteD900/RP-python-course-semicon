"""fab_toolkit — semiconductor OOP course utilities.

Grows across the 5-day course:
  Day 1: ElectricalDB — query interface for the PCM electrical database
  Day 2: WaferDataset — result container with alternate constructors + dunders
  Day 3: DataSource ABC, ElectricalSource, ProcessSource, Pipeline
  Day 4: properties, dataclasses, SOLID
  Day 5: capstone wiring
"""

from fab_toolkit.dataset import WaferDataset
from fab_toolkit.electrical_db import ElectricalDB

__all__ = ["ElectricalDB", "WaferDataset"]
