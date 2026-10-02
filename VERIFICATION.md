# Release verification — 0.0.10

Date: 2026-10-02

## Result

| Check | Result |
| --- | --- |
| Version increment | PASS — 0.0.9 -> 0.0.10 |
| Python unit/regression suite | PASS — 46/46 tests |
| Python compile checks | PASS — `SnapBeforeWatchTower.py`, `mqtt_report.py`, `tests/test_app.py`, and `tests/test_mqtt.py` compile successfully in memory |
| Public CLI help | PASS — both `-h` and `--help` exit 0 and document `-c CONFIG`, `-h`/`--help`, `--version`, and TOML-only operational settings |
| Public CLI version | PASS — `--version` exits 0 without configuration and prints `SnapBeforeWatchTower.py 0.0.10` |
| Operational CLI boundary | PASS — normal operation still requires `-c CONFIG`; retired operational flags remain rejected |
| TOML example parse | PASS — `config-example.toml` parses as TOML with 24 settings across `[application]`, `[mail]`, and `[mqtt]` |
| Requested continuation settings | PASS — both continuation controls remain present as `true` in the loadable example and existing continuation tests still pass |
| Dry-run combined success reporting | PASS — one full `main()` dry-run with mail/MQTT enabled and both `on_success=true` attempts one DRY-RUN success mail and one MQTT `status=success`, `dry_run=true` publish in the same execution |
| Mail success gating | PASS — successful dry-runs still send mail only with `[mail].on_success=true`; failure mail remains independent of that setting |
| Mail delivery result | PASS — the local `mail` helper returns true only on exit code 0 and returns false/logs the exit code and stderr on transport failure |
| MQTT success gating | PASS — successful live and dry-run executions publish only with `[mqtt].on_success=true`; failures publish whenever MQTT is enabled |
| MQTT attempt diagnostics | PASS — reporter logs an explicit publish attempt before the worker and a published confirmation after success |
| MQTT worker failure diagnostics | PASS — worker failures expose only a sanitized exception class such as `ConnectionRefusedError`; unsafe/free-form stderr is replaced with `UnknownError` |
| MQTT credential safety | PASS — worker exception text, broker password, and request JSON are not copied into parent failure messages |
| Paho requirement wording | PASS — `requirements-mqtt.txt` now says the dependency is required whenever MQTT is enabled, including dry-run reporting |
| Continuation behavior regression | PASS — missing-dataset and checked per-dataset list/destroy continuation/stop behavior remains covered and unchanged |
| Dry-run mutation safety | PASS — snapshot creation/destruction, log deletion, and Docker digest capture remain suppressed; snapshot listing remains real |
| TOML documentation coverage | PASS — all 24 assignments in `config-example.toml` are represented in both README.md and `config.example.md` |
| README current-behavior check | PASS — README contains no release history/version number and documents only the current interface/behavior |
| commented_code_map symbol coverage | PASS — every current Python class/function/method name in the application and tests is represented |
| Home Assistant YAML parse | PASS — supplied automation parses as YAML and still consumes `status`, `error`, `stderr`, and `dry_run` |
| Requested disclaimer | PASS — the disclaimer/liability block is identical in README.md and `SAFETY.md` and contains the requested wording |
| `.gitignore` example handling | PASS — private `config.toml` and `datasets` remain ignored; shipped examples remain trackable |
| Original-project manifest preservation | PASS — all 15 project file paths from 0.0.9 are retained; no project path was removed or added |
| Cache/build/temp exclusions | PASS — project tree contains no `__pycache__`, `.pyc`, `.pyo`, pytest/build/dist/egg-info caches, backups, or temporary files |
| ZIP integrity and fresh extraction | PASS — final ZIP passes `unzip -t`; fresh extraction has the same 15-file manifest and is byte-for-byte identical to the prepared 0.0.10 tree |
| Final ZIP manifest vs 0.0.9 | PASS — final release and supplied 0.0.9 baseline contain the same 15 project file paths |

## Dry-run success reporting verified

For an overall successful run, mail and MQTT remain independent:

| Channel state | Successful live run | Successful dry-run | Failed live run | Failed dry-run |
| --- | --- | --- | --- | --- |
| `enabled = false` | No report | No report | No report | No report |
| `enabled = true`, `on_success = false` | No success report | No success report | Failure report | Failure report |
| `enabled = true`, `on_success = true` | Success report | Success report | Failure report | Failure report |

The added full-`main()` regression specifically uses:

```toml
[application]
dry_run = true

[mail]
enabled = true
on_success = true

[mqtt]
enabled = true
on_success = true
```

with the remaining required values supplied by the test fixture. It proves that the same successful execution reaches both notification transports: mail receives subject `SnapBeforeWatchTower DRY-RUN SUCCESS - logs attached`, and MQTT receives a payload whose `status` is `success` and whose `dry_run` field is `true`.

This closes the 0.0.9 coverage gap where mail and MQTT dry-run success behavior had been tested separately rather than together through `main()`.

## Delivery diagnostics verified

Every real run now logs the loaded notification policy without including addresses, broker credentials, or passwords. For a successful dry-run with both success switches enabled, the expected sequence includes:

```text
Notification policy: dry_run=True; mail_enabled=True; mail_on_success=True; mqtt_enabled=True; mqtt_on_success=True
Success mail report enabled; attempting DRY-RUN success mail delivery.
...
MQTT final success report enabled; attempting publish [DRY-RUN]
```

A mail command exit code of zero logs `Mail was sent successfully`. A nonzero exit code is returned to the run coordinator as `False`, with the exit code and local mail stderr recorded in the error log. This remains a notification transport failure and does not replace the underlying ZFS/dry-run result.

The MQTT child process still keeps configuration and credentials off its command line. If Paho raises an exception, the child writes only the exception class name to stderr. The parent accepts only a short alphanumeric/underscore class name; anything else becomes `UnknownError`. This gives useful diagnostics without logging MQTT passwords or request JSON.

## Continuation behavior regression

The 0.0.9 continuation controls remain unchanged:

| Failure type | Setting | Behavior | Final result |
| --- | --- | --- | --- |
| ZFS explicitly reports configured dataset nonexistent | `continue_on_missing_dataset = true` | Record failure and continue with next configured dataset | Failure |
| ZFS explicitly reports configured dataset nonexistent | `continue_on_missing_dataset = false` | Stop immediately | Failure |
| Other checked per-dataset `zfs list`/`zfs destroy` failure | `continue_on_other_failures = true` | Record failure and continue with next configured dataset | Failure |
| Other checked per-dataset `zfs list`/`zfs destroy` failure | `continue_on_other_failures = false` | Stop immediately | Failure |
| Non-missing `zfs snapshot` failure | either value | Stop immediately | Failure |
| Config/root/input/global failure | either value | Stop immediately | Failure |

Recorded continuation failures still become final failures, so enabled mail/MQTT uses failure reporting regardless of `on_success`.

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

Operational settings remain TOML-only.

## Destructive-safety boundaries

Version 0.0.10 changes notification diagnostics and transport-result visibility only. It does not change:

- snapshot naming;
- which snapshots match managed retention;
- age-cutoff or `retain_count` calculations;
- which snapshots are selected for `zfs destroy`;
- `continue_on_missing_dataset` or `continue_on_other_failures` semantics;
- dry-run mutation suppression;
- Docker digest collection policy;
- root enforcement;
- TOML setting names/defaults;
- MQTT payload fields, QoS, retain, TLS, authentication, or timeout values;
- Home Assistant automation behavior.

## Manifest comparison

The supplied 0.0.9 archive and the 0.0.10 project both contain the same 15 project files:

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

Changed from 0.0.9:

- `README.md`
- `SnapBeforeWatchTower.py`
- `VERIFICATION.md`
- `VERSIONING.md`
- `commented_code_map.md`
- `config.example.md`
- `mqtt_report.py`
- `requirements-mqtt.txt`
- `tests/test_app.py`
- `tests/test_mqtt.py`

Unchanged from 0.0.9:

- `.gitignore`
- `SAFETY.md`
- `config-example.toml`
- `datasets.example.txt`
- `homeassistant/SnapBeforeWatchtower-mqtt-persistent-notification.yaml`

## What was not live-tested

No real ZFS snapshot was created or destroyed. No live Docker daemon digest capture, local `mail` delivery, MQTT broker connection, TLS/authentication exchange, Home Assistant automation execution, or Pushover delivery was performed.

The regression suite verifies that successful dry-run reporting reaches both notification paths together and that transport outcomes are observable, but an offline test cannot prove the target host's MTA, DNS/network path, broker credentials/ACLs, TLS certificates, or Home Assistant/Pushover configuration. If delivery still fails on the target host, the 0.0.10 log now distinguishes configuration suppression from an actual mail/MQTT transport failure and gives a safe MQTT failure class when available.
