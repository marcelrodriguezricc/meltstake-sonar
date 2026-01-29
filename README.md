# Melt Stake Imagenex Model 881A Controller

Controller/data handler for integrating the **Imagenex Model 881A Digital Multi-frequency Imaging Sonar** into the Melt Stake system.

## Requirements

- Python **3.11+** (project currently uses Python 3.11.x)

## Project Layout

This repo uses a **src/** layout:

- Package code: `src/meltstake_sonar/`
- Config files: `configs/`
- Logs: `logs/` (created at runtime)
- Sonar data: `data/` (created at runtime)
- 881A documentation: `/docs`

## Installation (recommended: virtual environment + editable install)

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

### Arguments

The CLI typically accepts the following arguments:

- `config`: Filename of configuration file (under `configs/`), e.g. `--config config.toml`, if none specified defaults to `config.toml`

- `num_deploy`: Number of deployment, used for naming of log file and directory where scan data `.dat` files will be saved in `data/`.

Example: 
```bash
python -m meltstake_sonar --config config.toml --num_deploy 01
```

Config lookup behavior is intended to support filename only (under `configs/`), e.g. `--config config.toml`

## License

MIT — see [`LICENSE`](LICENSE).