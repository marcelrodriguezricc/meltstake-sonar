# Melt Stake Imagenex Model 881A Controller

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Layout: src](https://img.shields.io/badge/layout-src-informational)
![Platform: Raspberry%20Pi](https://img.shields.io/badge/platform-Raspberry%20Pi-C51A4A)
![OS: Linux](https://img.shields.io/badge/os-Linux-FCC624)

Controller/data handler for integrating the **Imagenex Model 881A Digital Multi-frequency Imaging Sonar** into the Melt Stake system.

## Requirements

- Python **3.11+** (project currently uses Python 3.11.x)
- Target OS: **Debian 13 (Trixie) Lite** (Raspberry Pi)
- Tested on: **Debian 13 (Trixie) Lite** (Raspberry Pi) and **Mac OS**

## Project Layout

This repo uses a **src/** layout:

- Package code: `src/meltstake_sonar/`
- Config files: `configs/`
- Logs: `logs/` (created at runtime)
- Sonar data: `data/` (created at runtime)
- 881A documentation: `docs/`

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

After running, press Enter to start scanning. While scanning, entering "s", "quit", "exit", "q", "stop" will terminate the deployment.

### Arguments

The CLI typically accepts the following arguments:

- `debug`: Prints all logged lines to console for debugging.

- `config`: Filename of configuration file (under `configs/`), e.g. `--config config.toml`, if none specified defaults to `config.toml`.

- `meltstake`: Number of Melt Stake, used for naming of log and data directories.

- `hardware`: Unique hardware identifier, used for naming of log and data directories.


Example: 
```bash
python -m meltstake_sonar --config default_config.toml --meltstake 01 --hardware 2020
```

Config lookup behavior is intended to support filename only (under `configs/`), e.g. `--config config.toml`.

## License

MIT — see [`LICENSE`](LICENSE).