"""Optional final MQTT reports matching the supplied Home Assistant JSON contract."""
import datetime
import importlib
import json
import logging
from pathlib import Path
import ssl
import subprocess
import sys
import uuid
import socket
if __package__:
    from .mqtt_reporting import MQTTReporter, _ACTIVE
else:
    # Source worker is executed directly by absolute filename; its sibling lives
    # beside it. Frozen/public application imports use the package branch.
    from mqtt_reporting import MQTTReporter, _ACTIVE


DEFAULTS = {
    'port': 1883,
    'title': 'SnapBeforeWatchTower',
    'username': None,
    'password': None,
    'qos': 0,
    'tls': False,
    'ca_file': None,
    'cert_file': None,
    'key_file': None,
    'timeout': 15,
    'on_success': False,
}
REPORTING_KEYS = {
    'SendMQTTOnSuccess', 'MQTT_JSON_Status', 'mqtt_json_topic', 'broker_address',
    'broker_port', 'mqtt_username', 'mqtt_password', 'MQTTTLS',
    'LiveMQTTEnabled', 'LiveMQTTDiscovery', 'LiveBackupName', 'LiveManufacturer',
    'LiveHeartbeatSeconds', 'LiveNotifyStart', 'LiveNotifySuccess', 'LiveNotifyFailure', 'LiveDeviceID',
}
SUPPORTED_KEYS = REPORTING_KEYS | {'qos', 'ca_file', 'cert_file', 'key_file', 'timeout'}
REMOVED_KEYS = {'enabled': 'MQTT_JSON_Status', 'on_success': 'SendMQTTOnSuccess',
                'host': 'broker_address', 'port': 'broker_port', 'topic': 'mqtt_json_topic',
                'username': 'mqtt_username', 'password': 'mqtt_password', 'tls': 'MQTTTLS',
                'title': '[report].name or LiveBackupName'}
OPTIONAL_STRING_KEYS = ['username', 'password', 'ca_file', 'cert_file', 'key_file']


class MQTTPublishError(RuntimeError):
    """Safe parent-side MQTT worker failure with a non-secret reason class."""

    def __init__(self, reason='UnknownError'):
        self.reason = reason if isinstance(reason, str) and reason else 'UnknownError'
        super().__init__(f'MQTT publish worker failed ({self.reason})')


def validate_config(supplied, base_dir, dry_run=False, config_path=None):
    """Validate the TOML [mqtt] settings; disabled MQTT needs no dependency or broker details."""
    if not isinstance(supplied, dict):
        raise ValueError('MQTT configuration must be a TOML table')
    removed = set(supplied) & REMOVED_KEYS.keys()
    if removed:
        guidance = '; '.join(f'{key} -> {REMOVED_KEYS[key]}' for key in sorted(removed))
        raise ValueError(f'[mqtt] removed duplicate option(s); use {guidance}')
    unsupported = set(supplied) - SUPPORTED_KEYS
    if unsupported:
        names = ', '.join(sorted(unsupported))
        raise ValueError(f'MQTT configuration contains unsupported key(s): {names}')
    boolean_keys = {'MQTT_JSON_Status', 'SendMQTTOnSuccess', 'LiveMQTTEnabled',
                    'LiveMQTTDiscovery', 'LiveNotifyStart', 'LiveNotifySuccess', 'LiveNotifyFailure', 'MQTTTLS'}
    for key in boolean_keys & supplied.keys():
        if type(supplied[key]) is not bool:
            raise ValueError(f'MQTT {key} must be true or false')
    completion_enabled = supplied.get('MQTT_JSON_Status', False)
    live_enabled = supplied.get('LiveMQTTEnabled', False)
    if not completion_enabled and not live_enabled:
        return None

    normalized = {key: value for key, value in supplied.items() if key not in REPORTING_KEYS}
    worker_fields = {'broker_address': 'host', 'broker_port': 'port', 'mqtt_json_topic': 'topic',
               'mqtt_username': 'username', 'mqtt_password': 'password', 'MQTTTLS': 'tls',
               'SendMQTTOnSuccess': 'on_success'}
    for modern, original in worker_fields.items():
        if modern in supplied:
            normalized[original] = supplied[modern]
    # Live-only configurations do not need a completion topic.
    normalized.setdefault('topic', 'homeassistant/SnapBeforeWatchTower/example-host/status')
    normalized.setdefault('on_success', True)
    config = dict(DEFAULTS, **normalized)
    for key in ['host', 'topic', 'title']:
        if not isinstance(config.get(key), str) or not config[key].strip() or '\0' in config[key]:
            raise ValueError(f'MQTT {REMOVED_KEYS.get(key, key)} must be a nonempty string without NUL')
        config[key] = config[key].strip()

    if any(char in config['topic'] for char in '+#') or len(config['topic'].encode('utf-8')) > 65535:
        raise ValueError('MQTT mqtt_json_topic must be a publish topic without wildcards, at most 65535 UTF-8 bytes')

    for key, low, high in [('port', 1, 65535), ('qos', 0, 2), ('timeout', 1, 120)]:
        if type(config[key]) is not int or not low <= config[key] <= high:
            raise ValueError(f'MQTT {REMOVED_KEYS.get(key, key)} must be an integer from {low} to {high}')
    if type(config['tls']) is not bool:
        raise ValueError('MQTT MQTTTLS must be true or false')
    if type(config['on_success']) is not bool:
        raise ValueError('MQTT SendMQTTOnSuccess must be true or false')
    if config['tls'] and 'port' not in normalized:
        config['port'] = 8883

    for key in OPTIONAL_STRING_KEYS:
        value = config[key]
        if value == '':
            config[key] = None
            continue
        if value is not None and (not isinstance(value, str) or not value.strip() or '\0' in value):
            raise ValueError(f'MQTT {REMOVED_KEYS.get(key, key)} must be an empty string or a nonempty string without NUL')
        if isinstance(config[key], str):
            config[key] = config[key].strip()

    if config['password'] and not config['username']:
        raise ValueError('MQTT mqtt_password requires mqtt_username')
    if bool(config['cert_file']) != bool(config['key_file']):
        raise ValueError('MQTT cert_file and key_file must be supplied together')

    base_dir = Path(base_dir).resolve()
    for key in ['ca_file', 'cert_file', 'key_file']:
        if config[key]:
            if not config['tls']:
                raise ValueError(f'MQTT {key} requires MQTTTLS=true')
            resolved = (base_dir / config[key]).resolve()
            if not resolved.is_file():
                raise ValueError(f'MQTT {key} does not point to a file')
            config[key] = str(resolved)

    try:
        importlib.import_module('paho.mqtt.publish')
    except ImportError as exc:
        raise ValueError('MQTT requires paho-mqtt: install requirements-mqtt.txt with this Python interpreter') from exc
    config['_completion_enabled'] = completion_enabled
    config['_config_path'] = str(Path(config_path or Path(base_dir) / 'config.toml').resolve())
    for key in REPORTING_KEYS - worker_fields.keys():
        if key in supplied:
            config[key] = supplied[key]
    # New credentials are literal TOML strings; do not strip meaningful password spaces.
    for modern, original in [('mqtt_username', 'username'), ('mqtt_password', 'password')]:
        if modern in supplied:
            config[original] = supplied[modern] or None
    live_settings = dict(config, MQTT_JSON_Status=False, broker_address=config['host'],
                         broker_port=config['port'], mqtt_username=config['username'] or '',
                         mqtt_password=config['password'] or '', MQTTTLS=config['tls'])
    MQTTReporter(live_settings, job='SnapBeforeWatchTower', config_path=config['_config_path'])
    return config


class ErrorCapture(logging.Handler):
    """Keep bounded, current-run error details without rereading potentially stale logs."""

    def __init__(self):
        super().__init__(logging.ERROR)
        self.text = ''

    def emit(self, record):
        message = record.getMessage().strip()
        if message and message.strip('- \n\r\t'):
            self.text = (self.text + '\n' + message).strip()[-4096:]


def build_payload(config, command, version, exc, errors, run_id, dry_run=False, comment="", name="", stderr=""):
    """Describe the actual process outcome, retaining nonfatal errors as warnings."""
    code = 0
    if isinstance(exc, SystemExit):
        code = int(exc.code) if isinstance(exc.code, int) else (0 if exc.code is None else 1)
    elif isinstance(exc, KeyboardInterrupt):
        code = 130
    elif exc is not None:
        code = 1
    failure = code != 0
    detail = stderr.decode('utf-8', errors='replace') if isinstance(stderr, bytes) else stderr
    # Direct callers may supply an exception without the command observer.
    command_stderr = getattr(exc, 'stderr', '') if exc else ''
    if not detail and isinstance(command_stderr, (str, bytes)):
        detail = command_stderr.decode('utf-8', errors='replace') if isinstance(command_stderr, bytes) else command_stderr
    detail = detail[-4000:]
    friendly = name or config.get('LiveBackupName') or config['title']
    error = ''
    if failure:
        error = (errors or f'Process exited with code {code}') if isinstance(exc, SystemExit) else (str(exc) or type(exc).__name__)
    return {
        'status': 'failure' if failure else 'success',
        'title': friendly,
        'name': friendly,
        'job': 'SnapBeforeWatchTower',
        'success': code == 0,
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'host': socket.gethostname(),
        'comment': comment,
        'exit_code': code,
        'warning': bool(errors) and not failure,
        'warning_detail': errors[-4000:] if not failure else '',
        'error': error[-4096:],
        'stderr': detail,
        'command': command,
        'version': version,
        'run_id': run_id,
        'finished_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'dry_run': bool(dry_run),
    }


def publish_report(config, payload):
    """Use a killable worker to bound DNS/connect/publish time; keep credentials off argv."""
    if getattr(sys, 'frozen', False):
        # A frozen executable cannot launch mqtt_report.py directly because source
        # modules live inside the bundle. Re-execute the app with a private worker
        # switch instead. Configuration and credentials stay on stdin, not argv.
        worker_command = [sys.executable, '--mqtt-publish-worker']
    else:
        worker_command = [sys.executable, '-B', str(Path(__file__).resolve()), '--publish']
    result = subprocess.run(
        worker_command,
        input=json.dumps({'config': config, 'payload': payload}),
        text=True, capture_output=True, timeout=config['timeout'],
    )
    if result.returncode != 0:
        # The worker writes only an exception class name, never exception text or credentials.
        reason = (result.stderr or '').strip()
        if not reason.replace('_', '').isalnum() or len(reason) > 80:
            reason = 'UnknownError'
        raise MQTTPublishError(reason or 'UnknownError')


class RunReporter:
    """Observe the existing process result; report failures without replacing it."""

    def __init__(self, config, command, version, dry_run=False, comment="", name=""):
        self.config, self.command, self.version = config, command, version
        self.dry_run, self.comment, self.name = dry_run, comment, name
        self.run_id = str(uuid.uuid4())
        self.errors, self.error_logger = ErrorCapture(), None
        self.stderr, self.child_exit_code, self.child_command = '', None, ''
        self.live, self._token = None, None
        self.items, self.outcomes, self.current, self.completed = [], set(), None, 0
        self.failed_datasets = {}
        self.metrics = dict(snapshots_created=0, snapshots_deleted=0,
                            snapshot_creations_planned=0, snapshot_deletions_planned=0)

    def __enter__(self):
        self._token = _ACTIVE.set(self)
        if self.config and self.config.get('LiveMQTTEnabled', False):
            try:
                config = self.config
                settings = dict(config, MQTT_JSON_Status=False, broker_address=config['host'],
                                broker_port=config['port'], mqtt_username=config.get('username') or '',
                                mqtt_password=config.get('password') or '', MQTTTLS=config.get('tls', False))
                self.live = MQTTReporter(settings, job='SnapBeforeWatchTower',
                    name=self.name or config.get('LiveBackupName') or config['title'], dry_run=self.dry_run,
                    job_type='zfs_snapshot_retention', item_unit='datasets', config_path=config.get('_config_path'))
                self.live.run_id = self.run_id
                self.live.start()
                self.update(metrics=self.metrics)
            except Exception:
                logging.getLogger('SnapBeforeWatchTower').error('MQTT live startup failed; job continues')
                self.live = None
        return self

    def attach(self, error_logger):
        self.error_logger = error_logger
        error_logger.addHandler(self.errors)

    def update(self, **values):
        """Forward measured progress; an observer failure cannot change the job."""
        if self.live:
            try:
                self.live.update(**values)
            except Exception:
                logging.getLogger('SnapBeforeWatchTower').error('MQTT live progress update failed')

    def plan(self, datasets):
        self.items = list(datasets)
        self.update(total=len(self.items), completed=0, phase='datasets')

    def begin_item(self, index, dataset):
        self.current = index
        self.update(current_item=dataset, phase='snapshot_create' if self.command == 'create' else 'snapshot_retention')

    def end_item(self, index, dataset, exc=None):
        if index in self.outcomes:
            return
        self.outcomes.add(index)
        self.completed += 1
        reason = ''
        if exc is not None:
            reason = getattr(exc, 'stderr', '') or ''
            if isinstance(reason, bytes):
                reason = reason.decode('utf-8', errors='replace')
            reason = (reason.strip() if isinstance(reason, str) else '') or str(exc) or type(exc).__name__
            reason = reason[-4000:]
            self.failed_datasets[index] = dict(source=dataset, item_id=str(index), reason=reason)
        if self.live:
            try:
                self.live.record_item('failure' if exc is not None else 'success', name=dataset,
                                      item_id=str(index), reason=reason)
            except Exception:
                logging.getLogger('SnapBeforeWatchTower').error('MQTT live item update failed; job continues')
        self.current = None
        self.update(completed=self.completed)

    def capture_command(self, command, stderr, returncode, *, planned=False):
        """Keep real stderr in order and count successful/planned snapshot actions."""
        if isinstance(stderr, bytes):
            stderr = stderr.decode('utf-8', errors='replace')
        if isinstance(stderr, str) and stderr:
            self.stderr = (self.stderr + stderr)[-4000:]
            if self.live:
                self.live.append_stderr(stderr)
        if type(returncode) is int and returncode != 0:
            self.child_exit_code, self.child_command = returncode, ' '.join(command)
        key = None
        if command[:2] == ['zfs', 'snapshot'] and returncode == 0:
            key = 'snapshot_creations_planned' if planned else 'snapshots_created'
        elif command[:2] == ['zfs', 'destroy'] and returncode == 0:
            key = 'snapshot_deletions_planned' if planned else 'snapshots_deleted'
        if key:
            self.metrics[key] += 1
            self.update(metrics=dict(self.metrics))

    def completion_payload(self, exc):
        """One standalone completion object, with real snapshot-job dataset details."""
        payload = build_payload(self.config, self.command, self.version, exc, self.errors.text,
            self.run_id, dry_run=self.dry_run, comment=self.comment, name=self.name, stderr=self.stderr)
        if self.child_exit_code is not None:
            payload.update(child_exit_code=self.child_exit_code, child_command=self.child_command)
        payload['planned_datasets'] = [dict(source=source, item_id=str(index)) for index, source in enumerate(self.items)]
        payload['failed_datasets'] = [self.failed_datasets[index] for index in sorted(self.failed_datasets)]
        payload['skipped_datasets'] = [dict(source=source, item_id=str(index),
            reason='Not attempted: job stopped before this dataset') for index, source in enumerate(self.items)
            if index not in self.outcomes]
        return payload

    def __exit__(self, exc_type, exc, traceback):
        if self._token is not None:
            _ACTIVE.reset(self._token)
        if self.error_logger is not None:
            self.error_logger.removeHandler(self.errors)
        if not self.config:
            return False
        logger = logging.getLogger('SnapBeforeWatchTower')
        try:
            if exc is not None and self.current is not None:
                self.end_item(self.current, self.items[self.current], exc)
            payload = self.completion_payload(exc)
            if self.live:
                for index, dataset in enumerate(self.items):
                    if index not in self.outcomes:
                        self.live.record_item('skipped', name=dataset, item_id=str(index),
                                              reason='Not attempted: job stopped before this dataset')
                self.live.finish(payload['exit_code'], error=payload['error'], stderr=payload['stderr'],
                                 warning=payload['warning'], details={'command': self.command, 'version': self.version})
                if self.live.last_delivery['live'] == 'failed':
                    logger.error('MQTT live report delivery failed; job outcome preserved')
        except Exception:
            logger.error('MQTT live finalization failed; job outcome preserved')
        finally:
            if self.live:
                try:
                    self.live.close()
                except Exception:
                    logger.error('MQTT live shutdown failed; job outcome preserved')
        # Completion is independent from live transport/finalization.
        try:
            payload = self.completion_payload(exc)
            if not self.config.get('_completion_enabled', False):
                return False
            if payload['status'] == 'success' and not self.config['on_success']:
                logger.info('%sMQTT success report suppressed because SendMQTTOnSuccess=false', '[DRY-RUN] ' if self.dry_run else '')
                return False
            logger.info('MQTT final %s report enabled; attempting publish%s', payload['status'], ' [DRY-RUN]' if self.dry_run else '')
            publish_report(self.config, payload)
            logger.info('MQTT final %s report published%s', payload['status'], ' [DRY-RUN]' if self.dry_run else '')
        except subprocess.TimeoutExpired:
            logger.error('MQTT report timed out; delivery is unconfirmed')
        except MQTTPublishError as publish_error:
            logger.error('MQTT report failed in worker (%s); check broker, authentication, TLS, dependency, and topic permissions', publish_error.reason)
        except Exception:
            logger.error('MQTT report failed; check broker, authentication, TLS, dependency, and topic permissions')
        return False


def worker():
    """Publish non-retained JSON with Paho; parent enforces the complete time budget."""
    from paho.mqtt import publish

    request = json.load(sys.stdin)
    config = request['config']
    auth = None
    if config['username']:
        auth = {'username': config['username']}
        if config['password']:
            auth['password'] = config['password']
    context = None
    if config['tls']:
        context = ssl.create_default_context(cafile=config['ca_file'])
        if config['cert_file']:
            context.load_cert_chain(config['cert_file'], config['key_file'])
    publish.single(
        config['topic'], payload=json.dumps(request['payload'], ensure_ascii=True),
        hostname=config['host'], port=config['port'], qos=config['qos'], retain=False,
        auth=auth, tls=context,
    )


if __name__ == '__main__':
    if sys.argv[1:] != ['--publish']:
        sys.exit('Internal MQTT worker; use SnapBeforeWatchTower.py -c CONFIG')
    try:
        worker()
    except Exception as exc:
        # Only expose the exception class to the parent. Never print exception text,
        # broker credentials, or the JSON request.
        sys.stderr.write(type(exc).__name__)
        sys.exit(1)
