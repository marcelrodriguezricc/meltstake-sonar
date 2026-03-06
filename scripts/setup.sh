#!/usr/bin/env bash
set -euo pipefail

# Update the package list
apt-get update

# Install Python tooling for venvs
apt-get install -y python3 python3-venv python3-pip

# Create virtual machine
python3 -m venv /home/$USER/meltstake-sonar/.venv

# Install requirements
pip install -r requirements.txt

# Install this package
python -m pip install -e .