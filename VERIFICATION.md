# Release verification — 0.0.3

Date: 2026-09-15

## Result

| Check | Result |
| --- | --- |
| Version increment | PASS — 0.0.2 -> 0.0.3 |
| Python unit/regression suite | PASS — 25/25 tests |
| Python compile checks | PASS — application, MQTT module, and both test modules |
| CLI `--help` | PASS — all supported flags are present and described |
| CLI `--version` | PASS — `SnapBeforeWatchTower 0.0.3` |
| README CLI option coverage | PASS — every argparse option appears in README.md |
| commented_code_map symbol coverage | PASS — every Python class/function in application and tests is represented |
| Operational MQTT JSON validation | PASS — direct `username` + `password` loads in dry-run validation with no environment variable |
| Direct password worker behavior | PASS — mocked Paho publish receives the configured JSON password |
| Password-without-username validation | PASS — rejected before operations |
| Retired `password_env` key | PASS — rejected as unsupported |
| MQTT command-line credential exposure | PASS — credentials are not placed on the child process command line |
| MQTT publish failure sanitization | PASS — worker stderr/secret text is not copied into the raised/logged publish error |
| Original necessary-file manifest | PASS — all 20 non-runtime/non-cache project files from the supplied project are present |
| 0.0.2 clean baseline manifest | PASS — same 20 project paths; no required path removed or added |
| Clean-package exclusions | PASS — `.git`, runtime logs, `__pycache__`, `.pyc`, `.pyo`, test/build caches, and temporary files excluded |

## Credential-model verification

Version 0.0.3 implements the requested simple MQTT credential format directly in JSON:

```json
{
  "username": "mqtt-user",
  "password": "<String>"
}
```

`mqtt_report.load_config()` validates `password` as an optional nonempty string and requires `username` when it is set. `mqtt_report.worker()` passes the configured password directly to Paho. No environment-variable lookup or `sudo --preserve-env` handling remains in the application.

The supplied operational `mqtt.json` was migrated from the original project's credential value to the new `password` key without printing the credential in test output or release notes. The file is packaged with owner-only mode (`0600`) where ZIP permission metadata is honored. Because it contains a plaintext credential by explicit design, it remains ignored by `.gitignore` and should not be shared publicly.

## Manifest comparison

The final clean project keeps the same 20 relevant paths as the 0.0.2 clean baseline and the same 20 non-runtime/non-cache paths from the supplied project. Runtime `.git`, historical logs, and the supplied Python bytecode cache are intentionally excluded under the project's clean-package rules.

Files changed for 0.0.3:

- `README.md`
- `SnapBeforeWatchTower.py`
- `VERIFICATION.md`
- `VERSIONING.md`
- `commented_code_map.md`
- `config.example.md`
- `mqtt.example.json`
- `mqtt.json`
- `mqtt_report.py`
- `tests/test_app.py`
- `tests/test_mqtt.py`

Files retained byte-for-byte from the 0.0.2 clean baseline:

- `.gitignore`
- `.snaplist`
- `SAFETY.md`
- `datasets`
- `datasets.example.txt`
- `full-snaplist`
- `homeassistant/SnapBeforeWatchtower-mqtt-persistent-notification.yaml`
- `requirements-mqtt.txt`
- `snaplist`

The remaining unchanged baseline path count before refreshing this verification file was 10; `VERIFICATION.md` is intentionally rewritten for the 0.0.3 release and therefore becomes a changed file in the final package.

## What was not live-tested

No real ZFS datasets were created or destroyed. Docker digest capture and `mail` delivery were not run against live services. No real MQTT broker connection was attempted in this environment, and Paho availability on the target host was not assumed. Those external paths are covered by mocked regression tests, while actual broker credentials, network reachability, permissions, and target-host services still require the user's real host.
