#!/usr/bin/env bash
set -euo pipefail

# Update the package list
apt-get update

# Install Python tooling for venvs
apt-get install -y python3 python3-venv python3-pip

# Create virtual environment
python3 -m venv /home/$USER/meltstake-sonar/.venv

# Install requirements
/home/$USER/meltstake-ptv/.venv/bin/pip install -r /home/$USER/meltstake-sonar/requirements.txt

# Install this package
/home/$USER/meltstake-sonar/.venv/bin/pip install -e .