"""SnapBeforeWatchTower MQTT completion and Home Assistant live preview.

Setup: copy configs/config-example.toml to your private config.toml and
configs/datasets.example.txt to datasets, edit both, keep [application] and
other sections, set broker_address/broker_port/mqtt_username/mqtt_password in
[mqtt], then enable MQTT_JSON_Status and/or LiveMQTTEnabled independently.
Install requirements-mqtt.txt for source execution; the binary bundles Paho.
No JSON configuration/state/cache/log files are used. JSON travels over MQTT.
Existing application logs and Docker digest files are unchanged.

Run the usual command: sudo python3 SnapBeforeWatchTower.py -c config.toml.
MQTT_JSON_Status enables final reports; SendMQTTOnSuccess suppresses only
successful reports when false. LiveMQTTEnabled independently enables live
sensors, including clearly marked dry-runs. LiveNotify* controls live events,
not completion reports or sensors. Copy homeassistant/live-preview-card.yaml
as a Markdown card; match its manufacturer to LiveManufacturer. Configure the
Pushover action in success-failure-automation.yaml and retain your existing
completion topic. Do not enable duplicate completion automations. Dry-runs
are rejected before real sequencing/notification actions in both examples.

There is exactly one app completion publisher, controlled by MQTT_JSON_Status.
There is no [mqtt].enabled or second credential block. LiveMQTTEnabled controls
only the live sensors/events; both channels share broker_address, broker_port,
mqtt_username, mqtt_password, MQTTTLS and certificate settings. Old duplicate
option names are rejected with migration guidance; use the current example.
SendMQTTOnSuccess controls successful completion reports only; failures report
whenever MQTT_JSON_Status=true. A report is one standalone JSON object, never
the "integration-success"/"integration-failure" example wrapper. This project's
job ID is SnapBeforeWatchTower and its real process exit codes are preserved.

The app completion adapter adds planned_datasets, failed_datasets and
skipped_datasets from configured source entries and observed outcomes, even
when live preview is disabled. Reasons use real stderr/exception details; no
backup destination is invented for this snapshot job. Generic MQTTReporter
usage still has no dataset sections unless explicitly supplied via details.

The adapter in modules.mqtt_report.RunReporter observes the original coordinator.
Its completed/total counts are attempted configured dataset entries (including
failures); outcomes are separate successful_items/failed_items/skipped_items.
Unattempted entries after abort are skipped, not completed. Duplicated dataset
lines have distinct item IDs. Snapshot counters come from actual successful
commands or explicit dry-run plans, never elapsed-time estimates. No bytes or
rates are available for ZFS snapshot operations, so those fields stay null.
Capture actual child stderr via capture_command(); logging messages never
stand in for child output. Latest 4000 characters are kept in memory.

MQTTReporter also accepts a TOML path for reuse: start(), update(...),
record_item('success'|'failure'|'skipped', name=..., item_id=..., reason=...),
append_stderr(...), finish(integer_exit_code, ...), close(). Supply job_type
and item_unit for the actual application. Generic reports contain no dataset
sections. Optional finish(details=...) cannot override required report fields.
close() stops heartbeats without inventing success; HA expiration and the card
identify a lost heartbeat and distinguish an earlier retained result. Device
identity hashes host/job/config path (or explicit unique LiveDeviceID); role
attributes identify sensors even after renaming. Keep config paths stable to
retain identity. A pinned device ID must be unique across concurrent jobs.

Delivery uses bounded child processes with credentials on stdin, verified TLS,
non-retained completion/events, retained discovery/last result, and unretained
live state with expiry. Broker failures never replace the real job outcome.
SIGKILL/power loss cannot produce a final report: the heartbeat expires.
"""
from __future__ import annotations

from datetime import datetime, timezone
from contextvars import ContextVar
import hashlib
import json
import math
from pathlib import Path
import re
import socket
import ssl
import subprocess
import sys
from threading import Event, Lock, Thread
import time
import uuid

WORKER_FLAG = "--mqtt-reporting-worker"
_ACTIVE = ContextVar("snap_mqtt_observer", default=None)


def capture_command(command, stderr="", returncode=0, *, planned=False):
    """Observe real child output or a dry-run action; never affect job behavior."""
    observer = _ACTIVE.get()
    if observer is not None:
        try:
            observer.capture_command(command, stderr, returncode, planned=planned)
        except Exception:
            pass  # Instrumentation must not alter the application result.



def _now():
    return datetime.now(timezone.utc).isoformat()


def _json(value):
    text = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    text.encode("utf-8")
    return text


def _text(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if not isinstance(value, str):
        raise ValueError("Expected text or captured stderr bytes")
    return value


class MQTTReporter:
    def __init__(self, config="config.toml", *, job, name=None, dry_run=False,
                 job_type="task", item_unit="tasks", config_path=None):
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib  # Only needed on Python 3.10.
        path = Path(config_path or ("config.toml" if isinstance(config, dict) else config)).resolve()
        if isinstance(config, dict):
            self.settings = dict(config)
        else:
            try:
                with path.open("rb") as handle:
                    self.settings = tomllib.load(handle).get("mqtt", {})
            except ValueError:
                raise ValueError("Invalid TOML configuration") from None
        s = self.settings
        if not isinstance(s, dict):
            raise ValueError("[mqtt] must be a TOML table")
        for key in ("MQTT_JSON_Status", "SendMQTTOnSuccess", "LiveMQTTEnabled", "LiveMQTTDiscovery",
                    "LiveNotifyStart", "LiveNotifySuccess", "LiveNotifyFailure", "MQTTTLS"):
            if key in s and type(s[key]) is not bool:
                raise ValueError(f"{key} must be true or false")
        self.job = _text(job)
        self.job_type, self.item_unit = _text(job_type), _text(item_unit)
        self.name = _text(name if name is not None else s.get("LiveBackupName", job))
        self.manufacturer = _text(s.get("LiveManufacturer", "SnapBeforeWatchTower"))
        if not all(v.strip() and "\x00" not in v for v in (self.job, self.name, self.manufacturer)) or self.manufacturer != self.manufacturer.strip():
            raise ValueError("Job, name and manufacturer must be nonempty text without surrounding manufacturer whitespace")
        if type(dry_run) is not bool:
            raise ValueError("dry_run must be a boolean")
        self.dry_run, self.run_id = dry_run, str(uuid.uuid4())
        self.completion_enabled = s.get("MQTT_JSON_Status", False)
        self.live_enabled = s.get("LiveMQTTEnabled", False)
        self.topic = _text(s.get("mqtt_json_topic", "homeassistant/jobs/status"))
        host = s.get("broker_address", "")
        if not isinstance(host, str) or (self.completion_enabled or self.live_enabled) and not host.strip():
            raise ValueError("broker_address is required when MQTT is enabled")
        if "://" in host or "\x00" in host or host != host.strip():
            raise ValueError("broker_address must be a hostname/IP without a scheme or whitespace")
        port = s.get("broker_port", 1883)
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("broker_port must be an integer from 1 to 65535")
        for key in ("mqtt_username", "mqtt_password"):
            if not isinstance(s.get(key, ""), str):
                raise ValueError(f"{key} must be text")
        if s.get("mqtt_password") and not s.get("mqtt_username"):
            raise ValueError("mqtt_password requires mqtt_username")
        heartbeat = s.get("LiveHeartbeatSeconds", 60)
        if type(heartbeat) not in (int, float) or not math.isfinite(heartbeat) or heartbeat < 1:
            raise ValueError("LiveHeartbeatSeconds must be at least 1 second")
        self.heartbeat, self.expire_after = heartbeat, max(math.ceil(heartbeat * 3), math.ceil(heartbeat * 2 + 6))
        identity = hashlib.sha256(f"{socket.gethostname()}|{job}|{path}".encode()).hexdigest()[:16]
        self.device_id = s.get("LiveDeviceID") or "job_" + identity
        if not isinstance(self.device_id, str) or not re.fullmatch(r"[a-z0-9_]{1,80}", self.device_id):
            raise ValueError("LiveDeviceID must use lowercase letters, digits and underscores")
        self.state_topic = f"job-live/{self.device_id}/state"
        self.result_topic = f"job-live/{self.device_id}/last_result"
        self.events_topic = f"job-live/{self.device_id}/events"
        for topic in (self.topic, self.state_topic):
            if not topic or any(c in topic for c in "+#\x00") or len(topic.encode()) > 65535:
                raise ValueError("MQTT topic must be nonempty without wildcards")
        self._broker = dict(host=host, port=port, username=s.get("mqtt_username", ""),
                            password=s.get("mqtt_password", ""), tls=s.get("MQTTTLS", False),
                            ca_file=s.get("ca_file"), cert_file=s.get("cert_file"),
                            key_file=s.get("key_file"), qos=s.get("qos", 0))
        self._lock, self._wake, self._stop = Lock(), Event(), Event()
        self._thread, self._started, self._finished = None, False, False
        self._started_at, self._clock, self._ended = _now(), time.monotonic(), None
        self._dirty, self._events = True, []
        self.last_delivery = {"completion": "skipped", "live": "skipped"}
        self._state = dict(status="idle", success=None, exit_code=None, phase="waiting", current_item="",
                           completed=None, total=None, progress_percent=None, transferred_bytes=None,
                           bytes_per_second=None, error="", stderr="", warning=False, finished_at=None,
                           successful_items=[], failed_items=[], skipped_items=[], metrics={})

    def _snapshot(self):
        data = dict(self._state, name=self.name, title=self.name, job=self.job, schema_version=1,
                    device_id=self.device_id, manufacturer=self.manufacturer, run_id=self.run_id,
                    job_type=self.job_type, item_unit=self.item_unit, heartbeat_timeout=self.expire_after,
                    host=socket.gethostname(), dry_run=self.dry_run, started_at=self._started_at,
                    last_heartbeat=_now(), runtime_seconds=round((self._ended if self._ended is not None else time.monotonic()) - self._clock, 2))
        for label in ("successful", "failed", "skipped"):
            data[label + "_item_count"] = len(data[label + "_items"])
        return json.loads(_json(data))

    def snapshot(self):
        with self._lock:
            return self._snapshot()

    def start(self):
        with self._lock:
            if self._started or self._finished or self._stop.is_set():
                return False
            self._started, self._clock, self._started_at = True, time.monotonic(), _now()
            self._state.update(status="running", phase="starting")
            if not self.live_enabled:
                return False
            if self.settings.get("LiveNotifyStart", False):
                self._events.append(dict(self._snapshot(), event="started"))
            self._thread = Thread(target=self._live_loop, daemon=True)
        try:
            self._thread.start()
            return True
        except Exception:
            self.last_delivery["live"] = "failed"
            return False

    def update(self, **values):
        allowed = {"phase", "current_item", "completed", "total", "transferred_bytes", "bytes_per_second", "metrics"}
        if set(values) - allowed:
            raise ValueError("Unknown progress field")
        for key, value in values.items():
            if key in ("phase", "current_item"):
                _text(value)
                if not isinstance(value, str):
                    raise ValueError("Progress labels must be strings")
            elif key == "metrics":
                if not isinstance(value, dict) or any(type(v) is not int or v < 0 for v in value.values()):
                    raise ValueError("metrics must contain measured nonnegative integer counters")
            elif value is not None:
                kinds = (int, float) if key == "bytes_per_second" else (int,)
                if type(value) not in kinds or not math.isfinite(value) or value < 0:
                    raise ValueError("Progress measurements must be nonnegative numbers or null")
        with self._lock:
            if self._finished:
                return False
            state = dict(self._state, **values)
            done, total = state["completed"], state["total"]
            if done is not None and total is not None and done > total:
                raise ValueError("completed cannot exceed total")
            state["progress_percent"] = round(100 * done / total, 2) if done is not None and total else None
            self._state, self._dirty = state, True
        self._wake.set()
        return True

    def append_stderr(self, output):
        output = _text(output)
        with self._lock:
            if self._finished:
                return False
            self._state["stderr"] = (self._state["stderr"] + output)[-4000:]
            self._dirty = True
        self._wake.set()
        return True

    def record_item(self, outcome, *, name, item_id=None, reason=""):
        """Record an actual item outcome separately from attempted/total progress."""
        groups = {"success": "successful_items", "failure": "failed_items", "skipped": "skipped_items"}
        name, reason = _text(name), _text(reason)
        identity = _text(item_id if item_id is not None else name)
        if outcome not in groups or not name.strip():
            raise ValueError("Item needs a name and success/failure/skipped outcome")
        row = dict(name=name, item_id=identity, reason=reason)
        with self._lock:
            if self._finished:
                return False
            for group in groups.values():
                self._state[group] = [item for item in self._state[group] if item["item_id"] != identity]
            self._state[groups[outcome]].append(row)
            self._dirty = True
        self._wake.set()
        return True

    def finish(self, exit_code, *, error="", stderr=None, warning=False, details=None):
        """Finalize live state and send completion JSON. Returns the completion payload.

        Reporting transport failures are available in last_delivery; they never
        replace the application's exit code. Repeated finish calls send nothing.
        """
        if type(exit_code) is not int or type(warning) is not bool:
            raise ValueError("exit_code must be an integer; warning must be boolean")
        error = _text(error)
        if stderr is not None:
            stderr = _text(stderr)[-4000:]
        with self._lock:
            if self._finished:
                return None
            success = exit_code == 0
            report = dict(schema_version=1, name=self.name, title=self.name, job=self.job,
                          status="success" if success else "failure", success=success, exit_code=exit_code,
                          error=error, stderr=self._state["stderr"] if stderr is None else stderr,
                          warning=warning, dry_run=self.dry_run, run_id=self.run_id,
                          timestamp=_now(), host=socket.gethostname())
            if details is not None:
                if not isinstance(details, dict) or set(details).intersection(report):
                    raise ValueError("details must be an object and cannot override report fields")
                report.update(details)
            _json(report)
            done, total = self._state["completed"], self._state["total"]
            incomplete = bool(self._state["failed_items"]) or (done is not None and total is not None and done < total)
            status = "interrupted" if exit_code in (130, 143) else "failure" if not success else "incomplete" if incomplete else "success"
            self._state.update(status=status, success=success, exit_code=exit_code, phase="finished",
                               error=error, stderr=report["stderr"], warning=warning, finished_at=_now())
            self._finished, self._dirty, self._ended = True, True, time.monotonic()
            self._result = self._snapshot()
            if self.settings.get("LiveNotifySuccess" if status == "success" else "LiveNotifyFailure", True):
                self._events.append(dict(self._result, event="completed" if status == "success" else "failed"))
        # Stop/cancel periodic sends before one bounded final state/result send.
        # A one-second join followed by cancellation could lose the last result.
        self.close()
        if self.live_enabled:
            messages = self._discovery() if self.settings.get("LiveMQTTDiscovery", True) else []
            messages.extend([(self.state_topic, self._result, False), (self.result_topic, self._result, True)])
            messages.extend((self.events_topic, event, False) for event in self._events)
            self._events = []
            self.last_delivery["live"] = "sent" if self._send(messages, cancel=None) else "failed"
        if self.completion_enabled and (not success or self.settings.get("SendMQTTOnSuccess", True)):
            self.last_delivery["completion"] = "sent" if self._send([(self.topic, report, False)], cancel=None) else "failed"
        return report

    def close(self):
        """Stop live updates without inventing a successful outcome."""
        self._stop.set()
        self._wake.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _discovery(self):
        fields = [("status", "Status", None), ("progress_percent", "Progress", "%"),
                  ("completed", "Completed items", None), ("total", "Total items", None),
                  ("current_item", "Current item", None), ("phase", "Phase", None),
                  ("runtime_seconds", "Runtime", "s"), ("transferred_bytes", "Transferred", "B"),
                  ("bytes_per_second", "Transfer speed", "B/s"), ("last_heartbeat", "Last heartbeat", None),
                  ("last_result", "Last result", None), ("successful_item_count", "Successful items", None),
                  ("failed_item_count", "Failed items", None), ("skipped_item_count", "Skipped items", None)]
        messages = []
        for field, label, unit in fields:
            result = field == "last_result"
            identity = f"job_live_{self.device_id}_{field}"
            topic = self.result_topic if result else self.state_topic
            template = '{{ value_json.' + ('status' if result else field) + ' }}'
            if field in ("phase", "current_item"):
                template = '{{ value_json.' + field + '[:255] }}'
            data = dict(name=label, unique_id=identity, default_entity_id="sensor." + identity,
                        state_topic=topic, value_template=template,
                        device=dict(identifiers=["job_live_" + self.device_id], name=self.name,
                                    manufacturer=self.manufacturer, model="Live job preview"))
            if not result:
                data["expire_after"] = self.expire_after
            if unit:
                data["unit_of_measurement"] = unit
            if field in ("progress_percent", "completed", "total", "runtime_seconds", "transferred_bytes",
                         "bytes_per_second", "successful_item_count", "failed_item_count", "skipped_item_count"):
                data["state_class"] = "measurement"
                data["value_template"] = "{{ value_json." + field + " if value_json." + field + " is not none else 'unknown' }}"
            if field == "last_heartbeat":
                data["device_class"] = "timestamp"
            if field in ("status", "last_result"):
                data.update(json_attributes_topic=topic,
                            json_attributes_template='{{ dict(value_json, live_preview_role="' + ('last_result' if result else 'status') + '") | tojson }}')
            messages.append((f"homeassistant/sensor/{identity}/config", data, True))
        return messages

    def _live_loop(self):
        next_allowed = heartbeat_due = discovery_due = 0
        try:
            while not self._stop.is_set():
                with self._lock:
                    due = 0 if self._finished else next_allowed if self._dirty else heartbeat_due
                delay = max(0, due - time.monotonic())
                if delay:
                    self._wake.wait(delay)
                    self._wake.clear()
                    continue
                with self._lock:
                    if self._finished:
                        return  # finish() sends the final state/result synchronously.
                    self._dirty = False
                    finished, state = self._finished, self._snapshot()
                    events, self._events = self._events, []
                discover = self.settings.get("LiveMQTTDiscovery", True) and time.monotonic() >= discovery_due
                messages = self._discovery() if discover else []
                messages.append((self.state_topic, state, False))
                if finished:
                    messages.append((self.result_topic, state, True))
                messages.extend((self.events_topic, event, False) for event in events)
                ok = self._send(messages, cancel=self._stop)
                self.last_delivery["live"] = "sent" if ok else "failed"
                if not ok:
                    with self._lock:
                        self._events = events + self._events
                if ok and discover:
                    discovery_due = time.monotonic() + 300
                if finished:
                    return
                next_allowed, heartbeat_due = time.monotonic() + 1, time.monotonic() + self.heartbeat
        except Exception:
            self.last_delivery["live"] = "failed"

    def _send(self, messages, cancel):
        """Killable worker: credentials on stdin, five-second deadline, no raw errors."""
        process = None
        try:
            if cancel and cancel.is_set():
                return False
            request = _json(dict(broker=self._broker, messages=messages, completion_topic=self.topic))
            command = [sys.executable, WORKER_FLAG] if getattr(sys, "frozen", False) else [sys.executable, "-B", str(Path(__file__).resolve()), WORKER_FLAG]
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
            deadline, first = time.monotonic() + 5, True
            while time.monotonic() < deadline and not (cancel and cancel.is_set()):
                try:
                    process.communicate(input=request if first else None, timeout=0.1)
                    return process.returncode == 0
                except subprocess.TimeoutExpired:
                    first = False
        except Exception:
            pass
        finally:
            if process is not None and process.poll() is None:
                try:
                    process.kill()
                    process.communicate(timeout=1)
                except (OSError, subprocess.TimeoutExpired):
                    pass
        return False


def run_worker_if_requested():
    """Call before parsing the parent application's CLI arguments."""
    if sys.argv[1:] != [WORKER_FLAG]:
        return False
    try:
        from paho.mqtt.publish import multiple
        request = json.load(sys.stdin)
        broker = request["broker"]
        messages = [dict(topic=topic, payload=_json(payload), retain=retain,
                         qos=broker.get("qos", 0) if topic == request["completion_topic"] else 1)
                    for topic, payload, retain in request["messages"]]
        auth = dict(username=broker["username"], password=broker["password"]) if broker["username"] else None
        context = ssl.create_default_context(cafile=broker.get("ca_file")) if broker["tls"] else None
        if context and broker.get("cert_file"):
            context.load_cert_chain(broker["cert_file"], broker["key_file"])
        multiple(messages, hostname=broker["host"], port=broker["port"], auth=auth, tls=context)
    except Exception:
        raise SystemExit(1) from None
    raise SystemExit(0)


if __name__ == "__main__":
    run_worker_if_requested()
    print(__doc__)
