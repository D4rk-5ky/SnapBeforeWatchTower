# SnapBeforeWatchTower

SnapBeforeWatchTower creates ZFS snapshots for a list of datasets, records Docker image digests, and removes old matching snapshots and log groups according to an age and count policy. It does not start Watchtower, update containers, stop services, restore data, or coordinate application-consistent snapshots.

## Requirements and setup

- Linux and Python **3.10 or newer** (the source uses `str | None` annotations).
- ZFS tools in `PATH` and existing datasets accessible to root.
- Docker CLI and daemon for digest capture in a real `create` run. `delete` and dry-run do not invoke Docker.
- For email only: a configured `mail` program supporting `-s` and `--attach`.
- Core snapshot/email operation uses only the Python standard library. MQTT reporting requires `paho-mqtt` from `requirements-mqtt.txt`.

Extract the full project, enter its directory, and use `python3 SnapBeforeWatchTower.py`. Normal operations, including dry-run, require root. Help and version do not require root or ZFS.

## Setup

Copy the example configuration and edit it:

## Disclaimer

This project is AI-assisted / vibe-coded software created as a hobby project. It has not been professionally audited and may contain bugs, unsafe behavior, data-loss issues, security problems, or incorrect assumptions.

You are responsible for reviewing the code, testing it in a safe environment, making backups, and understanding what it does before using it on real data. The author is not responsible for damage, data loss, broken systems, security issues, or other problems caused by using this software.

## Data Loss Warning

This application can perform destructive operations, including deleting ZFS snapshots, and backup data. Always test with dry-runs first, check the generated plans, and keep a separate working backup.

---

## Overview

These display all CLI options and the installed application version, respectively.

## Dataset configuration

Create a UTF-8 text file with one dataset per line, for example `datasets.txt`:

```text
tank/docker
tank/appdata
```

Blank lines are ignored and surrounding whitespace is stripped. Lines are passed as whole dataset names; do not add quotes or comments. There is no comment syntax, dataset validation, or deduplication. An empty file performs no dataset operations but can still trigger Docker capture and log cleanup. Relative file paths resolve from the working directory.

The original `snaplist` and `full-snaplist` are included unchanged. They contain installation-specific names; review them before use. `full-snaplist` also contains `Storage/DataSet With Spaces`, which is passed literally to ZFS and is not validated by Python.

Snapshot settings are CLI arguments. Optional MQTT settings use a JSON file passed with `--mqtt-config`; when password authentication is used, set `username` and the plain string `password` directly in that JSON file. There is no general JSON/TOML/INI configuration file or `--config` option. See [config.example.md](config.example.md) for examples covering every option, [mqtt.example.json](mqtt.example.json) for every MQTT setting, and [datasets.example.txt](datasets.example.txt) for a small dataset template.

## Commands

Run these from the extracted project directory after replacing the dataset names.

### Preview creation and cleanup

```bash
sudo python3 SnapBeforeWatchTower.py --command create --file datasets.txt --older-than 7d --retain-count 10 --dry-run
```

This previews snapshot creation, lists existing ZFS snapshots to calculate retention, and previews old-log cleanup. Docker capture is skipped. **Dry-run still creates log directories and run logs, removes an empty current error log, and can send email if requested.** It does not execute ZFS snapshot creation/destruction or delete old log groups. The preview cannot test Docker availability or snapshot-creation permission and does not add the hypothetical new snapshot to the retention calculation.

### Create snapshots and clean up

```bash
sudo python3 SnapBeforeWatchTower.py --command create --file datasets.txt --older-than 7d --retain-count 10
```

The script first attempts Docker digest capture. For each dataset in file order, it creates one snapshot and immediately applies retention to that dataset. After all datasets, it cleans up old log groups. Each snapshot gets its own local timestamp; this is not an atomic snapshot across all datasets. A later failure does not undo earlier successful actions.

### Preview deletion

```bash
sudo python3 SnapBeforeWatchTower.py --command delete --file datasets.txt --older-than 7d --retain-count 10 --dry-run
```

This lists existing snapshots and previews eligible snapshot and log-group deletions.

### Delete old snapshots and logs

```bash
sudo python3 SnapBeforeWatchTower.py --command delete --file datasets.txt --older-than 7d --retain-count 10
```

This applies retention to listed datasets and then log groups. It does not create snapshots or capture Docker digests. There is no interactive deletion confirmation.

## All command-line options

| Option | Required/default | Behavior |
| --- | --- | --- |
| `-h`, `--help` | Optional | Show usage and exit before logging or external commands. |
| `--version` | Optional | Show application version and exit before logging or external commands. |
| `--mqtt-config PATH` | Unset | Load and validate MQTT JSON before dataset operations, then publish one final non-retained success/failure report. Optional `username` and plain-string `password` are read directly from the JSON. Dry-run validates the file but suppresses publishing. |
| `-c`, `--command create\|delete` | Required | Create then clean up, or clean up only. |
| `-f`, `--file PATH` | Required | Read the dataset list. |
| `-o`, `--older-than Nd\|Nw\|Nm` | Required | Delete eligible items strictly older than this age. `d` is days, `w` is weeks, `m` is 30-day months. Nonnegative whole numbers only, with lowercase units; `0d` is accepted. Applies to snapshots and logs. |
| `-r`, `--retain-count INTEGER` | Required | Protect this many newest matching snapshots per dataset and this many newest log timestamp groups. Zero and negative values both disable the count floor. |
| `-s`, `--send-mail EMAIL` | Unset | Request failure email; together with `--mail-on-success`, also request success email. |
| `-mos`, `--mail-on-success` | False | Add success email when `--send-mail` is present. Does not suppress failure email. Has no effect alone. |
| `-d`, `--dry-run` | False | Preview snapshot/old-log mutations, with the logging and email behavior described above. |

### Email example

```bash
sudo python3 SnapBeforeWatchTower.py -c create -f datasets.txt -o 7d -r 10 -s you@example.com -mos
```

This requests email for failures caught by the main operation handler or root check, and for runs considered successful. Omit `-mos` for failure-only notifications. Reports use the newest `.log` and newest `.err` independently by modification time. A nonempty `.err` and the `.log` are attached and included in the body. `.digest` files are not attached. Mail failures are logged; they do not reliably change the exit status.

## MQTT status reports

Install the optional dependency with the same Python interpreter that runs the app:

```bash
python3 -m pip install -r requirements-mqtt.txt
cp mqtt.example.json mqtt.json
```

Edit `mqtt.json`. For password authentication, put the broker username and password directly in the JSON:

```json
{
  "username": "mqtt-user",
  "password": "<String>"
}
```

Then run normally:

```bash
sudo python3 SnapBeforeWatchTower.py \
  --command create \
  --file datasets.txt \
  --older-than 7d \
  --retain-count 10 \
  --mqtt-config mqtt.json
```

The configuration is validated before logging, dataset reads, Docker, or ZFS operations. The app publishes exactly one final JSON report after logging/email finalization. MQTT is optional and disabled when the option is absent. Publishing is deliberately suppressed during `--dry-run`, because the supplied automation advances its backup sequence on `status: success`.

The report uses the fields read by the supplied Home Assistant automation:

```json
{
  "status": "success",
  "title": "Zotac RI531 - SnapBeforeWatchTower",
  "name": "Zotac RI531 - SnapBeforeWatchTower",
  "job": "Zotac RI531 - SnapBeforeWatchTower",
  "exit_code": 0,
  "warning": false,
  "error": "",
  "stderr": "",
  "command": "create",
  "version": "0.0.3",
  "run_id": "unique UUID",
  "finished_at": "UTC ISO-8601 timestamp"
}
```

`status` is `success` for exit code 0 and `failure` otherwise. Nonfatal messages written to the error logger—such as Docker digest capture failure, old-log deletion failure, or mail failure—produce `status: success`, `exit_code: 0`, and `warning: true`; their bounded current-run text appears in `stderr`. A fatal exception produces `status: failure`, a nonzero `exit_code`, and an `error`. `stderr` and `error` are each limited to 4096 characters. `run_id` lets consumers distinguish reports, and `finished_at` is UTC.

Reports use configured QoS 0, 1, or 2 and always use `retain: false`. The default port is 1883, changing automatically to 8883 when TLS is enabled and no port is set. Publish completion has a configurable 1–120 second timeout. MQTT publishing failure is logged after the underlying job outcome is known and does not replace that outcome or trigger another report.

The optional `password` field is a plain nonempty JSON string and requires `username`. Because the password is stored directly in the MQTT JSON file, protect that file with appropriate filesystem permissions and do not commit or share operational credentials. The password is passed to the internal MQTT worker over stdin rather than on the process command line, and detailed worker failures are still sanitized from application logs. File paths for CA/client certificates are resolved relative to the MQTT JSON file. TLS verifies the broker certificate and hostname; there is no insecure mode. See [config.example.md](config.example.md) for all MQTT fields.

The supplied automation does not yet subscribe to the example SnapBeforeWatchTower topic. Add a trigger using the exact topic from your `mqtt.json` and handle it with the existing `report`, `mqtt_status`, and success/failure branches. If this job is the final step, place the shutdown action in the SnapBeforeWatchTower success branch rather than scheduling it immediately after the start command.

## Retention and snapshot names

New snapshots are named `DATASET@SnapBeforeWatchTower-Date-YYYY-MM-DD_HH_MM_SS`. Deletion also recognizes the legacy `DATASET@SnapBeforeWatchTower-DateYYYY-MM-DD_HH_MM_SS` form. Names outside those patterns are ignored; impossible dates are skipped and logged.

For each dataset, matching snapshots are sorted by the timestamp in the name. The newest count floor is protected regardless of age. Among the remainder, only timestamps strictly before the age cutoff are deleted. For example, `--retain-count 10 --older-than 7d` keeps at least the newest ten matching snapshots if that many exist, plus all matching snapshots no older than seven days. Nonmatching snapshots do not count toward the floor.

**With a count of zero or less, all age-eligible matching snapshots can be deleted.** This setting does not guarantee that one snapshot remains. Local wall-clock time and embedded names drive retention, rather than ZFS creation properties. The ZFS list command has no recursive flag; list child datasets explicitly.

## Logs and operation results

Logs go in `logs/` beside the script when run as root and the write probe succeeds. Otherwise they use `SnapBeforeWatchTower/` under Python's temporary directory (normally `/tmp` on Linux). A non-root run creates fallback logs and exits with status 1 before ZFS or Docker commands; requested failure mail may still run.

Each run timestamp identifies:

- `.log`: INFO/DEBUG application messages; INFO also goes to the console.
- `.err`: ERROR messages and error separators; errors use a separate logger and are not automatically copied into `.log`. The current file is removed if empty on normal finalization.
- `.digest`: raw `docker images --digests` output on successful real create-mode capture.

Log cleanup groups `.log`, `.err`, and `.digest` by embedded timestamp and applies the same age/count settings as snapshots. Its filename matcher also accepts some underscore/lowercase variants and a matching suffix with extra leading text. Keep unrelated files outside the log directory.

Parser/configuration errors return status 2. Help/version and normal completion return 0; non-root execution and uncaught operational errors return a nonzero status. An exception stops subsequent operations without rollback. Review `.err` as well as the exit code: a Docker command returning nonzero, digest-write failure, log-deletion failure, mail failure, or MQTT delivery failure can be logged without making the overall run fail. In particular, Docker returning nonzero does not prevent snapshot creation or retention; a missing Docker executable raises an exception and stops the operation.

This program performs destructive ZFS snapshot deletion and log deletion. Review `SAFETY.md`, start with `dry_run = true`, verify the resulting plan/logs, and keep independent backups before using real deletion.
