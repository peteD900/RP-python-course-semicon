"""Synthetic fab data generator.

Produces two SQLite databases in the same directory as this script:
  electrical.db  — PCM electrical test results (5,625 rows)
  process.db     — process step timing records (~5 steps × 5 lots × 25 wafers)

Run from any directory:
    python data/generate.py

The generator is seeded (RANDOM_SEED = 42) and fully reproducible.
No third-party libraries required — stdlib only.

Baked-in signal (the capstone storyline):
  LOT003, wafers W10-W18 show a +0.05 V Vth shift.
  The corresponding ETCH_GATE step on chamber C2 runs ~25 s longer than nominal.
  Day 5 recovers this correlation via OLS regression.
"""

import math
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

RANDOM_SEED = 42

# --- Site definitions ---------------------------------------------------
# 9 fixed PCM sites on every wafer; coordinates in mm from wafer centre.
PCM_SITES: dict[str, dict] = {
    "S01": {"x": -60, "y": -60, "device_type": "TFT"},
    "S02": {"x":   0, "y": -60, "device_type": "TFT"},
    "S03": {"x":  60, "y": -60, "device_type": "TFT"},
    "S04": {"x": -60, "y":   0, "device_type": "resistor"},
    "S05": {"x":   0, "y":   0, "device_type": "resistor"},
    "S06": {"x":  60, "y":   0, "device_type": "resistor"},
    "S07": {"x": -60, "y":  60, "device_type": "capacitor"},
    "S08": {"x":   0, "y":  60, "device_type": "capacitor"},
    "S09": {"x":  60, "y":  60, "device_type": "capacitor"},
}

# Wafer numbers that carry the LOT003 defect (1-indexed, inclusive).
DEFECT_WAFER_RANGE = range(10, 19)  # W10–W18

# --- Process step definitions -------------------------------------------
RECIPE_STEPS: list[dict] = [
    {"step": "CLEAN",              "seconds": 120,  "temp_c": 50.0,  "pressure": 1013.0},
    {"step": "DEPOSIT_GATE_OXIDE", "seconds": 480,  "temp_c": 850.0, "pressure": 0.1},
    {"step": "ETCH_GATE",          "seconds": 200,  "temp_c": 20.0,  "pressure": 0.01},
    {"step": "ANNEAL",             "seconds": 3600, "temp_c": 950.0, "pressure": 1013.0},
    {"step": "MEASURE_THICKNESS",  "seconds": 30,   "temp_c": 25.0,  "pressure": 1013.0},
]

# Tool IDs available per step (tool assignment is random but seeded).
TOOLS = ["TOOL_A", "TOOL_B", "TOOL_C"]
CHAMBERS = ["C1", "C2"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _Rng:
    """Thin wrapper around a seeded random.Random for clarity."""

    def __init__(self, seed: int) -> None:
        import random
        self._r = random.Random(seed)

    def gauss(self, mu: float, sigma: float) -> float:
        return self._r.gauss(mu, sigma)

    def choice(self, seq):
        return self._r.choice(seq)

    def uniform(self, a: float, b: float) -> float:
        return self._r.uniform(a, b)


def _lot_id(n: int) -> str:
    return f"L{n:03d}"


def _wafer_id(n: int) -> str:
    return f"W{n:02d}"


# ---------------------------------------------------------------------------
# electrical.db
# ---------------------------------------------------------------------------

def _generate_electrical(rng: _Rng) -> list[tuple]:
    rows: list[tuple] = []

    for lot_num in range(1, 6):          # L001–L005
        lot = _lot_id(lot_num)
        for wafer_num in range(1, 26):   # W01–W25
            wafer = _wafer_id(wafer_num)
            is_defect_lot = lot == "L003" and wafer_num in DEFECT_WAFER_RANGE

            for site_id, site in PCM_SITES.items():
                x: int = site["x"]
                y: int = site["y"]
                device: str = site["device_type"]

                # Spatial edge uplift (proportional to distance from centre).
                edge_factor = max(abs(x), abs(y)) / 60.0   # 0.0 at centre, 1.0 at corners
                edge_vth_uplift = 0.008 * edge_factor

                # Lot-level baseline noise (wafer-to-wafer).
                wafer_noise = rng.gauss(0.0, 0.003)

                # Measurement noise.
                meas_noise = rng.gauss(0.0, 0.004)

                vth_base = 0.42
                vth_defect = 0.05 if is_defect_lot else 0.0
                vth = vth_base + wafer_noise + meas_noise + vth_defect + edge_vth_uplift

                # idsat: device-type dependent baseline.
                idsat_base = {"TFT": 500.0, "resistor": 300.0, "capacitor": 400.0}[device]
                idsat = idsat_base + rng.gauss(0.0, 10.0)

                # ioff: slight inverse relationship with vth (higher vth → lower ioff).
                ioff_base = 0.1e-9
                ioff = max(1e-12, ioff_base - 0.05e-9 * (vth - 0.42) + rng.gauss(0.0, 5e-12))

                # rsheet: relevant mainly for resistor sites.
                rsheet = 150.0 + rng.gauss(0.0, 3.0)

                temp_c = 25.0

                rows.append((
                    lot, wafer, site_id, x, y, device,
                    round(vth, 6),
                    round(idsat, 4),
                    round(ioff, 15),
                    round(rsheet, 4),
                    temp_c,
                ))

    return rows


def _write_electrical(db_path: Path, rows: list[tuple]) -> None:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS electrical")
    cur.execute("""
        CREATE TABLE electrical (
            lot_id      TEXT    NOT NULL,
            wafer_id    TEXT    NOT NULL,
            site_id     TEXT    NOT NULL,
            x           INTEGER NOT NULL,
            y           INTEGER NOT NULL,
            device_type TEXT    NOT NULL,
            vth         REAL,
            idsat       REAL,
            ioff        REAL,
            rsheet      REAL,
            temp_c      REAL
        )
    """)
    cur.executemany(
        "INSERT INTO electrical VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows
    )
    con.commit()
    con.close()


# ---------------------------------------------------------------------------
# process.db
# ---------------------------------------------------------------------------

def _generate_process(rng: _Rng) -> list[tuple]:
    rows: list[tuple] = []
    epoch = datetime(2024, 1, 1, 0, 0, 0)

    for lot_num in range(1, 6):
        lot = _lot_id(lot_num)
        # Advance the clock by a random inter-lot gap.
        t = epoch + timedelta(days=(lot_num - 1) * 7)

        for wafer_num in range(1, 26):
            wafer = _wafer_id(wafer_num)
            is_defect_lot = lot == "L003" and wafer_num in DEFECT_WAFER_RANGE

            for step_def in RECIPE_STEPS:
                step_name = step_def["step"]
                baseline_s = step_def["seconds"]
                base_temp = step_def["temp_c"]
                base_pressure = step_def["pressure"]

                tool_id = rng.choice(TOOLS)

                # For the defect lot/wafers, ETCH_GATE always runs on chamber C2.
                # This makes the signal detectable in the capstone analysis.
                if is_defect_lot and step_name == "ETCH_GATE":
                    chamber = "C2"
                else:
                    chamber = rng.choice(CHAMBERS)

                # Apply drift: LOT003 + C2 + ETCH_GATE runs ~25 s long.
                drift = 0.0
                if is_defect_lot and step_name == "ETCH_GATE" and chamber == "C2":
                    drift = 25.0

                step_seconds = baseline_s + rng.gauss(0.0, 5.0) + drift
                temp_c = base_temp + rng.gauss(0.0, 0.5)
                pressure = base_pressure * (1.0 + rng.gauss(0.0, 0.01))

                start_time = t.isoformat(sep=" ")
                t += timedelta(seconds=max(1.0, step_seconds) + rng.uniform(5, 30))

                rows.append((
                    lot, wafer, tool_id, step_name,
                    round(max(1.0, step_seconds), 2),
                    chamber,
                    start_time,
                    round(temp_c, 2),
                    round(pressure, 6),
                ))

    return rows


def _write_process(db_path: Path, rows: list[tuple]) -> None:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS process_steps")
    cur.execute("""
        CREATE TABLE process_steps (
            lot_id       TEXT NOT NULL,
            wafer_id     TEXT NOT NULL,
            tool_id      TEXT NOT NULL,
            recipe_step  TEXT NOT NULL,
            step_seconds REAL NOT NULL,
            chamber      TEXT NOT NULL,
            start_time   TEXT NOT NULL,
            temp_c       REAL,
            pressure     REAL
        )
    """)
    cur.executemany(
        "INSERT INTO process_steps VALUES (?,?,?,?,?,?,?,?,?)", rows
    )
    con.commit()
    con.close()


# ---------------------------------------------------------------------------
# Sanity check
# ---------------------------------------------------------------------------

def _check_signal(db_path: Path) -> None:
    """Print average Vth per lot to verify the LOT003 shift is visible."""
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("""
        SELECT lot_id, ROUND(AVG(vth), 4) as mean_vth
        FROM electrical
        WHERE device_type = 'TFT'
        GROUP BY lot_id
        ORDER BY lot_id
    """)
    print("\nMean TFT Vth by lot (LOT003 should be ~0.05 V higher):")
    for row in cur.fetchall():
        marker = " <-- DEFECT LOT" if row[0] == "L003" else ""
        print(f"  {row[0]}: {row[1]:.4f} V{marker}")
    con.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    data_dir = Path(__file__).parent
    elec_db = data_dir / "electrical.db"
    proc_db = data_dir / "process.db"

    rng = _Rng(RANDOM_SEED)

    print("Generating electrical.db …")
    elec_rows = _generate_electrical(rng)
    _write_electrical(elec_db, elec_rows)
    print(f"  {len(elec_rows):,} rows → {elec_db}")

    print("Generating process.db …")
    proc_rows = _generate_process(rng)
    _write_process(proc_db, proc_rows)
    print(f"  {len(proc_rows):,} rows → {proc_db}")

    _check_signal(elec_db)
    print("\nDone. Both databases are ready.")


if __name__ == "__main__":
    main()
