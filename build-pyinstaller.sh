#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PYINSTALLER_VENV:-${PROJECT_DIR}/.venv-build}"

python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install -r "${PROJECT_DIR}/requirements-build.txt"

cd "${PROJECT_DIR}"
rm -rf build dist
"${VENV_DIR}/bin/pyinstaller" --noconfirm --clean SnapBeforeWatchTower.spec

test -x "${PROJECT_DIR}/dist/SnapBeforeWatchTower"
"${PROJECT_DIR}/dist/SnapBeforeWatchTower" --help >/dev/null
"${PROJECT_DIR}/dist/SnapBeforeWatchTower" --version

cat > "${PROJECT_DIR}/dist/README.md" <<'DOC'
# PyInstaller output

The standalone Linux executable produced by `build-pyinstaller.sh` is:

```text
dist/SnapBeforeWatchTower
```

It bundles Python and Paho MQTT. ZFS, Docker, and the local `mail` command remain external host requirements.
DOC
