# Commented code map

This map describes the current application, why each function/class exists, and every external command the code can execute. It is not a version history.

## `SnapBeforeWatchTower.py`

### Module-level behavior

- `__version__` — current application release number embedded in MQTT reports, exposed by the public `--version` flag, and maintained in `VERSIONING.md`.
- TOML is parsed with Python's standard-library `tomllib`. Normal operation uses `-c CONFIG`; `-h`/`--help` and `--version` are informational flags. All operational values still come from the TOML file.

### Classes and functions

- `CustomLogger(logging.Logger)` — retained original helper that builds a logger with file and console handlers. The current main flow uses `setup_logger()` instead, but this class is preserved because it came from the original application and may still be useful to installations importing it.
  - `CustomLogger.__init__(name, log_filename)` — installs DEBUG file output and INFO console output with the standard formatter.

- `setup_logger(log_folder, log_date, prefix="SnapBeforeWatchTower")` — creates the active main logger and error logger for a run with the configured prefix on .log/.err names. It returns both loggers plus the `.err` path so final cleanup can remove an empty error file.
  - nested `_build_logger(name, level, handlers)` — centralizes handler formatting/installation and clears stale handlers so repeated in-process test/application runs do not duplicate output.

- `choose_log_folder(preferred_root_folder, fallback_folder=None)` — retained original root/non-root log-folder helper. The current run path uses `pick_log_folder()`; this function remains for compatibility with the original source.

- `runtime_base_dir()` — resolves the actual source script directory, or the actual executable directory when frozen. The configured fixed logging policy uses this directory even when the executable is in dist/.

- `pick_log_folder(script_log_folder, tmp_name="SnapBeforeWatchTower")` — creates and returns the fixed application-local logs directory. It never switches to temporary storage; permission failures propagate before external operations. The unused tmp_name argument remains for caller compatibility.

- `CommandError(RuntimeError)` — structured exception for failed external commands run through `run_cmd()`. It retains the command, return code, stdout, and stderr so the real failure propagates without silently continuing destructive logic.
  - `CommandError.__init__(cmd, returncode, stdout, stderr)` — stores command-result details and creates a concise exception message.

- `MissingDatasetsError(RuntimeError)` — run failure for one or more configured datasets that ZFS explicitly reports as nonexistent. With `continue_on_missing_dataset=true` it is raised after remaining configured datasets and normal log cleanup; with the setting false it is raised immediately. Its message keeps the explicit `dataset does not exist` reason for mail/MQTT reporting.
  - `MissingDatasetsError.__init__(datasets)` — stores missing dataset names and builds the user-facing final failure text.

- `DatasetCommandFailuresError(RuntimeError)` — aggregate final failure raised after one or more continuable checked per-dataset `zfs list`/`zfs destroy` command failures when `continue_on_other_failures=true`. It can also mention missing datasets already recorded in the same run.
  - `DatasetCommandFailuresError.__init__(failures, missing_datasets=())` — stores the failed dataset/exception pairs plus any missing dataset names and builds the final summary used by mail/MQTT.

- `is_missing_dataset_error(exc)` — inspects captured ZFS stderr from either `subprocess.CalledProcessError` or `CommandError` and returns true only for known absent-dataset wording (`dataset does not exist` or `no such pool or dataset`). This isolates the dedicated missing-dataset policy from unrelated failures.

- `remember_missing_dataset(error_logger, missing_datasets, dataset, exc)` — records each explicitly missing dataset once and logs that it is a run failure. The separate policy helper decides whether processing continues or stops.

- `is_checked_zfs_list_or_destroy_error(exc)` — accepts only `CommandError` instances produced by checked `zfs list` or `zfs destroy` commands. Snapshot creation, Docker, config, input, and unrelated failures are intentionally excluded from `continue_on_other_failures`.

- `remember_dataset_command_failure(error_logger, failures, dataset, exc)` — records one continuable per-dataset list/destroy failure, including command/stderr in the error log, so processing can move to the next configured dataset while preserving a final failure result.

- `handle_dataset_command_failure(error_logger, dataset, exc, missing_datasets, other_failures, continue_on_missing_dataset, continue_on_other_failures)` — single policy gate shared by create/delete loops. Missing-dataset errors follow `continue_on_missing_dataset`; other checked list/destroy failures follow `continue_on_other_failures`; anything else returns unhandled so the original exception propagates immediately.

- `run_cmd(cmd, logger=None, error_logger=None, check=True, dry_run=False)` — shared captured-subprocess helper. It avoids terminal spam, records failures through the error logger, raises `CommandError` when requested, and suppresses actual execution when `dry_run=True`.

- `get_newest_files(log_dir, prefix)` — finds the newest .log and .err independently by modification time, restricted to the exact escaped PREFIX-Date-* generated name pattern so overlapping prefixes do not supply another job's attachments. Independent selection preserves the application's existing mail behavior even when one file is missing.

- `send_mail(subject, body, recipient, attachment_files=None)` — invokes the local `mail` program, placing all options before the recipient for compatibility with common mail/mailx implementations. It returns the mail process exit code and stderr instead of hiding delivery failure.

- `MailTo(logger, error_logger, recipient, log_folder, subject=..., intro=..., prefix=..., title="", comment="")` — places the optional shared heading and unmodified multiline comment at the top, then builds the email body from the newest error log (included only if non-empty) and newest main log, attaches available logs, sends the message, then delegates result logging to `WasMailSent()`.

- `WasMailSent(logger, error_logger, MailExitCode, popenstderr)` — writes a clear success/failure result for the local mail command without changing the underlying snapshot result.

- `parse_older_than(value)` — converts `Nd`, `Nw`, or `Nm` strings to `datetime.timedelta`. Months intentionally mean 30 days. It rejects negative, fractional, uppercase, and malformed values. TOML loading reuses this existing parser instead of duplicating retention-age logic.

- `create_snapshot(logger, error_logger, dataset, dry_run=False)` — creates one timestamped managed snapshot for one dataset. In dry-run it only reports what would be created. Real ZFS failures are logged and re-raised so later logic cannot treat a failed creation as success.

- `extract_snapshot_date(snapshot_name)` — retained original timestamp parser for a managed snapshot-name fragment. The active retention implementation performs its own regex parse because it needs the complete snapshot match.

- `is_older_than(logger, error_logger, snapshot_date_str, older_than)` — retained original age helper. A malformed timestamp logs an error and returns `False`, which is the safe no-delete outcome.

- `delete_old_snapshots(logger, error_logger, dataset, older_than, retain_count, dry_run=False)` — lists snapshots for one dataset, selects only names matching SnapBeforeWatchTower's managed pattern, protects the newest count floor, applies the strict age cutoff, then destroys only snapshots that satisfy both rules. Invalid/unmanaged names are never selected. The ZFS list is executed even in dry-run so the preview is based on real current state.

- `delete_old_files(logger, error_logger, log_folder, older_than, retain_count, dry_run=False, prefix="SnapBeforeWatchTower")` — matches an anchored, regex-escaped prefix and groups `.log`, `.err`, and `.digest` files by embedded run timestamp, protects the configured newest group count, then deletes only old eligible groups. Dry-run reports candidates without removing them.

- `print_separator(logger, error_logger=None)` — writes the existing visual separator to the selected logger so terminal/log output remains readable.

- `save_docker_image_digests(logger, error_logger, log_folder, log_date, dry_run=False, prefix="SnapBeforeWatchTower")` — uses the same configured prefix as .log/.err and runs `docker images --digests` during real `create` operations and writes the output into the same timestamp group as the logs. Dry-run skips Docker. Docker failure is nonfatal but is captured as an error/warning, and partial digest output is not intentionally retained.

- `default_log_prefix()` — derives the basename of the actual resolved source or frozen executable, without its final extension, for an empty/omitted logging prefix and the default email heading.

- `load_report_settings(document)` — validates optional [logging] and [report] tables, rejects unknown keys/types/NUL and multiline prefix/title values, and restricts a custom prefix to a single safe filename component. It preserves comment whitespace/newlines as decoded by TOML.

- `load_app_config(path)` — loads the single TOML file and converts its settings into the runtime shape used by `run()`. It validates supported sections/keys/types, reuses `parse_older_than()`, resolves `dataset_file` relative to the TOML, validates `continue_on_missing_dataset` and `continue_on_other_failures` as booleans (both default `true` when omitted for backward compatibility), turns disabled mail into `send_mail=None`, passes validated log_prefix/report_title/report_comment to run(), applies a nonempty [report].title over the MQTT-specific title, and delegates [mqtt] validation to `mqtt_report.validate_config()`.

- `main()` — first recognizes the private `--mqtt-publish-worker` switch **only when frozen by PyInstaller**, allowing the standalone executable to act as its own bounded MQTT worker without exposing credentials on argv. Otherwise it builds the public CLI: `-c CONFIG` remains required for normal operation, standard `-h`/`--help` prints all public flags, and `--version` prints `__version__`; both informational flags exit before TOML loading or operations. Help uses argparse.RawDescriptionHelpFormatter to preserve examples, explains the required -c path, create/delete modes, Linux/root requirement, TOML-relative file paths, dry-run side effects, fixed log storage, [logging].prefix and [report].title/comment with newline syntax, and documentation locations. The parser generates usage for every public flag; operational CLI flags remain rejected. After normal parsing it loads TOML, creates the optional MQTT RunReporter with the preserved report comment, and enters the operation flow.

- `run(args, reporter)` — active operation coordinator. It resolves the fixed log folder, propagates the configured prefix to log/digest/retention/mail functions and title/comment to every success/failure mail branch, attaches the MQTT error observer, enforces root before dataset/Docker/ZFS operations, reads datasets, and executes create/delete behavior in file order. Missing-dataset errors are handled by `continue_on_missing_dataset`; other checked per-dataset `zfs list`/`zfs destroy` failures are handled by `continue_on_other_failures`. A `true` policy records the failure and moves to the next dataset, then raises an aggregate final failure after normal remaining processing/log cleanup; a `false` policy stops immediately. Snapshot-create failures that are not explicit missing-dataset errors and global/config/root/input failures remain immediately fatal. Mail failure reports are sent whenever mail is enabled; mail success reports require `[mail].on_success=true`. The same policy applies in dry-run, whose mail subjects/intro are explicitly marked as dry-run. Empty-current-`.err` cleanup remains unchanged.

## `mqtt_report.py`

- `MQTTPublishError` — parent-side MQTT worker failure type carrying only a sanitized exception-class reason; it deliberately excludes worker exception text and credentials.
  - `MQTTPublishError.__init__(reason="UnknownError")` — stores the parent-sanitized reason, substitutes an absent/non-string reason, and builds a diagnostic without secret worker text.
### Constants

- `DEFAULTS` — default MQTT port/title/auth/QoS/TLS/certificate/timeout settings plus `on_success=false`, used only when MQTT is enabled.
- `SUPPORTED_KEYS` — exact accepted TOML `[mqtt]` keys after the top-level `enabled` switch has been removed by `load_app_config()`.
- `OPTIONAL_STRING_KEYS` — optional string fields that may be represented by `""` in TOML because TOML has no `null` value. Empty strings are normalized to `None` before publishing.

### Classes and functions

- `validate_config(supplied, base_dir, dry_run=False, enabled=True)` — validates TOML-sourced MQTT settings. Unsupported keys are rejected even when disabled. When disabled, no broker details or Paho dependency are required. When enabled, it validates broker/topic/QoS/timeout/TLS/auth/`on_success`, resolves TLS files relative to the TOML directory, normalizes empty optional strings, and requires `paho-mqtt` even in dry-run because failure reporting remains active there.

- `ErrorCapture(logging.Handler)` — bounded in-memory collector for current-run error messages used in MQTT payloads. It avoids rereading older `.err` files and caps captured text at 4096 characters.
  - `ErrorCapture.__init__()` — configures ERROR-level capture and starts with empty text.
  - `ErrorCapture.emit(record)` — ignores separator-only messages and retains only the newest bounded error text.

- `build_payload(config, command, version, exc, errors, run_id, dry_run=False, comment="")` — adds the unmodified comment as a JSON string and translates the actual process outcome into the Home Assistant JSON contract. It distinguishes success/failure exit codes, preserves nonfatal logged errors as `warning=true`, adds bounded failure/stderr text, includes command/version/run/time metadata, and exposes `dry_run=true|false` for consumers.

- `publish_report(config, payload)` — launches the Python module in source mode, or re-executes the application binary with the private worker switch when frozen. A subprocess timeout bounds delivery; broker settings and payload travel over stdin, keeping credentials off argv. Only a validated exception-class reason is surfaced; arbitrary worker text is excluded from logs.

- `RunReporter` — context manager that observes exactly one application run and publishes at most one final MQTT status without masking the underlying result.
  - `RunReporter.__init__(config, command, version, dry_run=False, comment="")` — records the comment and settings, creates a unique run ID, and prepares an `ErrorCapture` handler.
  - `RunReporter.__enter__()` — returns the reporter for attachment to the application's error logger.
  - `RunReporter.attach(error_logger)` — attaches current-run error capture after logging is initialized.
  - `RunReporter.__exit__(exc_type, exc, traceback)` — detaches capture, does nothing when MQTT is disabled, otherwise passes the stored comment into the final payload and builds it for both real and dry-run executions, suppresses only successful reports when `[mqtt].on_success=false`, always attempts failure reports, logs sanitized MQTT failure/timeout messages, and always returns `False` so original exceptions continue propagating.

- `worker()` — child-process Paho publisher. It reads its request from stdin, constructs optional username/password auth and verified TLS context, then publishes exactly one non-retained message.

- module `__main__` guard — accepts only the private internal `--publish` worker switch. This is not a public application flag; users run `SnapBeforeWatchTower.py -c CONFIG`. Any other direct invocation of `mqtt_report.py` exits.

## External commands and why they exist

- `zfs snapshot DATASET@SnapBeforeWatchTower-Date-...` — creates the managed recovery point requested by `command="create"`.
- `zfs list -H -t snapshot -o name DATASET` — obtains current snapshot names for safe, explicit retention calculation. It is intentionally non-recursive and also runs in dry-run.
- `zfs destroy SNAPSHOT` — destroys only managed snapshots selected by both count-floor and age rules; suppressed in dry-run.
- `docker images --digests` — records the current local Docker image/digest inventory before snapshots during a real `create` run. Failure is nonfatal.
- `mail -s SUBJECT [--attach FILE ...] RECIPIENT` — optional local email notification transport; enabled only by TOML `[mail]` settings.
- `[python, -B, mqtt_report.py, --publish]` — private bounded MQTT child process. `--publish` is internal-only and is never a user-facing SnapBeforeWatchTower flag.

## `tests/test_app.py`

- `temporary_directory()` — disposable filesystem fixture with cleanup for portable tests.
- `write_config(...)` — creates minimal TOML configurations so integration tests exercise the real loader instead of fabricating argparse namespaces.
- `BehaviorTests` — regression suite for configuration mapping plus original safety/retention/mail/Docker/run-order behavior.
  - `setUp()` — creates mock loggers.
  - `test_duration_units_and_invalid_input()` — verifies accepted/rejected age syntax.
  - `test_toml_config_maps_former_flags_and_resolves_relative_dataset()` — proves old operational flags now come from TOML, mail/MQTT map correctly, and dataset paths are TOML-relative.
  - `test_toml_optional_sections_default_disabled()` — proves omitted optional notification sections are safely disabled and the two continuation settings map correctly.
  - `test_continuation_settings_default_true_when_omitted_for_older_configs()` — proves older TOML files without the two new keys retain default-true continuation behavior.
  - `test_toml_invalid_values_and_old_flag_keys_are_rejected()` — rejects invalid core values, non-boolean continuation settings, unknown/legacy keys, invalid enabled mail, retired `password_env`, and unsupported sections.
  - `test_retention_preserves_newest_and_ignores_unmanaged_or_invalid_dates()` — verifies count-floor ordering and managed-name filtering.
  - `test_retention_preserves_recent_snapshot_without_count_floor()` — verifies age protection still applies with no count floor.
  - `test_nonpositive_count_disables_floor()` — verifies zero/negative counts do not accidentally protect old snapshots.
  - `test_dry_run_lists_but_never_creates_destroys_or_captures_docker()` — proves destructive/create commands are suppressed while real snapshot listing remains.
  - `test_list_failure_prevents_destroy()` — proves a failed ZFS list aborts before destroy.
  - `test_create_failure_propagates()` — proves the low-level snapshot helper still re-raises ZFS creation failures for the run coordinator to classify.
  - `test_missing_dataset_detection_only_accepts_missing_zfs_messages()` — proves only known absent-dataset stderr is classified as the dedicated missing-dataset case.
  - `test_checked_zfs_list_destroy_detection_excludes_snapshot_and_unrelated_commands()` — proves `continue_on_other_failures` is limited to checked ZFS list/destroy `CommandError` instances.
  - `test_create_continues_after_missing_dataset_then_fails_run_and_sends_failure_mail()` — proves `continue_on_missing_dataset=true` processes later datasets, performs normal cleanup, then returns the missing-dataset aggregate failure and failure mail.
  - `test_delete_continues_after_missing_dataset_and_processes_following_dataset()` — proves delete/retention mode has the same configured missing-dataset continuation/final-failure behavior.
  - `test_missing_dataset_stops_immediately_when_configured_false_and_reports_failure()` — proves `continue_on_missing_dataset=false` stops before later datasets/cleanup while still reporting failure.
  - `test_other_zfs_list_destroy_failure_continues_when_configured_true_then_fails_run()` — proves both list and destroy failures are recorded, later datasets/cleanup continue, and the final result/mail remain failure when `continue_on_other_failures=true`.
  - `test_other_zfs_list_destroy_failure_stops_immediately_when_configured_false()` — proves the same checked failure stops immediately and still sends failure mail when `continue_on_other_failures=false`.
  - `test_snapshot_create_failure_still_aborts_even_when_other_failure_continuation_is_true()` — proves unrelated snapshot-create errors are outside `continue_on_other_failures` and remain immediately fatal.
  - `test_log_groups_count_age_and_dry_run()` — verifies log-group retention and dry-run behavior.
  - `test_docker_nonzero_is_logged_and_returns_none()` — verifies Docker digest failure stays nonfatal and leaves no digest artifact.
  - `test_nonroot_refuses_before_dataset_or_external_commands()` — verifies root enforcement occurs before dataset/ZFS/Docker operations.
  - `test_runtime_base_dir_uses_actual_dist_directory_when_frozen()` — proves a frozen executable under dist/ uses that actual executable directory for logs, following the explicitly requested fixed logging policy. Expected paths use the host platform format.
  - `test_runtime_base_dir_uses_executable_directory_when_frozen_outside_dist()` — proves a frozen executable deployed outside `dist` uses its executable directory. Expected paths use the host platform format.
  - `test_frozen_private_mqtt_worker_entrypoint_bypasses_public_cli()` — proves the private worker switch invokes only the MQTT worker when running frozen and does not require `-c CONFIG`.
  - `test_main_create_order_and_docker_failure_continuation()` — verifies create-mode ordering remains digest, create/retain per dataset, then log cleanup.
  - `test_dry_run_continued_dataset_command_failure_still_reports_failure()` — verifies a continued per-dataset list failure in dry-run still ends as failure and sends explicitly DRY-RUN failure mail even with success mail disabled.
  - `test_dry_run_success_mail_respects_on_success()` — verifies successful dry-runs send mail only when `[mail].on_success=true` and mark the report as dry-run.
  - `test_main_dry_run_success_attempts_mail_and_mqtt_when_both_on_success_are_true()` — full `main()` regression proving one successful dry-run with both channels enabled attempts both mail and MQTT success reporting in the same execution.
  - `test_dry_run_failure_mail_is_sent_even_when_on_success_is_false()` — verifies a failed dry-run still sends failure mail when mail is enabled even with success mail disabled.
  - `test_mailto_returns_delivery_result()` — verifies the mail helper reports local transport success/failure back to the run coordinator.
  - `test_mail_options_precede_recipient()` — verifies safe/compatible local `mail` argument order.
- `CLITests` — parser-boundary regression suite.
  - `run_cli(*args)` — invokes the real script parser in a subprocess without bytecode generation.
  - `test_help_describes_all_public_flags()` — verifies both help aliases exit successfully and document `-c CONFIG`, `-h`/`--help`, `--version`, and the TOML-only operational-settings rule.
  - `test_version_exits_without_config()` — verifies `--version` exits successfully and reports the exact current release without requiring `-c`.
  - `test_config_is_required_and_retired_operational_flags_are_rejected()` — verifies normal execution still requires `-c CONFIG` and retired operational/long-form config flags remain rejected.

## `tests/test_mqtt.py`

- `MQTTTests` — offline validation and publish-lifecycle suite; no real broker or Paho installation is required.
  - `setUp()` — builds a reusable validated-looking MQTT baseline.
  - `validate(value, dry_run=True, enabled=True)` — convenience wrapper around the real TOML-era MQTT validator in a disposable base directory.
  - `test_config_defaults_tls_port_and_disabled_mode()` — verifies defaults, implicit TLS port when omitted, and disabled mode.
  - `test_invalid_config_stops_early()` — verifies bad topic/port/QoS/timeout/TLS/auth/certificate/legacy/unknown values are rejected.
  - `test_password_optional_strings_and_dependency_validation()` — verifies direct password auth, empty-string normalization, username requirement, and conditional Paho dependency enforcement.
  - `test_tls_relative_paths_resolve_from_toml_directory()` — verifies certificate files use the TOML directory as their base.
  - `test_payload_success_warning_and_failure_contract()` — verifies JSON payload status/exit/warning metadata for representative outcomes.
  - `test_missing_dataset_failure_keeps_existing_failure_contract_and_reason()` — proves a missing-dataset aggregate remains `status=failure`, `exit_code=1`, `warning=false`, and carries the specific missing-dataset reason in `error` without changing the Home Assistant contract.
  - `test_capture_is_bounded_and_ignores_separators()` — verifies MQTT error text is bounded and cosmetic separators are ignored.
  - `test_worker_publish_uses_auth_tls_and_no_retain()` — verifies Paho receives direct auth, TLS context, payload, and `retain=false`.
  - `test_publisher_timeout_stdin_and_failure()` — verifies timeout usage, stdin transport, and secret-safe worker failure handling.
  - `test_frozen_publish_reexecutes_binary_worker_without_credentials_on_argv()` — proves frozen MQTT uses the standalone executable plus only the private worker switch on argv while broker configuration stays in stdin JSON.
  - `test_worker_failure_reason_is_logged_without_exception_text()` — verifies a safe worker exception class is logged while broker/credential details remain absent.
  - `test_success_reporting_respects_on_success_in_real_and_dry_run()` — verifies MQTT success reports are suppressed when `on_success=false` and published when `on_success=true`, identically for real and dry-run executions.
  - `test_failure_reporting_ignores_on_success_in_real_and_dry_run()` — verifies MQTT failures publish even when `on_success=false`, identically for real and dry-run executions.
  - `test_reporter_publishes_once_and_does_not_mask_failure()` — verifies one failure report while the original exception still propagates.
  - `test_publish_errors_preserve_original_outcome()` — verifies MQTT delivery failure is sanitized and never changes the underlying operation outcome.

## Configuration and integration files

- `config-example.toml` — loadable, fully commented example containing every supported `[application]`, `[mail]`, and `[mqtt]` setting. It defaults to dry-run with mail and MQTT disabled for a safer first copy.
- `config.example.md` — supplemental human-readable reference for the current TOML-driven interface. It documents `-c CONFIG`, `-h`/`--help`, `--version`, and every supported TOML setting, but is never parsed by the application.
- `datasets.example.txt` — minimal two-line example of the dataset-list format consumed by `dataset_file`.
- `requirements-mqtt.txt` — optional Paho MQTT dependency list required whenever `[mqtt].enabled=true`, including dry-run because failures still publish.
- `requirements-build.txt` — pinned build-only dependency list containing PyInstaller and Paho MQTT.
- `SnapBeforeWatchTower.spec` — one-file PyInstaller recipe; `collect_submodules('paho')` ensures all MQTT modules are bundled even though the application validates/imports Paho dynamically.
- `build-pyinstaller.sh` — build entry point. It recreates one gitignored `.build-pyinstaller/` workspace containing `venv/`, `pip-cache/`, PyInstaller `work/`, and PyInstaller `config/`; removes legacy root-level `build/` and `.venv-build/` locations; cleans every generated/stale `dist/` entry except the tracked `dist/README.md`; builds the one-file executable with explicit `--workpath`/`--distpath`; checks `--help`/`--version`; and fails unless `dist/` contains exactly `SnapBeforeWatchTower` and `README.md`.
- `dist/README.md` — tracked build-output note kept beside the generated executable. The build script preserves it while removing every other stale/generated `dist/` entry.
- `homeassistant/SnapBeforeWatchtower-mqtt-persistent-notification.yaml` — example Home Assistant MQTT status automation for SnapBeforeWatchTower. It listens for the JSON report, sends Pushover success/failure/unknown notifications, and displays the payload dry_run mode as DRY-RUN or LIVE, plus the optional multiline comment in success/failure notifications. report_comment defaults to empty for older payloads.
- `SAFETY.md` — contains the project disclaimer/liability text requested for SnapBeforeWatchTower plus a project-specific destructive ZFS/log-retention warning and the existing no-license notice.
- `.gitignore` — excludes private operational `config*` files, runtime dataset/list files, logs, Python caches, legacy build locations, and the complete generated `.build-pyinstaller/` workspace while explicitly unignoring the shipped `config-example.toml`, `config.example.md`, `datasets.example.txt`, and `dist/README.md` files so they remain trackable.


## Public CLI and private worker commands

| Command/flag | What it does and why |
| --- | --- |
| `python3 SnapBeforeWatchTower.py -c CONFIG` | Loads the required job TOML file and executes its configured create/delete mode. The relative CONFIG path uses the shell working directory; file paths inside TOML use its directory. |
| `-h`, `--help` | Shows all public flags, invocation examples and operational boundaries, then exits before config loading and work. |
| `--version` | Shows the release embedded in __version__ and exits without config or work. |
| `dist/SnapBeforeWatchTower -c CONFIG` | Same job flow using the frozen interpreter and modules. External ZFS/Docker/mail tools remain host requirements. |
| `SnapBeforeWatchTower --mqtt-publish-worker` | Frozen-only, private worker switch. Reads broker settings/payload from stdin and publishes through the same mqtt_report.worker implementation, avoiding a duplicate publisher. |
| `python -B mqtt_report.py --publish` | Private source-mode worker; -B avoids bytecode caches. The parent enforces the timeout and surfaces only a safe exception-class reason. |

## Build commands and shell control

The build script's commands are explained here so its cleanup operations are visible before running it.

| Command/control | Purpose |
| --- | --- |
| `bash build-pyinstaller.sh` | Executes the shipped build recipe with Bash, without requiring an executable permission bit on the script. |
| `set -euo pipefail` | Exits on unhandled command errors, unset variables, and failed pipeline members so incomplete builds are not reported as successful. |
| `dirname`, `cd`, `pwd` | Resolve the script's absolute project directory and run PyInstaller from that directory. |
| `rm -rf --` | Removes the fixed .build-pyinstaller workspace and project-level build/.venv-build locations before rebuilding. These locations must not contain user data. |
| `mkdir -p --` | Recreates the workspace subdirectories and dist directory needed for build output. |
| `python3 -m venv` | Creates an isolated build interpreter under .build-pyinstaller/venv. |
| `python -m pip install -r requirements-build.txt` | Installs the pinned build dependencies with a local pip cache; requires package access. Runtime dependency instructions remain separate. |
| `find dist -mindepth 1 -maxdepth 1 ! -name README.md -exec rm -rf -- {} +` | Removes every stale top-level dist entry except README.md, including hidden entries and directories. |
| `test -f`, `test -x` | Check that the tracked README and generated executable exist and the executable is runnable. |
| `pyinstaller --noconfirm --clean --workpath WORK --distpath DIST SnapBeforeWatchTower.spec` | Replaces stale output, cleans PyInstaller caches, explicitly assigns work/output directories, and builds the one-file application from the spec. PYINSTALLER_CONFIG_DIR places config/cache inside the workspace. |
| `SnapBeforeWatchTower --help`, `--version` | Smoke-test the generated binary using informational commands that do not create job artifacts. |
| `shopt -s nullglob dotglob` / `shopt -u nullglob dotglob` | Include hidden dist entries in the array inventory without retaining an unmatched glob; restore normal glob settings afterward. |
| Arrays, `if`, `for`, `case`, `[[ ... ]]`, `(( ... ))` | Enforce exactly README.md plus the executable in dist, and ensure build/.venv-build remain absent. |
| `echo`, `printf`, `exit 1`, redirection | Print build result/errors, suppress help output, route diagnostics to stderr, and reject a failed layout. |

The PyInstaller spec uses Path(SPECPATH).resolve() to locate inputs, collect_submodules('paho') for dynamic MQTT imports, Analysis for dependency discovery, PYZ for bundled Python modules, and EXE for the one-file console executable.

## Documentation, setup, and verification commands

- `cp config-example.toml config.toml`, `cp datasets.example.txt datasets` create editable operational copies; `nano config.toml` / `nano datasets` customize them. The dataset filename must match the TOML value.
- `sudo python3 ... -c CONFIG` or `sudo ./dist/SnapBeforeWatchTower -c CONFIG` supplies the required Linux root privilege, including for dry-run.
- `python3 -m pip install -r requirements-mqtt.txt` installs the optional source-mode Paho dependency with the interpreter used for the job.
- `python3 -B -m unittest discover -s tests -v` runs the offline suite; external application operations are mocked.
- `sha256sum -c manifest.sha256` checks the release file hashes after extraction. The manifest excludes its own hash to avoid a self-reference.
- `README.md` describes current usage and all commands, with the exact disclaimer immediately below the title.
- `VERSIONING.md` records every created release and all code/documentation changes; patch rollover is 99 to the next minor version.
- `VERIFICATION.md` records the checks actually run for this release and the live integration limits.
- `manifest.sha256` records SHA-256 for every other delivered project file, enabling independent extracted-package integrity checks.


## Report/logging regression coverage

These test methods are in tests/test_app.py:

- test_optional_log_report_defaults_preserve_existing_configs() — checks that omitted sections remain accepted with basename prefix, empty shared title/comment and notifications disabled.
- test_report_title_precedence_and_comment_newlines_from_toml() — exercises escaped-newline and both multiline TOML string forms, literal backslashes, shared title override and empty-title fallback.
- test_invalid_log_report_values_fail_before_operations() — rejects invalid tables/keys/types, path/glob/NUL prefixes and multiline titles; verifies CLI validation exits before the operation or publishing.
- test_custom_prefix_log_files_and_retention_keep_other_prefixes() — creates real disposable .log/.err/.digest groups, verifies dry-run/count protection, then checks only the exact configured prefix is cleaned.
- test_custom_prefix_digest_filename() — verifies Docker output is written to the same prefixed timestamp group as logs, with Docker mocked.
- test_email_title_and_multiline_comment_precede_current_report() — checks the exact email heading/comment line breaks and custom-prefix attachment selection, including exclusion of overlapping-prefix files.
- test_main_propagates_log_prefix_and_shared_report_in_success_and_failure() — runs main with real TOML loading and mocked operations for success, continued dataset failure and non-root failure; checks mail and MQTT metadata and prefix propagation together.
- test_fixed_log_folder_has_no_temporary_fallback() — exercises the fixed directory with a non-root identity and verifies unwritable-directory errors propagate with no fallback mkdir.
- test_unwritable_logs_prevent_external_operations() — verifies logging setup failure stops before application commands or mail work.
- test_empty_prefix_uses_actual_source_or_frozen_basename() — verifies empty-prefix derivation from the source and a renamed frozen executable.

Additional tests in tests/test_mqtt.py:

- test_comment_newlines_survive_payload_json_and_worker_publish() — checks exact blank lines/trailing newline through JSON encoding/decoding and the real worker interface with a mocked Paho publisher, retaining retain=false.
- test_reporter_propagates_comment_for_success_and_failure() — verifies the context manager includes the same comment for both final outcomes.

The fixed runtime log directory can be dist/logs/ when the executable is run from dist/. The unchanged build script removes it on the next rebuild because it cleans every generated dist entry before enforcing the two-file post-build layout. dist/README.md and README.md describe that boundary.
