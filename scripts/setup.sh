#!/bin/bash
set -euo pipefail

# Re-run as root (needed to create the venv in /root)
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  exec sudo -H "$0" "$@"
fi

# Update the package list
apt-get update

# Install Python tooling for venvs
apt-get install -y python3 python3-venv python3-pip

# Create + activate a virtual environment in /root
VENV_DIR="/root/meltstake-venv"
if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

# Optional but recommended: update packaging tools inside the venv
python -m pip install --upgrade pip setuptools wheel

# Install the desired package (replace 'your-package' with the actual package name)
apt-get install -y your-package

# Clean up
apt-get autoremove -y

echo "Installation complete! Virtual env active at: $VENV_DIR"