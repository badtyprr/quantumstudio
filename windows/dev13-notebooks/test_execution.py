"""Real Windows process/kernel failure tests, using an explicitly selected profile.

Run with the locked environment's Python. Fixtures exercise the private engine;
they do not add arbitrary notebooks to the public contract allowlist.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import execution


class PlatformProfileTests(unittest.TestCase):
    def test_both_original_contracts_select_only_the_host_profile(self):
        for name in ("ibm019", "ibm020"):
            contract = json.loads((execution.ROOT / "contracts" / (name + ".json")).read_bytes())
            for platform, expected in (("win32", "qiskit-aer-win-py312"), ("linux", "qiskit-aer-linux-py312")):
                with self.subTest(contract=name, platform=platform), patch.object(execution.sys, "platform", platform):
                    with patch.object(execution, "profile_for", return_value={"platform": platform}) as lookup:
                        self.assertEqual(execution.contract_profile(contract), {"platform": platform})
                        lookup.assert_called_once_with(expected)

    def test_unsupported_host_rejected_before_environment_or_source_access(self):
        for name in ("ibm019", "ibm020"):
            with self.subTest(contract=name), patch.object(execution.sys, "platform", "darwin"):
                with patch.object(execution, "profile_for") as lookup, patch.object(execution, "inspect_environment") as inspect:
                    with self.assertRaisesRegex(ValueError, "UNSUPPORTED_CONTRACT_PLATFORM"):
                        execution.validate_request({"contract": name, "source": "must-not-be-read"})
                    lookup.assert_not_called()
                    inspect.assert_not_called()

    def test_legacy_profile_still_requires_matching_platform(self):
        with patch.object(execution.sys, "platform", "linux"):
            with patch.object(execution, "profile_for", return_value={"platform": "win32"}):
                with self.assertRaisesRegex(ValueError, "UNSUPPORTED_CONTRACT_PLATFORM"):
                    execution.contract_profile({"profile": "qir-win-py312"})
        with patch.object(execution.sys, "platform", "win32"):
            with patch.object(execution, "profile_for", return_value={"platform": "win32"}) as lookup:
                execution.contract_profile({"profile": "qir-win-py312"})
                lookup.assert_called_once_with("qir-win-py312")

    def test_malformed_maps_rejected(self):
        for mapping in ([], {"darwin": "x"}, {"win32": 1}):
            with self.subTest(mapping=mapping), patch.object(execution.sys, "platform", "win32"):
                with self.assertRaisesRegex(ValueError, "INVALID_PLATFORM_PROFILES"):
                    execution.contract_profile({"profiles": mapping})

    def test_mapped_unknown_profile_cannot_bypass_allowlist(self):
        with patch.object(execution.sys, "platform", "linux"):
            with self.assertRaisesRegex(ValueError, "UNKNOWN_PROFILE"):
                execution.contract_profile({"profiles": {"linux": "arbitrary-unreviewed"}})

    def test_mapped_profile_cannot_claim_a_different_platform(self):
        with patch.object(execution.sys, "platform", "linux"):
            with patch.object(execution, "profile_for", return_value={"platform": "win32"}):
                with self.assertRaisesRegex(ValueError, "UNSUPPORTED_CONTRACT_PLATFORM"):
                    execution.contract_profile({"profiles": {"linux": "qiskit-aer-linux-py312"}})


class LifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = execution.profile_for("qiskit-aer-win-py312")
        cls.identity = execution.inspect_environment(Path(sys.executable), cls.profile)

    def setUp(self):
        evidence = os.environ.get("DEV13_TEST_EVIDENCE")
        if evidence:
            self.output = Path(evidence) / self._testMethodName
        else:
            self.temp = tempfile.TemporaryDirectory(prefix="dev13-test-")
            self.addCleanup(self.temp.cleanup)
            self.output = Path(self.temp.name) / "run"
        self.output.mkdir(parents=True, exist_ok=False)

    def fixture(self, code, timeout=10, grace=5):
        import nbformat
        notebook = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(text) for text in code])
        raw = nbformat.writes(notebook).encode()
        (self.output / "source-original.ipynb").write_bytes(raw)
        return dict(python=sys.executable, identity=self.identity, contract_sha256="test-fixture",
                    profile=dict(self.profile, default_cell_timeout_seconds=timeout, cancel_grace_seconds=grace),
                    witness='print("{}")', contract=dict(id="test-fixture", source={"sha256": execution.digest(raw)},
                    code_cells=list(range(len(code))), preamble=None, required_images=[], required_text={}))

    def records(self):
        return json.loads((self.output / "cells.json").read_bytes())

    def test_checkpoint_waits_for_brief_windows_reader(self):
        path = self.output / "checkpoint.json"
        execution.atomic_json(path, {"version": 1})
        reader = path.open("rb")
        closer = threading.Timer(0.2, reader.close)
        closer.start()
        try:
            execution.atomic_json(path, {"version": 2})
        finally:
            closer.join()
            reader.close()
        self.assertEqual(json.loads(path.read_bytes()), {"version": 2})

    def assert_cleanup(self, result):
        self.assertEqual(result["cleanup"]["active_processes"], 0)
        self.assertIs(result["cleanup"]["kernel_job_membership"], True)

    def test_source_error_retains_previous_outputs(self):
        config = self.fixture(['print("retained")', 'raise ValueError("source failure")', 'print("must not run")'])
        result = execution._supervise(self.output, config)
        self.assertEqual(result["state"], "failed")
        self.assert_cleanup(result)
        self.assertEqual([c["state"] for c in self.records()], ["succeeded", "failed", "not_run", "not_run"])
        notebook = json.loads((self.output / "executed.ipynb").read_bytes())
        self.assertEqual(notebook["cells"][0]["outputs"][0]["text"], "retained\n")
        self.assertEqual(notebook["cells"][1]["outputs"][0]["ename"], "ValueError")

    def test_timeout_retains_completed_cell(self):
        result = execution._supervise(self.output, self.fixture(['print("retained")', 'import time; time.sleep(30)', '42'], timeout=1))
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["error"]["type"], "CellTimeoutError")
        self.assertEqual(self.records()[2]["state"], "not_run")
        self.assert_cleanup(result)

    def test_original_displayed_result_is_required(self):
        config = self.fixture(["'wrong'"])
        config["contract"]["required_text"] = {"0": "'correct'"}
        result = execution._supervise(self.output, config)
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["authored_verification"], "failed")
        self.assertIn("SOURCE_RESULT_MISMATCH", result["error"]["message"])
        self.assert_cleanup(result)

    def test_wrong_interpreter_profile_rejected(self):
        with self.assertRaisesRegex(ValueError, "ENVIRONMENT_MISMATCH: python"):
            execution.inspect_environment(Path(sys.executable), dict(self.profile, python="0.0.0"))

    def test_reviewed_setup_preserves_source_and_inventory(self):
        config = self.fixture(['%pip --version', '42'])
        config['contract']['setup'] = {'cell': 0, 'commands': ['--version']}
        result = execution._supervise(self.output, config)
        self.assertEqual(result['state'], 'succeeded')
        setup = json.loads((self.output / 'setup-evidence.json').read_bytes())
        self.assertTrue(setup['accepted'])
        self.assertEqual(setup['before'], setup['after'])
        self.assertEqual([c['exit_code'] for c in setup['commands']], [0])
        notebook = json.loads((self.output / 'executed.ipynb').read_bytes())
        original = [notebook['cells'][r['index']]['source'] for r in self.records() if r['original_index'] is not None]
        self.assertEqual(original, ['%pip --version', '42'])
        self.assert_cleanup(result)

    def test_early_setup_failure_cannot_be_hidden_by_later_success(self):
        config = self.fixture(['%pip install --dev13-invalid-option\n%pip --version', '42'])
        config['contract']['setup'] = {'cell': 0, 'commands': ['install --dev13-invalid-option', '--version']}
        result = execution._supervise(self.output, config)
        self.assertEqual(result['state'], 'failed')
        setup = json.loads((self.output / 'setup-evidence.json').read_bytes())
        self.assertFalse(setup['accepted'])
        self.assertEqual(len(setup['commands']), 1)
        self.assertNotEqual(setup['commands'][0]['exit_code'], 0)
        self.assertEqual(next(r['state'] for r in self.records() if r['original_index'] == 1), 'not_run')
        self.assert_cleanup(result)

    def test_setup_metadata_drift_stops_later_cells(self):
        source = ('%pip --version\nimport pathlib,sys\n'
                  'directory=pathlib.Path("dev13_drift-0.dist-info"); directory.mkdir()\n'
                  '(directory/"METADATA").write_text("Metadata-Version: 2.1\\nName: dev13-drift\\nVersion: 0\\n")\n'
                  'sys.path.insert(0,str(pathlib.Path.cwd()))')
        config = self.fixture([source, '42'])
        config['contract']['setup'] = {'cell': 0, 'commands': ['--version']}
        result = execution._supervise(self.output, config)
        self.assertEqual(result['state'], 'failed')
        setup = json.loads((self.output / 'setup-evidence.json').read_bytes())
        self.assertIn('dev13-drift', setup['after'])
        self.assertFalse(setup['accepted'])
        self.assertEqual(next(r['state'] for r in self.records() if r['original_index'] == 1), 'not_run')
        self.assert_cleanup(result)

    def test_setup_scrubs_inherited_pip_and_child_python_settings(self):
        config = self.fixture(['%pip --version\nimport os\nassert os.environ["PIP_NO_INDEX"] == "1"\n'
                               'assert "PIP_INDEX_URL" not in os.environ\nassert "PYTHONPATH" not in os.environ'])
        config['contract']['setup'] = {'cell': 0, 'commands': ['--version']}
        with patch.dict(os.environ, {'PIP_INDEX_URL': 'https://invalid.example/', 'PIP_CONFIG_FILE': 'invalid',
                                     'PYTHONPATH': 'invalid', 'PIP_REQUIREMENT': 'invalid'}):
            result = execution._supervise(self.output, config)
        self.assertEqual(result['state'], 'succeeded')
        self.assert_cleanup(result)

    def test_missing_setup_package_fails_without_contacting_inherited_index(self):
        from http.server import BaseHTTPRequestHandler, HTTPServer
        requests = []

        class Index(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                self.send_response(404)
                self.end_headers()

            def log_message(self, *args):
                pass

        server = HTTPServer(('127.0.0.1', 0), Index)
        listener = threading.Thread(target=server.serve_forever)
        listener.start()
        config = self.fixture(['%pip install dev13-missing-package-proof-000000 --quiet', '42'])
        config['contract']['setup'] = {'cell': 0, 'commands': ['install dev13-missing-package-proof-000000 --quiet']}
        try:
            with patch.dict(os.environ, {'PIP_INDEX_URL': f'http://127.0.0.1:{server.server_port}/simple'}):
                result = execution._supervise(self.output, config)
        finally:
            server.shutdown()
            listener.join()
            server.server_close()
        self.assertEqual(result['state'], 'failed')
        self.assertEqual(requests, [])
        self.assertEqual(next(r['state'] for r in self.records() if r['original_index'] == 1), 'not_run')
        self.assert_cleanup(result)

    def test_semantic_rejection_retains_successful_source_and_evidence(self):
        config = self.fixture(['42'])
        config['witness'] = 'print(\'{"accepted": false, "reason": "unmeasured results"}\')'
        config['contract']['acceptance_field'] = 'accepted'
        result = execution._supervise(self.output, config)
        self.assertEqual(result['state'], 'failed')
        self.assertEqual(result['original_execution'], 'succeeded')
        self.assertEqual(result['authored_verification'], 'failed')
        self.assertEqual(result['independent_results']['reason'], 'unmeasured results')
        self.assert_cleanup(result)

    def test_ambient_pythonpath_cannot_replace_locked_package(self):
        foreign = self.output / "foreign"
        foreign.mkdir()
        (foreign / "qiskit.py").write_text('raise RuntimeError("ambient package replaced locked Qiskit")', encoding="utf-8")
        config = self.fixture(['import qiskit; assert qiskit.__version__ == "2.2.3"'])
        with patch.dict(os.environ, {"PYTHONPATH": str(foreign)}):
            result = execution._supervise(self.output, config)
        self.assertEqual(result["state"], "succeeded")
        self.assert_cleanup(result)

    def test_kernel_crash_is_failure(self):
        result = execution._supervise(self.output, self.fixture(['print("retained")', 'import os; os._exit(23)', '42']))
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["error"]["type"], "DeadKernelError")
        self.assertEqual(self.records()[0]["state"], "succeeded")
        self.assertEqual(self.records()[1]["state"], "failed")
        self.assertEqual(self.records()[2]["state"], "not_run")
        self.assert_cleanup(result)

    def cancellation(self, grace):
        unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"], creationflags=subprocess.CREATE_NO_WINDOW)
        self.addCleanup(lambda: unrelated.wait(timeout=10))
        self.addCleanup(unrelated.terminate)
        config = self.fixture(['print("retained")',
            'import subprocess,sys,time\nchild=subprocess.Popen([sys.executable,"-c","import time; time.sleep(120)"])\nprint(child.pid,flush=True)\ntime.sleep(120)', '42'], grace=grace)
        errors = []
        requested_at = []

        def request():
            try:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    path = self.output / "cells.json"
                    if path.exists() and json.loads(path.read_bytes())[1]["state"] == "running":
                        # Let the kernel create its descendant before cancelling.
                        time.sleep(0.5)
                        requested_at.append(time.monotonic())
                        execution.cancel(self.output)
                        execution.cancel(self.output)
                        return
                    time.sleep(0.05)
                raise AssertionError("Cell never started")
            except BaseException as error:
                errors.append(error)

        requester = threading.Thread(target=request)
        requester.start()
        try:
            result = execution._supervise(self.output, config)
        finally:
            requester.join(timeout=35)
        self.assertFalse(errors, errors)
        self.assertTrue(requested_at)
        self.assertLess(time.monotonic() - requested_at[0], 17)
        self.assertEqual(result["state"], "cancelled")
        self.assertEqual(result["original_execution"], "incomplete")
        self.assert_cleanup(result)
        self.assertIsNone(unrelated.poll())
        self.assertEqual(self.records()[0]["state"], "succeeded")
        self.assertEqual(self.records()[1]["state"], "interrupted")
        self.assertEqual(self.records()[2]["state"], "not_run")
        before = (self.output / "status.json").read_bytes()
        execution.cancel(self.output)
        self.assertEqual(before, (self.output / "status.json").read_bytes())
        if grace == 0:
            self.assertEqual(result["cleanup"]["method"], "forced")

    def test_cancel_and_descendant_cleanup(self):
        self.cancellation(5)

    def test_forced_cancel_keeps_checkpoint_and_unrelated_process(self):
        self.cancellation(0)

    def test_assignment_failure_never_starts_kernel(self):
        config = self.fixture(['42'])
        with patch.object(execution._WindowsJob, "assign", side_effect=OSError("assignment test")):
            with self.assertRaisesRegex(OSError, "assignment test"):
                execution._supervise(self.output, config)
        self.assertFalse((self.output / "kernel.json").exists())
        self.assertEqual(json.loads((self.output / "status.json").read_bytes())["state"], "failed")

    def cleanup_failure(self, error):
        config = self.fixture(['42'])
        with patch.object(execution._WindowsJob, 'assign', side_effect=OSError('assignment test')), \
                patch.object(execution._WindowsJob, 'terminate', side_effect=error):
            with self.assertRaisesRegex(OSError, 'assignment test'):
                execution._supervise(self.output, config)
        result = json.loads((self.output / 'status.json').read_bytes())
        self.assertEqual(result['state'], 'failed')
        self.assertTrue(result['cleanup']['unconfirmed'])
        self.assertEqual(result['cleanup']['errors'][0]['step'], 'terminate_owned_containment')
        self.assertFalse((self.output / 'kernel.json').exists())

    def test_stop_timeout_preserves_terminal_failure(self):
        self.cleanup_failure(TimeoutError('stop deadline'))

    def test_ownership_refusal_preserves_terminal_failure(self):
        self.cleanup_failure(RuntimeError('UNIT_OWNERSHIP_NOT_CONFIRMED'))

    def test_final_close_failure_revokes_success(self):
        real_close = execution._WindowsJob.close

        def failed_close(job):
            real_close(job)
            raise OSError('close failure')

        with patch.object(execution._WindowsJob, 'close', failed_close):
            result = execution._supervise(self.output, self.fixture(['42']))
        self.assertEqual(result['state'], 'failed')
        self.assertTrue(result['cleanup']['unconfirmed'])
        self.assertEqual(json.loads((self.output / 'status.json').read_bytes())['state'], 'failed')

    def control_eof(self, started):
        config = self.fixture(['print("retained")', 'import time; time.sleep(120)', '42'], timeout=180)
        execution.atomic_json(self.output / 'engine-request.json', config)
        job = execution._WindowsJob()
        process = None
        try:
            with (self.output / 'engine.stdout').open('w') as stdout, (self.output / 'engine.stderr').open('w') as stderr:
                process = subprocess.Popen([sys.executable, '-I', str(Path(execution.__file__).resolve()),
                                            '--engine', str(self.output)], stdin=subprocess.PIPE,
                                           stdout=stdout, stderr=stderr, text=True,
                                           creationflags=subprocess.CREATE_NO_WINDOW)
                job.assign(process)
                if started:
                    process.stdin.write('start\n')
                    process.stdin.flush()
                    deadline = time.monotonic() + 30
                    while time.monotonic() < deadline:
                        path = self.output / 'cells.json'
                        if path.exists() and json.loads(path.read_bytes())[1]['state'] == 'running':
                            break
                        time.sleep(0.05)
                    else:
                        self.fail('Second cell never started')
                process.stdin.close()
                self.assertNotEqual(process.wait(timeout=15), 0)
            if started:
                result = json.loads((self.output / 'engine-result.json').read_bytes())
                self.assertEqual(result['state'], 'failed')
                self.assertEqual(result['control_event'], 'control_eof')
                self.assertEqual([r['state'] for r in self.records()], ['succeeded', 'interrupted', 'not_run', 'not_run'])
                notebook = json.loads((self.output / 'executed.ipynb').read_bytes())
                self.assertEqual(notebook['cells'][0]['outputs'][0]['text'], 'retained\n')
            else:
                self.assertFalse((self.output / 'kernel.json').exists())
        finally:
            if process is not None and process.stdin and not process.stdin.closed:
                process.stdin.close()
            job.terminate()
            if process is not None:
                process.wait(timeout=10)
            job.close()

    def test_control_eof_before_gate_never_starts_kernel(self):
        self.control_eof(False)

    def test_control_eof_after_checkpoint_interrupts_execution(self):
        self.control_eof(True)

    def test_public_route_rejects_unknown_and_changed_source(self):
        source = self.output / "source.ipynb"
        source.write_text("{}", encoding="utf-8")
        target = self.output / "rejected"
        request = dict(contract="unreviewed", source=source, environment=Path(sys.executable).parent.parent, output=target)
        with self.assertRaisesRegex(ValueError, "UNKNOWN_CONTRACT"):
            execution.execute(request)
        request["contract"] = "ibm019"
        with self.assertRaisesRegex(ValueError, "SOURCE_HASH_MISMATCH"):
            execution.execute(request)
        self.assertFalse(target.exists())

    def test_public_route_refuses_existing_output(self):
        marker = self.output / "keep"
        marker.write_bytes(b"original")
        with self.assertRaises(FileExistsError):
            execution.execute(dict(output=self.output))
        self.assertEqual(marker.read_bytes(), b"original")


if __name__ == "__main__":
    unittest.main(verbosity=2)
