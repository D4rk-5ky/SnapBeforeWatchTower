# SnapBeforeWatchTower configuration reference — 0.0.20

This Markdown file is a reference, not an input file. The app reads TOML through
`-c CONFIG`. The loadable, fully commented example is
`configs/config-example.toml`. Copy it to your own ignored `config.toml`; it contains every supported setting. Protect operational
credentials and replace all placeholders. Reporting usage instructions live in
`modules/mqtt_reporting.py`; the four application/notification/report/logging sections
retain their existing meanings except the explicitly integrated MQTT metadata.

Public commands: `python3 SnapBeforeWatchTower.py -c config.toml` runs the
configured create/delete job (requires root, including dry-run). `-h`/`--help`
shows usage and `--version` prints the version without operations. The frozen
`./dist/SnapBeforeWatchTower` accepts the same flags. The build helper's
`-h`/`--help` and `--version` inspect its requirements/version without build work;
with no arguments it rebuilds the executable and replaces generated artifacts.

Relative dataset/TLS paths in TOML use its directory; the `-c` path itself uses
the shell working directory. Only dataset_file expands `~`. Completion reports
and live preview have independent enables; MQTT_JSON_Status is the only completion enable.
LiveMQTTEnabled is independent; both use the single broker/auth/TLS block. All defaults below are safe distribution
examples, not broker credentials or a ready-to-run production dataset list.

## Complete TOML example

```toml
[application]
command = "create"
dataset_file = "datasets"
older_than = "7d"
retain_count = 10
dry_run = true
continue_on_missing_dataset = true
continue_on_other_failures = true

[mail]
enabled = false
recipient = "you@example.com"
on_success = false

[mqtt]
MQTT_JSON_Status = false
SendMQTTOnSuccess = true
mqtt_json_topic = "homeassistant/SnapBeforeWatchTower/example-host/status"
broker_address = "mqtt.example.local"
broker_port = 1883
mqtt_username = "YOUR_MQTT_USERNAME"
mqtt_password = "YOUR_MQTT_PASSWORD"
MQTTTLS = false
ca_file = ""
cert_file = ""
key_file = ""
qos = 0
timeout = 15
LiveMQTTEnabled = false
LiveMQTTDiscovery = true
LiveBackupName = "SnapBeforeWatchTower"
LiveManufacturer = "SnapBeforeWatchTower"
LiveHeartbeatSeconds = 60
LiveNotifyStart = false
LiveNotifySuccess = true
LiveNotifyFailure = true
LiveDeviceID = ""

[logging]
prefix = ""

[report]
title = ""
name = "Nightly Docker snapshots"
comment = ""
```

The comments in the loadable examples document option purpose, accepted values,
precedence and notification behavior. Generic completed/total live progress counts
attempted configured dataset entries independently from item outcomes. No bytes
or rates are inferred. Dry-run completion reports are ignored by HA before real
sequences/notifications. Existing logs and digest files remain unchanged.
