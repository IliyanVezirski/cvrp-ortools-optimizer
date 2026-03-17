# CVRP OR-Tools Optimizer

A production-focused CVRP optimizer with:
- Dual solver support (`OR-Tools` and `PyVRP`)
- Dual routing engines (`OSRM` and `Valhalla`)
- Business rules for fleet, center-zone penalties, and warehouse pre-allocation
- Interactive maps, Excel reports, CSV exports, and chart generation
- A desktop Settings GUI and EXE workflow for non-technical users

## Key Features

### 1) Input Sources
- Excel input (`input_source = "excel"`)
- HTTP JSON input (`input_source = "http_json"`)
- Configurable JSON field mapping
- Business-day date logic and optional manual date override

### 2) Solvers
- `OR-Tools`: robust classical routing optimization
- `PyVRP`: alternative ILS-based approach
- Optional parallel OR-Tools strategy races with configurable workers

### 3) Routing Engines
- `OSRM` for fast static routing
- `Valhalla` for richer route cost modeling

### 4) Output Artifacts
- Main interactive map (HTML)
- Per-route HTML maps
- Unified Excel report
- Routes CSV export
- Optional charts (PNG)

### 5) Settings GUI (`config_gui.py`)
Tabbed configuration editor for:
- Input
- Vehicles
- Warehouse
- Solver
- Locations
- Output
- Scheduler

Supports:
- Save
- Save and close
- Save and run

### 6) Windows Scheduler Integration
From the GUI you can:
- Create a scheduled task
- Remove a scheduled task
- Check scheduled task status

## Project Structure

- `main.py` - orchestration entry point
- `main_exe.py` - EXE entry point / runtime bootstrap
- `config.py` - centralized dataclass-based configuration
- `config_gui.py` - desktop configuration UI
- `input_handler.py` - Excel/HTTP JSON loaders and normalization
- `cvrp_solver.py` - OR-Tools implementation
- `pyvrp_solver.py` - PyVRP implementation
- `output_handler.py` - maps, Excel, CSV, and chart generation
- `build_exe.py` - PyInstaller build script

## Quick Start (Python)

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python main.py
```

## Quick Start (Settings GUI)

```bash
python config_gui.py
```

## EXE Build

```bash
python build_exe.py
```

After build, use:
- `CVRP_Optimizer.exe` for optimization
- `Settings.bat` for opening the settings UI
- `start_cvrp.bat` for running optimizer via batch wrapper

## Important Runtime Notes

- Relative paths in config are resolved from the EXE runtime directory.
- Absolute paths are preserved as configured.
- If a directory is provided where a file path is expected (map/csv), the app auto-applies a default filename.

## Configuration Highlights

In `config.py`:
- `input.input_source`: `excel` or `http_json`
- `cvrp.solver_type`: `or_tools` or `pyvrp`
- `cvrp.enable_parallel_solving`: toggle OR-Tools parallel mode
- `output.*`: map, routes, excel, csv, and chart paths

## Troubleshooting

### EXE starts but cannot load paths
- Ensure `config.py` is in the same directory as `CVRP_Optimizer.exe`.
- Use absolute output paths if deploying outside the build folder.

### Scheduler task is created but does not run
- Check Task Scheduler history and account permissions.
- Verify `start_cvrp.bat` exists beside `CVRP_Optimizer.exe`.

### No files are generated
- Confirm the output paths in Settings are valid and writable.
- Check `logs/` for stack traces.

## License

MIT (or project-specific license if changed).
