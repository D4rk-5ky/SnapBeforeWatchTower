# Release verification — 0.0.4

Date: 2026-09-15

## Result

| Check | Result |
| --- | --- |
| Version increment | PASS — 0.0.3 -> 0.0.4 |
| Python unit/regression suite | PASS — 27/27 tests |
| Python compile checks | PASS — application, MQTT module, and both test modules |
| Public CLI surface | PASS — `SnapBeforeWatchTower.py` registers exactly one public argument: `-c CONFIG` |
| Old public flags | PASS — old command/file/retention/mail/MQTT/dry-run/version/help flags are rejected |
| TOML example parse | PASS — `config-example.toml` loads through the real application loader |
| TOML setting comments | PASS — all 21 example setting assignments have adjacent explanatory comments |
| README configuration coverage | PASS — every current TOML setting and the single `-c CONFIG` invocation are documented |
| commented_code_map symbol coverage | PASS — every Python class/function in application and tests is represented |
| Direct MQTT password model | PASS — TOML `password` is passed directly to mocked Paho auth; no password environment-variable mechanism remains |
| Optional mail model | PASS — disabled by default; enabled mail maps to existing failure/success behavior |
| Optional MQTT model | PASS — disabled by default; enabled configuration is validated and dry-run suppresses publish |
| TOML-relative dataset path | PASS — relative `dataset_file` resolves from the TOML directory |
| TOML-relative TLS paths | PASS — CA/client cert/key paths resolve from the TOML directory |
| Retention/dry-run/root/order regression tests | PASS — existing destructive-operation boundaries remain covered |
| Clean-package exclusions | PASS — `.git`, runtime logs, Python caches/bytecode, pytest/build caches, and temporary files excluded |

## Configuration migration verification

Version 0.0.4 uses one TOML file for all runtime configuration. The public invocation is:

```bash
sudo python3 SnapBeforeWatchTower.py -c config.toml
```

The former runtime flags are represented in `[application]`, mail is optional under `[mail]`, and the complete former MQTT JSON setting set is represented under `[mqtt]`, including the requested direct plaintext string:

```toml
password = "<String>"
```

No `password_env`/environment-variable credential lookup remains.

The example defaults to `dry_run = true`, mail disabled, and MQTT disabled. This makes a copied example safer to inspect before enabling real destructive operations or notifications.

## Manifest comparison against 0.0.3

The 0.0.3 clean release contained 20 project files. The 0.0.4 clean release contains 18 project files.

Three obsolete configuration paths were intentionally removed because the application no longer reads them:

- `config.example.md`
- `mqtt.example.json`
- `mqtt.json`

One replacement configuration path was added:

- `config-example.toml`

Every other original clean-release path is retained. The original ZFS dataset/example files, safety notice, Home Assistant automation, MQTT dependency file, application/test files, and project documentation remain present. Runtime/cache material is excluded by policy.

## Behavior intentionally preserved

The TOML migration does not change the managed snapshot naming pattern, retention selection logic, non-recursive ZFS listing behavior, create/delete operation order, Docker digest failure semantics, local mail command behavior, root enforcement, dry-run mutation suppression, MQTT payload schema, MQTT non-retained publish behavior, or MQTT failure isolation/sanitization.

## What was not live-tested

No real ZFS snapshots were created or destroyed. Docker digest capture and local `mail` delivery were not exercised against live services. No real MQTT broker connection was attempted. Those paths are covered by mocked regression tests, while target-host ZFS permissions, Docker daemon availability, mail configuration, broker reachability, credentials, TLS trust, and Home Assistant behavior still require validation on the real host.
