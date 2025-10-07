#!/usr/bin/env bash
set -euo pipefail

# Simple bootstrapper for the PDF pipeline project.
#
# Usage:
#   ./scripts/setup.sh                # create .venv and install core deps
#   INSTALL_NOUGAT=1 ./scripts/setup.sh  # optionally install heavy Nougat extras
#
# Environment variables:
#   PYTHON          - Python interpreter to use (default: python3)
#   VENV_DIR        - Target directory for the virtual environment (default: .venv)
#   INSTALL_NOUGAT  - If set to 1, install requirements-nougat.txt
#
# The script prints the commands it executes for transparency.

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PYTHON_BIN=${PYTHON:-python3}
VENV_DIR=${VENV_DIR:-"$PROJECT_ROOT/.venv"}
INSTALL_NOUGAT=${INSTALL_NOUGAT:-0}

run() {
  echo "> $*"
  "$@"
}

if [[ ! -d "$VENV_DIR" ]]; then
  run "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

run pip install --upgrade pip
run pip install -r "$PROJECT_ROOT/requirements.txt"

if [[ "$INSTALL_NOUGAT" == "1" ]]; then
  run pip install -r "$PROJECT_ROOT/requirements-nougat.txt"
fi

echo
python - <<'PY'
from pathlib import Path
from textwrap import indent
import json

config_path = Path("config/config.example.json")
if config_path.is_file():
    data = json.loads(config_path.read_text(encoding="utf-8"))
    print("Konfiguration (config/config.example.json):")
    print(indent(json.dumps(data, indent=2, ensure_ascii=False), "  "))
else:
    print("Hinweis: Keine Beispielkonfiguration gefunden.")
PY

echo
cat <<'MSG'
Setup abgeschlossen! Aktivieren Sie die Umgebung mit:
  source "$VENV_DIR/bin/activate"

Passen Sie anschließend Ihre Konfiguration an (siehe docs/setup/configuration.md).
MSG
