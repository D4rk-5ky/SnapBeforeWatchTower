# SnapBeforeWatchTower

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

SnapBeforeWatchTower **0.0.20** creates ZFS snapshots for datasets listed in a text file, records Docker image digests during `create` runs, and removes old matching snapshots and log groups according to an age/count retention policy. Configuration is supplied through one TOML file.

The application does **not** start Watchtower, update containers, restore data, stop services, or create application-consistent snapshots.

## Requirements

- Linux with Python **3.11 or newer**. Python 3.11 is required because TOML is read with the standard-library `tomllib` module.
- ZFS tools available in `PATH` and permission to operate on the configured datasets.
- Root privileges for normal operation, including dry-run.
- Docker CLI/daemon for image-digest capture during a real `create` run. Docker is not invoked for `delete` or dry-run.
- Optional mail notifications require a local `mail` program that supports `-s` and `--attach`.
- Optional MQTT reporting in **source mode** requires `paho-mqtt` from `requirements-mqtt.txt` whenever `[mqtt].MQTT_JSON_Status = true` or `[mqtt].LiveMQTTEnabled = true`, including dry-run because failure reports may still need to publish. The standalone PyInstaller executable bundles Paho and does not need a separate Python/Paho install on the target host.

## Setup

Copy the example configuration and edit it:

```bash
cp configs/config-example.toml config.toml
cp configs/datasets.example.txt datasets
nano config.toml
nano datasets
chmod 600 config.toml
```

`cp` copies the examples, `nano` opens them for editing, and `chmod 600` restricts config access to its owner. Run setup from the project directory.

`config.toml` is ignored by `.gitignore` because it can contain an MQTT password.

The supplied configuration example starts with `dry_run = true`, mail disabled, and MQTT disabled. The supplied `configs/datasets.example.txt` is a harmless format example and should be copied/edited into the `dataset_file` named by your TOML. These defaults are intentional so a copied example does not immediately destroy snapshots or send notifications.

Supporting Python modules are packaged in `modules/`; `SnapBeforeWatchTower.py`
remains the root CLI entry point. Configuration and dataset examples live in
`configs/`. Copy examples into private runtime files as shown above; relative
paths inside TOML are still resolved against the copied TOML file's directory.

## Standalone PyInstaller build

A pinned PyInstaller build recipe is included. Inspect its options and source version before building:

```bash
./build-pyinstaller.sh --help
./build-pyinstaller.sh --version
```

`-h`/`--help` explains the build requirements, replaced directories, and output checks. `--version` reads the application source version without importing it. Use either option alone; both exit before any build cleanup, installation, or directory creation. Unknown arguments and combinations exit 2 before build work. With no arguments the script performs the build. Build dependencies are isolated from the runtime/source dependency file:

```bash
./build-pyinstaller.sh
```

The script creates one private, gitignored `.build-pyinstaller/` workspace, with the build virtual environment, pip cache, PyInstaller work files, and PyInstaller config/cache kept underneath it. It also removes the legacy project-level `build/` and `.venv-build/` locations from older releases. Before building, it cleans every generated/stale entry from `dist/` while keeping the tracked `dist/README.md`. After the build it verifies the executable with `--help` and `--version` and fails unless `dist/` contains exactly the executable and README. The final executable path is:

```text
dist/SnapBeforeWatchTower
```

`SnapBeforeWatchTower.spec` explicitly collects all `paho` submodules so MQTT support is present even though Paho is imported dynamically. The executable also contains the Python interpreter and standard-library modules used by the application. It still relies on normal host tools such as `zfs`, `docker`, and `mail` because those are external system commands, not Python modules. All generated build state is isolated under the gitignored `.build-pyinstaller/` directory; it is not part of the release output. The generated `dist/` directory is intentionally restricted to **exactly two files**: `dist/SnapBeforeWatchTower` and the tracked `dist/README.md`. No dependency directory, log directory, cache, work directory, hidden file, or other artifact is allowed there.

Run the standalone build exactly like the source version:

```bash
./dist/SnapBeforeWatchTower --help
./dist/SnapBeforeWatchTower --version
sudo ./dist/SnapBeforeWatchTower -c config.toml
```

PyInstaller output is platform/architecture specific. See `dist/README.md` for the included binary’s build environment and compatibility limits. Build on the Linux architecture on which you intend to run the executable. In frozen mode the MQTT timeout worker safely re-executes the same `dist/SnapBeforeWatchTower` binary using a private internal switch while keeping broker configuration and credentials on stdin rather than command-line arguments. When the executable is run from a project `dist/` directory, persistent root-run logs are written to the project-level `logs/` directory so `dist/` stays clean; if the executable is deployed somewhere else, logs use a `logs/` directory beside that deployed executable. Non-root runs use the same fixed log location before refusing operation; there is no temporary fallback.

## Command-line interface

Normal operation uses one TOML configuration file:

```bash
sudo python3 SnapBeforeWatchTower.py -c config.toml
```

The public command-line flags are:

| Flag | Meaning |
| --- | --- |
| `-c CONFIG` | Required for normal operation. Load all settings from this TOML file. A relative `CONFIG` path uses the current working directory. |
| `-h`, `--help` | Show the complete command-line help and exit without loading configuration or running ZFS/Docker/mail/MQTT operations. |
| `--version` | Show the SnapBeforeWatchTower application version and exit without loading configuration or running operations. |

Examples:

```bash
python3 SnapBeforeWatchTower.py --help
python3 SnapBeforeWatchTower.py --version
sudo python3 SnapBeforeWatchTower.py -c config.toml
```

There are no separate command, dataset, retention, mail, MQTT, or dry-run CLI flags. Those operational settings remain in TOML so one file describes the whole scheduled job.

Relative dataset and TLS file paths in the TOML file are resolved relative to the TOML file itself. `dataset_file` also expands `~`; TLS paths do not. This makes cron/systemd execution independent of the shell's working directory.

## Configuration

The complete commented configuration is in `configs/config-example.toml`. Every supported setting is shown there.

`configs/config.example.md` is a supplemental human-readable reference for the same current TOML settings and public `-c CONFIG`, `-h`/`--help`, and `--version` flags; it is not loaded by the application.

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

`older_than` controls the age cutoff for managed snapshots and log groups. It must be a nonnegative integer followed by `d`, `w`, or `m`: for example `7d`, `2w`, or `1m`. Months are treated as 30 days. Deletion uses a strict older-than comparison. The duration and its cutoff must fit Python’s date range (no earlier than year 1); an out-of-range age is rejected during configuration validation before operations.

`retain_count` protects at least that many newest matching snapshots per dataset and newest log timestamp groups. Zero or a negative value disables the count floor; the age cutoff still applies.

`dry_run = true` previews ZFS snapshot creation/destruction and old-log deletion. Dry-run still lists existing ZFS snapshots and creates run logs; Docker digest collection is skipped. Mail and MQTT reporting follow the same success/failure policy as a real run: when a channel is enabled, failures are reported when completion is enabled, while successful reports require `[mail].on_success = true` for mail or `[mqtt].SendMQTTOnSuccess = true` for MQTT. Live preview is controlled independently by `[mqtt].LiveMQTTEnabled`.

`continue_on_missing_dataset = true` means that when ZFS explicitly reports a configured dataset as nonexistent, the script records that dataset as failed and moves to the next configured dataset. `false` stops dataset processing immediately. In both cases the run result is failure and enabled mail/MQTT reports that failure. The setting defaults to `true` when omitted.

`continue_on_other_failures = true` means that any other checked per-dataset `zfs list` or `zfs destroy` command failure is recorded and processing moves to the next configured dataset. `false` stops immediately on that command failure. This setting does **not** make snapshot-create failures, configuration errors, root failures, missing/unreadable input files, Docker failures, log-file failures, or other global failures recoverable. It defaults to `true` when omitted.

### `[logging]` and `[report]`

`[logging].prefix` selects log/digest filenames; empty uses the application
basename. It must be a single safe filename component, as described in the
configuration comments. Snapshot naming is unaffected.

`[report].name` is the friendly run name in email and both completion JSON
`name`/`title`. MQTT `job` stays `SnapBeforeWatchTower`. An omitted run name uses
`LiveBackupName`, then the report title/project fallback for MQTT. Email keeps its
existing name/title/basename fallback. `[report].comment` preserves TOML-decoded
newlines in email and completion JSON and never changes subjects.

### `[mail]` — optional

```toml
[mail]
enabled = false
recipient = "you@example.com"
on_success = false
```

When `enabled = false`, mail is disabled regardless of the other mail values.

When `enabled = true`, `recipient` must be non-empty. Failure mail is always enabled, including during dry-run. `on_success = true` additionally sends a success report for both real and dry-run executions; `on_success = false` suppresses only success mail and never suppresses failure mail. Dry-run mail subjects are explicitly marked `DRY-RUN`. A run that records missing datasets or continuable per-dataset `zfs list`/`zfs destroy` failures still sends failure mail after remaining configured datasets are processed; missing-only failures retain the dedicated missing-dataset subject, while other continued command failures use a dataset-command-failure subject. The report selects the newest `.log` and newest `.err` independently by modification time; the selected `.err` is included only when non-empty. Every report path uses the configured prefix and run name, with the comment immediately below the name in the body. Without a name the heading falls back to the configured title/app basename; the subject retains its status wording. Mail delivery failure is logged but does not replace the snapshot job exit result. The mail report records whether the local `mail` command returned success; a failed success-mail attempt is written explicitly to the error log so it cannot be mistaken for an `on_success` suppression.

### `[mqtt]` — completion reporting and live preview

Install the source-mode optional dependency with the interpreter used to run
the app (`python3 -m pip install -r requirements-mqtt.txt`). The binary bundles it.

`configs/config-example.toml` shows all supported settings with comments
and placeholder credentials. The distributed configuration starts in dry-run
with completion and live reporting disabled. `MQTT_JSON_Status` and
`LiveMQTTEnabled` enable the two channels independently. `MQTT_JSON_Status` is the only completion-report enable; there is no `[mqtt].enabled`.
Both channels use the single `broker_address`, `broker_port`, `mqtt_username`,
`mqtt_password` and `MQTTTLS`/certificate settings. `SendMQTTOnSuccess` suppresses
successful completion messages only; failures still report when completion is
on. The completion topic is unchanged.

Old duplicate MQTT names (`enabled`, `on_success`, `host`, `port`, `topic`,
`username`, `password`, `tls`, `title`) are rejected with replacement guidance.
Update your private `[mqtt]` table from the commented example, retaining your
existing topic/credentials in the canonical fields. Other config sections,
including `[mail].enabled`, are unchanged.

The usage instructions are in the `modules/mqtt_reporting.py` module docstring; the
configuration comments explain each setting. The integration adds no JSON
configuration, state, cache, or log files. Existing application logs/digests stay
unchanged. Job commands and invocation remain the same.

Completion reports include matching friendly `name`/`title`, stable `job`, typed
`status`/`success`/`exit_code`, actual recent child stderr, warnings, dry-run,
host and run/time metadata. The reported exit code is the original process
result; an uncaught child-command exception still makes this app exit 1. The
child's distinct return code is preserved as `child_exit_code` when available.
Reporting failures do not replace the process result. Each report is a separate
JSON object, without an outer success/failure label. The snapshot-job adapter
includes `planned_datasets`, `failed_datasets`, and `skipped_datasets` with actual
source names, occurrence IDs and reasons. It does not invent a destination or
copy Syncerate's job ID/exit code. Generic live-module reports remain independent
of dataset-specific extensions.

Live state uses separate topics and measures attempted dataset entries,
success/failure/skipped outcomes, snapshot creates/deletes and dry-run plans.
Transfers are not measured by this application; bytes/rates remain null. The
card discovers devices by configurable manufacturer and stable sensor roles.

## Dataset file

Example:

```text
tank/docker
tank/appdata
```

The release includes `configs/datasets.example.txt` as the dataset-list format example. Copy it to the filename configured by `dataset_file` (the default example uses `datasets`) and replace the example dataset names before use. Dataset names are passed literally to ZFS after surrounding whitespace is stripped.

## Snapshot naming and retention

New snapshots are named:

```text
DATASET@SnapBeforeWatchTower-Date-YYYY-MM-DD_HH_MM_SS
```

Only snapshots matching the SnapBeforeWatchTower naming pattern participate in managed retention. Snapshots are sorted by the timestamp embedded in the name. The newest `retain_count` are protected, then older unprotected snapshots are destroyed only when their embedded timestamp is older than the configured cutoff.

Snapshot listing is non-recursive for each configured dataset. A malformed managed timestamp is skipped rather than destroyed. If ZFS explicitly says a configured dataset does not exist, `continue_on_missing_dataset` decides whether the script records the failure and advances to the next dataset (`true`) or stops immediately (`false`). Any other checked `zfs list` or `zfs destroy` failure is controlled separately by `continue_on_other_failures`; when true, that dataset is recorded as failed and processing advances to the next configured dataset, while false stops immediately. Recorded continuable failures still make the final run fail after remaining dataset processing and normal log cleanup. Snapshot-create failures that are not the explicit missing-dataset case remain immediately fatal regardless of `continue_on_other_failures`.

Each dataset is processed separately and a new timestamp is generated for each snapshot. A later failure does not roll back earlier successful snapshots or deletions.

## Log and digest files

Source runs write to `logs/` beside the source script. A binary in a directory named `dist` writes to the parent project’s `logs/`; a binary deployed elsewhere writes beside the executable. If the directory is unwritable, the run fails before ZFS/Docker work; no temporary fallback is used. `[logging].prefix` controls the generated file names.

A run can create:

```text
PREFIX-Date-YYYY-MM-DD_HH_MM_SS.log
PREFIX-Date-YYYY-MM-DD_HH_MM_SS.err
PREFIX-Date-YYYY-MM-DD_HH_MM_SS.digest
```

An empty current `.err` is removed at the end of the run, including dry-run. Mail reads the newest log/error files independently, so a report can include an older non-empty error file when the current one is unavailable. Private `config.toml`, `datasets`, `Storage-Docker-Cleanup`, and `AsusN14E-snaplist` files are not distributed and are ignored by Git (including lowercase host-list spellings). Create your own config/dataset list from the examples in `configs/`.

Managed old log/digest files are grouped by timestamp and use the same `older_than`/`retain_count` policy as snapshots.

During a real `create` run, Docker digests are collected with:

```bash
docker images --digests
```

A nonzero Docker exit or digest-file write failure is logged and the snapshot run continues; failure to launch Docker (for example a missing executable) is fatal. No empty/partial digest file is intentionally kept after a failed capture.

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

## Home Assistant MQTT examples

The supplied `homeassistant/success-failure-automation.yaml` and
`homeassistant/live-preview-card.yaml` are the completion/Pushover automation
and manufacturer-discovered Markdown card. Keep the completion topic matching
your config. Configure your own Pushover service, and enable only one completion
automation on that topic. The original automation filename is retained as an
alternative. Both examples ignore dry-run reports before notification or real
sequence actions. Live sensors/events do not trigger the completion automation.
See the module instructions and YAML comments for installation and live-test
limits. This project does not modify a Home Assistant installation.

## Safety

This program performs destructive ZFS snapshot deletion and log deletion. Review `SAFETY.md`, start with `dry_run = true`, verify the resulting plan/logs, and keep independent backups before using real deletion.

## Exit results and validation

| Exit result | Meaning |
| --- | --- |
| `0` | Operation completed, or an informational `--help`/`--version` command exited. Nonfatal digest, log-cleanup, or notification errors may still have been logged. |
| `1` | Root refusal or an uncaught operational/configured-dataset failure. Continued per-dataset failures still produce an overall failure. |
| `2` | CLI or configuration loading/validation error, before operational work and notification reporting. |

The command must be a TOML string with value `"create"` or `"delete"`; arrays, tables, booleans, and numbers are configuration errors. Invalid command types and out-of-range ages exit 2 with a configuration message before logs, root checks, operations, or reports. Configuration errors do not send mail/MQTT.

Review the logs as well as the exit code. MQTT reports logged nonfatal errors as `warning: true` on an otherwise successful run; logger messages are kept separate from actual child stderr. Notification delivery failure does not change the operation result; a successful exit alone does not prove delivery. Earlier completed snapshots or deletions are not rolled back on later failure.

To create snapshots, set `[application].command = "create"`. To perform retention only, set it to `"delete"`. Keep `dry_run = true` while checking the intended plan; after testing on disposable data, set it to `false` for real operations. Invoke the same `-c CONFIG` command for either mode.

Run the included offline regression tests from the project directory with Python 3.11 or newer:

```bash
python3 -B -m unittest discover -s tests -v
```

`-B` prevents bytecode cache creation, `discover -s tests` finds the shipped tests, and `-v` shows each result. Storage and notification delivery are isolated in these tests. One harmless Python child verifies real stderr capture. Optional PyYAML/Jinja tests render the HA examples offline and skip if those test tools are unavailable. Read `VERIFICATION.md` for release checks and live-testing limits. `manifest.sha256` lists release file hashes, excluding itself; on Linux verify them from this directory with:

```bash
sha256sum -c manifest.sha256
```

This checks file integrity; it does not certify operational safety.
