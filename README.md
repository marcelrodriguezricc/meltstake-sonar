# Melt Stake Imagenex Model 881A Controller - by Marcel Rodriguez-Riccelli

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Layout: src](https://img.shields.io/badge/layout-src-informational)
![Platform: Raspberry%20Pi](https://img.shields.io/badge/platform-Raspberry%20Pi-C51A4A)
![OS: Linux](https://img.shields.io/badge/os-Linux-FCC624)

Controller/data handler for integrating the **Imagenex Model 881A Digital Multi-frequency Imaging Sonar** into the Melt Stake system, with additional parsing and visualization tools.

## Requirements

- Python **3.11+** (project currently uses Python 3.11.x)
- Target OS: **Debian 13 (Trixie) Lite** (Raspberry Pi)
- Tested on: **Debian 13 (Trixie) Lite** (Raspberry Pi) and **Mac OS**
- Optional: **MATLAB** for sonar data parsing and visualization

## Project Layout

This repo uses a **src/** layout:

- Package code: `src/meltstake_sonar/`
- Config files: `configs/`
- Sonar data: `data/` (created at runtime unless different directory is specified)
- 881A documentation: `docs/`
- Shell scripts for run and setup on Linux: `scripts/`
- Secondary programs: `tools/`
- Tests: `tests/`

## Installation

From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

## Usage

Run the package entrypoint from the repo root:

```bash
python -m meltstake_sonar
```

If you prefer not to install the package, you can run using `PYTHONPATH`:

```bash
PYTHONPATH=src python -m meltstake_sonar
```

After initialization, press Enter to start scanning. While scanning, entering "s", "quit", "exit", "q", "stop" will terminate the deployment.

### Arguments

The CLI typically accepts the following arguments:

- `debug`: Prints all logged lines to console for debugging.

- `config`: Filename of configuration file (under `configs/`), e.g. `--config config.toml`, if none specified defaults to `default_config.toml`.

- `data`: Path where data, logs, and other files created at runtime will be stored (default: ROOT/data).


Example: 
```bash
python -m meltstake_sonar --config default_config.toml --data /Users/me/Desktop/ms01_2026-02-09_2020
```

Config lookup behavior is intended to support filename only (under `configs/`), e.g. `--config config.toml`.

## Tools

- ### Raw Sonar Data to CSV Converter (binary_convert) - by Louis Ross

    Converts sonar scan .dat files to a single RunData.csv file.

    **Requirements**

    A directory which contains:
        - `RunIndex.csv` - an indexed list of time, type, and name of all sonarScanX.dat files,
        - One or many `sonarScanX.dat` files - contains raw sonar data

    **Usage**

    From repository root run:

    ```bash
    python -m tools.binary_convert.main /path/to/sonar/data
    ```

- ### MATLAB Parser & Visualizer (matlab_parser)- original by Kaelan Weiss, modified by Marcel Rodriguez-Riccelli

    **parse881a.m**

    After binary_convert, use RunIndex.csv and RunData.csv to generate a MATLAB struct.

    From `tools/matlab_parser`, run:

    ```bash
    matlab -batch "parse881a('/path/to/sonar881a;','data_folder','/path/to/csvs')"
    ```

    **visualize881a.m**

    After generating a MATLAB struct, generate a polar graph of each scan.

    From `tools/matlab_parser`, run:

    ```bash
    matlab -batch "visualize881a('/path/to/struct')"
    ```

## License

MIT — see [`LICENSE`](LICENSE).