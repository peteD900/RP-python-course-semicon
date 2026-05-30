# Semiconductor OOP Python Course

A 5-day hands-on course teaching object-oriented Python through realistic
semiconductor fab data-analysis tasks. Every OOP concept appears because a
real data workflow needs it — no toy `Dog`/`Cat` examples.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for environment management
- [Quarto](https://quarto.org) for rendering lesson notebooks

## Setup

Install the `fab_toolkit` package and dev dependencies:

```bash
uv sync --extra dev
```

## Regenerate data

SQLite databases are gitignored. Generate them before running lessons or tests:

```bash
python data/generate.py
```

This produces `data/electrical.db` (PCM electrical measurements) and
`data/process.db` (process step timing). Both are seeded and fully reproducible.

## Run tests

```bash
uv run pytest
```

## Render a lesson

```bash
quarto render days/day1_classes/day1.qmd
```

Quarto sets the working directory to the `.qmd` file's location; paths inside
the notebook are relative to `days/day1_classes/`. Run the render command from
the repo root.

## Course structure

| Day | Topic | Key concepts |
|-----|-------|--------------|
| 1 | Classes & Instances | `__init__`, `self`, class vs instance attrs, `__repr__` |
| 2 | Methods & Data Model | alternate constructors, `__len__`, `__getitem__`, `__iter__` |
| 3 | Inheritance vs Composition | ABC, `DataSource`, `Pipeline`, `Lot`/`Wafer` |
| 4 | Properties, Dataclasses & SOLID | `@property`, `@dataclass`, Protocol, O/C, DI |
| 5 | Capstone | end-to-end: extract → join → model → wafer map → HTML report |
