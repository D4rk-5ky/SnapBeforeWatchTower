#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# Informational/invalid arguments must exit before deleting artifacts or creating
# the build environment. Read the version from source without importing the app.
if (( $# > 0 )); then
    if (( $# != 1 )); then
        echo "ERROR: expected no arguments, --help, or --version. See --help." >&2
        exit 2
    fi
    case "$1" in
        -h|--help)
            cat <<'HELP'
Usage: build-pyinstaller.sh [--help | --version]

With no arguments, rebuild dist/SnapBeforeWatchTower using requirements-build.txt.
Requires Linux, Python 3.11+, venv support, and access to the pinned dependencies.
The build replaces .build-pyinstaller/, removes legacy build/ and .venv-build/,
and removes every dist/ entry except README.md before writing the executable.
Run it only in a project copy whose generated artifacts may be replaced.

Options (used alone):
  -h, --help  Show this help and exit without creating or removing files.
  --version   Show the application source version and exit without build work.

The build bundles Python/Paho MQTT; zfs, docker and mail remain host tools.
After building, --help/--version smoke checks and the two-file dist/ check run.
HELP
            exit 0
            ;;
        --version)
            python3 -B -c 'import ast, pathlib, sys
module = ast.parse(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
version = next(ast.literal_eval(node.value) for node in module.body
               if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == "__version__"
                       for target in node.targets))
print("SnapBeforeWatchTower build helper " + version)' "${PROJECT_DIR}/SnapBeforeWatchTower.py"
            exit 0
            ;;
        *)
            echo "ERROR: unknown argument. Use --help or --version, or no arguments to build." >&2
            exit 2
            ;;
    esac
fi

BUILD_ROOT="${PROJECT_DIR}/.build-pyinstaller"
VENV_DIR="${BUILD_ROOT}/venv"
WORK_DIR="${BUILD_ROOT}/work"
CONFIG_DIR="${BUILD_ROOT}/config"
PIP_CACHE_DIR="${BUILD_ROOT}/pip-cache"

# All generated build state belongs under one gitignored directory. Remove the
# current build root first so each build starts from a clean state. Also remove
# the legacy project-level locations used by older releases.
rm -rf -- "${BUILD_ROOT}" "${PROJECT_DIR}/build" "${PROJECT_DIR}/.venv-build"
mkdir -p -- "${BUILD_ROOT}" "${WORK_DIR}" "${CONFIG_DIR}" "${PIP_CACHE_DIR}"

python3 -m venv "${VENV_DIR}"
PIP_CACHE_DIR="${PIP_CACHE_DIR}" "${VENV_DIR}/bin/python" -m pip install -r "${PROJECT_DIR}/requirements-build.txt"

cd "${PROJECT_DIR}"

# dist/ is a protected delivery directory. Keep only the tracked README before
# building; every stale executable, hidden file, directory, or other artifact is removed.
mkdir -p dist
find dist -mindepth 1 -maxdepth 1 ! -name README.md -exec rm -rf -- {} +

DIST_README="${PROJECT_DIR}/dist/README.md"
test -f "${DIST_README}"

# Keep PyInstaller work/cache/config output outside dist/ and outside the project
# root. Only the final one-file executable is written to dist/.
PYINSTALLER_CONFIG_DIR="${CONFIG_DIR}" \
"${VENV_DIR}/bin/pyinstaller" \
    --noconfirm \
    --clean \
    --workpath "${WORK_DIR}" \
    --distpath "${PROJECT_DIR}/dist" \
    SnapBeforeWatchTower.spec

EXECUTABLE="${PROJECT_DIR}/dist/SnapBeforeWatchTower"
test -f "${EXECUTABLE}"
test -x "${EXECUTABLE}"

# Smoke-test the frozen CLI. These informational commands must not create
# additional dist/ files or directories.
"${EXECUTABLE}" --help >/dev/null
"${EXECUTABLE}" --version

# dist/ is intentionally limited to exactly two entries: the executable and
# the tracked README. Hidden files/directories and any other artifacts are errors.
shopt -s nullglob dotglob
DIST_ENTRIES=("${PROJECT_DIR}/dist/"*)
shopt -u nullglob dotglob

EXPECTED_EXECUTABLE="${PROJECT_DIR}/dist/SnapBeforeWatchTower"
EXPECTED_README="${PROJECT_DIR}/dist/README.md"

if (( ${#DIST_ENTRIES[@]} != 2 )); then
    echo "ERROR: dist/ must contain exactly SnapBeforeWatchTower and README.md." >&2
    printf 'Found: %s\n' "${DIST_ENTRIES[@]}" >&2
    exit 1
fi

FOUND_EXECUTABLE=false
FOUND_README=false
for entry in "${DIST_ENTRIES[@]}"; do
    case "${entry}" in
        "${EXPECTED_EXECUTABLE}") FOUND_EXECUTABLE=true ;;
        "${EXPECTED_README}") FOUND_README=true ;;
        *)
            echo "ERROR: unexpected dist/ entry: ${entry}" >&2
            exit 1
            ;;
    esac
done

if [[ "${FOUND_EXECUTABLE}" != true || "${FOUND_README}" != true ]]; then
    echo "ERROR: dist/ must contain exactly SnapBeforeWatchTower and README.md." >&2
    printf 'Found: %s\n' "${DIST_ENTRIES[@]}" >&2
    exit 1
fi

# The legacy project-level build locations must stay absent. If PyInstaller or a
# future build change recreates either one, fail instead of silently scattering
# generated build state around the project tree.
for legacy_path in "${PROJECT_DIR}/build" "${PROJECT_DIR}/.venv-build"; do
    if [[ -e "${legacy_path}" ]]; then
        echo "ERROR: generated build state escaped .build-pyinstaller/: ${legacy_path}" >&2
        exit 1
    fi
done

printf 'Build complete. dist/ contains only: %s and %s\n' "${EXECUTABLE}" "${DIST_README}"
printf 'Generated build work is isolated under: %s\n' "${BUILD_ROOT}"
