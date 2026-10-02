# Release verification — 0.0.8

Date: 2026-10-02

## Result

| Check | Result |
| --- | --- |
| Version increment | PASS — 0.0.7 -> 0.0.8 |
| Python unit/regression suite | PASS — 37/37 tests |
| Python compile checks | PASS — `SnapBeforeWatchTower.py`, `mqtt_report.py`, `tests/test_app.py`, and `tests/test_mqtt.py` compile successfully |
| Public CLI help | PASS — both `-h` and `--help` exit 0 and document `-c CONFIG`, `-h`/`--help`, `--version`, and that operational settings remain TOML-only |
| Public CLI version | PASS — `--version` exits 0 without configuration and prints `SnapBeforeWatchTower.py 0.0.8` |
| Operational CLI boundary | PASS — missing `-c`, retired `--config`, and retired CLI `--dry-run` remain rejected with exit code 2 |
| TOML example parse | PASS — `config-example.toml` loads through the real application loader with `command=create`, `dry_run=true`, mail disabled, and MQTT disabled |
| TOML documentation coverage | PASS — all 22 assignments in `config-example.toml` are represented in both README.md and `config.example.md` |
| Notification-policy regression coverage | PASS — mail and MQTT success reports are gated independently by `on_success`; enabled failure reporting remains active with `on_success=false`; both rules are tested in dry-run, and MQTT is tested in real runs too |
| MQTT dry-run report metadata | PASS — published MQTT payloads include `dry_run=true|false`; dry-run is no longer globally suppressed |
| MQTT dependency boundary | PASS — enabled MQTT requires `paho-mqtt` in both real and dry-run configuration validation because dry-run failures can publish |
| Home Assistant YAML parse | PASS — supplied automation parses as YAML and reads `dry_run` for `DRY-RUN`/`LIVE` notification mode text |
| README current-behavior check | PASS — README contains no release-version history/version number and documents only the current interface/behavior |
| commented_code_map symbol coverage | PASS — every current Python class/function/method name in the application and tests is represented |
| Requested disclaimer | PASS — the supplied disclaimer/liability text is present verbatim in both README.md and `SAFETY.md` |
| `.gitignore` example handling | PASS — private `config.toml` and `datasets` remain ignored; `config-example.toml`, `config.example.md`, and `datasets.example.txt` are trackable |
| Original-project manifest preservation | PASS — all 15 file paths from the supplied 0.0.7 archive are retained; no project path was removed or added |
| Cache/build/temp exclusions | PASS — final package contains no `__pycache__`, `.pyc`, `.pyo`, `.pytest_cache`, build/dist, backup, or temporary artifacts |
| ZIP integrity and fresh extraction | PASS — `unzip -t` reports no errors and a fresh extraction is byte-for-byte equal to the prepared 0.0.8 project tree |
| Final ZIP manifest vs supplied archive | PASS — both contain the same 15 project file paths; no forbidden cache/build/temp entries are present |

## Notification behavior verified

Mail and MQTT now follow the same selection policy while remaining independently configurable:

| Channel configuration | Successful live run | Successful dry-run | Failed live run | Failed dry-run |
| --- | --- | --- | --- | --- |
| `enabled=false` | no report | no report | no report | no report |
| `enabled=true`, `on_success=false` | no success report | no success report | failure report | failure report |
| `enabled=true`, `on_success=true` | success report | success report | failure report | failure report |

`[mail].on_success` affects only mail. `[mqtt].on_success` affects only MQTT. Mail dry-run subjects/introduction text identify the run as dry-run. MQTT payloads always include a `dry_run` boolean when a report is published.

The supplied Home Assistant automation keeps the existing `status=success` / `status=failure` branching and adds visible `Mode: DRY-RUN` or `Mode: LIVE` text from the payload.

## CLI behavior verified

Normal operation remains:

```text
sudo python3 SnapBeforeWatchTower.py -c config.toml
```

Informational interfaces remain:

```text
python3 SnapBeforeWatchTower.py --help
python3 SnapBeforeWatchTower.py --version
```

`--help` and `--version` are handled by `argparse` before `load_app_config()` is called, so they do not require a TOML file and do not enter logging, root enforcement, ZFS, Docker, mail, or MQTT operation paths.

Operational settings were intentionally **not** restored as command-line flags. Create/delete mode, dataset file, retention, dry-run, mail, and MQTT remain configured in TOML.

## Destructive safety behavior intentionally unchanged

Version 0.0.8 changes notification/report selection only. It does not change snapshot naming, retention selection, count-floor behavior, age cutoff behavior, managed snapshot filtering, `zfs destroy` selection, Docker digest capture semantics, root enforcement, missing-dataset continuation/final-failure behavior, mail transport command construction, MQTT QoS/retain/TLS/auth/timeout behavior, broker credential transport, or dry-run mutation suppression.

Dry-run still suppresses snapshot creation, snapshot destruction, old-log deletion, and Docker digest collection while retaining real ZFS snapshot listing for an accurate retention preview. The notification transports are intentionally **not** suppressed in dry-run anymore; they follow the same success/failure policy shown above.

The application can still perform destructive ZFS snapshot deletion and managed log-file deletion during real runs. The requested disclaimer remains included in README.md and `SAFETY.md`; the example configuration still defaults to `dry_run = true` with mail and MQTT disabled.

## `.gitignore` behavior verified

Version 0.0.8 preserves the corrected rules from 0.0.7:

```text
config*
!config-example.toml
!config.example.md

!datasets.example.txt
```

A disposable Git repository check confirmed:

- `config.toml` — ignored
- `config-example.toml` — trackable
- `config.example.md` — trackable
- `datasets.example.txt` — trackable
- `datasets` — ignored

## Manifest comparison

The supplied 0.0.7 archive and the 0.0.8 project both contain these 15 project paths:

- `.gitignore`
- `README.md`
- `SAFETY.md`
- `SnapBeforeWatchTower.py`
- `VERIFICATION.md`
- `VERSIONING.md`
- `commented_code_map.md`
- `config-example.toml`
- `config.example.md`
- `datasets.example.txt`
- `homeassistant/SnapBeforeWatchtower-mqtt-persistent-notification.yaml`
- `mqtt_report.py`
- `requirements-mqtt.txt`
- `tests/test_app.py`
- `tests/test_mqtt.py`

Changed from the supplied 0.0.7 baseline:

- `README.md`
- `SnapBeforeWatchTower.py`
- `VERIFICATION.md`
- `VERSIONING.md`
- `commented_code_map.md`
- `config-example.toml`
- `config.example.md`
- `homeassistant/SnapBeforeWatchtower-mqtt-persistent-notification.yaml`
- `mqtt_report.py`
- `tests/test_app.py`
- `tests/test_mqtt.py`

Unchanged from the supplied 0.0.7 baseline:

- `.gitignore`
- `SAFETY.md`
- `datasets.example.txt`
- `requirements-mqtt.txt`

## What was not live-tested

No real ZFS snapshot was created or destroyed. No live Docker daemon digest capture, local `mail` delivery, MQTT broker connection, TLS/authentication exchange, Home Assistant automation execution, or Pushover delivery was performed.

The regression suite mocks external operations and verifies the application safety boundaries, notification selection, payload construction, and command ordering offline. Real-host ZFS permissions/error wording, local mail configuration, broker connectivity/credentials/TLS, and Home Assistant/Pushover execution should still be validated on the target system before production use.
