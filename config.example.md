# SnapBeforeWatchTower configuration reference

SnapBeforeWatchTower is configured through a single TOML file. This Markdown file is a human-readable reference only; the application does **not** load it. The loadable example is `config-example.toml`.

## Public command-line option

There is one public command-line option:

```bash
sudo python3 SnapBeforeWatchTower.py -c config.toml
```

| Option | Required | Meaning |
| --- | --- | --- |
| `-c CONFIG` | Yes | Path to the TOML configuration file. Relative file paths *inside* the TOML file are resolved relative to the TOML file itself. |

There are no separate public flags for command mode, datasets, retention, mail, MQTT, dry-run, help, or version. Those runtime settings belong in TOML so one file describes the whole job.

## Complete TOML example

Copy `config-example.toml` to a private operational file such as `config.toml`, copy `datasets.example.txt` to the dataset filename configured in that TOML (the example uses `datasets`), and edit both files. The example intentionally starts with `dry_run = true`, mail disabled, and MQTT disabled.

```toml
[application]
command = "create"
dataset_file = "datasets"
older_than = "7d"
retain_count = 10
dry_run = true

[mail]
enabled = false
recipient = "you@example.com"
on_success = false

[mqtt]
enabled = false
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

## `[application]`

| Setting | Required | Meaning |
| --- | --- | --- |
| `command` | Yes | `"create"` captures Docker image digests, creates one managed ZFS snapshot per dataset, applies snapshot retention, then cleans old log groups. `"delete"` only applies snapshot retention and log cleanup. |
| `dataset_file` | Yes | UTF-8 file containing one ZFS dataset name per non-empty line. Relative paths are resolved relative to the TOML file. If ZFS reports a configured dataset does not exist, that dataset is skipped so later datasets still run, but the final run remains failure and notifications identify the missing dataset(s). |
| `older_than` | Yes | Strict age cutoff such as `"7d"`, `"2w"`, or `"1m"`. Months are treated as 30 days. The integer must be nonnegative. |
| `retain_count` | Yes | Protect at least this many newest matching snapshots per dataset and newest log timestamp groups. Zero or a negative integer disables the count floor; age rules still apply. |
| `dry_run` | Yes | When `true`, preview snapshot creation/destruction and old-log deletion. Snapshot listing and logging still occur, configured email can still be sent, Docker digest capture is skipped, and MQTT publishing is suppressed. |

## `[mail]` — optional

The whole `[mail]` table may be omitted; mail then defaults to disabled.

| Setting | Required/default | Meaning |
| --- | --- | --- |
| `enabled` | Default `false` | Enables failure mail. When false, the other mail values are ignored for runtime delivery. |
| `recipient` | Required when enabled | Recipient passed to the local `mail` command. Must be a non-empty string when mail is enabled. |
| `on_success` | Default `false` | Also sends a success mail. Failure mail remains enabled whenever mail is enabled. |

## `[mqtt]` — optional

The whole `[mqtt]` table may be omitted; MQTT then defaults to disabled. Install `requirements-mqtt.txt` only when real MQTT publishing is enabled.

| Setting | Required/default | Meaning |
| --- | --- | --- |
| `enabled` | Default `false` | Enables the final MQTT JSON status report. Disabled mode does not require broker fields or Paho. |
| `host` | Required when enabled | MQTT broker hostname or IP address. |
| `port` | Default `1883`, or `8883` when TLS is enabled and the key is omitted | Broker TCP port, integer 1–65535. |
| `topic` | Required when enabled | Publish topic. `+` and `#` wildcards are rejected. It must match the Home Assistant MQTT trigger topic. |
| `title` | Default `"SnapBeforeWatchTower"` | Human-readable run name copied to the MQTT payload fields `title`, `name`, and `job`. |
| `username` | Optional | Broker username. Use an empty string for no username. |
| `password` | Optional | Plain TOML password string. A non-empty password requires a non-empty username. Protect `config.toml` with restrictive permissions. |
| `qos` | Default `0` | MQTT QoS: `0`, `1`, or `2`. Reports are always non-retained. |
| `tls` | Default `false` | Enables verified TLS with certificate and hostname verification. |
| `ca_file` | Optional | CA bundle path. Empty string uses system trust. Relative paths are resolved relative to the TOML file. Requires TLS when set. |
| `cert_file` | Optional | Client certificate path for mutual TLS. Must be paired with `key_file`; relative paths are TOML-relative. |
| `key_file` | Optional | Client private-key path for mutual TLS. Must be paired with `cert_file`; relative paths are TOML-relative. |
| `timeout` | Default `15` | Total MQTT worker timeout in seconds, integer 1–120. |

Unknown TOML sections and unknown keys are rejected. The retired JSON MQTT configuration and old multi-flag interface are not supported.

## Dataset file

Example:

```text
tank/docker
tank/appdata
```

Blank lines are ignored. Dataset lines are stripped of surrounding whitespace, are not deduplicated, and do not support comments. Missing-dataset continuation is intentionally narrow: only ZFS stderr identifying a nonexistent dataset is continuable. Other ZFS failures still abort normally. The final MQTT contract remains `success`/`failure`; a missing-dataset run reports `failure` with exit code 1 and a specific reason in `error`.

## Safe first run

Keep `dry_run = true`, verify the logs and planned snapshot retention carefully, and review `SAFETY.md` before changing to a real run. Dry-run still performs real ZFS snapshot listing, so ZFS tools and access to the named datasets are still required.
