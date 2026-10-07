# SnapBeforeWatchTower configuration reference

SnapBeforeWatchTower is configured through a single TOML file. This Markdown file is a human-readable reference only; the application does **not** load it. The loadable example is `config-example.toml`.

## Public command-line flags

Normal operation:

```bash
sudo python3 SnapBeforeWatchTower.py -c config.toml
```

| Flag | Required | Meaning |
| --- | --- | --- |
| `-c CONFIG` | Yes for normal operation | Path to the TOML configuration file. A relative CONFIG path uses the current working directory. Relative dataset/TLS paths *inside* TOML use the TOML directory; dataset_file also expands ~. |
| `-h`, `--help` | No | Show complete CLI help and exit before configuration loading or operational work. |
| `--version` | No | Show the application version and exit before configuration loading or operational work. |

Reference commands:

```bash
python3 SnapBeforeWatchTower.py --help
python3 SnapBeforeWatchTower.py --version
./dist/SnapBeforeWatchTower --help
./dist/SnapBeforeWatchTower --version
sudo ./dist/SnapBeforeWatchTower -c config.toml
```

The PyInstaller build is produced by `bash build-pyinstaller.sh` at `dist/SnapBeforeWatchTower`. All generated build state (virtual environment, pip cache, PyInstaller work files, and PyInstaller config/cache) is kept under the gitignored `.build-pyinstaller/` directory. The build script cleans generated/stale `dist/` content while retaining `dist/README.md`, and fails unless the final directory contains exactly `SnapBeforeWatchTower` and `README.md`. It bundles Python plus Paho MQTT; external host commands such as ZFS, Docker, and `mail` remain system requirements.

There are no separate public flags for command mode, datasets, retention, mail, MQTT, or dry-run. Those runtime settings belong in TOML so one file describes the whole job.

## Complete TOML example

Copy `config-example.toml` to a private operational file such as `config.toml`, copy `datasets.example.txt` to the dataset filename configured in that TOML (the example uses `datasets`), and edit both files. The example intentionally starts with `dry_run = true`, mail disabled, and MQTT disabled.

```toml
[application]
command = "create"
dataset_file = "datasets"
older_than = "7d"
retain_count = 10
dry_run = true
continue_on_missing_dataset = true
continue_on_other_failures = true

[logging]
prefix = "SnapBeforeWatchTower"

[report]
title = "Example host - SnapBeforeWatchTower"
comment = ""

[mail]
enabled = false
recipient = "you@example.com"
on_success = false

[mqtt]
enabled = false
on_success = false
host = "mqtt.example.local"
port = 1883
topic = "homeassistant/SnapBeforeWatchTower/example-host/status"
title = "Example host - SnapBeforeWatchTower"
username = "your-mqtt-user"
password = "<String>"
qos = 0
tls = false
ca_file = ""
cert_file = ""
key_file = ""
timeout = 15
```

## `[application]`

| Setting | Required | Meaning |
| --- | --- | --- |
| `command` | Yes | `"create"` captures Docker image digests, creates one managed ZFS snapshot per dataset, applies snapshot retention, then cleans old log groups. `"delete"` only applies snapshot retention and log cleanup. |
| `dataset_file` | Yes | UTF-8 file containing one ZFS dataset name per non-empty line. Relative paths are resolved relative to the TOML file. Per-dataset continuation is controlled by the two settings below; recorded failures still make the final run fail. |
| `older_than` | Yes | Strict age cutoff such as `"7d"`, `"2w"`, or `"1m"`. Months are treated as 30 days. The integer must be nonnegative. |
| `retain_count` | Yes | Protect at least this many newest matching snapshots per dataset and newest log timestamp groups. Zero or a negative integer disables the count floor; age rules still apply. |
| `dry_run` | Yes | When `true`, preview snapshot creation/destruction and old-log deletion. Snapshot listing and logging still occur and Docker digest capture is skipped. Mail/MQTT reporting follows the normal policy: failures report when the channel is enabled; successful dry-runs require that channel's `on_success=true`. |
| `continue_on_missing_dataset` | Default `true` | When ZFS explicitly reports a configured dataset as nonexistent, `true` records the failure and continues with the next configured dataset; `false` stops immediately. Either way, the final run is failure and enabled mail/MQTT reports it. |
| `continue_on_other_failures` | Default `true` | For any other checked per-dataset `zfs list` or `zfs destroy` failure, `true` records the failure and continues with the next configured dataset; `false` stops immediately. It does not make global/config/root/input or unrelated snapshot-create failures recoverable. |

## `[logging]` and `[report]` — optional

```toml
[logging]
prefix = "SnapBeforeWatchTower"

[report]
title = "Example host - SnapBeforeWatchTower"
comment = ""
```

| Setting | Default | Meaning |
| --- | --- | --- |
| `[logging].prefix` | `""` | Names the `.log`, `.err`, and `.digest` files. Empty uses the actual script/executable basename without its final extension. Custom values start with an ASCII letter/digit and use only letters, digits, dots, underscores, or hyphens. Paths, wildcard characters, and line breaks are rejected. |
| `[report].title` | `""` | Single-line heading at the top of the email body and the MQTT `title`, `name`, and `job` fields. A nonempty value overrides `[mqtt].title`. Empty uses the script/executable basename for email and preserves `[mqtt].title` for MQTT. Existing SUCCESS/FAILED/DRY-RUN email subjects are retained. |
| `[report].comment` | `""` | Free-form text included after the email heading and in MQTT's `comment` field. Newlines, blank lines and surrounding whitespace are preserved. NUL and non-string values are rejected. |

All generated `.log`/`.err`/`.digest` files are stored in `logs/` beside the actual source script or frozen executable. This includes `dist/logs/` when the executable is run from `dist/`. There is no temporary fallback; an unwritable folder stops the run before ZFS or Docker work. Root is still required for the operation, including dry-run.

Log retention and mail attachment lookup use the configured prefix. Changing it leaves previous-prefix files in place; snapshot naming and snapshot retention still use `SnapBeforeWatchTower-Date-...` and are unaffected. If mail and MQTT are disabled, report settings do not enable them.

For a two-line comment, use a double-quoted TOML string with a newline escape:

```toml
[report]
title = "Example host - SnapBeforeWatchTower"
comment = "First line\nSecond line"
```

Or write the lines directly in a multiline TOML string:

```toml
[report]
title = "Example host - SnapBeforeWatchTower"
comment = """
First line

Second line
"""
```

Replace the existing `[report]` table when trying an example; TOML does not allow duplicate tables. TOML removes the newline immediately after the opening triple quotes. Remaining line breaks are retained in email and JSON. A literal TOML string such as `comment = 'First\nSecond'` keeps the backslash and `n` characters, as TOML specifies. The application does not perform a second unescape pass. MQTT represents newline characters as JSON escapes on the wire; consumers recover real line breaks when decoding JSON.

## `[mail]` — optional

The whole `[mail]` table may be omitted; mail then defaults to disabled.

| Setting | Required/default | Meaning |
| --- | --- | --- |
| `enabled` | Default `false` | Enables failure mail. When false, the other mail values are ignored for runtime delivery. |
| `recipient` | Required when enabled | Recipient passed to the local `mail` command. Must be a non-empty string when mail is enabled. |
| `on_success` | Default `false` | Also sends success mail for real and dry-run executions. Failure mail remains enabled whenever mail is enabled, regardless of this setting. |

## `[mqtt]` — optional

The whole `[mqtt]` table may be omitted; MQTT then defaults to disabled. Install `requirements-mqtt.txt` whenever MQTT is enabled, including dry-run, because successful dry-runs can publish when `on_success=true` and failed dry-runs still publish failure reports.

| Setting | Required/default | Meaning |
| --- | --- | --- |
| `enabled` | Default `false` | Enables MQTT reporting. Disabled mode does not require broker fields or Paho. When enabled, failures are always reported in both real and dry-run executions. |
| `on_success` | Default `false` | Also publishes success reports for real and dry-run executions. When false, only successful MQTT reports are suppressed; failure reports still publish. |
| `host` | Required when enabled | MQTT broker hostname or IP address. |
| `port` | Default `1883`, or `8883` when TLS is enabled and the key is omitted | Broker TCP port, integer 1–65535. |
| `topic` | Required when enabled | Nonempty publish topic without NUL, at most 65535 UTF-8 bytes. `+` and `#` wildcards are rejected. Replace `example-host` consistently here and in the Home Assistant MQTT trigger. |
| `title` | Default `"SnapBeforeWatchTower"` | MQTT title fallback for `title`, `name`, and `job`. A nonempty `[report].title` overrides it. |
| `username` | Optional | Broker username. Use an empty string for no username. |
| `password` | Optional | Plain TOML password string. A non-empty password requires a non-empty username. Protect `config.toml` with restrictive permissions. |
| `qos` | Default `0` | MQTT QoS: `0`, `1`, or `2`. Reports are always non-retained. |
| `tls` | Default `false` | Enables verified TLS with certificate and hostname verification. |
| `ca_file` | Optional | CA bundle path. Empty string uses system trust. Relative paths are resolved relative to the TOML file. Requires TLS when set. |
| `cert_file` | Optional | Client certificate path for mutual TLS. Must be paired with `key_file`; relative paths are TOML-relative. |
| `key_file` | Optional | Client private-key path for mutual TLS. Must be paired with `cert_file`; relative paths are TOML-relative. |
| `timeout` | Default `15` | Total MQTT worker timeout in seconds, integer 1–120. |

Unknown TOML sections and unknown keys are rejected. All operational configuration uses the TOML file.

## Dataset file

Example:

```text
tank/docker
tank/appdata
```

Blank lines are ignored. Dataset lines are stripped of surrounding whitespace, are not deduplicated, and do not support comments. Missing-dataset continuation is intentionally narrow: only explicit ZFS nonexistent-dataset stderr uses `continue_on_missing_dataset`. Other checked per-dataset `zfs list`/`zfs destroy` failures use `continue_on_other_failures`. Snapshot-create failures that are not the missing-dataset case, configuration errors, root failures, missing/unreadable input files, and other global failures remain immediately fatal. The final MQTT contract remains `success`/`failure`; any recorded continuation failure reports `failure` with exit code 1. Every published payload also contains `dry_run=true|false` so consumers can distinguish preview and live reports.

## Safe first run

Keep `dry_run = true`, verify the logs and planned snapshot retention carefully, and review `SAFETY.md` before changing to a real run. Dry-run still performs real ZFS snapshot listing, so ZFS tools and access to the named datasets are still required. If mail or MQTT is enabled, dry-run can also send real notifications according to each channel's `on_success` setting. The run log prints the loaded notification policy and records each success-report delivery attempt/result so a transport failure can be distinguished from an `on_success=false` suppression.
