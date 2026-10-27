"""MQTT contract and lifecycle tests; no broker, Paho installation, or network needed."""
import io
import json
import logging
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import Mock, patch

from test_app import app, temporary_directory, ROOT
from modules import mqtt_report as mqtt


class MQTTTests(unittest.TestCase):
    """Verify TOML-sourced MQTT validation, non-retained publishing, and safe run integration."""

    def setUp(self):
        self.config = dict(mqtt.DEFAULTS, host='broker.example', topic='test/snap/status', _completion_enabled=True)
        self.dependency = patch.object(mqtt.importlib, 'import_module', return_value=Mock())
        self.dependency.start()
        self.addCleanup(self.dependency.stop)

    def validate(self, value, dry_run=True, enabled=True):
        if isinstance(value, dict):
            value = dict(value)
            value.setdefault('MQTT_JSON_Status', enabled)
        with temporary_directory() as folder:
            return mqtt.validate_config(value, Path(folder), dry_run=dry_run)

    def test_config_defaults_tls_port_and_disabled_mode(self):
        result = self.validate({'broker_address': 'broker', 'mqtt_json_topic': 'test/status'})
        self.assertEqual(result['host'], 'broker')
        self.assertEqual(result['topic'], 'test/status')
        self.assertEqual(result['port'], 1883)
        self.assertTrue(result['on_success'])
        self.assertTrue(result['_completion_enabled'])
        result = self.validate({'broker_address': 'broker', 'mqtt_json_topic': 'test/status', 'MQTTTLS': True})
        self.assertEqual(result['port'], 8883)
        self.assertIsNone(self.validate({}, enabled=False))

    def test_invalid_config_stops_early(self):
        for update in [
            {'mqtt_json_topic': 'a/#'}, {'broker_port': True}, {'qos': 3}, {'timeout': 0}, {'timeout': 121},
            {'MQTTTLS': 'false'}, {'SendMQTTOnSuccess': 'true'}, {'retain': True}, {'mqtt_username': 12}, {'password_env': 'TEST_PASSWORD'},
            {'mqtt_password': 12}, {'cert_file': 'a.pem'}, {'ca_file': 'a.pem'}, {'mqtt_json_topic': ''}, {'broker_address': ''},
        ]:
            with self.subTest(update=update), self.assertRaises(ValueError):
                value = dict(broker_address='broker', mqtt_json_topic='test/status')
                value.update(update)
                self.validate(value)
        with self.assertRaises(ValueError):
            self.validate([])
        with self.assertRaisesRegex(ValueError, 'unsupported key'):
            self.validate({'password_env': 'OLD_ENV_NAME'}, enabled=False)

    def test_password_optional_strings_and_dependency_validation(self):
        value = dict(broker_address='broker', mqtt_username='user', mqtt_password='plain-secret')
        self.assertEqual(self.validate(value)['password'], 'plain-secret')
        anonymous = self.validate(dict(broker_address='broker', mqtt_username='', mqtt_password='', ca_file='', cert_file='', key_file=''))
        self.assertIsNone(anonymous['username'])
        self.assertIsNone(anonymous['password'])
        with self.assertRaisesRegex(ValueError, 'mqtt_password requires mqtt_username'):
            self.validate(dict(broker_address='broker', mqtt_password='plain-secret'))
        for dry_run in [False, True]:
            with patch.object(mqtt.importlib, 'import_module', side_effect=ImportError('missing')):
                with self.assertRaisesRegex(ValueError, 'requirements-mqtt.txt'):
                    self.validate(value, dry_run=dry_run)

    def test_tls_relative_paths_resolve_from_toml_directory(self):
        with temporary_directory() as folder:
            base = Path(folder)
            for name in ['ca.pem', 'client.pem', 'client.key']:
                (base / name).write_text('test', encoding='utf-8')
            result = mqtt.validate_config(
                dict(MQTT_JSON_Status=True, broker_address='broker', MQTTTLS=True, ca_file='ca.pem', cert_file='client.pem', key_file='client.key'),
                base, dry_run=True,
            )
            self.assertEqual(result['ca_file'], str((base / 'ca.pem').resolve()))
            self.assertEqual(result['cert_file'], str((base / 'client.pem').resolve()))
            self.assertEqual(result['key_file'], str((base / 'client.key').resolve()))

    def test_payload_success_warning_and_failure_contract(self):
        for exc, errors, status, code, warning in [
            (None, '', 'success', 0, False),
            (None, 'Digest collection failed', 'success', 0, True),
            (RuntimeError('Snapshot failed'), 'zfs failure', 'failure', 1, False),
            (SystemExit(1), 'Must run as root', 'failure', 1, False),
            (KeyboardInterrupt(), '', 'failure', 130, False),
        ]:
            payload = mqtt.build_payload(self.config, 'create', app.__version__, exc, errors, 'run-123')
            self.assertEqual((payload['status'], payload['exit_code'], payload['warning']), (status, code, warning))
            for key in ['title', 'name', 'job', 'error', 'stderr', 'run_id', 'finished_at']:
                self.assertIsInstance(payload[key], str)
            self.assertEqual(json.loads(json.dumps(payload)), payload)
            self.assertEqual(payload['title'], self.config['title'])
            self.assertFalse(payload['dry_run'])
            if status == 'failure':
                self.assertTrue(payload['error'])

    def test_missing_dataset_failure_keeps_existing_failure_contract_and_reason(self):
        exc = app.MissingDatasetsError(['tank/missing', 'tank/also-missing'])
        payload = mqtt.build_payload(self.config, 'create', app.__version__, exc, 'missing dataset detail', 'run-missing', stderr='actual missing dataset stderr')
        self.assertEqual(payload['status'], 'failure')
        self.assertEqual(payload['exit_code'], 1)
        self.assertFalse(payload['warning'])
        self.assertIn('dataset does not exist', payload['error'])
        self.assertIn('tank/missing', payload['error'])
        self.assertIn('tank/also-missing', payload['error'])
        self.assertEqual(payload['stderr'], 'actual missing dataset stderr')

    def test_capture_is_bounded_and_ignores_separators(self):
        capture = mqtt.ErrorCapture()
        capture.emit(logging.LogRecord('test', logging.ERROR, '', 0, '\n----\n', (), None))
        self.assertEqual(capture.text, '')
        capture.emit(logging.LogRecord('test', logging.ERROR, '', 0, 'x' * 8000, (), None))
        self.assertEqual(len(capture.text), 4096)

    def test_worker_publish_uses_auth_tls_and_no_retain(self):
        publish = Mock()
        paho = types.ModuleType('paho')
        package = types.ModuleType('paho.mqtt')
        package.publish = publish
        config = dict(self.config, username='user', password='secret', tls=True)
        payload = mqtt.build_payload(config, 'create', app.__version__, None, '', 'run-1')
        context = Mock()
        with patch.dict(sys.modules, {'paho': paho, 'paho.mqtt': package}), \
             patch.object(sys, 'stdin', io.StringIO(json.dumps({'config': config, 'payload': payload}))), \
             patch.object(mqtt.ssl, 'create_default_context', return_value=context):
            mqtt.worker()
        publish.single.assert_called_once()
        kwargs = publish.single.call_args.kwargs
        self.assertFalse(kwargs['retain'])
        self.assertEqual(kwargs['auth'], {'username': 'user', 'password': 'secret'})
        self.assertIs(kwargs['tls'], context)
        self.assertEqual(json.loads(kwargs['payload']), payload)

    def test_publisher_timeout_stdin_and_failure(self):
        with patch.object(mqtt.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')) as run:
            mqtt.publish_report(self.config, {'status': 'success'})
        self.assertEqual(run.call_args.kwargs['timeout'], 15)
        self.assertEqual(json.loads(run.call_args.kwargs['input'])['payload']['status'], 'success')
        self.assertNotIn('broker.example', ' '.join(run.call_args.args[0]))
        with patch.object(mqtt.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'ConnectionRefusedError')):
            with self.assertRaises(mqtt.MQTTPublishError) as exc:
                mqtt.publish_report(self.config, {})
        self.assertEqual(exc.exception.reason, 'ConnectionRefusedError')
        self.assertNotIn('broker.example', str(exc.exception))

        with patch.object(mqtt.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'secret details: password=oops')):
            with self.assertRaises(mqtt.MQTTPublishError) as exc:
                mqtt.publish_report(self.config, {})
        self.assertEqual(exc.exception.reason, 'UnknownError')
        self.assertNotIn('password', str(exc.exception))

    def test_frozen_publish_reexecutes_binary_worker_without_credentials_on_argv(self):
        with patch.object(mqtt.sys, 'frozen', True, create=True), \
             patch.object(mqtt.sys, 'executable', '/opt/sbwt/dist/SnapBeforeWatchTower'), \
             patch.object(mqtt.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')) as run:
            mqtt.publish_report(self.config, {'status': 'success'})
        self.assertEqual(run.call_args.args[0], ['/opt/sbwt/dist/SnapBeforeWatchTower', '--mqtt-publish-worker'])
        self.assertNotIn('broker.example', ' '.join(run.call_args.args[0]))
        request = json.loads(run.call_args.kwargs['input'])
        self.assertEqual(request['config']['host'], 'broker.example')

    def test_success_reporting_respects_on_success_in_real_and_dry_run(self):
        with patch.object(mqtt, 'publish_report') as publish:
            with mqtt.RunReporter(None, 'create', app.__version__):
                pass
            for dry_run in [False, True]:
                with mqtt.RunReporter(self.config, 'create', app.__version__, dry_run=dry_run):
                    pass
        publish.assert_not_called()

        enabled = dict(self.config, on_success=True)
        for dry_run in [False, True]:
            with self.subTest(dry_run=dry_run), patch.object(mqtt, 'publish_report') as publish:
                with mqtt.RunReporter(enabled, 'create', app.__version__, dry_run=dry_run):
                    pass
                publish.assert_called_once()
                payload = publish.call_args.args[1]
                self.assertEqual(payload['status'], 'success')
                self.assertIs(payload['dry_run'], dry_run)

    def test_failure_reporting_ignores_on_success_in_real_and_dry_run(self):
        for dry_run in [False, True]:
            with self.subTest(dry_run=dry_run), patch.object(mqtt, 'publish_report') as publish:
                with self.assertRaisesRegex(RuntimeError, 'original failure'):
                    with mqtt.RunReporter(self.config, 'create', app.__version__, dry_run=dry_run):
                        raise RuntimeError('original failure')
                publish.assert_called_once()
                payload = publish.call_args.args[1]
                self.assertEqual(payload['status'], 'failure')
                self.assertIs(payload['dry_run'], dry_run)

    def test_reporter_publishes_once_and_does_not_mask_failure(self):
        error_logger = logging.Logger('isolated')
        with patch.object(mqtt, 'publish_report') as publish:
            with self.assertRaisesRegex(RuntimeError, 'original failure'):
                with mqtt.RunReporter(self.config, 'delete', app.__version__) as reporter:
                    reporter.attach(error_logger)
                    error_logger.error('Captured detail')
                    raise RuntimeError('original failure')
        publish.assert_called_once()
        self.assertEqual(publish.call_args.args[1]['status'], 'failure')
        self.assertEqual(publish.call_args.args[1]['stderr'], '')  # Logger text is not child stderr.
        self.assertIn('original failure', publish.call_args.args[1]['error'])
        self.assertEqual(error_logger.handlers, [])

    def test_worker_failure_reason_is_logged_without_exception_text(self):
        failure = mqtt.MQTTPublishError('ConnectionRefusedError')
        with patch.object(mqtt, 'publish_report', side_effect=failure), \
             self.assertLogs('SnapBeforeWatchTower', level='ERROR') as logs:
            with mqtt.RunReporter(dict(self.config, on_success=True), 'create', app.__version__, dry_run=True):
                pass
        combined = '\n'.join(logs.output)
        self.assertIn('ConnectionRefusedError', combined)
        self.assertNotIn('broker.example', combined)

    def test_publish_errors_preserve_original_outcome(self):
        for failure in [RuntimeError('secret'), subprocess.TimeoutExpired('worker', 15)]:
            with patch.object(mqtt, 'publish_report', side_effect=failure), self.assertLogs('SnapBeforeWatchTower', level='ERROR') as logs:
                with mqtt.RunReporter(dict(self.config, on_success=True), 'create', app.__version__):
                    pass
            self.assertNotIn('secret', '\n'.join(logs.output))

    def test_payload_friendly_name_title_and_stable_job_with_legacy_fallback(self):
        for exc in [None, RuntimeError('failed')]:
            for name in ['', 'Nightly æ backup']:
                with self.subTest(exc=exc, name=name):
                    payload = mqtt.build_payload(self.config, 'create', app.__version__, exc, '', 'run-name',
                                                 name=name, comment='Details')
                    self.assertEqual(payload['title'], name or self.config['title'])
                    self.assertEqual(payload['name'], name or self.config['title'])
                    self.assertEqual(payload['job'], 'SnapBeforeWatchTower')
                    self.assertEqual(payload['comment'], 'Details')

    def test_reporter_sends_run_name_for_real_and_dry_success_and_failure(self):
        for dry_run in [False, True]:
            for failed in [False, True]:
                with self.subTest(dry_run=dry_run, failed=failed), patch.object(mqtt, 'publish_report') as publish:
                    reporter = mqtt.RunReporter(dict(self.config, on_success=True), 'create', app.__version__,
                                                dry_run=dry_run, name='Nightly backup', comment='Details')
                    if failed:
                        with self.assertRaises(RuntimeError):
                            with reporter:
                                raise RuntimeError('failed')
                    else:
                        with reporter:
                            pass
                    publish.assert_called_once()
                    payload = publish.call_args.args[1]
                    self.assertEqual(payload['name'], 'Nightly backup')
                    self.assertEqual(payload['job'], 'SnapBeforeWatchTower')
                    self.assertEqual(payload['title'], 'Nightly backup')
                    self.assertEqual(payload['status'], 'failure' if failed else 'success')
                    self.assertEqual(payload['dry_run'], dry_run)

    def test_comment_newlines_survive_payload_json_and_worker_publish(self):
        comment = 'First line\n\nSecond line\n'
        payload = mqtt.build_payload(self.config, 'create', app.__version__, None, '', 'run-comment', comment=comment, name='Nightly æ backup')
        self.assertEqual(json.loads(json.dumps(payload))['comment'], comment)
        publish = Mock()
        paho = types.ModuleType('paho')
        package = types.ModuleType('paho.mqtt')
        package.publish = publish
        with patch.dict(sys.modules, {'paho': paho, 'paho.mqtt': package}), \
             patch.object(sys, 'stdin', io.StringIO(json.dumps({'config': self.config, 'payload': payload}))):
            mqtt.worker()
        self.assertEqual(json.loads(publish.single.call_args.kwargs['payload'])['comment'], comment)
        self.assertEqual(json.loads(publish.single.call_args.kwargs['payload'])['name'], 'Nightly æ backup')
        self.assertFalse(publish.single.call_args.kwargs['retain'])

    def test_reporter_propagates_comment_for_success_and_failure(self):
        for failure in [False, True]:
            with self.subTest(failure=failure), patch.object(mqtt, 'publish_report') as publish:
                reporter = mqtt.RunReporter(dict(self.config, on_success=True), 'create', app.__version__,
                                            dry_run=True, comment='First\nSecond')
                if failure:
                    with self.assertRaises(RuntimeError):
                        with reporter:
                            raise RuntimeError('failed')
                else:
                    with reporter:
                        pass
                self.assertEqual(publish.call_args.args[1]['comment'], 'First\nSecond')


class IntegratedReportingTests(unittest.TestCase):
    """Exercise real coordinator/report adapter with storage and transport isolated."""

    def settings(self, **overrides):
        values = dict(mqtt.DEFAULTS, host='example.invalid', topic='existing/project/status',
                      _completion_enabled=True, LiveMQTTEnabled=True, LiveBackupName='Snapshot job',
                      LiveManufacturer='Custom monitor', LiveHeartbeatSeconds=1)
        values.update(overrides)
        return values

    def test_main_loads_template_config_and_reports_real_measured_dry_run(self):
        from modules.mqtt_reporting import MQTTReporter
        import logging
        with temporary_directory() as folder:
            Path(folder,'datasets').write_text('tank/example\n')
            text=(ROOT/'configs/config-example.toml').read_text().replace('command = "create"','command = "delete"',1)
            text=text.replace('MQTT_JSON_Status = false','MQTT_JSON_Status = true',1).replace('LiveMQTTEnabled = false','LiveMQTTEnabled = true',1)
            path=Path(folder,'config.toml');path.write_text(text)
            messages=[]
            def transport(engine,packets,cancel):
                messages.extend(packets);return True
            with patch.object(sys,'argv',['app','-c',str(path)]),patch.object(app.os,'geteuid',return_value=0), \
                 patch.object(app,'runtime_base_dir',return_value=folder),patch.object(mqtt.importlib,'import_module'), \
                 patch.object(app.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'','observed list stderr')), \
                 patch.object(MQTTReporter,'_send',transport),patch.object(mqtt,'publish_report') as publish:
                app.main()
            publish.assert_called_once()
            config,payload=publish.call_args.args
            self.assertEqual(config['topic'],'homeassistant/SnapBeforeWatchTower/example-host/status')
            self.assertTrue(payload['dry_run']);self.assertTrue(payload['success'])
            self.assertEqual(payload['stderr'],'observed list stderr')
            result=next(p for topic,p,retained in messages if topic.endswith('/last_result'))
            self.assertEqual((result['completed'],result['total'],result['successful_item_count']),(1,1,1))
            self.assertEqual(result['job_type'],'zfs_snapshot_retention')
            self.assertEqual(result['run_id'],payload['run_id'])
            for logger in [logging.getLogger('SnapBeforeWatchTower'),logging.getLogger('SnapBeforeWatchTowerError')]:
                for handler in logger.handlers[:]:handler.close();logger.removeHandler(handler)

    def test_typed_completion_matches_process_codes_and_contains_no_dataset_sections(self):
        for exc, code in [(None, 0), (SystemExit(23), 23), (SystemExit(True), 1),
                          (KeyboardInterrupt(), 130), (RuntimeError('failure'), 1)]:
            with self.subTest(code=code):
                payload = mqtt.build_payload(self.settings(), 'delete', app.__version__, exc, '', 'run', name='ZFS snapshots')
                self.assertEqual(payload['name'], payload['title'])
                self.assertEqual(payload['job'], 'SnapBeforeWatchTower')
                self.assertEqual(payload['exit_code'], code)
                self.assertIs(type(payload['exit_code']), int)
                self.assertIs(payload['success'], code == 0)
                self.assertEqual(payload['status'], 'success' if code == 0 else 'failure')
                for key in ['success', 'warning', 'dry_run']:
                    self.assertIs(type(payload[key]), bool)
                for key in ['error', 'stderr', 'run_id', 'timestamp', 'host', 'name', 'title', 'job']:
                    self.assertIsInstance(payload[key], str)
                self.assertFalse(any('dataset' in k for k in payload))

    def test_canonical_shared_connection_and_channels_are_independent(self):
        for completion in [False, True]:
            for live in [False, True]:
                values=dict(MQTT_JSON_Status=completion, LiveMQTTEnabled=live,
                            broker_address='broker', broker_port=1884, mqtt_username='user',
                            mqtt_password=' secret ', SendMQTTOnSuccess=True, mqtt_json_topic='original/topic')
                with patch.object(mqtt.importlib, 'import_module'):
                    result=mqtt.validate_config(values, ROOT)
                if not completion and not live:
                    self.assertIsNone(result)
                else:
                    self.assertEqual(result['topic'],'original/topic')
                    self.assertEqual(result['password'],' secret ')
                    self.assertEqual(result['_completion_enabled'],completion)
                    self.assertEqual(result['LiveMQTTEnabled'],live)
                    self.assertEqual(result['port'],1884)
        with patch.object(mqtt.importlib, 'import_module'):
            result=mqtt.validate_config(dict(MQTT_JSON_Status=True, broker_address='broker',
                                              MQTTTLS=True, mqtt_json_topic='preserved/status'), ROOT)
        self.assertEqual(result['port'],8883)
        self.assertEqual(result['topic'],'preserved/status')
        for bad in [{'LiveMQTTEnabled':'true'}, {'MQTT_JSON_Status':1}, {'LiveHeartbeatSeconds':0},
                    {'LiveDeviceID':'INVALID'}, {'LiveManufacturer':' bad '}]:
            with self.subTest(bad=bad), patch.object(mqtt.importlib,'import_module'), self.assertRaises(ValueError):
                mqtt.validate_config(dict(broker_address='broker',LiveMQTTEnabled=True) | bad,ROOT)

    def test_removed_duplicate_options_are_rejected_before_job_work(self):
        for key, replacement in mqtt.REMOVED_KEYS.items():
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'removed duplicate option'):
                mqtt.validate_config({key: False}, ROOT)
            self.assertNotIn(key, mqtt.SUPPORTED_KEYS)
        with temporary_directory() as folder:
            config = Path(folder, 'config.toml')
            text = (ROOT/'configs/config-example.toml').read_text().replace('[mqtt]', '[mqtt]\nenabled = false', 1)
            config.write_text(text)
            with patch.object(sys, 'argv', ['app', '-c', str(config)]), patch.object(app, 'run') as work:
                with self.assertRaises(SystemExit) as code:
                    app.main()
                self.assertEqual(code.exception.code, 2)
                work.assert_not_called()

    def test_single_connection_credentials_are_shared_in_all_canonical_enable_modes(self):
        from modules.mqtt_reporting import MQTTReporter
        for completion in [False, True]:
            for live in [False, True]:
                raw = dict(MQTT_JSON_Status=completion, LiveMQTTEnabled=live,
                    SendMQTTOnSuccess=True, broker_address='shared-broker', broker_port=1884,
                    mqtt_username='shared-user', mqtt_password=' shared-secret ',
                    mqtt_json_topic='homeassistant/SnapBeforeWatchTower/example-host/status')
                with patch.object(mqtt.importlib, 'import_module'):
                    config = mqtt.validate_config(raw, ROOT)
                with patch.object(MQTTReporter, '_send', return_value=True) as send, \
                     patch.object(mqtt, 'publish_report') as complete:
                    with mqtt.RunReporter(config, 'delete', app.__version__) as observer:
                        observer.plan([])
                    self.assertEqual(complete.call_count, int(completion))
                    self.assertEqual(send.called, live)
                    if live:
                        broker = observer.live._broker
                        self.assertEqual((broker['host'], broker['port'], broker['username'], broker['password']),
                                         ('shared-broker', 1884, 'shared-user', ' shared-secret '))
                    if completion:
                        sent_config, payload = complete.call_args.args
                        self.assertEqual((sent_config['host'], sent_config['port'], sent_config['username'], sent_config['password']),
                                         ('shared-broker', 1884, 'shared-user', ' shared-secret '))
                        self.assertEqual(payload['status'], 'success')
                        self.assertNotIn('integration-success', payload)

    def test_dataset_diagnostics_exist_with_completion_only_and_do_not_invent_destinations(self):
        for failed in [False, True]:
            with self.subTest(failed=failed):
                observer, payload, error, commands, messages = self.run_observed_job(
                    failure='snapshot' if failed else None, live=False)
                self.assertIsNone(observer.live)
                self.assertEqual(payload['status'], 'failure' if failed else 'success')
                self.assertIs(payload['success'], not failed)
                self.assertEqual(payload['exit_code'], 1 if failed else 0)
                self.assertEqual(len(payload['planned_datasets']), 3)
                self.assertEqual(len(payload['failed_datasets']), int(failed))
                self.assertEqual(len(payload['skipped_datasets']), int(failed))
                if failed:
                    self.assertEqual(payload['failed_datasets'][0]['source'], 'tank/bad')
                    self.assertEqual(payload['failed_datasets'][0]['reason'], 'E'*4000)
                    self.assertEqual(payload['skipped_datasets'][0]['item_id'], '2')
                    self.assertEqual(payload['child_exit_code'], 37)
                for rows in ['planned_datasets','skipped_datasets','failed_datasets']:
                    self.assertTrue(all('destination' not in row for row in payload[rows]))

    def run_observed_job(self, command='create', dry_run=False, stop=False, failure='snapshot', live=True):
        """Use original operations with deterministic child results and no external work."""
        from modules.mqtt_reporting import MQTTReporter
        commands=[]
        sent=[]
        def child(cmd, **kwargs):
            commands.append(cmd)
            if cmd[:2]==['zfs','snapshot'] and 'tank/bad@' in cmd[2] and failure=='snapshot':
                raise subprocess.CalledProcessError(37,cmd,stderr='actual child error\n'+'E'*4500)
            if cmd[:2]==['zfs','list']:
                if cmd[-1]=='tank/bad' and failure=='list':
                    return subprocess.CompletedProcess(cmd,41,'','real list failure\n')
                return subprocess.CompletedProcess(cmd,0,cmd[-1]+'@SnapBeforeWatchTower-Date-2000-01-01_00_00_00\n','list diagnostic\n')
            return subprocess.CompletedProcess(cmd,0,'digests','child diagnostic\n')
        def transport(engine, messages, cancel):
            sent.extend(messages)
            return True
        with temporary_directory() as folder:
            path=Path(folder,'datasets');path.write_text('tank/good\ntank/bad\ntank/good\n')
            args=types.SimpleNamespace(command=command,file=str(path),older_than=__import__('datetime').timedelta(days=7),
                retain_count=0,send_mail=None,mail_on_success=False,dry_run=dry_run,
                continue_on_missing_dataset=True,continue_on_other_failures=not stop)
            observer=mqtt.RunReporter(self.settings(on_success=True,LiveMQTTEnabled=live),command,app.__version__,dry_run=dry_run)
            error=None
            with patch.object(app.os,'geteuid',return_value=0), \
                 patch.object(app,'runtime_base_dir',return_value=folder), \
                 patch.object(app.subprocess,'run',side_effect=child), \
                 patch.object(MQTTReporter,'_send',transport), patch.object(mqtt,'publish_report') as publish:
                try:
                    with observer:
                        app.run(args,observer)
                except BaseException as exc:
                    error=exc
                publish.assert_called_once()
                payload=publish.call_args.args[1]
            for logger in [__import__('logging').getLogger('SnapBeforeWatchTower'),__import__('logging').getLogger('SnapBeforeWatchTowerError')]:
                for handler in logger.handlers[:]:
                    handler.close();logger.removeHandler(handler)
            self.assertFalse(list(Path(folder).rglob('*.json')))
        return observer,payload,error,commands,sent

    def test_fatal_snapshot_keeps_job_failure_and_child_code_stderr_and_unattempted_items(self):
        observer,payload,error,commands,sent=self.run_observed_job()
        self.assertIsInstance(error,subprocess.CalledProcessError)
        self.assertEqual(error.returncode,37)
        self.assertEqual(payload['exit_code'],1)  # Original unhandled exception => process exit 1.
        self.assertEqual(payload['child_exit_code'],37)
        self.assertEqual(payload['stderr'],'E'*4000)
        state=observer.live.snapshot()
        self.assertEqual((state['completed'],state['total'],state['progress_percent']),(2,3,66.67))
        self.assertEqual((state['successful_item_count'],state['failed_item_count'],state['skipped_item_count']),(1,1,1))
        self.assertEqual(state['metrics']['snapshots_created'],1)
        self.assertEqual(state['metrics']['snapshots_deleted'],1)
        self.assertIsNone(state['transferred_bytes']);self.assertIsNone(state['bytes_per_second'])
        self.assertEqual(state['status'],'failure')
        self.assertTrue(any(topic==observer.live.result_topic and retained for topic,_,retained in sent))

    def test_continued_failure_counts_attempts_separately_and_duplicate_entries(self):
        observer,payload,error,commands,sent=self.run_observed_job(command='delete',failure='list')
        self.assertIsInstance(error,app.DatasetCommandFailuresError)
        state=observer.live.snapshot()
        self.assertEqual((state['completed'],state['total'],state['progress_percent']),(3,3,100.0))
        self.assertEqual(state['successful_item_count'],2)
        self.assertEqual(state['failed_item_count'],1)
        self.assertEqual(state['skipped_item_count'],0)
        self.assertEqual(payload['exit_code'],1)
        self.assertIn('real list failure',payload['stderr'])
        self.assertEqual(payload['child_exit_code'],41)
        self.assertFalse(any(cmd[0]=='docker' for cmd in commands))

    def test_dry_run_previews_capture_real_lists_and_never_create_destroy_or_transfer(self):
        observer,payload,error,commands,sent=self.run_observed_job(dry_run=True,failure=None)
        self.assertIsNone(error);self.assertTrue(payload['dry_run']);self.assertTrue(payload['success'])
        self.assertTrue(all(cmd[:2]==['zfs','list'] for cmd in commands))
        state=observer.live.snapshot()
        self.assertEqual(state['completed'],3);self.assertTrue(state['dry_run'])
        self.assertEqual(state['metrics'],dict(snapshots_created=0,snapshots_deleted=0,
                                             snapshot_creations_planned=3,snapshot_deletions_planned=3))
        self.assertEqual(payload['stderr'],'list diagnostic\n'*3)

    def test_disabled_and_live_only_and_completion_only_are_independent(self):
        from modules.mqtt_reporting import MQTTReporter
        for completion,live in [(False,False),(False,True),(True,False),(True,True)]:
            with self.subTest(completion=completion,live=live), \
                 patch.object(MQTTReporter,'_send',return_value=True) as send, \
                 patch.object(mqtt,'publish_report') as publish:
                with mqtt.RunReporter(self.settings(_completion_enabled=completion,LiveMQTTEnabled=live,on_success=True),
                                      'delete',app.__version__) as reporter:
                    reporter.plan([])
                self.assertEqual(publish.call_count,int(completion))
                self.assertEqual(send.called,live)

    def test_broker_failures_and_interrupts_preserve_process_outcome(self):
        from modules.mqtt_reporting import MQTTReporter
        for exc in [SystemExit(19),KeyboardInterrupt()]:
            with patch.object(MQTTReporter,'_send',return_value=False), \
                 patch.object(mqtt,'publish_report',side_effect=RuntimeError('private credentials')):
                with self.assertRaises(type(exc)) as raised:
                    with mqtt.RunReporter(self.settings(on_success=True),'create',app.__version__) as reporter:
                        reporter.plan(['tank/one','tank/two']);reporter.begin_item(0,'tank/one')
                        raise exc
                self.assertIs(raised.exception,exc)
                state=reporter.live.snapshot()
                self.assertEqual(state['completed'],1)
                self.assertEqual(state['skipped_item_count'],1)
                self.assertEqual(state['status'],'interrupted' if isinstance(exc,KeyboardInterrupt) else 'failure')

    def test_live_observer_errors_cannot_replace_job_failure_or_block_completion(self):
        from modules.mqtt_reporting import MQTTReporter
        original = RuntimeError('original job failure')
        for failure in ['startup', 'shutdown']:
            with self.subTest(failure=failure), patch.object(mqtt,'publish_report') as publish:
                target = patch.object(mqtt,'MQTTReporter',side_effect=RuntimeError('observer failed')) if failure=='startup' else patch.object(MQTTReporter,'close',side_effect=RuntimeError('observer failed'))
                with target, patch.object(MQTTReporter,'start',return_value=False):
                    with self.assertRaises(RuntimeError) as raised:
                        with mqtt.RunReporter(self.settings(),'create',app.__version__):
                            raise original
                self.assertIs(raised.exception,original)
                publish.assert_called_once()
                self.assertEqual(publish.call_args.args[1]['exit_code'],1)

    def test_unknown_progress_and_generic_items_have_no_dataset_assumptions(self):
        from modules.mqtt_reporting import MQTTReporter
        engine=MQTTReporter({},job='file-job',job_type='file_cleanup',item_unit='files')
        engine.start();engine.record_item('success',name='example.txt')
        report=engine.finish(0)
        state=engine.snapshot()
        self.assertEqual(state['job_type'],'file_cleanup');self.assertEqual(state['item_unit'],'files')
        self.assertIsNone(state['total']);self.assertIsNone(state['progress_percent'])
        self.assertEqual(state['successful_item_count'],1)
        self.assertFalse(any('dataset' in k for k in report|state))
        engine=MQTTReporter({},job='task')
        engine.update(total=10,completed=2);engine.finish(0)
        self.assertEqual(engine.snapshot()['status'],'incomplete')
        self.assertEqual(engine.snapshot()['progress_percent'],20)

    def test_discovery_identity_manufacturer_and_roles_survive_sensor_renaming(self):
        from modules.mqtt_reporting import MQTTReporter
        values=dict(broker_address='broker',LiveMQTTEnabled=True,LiveManufacturer='My fleet')
        a=MQTTReporter(values,job='job',config_path='/config/a.toml')
        b=MQTTReporter(values,job='job',config_path='/config/b.toml')
        same=MQTTReporter(values,job='job',config_path='/config/a.toml',name='Renamed job')
        self.assertNotEqual(a.device_id,b.device_id);self.assertEqual(a.device_id,same.device_id)
        discovery=a._discovery()
        for _,data,retained in discovery:
            self.assertTrue(retained);self.assertEqual(data['device']['manufacturer'],'My fleet')
            self.assertEqual(data['device']['identifiers'],['job_live_'+a.device_id])
            if data['name'] in {'Progress','Transferred','Transfer speed','Total items'}:
                self.assertIn("else 'unknown'",data['value_template'])
        roles=[data['json_attributes_template'] for _,data,_ in discovery if 'json_attributes_template' in data]
        self.assertTrue(any('live_preview_role="status"' in v for v in roles))
        self.assertTrue(any('live_preview_role="last_result"' in v for v in roles))
        self.assertTrue(all('expire_after' in data for _,data,_ in discovery if data['name']!='Last result'))

    def test_live_worker_failure_is_bounded_credentials_off_argv_and_reaped(self):
        from modules.mqtt_reporting import MQTTReporter
        from modules import mqtt_reporting as live
        engine=MQTTReporter(dict(broker_address='broker',mqtt_username='user',mqtt_password='secret'),job='job')
        proc=Mock();proc.poll.return_value=None
        proc.communicate.side_effect=[subprocess.TimeoutExpired('worker',.1),('','')]
        state = engine.snapshot()
        with patch.object(live.subprocess,'Popen',return_value=proc) as popen, \
             patch.object(live.time,'monotonic',side_effect=[0,0,6]):
            self.assertFalse(engine._send([(engine.state_topic,state,False)],cancel=None))
        proc.kill.assert_called_once()
        argv=popen.call_args.args[0]
        self.assertNotIn('secret',' '.join(argv));self.assertNotIn('broker',' '.join(argv))
        self.assertIn('secret',proc.communicate.call_args_list[0].kwargs['input'])

    def test_live_worker_verified_tls_and_no_retained_completion_or_events(self):
        from modules import mqtt_reporting as live
        publish=Mock();paho=types.ModuleType('paho');package=types.ModuleType('paho.mqtt')
        module=types.ModuleType('paho.mqtt.publish');module.multiple=publish
        broker=dict(host='broker',port=8883,username='user',password='secret',tls=True,
                    ca_file='ca.pem',cert_file='client.pem',key_file='client.key',qos=2)
        request=dict(broker=broker,completion_topic='completion',messages=[('completion',{'status':'success'},False),
                     ('job-live/id/events',{'event':'started'},False),('job-live/id/last_result',{'status':'failure'},True)])
        context=Mock()
        with patch.dict(sys.modules,{'paho':paho,'paho.mqtt':package,'paho.mqtt.publish':module}), \
             patch.object(sys,'argv',['app',live.WORKER_FLAG]),patch.object(sys,'stdin',io.StringIO(json.dumps(request))), \
             patch.object(live.ssl,'create_default_context',return_value=context) as tls:
            with self.assertRaises(SystemExit) as result:live.run_worker_if_requested()
        self.assertEqual(result.exception.code,0)
        tls.assert_called_once_with(cafile='ca.pem');context.load_cert_chain.assert_called_once_with('client.pem','client.key')
        messages=publish.call_args.args[0]
        self.assertEqual([m['retain'] for m in messages],[False,False,True])
        self.assertEqual([m['qos'] for m in messages],[2,1,1])

    def test_actual_harmless_child_stderr_is_captured_without_fabricated_log_text(self):
        for code in [0,7]:
            with self.subTest(code=code), patch.object(mqtt,'publish_report') as publish:
                observer=mqtt.RunReporter(self.settings(LiveMQTTEnabled=False,on_success=True),'delete',app.__version__)
                def child():
                    with observer:
                        app.run_cmd([sys.executable,'-c',"import sys;sys.stderr.write('actual stderr\\n'+'Z'*4100);sys.exit("+str(code)+")"])
                if code:
                    with self.assertRaises(app.CommandError) as raised:child()
                    self.assertEqual(raised.exception.returncode,7)
                else:
                    child()
                payload=publish.call_args.args[1]
                self.assertEqual(payload['stderr'],'Z'*4000)
                self.assertEqual(payload['exit_code'],1 if code else 0)

    def test_live_heartbeat_and_event_switches_without_completion_reports(self):
        from modules import mqtt_reporting as live
        from threading import Event
        beat=Event();packets=[]
        def send(engine,messages,cancel):
            packets.extend(messages)
            if sum(topic==engine.state_topic for topic,_,_ in packets)>=2:beat.set()
            return True
        engine=live.MQTTReporter(dict(broker_address='broker',LiveMQTTEnabled=True,
                                     LiveHeartbeatSeconds=1,LiveMQTTDiscovery=False),job='heartbeat')
        with patch.object(live.MQTTReporter,'_send',send):
            engine.start()
            try:self.assertTrue(beat.wait(3))
            finally:engine.close()
        states=[p for topic,p,_ in packets if topic==engine.state_topic]
        self.assertGreaterEqual(len(states),2)
        self.assertNotEqual(states[0]['last_heartbeat'],states[1]['last_heartbeat'])
        self.assertTrue(all(p['status']=='running' and p['progress_percent'] is None for p in states))
        for failed in [False,True]:
            for enabled in [False,True]:
                values=dict(broker_address='broker',LiveMQTTEnabled=True,LiveNotifyStart=enabled,
                            LiveNotifySuccess=enabled,LiveNotifyFailure=enabled)
                thread=Mock();thread.is_alive.return_value=False
                with patch.object(live,'Thread',return_value=thread),patch.object(live.MQTTReporter,'_send',return_value=True) as delivery:
                    engine=live.MQTTReporter(values,job='events');engine.start();engine.finish(1 if failed else 0)
                messages=delivery.call_args.args[0]
                events=[p['event'] for topic,p,_ in messages if topic==engine.events_topic]
                self.assertEqual(events, ['started','failed' if failed else 'completed'] if enabled else [])
                self.assertTrue(any(topic==engine.result_topic and retained for topic,_,retained in messages))


class HomeAssistantTemplateTests(unittest.TestCase):
    """Render actual YAML/Jinja using a local HA facade; never access an installation."""

    def setUp(self):
        try:
            import yaml
            from jinja2.nativetypes import NativeEnvironment
            from jinja2 import Environment
        except ImportError:
            self.skipTest('Optional offline YAML/Jinja test tools are not installed')
        self.yaml=yaml;self.native=NativeEnvironment();self.env=Environment()
        def boolean(value,default=False):
            if isinstance(value,str):return value.strip().lower() in {'true','on','yes','1'}
            return bool(value) if value is not None else default
        self.native.filters['bool']=boolean;self.env.filters['bool']=boolean

    def test_completion_automation_typed_contract_dry_run_guard_and_pushover_limits(self):
        doc=self.yaml.safe_load((ROOT/'homeassistant/success-failure-automation.yaml').read_text())
        self.assertEqual(doc['triggers'][0]['topic'],'homeassistant/SnapBeforeWatchTower/example-host/status')
        self.assertIn('stop',doc['actions'][1]['then'][0])
        guard=doc['actions'][1]['if'][0]['value_template']
        self.assertTrue(self.native.from_string(guard).render(report={'dry_run':True}))
        for code in [0,17]:
            report=dict(name='N'*1000,title='N'*1000,job='SnapBeforeWatchTower',exit_code=code,
                        success=code==0,status='success' if code==0 else 'failure',warning=True,
                        warning_detail='W'*4000,error='E'*4000,stderr='old'+'S'*3997,
                        child_exit_code=37,command='create',host='H'*1000,comment='C'*1000,dry_run=False)
            values={'trigger':types.SimpleNamespace(payload_json=report)}
            for action in doc['actions']:
                for key,template in action.get('variables',{}).items():
                    values[key]=self.native.from_string(template).render(**values)
            self.assertEqual(values['notice_status'],report['status'])
            self.assertLessEqual(len(values['notice_message']),1024)
            self.assertLessEqual(len(values['notice_title']),250)
            self.assertIn('Exit code: '+str(code),values['notice_message'])
            self.assertIn('Stderr',values['notice_message'])
            self.assertIn('S'*10,values['notice_message'])
        for bad in [{'status':'success','success':True,'exit_code':2},
                    {'status':'success','success':'true','exit_code':'0'},
                    {'status':'success','success':True,'exit_code':False}]:
            template=doc['actions'][2]['variables']['valid_report']
            self.assertFalse(self.native.from_string(template).render(report=bad))
        old=self.yaml.safe_load((ROOT/'homeassistant/SnapBeforeWatchtower-mqtt-persistent-notification.yaml').read_text())
        self.assertIn('if',old['actions'][1]);self.assertIn('stop',old['actions'][1]['then'][0])
        self.assertEqual(old['actions'],doc['actions'])

    def render_card(self, *, job_type='zfs_snapshot_retention', unit='datasets', state='running', stale=False, dry_run=False):
        import datetime
        doc=self.yaml.safe_load((ROOT/'homeassistant/live-preview-card.yaml').read_text())
        self.assertEqual(doc['type'],'markdown');self.assertIn('content: |', (ROOT/'homeassistant/live-preview-card.yaml').read_text())
        now=datetime.datetime.now(datetime.timezone.utc)
        live='sensor.renamed_arbitrary';last='sensor.another_arbitrary_name'
        attributes=dict(live_preview_role='status',status='running' if stale else state,name='Current job',
            job_type=job_type,item_unit=unit,completed=1,total=3,progress_percent=33.33,
            successful_items=[dict(name='good item',reason='')],failed_items=[dict(name='bad item',reason='Permission denied')],
            skipped_items=[dict(name='unattempted',reason='Stopped early')],metrics=dict(snapshots_created=1,snapshots_deleted=2,
            snapshot_creations_planned=1,snapshot_deletions_planned=2),last_heartbeat=(now-datetime.timedelta(seconds=500 if stale else 0)).isoformat(),
            heartbeat_timeout=180,run_id='new',stderr='actual <stderr>',runtime_seconds=12,
            transferred_bytes=None,bytes_per_second=None,dry_run=dry_run,exit_code=1 if state=='failure' else None)
        attrs={live:attributes,last:dict(live_preview_role='last_result',status='failure',run_id='old',finished_at=now.isoformat())}
        class States:
            sensor=[types.SimpleNamespace(entity_id=live),types.SimpleNamespace(entity_id=last),types.SimpleNamespace(entity_id='sensor.other_fleet')]
            def __call__(self,eid):return 'unavailable' if eid==live and stale else state if eid==live else 'failure'
        def timestamp(value,default=None):
            if value is None:return default
            return (datetime.datetime.fromisoformat(value) if isinstance(value,str) else value).timestamp()
        self.env.globals.update(states=States(),state_attr=lambda eid,key:attrs.get(eid,{}).get(key),
            device_id=lambda eid:'other' if eid=='sensor.other_fleet' else 'device',
            device_attr=lambda dev,key: ('Other fleet' if dev=='other' else 'SnapBeforeWatchTower') if key=='manufacturer' else 'ZFS job',
            device_entities=lambda dev:[live,last] if dev=='device' else ['sensor.other_fleet'],
            as_timestamp=timestamp,now=lambda:now,as_datetime=lambda value,default=None:datetime.datetime.fromisoformat(value) if value else default,
            as_local=lambda value:value)
        return self.env.from_string(doc['content']).render()

    def test_card_uses_roles_project_fields_generic_items_and_null_measurements(self):
        card=self.render_card(dry_run=True)
        for text in ['1 job(s) discovered','Datasets attempted','Snapshots:','PREVIEW','Permission denied','Stopped early',
                     'actual &lt;stderr&gt;','Heartbeat:','Retained last result:','33.3']:
            self.assertIn(text,card)
        self.assertNotIn('**Transferred:**',card)
        generic=self.render_card(job_type='file_cleanup',unit='files')
        self.assertIn('Files attempted',generic);self.assertNotIn('**Snapshots:**',generic)
        self.assertNotIn('Datasets',generic)

    def test_card_lost_heartbeat_interrupts_and_retained_history_are_honest(self):
        card=self.render_card(stale=True)
        self.assertIn('HEARTBEAT LOST',card);self.assertIn('Its outcome is unknown',card)
        self.assertIn('Previous retained result: FAILURE',card)
        self.assertIn('INTERRUPTED',self.render_card(state='interrupted'))
        self.assertIn('INCOMPLETE',self.render_card(state='incomplete'))


if __name__ == '__main__':
    unittest.main()
