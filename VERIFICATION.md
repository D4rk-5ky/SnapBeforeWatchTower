# Verification — SnapBeforeWatchTower 0.0.20

Date: 2026-10-27. Version 0.0.19 → 0.0.20, exactly one patch step.

## Current configuration and payload behavior

- MQTT_JSON_Status is the only completion-report enable. LiveMQTTEnabled independently enables live preview, including live-only operation. SendMQTTOnSuccess affects successful completion messages only; enabled completion always attempts failure messages.
- There is one broker_address/broker_port/mqtt_username/mqtt_password/MQTTTLS/certificate configuration shared by both channels. Remove old duplicate MQTT enabled/on_success/host/port/topic/username/password/tls/title keys; the validator provides replacement guidance and exits 2 before work. The [mail] table and other non-MQTT sections remain unchanged.
- The example now has 22 canonical MQTT options, 36 total. All retained option values and the original completion topic match 0.0.19. Existing private config files containing duplicate options need updating from configs/config-example.toml; no silent alias fallback remains.
- Each completion publishes one standalone JSON object with matching friendly name/title, stable job=SnapBeforeWatchTower, success/failure status, boolean success/warning/dry_run, integer actual process exit_code, real error/stderr, run/time/host metadata. The demonstration wrapper and Syncerate job/destination/exit values are not copied.
- This dataset-based app supplies planned_datasets, failed_datasets and skipped_datasets from actual configured entries/outcomes, even with live disabled. Sources and occurrence IDs are real; reasons use actual stderr/exception details and there is no invented backup destination. Generic build_payload/MQTTReporter remain free of dataset sections.
- Uncaught snapshot/command exceptions still make the app exit 1; distinct failing child codes remain child_exit_code. SystemExit and KeyboardInterrupt retain their outcomes. Reporting failures never replace the job failure. Current-item finalization is shared before live/completion output, preventing incomplete diagnostics in completion-only mode.
- The HA automation/card are byte-identical to 0.0.19 and compatible with the completion/live schemas. The card still uses manufacturer/role discovery, generic item counts and snapshot metrics. Dry-runs are ignored before real completion sequences/notifications.

## Checks completed

| Check | Result |
| --- | --- |
| Regression | **90 tests pass, no skips**, including all prior storage/safety/CLI/transport/HA tests and three new canonical-schema/credential/dataset diagnostic cases. |
| Independent switches/shared credentials | All four completion/live combinations tested using canonical raw config; exact host/port/user/password supplied to both transports agree, including meaningful password whitespace. No second enable or separate credential set is required. |
| Removed duplicate settings | Every removed option is rejected, even if disabled. A real main/config load with old enabled exits 2 before operations. Canonical public option list has no duplicate names. |
| Completion-only datasets | Mocked actual coordinator success/failure with live disabled supplies configured sources, true failure reasons, unattempted skips and actual process/child codes without destinations or example wrapper. |
| JSON and diagnostics | Required field types and status/success/exit agreement pass. Existing real harmless Python child still verifies actual 4000-character stderr capture. Generic non-dataset report tests pass; no filesystem JSON state/config/cache/logs are introduced. |
| HA templates | Offline YAML/Jinja tests pass for typed success/failure/malformed reports, Pushover limits, dry-run ordering, manufacturer filtering, renamed roles, ZFS/generic item labels, null transfers, heartbeat loss and retained history. No HA installation or notification is touched. |
| Job source audit | Every storage/safety helper body unchanged. Run coordinator AST matches 0.0.19 after removing notification-policy log assignments/message only. Loader changes are confined to canonical MQTT parsing and report-title forwarding; all non-MQTT config values remain identical. |
| Documentation/config | 36-key TOML and Markdown example values agree. Both histories identical; prior entries and disclaimer sections unchanged. Code map names all 188 class/function/method definitions. Layout/private-file ignore rules preserved. |
| Compile/build | Six Python files plus the spec compile in memory. Bash syntax and source/build-helper help/version pass. Pinned PyInstaller 6.22.3/Paho 2.1.0 executable rebuild succeeds on Python 3.14.4, Linux x86_64/glibc 2.43. |
| Worker/CLI | Source and executable help/version/parser checks pass, including from another cwd. Both direct source workers and both frozen worker entry points import and fail safely on empty requests before publishing. Version output is 0.0.20. |
| Full clean archive | All 27 previous files/modes retained, no additions/removals. Verify CRC, safe paths, exact bytes, caches/private-file exclusions and 26 checksum entries. Fresh extraction repeats all 90 tests, CLI/worker checks and checksum validation. |

## Limits

No real ZFS snapshot/list/destroy, Docker capture, mail delivery, MQTT broker,
authentication/TLS exchange, Home Assistant/Pushover delivery, scheduling or
production deployment was tested. Storage and transport are isolated in tests;
the stderr fixture uses only a harmless Python child. No destructive job, live
notification or HA installation change was performed. Offline HA helpers are
approximations; broker and target HA behavior still need non-production testing.

A matching local pinned build toolchain was reused; fresh dependency installation
was not rerun. Other Python versions, architectures/distributions and older glibc
remain untested. All cache/build/test scratch output is outside the release ZIP.
Earlier archives remain untouched. Config migration concerns only the duplicate
MQTT options explicitly removed here; command, job exit, storage/safety and
scheduling behavior remain preserved.
