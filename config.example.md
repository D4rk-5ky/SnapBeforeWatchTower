# Configuration examples

The application is configured only through CLI flags and a UTF-8 dataset list. This document is an example reference, not a file the app can load. Replace example paths, dataset names, and the recipient before running. All options and aliases are listed in README.md.

## Dataset list

Copy `datasets.example.txt` to `datasets.txt` and edit its two dataset names. There are no supported comments or other keys in this list. The original `snaplist` and `full-snaplist` remain available as installation-specific examples.

## Every option, using long names

```bash
python3 SnapBeforeWatchTower.py --help
python3 SnapBeforeWatchTower.py --version
sudo python3 SnapBeforeWatchTower.py \
  --command create \
  --file datasets.txt \
  --older-than 7d \
  --retain-count 10 \
  --send-mail you@example.com \
  --mail-on-success \
  --mqtt-config mqtt.json \
  --dry-run
```

The first commands display usage/version. The last command previews creation and retention with all operational options, using the plain MQTT username/password stored in the selected JSON file. It still writes run logs and may send email; it validates MQTT configuration but suppresses MQTT publishing. Remove `--send-mail` and `--mail-on-success` to disable mail; remove only `--mail-on-success` for failure-only mail. Remove `--mqtt-config` to disable MQTT. Remove `--dry-run` to perform the real operations after reviewing the preview.

## Short aliases and deletion

```bash
python3 SnapBeforeWatchTower.py -h
sudo python3 SnapBeforeWatchTower.py -c delete -f datasets.txt -o 2w -r 10 -s you@example.com -mos -d
```

This previews deletion without invoking Docker. `1m` means 30 days, `2w` means 14 days, and `7d` means seven days. Command, file, age, and count have no defaults and must be supplied. Mail is unset and both switches are false by default. Use a positive count to protect the newest matching snapshots and log groups; zero and negative counts remove that protection. `--version` has no short alias.

## MQTT JSON: every setting

Install `requirements-mqtt.txt`, copy `mqtt.example.json` to a private operational file such as `mqtt.json`, and edit it:

```json
{
  "host": "mqtt.example.local",
  "port": 1883,
  "topic": "homeassistant/SnapBeforeWatchTower/Zotac-RI531/status",
  "title": "Zotac RI531 - SnapBeforeWatchTower",
  "username": "your-mqtt-user",
  "password": "<String>",
  "qos": 0,
  "tls": false,
  "ca_file": null,
  "cert_file": null,
  "key_file": null,
  "timeout": 15
}
```

| Key | Required/default | Meaning |
| --- | --- | --- |
| `host` | Required | Broker hostname or IP address. |
| `topic` | Required | Publish topic; `+` and `#` wildcards are rejected. Use the same value in Home Assistant's MQTT trigger. |
| `port` | 1883, or 8883 when TLS is true and this key is omitted | Broker TCP port, 1–65535. |
| `title` | `SnapBeforeWatchTower` | Human-readable run name copied to `title`, `name`, and `job`. |
| `username` | null | Optional broker username. |
| `password` | null | Optional plain nonempty password string stored directly in the JSON; requires `username`. |
| `qos` | 0 | MQTT delivery QoS: 0, 1, or 2. Reports are never retained. |
| `tls` | false | Enable server-authenticated TLS. |
| `ca_file` | null | Optional CA bundle path relative to this JSON file; requires TLS. System trusted CAs are used when null. |
| `cert_file` | null | Optional client certificate path relative to this JSON file; requires TLS and `key_file`. |
| `key_file` | null | Optional client key path relative to this JSON file; requires TLS and `cert_file`. |
| `timeout` | 15 | Total MQTT worker timeout in seconds, integer 1–120. |

Unknown keys are rejected. For password authentication, place the credentials directly in the JSON:

```json
{
  "username": "mqtt-user",
  "password": "<String>"
}
```

Run the application normally with `--mqtt-config mqtt.json`; no environment-variable setup is required. Because the operational JSON contains the password, protect that file with restrictive permissions and do not commit or share it.

Home Assistant must subscribe to the exact topic. A compatible trigger block is:

```yaml
- trigger: mqtt
  id: snapbeforewatchtower_status
  options:
    topic: homeassistant/SnapBeforeWatchTower/Zotac-RI531/status
```

It can reuse the supplied automation's `trigger.payload_json`, `report.status`, `report.title`, `report.exit_code`, `report.warning`, `report.error`, and `report.stderr` templates.
