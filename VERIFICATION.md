# Release verification — 0.0.11

Date: 2026-10-02

## Result

| Check | Result |
| --- | --- |
| Version increment | PASS — 0.0.10 -> 0.0.11 |
| Python unit/regression suite | PASS — 49/49 tests |
| Python compile checks | PASS — all application/test Python files compile successfully in memory |
| Source CLI help | PASS — `-h` and `--help` exit 0 and document `-c CONFIG` plus `--version` |
| Source CLI version | PASS — `--version` exits 0 and reports `SnapBeforeWatchTower.py 0.0.11` |
| Public CLI boundary | PASS — operational values remain TOML-only; the private MQTT worker switch is accepted only by a frozen executable |
| Frozen MQTT worker design | PASS — unit regression proves frozen publishing re-executes only the standalone binary plus `--mqtt-publish-worker`; broker config/password remain in stdin JSON rather than argv |
| Frozen worker entry point | PASS — unit regression proves frozen `--mqtt-publish-worker` invokes the worker without requiring `-c CONFIG` |
| Frozen log directory | PASS — unit regression proves frozen mode uses the executable directory; source mode keeps the source directory; non-root fallback remains `/tmp/SnapBeforeWatchTower` |
| PyInstaller spec | PASS — one-file console executable named `SnapBeforeWatchTower`; all `paho` submodules explicitly collected |
| Build requirements | PASS — `requirements-build.txt` pins `pyinstaller==6.22.3` and `paho-mqtt==2.1.0` |
| Build script syntax/layout | PASS — shell syntax valid; script builds from project root, cleans stale `build/`/`dist/`, targets `dist/SnapBeforeWatchTower`, then smoke-tests frozen `--help` and `--version` |
| Third-party runtime module audit | PASS — application runtime uses only Python standard library plus Paho MQTT; Paho is explicitly included by the spec |
| Existing dry-run success/failure reporting | PASS — combined mail+MQTT dry-run success regression and failure-report regressions remain green |
| Continuation behavior | PASS — missing-dataset and other checked per-dataset list/destroy continue/stop behavior remains unchanged and covered |
| Dry-run mutation safety | PASS — create/destroy/log deletion/Docker digest capture remain suppressed; snapshot listing remains real |
| Configuration compatibility | PASS — no TOML setting names/defaults changed in 0.0.11 |
| TOML example/documentation coverage | PASS — `config-example.toml` parses with 24 assignments across `[application]`, `[mail]`, and `[mqtt]`; every setting is represented in README.md and `config.example.md` |
| Home Assistant integration | PASS — MQTT payload contract is unchanged and the supplied HA automation parses successfully as YAML |
| Disclaimer | PASS — requested disclaimer text remains present in both README.md and SAFETY.md |
| `.gitignore` build handling | PASS — generated `dist/SnapBeforeWatchTower`, `.venv-build/`, and `build/` are ignored; `dist/README.md` and shipped examples remain trackable |
| Cache/build/temp exclusion | PASS — prepared release tree contains no `.venv-build`, `build/`, `__pycache__`, `.pyc`, `.pyo`, `.pytest_cache`, backup, or temporary artifacts |
| Actual PyInstaller binary build in this sandbox | NOT RUN — PyInstaller/Paho were not preinstalled and the sandbox could not resolve/reach PyPI/files.pythonhosted.org, so build dependencies could not be installed |

## PyInstaller build behavior

The included build entry point is:

```bash
./build-pyinstaller.sh
```

It creates/uses `.venv-build`, installs `requirements-build.txt`, builds the one-file Linux executable, and verifies:

```text
dist/SnapBeforeWatchTower --help
dist/SnapBeforeWatchTower --version
```

The build is fail-fast: if the executable is not created or either smoke check fails, the script exits nonzero.

`SnapBeforeWatchTower.spec` uses `collect_submodules('paho')`, so the final frozen application contains the optional MQTT Python package even though application validation/import paths are dynamic. Standard-library modules and the active Python interpreter are handled by PyInstaller. External host programs (`zfs`, `docker`, and `mail`) are intentionally not bundled.

The frozen MQTT timeout worker cannot execute `mqtt_report.py` as a source file because one-file modules live inside the bundle. Frozen mode therefore re-executes the same `dist/SnapBeforeWatchTower` executable with the private `--mqtt-publish-worker` switch. Configuration and credentials still travel only via stdin JSON. Source mode keeps the existing `python mqtt_report.py --publish` behavior.

PyInstaller one-file `__file__` points into a temporary extraction tree. `runtime_base_dir()` therefore uses `sys.executable` when frozen, so root-run persistent logs are placed under `dist/logs/` rather than disappearing with the temporary extraction directory.

## Build limitation in this verification environment

The hosted sandbox used to prepare 0.0.11 could not resolve or connect to PyPI/files.pythonhosted.org. It also had no PyInstaller or Paho installation/wheel cache available. As a result, the actual ELF executable could not be generated or executed here.

This release does **not** claim that an unbuilt binary was tested. The final archive contains the complete pinned build recipe and the required `dist/` output layout documentation. Running `./build-pyinstaller.sh` on a Linux build host with package access will create `dist/SnapBeforeWatchTower` and perform its built-in smoke checks.

## Existing notification behavior regression

For an overall successful run, mail and MQTT remain independent:

| Channel state | Successful live run | Successful dry-run | Failed live run | Failed dry-run |
| --- | --- | --- | --- | --- |
| `enabled = false` | No report | No report | No report | No report |
| `enabled = true`, `on_success = false` | No success report | No success report | Failure report | Failure report |
| `enabled = true`, `on_success = true` | Success report | Success report | Failure report | Failure report |

A combined full-`main()` regression still proves one successful `dry_run=true` run with both mail and MQTT enabled and both `on_success=true` attempts both notification transports.

## Continuation behavior regression

| Failure type | Setting | Behavior | Final result |
| --- | --- | --- | --- |
| ZFS explicitly reports configured dataset nonexistent | `continue_on_missing_dataset = true` | Record failure and continue with next configured dataset | Failure |
| ZFS explicitly reports configured dataset nonexistent | `continue_on_missing_dataset = false` | Stop immediately | Failure |
| Other checked per-dataset `zfs list`/`zfs destroy` failure | `continue_on_other_failures = true` | Record failure and continue with next configured dataset | Failure |
| Other checked per-dataset `zfs list`/`zfs destroy` failure | `continue_on_other_failures = false` | Stop immediately | Failure |
| Non-missing `zfs snapshot` failure | either value | Stop immediately | Failure |
| Config/root/input/global failure | either value | Stop immediately | Failure |

Recorded continuation failures still become final failures, so enabled mail/MQTT reports failure regardless of `on_success`.

## Destructive-safety boundaries

Version 0.0.11 changes standalone packaging/frozen-runtime support only. It does not change:

- snapshot naming;
- managed snapshot matching;
- retention age/count calculations;
- `zfs destroy` target selection;
- `continue_on_missing_dataset` or `continue_on_other_failures` semantics;
- dry-run mutation suppression;
- Docker digest behavior;
- root enforcement;
- TOML setting names/defaults;
- mail success/failure policy;
- MQTT success/failure policy, payload fields, QoS, retain, TLS, authentication, or timeout;
- Home Assistant automation behavior.

## Manifest comparison against 0.0.10

All 15 paths from the supplied 0.0.10 release are retained. Four intentional files are added for PyInstaller/build output documentation, making 19 project paths in the prepared 0.0.11 source tree.

Added:

- `SnapBeforeWatchTower.spec`
- `build-pyinstaller.sh`
- `requirements-build.txt`
- `dist/README.md`

Changed:

- `.gitignore`
- `README.md`
- `SnapBeforeWatchTower.py`
- `VERIFICATION.md`
- `VERSIONING.md`
- `commented_code_map.md`
- `config.example.md`
- `mqtt_report.py`
- `tests/test_app.py`
- `tests/test_mqtt.py`

Unchanged:

- `SAFETY.md`
- `config-example.toml`
- `datasets.example.txt`
- `homeassistant/SnapBeforeWatchtower-mqtt-persistent-notification.yaml`
- `requirements-mqtt.txt`

## What was not live-tested

No real ZFS snapshot was created or destroyed. No live Docker digest capture, local mail delivery, MQTT broker/TLS/authentication exchange, Home Assistant automation execution, or Pushover delivery was performed. The actual PyInstaller executable could not be built in this sandbox for the dependency-download reason documented above.
