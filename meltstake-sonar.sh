#!/usr/bin/env bash
set -euo pipefail

# Set the directory
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate virtual environment
source "$DIR/.venv/bin/activate"

# Execute the main script
exec python -u "$DIR/source/main.py"