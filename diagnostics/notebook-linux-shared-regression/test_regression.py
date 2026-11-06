"""SDK-free negative tests. No product import, environment install or runtime dispatch."""
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE/(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


h = load('run_regression')
f = load('fixtures')


class IntegrityTests(unittest.TestCase):
    def test_paths_reject_escape_alias_and_drive(self):
        for path in ('../x', '/x', 'a/../x', 'a//b', './x', 'C:x', 'a\\b', ''):
            with self.subTest(path=path), self.assertRaises(ValueError):
                h.safe_parts(path)
        self.assertEqual(h.safe_parts('a/b'), ('a', 'b'))

    def test_duplicate_and_malformed_lock_names(self):
        suffix = ' --hash=sha256:'+'0'*64
        self.assertEqual(h.lock_inventory('Some_Pkg==1.0'+suffix), {'some-pkg': '1.0'})
        for text in ('', 'pkg>=1'+suffix, 'pkg==1', 'pkg==1 --index-url=x',
                     'Some.Pkg==1'+suffix+'\nsome_pkg==2'+suffix):
            with self.subTest(text=text), self.assertRaises(ValueError):
                h.lock_inventory(text)

    def test_runtime_copy_rejects_changed_source_and_collision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'source'
            source.mkdir()
            (source/'engine.py').write_bytes(b'exact')
            expected = {'engine.py': dict(bytes=5, sha256=hashlib.sha256(b'exact').hexdigest())}
            with patch.dict(h.EXPECTED, source_files=expected):
                h.copy_runtime(source, root/'copy')
                with self.assertRaises(ValueError):
                    h.copy_runtime(source, root/'copy')
                (source/'engine.py').write_bytes(b'changed')
                with self.assertRaises(ValueError):
                    h.copy_runtime(source, root/'other')

    def test_fixture_namespace_fresh_and_product_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'execution.py').write_bytes(b'original')
            codes, descriptors, lifecycle = f.authored('observer_success', root, root/'evidence', 'nonce')
            self.assertEqual((root/'execution.py').read_bytes(), b'original')
            for descriptor in descriptors+[lifecycle['bootstrap'], lifecycle['cleanup']]:
                self.assertTrue(descriptor['path'].startswith('regression-fixtures/'))
                self.assertEqual(h.digest(root/descriptor['path']), descriptor['sha256'])
            with self.assertRaises(FileExistsError):
                f.authored('observer_success', root, root/'evidence', 'nonce')

    def test_archive_digest_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'dependency.zip').write_bytes(b'wrong')
            with self.assertRaises(ValueError):
                h.unpack(root, dict(bytes=5, sha256='0'*64))
            self.assertFalse((root/'retained').exists())

    def test_archive_traversal_even_with_matching_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with zipfile.ZipFile(root/'dependency.zip', 'w') as package:
                package.writestr('../escaped', 'wrong')
            archive = root/'dependency.zip'
            with self.assertRaises(ValueError):
                h.unpack(root, dict(bytes=archive.stat().st_size, sha256=h.digest(archive), entries=1))
            self.assertFalse((root.parent/'escaped').exists())

    def test_manifest_requires_exact_set_and_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'a').write_bytes(b'right')
            h.write(root/'evidence-manifest.json', {'a': dict(bytes=5, sha256=h.digest(root/'a'))})
            h.verify_manifest(root, 1)
            (root/'extra').write_bytes(b'x')
            with self.assertRaises(ValueError):
                h.verify_manifest(root, 1)

    def test_frozen_method_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'tests.py'
            path.write_text('class LinuxLifecycleTests:\n def test_one(self): pass\n def helper(self): pass\n')
            self.assertEqual(h.method_set(path), ['test_one'])
            self.assertNotEqual(h.method_set(path), h.EXPECTED['lifecycle_methods'])
        self.assertEqual(len(h.EXPECTED['lifecycle_methods']), 14)
        self.assertEqual(len(h.EXPECTED['cases']), 7)


class AcquisitionEvidenceTests(unittest.TestCase):
    def test_raw_mismatch_and_malformed_metadata_retained_before_rejection(self):
        for raw in (b'{"id":0,"expired":false}', b'not valid json'):
            calls = []
            class Opener:
                def open(self, request, timeout):
                    calls.append(request.full_url)
                    return io.BytesIO(raw)
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as directory, \
                    patch.object(h.urllib.request, 'build_opener', return_value=Opener()), \
                    patch.object(h.signal, 'SIGALRM', 14, create=True), \
                    patch.object(h.signal, 'signal', return_value=None), \
                    patch.object(h.signal, 'alarm', create=True), \
                    patch.dict(h.os.environ, {'ARTIFACT_TOKEN': 'OFFLINE_FAKE'}):
                root = Path(directory)
                with self.assertRaises(RuntimeError):
                    h.acquire(root, h.EXPECTED['artifacts'][0])
                self.assertEqual((root/'artifact-api.json').read_bytes(), raw)
                self.assertEqual(len(calls), 1)
                self.assertFalse((root/'dependency.zip').exists())
                self.assertFalse(any('OFFLINE_FAKE' in path.read_text() for path in root.iterdir()))


class SupervisorExitTests(unittest.TestCase):
    def test_expected_success_failure_and_cancel_exits(self):
        for case in h.EXPECTED['cases']:
            receipts = []
            expected = 0 if case == 'observer_success' else 1
            f.supervisor_exit(case, expected, receipts.append)
            self.assertEqual(receipts, [dict(actual=expected, expected=expected, case=case)])

    def test_wrong_and_abnormal_exit_preserved_before_rejection(self):
        for case, code in [('observer_success', 1), ('observer_success', -9),
                           ('observer_failure', 0), ('observer_cancel_force0', -15)]:
            receipts = []
            with self.subTest(case=case, code=code), self.assertRaises(ValueError):
                f.supervisor_exit(case, code, receipts.append)
            self.assertEqual(receipts[0]['actual'], code)

    def test_exit_receipt_persistence_failure_is_not_acceptance(self):
        def failed(receipt):
            raise OSError('disk failed')
        with self.assertRaises(OSError):
            f.supervisor_exit('observer_success', 0, failed)


class CleanupTests(unittest.TestCase):
    def test_failed_observation_and_raw_persistence_do_not_gate_cleanup(self):
        seen = []
        def fail_query():
            seen.append('query')
            raise OSError('query failed')
        def persist(rows):
            seen.append('persist')
            self.assertEqual(rows[0]['error']['message'], 'query failed')
            self.assertEqual(rows[1]['result'], 'stopped')
            raise OSError('disk failed')
        with patch('sys.stderr', io.StringIO()):
            rows = h.cleanup_all([('query', fail_query), ('stop', lambda: seen.append('stop') or 'stopped'),
                                  ('collect', lambda: seen.append('collect'))], persist)
        self.assertEqual(seen, ['query', 'stop', 'collect', 'persist'])
        self.assertEqual(rows[-1]['step'], 'persist_cleanup')
        with self.assertRaises(ValueError):
            h.clean_report(rows)

    def test_cleanup_secondary_retained_without_replacing_primary(self):
        primary = RuntimeError('primary')
        saved = []
        def fail():
            raise OSError('stop failed')
        rows = h.cleanup_all([('stop', fail), ('collect', lambda: 0)], saved.extend)
        self.assertEqual(str(primary), 'primary')
        self.assertEqual(saved, rows)
        self.assertEqual(rows[0]['error']['message'], 'stop failed')
        self.assertEqual(rows[1]['result'], 0)

    def test_command_failure_stops_sequence_and_persists_exit(self):
        class Process:
            def wait(self, timeout): return 7
            def poll(self): return 7
        with tempfile.TemporaryDirectory() as directory, patch.object(h.subprocess, 'Popen', return_value=Process()):
            log = Path(directory)/'case.log'
            with self.assertRaises(ValueError):
                h.command(['never-executed'], 1, log)
            self.assertEqual(h.read(log.with_suffix('.receipt.json'))['exit'], 7)

    def test_command_write_failure_still_collects_launcher(self):
        seen = []
        class Process:
            def wait(self, timeout): seen.append('wait'); return 0
            def poll(self): return 0
        with tempfile.TemporaryDirectory() as directory, patch.object(h.subprocess, 'Popen', return_value=Process()), \
                patch.object(h, 'write', side_effect=OSError('disk')), patch('sys.stderr', io.StringIO()):
            with self.assertRaises(ValueError):
                h.command(['never-executed'], 1, Path(directory)/'case.log')
        self.assertEqual(seen, ['wait', 'wait'])

    def test_timeout_kills_only_owned_launcher_and_runs_service_cleanup(self):
        seen = []
        class Process:
            def wait(self, timeout):
                seen.append('wait')
                if len(seen) == 1: raise TimeoutError('deadline')
                return -9
            def poll(self): return None
            def kill(self): seen.append('kill')
        with tempfile.TemporaryDirectory() as directory, patch.object(h.subprocess, 'Popen', return_value=Process()), \
                patch.object(h, 'owned_cleanup', side_effect=lambda *a, **kw: seen.append('service')):
            root = Path(directory)
            with self.assertRaises(TimeoutError):
                h.command(['never-executed'], 1, root/'case.log', root, root)
            raw = h.read(root/'case.receipt.json')
            self.assertEqual(raw['primary']['type'], 'TimeoutError')
        self.assertEqual(seen, ['wait', 'kill', 'wait', 'service'])


class InstallerContainmentTests(unittest.TestCase):
    def config(self, root):
        return dict(profile='notebook-linux-py312', python=h.sys.executable,
                    wheelhouse=str(root/'wheels'), destination=str(root/'environment'), source_root=str(root/'source'))

    def exercise(self, root, fault=None):
        events = []
        state = dict(children=1, assigned=False, waits=0, foreign=False)
        class Control(io.StringIO):
            def write(self, value):
                if not state['assigned']:
                    raise RuntimeError('Gate released before ownership')
                events.append('gate')
                return super().write(value)
        class Process:
            stdin = Control()
            def poll(self): return None if state['children'] else 0
            def kill(self): events.append('collect-direct-launcher')
            def wait(self, timeout):
                state['waits'] += 1
                if state['waits'] == 1:
                    if fault in ('timeout', 'query-write'):
                        events.append('nested-pip-still-live')
                        raise TimeoutError('outer300')
                    state['children'] = 0
                    return 7 if fault == 'exit7' else 0
                return -9 if fault in ('timeout', 'query-write') else 0
        class Service:
            def __init__(self, output, runtime):
                self.runtime = runtime
                self.output = output
                events.append('service-created')
            def command(self, argv):
                self.argv = argv
                return argv
            def assign(self, process):
                events.append('assign')
                if fault == 'identity':
                    state['foreign'] = True
                    raise RuntimeError('wrong unit identity')
                state['assigned'] = True
            def terminate(self):
                events.append('terminate-attempt')
                if state['foreign']:
                    raise RuntimeError('ownership not confirmed')
                if fault == 'query-write':
                    raise OSError('service observation persistence failed')
                state['children'] = 0
                events.append('owned-unit-stop')
            def stop_client(self): events.append('verified-client-collection')
            def active(self):
                events.append('population-query')
                if fault == 'query-write':
                    raise OSError('population unknown')
                return state['children']
            def close(self): events.append('service-close')
        def recover(*args, **kwargs):
            events.append('independent-identity-check')
            if state['foreign']:
                raise RuntimeError('foreign unit refused')
            state['children'] = 0
            events.append('independent-owned-unit-stop')
        real_write = h.write
        def write(path, value):
            if fault == 'query-write' and path.name == 'install-cleanup.json':
                raise OSError('disk full')
            real_write(path, value)
        with patch.object(h, 'owned_cleanup', side_effect=recover), patch.object(h, 'write', side_effect=write), \
                patch('sys.stderr', io.StringIO()):
            operation = lambda: h.contained_install(root/'source', root/'install', self.config(root),
                                                   service_factory=Service, popen=lambda *a, **kw: Process(), clock=lambda: 0)
            if fault:
                with self.assertRaises((ValueError, RuntimeError, TimeoutError)):
                    operation()
            else:
                operation()
        return events, state

    def test_normal_gated_install_and_terminal_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            events, state = self.exercise(root)
            self.assertLess(events.index('assign'), events.index('gate'))
            self.assertEqual(state['children'], 0)
            self.assertEqual(h.read(root/'install/install-acceptance.json')['exit'], 0)
            self.assertIn('service-close', events)

    def test_nonzero_launcher_retained_and_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.exercise(root, 'exit7')
            self.assertEqual(h.read(root/'install/launcher-exit.json')['exit'], 7)
            self.assertFalse((root/'install/install-acceptance.json').exists())

    def test_outer_timeout_stops_nested_installer_via_exact_unit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            events, state = self.exercise(root, 'timeout')
            self.assertIn('nested-pip-still-live', events)
            self.assertIn('owned-unit-stop', events)
            self.assertEqual(state['children'], 0)
            raw = h.read(root/'install/install-cleanup.json')
            self.assertEqual(raw['primary']['type'], 'TimeoutError')
            self.assertFalse((root/'install/install-acceptance.json').exists())

    def test_identity_mismatch_never_releases_gate_or_stops_foreign_unit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            events, state = self.exercise(root, 'identity')
            self.assertNotIn('gate', events)
            self.assertNotIn('owned-unit-stop', events)
            self.assertNotIn('independent-owned-unit-stop', events)
            self.assertIn('service-close', events)
            self.assertFalse((root/'install/install-acceptance.json').exists())

    def test_query_and_persistence_failure_still_recover_and_collect(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            events, state = self.exercise(root, 'query-write')
            self.assertIn('independent-owned-unit-stop', events)
            self.assertIn('verified-client-collection', events)
            self.assertIn('population-query', events)
            self.assertIn('service-close', events)
            self.assertEqual(state['children'], 0)
            self.assertFalse((root/'install/install-acceptance.json').exists())

    def test_worker_eof_or_wrong_gate_never_reads_request_or_starts_install(self):
        with patch.object(h, 'read') as read, patch.object(h.subprocess, 'run') as launch:
            for control in ('', 'wrong\n'):
                with self.assertRaises(ValueError):
                    h.install_worker(Path('unused'), io.StringIO(control))
            read.assert_not_called()
            launch.assert_not_called()

    def test_worker_exact_public_argv_and_failed_exit_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = self.config(root)
            h.write(root/'install-request.json', config)
            launched = []
            with patch.object(h, 'verify_sources'), self.assertRaises(ValueError):
                h.install_worker(root, io.StringIO('start\n'), lambda argv: launched.append(argv) or 7)
            self.assertEqual(launched, [h.install_argv(config)])
            self.assertEqual(h.read(root/'worker-exit.json')['exit'], 7)
            self.assertEqual(launched[0][5:7], ['environment', '--profile'])
            self.assertNotIn('--index-url', launched[0])


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.identity = dict(pid=123, starttime='456', cgroup='0::/system.slice/owned.service\n', executable='/python')
        self.ready = dict(nonce='exact', child=self.identity, popen_pid=123, popen_live=True)
        self.service = dict(unit='owned.service', gate_held=True, description='owned',
                            at_gate={'properties': dict(Id='owned.service', Description='owned', ControlGroup='/system.slice/owned.service')})

    def test_positive_identity(self):
        f.validate_ready(self.ready, self.identity, 'exact', self.service, True)

    def test_nonce_reuse_pid_cgroup_and_exit_rejected(self):
        for field, value in [('pid', 124), ('starttime', 'old'), ('cgroup', '0::/other.service\n'), ('executable', '/other')]:
            identity = dict(self.identity, **{field: value})
            with self.subTest(field=field), self.assertRaises(ValueError):
                f.validate_ready(self.ready, identity, 'exact', self.service, True)
        for nonce, live in [('wrong', True), ('exact', False)]:
            with self.assertRaises(ValueError):
                f.validate_ready(self.ready, self.identity, nonce, self.service, live)

    def test_specific_service_and_handle_required(self):
        service = copy.deepcopy(self.service)
        service['at_gate']['properties']['ControlGroup'] = '/other/foreign.service'
        with self.assertRaises(ValueError):
            f.validate_ready(self.ready, self.identity, 'exact', service, True)
        ready = dict(self.ready, popen_pid=999)
        with self.assertRaises(ValueError):
            f.validate_ready(ready, self.identity, 'exact', self.service, True)


class DeadlineTests(unittest.TestCase):
    def setUp(self):
        self.record = dict(state='failed', elapsed_seconds=1.02, error=dict(type='DeadKernelError', message='Kernel died'))
        self.primary = dict(type='CellExecutionError', message='OBSERVATION_PRIMARY')
        self.context = dict(contract={'observer_lifecycle': {'cleanup_timeout_seconds': 1, 'cleanup': {'sha256': h.EXPECTED['deadline']['cleanup_source_sha256']}}}, profile={'default_cell_timeout_seconds': 10})

    def test_pinned_classification(self):
        record = f.classify_deadline(self.record, 'CLEANUP_STARTED\n', self.primary, h.EXPECTED['deadline'], self.context)
        self.assertEqual(record['restoration'], 'unconfirmed')

    def test_early_same_message_and_unrelated_errors_rejected(self):
        for change in (dict(elapsed_seconds=.1), dict(elapsed_seconds=3), dict(state='succeeded'),
                       dict(error=dict(type='TimeoutError', message='')), dict(error=dict(type='DeadKernelError', message='other'))):
            with self.subTest(change=change), self.assertRaises(ValueError):
                f.classify_deadline(dict(self.record, **change), 'CLEANUP_STARTED\n', self.primary, h.EXPECTED['deadline'], self.context)
        with self.assertRaises(ValueError):
            f.classify_deadline(self.record, '', self.primary, h.EXPECTED['deadline'], self.context)
        with self.assertRaises(ValueError):
            f.classify_deadline(self.record, 'CLEANUP_STARTED\n', dict(type='Other', message='OBSERVATION_PRIMARY'), h.EXPECTED['deadline'], self.context)

    def test_marker_only_wrong_primary_and_changed_allowance_rejected(self):
        with self.assertRaises(ValueError):
            f.classify_deadline(dict(state='running', elapsed_seconds=1), 'CLEANUP_STARTED\n', self.primary, h.EXPECTED['deadline'], self.context)
        with self.assertRaises(ValueError):
            f.classify_deadline(self.record, 'CLEANUP_STARTED\n', dict(type='CellExecutionError', message='UNRELATED'), h.EXPECTED['deadline'], self.context)
        changed = copy.deepcopy(self.context)
        changed['contract']['observer_lifecycle']['cleanup_timeout_seconds'] = 2
        with self.assertRaises(ValueError):
            f.classify_deadline(self.record, 'CLEANUP_STARTED\n', self.primary, h.EXPECTED['deadline'], changed)
        changed = copy.deepcopy(self.context)
        changed['contract']['observer_lifecycle']['cleanup']['sha256'] = '0'*64
        with self.assertRaises(ValueError):
            f.classify_deadline(self.record, 'CLEANUP_STARTED\n', self.primary, h.EXPECTED['deadline'], changed)


if __name__ == '__main__':
    unittest.main(verbosity=2)
