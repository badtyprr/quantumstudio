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
