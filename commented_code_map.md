# Commented code map

This map covers every Python class/function and every application or external command in version 0.0.3. It explains both the action and the reason for it. Line numbers are intentionally omitted because they change as the program evolves.

## Program flow

```text
main
  parse CLI -> validate optional MQTT config
  RunReporter context
    run
      choose log folder -> set up loggers -> attach error observer
      require root
      read dataset file
      create: Docker digests -> for each dataset create -> retain -> clean logs
      delete: for each dataset retain -> clean logs
      optional email during run finalization
    publish one optional final MQTT outcome after run finalization
```

The MQTT wrapper observes the existing operation flow. It does not implement, reorder, retry, or roll back ZFS/Docker/email work. Dry-run reaches the wrapper but suppresses its publish action.

## `SnapBeforeWatchTower.py`

### Module value

- `__version__`: one authoritative release number used by `--version` and the MQTT report. This prevents separate displayed versions from drifting.

### Classes and methods

- `CustomLogger(logging.Logger)`: retained original logger subclass. Its constructor creates a DEBUG file handler and INFO console handler for a supplied path. The current CLI does not instantiate it because `setup_logger()` implements the active two-logger design; it remains to preserve original source/API compatibility.
- `CustomLogger.__init__(name, log_filename)`: initializes those two handlers. It exists only as the setup step for the retained class.
- `CommandError(RuntimeError)`: represents a captured external-command failure with command, return code, stdout, and stderr available to callers.
- `CommandError.__init__(cmd, returncode, stdout, stderr)`: builds a readable message and preserves every subprocess result field so the outer error handler can report the failure.

### Logging and output helpers

- `setup_logger(log_folder, log_date)`: creates the active main `.log` logger and separate `.err` logger, plus console handlers. It uses one run timestamp so files belong to the same cleanup group and returns the error path for final empty-file removal.
- `setup_logger._build_logger(name, level, handlers)`: nested factory that disables propagation, clears handlers left by repeat in-process runs, formats new handlers, and attaches them. This prevents doubled messages in tests or embedded use.
- `choose_log_folder(preferred_root_folder, fallback_folder=None)`: retained original root/fallback chooser. The CLI does not call it; `pick_log_folder()` adds a root write test. It stays to preserve the supplied project.
- `pick_log_folder(script_log_folder, tmp_name='SnapBeforeWatchTower')`: sends non-root logging to the temporary directory; for root, prefers `logs/` beside the script and falls back when it cannot write there. Logging must work before the privilege refusal or operational error can be recorded.
- `pick_log_folder._ensure_writable(path)`: creates a directory and writes/removes `.write_test`. This verifies actual write permission rather than trusting metadata.
- `get_newest_files(log_dir, prefix)`: sorts matching paths by modification time and returns the first `.log` and `.err` independently. `MailTo()` uses it to assemble the current-style report attachments.
- `print_separator(logger, error_logger=None)`: writes a visible dashed separator to one logger. It makes long multi-dataset runs easier to scan; when passed an error logger, the separator also enters `.err`.

### Generic command and email helpers

- `run_cmd(cmd, logger=None, error_logger=None, check=True, dry_run=False)`: runs an argument-list command with captured text output, logs nonzero stderr, optionally raises `CommandError`, and returns a synthetic success during dry-run. Centralizing destructive ZFS execution makes its no-execution dry-run boundary explicit.
- `send_mail(subject, body, recipient, attachment_files=None)`: invokes `mail` with the subject and attachments before the recipient, feeds the body through stdin, and returns the process result. Stdin avoids treating body text as command arguments.
- `MailTo(logger, error_logger, recipient, log_folder, subject=..., intro=..., prefix=...)`: finds the newest report files, adds a nonempty `.err` and `.log` to both attachments/body where available, calls `send_mail()`, and logs delivery result. This reuses one format for root, fatal-error, and success notifications.
- `WasMailSent(logger, error_logger, MailExitCode, popenstderr)`: records mail success or the mail program's failure output. It keeps notification diagnostics within the established logger layout.

### Parsing, snapshots, retention, and Docker

- `parse_older_than(value)`: accepts lowercase whole-number `d`, `w`, or `m` durations and converts them to `datetime.timedelta`; months are exactly 30 days. Passing this function to argparse rejects malformed ages before operations begin.
- `create_snapshot(logger, error_logger, dataset, dry_run=False)`: creates `dataset@SnapBeforeWatchTower-Date-<local timestamp>` with `zfs snapshot`; dry-run logs the full planned name. It rethrows ZFS failure to stop later work instead of pretending creation succeeded.
- `extract_snapshot_date(snapshot_name)`: retained original helper that splits after `Date` and parses a timestamp. The active retention implementation performs stricter regex matching itself and does not call this helper.
- `is_older_than(logger, error_logger, snapshot_date_str, older_than)`: retained original age helper. It returns false on invalid dates as a deletion-safe fallback; active retention parses and compares timestamps inside `delete_old_snapshots()`.
- `delete_old_snapshots(logger, error_logger, dataset, older_than, retain_count, dry_run=False)`: lists one dataset's snapshots, accepts only managed current/legacy names, skips invalid timestamps, sorts newest first, protects the requested newest count, and destroys only the remaining items older than the cutoff. The strict matching and invalid-date skip prevent unrelated snapshots from being deleted.
- `delete_old_files(logger, error_logger, log_folder, older_than, retain_count, dry_run=False)`: groups managed `.log`, `.err`, and `.digest` files by embedded timestamp, protects enough newest groups overall, then previews or deletes old eligible groups. Grouping prevents retention from separating related run files.
- `save_docker_image_digests(logger, error_logger, log_folder, log_date, dry_run=False)`: writes successful `docker images --digests` output to the run's `.digest`; removes partial output and logs nonzero Docker results. Dry-run skips Docker so previews do not require its daemon.

### Entry points

- `main()`: defines/parses every CLI option, loads and validates optional MQTT JSON, starts `RunReporter`, then calls `run()`. MQTT validation occurs here so invalid settings stop before logging, dataset reads, or external commands.
- `run(args, reporter)`: contains the supplied application flow: establish logs, attach current-run error capture, enforce root, read/normalize datasets, dispatch create/delete actions, send requested mail, and remove an empty current `.err`. Separating it from parsing lets the MQTT context observe all normal/fatal exits without duplicating operations.
- `if __name__ == '__main__': main()`: launches the CLI only when the file is executed, while keeping imports testable without starting work.

## `mqtt_report.py`

### Configuration and payload functions

- `load_config(path, dry_run=False)`: loads a JSON object, rejects unknown/unsafe values, applies defaults, validates optional plain-string `username`/`password` authentication, requires a username whenever a password is set, resolves certificate paths beside the JSON file, and checks Paho availability for real runs. Dry-run skips only the dependency check because it will not publish.
- `build_payload(config, command, version, exc, errors, run_id)`: produces the Home Assistant-compatible JSON object. It maps normal completion to success/0, exceptions to failure/nonzero, and captured nonfatal error logs to `warning: true`; it bounds error text to keep MQTT messages manageable.
- `publish_report(config, payload)`: passes configuration/payload as JSON over stdin to a child Python worker and enforces the complete configured timeout. Broker settings and credentials stay off the process command line, and detailed child failures are not copied into application logs where secrets could leak.
- `worker()`: imports Paho only for an actual publish, builds optional auth and verified TLS context, then publishes one JSON message with configured QoS and fixed `retain=False`. It is isolated so the parent can terminate DNS, connection, or publish stalls.
- `if __name__ == '__main__'` worker guard: accepts only the internal `--publish` command; direct accidental invocation prints a usage-oriented refusal.

### MQTT classes and methods

- `ErrorCapture(logging.Handler)`: a current-run in-memory error observer used for MQTT `warning`/`stderr`, independent of possibly stale log files.
- `ErrorCapture.__init__()`: configures ERROR level and empty captured text.
- `ErrorCapture.emit(record)`: ignores visual separator-only records, appends meaningful messages, and retains the last 4096 characters so reports stay bounded.
- `RunReporter`: context manager that surrounds one application run and owns its unique report ID.
- `RunReporter.__init__(config, command, version, dry_run=False)`: stores immutable run context and creates the capture handler.
- `RunReporter.__enter__()`: returns the reporter so `run()` can attach its error logger after logger creation.
- `RunReporter.attach(error_logger)`: attaches the capture observer to the active error logger, ensuring only this run's warnings/failures enter the payload.
- `RunReporter.__exit__(exc_type, exc, traceback)`: detaches capture, suppresses dry-run delivery, builds/publishes one report, logs sanitized MQTT failure, and always returns false so it never hides the original exception/SystemExit.

## CLI commands and options

- `python3 SnapBeforeWatchTower.py --help` / `-h`: argparse prints every option and exits before logging or external commands. It is the quickest local capability check.
- `python3 SnapBeforeWatchTower.py --version`: prints `SnapBeforeWatchTower 0.0.3` and exits before logging or external commands.
- `--command create` / `-c create`: capture Docker digests, create one snapshot per listed dataset, apply snapshot retention after each creation, then clean log groups.
- `--command delete` / `-c delete`: apply snapshot retention without creating snapshots or invoking Docker, then clean log groups.
- `--file PATH` / `-f PATH`: select the required dataset list.
- `--older-than AGE` / `-o AGE`: set the strict age cutoff for both snapshots and log groups.
- `--retain-count INTEGER` / `-r INTEGER`: protect the newest matching snapshot count per dataset and newest log groups overall; nonpositive values protect none by count.
- `--send-mail EMAIL` / `-s EMAIL`: enable failure reporting to the recipient.
- `--mail-on-success` / `-mos`: additionally enable a success report when a recipient was supplied.
- `--dry-run` / `-d`: preview ZFS mutations and old-log deletions; Docker and MQTT are skipped, while logging, ZFS listing, and requested mail still occur.
- `--mqtt-config PATH`: validate and enable one final MQTT outcome report for a real run.

## External commands

- `zfs snapshot DATASET@NAME`: creates the managed snapshot. It is called directly by `create_snapshot()` and never during dry-run.
- `zfs list -H -t snapshot -o name DATASET`: lists snapshot names for one dataset without headings. Retention needs the full names to apply its strict managed-name filter; it also runs during dry-run to build a realistic deletion plan.
- `zfs destroy FULL_SNAPSHOT_NAME`: deletes only a name selected by `delete_old_snapshots()`; `run_cmd()` suppresses it during dry-run.
- `docker images --digests`: records repository/tag/image ID/digest information before real create-mode snapshots. Its nonzero result is a warning, while inability to start the executable is fatal.
- `mail -s SUBJECT [--attach FILE ...] RECIPIENT`: sends requested reports. The body is piped through stdin and file arguments are separate subprocess arguments; no shell evaluates them.
- `python mqtt_report.py --publish`: internal child worker for one MQTT publish. JSON configuration arrives over stdin; the parent kills a timeout and sanitizes failure details.
- `python -m pip install -r requirements-mqtt.txt`: documented operator setup command that installs the optional Paho dependency. The application never runs pip itself.

## Packaged configuration/data files

- `mqtt.example.json`: all supported MQTT keys, including direct `username` and plain-string `password` fields. It is not loaded unless copied/selected with `--mqtt-config`.
- `requirements-mqtt.txt`: optional Paho version range used only for MQTT publishing.
- `datasets.example.txt`: small generic dataset list template.
- `snaplist` and `full-snaplist`: original installation-specific dataset lists, preserved byte for byte.
- `.gitignore`: excludes the operational `mqtt.json`, runtime logs, Python bytecode/cache directories, test cache, and build artifacts so generated files are not accidentally committed.

## Tests

All tests mock ZFS, Docker, mail, MQTT, and privilege effects; they do not mutate real services.

### `tests/test_app.py`

- `temporary_directory()`: makes/removes disposable files under the chosen temp root with portable permissions, because retention tests must test real file grouping/deletion.
- `BehaviorTests.setUp()`: provides isolated mock loggers.
- `test_duration_units_and_invalid_input()`: protects exact age parsing and malformed-input rejection.
- `test_retention_preserves_newest_and_ignores_unmanaged_or_invalid_dates()`: protects the name filter, legacy compatibility, invalid-date skip, newest floor, and destroy order.
- `test_retention_preserves_recent_snapshot_without_count_floor()`: proves age still protects recent snapshots when the count floor is zero.
- `test_nonpositive_count_disables_floor()`: documents and checks the hazardous zero/negative behavior.
- `test_dry_run_lists_but_never_creates_destroys_or_captures_docker()`: verifies the core dry-run command boundary.
- `test_list_failure_prevents_destroy()`: proves retention does not destroy after failed discovery.
- `test_create_failure_propagates()`: proves snapshot creation errors stop the run.
- `test_log_groups_count_age_and_dry_run()`: checks grouped retention, unrelated-file preservation, and preview versus real deletion.
- `test_docker_nonzero_is_logged_and_returns_none()`: captures the existing nonfatal Docker behavior and absence of partial digest files.
- `test_nonroot_refuses_before_dataset_or_external_commands()`: protects the privilege safety gate.
- `test_main_create_order_and_docker_failure_continuation()`: protects dataset whitespace/blank handling and supplied create/retention/cleanup ordering.
- `test_mail_options_precede_recipient()`: protects the argument-list layout sent to `mail`.
- `CLITests.run_cli()`: invokes parser-only subprocesses with bytecode disabled.
- `test_help_and_version()`: verifies both informational paths and all documented options.
- `test_invalid_arguments_stop_before_operations()`: verifies argparse's status 2 and clean error messages.

### `tests/test_mqtt.py`

- `MQTTTests.setUp()` and `read_config()`: build safe defaults and disposable JSON for validation tests.
- `test_config_defaults_and_tls_port()`: checks optional defaults and automatic TLS port.
- `test_invalid_config_stops_early()`: checks wrong types/ranges, wildcard topics, unsupported legacy keys, invalid password types, incomplete auth/certificate settings, and unknown keys.
- `test_password_and_dependency_validation()`: checks direct plain-string password loading, the password-requires-username rule, rejection of the old `password_env` key, and Paho requirements only for real MQTT runs.
- `test_payload_success_warning_and_failure_contract()`: validates every automation-consumed field for success, warning, exception, root refusal, and interruption.
- `test_capture_is_bounded_and_ignores_separators()`: protects useful and bounded `stderr` reporting.
- `test_worker_publish_uses_json_auth_tls_and_no_retain()`: checks Paho inputs, direct JSON password authentication, TLS context, JSON, and fixed non-retained delivery.
- `test_publisher_timeout_stdin_and_failure()`: checks timeout, stdin transfer, command-line privacy, and sanitized failures.
- `test_disabled_and_dry_run_never_publish()`: ensures opt-in and preview modes cannot emit an MQTT report.
- `test_reporter_publishes_once_and_does_not_mask_failure()`: protects single final failure delivery, capture cleanup, and exception propagation.
- `test_publish_errors_preserve_original_outcome()`: proves MQTT failure/timeout cannot alter a completed job or expose exception text.
- `test_main_integration_final_success_and_failure()`: checks main/report lifecycle for normal, exception, and SystemExit outcomes.
