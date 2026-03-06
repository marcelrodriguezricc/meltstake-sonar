#!/usr/bin/env bash
set -euo pipefail

# Update the package list
apt-get update

# Install Python tooling for venvs
apt-get install -y python3 python3-venv python3-pip

# Create virtual environment
python3 -m venv /home/$USER/meltstake-sonar/.venv

# Install requirements (using venv's pip directly)
/home/$USER/meltstake-sonar/.venv/bin/pip install -r requirements.txt

# Install this package (using venv's pip directly)
/home/$USER/meltstake-sonar/.venv/bin/pip install -e .