# SnapBeforeWatchTower

SnapBeforeWatchTower creates ZFS snapshots for datasets listed in a text file, records Docker image digests during `create` runs, and removes old matching snapshots and log groups according to an age/count retention policy. Configuration is supplied through one TOML file.

The application does **not** start Watchtower, update containers, restore data, stop services, or create application-consistent snapshots.

## Requirements

- Linux with Python **3.11 or newer**. Python 3.11 is required because TOML is read with the standard-library `tomllib` module.
- ZFS tools available in `PATH` and permission to operate on the configured datasets.
- Root privileges for normal operation, including dry-run.
- Docker CLI/daemon for image-digest capture during a real `create` run. Docker is not invoked for `delete` or dry-run.
- Optional mail notifications require a local `mail` program that supports `-s` and `--attach`.
- Optional MQTT reporting in **source mode** requires `paho-mqtt` from `requirements-mqtt.txt` whenever `[mqtt].enabled = true`, including dry-run because failure reports may still need to publish. The standalone PyInstaller executable bundles Paho and does not need a separate Python/Paho install on the target host.

## Setup

Copy the example configuration and edit it:

```bash
cp config-example.toml config.toml
cp datasets.example.txt datasets
nano config.toml
nano datasets
```

`config.toml` is ignored by `.gitignore` because it can contain an MQTT password.

The supplied configuration example starts with `dry_run = true`, mail disabled, and MQTT disabled. The supplied `datasets.example.txt` is a harmless format example and should be copied/edited into the `dataset_file` named by your TOML. These defaults are intentional so a copied example does not immediately destroy snapshots or send notifications.

## Standalone PyInstaller build

A reproducible PyInstaller build is included. Build dependencies are isolated from the runtime/source dependency file:

```bash
./build-pyinstaller.sh
```

The script creates a private `.venv-build`, installs the pinned packages from `requirements-build.txt`, removes previous `build/` and `dist/` outputs, then builds and verifies the executable with `--help` and `--version`. The final executable path is:

```text
dist/SnapBeforeWatchTower
```

`SnapBeforeWatchTower.spec` explicitly collects all `paho` submodules so MQTT support is present even though Paho is imported dynamically. The executable also contains the Python interpreter and standard-library modules used by the application. It still relies on normal host tools such as `zfs`, `docker`, and `mail` because those are external system commands, not Python modules.

Run the standalone build exactly like the source version:

```bash
./dist/SnapBeforeWatchTower --help
./dist/SnapBeforeWatchTower --version
sudo ./dist/SnapBeforeWatchTower -c config.toml
```

PyInstaller output is platform/architecture specific. Build on the Linux architecture on which you intend to run the executable. In frozen mode the MQTT timeout worker safely re-executes the same `dist/SnapBeforeWatchTower` binary using a private internal switch while keeping broker configuration and credentials on stdin rather than command-line arguments. Persistent root-run logs are written to `dist/logs/`; non-root execution retains the existing `/tmp/SnapBeforeWatchTower` fallback.

## Command-line interface

Normal operation uses one TOML configuration file:

```bash
sudo python3 SnapBeforeWatchTower.py -c config.toml
```

The public command-line flags are:

| Flag | Meaning |
| --- | --- |
| `-c CONFIG` | Required for normal operation. Load the TOML configuration file from `CONFIG`. |
| `-h`, `--help` | Show the complete command-line help and exit without loading configuration or running ZFS/Docker/mail/MQTT operations. |
| `--version` | Show the SnapBeforeWatchTower application version and exit without loading configuration or running operations. |

Examples:

```bash
python3 SnapBeforeWatchTower.py --help
python3 SnapBeforeWatchTower.py --version
sudo python3 SnapBeforeWatchTower.py -c config.toml
```

There are no separate command, dataset, retention, mail, MQTT, or dry-run CLI flags. Those operational settings remain in TOML so one file describes the whole scheduled job.

Relative paths in the TOML file are resolved relative to the TOML file itself. This makes cron/systemd execution independent of the shell's working directory.

## Configuration

The complete commented configuration is in `config-example.toml`. Every supported setting is shown there.

`config.example.md` is a supplemental human-readable reference for the same current TOML settings and public `-c CONFIG`, `-h`/`--help`, and `--version` flags; it is not loaded by the application.

### `[application]`

```toml
[application]
command = "create"
dataset_file = "datasets"
older_than = "7d"
retain_count = 10
dry_run = true
continue_on_missing_dataset = true
continue_on_other_failures = true
```

`command` must be `"create"` or `"delete"`. `create` captures Docker image digests, creates one managed snapshot per dataset, immediately applies snapshot retention to that dataset, and then cleans old log groups. `delete` only applies snapshot retention and log cleanup; it does not create snapshots or invoke Docker.

`dataset_file` points to the UTF-8 dataset-list file. Each non-empty line is treated as one complete ZFS dataset name. Blank lines are ignored. Dataset lines are not deduplicated and there is no comment syntax. A relative path is resolved relative to the TOML file. Missing-dataset and other per-dataset ZFS continuation behavior is controlled by the two settings below; either kind of recorded failure still makes the overall run fail.

`older_than` controls the age cutoff for managed snapshots and log groups. It must be a nonnegative integer followed by `d`, `w`, or `m`: for example `7d`, `2w`, or `1m`. Months are treated as 30 days. Deletion uses a strict older-than comparison.

`retain_count` protects at least that many newest matching snapshots per dataset and newest log timestamp groups. Zero or a negative value disables the count floor; the age cutoff still applies.

`dry_run = true` previews ZFS snapshot creation/destruction and old-log deletion. Dry-run still lists existing ZFS snapshots and creates run logs; Docker digest collection is skipped. Mail and MQTT reporting follow the same success/failure policy as a real run: when a channel is enabled, failures are reported regardless of its `on_success` value, while successful dry-runs are reported only when that channel has `on_success = true`.

`continue_on_missing_dataset = true` means that when ZFS explicitly reports a configured dataset as nonexistent, the script records that dataset as failed and moves to the next configured dataset. `false` stops dataset processing immediately. In both cases the run result is failure and enabled mail/MQTT reports that failure. The setting defaults to `true` when omitted.

`continue_on_other_failures = true` means that any other checked per-dataset `zfs list` or `zfs destroy` command failure is recorded and processing moves to the next configured dataset. `false` stops immediately on that command failure. This setting does **not** make snapshot-create failures, configuration errors, root failures, missing/unreadable input files, Docker failures, log-file failures, or other global failures recoverable. It defaults to `true` when omitted.

### `[mail]` — optional

```toml
[mail]
enabled = false
recipient = "you@example.com"
on_success = false
```

When `enabled = false`, mail is disabled regardless of the other mail values.

When `enabled = true`, `recipient` must be non-empty. Failure mail is always enabled, including during dry-run. `on_success = true` additionally sends a success report for both real and dry-run executions; `on_success = false` suppresses only success mail and never suppresses failure mail. Dry-run mail subjects are explicitly marked `DRY-RUN`. A run that records missing datasets or continuable per-dataset `zfs list`/`zfs destroy` failures still sends failure mail after remaining configured datasets are processed; missing-only failures retain the dedicated missing-dataset subject, while other continued command failures use a dataset-command-failure subject. The report uses the newest `.log` and newest non-empty `.err` files and attaches them where available. Mail delivery failure is logged but does not replace the snapshot job exit result. `MailTo()` now records whether the local `mail` command returned success; a failed success-mail attempt is written explicitly to the error log so it cannot be mistaken for an `on_success` suppression.

### `[mqtt]` — optional

When running from Python source, install the optional dependency with the same interpreter used to run the application:

```bash
python3 -m pip install -r requirements-mqtt.txt
```

Configuration example:

```toml
[mqtt]
enabled = false
on_success = false
host = "mqtt.example.local"
port = 1883
topic = "homeassistant/SnapBeforeWatchTower/Zotac-RI531/status"
title = "Zotac RI531 - SnapBeforeWatchTower"
username = "your-mqtt-user"
password = "<String>"
qos = 0
tls = false
ca_file = ""
cert_file = ""
key_file = ""
timeout = 15
```

When `enabled = false`, MQTT reporting is disabled. In source mode `paho-mqtt` is then not required; the standalone executable already contains it. Unsupported MQTT keys are still rejected.

When `enabled = true`, MQTT failure reports are always attempted, including during dry-run. `on_success = true` additionally publishes success reports for both real and dry-run executions; `on_success = false` suppresses only successful MQTT reports. Because a dry-run can still fail and must then report that failure, `paho-mqtt` is required whenever MQTT is enabled. Before a publish attempt the run log now says that the final MQTT report is being attempted; success is logged as published. If the bounded worker fails, the parent logs a credential-safe exception class such as `ConnectionRefusedError` instead of silently reducing the failure to a generic no-message symptom.

When `enabled = true`, `host` and `topic` are required non-empty strings. `topic` cannot contain `+` or `#`. `port` must be 1–65535, `qos` must be 0, 1, or 2, and `timeout` must be 1–120 seconds. Reports are always published with `retain = false`.

`username` and `password` are plain TOML strings. An empty string disables that optional value. A non-empty password requires a non-empty username. Because the password is stored directly in the TOML file, protect the operational config with restrictive filesystem permissions and do not commit or share it.

`tls = true` enables certificate and hostname verification. `ca_file` is optional; an empty string uses system trust. `cert_file` and `key_file` must either both be empty or both point to files. Relative certificate/key paths are resolved relative to the TOML file.

The final MQTT payload contains `status`, `title`, `name`, `job`, `exit_code`, `warning`, `error`, `stderr`, `command`, `version`, `run_id`, `finished_at`, and `dry_run`. `dry_run` is `true` for preview runs and `false` for real runs. Exit code 0 reports `status: success`; nonzero outcomes report `status: failure`. Missing datasets and continued per-dataset `zfs list`/`zfs destroy` failures do not introduce new status values: after any configured continuation, the final report is still `status: failure` with `exit_code: 1`. Missing-only runs identify the missing dataset name(s) and the `dataset does not exist` reason in `error`; continued list/destroy failures identify the affected dataset(s), while detailed current-run command errors remain available in bounded `stderr`. This keeps the supplied Home Assistant success/failure branching unchanged. Nonfatal messages captured by the error logger can produce `warning: true` while the overall status remains success. Error fields are bounded to 4096 characters.

MQTT runs in a separate child process so its total operation can be timed out. Broker credentials are passed to that child over stdin rather than on its process command line. MQTT publish failures are sanitized in application logs and do not replace the underlying snapshot operation result.

### Notification policy

Mail and MQTT use the same result-selection rules independently:

| Channel state | Successful real run | Successful dry-run | Failed real run | Failed dry-run |
| --- | --- | --- | --- | --- |
| `enabled = false` | No report | No report | No report | No report |
| `enabled = true`, `on_success = false` | No success report | No success report | Failure report | Failure report |
| `enabled = true`, `on_success = true` | Success report | Success report | Failure report | Failure report |

`[mail].on_success` controls only mail success reports. `[mqtt].on_success` controls only MQTT success reports. One channel can therefore report success while the other remains failure-only.

### Notification delivery diagnostics

Every run writes a notification-policy line showing `dry_run`, whether mail/MQTT are enabled, and both success-report switches. On a successful dry-run with both channels enabled and both `on_success = true`, the log should then contain a mail success-report attempt and an MQTT success-report publish attempt.

For mail, `Mail was sent successfully` means the local `mail` command returned exit code 0. A nonzero mail exit code is logged with its stderr and a clear `Success mail report was attempted...delivery failure` message. The notification transport failure does not change a successful ZFS/dry-run result.

For MQTT, `MQTT final success report published [DRY-RUN]` confirms that the Paho worker completed successfully. If publishing fails, the log includes a safe worker exception class when available (for example `ConnectionRefusedError`) while never printing the MQTT password or request JSON. A timeout is logged separately as delivery unconfirmed.

## Dataset file

Example:

```text
tank/docker
tank/appdata
```

The release includes `datasets.example.txt` as the dataset-list format example. Copy it to the filename configured by `dataset_file` (the default example uses `datasets`) and replace the example dataset names before use. Dataset names are passed literally to ZFS after surrounding whitespace is stripped.

## Snapshot naming and retention

New snapshots are named:

```text
DATASET@SnapBeforeWatchTower-Date-YYYY-MM-DD_HH_MM_SS
```

Only snapshots matching the SnapBeforeWatchTower naming pattern participate in managed retention. Snapshots are sorted by the timestamp embedded in the name. The newest `retain_count` are protected, then older unprotected snapshots are destroyed only when their embedded timestamp is older than the configured cutoff.

Snapshot listing is non-recursive for each configured dataset. A malformed managed timestamp is skipped rather than destroyed. If ZFS explicitly says a configured dataset does not exist, `continue_on_missing_dataset` decides whether the script records the failure and advances to the next dataset (`true`) or stops immediately (`false`). Any other checked `zfs list` or `zfs destroy` failure is controlled separately by `continue_on_other_failures`; when true, that dataset is recorded as failed and processing advances to the next configured dataset, while false stops immediately. Recorded continuable failures still make the final run fail after remaining dataset processing and normal log cleanup. Snapshot-create failures that are not the explicit missing-dataset case remain immediately fatal regardless of `continue_on_other_failures`.

Each dataset is processed separately and a new timestamp is generated for each snapshot. A later failure does not roll back earlier successful snapshots or deletions.

## Log and digest files

Logs are normally written under `./logs` beside the script when running as root. If that location is not writable, or when the script is run without root, the application uses a temporary fallback directory.

A run can create:

```text
SnapBeforeWatchTower-Date-YYYY-MM-DD_HH_MM_SS.log
SnapBeforeWatchTower-Date-YYYY-MM-DD_HH_MM_SS.err
SnapBeforeWatchTower-Date-YYYY-MM-DD_HH_MM_SS.digest
```

An empty current `.err` is removed at the end of the run. Managed old log/digest files are grouped by timestamp and use the same `older_than`/`retain_count` policy as snapshots.

During a real `create` run, Docker digests are collected with:

```bash
docker images --digests
```

A Docker digest failure is logged and the snapshot run continues. No empty/partial digest file is intentionally kept after a failed capture.

## External commands used

For real operations, SnapBeforeWatchTower can invoke:

```text
zfs snapshot DATASET@SNAPSHOT
zfs list -H -t snapshot -o name DATASET
zfs destroy SNAPSHOT

docker images --digests

mail -s SUBJECT [--attach FILE ...] RECIPIENT
```

The application does not use shell interpolation for these commands; arguments are passed as separate subprocess arguments.

## Home Assistant MQTT automation

`homeassistant/SnapBeforeWatchtower-mqtt-persistent-notification.yaml` contains a compatible Home Assistant automation. Its MQTT trigger topic must exactly match `[mqtt].topic` in your TOML configuration. The automation reads the payload `dry_run` flag and displays `DRY-RUN` or `LIVE` in success and failure notifications. Missing datasets and continued list/destroy failures still use `status: failure`, and the automation includes the payload `error` and `stderr` fields so the failure reason remains visible.

## Safety

This program performs destructive ZFS snapshot deletion and log deletion. Review `SAFETY.md`, start with `dry_run = true`, verify the resulting plan/logs, and keep independent backups before using real deletion.

## ⚠️ Disclaimer / Liability

**Use this script at your own risk.**

The author takes **no responsibility or liability** for any data loss, service disruption, misconfiguration, service outage, missed backups, credential exposure, or other damage that may occur from using this script.

Before running it in production, you **must**:

- Read the entire source code
- Understand exactly what it does (and what it does *not* do)
- Review and adapt it to your own environment
- Test it carefully in a non‑production setup

By using this script, **you accept full responsibility** for its effects.

⚠️ AI-assisted / vibe-coded experimental software. Use at your own risk.

## Disclaimer

This project is AI-assisted / vibe-coded software created as a hobby project. It has not been professionally audited and may contain bugs, unsafe behavior, data-loss issues, security problems, or incorrect assumptions.

You are responsible for reviewing the code, testing it in a safe environment, making backups, and understanding what it does before using it on real data. The author is not responsible for damage, data loss, broken systems, security issues, or other problems caused by using this software.

---
