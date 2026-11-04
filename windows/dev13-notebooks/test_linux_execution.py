"""Hosted Linux prerequisite entry point; full lifecycle tests are not yet added."""
import argparse
from pathlib import Path
import sys
import subprocess
import unittest
import json
import os
import signal
import time
import select

from linux_lifecycle import _close_control, _unit_snapshot, _empty_group, _command, preflight


class PreflightFailureTests(unittest.TestCase):
    def test_early_exit_pipe_close_preserves_cleanup(self):
        process = subprocess.Popen([sys.executable, "-I", "-c", "pass"],
                                   stdin=subprocess.PIPE, text=True)
        process.wait(timeout=10)
        process.stdin.write("start\n")
        with self.assertRaises(OSError):
            process.stdin.flush()
        report = {"state": "succeeded"}
        _close_control(process, report)
        self.assertEqual(report["state"], "failed")
        self.assertIn("control_close_error", report)
        self.assertTrue(process.stdin.closed)
        self.assertEqual(process.wait(timeout=1), 0)


class LinuxLifecycleTests(unittest.TestCase):
    evidence_root = None

    @classmethod
    def setUpClass(cls):
        if sys.platform != 'linux':
            raise RuntimeError('ACTUAL_LINUX_REQUIRED; no skipped capability pass')
        import execution
        cls.profile = execution.profile_for('notebook-linux-py312')
        cls.identity = execution.inspect_environment(Path(sys.executable), cls.profile)

    def setUp(self):
        self.output = self.evidence_root / (self._testMethodName + ' space-λ')
        self.output.mkdir(parents=True, exist_ok=False)
        self.process = None
        self.sentinel = subprocess.Popen([sys.executable, '-I', '-u', '-c',
            'import sys;\nfor line in sys.stdin: print(line.strip(),flush=True)'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, close_fds=True)
        self.sentinel_cgroup = Path(f'/proc/{self.sentinel.pid}/cgroup').read_text()

    def sentinel_alive(self):
        self.assertIsNone(self.sentinel.poll())
        self.sentinel.stdin.write('still alive\n'); self.sentinel.stdin.flush()
        self.assertTrue(select.select([self.sentinel.stdout], [], [], 3)[0])
        self.assertEqual(self.sentinel.stdout.readline(), 'still alive\n')
        self.assertEqual(Path(f'/proc/{self.sentinel.pid}/cgroup').read_text(), self.sentinel_cgroup)

    def tearDown(self):
        try:
            self.sentinel_alive()
        finally:
            self.sentinel.stdin.close()
            self.sentinel.wait(timeout=5)
            self.sentinel.stdout.close()
            if self.process is not None and self.process.poll() is None:
                self.process.kill(); self.process.wait(timeout=5)
            # Failure cleanup is restricted to the exact recorded test unit.
            path = self.output / 'service.json'
            if path.exists():
                data = json.loads(path.read_bytes())
                snapshot = _unit_snapshot(data['unit'])['properties']
                if snapshot.get('Description') == data['description']:
                    _command(['sudo', '-n', 'systemctl', 'stop', data['unit']], timeout=15)
                    _command(['sudo', '-n', 'systemctl', 'reset-failed', data['unit']])

    def start(self, codes, timeout=120, grace=5, runtime=90, image=False):
        import execution
        import nbformat
        notebook = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(code) for code in codes])
        raw = nbformat.writes(notebook).encode()
        (self.output / 'source-original.ipynb').write_bytes(raw)
        config = dict(python=sys.executable, identity=self.identity, contract_sha256='authored-linux-fixture',
                      profile=dict(self.profile, default_cell_timeout_seconds=timeout,
                                   cancel_grace_seconds=grace, service_runtime_seconds=runtime),
                      witness='print("{}")', contract=dict(id='authored-linux-fixture',
                      source={'sha256': execution.digest(raw)}, code_cells=list(range(len(codes))),
                      preamble=None, required_images=[0] if image else [], required_text={}))
        execution.atomic_json(self.output / 'engine-request.json', config)
        with (self.output / 'supervisor.stdout').open('w') as stdout, (self.output / 'supervisor.stderr').open('w') as stderr:
            self.process = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()),
                                             '--supervise', '--output', str(self.output)],
                                            stdout=stdout, stderr=stderr, close_fds=True)

    def wait_for(self, filename, predicate=lambda value: True, timeout=30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            path = self.output / filename
            if path.exists():
                value = json.loads(path.read_bytes())
                if predicate(value):
                    return value
            if self.process.poll() is not None:
                self.fail('Supervisor exited before ' + filename + '; see retained stderr/status')
            time.sleep(0.05)
        self.fail('Deadline waiting for ' + filename)

    def running(self):
        self.wait_for('cells.json', lambda cells: len(cells) > 1 and cells[1]['state'] == 'running')
        return self.wait_for('status.json', lambda status: status['state'] == 'running')

    def assert_empty(self):
        data = json.loads((self.output / 'service.json').read_bytes())
        self.assertTrue(data['gate_held'])
        relative = data['at_gate']['properties']['ControlGroup']
        self.assertEqual(Path(relative).name, data['unit'])
        group = Path('/sys/fs/cgroup') / relative.lstrip('/')
        self.assertNotIn('..', group.parts)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and not _empty_group(group)['empty']:
            time.sleep(0.05)
        observation = _empty_group(group)
        (self.output / 'harness-cleanup.json').write_text(json.dumps(dict(
            observer='outside-service test harness, not supervisor result', unit=data['unit'],
            observation=observation, sentinel_pid=self.sentinel.pid,
            sentinel_cgroup=self.sentinel_cgroup), indent=2))
        self.assertTrue(observation['empty'])
        self.sentinel_alive()

    def finish(self, expected):
        self.process.wait(timeout=35)
        result = json.loads((self.output / 'status.json').read_bytes())
        self.assertEqual(result['state'], expected, result)
        self.assertEqual(result['cleanup']['active_processes'], 0)
        self.assert_empty()
        return result

    def test_complete_notebook_and_rich_output(self):
        self.start(['import matplotlib.pyplot as plt\nplt.plot([0,1],[0,1]); plt.show()', 'print("complete")'], image=True)
        result = self.finish('succeeded')
        self.assertTrue(result['source_cells_preserved'])
        self.assertTrue(result['cleanup']['kernel_job_membership'])
        self.assertEqual(result['original_execution'], 'succeeded')
        source = json.loads((self.output / 'source-original.ipynb').read_bytes())
        rendered = json.loads((self.output / 'executed.ipynb').read_bytes())
        self.assertEqual([''.join(c['source']) for c in source['cells']],
                         [''.join(c['source']) for c in rendered['cells'][:-1]])

    def test_source_error(self):
        self.start(['print("retained")', 'raise ValueError("source failure")', '42'])
        result = self.finish('failed')
        self.assertEqual(result['error']['type'], 'CellExecutionError')

    def test_cell_timeout(self):
        self.start(['print("retained")', 'import time; time.sleep(120)', '42'], timeout=1)
        self.assertEqual(self.finish('failed')['error']['type'], 'CellTimeoutError')

    def test_kernel_crash(self):
        self.start(['print("retained")', 'import os; os._exit(23)', '42'])
        self.assertEqual(self.finish('failed')['error']['type'], 'DeadKernelError')

    def test_cancel(self):
        import execution
        self.start(['print("retained")', 'import time; time.sleep(120)', '42'])
        self.running(); execution.cancel(self.output); execution.cancel(self.output)
        self.assertEqual(self.finish('cancelled')['original_execution'], 'incomplete')

    def test_engine_sigkill(self):
        self.start(['print("retained")', 'import time; time.sleep(120)', '42'])
        status = self.running(); os.kill(status['engine_pid'], signal.SIGKILL)
        result = self.finish('failed')
        self.assertEqual(result['original_execution'], 'incomplete')
        cells = json.loads((self.output / 'cells.json').read_bytes())
        self.assertEqual([cell['state'] for cell in cells], ['succeeded', 'interrupted', 'not_run', 'not_run'])
        notebook = json.loads((self.output / 'executed.ipynb').read_bytes())
        self.assertEqual(notebook['cells'][0]['outputs'][0]['text'], 'retained\n')

    def test_client_loss(self):
        from linux_lifecycle import inspect_client
        self.start(['print("retained")', 'import time; time.sleep(120)', '42'])
        status = self.running()
        service = json.loads((self.output / 'service.json').read_bytes())
        observation = inspect_client(sys.executable, self.output / 'client-identity.json', service['unit'], kill=True)
        self.assertEqual(observation['pid'], status['client_pid'])
        (self.output / 'client-signal.json').write_text(json.dumps(observation, indent=2))
        self.assertEqual(self.finish('failed')['failure_cause'], 'launcher_loss')

    def test_supervisor_loss(self):
        self.start(['print("retained")', 'import time; time.sleep(120)', '42'])
        self.running(); self.process.kill(); self.process.wait(timeout=5)
        self.assert_empty()
        result = json.loads((self.output / 'engine-result.json').read_bytes())
        self.assertEqual(result['control_event'], 'control_eof')
        self.assertEqual(result['state'], 'failed')
        # The dead supervisor cannot publish terminal status.
        self.assertEqual(json.loads((self.output / 'status.json').read_bytes())['state'], 'running')

    def test_runtime_deadline(self):
        self.start(['print("retained")', 'import time; time.sleep(120)', '42'], runtime=12)
        self.assertEqual(self.finish('failed')['failure_cause'], 'service_runtime_timeout')

    def test_detached_descendants_forced_cancel(self):
        import execution
        escaped = ('import os,signal,time,pathlib\nos.setsid()\n'
                   'if os.fork(): os._exit(0)\n'
                   'signal.signal(signal.SIGTERM,signal.SIG_IGN)\n'
                   'pathlib.Path("escaped-ready").write_text(str(os.getpid()))\n'
                   'for i in range(8):\n'
                   ' if os.fork()==0: time.sleep(120); os._exit(0)\n'
                   ' time.sleep(0.2)\n'
                   'time.sleep(120)')
        code = ('import subprocess,sys,time,pathlib\n'
                f'subprocess.Popen([sys.executable,"-c",{escaped!r}])\n'
                'time.sleep(0.5)\npathlib.Path("descendants-ready").write_text("ready")\ntime.sleep(120)')
        self.start(['print("retained")', code, '42'], grace=0)
        self.running()
        deadline = time.monotonic() + 10
        while not (self.output / 'descendants-ready').exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertTrue((self.output / 'descendants-ready').exists())
        self.assertTrue((self.output / 'escaped-ready').exists())
        execution.cancel(self.output)
        self.assertEqual(self.finish('cancelled')['cleanup']['method'], 'forced')

    def test_gate_eof_without_kernel(self):
        import execution
        from linux_lifecycle import LinuxService
        service = LinuxService(self.output, 30)
        with (self.output / 'direct.stdout').open('w') as stdout, (self.output / 'direct.stderr').open('w') as stderr:
            process = subprocess.Popen(service.command([sys.executable, '-I', str(Path(execution.__file__).resolve()),
                                                         '--engine', str(self.output)]),
                                       stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, text=True, close_fds=True)
            try:
                service.assign(process)
                self.assertFalse((self.output / 'kernel.json').exists())
                process.stdin.close()
                self.assertNotEqual(process.wait(timeout=15), 0)
                self.assert_empty()
            finally:
                _close_control(process, {})
                service.terminate(); service.close()
                process.wait(timeout=15)

    def test_wrong_unit_identity_cannot_be_stopped(self):
        from unittest.mock import patch
        import linux_lifecycle
        import execution
        service = linux_lifecycle.LinuxService(self.output, 30)
        with (self.output / 'direct.stdout').open('w') as stdout, (self.output / 'direct.stderr').open('w') as stderr:
            process = subprocess.Popen(service.command([sys.executable, '-I', str(Path(execution.__file__).resolve()),
                                                         '--engine', str(self.output)]),
                                       stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, text=True, close_fds=True)
            try:
                service.assign(process)
                snapshot = _unit_snapshot(service.unit)
                snapshot['properties']['Description'] = 'unrelated unit'
                with patch.object(linux_lifecycle, '_unit_snapshot', return_value=snapshot), patch.object(linux_lifecycle, '_command') as command:
                    with self.assertRaisesRegex(RuntimeError, 'OWNERSHIP_NOT_CONFIRMED'):
                        service.terminate()
                    command.assert_not_called()
                process.stdin.close(); process.wait(timeout=15)
                self.assert_empty()
            finally:
                _close_control(process, {})
                service.terminate(); service.close()
                process.wait(timeout=15)

    def test_failed_engine_start(self):
        from linux_lifecycle import LinuxService
        service = LinuxService(self.output, 30)
        with (self.output / 'direct.stdout').open('w') as stdout, (self.output / 'direct.stderr').open('w') as stderr:
            process = subprocess.Popen(service.command([sys.executable, '-I', str(self.output / 'missing-engine.py')]),
                                       stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, text=True, close_fds=True)
            try:
                with self.assertRaises((RuntimeError, FileNotFoundError, ProcessLookupError)):
                    service.assign(process)
                self.assertNotEqual(process.wait(timeout=15), 0)
                self.assertFalse((self.output / 'kernel.json').exists())
            finally:
                _close_control(process, {})
                service.terminate(); service.close(); process.wait(timeout=15)
        self.assertEqual(_unit_snapshot(service.unit)['properties'].get('MainPID', '0'), '0')

    def test_repeated_runs_use_distinct_units(self):
        root = self.output
        units = []
        for index in range(3):
            self.output = root / str(index)
            self.output.mkdir()
            self.start(['print("repeat")'])
            self.finish('succeeded')
            units.append(json.loads((self.output / 'service.json').read_bytes())['unit'])
        self.assertEqual(len(set(units)), 3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument('--suite', action='store_true')
    mode.add_argument('--supervise', action='store_true')
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PreflightFailureTests))
        return 0 if result.wasSuccessful() else 1
    if args.output is None:
        parser.error("this mode requires --output")
    if args.supervise:
        import execution
        result = execution._supervise(args.output, json.loads((args.output / 'engine-request.json').read_bytes()))
        return 0 if result['state'] == 'succeeded' else 1
    if args.suite:
        args.output.mkdir(parents=True, exist_ok=False)
        LinuxLifecycleTests.evidence_root = args.output.resolve()
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LinuxLifecycleTests))
        return 0 if result.wasSuccessful() else 1
    report = preflight(args.output)
    print(report["state"])
    if report.get("error"):
        print(report["error"], file=sys.stderr)
    return 0 if report["state"] == "succeeded" else 1


if __name__ == "__main__":
    sys.exit(main())
