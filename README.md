# CVRP Optimizer

A complete vehicle routing solution for capacitated delivery planning, built for real operational use.

The project solves CVRP (Capacitated Vehicle Routing Problem) with two optimization engines, supports multiple routing backends, applies business-specific constraints, and produces rich outputs for dispatching and analysis.

---

## Table of Contents

- Overview
- Core Capabilities
- System Architecture
- Optimization Workflow
- Input Handling
- Fleet and Business Constraints
- Solver Layer
- Routing Engine Layer
- Output and Reporting
- Settings GUI
- Scheduler Integration
- Configuration Reference
- EXE Runtime Behavior
- Build and Distribution
- Repository Structure
- Quick Start
- Troubleshooting

---

## Overview

CVRP Optimizer is designed to:

- Load customer demand from Excel or HTTP JSON feeds.
- Validate and normalize coordinates and volumes.
- Allocate customers between vehicles and warehouse according to policy limits.
- Build optimized routes with OR-Tools or PyVRP.
- Apply custom business rules (center-zone priorities, penalties, capacity and route limits, optional customer dropping).
- Export operational outputs for dispatching teams.

The system is suitable for daily route planning where constraints change often and non-technical users must be able to tune behavior from a GUI.

---

## Core Capabilities

- Dual solver support:
  - OR-Tools
  - PyVRP
- Dual routing integration:
  - OSRM
  - Valhalla
- Warehouse pre-allocation logic for oversized/filtered customers.
- Center-zone cost shaping and traffic-aware behavior.
- Optional parallel OR-Tools strategy competition.
- Interactive map output:
  - full map
  - per-route maps
- Excel reporting and CSV route export.
- Charts for efficiency and route comparisons.
- Desktop settings editor with save/run workflow.
- Windows Scheduled Task management from GUI.

---

## System Architecture

Main orchestration is in `main.py`.

High-level flow:

1. Load configuration from `config.py`.
2. Load and normalize input data in `input_handler.py`.
3. Split and optimize warehouse allocation in `warehouse_manager.py`.
4. Solve CVRP in `cvrp_solver.py` or `pyvrp_solver.py`.
5. Generate outputs in `output_handler.py`.

Runtime entry points:

- Python mode: `main.py`
- EXE mode: `main_exe.py`
- Configuration UI: `config_gui.py`

---

## Optimization Workflow

1. Read customers and depot/location settings.
2. Validate demand and coordinates.
3. Apply pre-solver business filtering (warehouse/customer constraints).
4. Build solver model and dimensions/constraints.
5. Solve using selected engine and search strategy.
6. Post-process routes (metrics, geometry, summaries).
7. Export map, tabular outputs, and diagnostics.

---

## Input Handling

Input is controlled by `input.input_source` in `config.py`.

Supported modes:

- `excel`
  - Uses `input.excel_file_path`.
- `http_json`
  - Uses `input.json_url` and mapping fields.

HTTP JSON mode features:

- Field mapping for client id, name, volume, GPS, and document number.
- Optional date override.
- Business-day date logic when override is empty.
- Robust parsing for mixed payload quality and encoding variations.

---

## Fleet and Business Constraints

Vehicle model supports:

- Per-type enable/disable.
- Vehicle count per type.
- Capacity per vehicle.
- Time and customer limits per route.
- Service time per stop.
- Optional custom start/depot behavior.

Business rules include:

- Center-zone prioritization and penalties.
- Optional city traffic adjustment.
- Warehouse thresholds and tolerance logic.
- Optional customer skipping with configured disjunction penalty.

---

## Solver Layer

### OR-Tools (`cvrp_solver.py`)

- Classical routing model.
- Supports first-solution and local-search strategy tuning.
- Optional parallel solving setup with configurable worker strategy lists.
- Strong support for custom dimensions and penalties.

Key config keys:

- `cvrp.solver_type = "or_tools"`
- `cvrp.first_solution_strategy`
- `cvrp.local_search_metaheuristic`
- `cvrp.enable_parallel_solving`
- `cvrp.num_workers`
- `cvrp.parallel_first_solution_strategies`
- `cvrp.parallel_local_search_metaheuristics`

### PyVRP (`pyvrp_solver.py`)

- Alternative ILS-style VRP solving.
- Suitable for route-quality-focused scenarios.
- Mapped into the same output contract as OR-Tools.

Key config key:

- `cvrp.solver_type = "pyvrp"`

---

## Routing Engine Layer

### OSRM

- Fast matrix and route geometry generation.
- Good default for static routing workflows.

### Valhalla

- Rich cost behavior and profile support.
- Useful where travel-time realism and profile control are needed.

Routing selection is configured in `config.routing` and corresponding engine sections.

---

## Output and Reporting

Generated artifacts are controlled from `output.*` settings.

Primary outputs:

- Interactive full-route HTML map.
- Per-route HTML maps in a dedicated routes directory.
- Excel report(s) for route and warehouse summaries.
- CSV export for route rows and dispatching pipelines.
- Optional chart image set.

Path behavior:

- Absolute paths are respected.
- Relative paths are resolved from runtime base directory.
- If a directory is provided where a file path is expected (map/csv), default filename is auto-applied.

---

## Settings GUI

`config_gui.py` provides a tabbed editor for all major configuration blocks.

Tabs:

- Input
- Vehicles
- Warehouse
- Solver
- Locations
- Output
- Scheduler

Actions:

- Save
- Save and close
- Save and run

Solver tab includes advanced OR-Tools controls, including parallel strategy lists.

---

## Scheduler Integration

The GUI supports Windows Scheduled Task operations:

- Create task
- Remove task
- Check task status

The scheduled command is generated to run the optimizer from deployment folder context.

---

## Configuration Reference

Main config groups in `config.py`:

- `input`
- `vehicles`
- `warehouse`
- `cvrp`
- `locations`
- `output`
- `routing`
- `osrm`
- `valhalla`
- `logging`
- `cache`
- `performance`

Recommended first settings to verify:

- `input.input_source`
- `cvrp.solver_type`
- `output.map_output_file`
- `output.routes_output_dir`
- `output.excel_output_dir`
- `output.csv_output_file`

---

## EXE Runtime Behavior

`main_exe.py` handles deployment runtime details:

- Uses EXE directory as runtime base.
- Loads `config.py` from the EXE folder.
- Creates required runtime directories.
- Supports `--settings` mode to open configuration UI.

Batch helpers produced by build process:

- `Settings.bat`
- `start_cvrp.bat`

---

## Build and Distribution

Use `build_exe.py` to package the application.

Build script responsibilities:

- Generate spec/version metadata.
- Resolve native dependencies.
- Build EXE via PyInstaller.
- Create runtime helper batch files.
- Copy runtime config where required.

---

## Repository Structure

- `main.py` - Core orchestrator
- `main_exe.py` - EXE bootstrap/runtime logic
- `config.py` - Central dataclass configuration
- `config_gui.py` - Desktop settings editor
- `input_handler.py` - Input loading and normalization
- `warehouse_manager.py` - Warehouse allocation logic
- `cvrp_solver.py` - OR-Tools solver implementation
- `pyvrp_solver.py` - PyVRP solver implementation
- `output_handler.py` - Map/report/chart exporters
- `osrm_client.py` - OSRM integration
- `valhalla_client.py` - Valhalla integration
- `build_exe.py` - Build and packaging pipeline

---

## Quick Start

### Python mode

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python main.py
```

### Settings UI

```bash
python config_gui.py
```

### Build EXE

```bash
python build_exe.py
```

---

## Troubleshooting

### No output files generated

- Verify output paths in Settings.
- Ensure directories are writable.
- Check `logs/` for stack traces.

### EXE cannot find configuration

- Confirm `config.py` is in same folder as `CVRP_Optimizer.exe`.

### Scheduler task exists but does not execute as expected

- Verify user permissions and task run context.
- Confirm `start_cvrp.bat` and `CVRP_Optimizer.exe` are in deployment folder.

### Input not loading

- For Excel mode, verify file path and sheet/column mapping.
- For HTTP JSON mode, verify URL and field mapping.

---

## License

MIT (or project-specific license, if changed in this repository).
