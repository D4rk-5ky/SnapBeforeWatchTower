# Versioning and complete change log

`SnapBeforeWatchTower.py::__version__` is the application version embedded in release metadata and MQTT reports. The current release is 0.0.11. Normal operation remains TOML-driven with `-c CONFIG`; the public CLI also exposes informational `-h`/`--help` and `--version` flags.

Each new created release advances by one patch step. The patch component ranges from 0 through 99: `0.0.98 -> 0.0.99 -> 0.1.0 -> 0.1.1`. Never emit `0.0.100`. Do not invent releases for intermediate edits while preparing a single release. Update this file with every release and record every code change, documentation change, and added file. Keep README.md focused on current usage and keep configuration examples and commented_code_map.md synchronized.

## 0.0.11 — 2026-10-02

### PyInstaller standalone build

- Bump the application version from 0.0.10 to 0.0.11 so source and frozen `--version`/MQTT metadata identify this build-support release.
- Add `SnapBeforeWatchTower.spec` as a one-file PyInstaller recipe and explicitly collect every `paho` submodule so the optional MQTT implementation is present in frozen builds even though Paho is imported dynamically.
- Add `requirements-build.txt` with pinned `pyinstaller==6.22.3` and `paho-mqtt==2.1.0` build dependencies. The source-only MQTT requirement remains separately documented in `requirements-mqtt.txt`.
- Add `build-pyinstaller.sh`. It creates/uses `.venv-build`, installs the build requirements, removes stale `build/` and `dist/` output, builds `dist/SnapBeforeWatchTower`, then smoke-tests the frozen executable with `--help` and `--version`.
- Add `dist/README.md` to document the required final output path. Update `.gitignore` so generated `dist/*` artifacts remain ignored while that documentation file stays trackable.
- Add `runtime_base_dir()` so a PyInstaller one-file executable stores persistent root-run logs beside the executable instead of inside PyInstaller's temporary extraction directory. Source execution keeps the existing script-directory log location; non-root execution keeps the `/tmp/SnapBeforeWatchTower` fallback.
- Make frozen MQTT publishing re-execute the same standalone binary with a private `--mqtt-publish-worker` switch. The private worker is accepted only when `sys.frozen` is set; normal source/public CLI behavior remains unchanged. MQTT configuration, payload, and credentials remain on stdin rather than argv.
- Keep the source-mode MQTT worker unchanged: source runs continue to launch `mqtt_report.py --publish` with the same bounded timeout and secret-safe exception-class diagnostics.
- Preserve all ZFS snapshot/retention, dry-run, continuation, mail/MQTT success/failure selection, root-enforcement, and configuration behavior.

### Tests, documentation, and packaging

- Add regression coverage for frozen runtime-directory selection, the frozen private MQTT-worker entry point, and frozen MQTT child-process argv/stdin behavior.
- Update the existing test fixtures/version assertions to 0.0.11; the offline regression suite is now 49 tests.
- Update README.md and `config.example.md` with source-vs-standalone dependency guidance, build instructions, the `dist/SnapBeforeWatchTower` path, frozen log location, and frozen MQTT worker behavior. README remains current-usage documentation only.
- Update `commented_code_map.md` for every new function/test/build file and explain why the frozen worker/log-directory changes are required.
- Keep build caches, `.venv-build`, bytecode, and generated PyInstaller `build/` output out of the final source/release archive.
- The hosted build sandbox used for this release could not resolve/reach PyPI and did not have PyInstaller/Paho preinstalled, so the actual Linux binary could not be generated here. The release contains the complete pinned build recipe and required `dist/` target layout; this limitation is recorded in `VERIFICATION.md` rather than claiming an unperformed binary test.

## 0.0.10 — 2026-10-02

### Application code and notification delivery diagnostics

- Bump the application version from 0.0.9 to 0.0.10 so `--version` and MQTT release metadata identify this notification-diagnostics release.
- Preserve the 0.0.9 notification selection rules: a successful live or dry-run execution sends mail/MQTT only when that channel is enabled and its own `on_success=true`; failures still report whenever the channel is enabled regardless of `on_success`.
- Add a startup notification-policy log line showing `dry_run`, whether mail/MQTT are enabled, and the two `on_success` values without logging recipients, broker credentials, or MQTT passwords. This makes it immediately visible whether success reporting was actually enabled in the loaded TOML.
- Make `MailTo()` and `WasMailSent()` return a boolean transport result. A successful local `mail` exit returns `True`; a nonzero exit returns `False`, records the exit code/stderr, and lets the caller state explicitly that the success-mail attempt failed. Notification transport failure still does not replace the underlying ZFS/dry-run result.
- Add explicit success-mail attempt logging before invoking the local mail command and explicit suppression logging when mail is enabled but `[mail].on_success=false`.
- Add explicit MQTT publish-attempt logging before the bounded worker is launched and preserve the existing published confirmation message on success.
- Add `MQTTPublishError`, a parent-side error that carries only a sanitized MQTT worker exception-class reason. The child process now writes only `type(exc).__name__` on failure, never exception text, credentials, or request JSON. The parent can therefore distinguish failures such as `ConnectionRefusedError` while keeping secrets out of logs.
- Keep MQTT report failures and timeouts non-masking: they are logged, but they do not alter the original snapshot/dry-run exit outcome.
- Correct the stale `requirements-mqtt.txt` comment: Paho is required whenever `[mqtt].enabled=true`, including dry-run reporting.
- No ZFS snapshot creation/destruction, retention selection, continuation policy, Docker behavior, root enforcement, TOML setting, MQTT payload contract, QoS/retain/TLS/auth behavior, or Home Assistant automation behavior was changed.

### Tests, documentation, and packaging

- Add a full `main()` regression proving that one successful `dry_run=true` execution with both mail and MQTT enabled and both `on_success=true` attempts both success reports in the same run. This closes the coverage gap where 0.0.9 tested those channels only in separate unit paths.
- Add regression coverage for mail helper delivery-result propagation, sanitized MQTT worker failure reasons, and credential-safe MQTT failure logging.
- Update README.md with current notification delivery diagnostics and troubleshooting behavior; keep it free of release history.
- Update `config.example.md`, `commented_code_map.md`, `requirements-mqtt.txt`, and `VERIFICATION.md` so documentation matches the actual dry-run notification behavior and diagnostics.
- Package the complete project with the same 15 project paths as 0.0.9 and exclude caches, bytecode, backups, build artifacts, and temporary files.

## 0.0.9 — 2026-10-02

### Application code and failure-continuation behavior

- Bump the application version from 0.0.8 to 0.0.9 so `--version` and MQTT release metadata identify this behavior release.
- Add `[application].continue_on_missing_dataset` as a boolean continuation policy. `true` records an explicitly nonexistent configured ZFS dataset and continues with the next configured dataset; `false` stops immediately. Both paths remain overall failures and therefore use enabled mail/MQTT failure reporting.
- Add `[application].continue_on_other_failures` as a separate boolean policy for any other checked per-dataset `zfs list` or `zfs destroy` `CommandError`. `true` records the failure and continues with the next configured dataset; `false` stops immediately.
- Default both new settings to `true` when omitted so existing 0.0.8-style TOML files retain the previous missing-dataset continuation behavior and adopt the requested per-dataset list/destroy continuation behavior without becoming invalid.
- Add `DatasetCommandFailuresError` to preserve an overall failure result after one or more `continue_on_other_failures=true` continuations. It records affected datasets and can include missing datasets already seen in the same run.
- Add `is_checked_zfs_list_or_destroy_error()`, `remember_dataset_command_failure()`, and shared `handle_dataset_command_failure()` so create/delete loops use one classification/policy implementation rather than duplicating continuation logic.
- Keep missing-dataset detection deliberately narrow: only ZFS stderr containing `dataset does not exist` or `no such pool or dataset` enters the missing-dataset policy.
- Keep `continue_on_other_failures` deliberately narrow: it applies only to checked `zfs list`/`zfs destroy` failures raised through `run_cmd()`. Non-missing `zfs snapshot` failures remain immediately fatal, as do configuration, root, dataset-file/input, and other global failures.
- Preserve end-of-run failure semantics for all recorded continuations. Remaining configured datasets and normal log cleanup run when continuation is enabled, then the process still raises a failure so MQTT reports `status=failure` and enabled mail sends failure mail.
- Add dedicated failure-mail wording/subject for continued list/destroy failures and correct missing-dataset mail wording so `continue_on_missing_dataset=false` says the run stopped immediately instead of claiming later datasets were processed.
- Keep dry-run notification behavior unchanged from 0.0.8: failures report when mail/MQTT is enabled regardless of `on_success`, while success reports still require the channel's `on_success=true`.
- No snapshot naming, managed-snapshot selection, retain-count/age calculation, actual `zfs destroy` target selection, Docker digest policy, MQTT QoS/retain/TLS/auth/timeout behavior, mail command construction, or root enforcement was changed.

### Configuration, documentation, tests, and packaging

- Add both continuation settings to `config-example.toml` with the requested explanatory comments and explicit `true` values.
- Update `README.md` and `config.example.md` for current 0.0.9 behavior, including defaults, exact continuation boundaries, final failure/report behavior, and the distinction between missing-dataset, list/destroy, snapshot-create, and global failures.
- Update `commented_code_map.md` for every new class/function/policy path and the expanded regression suite.
- Update MQTT test fixture version strings from 0.0.8 to 0.0.9.
- Extend tests for both boolean settings, backward-compatible omitted-key defaults, invalid types, missing-dataset continue/stop behavior, `zfs list`/`zfs destroy` continue/stop behavior, failure mail, and proof that unrelated snapshot-create failures remain immediately fatal.
- Refresh `VERIFICATION.md` and package the complete project as a clean ZIP with no Python bytecode/cache/build/temp artifacts.

## 0.0.8 — 2026-10-02

### Application code and notification behavior

- Bump the application version from 0.0.7 to 0.0.8 so `--version` and MQTT release metadata identify this behavior release.
- Add `[mqtt].on_success` with default `false`, mirroring `[mail].on_success`. When MQTT is enabled, `on_success=true` publishes successful run reports; `on_success=false` suppresses only successful reports.
- Keep failure reporting independent from success reporting: when mail or MQTT is enabled, failures are reported regardless of that channel's `on_success` value. Mail and MQTT keep separate switches, so either channel can be success-enabled independently.
- Apply the same notification policy during `dry_run=true`. Successful dry-runs are reported only when the corresponding channel's `on_success=true`; failed dry-runs still report when the channel is enabled. MQTT is no longer globally suppressed during dry-run.
- Add `dry_run` boolean to every published MQTT payload so Home Assistant/other consumers can distinguish preview and live reports without changing the existing `success`/`failure` status contract.
- Mark dry-run mail subjects and success/failure introductory text explicitly as `DRY-RUN`.
- Require the Paho MQTT dependency whenever MQTT is enabled, including dry-run, because a failed dry-run must still be able to publish a failure report.
- Preserve ZFS snapshot naming, snapshot/list/destroy safety, retention selection, count/age rules, Docker dry-run suppression, root enforcement, missing-dataset continuation/final-failure behavior, mail transport, MQTT QoS/retain/TLS/auth/timeout behavior, and report-failure non-masking behavior.

### Configuration, documentation, tests, integration, and packaging

- Add `[mqtt].on_success = false` to `config-example.toml` and `config.example.md`, and document the identical real/dry-run success/failure policy for mail and MQTT.
- Update README.md with the current notification rules, a compact result matrix, the new MQTT payload `dry_run` field, Paho requirements for dry-run MQTT, and explicit dry-run mail behavior.
- Update `commented_code_map.md` for the MQTT success gate, dry-run reporting, payload field, dependency behavior, and new regression tests.
- Update the supplied Home Assistant automation to read `dry_run` from the MQTT payload and show `Mode: DRY-RUN` or `Mode: LIVE` in success/failure Pushover messages.
- Extend tests for mail success/failure behavior in dry-run, MQTT success gating in real and dry-run runs, MQTT failure reporting despite `on_success=false`, dry-run payload metadata, and Paho dependency validation for both real and dry-run MQTT.
- Refresh `VERIFICATION.md` and package the complete project as a clean ZIP with no cache, bytecode, build, or temporary artifacts.

## 0.0.7 — 2026-10-02

### Application code and behavior

- Bump the application version from 0.0.6 to 0.0.7 so `--version` and MQTT release metadata identify this maintenance release.
- Restore standard `-h`/`--help` through `argparse` and add public `--version`. Both informational flags exit before TOML loading, root checks, logging setup, ZFS/Docker/mail work, or MQTT reporting.
- Keep `-c CONFIG` as the only operational CLI input. Create/delete mode, dataset file, retention, dry-run, mail, and MQTT settings remain TOML-only; retired operational flags are not restored.
- Add CLI help epilog text that explicitly tells users operational settings belong in TOML.
- Preserve snapshot naming, retention selection, managed-name filtering, missing-dataset continuation/final-failure behavior, Docker digest semantics, root enforcement, mail behavior, MQTT payload/publish behavior, and dry-run safety boundaries unchanged.

### Documentation, tests, safety, and packaging

- Update README.md for current behavior only with the complete public CLI (`-c`, `-h`/`--help`, `--version`), examples, and the requested disclaimer/liability text.
- Replace the older `SAFETY.md` disclaimer wording with the requested disclaimer/liability text while retaining a SnapBeforeWatchTower-specific warning about destructive snapshot/log deletion and the no-license notice.
- Update `config-example.toml` comments and `config.example.md` so the loadable example/reference mention help/version and continue to document every TOML setting.
- Update `commented_code_map.md` for the public help/version behavior, new CLI regression tests, disclaimer file role, and `.gitignore` behavior.
- Update CLI regression coverage: help must describe every public flag; version must report 0.0.7 without configuration; missing config and retired operational flags must still fail cleanly.
- Update MQTT regression fixture version strings from 0.0.6 to 0.0.7.
- Correct `.gitignore` so the broad private `config*` rule explicitly unignores the shipped `config-example.toml` and `config.example.md` files, and fix the malformed `datasets.example.txt` negation rule, matching the documented intent and keeping all shipped examples trackable.
- Refresh `VERIFICATION.md` after compile, regression, CLI, config-example, documentation, manifest, and clean-package checks.
- Preserve every project path from the supplied 0.0.6 archive and add no new project path.

## 0.0.6 — 2026-09-25

### Application code and behavior

- Bump the application version from 0.0.5 to 0.0.6 so MQTT release metadata identifies this behavior release.
- Add `MissingDatasetsError` as an aggregate final failure used only after the script has processed all remaining configured datasets and normal log cleanup following one or more missing-dataset errors.
- Add `is_missing_dataset_error()` to classify captured ZFS stderr conservatively. It recognizes `dataset does not exist` and `no such pool or dataset`; unrelated ZFS errors are not continuable.
- Add `remember_missing_dataset()` to record each missing dataset once and log that processing will continue with later datasets.
- In `create` mode, catch missing-dataset failures from both `zfs snapshot` (`subprocess.CalledProcessError`) and retention `zfs list` (`CommandError`) around each dataset. Skip only that dataset, continue later datasets, then run normal log cleanup.
- In `delete` mode, catch the same missing-dataset condition from the per-dataset snapshot listing, continue later datasets, then run normal log cleanup.
- After remaining work finishes, raise `MissingDatasetsError` so the process still has a failure outcome. Failure mail is sent when mail is enabled, with a dedicated `SnapBeforeWatchTower FAILED - missing dataset` subject and introductory text naming the reason. `on_success=true` does not cause an additional success mail for this run.
- Preserve the MQTT schema and Home Assistant contract: no new status/event is introduced. Missing-dataset runs publish `status: "failure"`, `exit_code: 1`, and keep `warning: false`; the existing `error` field now names the missing dataset(s) and says `dataset does not exist`, while `stderr` retains bounded current-run error detail.
- Preserve the immediate-abort safety behavior for every non-missing ZFS error such as permission failures. No retention selection, snapshot naming, destroy safety, Docker behavior, root enforcement, TOML schema, MQTT publish/QoS/retain/TLS behavior, or dry-run mutation boundary is changed.

### Documentation, tests, integration, and packaging

- Update README.md for current behavior only: missing-dataset continuation, final failure/mail behavior, unchanged MQTT success/failure contract, and the distinction between continuable missing datasets and immediately fatal unrelated ZFS errors.
- Update `config-example.toml` and `config.example.md` to describe the missing-dataset behavior without adding any new configuration setting. All existing settings and the single public `-c CONFIG` option remain unchanged.
- Update `commented_code_map.md` for the new exception/helpers, run coordination, and regression tests.
- Add regression coverage for exact missing-dataset stderr classification, create-mode continuation plus failure mail, delete-mode continuation, unrelated-error immediate abort, and the unchanged MQTT failure schema/reason.
- Update MQTT regression fixture version strings to 0.0.6.
- Keep the supplied Home Assistant automation control flow unchanged because it already branches on `status == "success"` and `status == "failure"` and displays the existing `error`/`stderr` fields.
- Keep `SAFETY.md` and its disclaimer/liability/data-loss notices unchanged.
- Refresh `VERIFICATION.md` and package a clean release ZIP with all original project paths and no Python/cache/build/temp artifacts.

## 0.0.5 — 2026-09-25

### Application code and behavior

- Bump the application version from 0.0.4 to 0.0.5 so MQTT release metadata identifies this maintenance release.
- Update MQTT regression-test sample version strings from 0.0.4 to 0.0.5 so test fixtures match the current release metadata.
- No ZFS snapshot creation/deletion logic, retention selection, Docker digest behavior, root enforcement, mail behavior, MQTT validation/publish behavior, dry-run semantics, operation order, or destructive-operation safety boundaries changed.

### Configuration, documentation, integration, and packaging

- Repair the stale `config.example.md` that was present in the supplied 0.0.4 archive even though the 0.0.4 history/verification described it as removed. Preserve the path rather than deleting it and rewrite it as a current supplemental TOML reference.
- Document the single public `-c CONFIG` option and every supported `[application]`, `[mail]`, and `[mqtt]` setting in `config.example.md`; remove obsolete multi-flag and `mqtt.json` instructions from that file.
- Keep `config-example.toml` as the loadable fully commented example; add README/setup guidance to copy `datasets.example.txt` to the configured dataset filename before first use.
- Correct README current-use text that incorrectly claimed `datasets`, `snaplist`, and `full-snaplist` were included in the supplied archive. The release only ships `datasets.example.txt`; no missing historical files were invented or reconstructed.
- Fix `.gitignore` so broad private `config*` exclusion still protects operational configs while explicitly keeping `config-example.toml` and `config.example.md` trackable, alongside the existing `datasets.example.txt` exception.
- Fix copied Home Assistant naming remnants: replace `Syncerate`/`syncerate` descriptions, fallback names, trigger ID, and unknown-status title with `SnapBeforeWatchTower`/`snapbeforewatchtower`. The MQTT topic and notification logic are unchanged.
- Extend `commented_code_map.md` with the current configuration, safety, dependency, `.gitignore`, dataset-example, and Home Assistant integration files while retaining complete Python function/class/command explanations.
- Keep `SAFETY.md` and its disclaimer/liability/data-loss notices unchanged.
- Refresh `VERIFICATION.md` with post-change compile, regression, CLI-boundary, documentation/config-coverage, naming, manifest, and clean-package checks.
- Preserve every path present in the supplied 0.0.4 archive. No source/project file is removed and no runtime/cache material is added to the release ZIP.

## 0.0.4 — 2026-09-15

### Application code changes (complete)

- Bump the application version from 0.0.3 to 0.0.4.
- Replace the multi-flag runtime interface with one TOML configuration file. The only public application CLI option is now `-c CONFIG`.
- Remove public `--version`, `--mqtt-config`, `--command`, `--file`, `--older-than`, `--retain-count`, `--send-mail`, `--mail-on-success`, `--dry-run`, and the automatic `-h/--help` option so operational settings cannot be split between CLI and TOML.
- Add `load_app_config()` using Python 3.11+ standard-library `tomllib`. It validates the exact `[application]`, optional `[mail]`, and optional `[mqtt]` tables and rejects unsupported/legacy keys.
- Map TOML application values into the existing runtime attributes so the original ZFS snapshot creation/deletion, retention, Docker digest, logging, mail, root-check, and operation-order code can be reused unchanged.
- Reuse the existing `parse_older_than()` function for TOML `older_than` validation instead of creating a second retention-duration parser.
- Resolve `dataset_file` relative to the TOML file, making scheduled execution independent of the process working directory.
- Move mail settings into optional `[mail]` with explicit `enabled`, `recipient`, and `on_success`. Disabled mail maps to the original no-recipient behavior.
- Change `mqtt_report.load_config()` into `validate_config()` for TOML-sourced values. MQTT retains direct plain-string `password`, QoS, verified TLS, certificate, timeout, non-retained publish, sanitized error, and child-process behavior.
- Add explicit `[mqtt].enabled`. Disabled MQTT requires no broker fields/Paho dependency, while unsupported MQTT keys are still rejected.
- Normalize TOML empty strings for optional MQTT username/password/certificate fields to `None`, because TOML has no JSON-style `null` literal.
- Resolve MQTT CA/client certificate/key paths relative to the TOML file.
- Preserve dry-run MQTT suppression and validate enabled MQTT settings without requiring Paho during dry-run.
- Update the private `mqtt_report.py --publish` worker error text to point users to `SnapBeforeWatchTower.py -c CONFIG`; `--publish` remains internal-only and is not a public app flag.
- No ZFS retention selection rules, snapshot naming, Docker failure semantics, mail command behavior, root enforcement, MQTT payload schema, MQTT retain/QoS semantics, or destructive-operation safety behavior changed.

### Configuration, documentation, tests, and packaging

- Add `config-example.toml` as the single complete configuration example. Every setting has inline comments explaining purpose, valid values, defaults/behavior, relative-path rules, and security implications.
- Include all former `mqtt.json` settings directly in `[mqtt]`, including the requested plain `password = "<String>"`, and include mail as an optional TOML feature.
- Set the example to `dry_run = true`, `[mail].enabled = false`, and `[mqtt].enabled = false` for a safer first run.
- Remove obsolete `config.example.md`, `mqtt.example.json`, and operational `mqtt.json`, because the application no longer reads those formats/files.
- Update `.gitignore` to ignore `config.toml`, the expected private operational TOML that may contain an MQTT password.
- Rewrite README.md for current TOML-only usage, the single `-c CONFIG` invocation, every TOML setting, dataset format, retention behavior, external commands, optional mail/MQTT, logging, and safety. No old-version history is kept in README.
- Rewrite `commented_code_map.md` to cover every application/test function/class and every external/private command, including why each exists and which original helpers remain preserved but unused.
- Update regression tests for TOML loading, relative paths, optional section defaults, legacy-key rejection, direct MQTT password handling, TLS paths, and the single-public-flag parser boundary while retaining the original retention/dry-run/root/order/mail tests.
- Refresh VERIFICATION.md after compile, TOML parse, CLI-boundary, documentation-coverage, regression, manifest, clean-package, and fresh-ZIP checks.

## 0.0.3 — 2026-09-15

### Application code changes (complete)

- Bump the application version from 0.0.2 to 0.0.3.
- Replace the MQTT `password_env` environment-variable credential model with the requested direct JSON field `"password": "<String>"`.
- `mqtt_report.load_config()` now accepts `password` as an optional nonempty string, requires `username` when a password is supplied, and rejects the old `password_env` key as unsupported.
- `mqtt_report.worker()` now passes the configured JSON password directly to Paho authentication instead of looking up an environment variable.
- Remove now-unused `os` and `re` imports from `mqtt_report.py`.
- Update `--mqtt-config` CLI help to state that username/password are read directly from JSON.
- Preserve the existing MQTT child-worker boundary: broker credentials remain off the process command line, publish failures remain sanitized, timeout/QoS/TLS/retain behavior is unchanged, and MQTT failure still cannot replace the underlying snapshot job outcome.
- No ZFS snapshot creation/deletion, retention calculation, Docker capture, logging, mail, root enforcement, MQTT payload schema, TLS behavior, publish QoS/retain behavior, or operation ordering changed.

### Configuration, documentation, tests, and packaging

- Migrate the supplied operational `mqtt.json` from `password_env` to `password`, preserving the user's existing configured broker password under the requested key.
- Update `mqtt.example.json` and `config.example.md` to show `"password": "<String>"` directly and remove environment-variable/sudo-preservation setup.
- Update README.md for current 0.0.3 behavior only: direct JSON password configuration, ordinary `sudo` invocation, current payload version, file-permission warning, and unchanged sanitized child-worker behavior.
- Update `commented_code_map.md` for version 0.0.3 and the direct-password validation/publish/test paths.
- Update CLI and MQTT tests to expect 0.0.3, direct JSON password authentication, username/password validation, and rejection of the retired `password_env` key.
- Refresh VERIFICATION.md after release checks and rebuild a clean ZIP excluding `.git`, runtime logs, Python caches/bytecode, test/build caches, and temporary files.

## 0.0.2 — 2026-09-15

### Application code changes (complete)

- Bump the application version from 0.0.1 to 0.0.2.
- Keep the existing safe MQTT credential model: `password_env` still names an environment variable and the password is still never accepted as a JSON password field.
- Add explicit validation that `password_env` is a conventional environment-variable name (`[A-Za-z_][A-Za-z0-9_]*`). This catches the exact misconfiguration where a literal broker password was placed in `password_env` instead of a variable name.
- Replace the ambiguous missing-password error with actionable `sudo --preserve-env=<password_env-name>` guidance while deliberately not echoing the configured value, because a mistaken value could itself be a password.
- Expand the `--mqtt-config` CLI help so the environment-variable requirement and dry-run behavior are visible directly in `--help`.
- No ZFS snapshot creation/deletion, retention calculation, Docker capture, logging, mail, root enforcement, MQTT payload schema, TLS behavior, publish QoS/retain behavior, or operation ordering changed.

### Configuration, documentation, tests, and packaging

- Correct the supplied operational `mqtt.json` so `password_env` contains `SNAP_MQTT_PASSWORD` instead of a literal secret; no broker password is retained in the release copy.
- Update `mqtt.example.json` to demonstrate a username plus `SNAP_MQTT_PASSWORD` variable reference rather than leaving the credential relationship implicit.
- Update README.md and config.example.md with the exact export plus `sudo --preserve-env=SNAP_MQTT_PASSWORD` invocation, service-manager guidance, variable-name rules, and current 0.0.2 payload example. README remains current-usage documentation only.
- Update `commented_code_map.md` for version 0.0.2, the stricter `load_config()` behavior, the MQTT regression test, and `.gitignore`.
- Extend CLI tests so `--mqtt-config` must appear in `--help`, and update version expectations to 0.0.2.
- Extend MQTT tests to cover malformed environment-variable names, the literal-password mistake, missing/empty variables with sudo guidance, and continued secret redaction.
- Fix `.gitignore` typo `__pycachhe__/` to `__pycache__/` and add common Python bytecode, pytest, build, dist, and egg-info exclusions required by the clean-package policy.
- Refresh VERIFICATION.md after the release checks and package only clean project files, excluding `.git`, runtime logs, Python caches/bytecode, test/build caches, and temporary files.

## 0.0.1 — 2026-09-15

The supplied `SnapBeforeWatchTower-main.zip` contained four files and no explicit version or version history. This is its first recorded release; the unversioned input is treated as the 0.0.0 baseline for this initial increment, not claimed as an earlier published release.

### Application code changes (complete)

- Add the module constant `__version__ = "0.0.1"`.
- Register `--version` on the existing parser. It exits before logging, privilege checks, or external commands.
- Add optional `--mqtt-config PATH` final reporting using `mqtt_report.py` and optional `paho-mqtt` dependency.
- Validate MQTT JSON, dependency availability, credentials by environment-variable reference, publish topics, QoS, timeout, and verified TLS/certificate settings before dataset operations.
- Publish one non-retained JSON report matching the supplied Home Assistant fields: `status`, `title`, `name`, `job`, `exit_code`, `warning`, `error`, and `stderr`, plus command/version/run metadata.
- Suppress MQTT delivery during dry-run so a preview cannot advance automation; preserve the underlying process result when MQTT delivery fails.
- Bound MQTT work in a child process and enforce a 1–120 second total timeout. Keep secrets and broker parameters off the child command line and sanitize publish errors.
- Split the original `main()` operation body into `run(args, reporter)` so the reporter can observe final success, exceptions, and non-root exits without duplicating operation logic.
- Clarify existing `--retain-count` help: it applies to snapshot and log retention, and nonpositive values disable the count floor.
- Clarify existing `--mail-on-success` help: it adds success mail without disabling failure mail.
- Clarify existing `--dry-run` help: ZFS listing, logging, and requested mail still occur.
- No snapshot creation/deletion, retention, ZFS/Docker command execution, logging, email, or privilege-check behavior changed. All original functions and classes, including unused helpers, are retained.

### Documentation and project files

- Rewrite README.md for current setup, every command/flag, dataset format, retention rules, logging, notifications, exit behavior, and existing operational limitations. Correct the Python minimum from 3.9 to 3.10 and remove unsupported guarantees.
- Preserve the original README disclaimers and license statement in SAFETY.md.
- Add commented_code_map.md explaining every application and test function, nested helper, class, and command, including why it exists and whether the CLI uses it.
- Add config.example.md with all available flags and aliases, both command modes, defaults, and email/dry-run behavior; add datasets.example.txt.
- Add mqtt.example.json and requirements-mqtt.txt with every MQTT setting and the optional dependency range.
- Add tests/test_app.py and tests/test_mqtt.py with standard-library tests of retention, dry-run boundaries, non-root refusal, errors, command order, CLI parsing/version behavior, MQTT JSON/schema compatibility, config validation, redaction, TLS/auth arguments, timeouts, and final-report lifecycle. External operations are mocked.
- Add this VERSIONING.md as the single version history file (no duplicate differing only by filename case).
- Preserve `snaplist` and `full-snaplist` byte for byte; retain all four original paths.

### Verification and packaging

Check Python compilation, CLI help/version and invalid arguments, mocked behavior tests, unchanged operational source structure, documentation coverage, original-file preservation, and ZIP extraction/content equality. Exclude Python bytecode, caches, temporary files, and runtime logs. Exact results and per-file SHA-256 manifests accompany the release ZIP in the verification report. Live Linux/ZFS/Docker/mail integration requires a suitable test host and is not certified by these checks.
