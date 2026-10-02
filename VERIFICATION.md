# Release verification — 0.0.14

## Summary

Version 0.0.14 keeps the 0.0.13 delivery contract unchanged: after a successful PyInstaller build, `dist/` may contain **only** `README.md` and the executable `SnapBeforeWatchTower`. The change in this release is that all generated build state is consolidated under one separate, gitignored `.build-pyinstaller/` workspace instead of being scattered across project-level `.venv-build/` and `build/` directories.

| Check | Result |
| --- | --- |
| Version increment | PASS — 0.0.13 -> 0.0.14 |
| Offline unit/regression suite | PASS — 50/50 tests |
| Source CLI help | PASS — `--help` exits 0 and documents `-c`, `-h/--help`, and `--version` |
| Source CLI version | PASS — `--version` reports `SnapBeforeWatchTower.py 0.0.14` |
| Python compile check | PASS — all 4 project `.py` files compile in memory |
| Build-script shell syntax | PASS — `bash -n build-pyinstaller.sh` |
| Example TOML parse | PASS — standard-library `tomllib` loads `[application]`, `[mail]`, and `[mqtt]` |
| Configuration coverage | PASS — all 24 example TOML settings are present in `config.example.md` |
| Code-map coverage | PASS — all 29 module-level symbols in `SnapBeforeWatchTower.py` and all 7 in `mqtt_report.py` are named in `commented_code_map.md` |
| Disclaimer consistency | PASS — README and SAFETY carry the same requested disclaimer block |
| Build workspace isolation | PASS — controlled build places venv/pip cache/PyInstaller work/config under `.build-pyinstaller/` only |
| Legacy build locations | PASS — controlled build leaves project-level `build/` and `.venv-build/` absent |
| Git ignore behavior | PASS — `.build-pyinstaller/`, legacy `build/`, legacy `.venv-build/`, and generated `dist/SnapBeforeWatchTower` are ignored; `dist/README.md` remains trackable |
| Clean pre-build dist policy | PASS — build script removes every `dist/` entry except `README.md` before invoking PyInstaller |
| Final dist policy | PASS — build script accepts exactly `README.md` + `SnapBeforeWatchTower` and rejects all other normal/hidden entries |
| Controlled clean-build harness | PASS — stub build ended with exactly `README.md` and `SnapBeforeWatchTower` |
| Controlled extra-artifact rejection | PASS — stub build adding `extra.txt` exited nonzero |
| Runtime dist cleanliness | PASS — existing frozen-runtime regression keeps project logs outside `dist/` |
| Manifest vs 0.0.13 | PASS — same 19 project file paths; no path added or removed |
| PyInstaller/Paho availability in this sandbox | NOT AVAILABLE — neither package is installed locally and PyPI cannot be reached by pip, so no real ELF build is claimed |

## Required final `dist/` layout

After a successful real build:

```text
dist/
├── README.md
└── SnapBeforeWatchTower
```

No dependency folder, build directory, log directory, hidden file, cache, second executable, or other artifact is permitted in `dist/`.

## Generated build workspace

All generated build state is intentionally kept under this gitignored directory:

```text
.build-pyinstaller/
├── config/
├── pip-cache/
├── venv/
└── work/
```

`build-pyinstaller.sh` removes `.build-pyinstaller/` before each build and recreates it from scratch. It also removes the legacy project-level `build/` and `.venv-build/` directories used by older releases. The PyInstaller call receives an explicit `--workpath`, explicit `--distpath`, and `PYINSTALLER_CONFIG_DIR`, while pip receives a build-local cache path.

The static build inputs remain tracked project files because they are required to reproduce the build:

- `build-pyinstaller.sh`
- `SnapBeforeWatchTower.spec`
- `requirements-build.txt`

These are not generated build artifacts and are therefore not placed in or ignored with `.build-pyinstaller/`.

## Controlled build-layout verification

A local stub harness was used because real PyInstaller/Paho are not installed in this sandbox.

The success case produced exactly:

```text
dist/README.md
dist/SnapBeforeWatchTower
```

and generated build state only under:

```text
.build-pyinstaller/config/
.build-pyinstaller/pip-cache/
.build-pyinstaller/venv/
.build-pyinstaller/work/
```

The project-level legacy `build/` and `.venv-build/` directories were absent after the build.

The failure case deliberately produced:

```text
dist/README.md
dist/SnapBeforeWatchTower
dist/extra.txt
```

The build script exited with code 1 and reported that `dist/` must contain exactly `SnapBeforeWatchTower` and `README.md`.

## Runtime log behavior

The existing frozen-runtime log placement remains unchanged:

- source execution: project/source directory -> project `logs/`;
- frozen executable at `.../dist/SnapBeforeWatchTower`: parent project directory -> project-level `logs/`, not `dist/logs/`;
- frozen executable deployed outside a directory named `dist`: executable directory -> `logs/` beside that deployment;
- non-root fallback remains `/tmp/SnapBeforeWatchTower`.

This prevents normal execution from adding a third `dist/` entry.

## Safety/behavior scope

Version 0.0.14 does **not** change:

- snapshot naming or retention calculations;
- `zfs snapshot`, `zfs list`, or `zfs destroy` semantics;
- `continue_on_missing_dataset` or `continue_on_other_failures` behavior;
- dry-run mutation suppression;
- Docker digest capture behavior;
- root enforcement;
- TOML setting names/defaults;
- mail success/failure reporting policy;
- MQTT success/failure reporting policy, payloads, QoS, retain, TLS, authentication, or timeout;
- Home Assistant automation behavior.

## Manifest comparison against 0.0.13

The supplied 0.0.13 archive contained 19 project files. Version 0.0.14 preserves the same 19 paths with no additions or removals. Changes are limited to the versioned application/test fixtures and the build/documentation files required for build-workspace isolation.

The clean source release excludes `.build-pyinstaller/`, legacy `.venv-build/`, legacy `build/`, generated `dist/SnapBeforeWatchTower`, Python bytecode, caches, backups, and temporary files. The tracked `dist/README.md` remains included.

## What was not live-tested

No real ZFS snapshot was created or destroyed. No live Docker digest capture, local mail delivery, MQTT broker/TLS/authentication exchange, Home Assistant automation execution, or Pushover delivery was performed. A real PyInstaller ELF executable was not built in this sandbox because PyInstaller/Paho are not installed and pip cannot currently reach PyPI; the controlled build-layout harness verifies the shell packaging contract instead.
