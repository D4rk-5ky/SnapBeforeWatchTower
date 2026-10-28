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

- `runtime_base_dir()` — returns the persistent application directory. Source mode uses the directory containing `SnapBeforeWatchTower.py`. A frozen executable inside a project `dist/` uses the project directory so runtime logs do not create `dist/logs/`; a frozen executable deployed elsewhere uses the directory containing `sys.executable`.

- `pick_log_folder(script_log_folder, tmp_name="SnapBeforeWatchTower")` — creates and returns the fixed application-local log directory, regardless of UID. Directory-creation failure propagates before external operations. `tmp_name` is retained as an unused compatibility parameter. There is no fallback or nested probe.

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

- `MailTo(logger, error_logger, recipient, log_folder, subject=..., intro=..., prefix=..., title="", comment="", name="")` — uses `name` as the email body heading, falling back to `title` for older callers, and places the unmodified multiline comment immediately below it. It preserves the caller's subject, then builds the email body from the newest error log (included only if non-empty) and newest main log, attaches available logs, sends the message, then delegates result logging to `WasMailSent()`.

- `WasMailSent(logger, error_logger, MailExitCode, popenstderr)` — writes a clear success/failure result for the local mail command without changing the underlying snapshot result.

- `parse_older_than(value)` — converts `Nd`, `Nw`, or `Nm` strings to `datetime.timedelta`. Months intentionally mean 30 days. It rejects negative, fractional, uppercase, and malformed values, integer/duration overflow, and a computed cutoff earlier than Python year 1. Overflow is normalized to `argparse.ArgumentTypeError`, which the loader converts into a configuration error before operations. TOML loading reuses this existing parser instead of duplicating retention-age logic.

- `create_snapshot(logger, error_logger, dataset, dry_run=False)` — creates one timestamped managed snapshot for one dataset. In dry-run it only reports what would be created. Real ZFS failures are logged and re-raised so later logic cannot treat a failed creation as success.

- `extract_snapshot_date(snapshot_name)` — retained original timestamp parser expecting `DateYYYY...` without the newer hyphen; it is unused by active retention. The active retention implementation performs its own regex parse because it needs the complete snapshot match.

- `is_older_than(logger, error_logger, snapshot_date_str, older_than)` — retained original age helper. A malformed timestamp logs an error and returns `False`, which is the safe no-delete outcome.

- `delete_old_snapshots(logger, error_logger, dataset, older_than, retain_count, dry_run=False)` — lists snapshots for one dataset, selects only names matching SnapBeforeWatchTower's managed pattern, protects the newest count floor, applies the strict age cutoff, then destroys only snapshots that satisfy both rules. Invalid/unmanaged names are never selected. The ZFS list is executed even in dry-run so the preview is based on real current state.

- `delete_old_files(logger, error_logger, log_folder, older_than, retain_count, dry_run=False, prefix="SnapBeforeWatchTower")` — matches an anchored, regex-escaped prefix and groups `.log`, `.err`, and `.digest` files by embedded run timestamp, protects the configured newest group count, then deletes only old eligible groups. Dry-run reports candidates without removing them.

- `print_separator(logger, error_logger=None)` — writes the existing visual separator to the selected logger so terminal/log output remains readable.

- `save_docker_image_digests(logger, error_logger, log_folder, log_date, dry_run=False, prefix="SnapBeforeWatchTower")` — uses the same configured prefix as .log/.err and runs `docker images --digests` during real `create` operations and writes the output into the same timestamp group as the logs. Dry-run skips Docker. Docker failure is nonfatal but is captured as an error/warning, and partial digest output is not intentionally retained.

- `default_log_prefix()` — derives the basename of the actual resolved source or frozen executable, without its final extension, for an empty/omitted logging prefix and the default email heading.

- `load_report_settings(document)` — validates optional [logging] and [report] tables, rejects unknown keys/types/NUL and multiline prefix/title/name values, and restricts a custom prefix to a single safe filename component. It strips surrounding name/title whitespace, preserves comment whitespace/newlines as decoded by TOML, and returns `(prefix, title, name, comment)` for the loader.

- `load_app_config(path)` — loads the single TOML file and converts its settings into the runtime shape used by `run()`. It maps optional `[report].name` to `args.report_name` independently of title/comment and validates supported sections/keys/types (including command string type before set membership so arrays/tables do not raise TypeError), reuses `parse_older_than()`, resolves `dataset_file` relative to the TOML, validates `continue_on_missing_dataset` and `continue_on_other_failures` as booleans (both default `true` when omitted for backward compatibility), turns disabled mail into `send_mail=None`, and delegates `[mqtt]` validation to `mqtt_report.validate_config()`.

- `main()` — first recognizes the private `--mqtt-publish-worker` switch **only when frozen by PyInstaller**, allowing the standalone executable to act as its own bounded MQTT worker without exposing credentials on argv. Otherwise it builds the public CLI: `-c CONFIG` remains required for normal operation, standard `-h`/`--help` prints all public flags, and `--version` prints `__version__`; both informational flags exit before TOML loading or operations. Retired operational CLI flags remain rejected. After normal parsing it loads TOML, creates the optional MQTT `RunReporter` with the run name/comment, and enters the operation flow.

- `run(args, reporter)` — active operation coordinator. It chooses logging, attaches the MQTT error observer, enforces root before dataset/Docker/ZFS operations, reads datasets, and executes create/delete behavior in file order. Missing-dataset errors are handled by `continue_on_missing_dataset`; other checked per-dataset `zfs list`/`zfs destroy` failures are handled by `continue_on_other_failures`. A `true` policy records the failure and moves to the next dataset, then raises an aggregate final failure after normal remaining processing/log cleanup; a `false` policy stops immediately. Snapshot-create failures that are not explicit missing-dataset errors and global/config/root/input failures remain immediately fatal. Every mail path forwards the configured log prefix, run name, fallback heading, and multiline comment, including aggregate list/destroy failures. Mail failure reports are sent whenever mail is enabled; mail success reports require `[mail].on_success=true`. The same policy applies in dry-run, whose mail subjects/intro are explicitly marked as dry-run. Empty-current-`.err` cleanup remains unchanged.

## `modules/mqtt_report.py`

- `MQTTPublishError.__init__(reason)` — retains a nonempty reason string and builds a credential-free parent exception message.
- `MQTTPublishError` — parent-side MQTT worker failure type carrying only a sanitized exception-class reason; it deliberately excludes worker exception text and credentials.
### Constants

- `DEFAULTS` — private normalized worker defaults, not extra TOML options. Public completion success policy comes from SendMQTTOnSuccess (default true).
- `SUPPORTED_KEYS` — the exact 22 canonical [mqtt] options. MQTT_JSON_Status is the sole completion enable; LiveMQTTEnabled is independent.
- `OPTIONAL_STRING_KEYS` — optional string fields that may be represented by `""` in TOML because TOML has no `null` value. Empty strings are normalized to `None` before publishing.

### Classes and functions

- `validate_config(supplied, base_dir, dry_run=False, config_path=None)` — validates TOML-sourced MQTT settings. Unsupported keys are rejected even when disabled. When disabled, no broker details or Paho dependency are required. When enabled, it validates the one shared broker/topic/QoS/timeout/TLS/auth block and SendMQTTOnSuccess, resolves TLS files relative to the TOML directory, normalizes empty optional strings, and requires `paho-mqtt` even in dry-run because failure reporting remains active there.

- `ErrorCapture(logging.Handler)` — bounded in-memory collector for current-run error messages used in MQTT payloads. It avoids rereading older `.err` files and caps captured text at 4096 characters.
  - `ErrorCapture.__init__()` — configures ERROR-level capture and starts with empty text.
  - `ErrorCapture.emit(record)` — ignores separator-only messages and retains only the newest bounded error text.

- `build_payload(config, command, version, exc, errors, run_id, dry_run=False, comment="", name="")` — assigns the friendly run name to MQTT `name`/`title` (using LiveBackupName/title fallbacks if empty), makes the friendly `name`/`title` agree and fixes `job` to the stable project identifier, adds the unmodified comment as a JSON string and translates the actual process outcome into the Home Assistant JSON contract. It distinguishes success/failure exit codes, preserves nonfatal logged errors as `warning=true`, adds bounded failure/stderr text, includes command/version/run/time metadata, and exposes `dry_run=true|false` for consumers.

- `publish_report(config, payload)` — launches the Python module in source mode, or re-executes the application binary with the private worker switch when frozen. A subprocess timeout bounds delivery; broker settings and payload travel over stdin, keeping credentials off argv. Only a validated exception-class reason is surfaced; arbitrary worker text is excluded from logs.

- `RunReporter` — context manager that observes exactly one application run and publishes at most one final MQTT status without masking the underlying result.
  - `RunReporter.__init__(config, command, version, dry_run=False, comment="", name="")` — records the name, comment and settings, creates a unique run ID, and prepares an `ErrorCapture` handler.
  - `RunReporter.__enter__()` — returns the reporter for attachment to the application's error logger.
  - `RunReporter.attach(error_logger)` — attaches current-run error capture after logging is initialized.
  - `RunReporter.__exit__(exc_type, exc, traceback)` — detaches capture, does nothing when MQTT is disabled, otherwise passes the stored name/comment into the final payload and builds it for both real and dry-run executions, suppresses only successful reports when `[mqtt].on_success=false`, always attempts failure reports, logs sanitized MQTT failure/timeout messages, and always returns `False` so original exceptions continue propagating.

- `worker()` — child-process Paho publisher. It reads its request from stdin, constructs optional username/password auth and verified TLS context, then publishes exactly one non-retained message.

- module `__main__` guard — accepts only the private internal `--publish` worker switch. This is not a public application flag; users run `SnapBeforeWatchTower.py -c CONFIG`. Any other direct invocation of `modules/mqtt_report.py` exits.

## External commands and why they exist

- `zfs snapshot DATASET@SnapBeforeWatchTower-Date-...` — creates the managed recovery point requested by `command="create"`.
- `zfs list -H -t snapshot -o name DATASET` — obtains current snapshot names for safe, explicit retention calculation. It is intentionally non-recursive and also runs in dry-run.
- `zfs destroy SNAPSHOT` — destroys only managed snapshots selected by both count-floor and age rules; suppressed in dry-run.
- `docker images --digests` — records the current local Docker image/digest inventory before snapshots during a real `create` run. A nonzero Docker result or digest-file write failure is logged and nonfatal; failure to launch Docker propagates and is fatal.
- `mail -s SUBJECT [--attach FILE ...] RECIPIENT` — optional local email notification transport; enabled only by TOML `[mail]` settings.
- `[python, -B, modules/mqtt_report.py, --publish]` — private bounded MQTT child process. `--publish` is internal-only and is never a user-facing SnapBeforeWatchTower flag.

## `tests/test_app.py`

- `temporary_directory()` — disposable filesystem fixture with cleanup for portable tests.
- `write_config(..., logging_settings="", report="")` — accepts optional logging/report fragments and creates minimal TOML configurations so integration tests exercise the real loader instead of fabricating argparse namespaces.
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
  - `test_runtime_base_dir_keeps_project_dist_clean_when_frozen()` — proves a frozen executable under `dist/` uses the project directory as its persistent base so runtime logs cannot pollute `dist/`.
  - `test_runtime_base_dir_uses_executable_directory_when_frozen_outside_dist()` — proves a frozen executable deployed outside a directory named `dist` still uses its executable directory as the persistent base.
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
  - `test_reporter_publishes_once_and_does_not_mask_failure()` — verifies one failure report while the original exception still propagates; logger messages are not fabricated child stderr.
  - `test_publish_errors_preserve_original_outcome()` — verifies MQTT delivery failure is sanitized and never changes the underlying operation outcome.

## Configuration and integration files

- `configs/config-example.toml` — loadable, fully commented example containing every supported `[application]`, `[mail]`, `[mqtt]`, `[logging]`, and `[report]` setting. It defaults to dry-run with mail and MQTT disabled for a safer first copy.
- `configs/config.example.md` — supplemental human-readable reference for the current TOML-driven interface. It documents `-c CONFIG`, `-h`/`--help`, `--version`, and every supported TOML setting, but is never parsed by the application.
- `configs/datasets.example.txt` — minimal two-line example of the dataset-list format consumed by `dataset_file`.
- `requirements-mqtt.txt` — optional Paho MQTT dependency list required when MQTT_JSON_Status or LiveMQTTEnabled is true, including dry-run because failures still publish.
- `requirements-build.txt` — pinned build-only dependency list containing PyInstaller and Paho MQTT.
- `SnapBeforeWatchTower.spec` — one-file PyInstaller recipe; `collect_submodules('paho')` ensures all MQTT modules are bundled even though the application validates/imports Paho dynamically.
- `build-pyinstaller.sh` — reproducible build entry point. It recreates one gitignored `.build-pyinstaller/` workspace containing `venv/`, `pip-cache/`, PyInstaller `work/`, and PyInstaller `config/`; removes legacy root-level `build/` and `.venv-build/` locations; cleans every generated/stale `dist/` entry except the tracked `dist/README.md`; builds the one-file executable with explicit `--workpath`/`--distpath`; checks `--help`/`--version`; and fails unless `dist/` contains exactly `SnapBeforeWatchTower` and `README.md`.
- `dist/README.md` — tracked build-output note kept beside the generated executable. The build script preserves it while removing every other stale/generated `dist/` entry.
- `homeassistant/SnapBeforeWatchtower-mqtt-persistent-notification.yaml` — example Home Assistant MQTT status automation for SnapBeforeWatchTower. It displays the friendly title/name, bounded comment and diagnostics, listens for the typed JSON report, sends bounded Pushover success/failure/unknown notifications, and rejects dry-runs before real notifications; it uses the same typed, bounded completion actions as the supplied example.
- `SAFETY.md` — contains the project disclaimer/liability text requested for SnapBeforeWatchTower plus a project-specific destructive ZFS/log-retention warning and the existing no-license notice.
- `.gitignore` — excludes private operational `config*` files, runtime dataset/list files, logs, Python caches, legacy build locations, and the complete generated `.build-pyinstaller/` workspace while explicitly unignoring the shipped `configs/config-example.toml`, `configs/config.example.md`, `configs/datasets.example.txt`, and `dist/README.md` files so they remain trackable.

## Additional existing test functions

- `test_optional_log_report_defaults_preserve_existing_configs()` — checks older configs receive basename logging and empty shared report values.
- `test_report_title_precedence_and_comment_newlines_from_toml()` — checks shared MQTT fallback-title precedence and basic/literal/multiline TOML comment decoding.
- `test_invalid_log_report_values_fail_before_operations()` — rejects invalid types, paths, glob syntax, multiline headings, unknown keys, and NUL before work.
- `test_custom_prefix_log_files_and_retention_keep_other_prefixes()` — proves custom-prefix file creation and age/count cleanup leave other prefixes alone.
- `test_custom_prefix_digest_filename()` — checks Docker inventory shares the selected prefix.
- `test_email_title_and_multiline_comment_precede_current_report()` — checks email content and exact-prefix attachment selection.
- `test_main_propagates_log_prefix_and_shared_report_in_success_and_failure()` — exercises the real loader/coordinator on success, continued list/destroy failure, missing dataset, fatal error, and root refusal; checks the run name, configured MQTT fallback title, mail metadata, and unchanged subjects.
- `test_fixed_log_folder_has_no_temporary_fallback()` — checks fixed placement for non-root callers and propagation of directory failure.
- `test_unwritable_logs_prevent_external_operations()` — proves log initialization failure prevents command/mail execution.
- `test_empty_prefix_uses_actual_source_or_frozen_basename()` — checks source, frozen, and unusual executable-name fallback handling.
- `test_comment_newlines_survive_payload_json_and_worker_publish()` — checks the run name and multiline text survive JSON serialization and the mocked Paho call.
- `test_reporter_propagates_comment_for_success_and_failure()` — checks both final MQTT outcome paths retain report text.

## Build commands and supporting files

- `python3 -m venv PATH` — creates the isolated build interpreter. Its `python -m pip install -r requirements-build.txt` installs the pinned build tools; `PIP_CACHE_DIR` confines download cache to the build workspace.
- `rm -rf -- PATHS` in `build-pyinstaller.sh` — removes only generated build roots/legacy build directories. `find dist ... ! -name README.md -exec rm -rf ...` removes stale delivery artifacts while preserving the tracked README. Run only within a reviewed project copy.
- `mkdir -p` creates generated directories; `cd` selects the project; `test -f`/`test -x` verify required outputs. Shell `shopt`, arrays, `case`, and count checks enforce exactly two entries in `dist/`. `printf`/`echo` print diagnostics; nonzero `exit` rejects invalid output.
- `pyinstaller --noconfirm --clean --workpath ... --distpath ... SnapBeforeWatchTower.spec` — rebuilds the one-file delivery; work/config are isolated. `Analysis` gathers source and Paho imports, `PYZ` packages modules, and `EXE` creates the console executable without UPX. `--help`/`--version` then smoke-test it.
- Frozen private `[executable, --mqtt-publish-worker]` — counterpart to the source MQTT child command; keeps credentials on stdin and applies the same parent timeout.
- README commands `cp`, `nano`, and `chmod 600` prepare private operational files; `sudo python3 ... -c CONFIG` or `sudo ./dist/SnapBeforeWatchTower -c CONFIG` runs the reviewed job. `python3 -B -m unittest discover -s tests -v` runs offline tests without bytecode. `sha256sum -c manifest.sha256` verifies packaged file integrity.
- `config.toml`, `datasets`, `AsusN14E-snaplist`, `Storage-Docker-Cleanup` — private runtime inputs excluded from distribution and explicitly ignored, including lowercase host-list names. Create local inputs from configs/ examples; the app reads only the configured dataset_file.
- `VERSIONING.md` — complete canonical release history. `versioning.md` is an identical lowercase compatibility copy, kept synchronized for the requested filename.
- `VERIFICATION.md` — release-specific checks and limitations. `manifest.sha256` covers every delivered project file except itself; `PACKAGE_MANIFEST.md` compares final paths/content with the supplied archive.
- MQTT module `__main__` error guard catches worker exceptions, prints only their class name, and exits 1, preventing broker/credential text from leaking to the parent.

- `test_shipped_example_covers_every_supported_setting_and_safe_defaults()` — parses the actual delivered TOML, checks the exact supported keys in all five sections, and loads it to verify dry-run and disabled-notification defaults without running external commands.

## Run-name regression coverage

- `test_report_name_loads_without_mqtt_and_is_optional()` — checks trimming, Unicode names, empty/whitespace fallback, and use with MQTT disabled.
- `test_email_run_name_then_comment_and_subject_unchanged()` — checks actual mail-helper output starts with name then the exact multiline comment, precedes outcome/logs, selects the configured attachments, and preserves success/failure subjects.
- `test_payload_friendly_name_title_and_stable_job_with_legacy_fallback()` — checks named and unnamed success/failure MQTT payloads use matching friendly name/title and the stable project job ID.
- `test_reporter_sends_run_name_for_real_and_dry_success_and_failure()` — checks the full reporter passes the configured name in live/dry-run success/failure messages without changing result semantics.
- Existing invalid-report, legacy-default, shipped-example, public-help, combined coordinator, and JSON/worker tests also cover the name field and reject invalid names before operations.

## Build helper interface and validation checks

- `build-pyinstaller.sh -h` / `--help` — prints requirements, all public build flags, cleanup paths, and output checks. Runs before any cleanup/installation so inspecting help cannot replace an executable or create a build directory.
- `build-pyinstaller.sh --version` — uses `python3 -B -c` and the standard-library `ast` module to read the literal `__version__` assignment from `SnapBeforeWatchTower.py`. It does not import application code, install dependencies, or create bytecode. Sharing the source version avoids a second version constant.
- The shell argument guard requires exactly one informational flag when arguments are present. Unknown flags, positional arguments, and flag combinations exit 2 before build work. With no arguments, the existing build and two-file `dist/` safety checks execute unchanged.
- `test_invalid_command_types_fail_before_operations_or_notifications()` — loads real TOML arrays, inline tables, booleans, and numbers through `main()` and verifies configuration exit 2 before the operation coordinator or reporter starts. This prevents an unhashable command from escaping validation as a traceback.
- `test_out_of_range_retention_fails_before_operations_or_notifications()` — checks a normal duration plus oversized days/weeks/months, a timedelta-valid but calendar-invalid cutoff, and a very long integer. Verifies the shared parser gives a controlled error and the CLI stops before work/reporting, avoiding a snapshot being created before cutoff arithmetic fails.
- MQTT test payload/reporter fixtures use `app.__version__` so the injected current version stays synchronized with source metadata.
- The Home Assistant YAML filename is preserved; its three delivery actions use `notify.pushover`, so the user must configure that service or adapt each action to their selected notification service.

## Integrated reporting architecture

`modules/mqtt_report.py` remains the application adapter and existing bounded completion
publisher. `modules/mqtt_reporting.py` is the supplied generic live engine, with usage
instructions in its module docstring. The app has small observer calls around
existing work. Dataset-list processing, create/delete order, retention selection,
commands, root checks, continuation policy, mail behavior and scheduling are not
reimplemented. Context-local observation keeps unrelated threads/imported calls
from being attributed to a run. It captures only actual child stderr, in order,
with a 4000-character tail; ErrorCapture log text is a separate warning detail.

The canonical [mqtt] options are the only public reporting configuration.
Removed duplicate names are rejected with replacement guidance; no hidden
legacy enable or credential block can override the selected connection. The actual process
exit code is authoritative: unhandled command exceptions remain app exit 1;
child_exit_code preserves a distinct failing child result. SystemExit and
KeyboardInterrupt are observed without suppressing or replacing them.

### `modules/mqtt_report.py` adapter changes

- `REPORTING_KEYS` — exact additional option names accepted in the existing [mqtt] table, keeping unknown-key validation explicit.
- `validate_config()` — validates the two independent canonical channel switches, rejects removed duplicate options, normalizes the one shared broker/auth/topic/TLS/certificate block and validates dependency availability, preserves literal passwords, stores config identity and independent completion/live flags, and validates the live engine before operations. Returns None when both channels are disabled.
- `build_payload()` — emits the required typed completion contract with matching friendly name/title and stable job. It reports the process outcome, captures actual exception stderr only as a fallback, and keeps logger text out of stderr. It preserves version/operation/comment and warning-detail extensions.
- `RunReporter.__enter__()` — installs the context-local observer and independently starts the live engine when enabled, sharing its run_id with completion. It does not start a job or add scheduling/locking.
- `RunReporter.update()` — forwards measured progress and suppresses observer failures so reporting cannot alter job behavior.
- `RunReporter.plan()` — records the configured dataset entries and known total after the original input file has been read.
- `RunReporter.begin_item()` — identifies the current dataset occurrence and its create/retention phase; duplicate names retain separate integer IDs.
- `RunReporter.end_item()` — counts one attempted entry and records its success or failure separately. It does not count unattempted/skipped entries as completed.
- `RunReporter.capture_command()` — appends actual child stderr, remembers a failing child's separate code/command, and counts successful real snapshot/destroy commands or explicit dry-run plans. It cannot execute or retry any job command.
- `RunReporter.__exit__()` — restores the observer context, detaches log capture, finalizes measured outcomes (including pending skips), sends retained live last_result and independently attempts the existing completion publisher. Every path returns False, preserving the original exception/process exit. Broker failures are logged without replacing that result.

### `modules/mqtt_reporting.py` functions and methods

- `_now()` — formats an actual UTC timestamp for payloads/heartbeats.
- `_json()` — serializes valid UTF-8, finite JSON in memory for MQTT/stdin; never writes a file.
- `_text()` — decodes captured bytes safely and rejects invented/non-text diagnostic values.
- `capture_command()` — routes a child result or explicit dry-run plan to the current context observer, swallowing instrumentation failures to preserve application semantics.
- `MQTTReporter` — generic, in-memory MQTT live/optional completion engine. Its defaults have no dataset fields.
- `MQTTReporter.__init__()` — loads a TOML [mqtt] table or validated in-memory settings, validates flags/identity/broker/heartbeat, creates per-host/job/config identity and separate live/result/event topics, and starts unknown measurements as null.
- `MQTTReporter._snapshot()` — takes an in-memory JSON-safe copy with actual runtime, heartbeat, job_type/item_unit, item outcome counts, explicit expiry and no estimated transfer measurements.
- `MQTTReporter.snapshot()` — returns that copy under the state lock for concurrent readers.
- `MQTTReporter.start()` — marks the run running and starts only the enabled live heartbeat thread, optionally queueing a start event. It is idempotent and does not execute application work.
- `MQTTReporter.update()` — accepts validated labels, measured nonnegative counters/rates/bytes or null, rejects completed > total, and calculates a percentage only from known completed/total.
- `MQTTReporter.append_stderr()` — maintains the latest 4000 actual stderr characters in memory.
- `MQTTReporter.record_item()` — records success/failure/skipped rows by stable item ID independently of generic attempted/total counters, so duplicate dataset lines and generic file/task jobs work correctly.
- `MQTTReporter.finish()` — validates integer exit/boolean warning, builds the required generic completion contract, marks failure/interruption/incomplete truthfully, stops periodic sending, then performs a bounded final state/retained result/event send. It never forces completed=total or 100 percent.
- `MQTTReporter.close()` — cancels bounded worker activity and joins the heartbeat thread without inventing a final outcome. A lost process is handled by HA expiry.
- `MQTTReporter._discovery()` — creates retained per-device sensor configuration, configurable manufacturer, unique IDs and stable status/last_result attribute role markers. Live sensors expire; last_result does not.
- `MQTTReporter._live_loop()` — throttles updates, sends measured heartbeats, retries discovery periodically, and preserves unsent lifecycle events on a canceled/failed send. Final results are owned by finish() so short runs do not lose them.
- `MQTTReporter._send()` — runs a killable five-second worker with credentials on stdin, never argv, and reaps timed-out/canceled children. Reports delivery failure without leaking raw transport exception text.
- `run_worker_if_requested()` — private source/frozen worker dispatch before normal CLI parsing. It imports bundled Paho, reads stdin JSON, builds verified TLS (including existing CA/client certificate options) and publishes on the specified topics without application work.

### Commands, configuration and templates

- `[python, -B, modules/mqtt_reporting.py, --mqtt-reporting-worker]` or `[frozen executable, --mqtt-reporting-worker]` — internal live transport; no new public job command. Existing completion `--publish` / frozen `--mqtt-publish-worker` workers remain in use.
- `configs/config-example.toml` — the sole loadable complete configuration example, with all 36 options and placeholders. Private config.toml is not shipped; create it by copying this example. Config values and path-resolution rules are unchanged.
- `homeassistant/success-failure-automation.yaml` — supplied completion/Pushover example on the existing project topic; ignores previews before real actions, validates typed agreement, includes diagnostics and bounds messages to Pushover limits. This is an example, not an installed sequence.
- `homeassistant/live-preview-card.yaml` — supplied `type: markdown` / `content: |` card, adapted to the emitted generic item schema and measured ZFS snapshot counters. It discovers a configurable manufacturer, identifies renamed entities by stable roles, shows reasons/stderr/runtime/heartbeat/history, hides null transfer sections and identifies a newer lost run honestly.
- Original HA automation filename — preserved as an alternative; its early guard rejects dry-runs and its actions match the typed, bounded supplied completion example. Enable only one completion notification automation per topic.
- No sample JSON/config/state/cache/log files are introduced. Existing app logs/digest files remain required original behavior.

### Integration regression tests
- `IntegratedReportingTests` — Exercise real coordinator/report adapter with storage and transport isolated.
- `IntegratedReportingTests.settings` — Builds an isolated MQTT config with explicit channels for boundary tests.
- `IntegratedReportingTests.test_typed_completion_matches_process_codes_and_contains_no_dataset_sections` — Verifies typed completion matches process codes and contains no dataset sections without production storage, broker delivery or a Home Assistant installation.
- `IntegratedReportingTests.test_canonical_shared_connection_and_channels_are_independent` — Verifies one canonical connection/topic and independent completion/live enables without production storage, broker delivery or a Home Assistant installation.
- `IntegratedReportingTests.run_observed_job` — Use original operations with deterministic child results and no external work.
- `IntegratedReportingTests.run_observed_job.child` — Returns deterministic child results or actual captured-error fixtures without invoking ZFS/Docker.
- `IntegratedReportingTests.run_observed_job.transport` — Captures emitted live messages in memory instead of publishing them.
- `IntegratedReportingTests.test_fatal_snapshot_keeps_job_failure_and_child_code_stderr_and_unattempted_items` — Verifies fatal snapshot keeps job failure and child code stderr and unattempted items without production storage, broker delivery or a Home Assistant installation.
- `IntegratedReportingTests.test_continued_failure_counts_attempts_separately_and_duplicate_entries` — Verifies continued failure counts attempts separately and duplicate entries without production storage, broker delivery or a Home Assistant installation.
- `IntegratedReportingTests.test_dry_run_previews_capture_real_lists_and_never_create_destroy_or_transfer` — Verifies dry run previews capture real lists and never create destroy or transfer without production storage, broker delivery or a Home Assistant installation.
- `IntegratedReportingTests.test_disabled_and_live_only_and_completion_only_are_independent` — Verifies disabled and live only and completion only are independent without production storage, broker delivery or a Home Assistant installation.
- `IntegratedReportingTests.test_broker_failures_and_interrupts_preserve_process_outcome` — Verifies broker failures and interrupts preserve process outcome without production storage, broker delivery or a Home Assistant installation.
- `IntegratedReportingTests.test_unknown_progress_and_generic_items_have_no_dataset_assumptions` — Verifies unknown progress and generic items have no dataset assumptions without production storage, broker delivery or a Home Assistant installation.
- `IntegratedReportingTests.test_discovery_identity_manufacturer_and_roles_survive_sensor_renaming` — Verifies discovery identity manufacturer and roles survive sensor renaming without production storage, broker delivery or a Home Assistant installation.
- `IntegratedReportingTests.test_live_worker_failure_is_bounded_credentials_off_argv_and_reaped` — Verifies live worker failure is bounded credentials off argv and reaped without production storage, broker delivery or a Home Assistant installation.
- `IntegratedReportingTests.test_live_worker_verified_tls_and_no_retained_completion_or_events` — Verifies live worker verified tls and no retained completion or events without production storage, broker delivery or a Home Assistant installation.
- `IntegratedReportingTests.test_actual_harmless_child_stderr_is_captured_without_fabricated_log_text` — Verifies actual harmless child stderr is captured without fabricated log text without production storage, broker delivery or a Home Assistant installation.
- `IntegratedReportingTests.test_actual_harmless_child_stderr_is_captured_without_fabricated_log_text.child` — Returns deterministic child results or actual captured-error fixtures without invoking ZFS/Docker.
- `IntegratedReportingTests.test_live_heartbeat_and_event_switches_without_completion_reports` — Verifies live heartbeat and event switches without completion reports without production storage, broker delivery or a Home Assistant installation.
- `IntegratedReportingTests.test_live_heartbeat_and_event_switches_without_completion_reports.send` — Collects heartbeat packets and signals when a measured update arrives.
- `HomeAssistantTemplateTests` — Render actual YAML/Jinja using a local HA facade; never access an installation.
- `HomeAssistantTemplateTests.setUp` — Loads optional offline YAML/Jinja tooling and approximates the HA boolean filter; skips only these template tests when tooling is absent.
- `HomeAssistantTemplateTests.setUp.boolean` — Approximates the HA bool filter for offline template rendering.
- `HomeAssistantTemplateTests.test_completion_automation_typed_contract_dry_run_guard_and_pushover_limits` — Verifies completion automation typed contract dry run guard and pushover limits without production storage, broker delivery or a Home Assistant installation.
- `HomeAssistantTemplateTests.render_card` — Renders the actual Markdown card with renamed role-marked sensors and simulated live/history attributes.
- `HomeAssistantTemplateTests.render_card.States` — Local fixture implementing the HA states facade for template checks.
- `HomeAssistantTemplateTests.render_card.States.__call__` — Returns the simulated HA entity state for template lookups.
- `HomeAssistantTemplateTests.render_card.timestamp` — Converts fixture dates to epoch timestamps for heartbeat expiry checks.
- `HomeAssistantTemplateTests.test_card_uses_roles_project_fields_generic_items_and_null_measurements` — Verifies card uses roles project fields generic items and null measurements without production storage, broker delivery or a Home Assistant installation.
- `HomeAssistantTemplateTests.test_card_lost_heartbeat_interrupts_and_retained_history_are_honest` — Verifies card lost heartbeat interrupts and retained history are honest without production storage, broker delivery or a Home Assistant installation.

- `IntegratedReportingTests.test_live_observer_errors_cannot_replace_job_failure_or_block_completion()` — injects live startup/shutdown failures and verifies the original exception and independent completion failure report survive.

- `IntegratedReportingTests.test_main_loads_template_config_and_reports_real_measured_dry_run()` and nested `transport()` — run the real TOML loader/main adapter with new independent flags enabled, fake only storage/transport, and verify matching run IDs, preserved topic, real stderr and one measured dataset outcome.

## Package and example layout

- `modules/__init__.py` — marks the supporting-code directory as a Python package without importing or executing application work.
- Root `SnapBeforeWatchTower.py` imports `modules.mqtt_report` / `modules.mqtt_reporting`, keeping the public command and source log directory unchanged.
- `modules.mqtt_report` uses a relative sibling import for normal package/frozen execution. When the source completion worker runs by absolute file path, it imports its sibling module from the worker directory. This preserves the bounded private worker command and works independently of the caller's working directory without injecting search paths.
- `modules/mqtt_reporting.py` remains self-contained when used as the absolute-path source live worker. Frozen workers still re-execute the root executable with the existing private flags.
- All examples are under `configs/`: config-example.toml, config.example.md and datasets.example.txt. `.gitignore` explicitly unignores the example directory/files despite its broad config* privacy pattern.
- Root `config.toml` and the host-specific dataset lists are intentionally absent; all requested private filenames (including datasets, already absent in the prior release) are ignored. Example dataset/TOML values, job commands, notification behavior, and all other safety settings are unchanged.

## Single completion reporting configuration

- `REMOVED_KEYS` — migration map for duplicate legacy MQTT option names. Validation rejects them before dependency checks or job work, avoiding a second enable or conflicting credentials.
- `RunReporter.completion_payload(exc)` — one shared application completion builder, reused by live finalization and the sole completion send path. Adds actual planned/failed/skipped dataset source records, occurrence IDs and reasons independently of live preview. Generic build_payload/MQTTReporter continue to avoid dataset-specific fields.
- `RunReporter.end_item()` — now remembers failed source records for completion-only jobs and uses actual exception stderr (latest 4000 characters), falling back to the real exception message/type when unavailable. It still counts attempted items separately from skipped outcomes.
- `IntegratedReportingTests.test_removed_duplicate_options_are_rejected_before_job_work()` — checks every removed option and proves an old [mqtt].enabled config exits 2 before operations rather than silently selecting another reporting channel.
- `IntegratedReportingTests.test_single_connection_credentials_are_shared_in_all_canonical_enable_modes()` — tests all four canonical enable combinations and compares the exact broker/port/username/password used by live and completion, including meaningful password whitespace. Verifies standalone JSON without the example wrapper.
- `IntegratedReportingTests.test_dataset_diagnostics_exist_with_completion_only_and_do_not_invent_destinations()` — exercises successful and failing actual coordinators with mocked storage and live disabled; verifies typed result/exit codes, configured sources, real failure reasons, unattempted skips and no fabricated backup destination.
- The root configuration loader passes [mqtt] directly to canonical validation; [report].title remains a mail/friendly fallback outside MQTT configuration. Startup policy logs name MQTT_JSON_Status, SendMQTTOnSuccess and LiveMQTTEnabled explicitly.
