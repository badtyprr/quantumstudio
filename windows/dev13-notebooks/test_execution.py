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


class SelectedCellTests(unittest.TestCase):
    """Synthetic private-engine checks; never execute the QB007 source or SDK."""

    def fixture(self):
        import nbformat
        cells = [nbformat.v4.new_code_cell("value += 1"),
                 nbformat.v4.new_code_cell("raise RuntimeError('OMITTED_SENTINEL')"),
                 nbformat.v4.new_markdown_cell("Original retained prose"),
                 nbformat.v4.new_code_cell("value += 10")]
        contract = dict(id="synthetic-selected", route=execution.SELECTED_ROUTE,
                        selected_cells=[0, 3], code_cells=[0, 3], excluded_code_cells={"1": "not selected"},
                        preamble="value = 0", required_images=[], required_text={})
        return cells, contract

    def run_synthetic(self, cells, contract, fail_at=None, before_execute=None, witness=None):
        import asyncio
        import contextlib
        import io
        from types import SimpleNamespace
        import nbformat

        temporary = tempfile.TemporaryDirectory(prefix="dev13-selected-unit-")
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        raw = nbformat.writes(nbformat.v4.new_notebook(cells=cells)).encode()
        (output / "source-original.ipynb").write_bytes(raw)
        calls = []

        class Client:
            def __init__(self, notebook, **kwargs):
                self.namespace = {}

            @contextlib.asynccontextmanager
            async def async_setup_kernel(self, **kwargs):
                yield

            async def async_execute_cell(self, cell, index):
                calls.append(cell.source)
                if before_execute:
                    await before_execute(cell, index)
                if index == fail_at:
                    raise asyncio.CancelledError()
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    exec(compile(cell.source, "authored-synthetic-fixture", "exec"), self.namespace)
                cell.execution_count = index + 1
                if stdout.getvalue():
                    cell.outputs = [nbformat.v4.new_output("stream", name="stdout", text=stdout.getvalue())]

        config = dict(contract=contract, profile={"default_cell_timeout_seconds": 3},
                      witness='print("{\\"accepted\\": true}")')
        if witness is not None:
            config["witness"] = witness
        with patch("nbclient.NotebookClient", Client), patch("jupyter_client.AsyncKernelManager",
                return_value=SimpleNamespace(provisioner=SimpleNamespace(pid=123))):
            outcome = asyncio.run(execution._run_notebook(output, config))
        return output, outcome, calls, raw

    def test_selected_engine_never_executes_omitted_sentinel(self):
        cells, contract = self.fixture()
        output, result, calls, raw = self.run_synthetic(cells, contract)
        self.assertEqual(result["state"], "succeeded")
        self.assertEqual(result["selected_execution"], "succeeded")
        self.assertEqual(result["original_execution"], "not_executed_as_whole")
        self.assertFalse(result["whole_notebook_complete"])
        self.assertFalse(any("OMITTED_SENTINEL" in code for code in calls))
        self.assertEqual((output / "source-original.ipynb").read_bytes(), raw)
        rows = json.loads((output / "source-disposition.json").read_bytes())["cells"]
        self.assertEqual([r["state"] for r in rows], ["succeeded", "excluded_by_contract", "not_executable", "succeeded"])
        executed = json.loads((output / "executed.ipynb").read_bytes())["cells"]
        self.assertEqual([c["source"] for c in executed][1:3], ["value += 1", "value += 10"])

    def test_whole_route_still_executes_every_code_cell(self):
        cells, contract = self.fixture()
        cells[1].source = "value += 100"
        contract.pop("selected_cells")
        contract.pop("excluded_code_cells")
        contract.update(route="notebook", code_cells=[0, 1, 3])
        output, result, calls, _ = self.run_synthetic(cells, contract)
        self.assertIn("value += 100", calls)
        self.assertEqual(result["original_execution"], "succeeded")
        self.assertNotIn("selected_execution", result)
        self.assertFalse((output / "source-disposition.json").exists())
        self.assertEqual(len(json.loads((output / "executed.ipynb").read_bytes())["cells"]), 6)

    def test_cancelled_selected_checkpoint_keeps_all_dispositions(self):
        cells, contract = self.fixture()
        output, result, _, _ = self.run_synthetic(cells, contract, fail_at=2)
        self.assertEqual(result["selected_execution"], "incomplete")
        self.assertEqual(result["original_execution"], "not_executed_as_whole")
        self.assertFalse(result["whole_notebook_complete"])
        rows = json.loads((output / "source-disposition.json").read_bytes())["cells"]
        self.assertEqual([r["state"] for r in rows], ["succeeded", "excluded_by_contract", "not_executable", "interrupted"])

    def test_lost_report_recovery_retains_selected_scope(self):
        cells, contract = self.fixture()
        output, _, _, _ = self.run_synthetic(cells, contract)
        records = json.loads((output / "cells.json").read_bytes())
        records[2]["state"] = "running"
        execution.atomic_json(output / "cells.json", records)
        status = dict(route=execution.SELECTED_ROUTE)
        execution._recover_checkpoint_disposition(output, status)
        self.assertEqual(status["selected_execution"], "incomplete")
        self.assertEqual(status["original_execution"], "not_executed_as_whole")
        rows = json.loads((output / "source-disposition.json").read_bytes())["cells"]
        self.assertEqual(rows[3]["state"], "interrupted")
        self.assertEqual(rows[1]["state"], "excluded_by_contract")

    def test_selection_schema_rejects_malformed_indices(self):
        cells, original = self.fixture()
        for selection in ([], [True], [-1], [4], [0, 0], [3, 0], [2], "0,3", None):
            with self.subTest(selection=selection):
                contract = dict(original, selected_cells=selection, code_cells=selection)
                with self.assertRaisesRegex(ValueError, "INVALID_CELL_SELECTION"):
                    execution._execution_indices(contract, cells)

    def test_exclusions_and_output_requirements_are_complete(self):
        cells, original = self.fixture()
        for change in ({"excluded_code_cells": {}}, {"excluded_code_cells": {"1": ""}},
                       {"excluded_code_cells": {"1": "reason", "2": "extra"}},
                       {"required_images": [1]}, {"required_text": {"1": "bad"}},
                       {"setup": {"cell": 0}}, {"code_cells": [0]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                execution._execution_indices(dict(original, **change), cells)

    def test_selection_requires_explicit_route(self):
        cells, contract = self.fixture()
        for route in ("notebook", "unknown"):
            with self.subTest(route=route), self.assertRaises(ValueError):
                execution._execution_indices(dict(contract, route=route), cells)

    def test_public_changed_source_witness_or_selection_rejected_before_environment(self):
        import copy
        import nbformat
        cells, contract = self.fixture()
        raw = nbformat.writes(nbformat.v4.new_notebook(cells=cells)).encode()
        contract.update(source={"sha256": execution.digest(raw), "cells": [
            dict(index=i, type=c.cell_type, sha256=execution.digest(c.source.encode())) for i, c in enumerate(cells)]},
            witness={"path": "witness.py", "sha256": execution.digest(b'print("{}")')})
        for kind in ("source", "witness", "selection"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "contracts").mkdir()
                current = copy.deepcopy(contract)
                if kind == "selection":
                    current["selected_cells"] = [1, 0]
                (root / "contracts/qb007.json").write_text(json.dumps(current))
                (root / "source.ipynb").write_bytes(raw + (b" " if kind == "source" else b""))
                (root / "witness.py").write_bytes(b'print("changed")' if kind == "witness" else b'print("{}")')
                with patch.object(execution, "ROOT", root), patch.object(execution, "contract_profile", return_value={"platform": "win32"}), patch.object(execution, "inspect_environment") as inspect:
                    with self.assertRaises(ValueError):
                        execution.validate_request(dict(contract="qb007", source=root / "source.ipynb", environment=root))
                    inspect.assert_not_called()

    def test_qb007_contract_accounts_all_original_cells_without_running_them(self):
        contract = json.loads((execution.ROOT / "contracts/qb007.json").read_bytes())
        descriptors = [{"cell_type": c["type"]} for c in contract["source"]["cells"]]
        self.assertEqual(execution._execution_indices(contract, descriptors), [7, 9, 11, 14, 23, 25])
        self.assertEqual(len(descriptors), 33)
        self.assertEqual(len(contract["excluded_code_cells"]), 15)
        self.assertEqual(sum(c["cell_type"] == "markdown" for c in descriptors), 12)
        witness = execution.canonical(execution.ROOT / contract["witness"]["path"])
        self.assertEqual(execution.digest(witness), contract["witness"]["sha256"])
        compile(witness, "authored-qb007-witness-not-executed", "exec")


class PostCellObserverTests(unittest.TestCase):
    """Authored synthetic Python only: no SDK imports, kernels or child processes."""

    run_synthetic = SelectedCellTests.run_synthetic

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="dev13-observer-unit-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        patcher = patch.object(execution, "ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def source(self, name, text):
        (self.root / name).write_text(text, encoding="utf-8")
        return dict(path=name, sha256=execution.digest(text.encode("utf-8")))

    def fixture(self, observer="assert value == 1", lifecycle=False):
        import nbformat
        cells = [nbformat.v4.new_code_cell("value = 1; print('original-output')"),
                 nbformat.v4.new_markdown_cell("unchanged prose"),
                 nbformat.v4.new_code_cell("value = 2")]
        descriptor = dict(after_original_index=0, role="postcell-observer",
                          **self.source("observe.py", observer))
        contract = dict(id="synthetic-observer", preamble="", code_cells=[0, 2],
                        required_images=[], required_text={}, post_cell_observers=[descriptor])
        if lifecycle:
            contract["observer_lifecycle"] = dict(
                bootstrap=self.source("bootstrap.py", "original = object(); hook = original; hook = 'wrapped'"),
                cleanup=self.source("cleanup.py", "hook = original; assert hook is original; print('restored')"),
                cleanup_timeout_seconds=1)
        return cells, contract

    def test_success_order_outputs_and_association(self):
        cells, contract = self.fixture(lifecycle=True)
        output, result, calls, raw = self.run_synthetic(cells, contract)
        self.assertEqual(result["state"], "succeeded")
        self.assertEqual(result["authored_observation"], "succeeded")
        self.assertEqual(result["observer_cleanup"], "succeeded")
        self.assertEqual(calls[2], "assert value == 1")
        self.assertEqual(calls[3], "value = 2")
        self.assertIn("restored", calls[-2])
        records = json.loads((output / "cells.json").read_bytes())
        self.assertEqual(records[2]["after_original_index"], 0)
        self.assertIsNone(records[2]["original_index"])
        self.assertEqual(records[-1]["authored_role"], "independent-witness")
        notebook = json.loads((output / "executed.ipynb").read_bytes())
        originals = [notebook["cells"][r["index"]] for r in records if r["original_index"] is not None]
        self.assertEqual([execution.cell_text(c) for c in originals], [c.source for c in cells])
        self.assertIn("original-output", "".join(originals[0]["outputs"][0]["text"]))
        self.assertEqual((output / "source-original.ipynb").read_bytes(), raw)

    def test_failed_observer_preserves_original_and_stops_next(self):
        cells, contract = self.fixture("raise ValueError('OBSERVATION_FAILED')", lifecycle=True)
        output, result, calls, raw = self.run_synthetic(cells, contract)
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["authored_observation"], "failed")
        self.assertEqual(result["original_execution"], "incomplete")
        self.assertEqual(result["authored_verification"], "not_run")
        self.assertEqual(result["observer_cleanup"], "succeeded")
        self.assertNotIn("value = 2", calls)
        records = json.loads((output / "cells.json").read_bytes())
        self.assertEqual(records[1]["state"], "succeeded")
        self.assertEqual(records[2]["state"], "failed")
        notebook = json.loads((output / "executed.ipynb").read_bytes())
        self.assertIn("original-output", "".join(notebook["cells"][1]["outputs"][0]["text"]))
        self.assertEqual((output / "source-original.ipynb").read_bytes(), raw)

    def test_last_original_success_does_not_hide_observer_failure(self):
        cells, contract = self.fixture("raise ValueError('LAST_OBSERVER')")
        contract["post_cell_observers"][0]["after_original_index"] = 2
        output, result, calls, raw = self.run_synthetic(cells, contract)
        self.assertEqual(result["original_execution"], "succeeded")
        self.assertEqual(result["authored_observation"], "failed")
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["authored_verification"], "not_run")

    def test_original_exception_survives_cleanup_exception(self):
        cells, contract = self.fixture(lifecycle=True)
        cells[0].source = "raise ValueError('ORIGINAL_ERROR')"
        contract["observer_lifecycle"]["cleanup"] = self.source("cleanup.py", "raise RuntimeError('CLEANUP_ERROR')")
        output, result, calls, raw = self.run_synthetic(cells, contract)
        self.assertEqual(result["error"]["type"], "ValueError")
        self.assertEqual(result["error"]["message"], "ORIGINAL_ERROR")
        self.assertEqual(result["observer_cleanup"], "failed")
        self.assertEqual(result["authored_observation"], "not_run")
        records = json.loads((output / "cells.json").read_bytes())
        self.assertEqual(records[-2]["error"]["message"], "CLEANUP_ERROR")
        self.assertNotIn("value = 2", calls)

    def test_cleanup_failure_prevents_witness(self):
        cells, contract = self.fixture(lifecycle=True)
        contract["observer_lifecycle"]["cleanup"] = self.source("cleanup.py", "raise ValueError('cleanup')")
        output, result, calls, raw = self.run_synthetic(cells, contract)
        self.assertEqual(result["original_execution"], "succeeded")
        self.assertEqual(result["authored_observation"], "succeeded")
        self.assertEqual(result["observer_cleanup"], "failed")
        self.assertEqual(result["authored_verification"], "not_run")
        self.assertEqual(result["state"], "failed")

    def test_partial_bootstrap_failure_attempts_cleanup(self):
        cells, contract = self.fixture(lifecycle=True)
        contract["observer_lifecycle"]["bootstrap"] = self.source("bootstrap.py", "original = object(); raise ValueError('BOOTSTRAP')")
        output, result, calls, raw = self.run_synthetic(cells, contract)
        self.assertEqual(result["observer_bootstrap"], "failed")
        self.assertEqual(result["observer_cleanup"], "succeeded")
        self.assertNotIn(cells[0].source, calls)

    def test_cleanup_timeout_is_bounded_and_preserves_primary(self):
        import asyncio
        cells, contract = self.fixture("raise ValueError('PRIMARY')", lifecycle=True)
        async def delay(cell, index):
            if "authored-observer-cleanup" in cell.metadata.get("tags", []):
                await asyncio.sleep(30)
        started = time.monotonic()
        output, result, calls, raw = self.run_synthetic(cells, contract, before_execute=delay)
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual(result["error"]["message"], "PRIMARY")
        self.assertEqual(result["observer_cleanup"], "failed")
        records = json.loads((output / "cells.json").read_bytes())
        self.assertEqual(records[-2]["error"]["type"], "TimeoutError")

    def test_cancelled_observer_skips_cleanup_and_lost_report_recovers(self):
        cells, contract = self.fixture(lifecycle=True)
        output, result, calls, raw = self.run_synthetic(cells, contract, fail_at=2)
        self.assertEqual(result["authored_observation"], "interrupted")
        self.assertEqual(result["observer_cleanup"], "not_run")
        self.assertNotIn("value = 2", calls)
        records = json.loads((output / "cells.json").read_bytes())
        records[2]["state"] = "running"
        execution.atomic_json(output / "cells.json", records)
        status = {}
        execution._recover_checkpoint_disposition(output, status)
        self.assertEqual(status["authored_observation"], "interrupted")
        self.assertEqual(status["original_execution"], "incomplete")
        self.assertEqual(status["authored_verification"], "not_run")
        self.assertEqual(status["observer_cleanup"], "not_run")

    def test_source_timeout_or_dead_kernel_does_not_queue_cleanup(self):
        from nbclient.exceptions import DeadKernelError, CellTimeoutError
        for error in (CellTimeoutError("source timeout"), DeadKernelError("dead")):
            with self.subTest(error=type(error).__name__):
                cells, contract = self.fixture(lifecycle=True)
                async def fail(cell, index):
                    if index == 1:
                        raise error
                output, result, calls, raw = self.run_synthetic(cells, contract, before_execute=fail)
                self.assertEqual(result["observer_cleanup"], "not_run")
                self.assertEqual(len(calls), 2)

    def test_multiple_observers_run_once_in_source_order(self):
        cells, contract = self.fixture()
        contract["post_cell_observers"].append(dict(after_original_index=2, role="timing-postcell",
            **self.source("second observe ü.py", "assert value == 2; print('second-observer')")))
        output, result, calls, raw = self.run_synthetic(cells, contract)
        self.assertEqual(result["authored_observation"], "succeeded")
        self.assertEqual(calls.count("assert value == 1"), 1)
        self.assertEqual(calls.count("assert value == 2; print('second-observer')"), 1)
        records = json.loads((output / "cells.json").read_bytes())
        observers = [r for r in records if "after_original_index" in r]
        self.assertEqual([r["after_original_index"] for r in observers], [0, 2])

    def test_setup_check_failure_is_not_observer_or_source_failure(self):
        cells, contract = self.fixture(lifecycle=True)
        contract["setup"] = dict(cell=0, commands=["authored-stub"])
        with patch.object(execution, "_setup_observer", return_value="setup_stub = True"), patch.object(execution, "SETUP_CHECK", "raise ValueError('SETUP_FAILED')"):
            output, result, calls, raw = self.run_synthetic(cells, contract)
        records = json.loads((output / "cells.json").read_bytes())
        self.assertEqual(next(r for r in records if r["original_index"] == 0)["state"], "succeeded")
        self.assertEqual(result["authored_observation"], "not_run")
        self.assertEqual(result["observer_cleanup"], "succeeded")
        self.assertEqual(result["error"]["message"], "SETUP_FAILED")
        self.assertNotIn("value = 2", calls)

    def test_final_witness_failure_retains_successful_observation_and_cleanup(self):
        cells, contract = self.fixture(lifecycle=True)
        output, result, calls, raw = self.run_synthetic(cells, contract, witness="raise ValueError('WITNESS_FAILED')")
        self.assertEqual(result["original_execution"], "succeeded")
        self.assertEqual(result["authored_observation"], "succeeded")
        self.assertEqual(result["observer_cleanup"], "succeeded")
        self.assertEqual(result["authored_verification"], "failed")
        self.assertEqual(result["error"]["message"], "WITNESS_FAILED")
        self.assertEqual(calls.count("hook = original; assert hook is original; print('restored')"), 1)

    def test_descriptor_rejects_invalid_indices_roles_and_structure(self):
        cells, contract = self.fixture()
        original = contract["post_cell_observers"][0]
        variants = [None, {}, [None], [dict(original, extra=1)],
                    [dict(original, role="independent-witness")],
                    [dict(original), dict(original)],
                    [dict(original, after_original_index=2), dict(original)]]
        variants += [[dict(original, after_original_index=i)] for i in (True, -1, 1, 3, "0", 0.0)]
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ValueError):
                execution._observer_sources(dict(contract, post_cell_observers=value), cells)
        selected = dict(contract, route=execution.SELECTED_ROUTE, selected_cells=[2], code_cells=[2],
                        excluded_code_cells={"0": "omitted"})
        with self.assertRaises(ValueError):
            execution._observer_sources(selected, cells)

    def test_path_hash_and_resolved_escape_rejected(self):
        cells, contract = self.fixture()
        original = contract["post_cell_observers"][0]
        variants = [dict(original, path=p) for p in ("../observe.py", str(self.root / "observe.py"), "C:observe.py", "")]
        variants += [dict(original, sha256=h) for h in ("0" * 64, "F" * 64, None, "short")]
        for descriptor in variants:
            with self.subTest(descriptor=descriptor), self.assertRaises(ValueError):
                execution._observer_sources(dict(contract, post_cell_observers=[descriptor]), cells)
        original_resolve = Path.resolve
        def redirected(path, *args, **kwargs):
            if path.name == "observe.py":
                return self.root.parent / "outside.py"
            return original_resolve(path, *args, **kwargs)
        with patch.object(Path, "resolve", redirected), self.assertRaisesRegex(ValueError, "OBSERVER_PATH_ESCAPE"):
            execution._observer_sources(contract, cells)

    def test_lifecycle_schema_and_hashes_rejected(self):
        cells, contract = self.fixture(lifecycle=True)
        variants = [None, {}, dict(contract["observer_lifecycle"], extra=1)]
        variants += [dict(contract["observer_lifecycle"], cleanup_timeout_seconds=x) for x in (True, 0, 6, 1.0, "1")]
        variants += [dict(contract["observer_lifecycle"], bootstrap={"path": "bootstrap.py"}),
                     dict(contract["observer_lifecycle"], cleanup=dict(path="cleanup.py", sha256="0" * 64))]
        # An absent lifecycle is valid; an explicit null also means no hooks.
        for value in variants[1:]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                execution._observer_sources(dict(contract, observer_lifecycle=value), cells)
        with self.assertRaises(ValueError):
            execution._observer_sources(dict(contract, post_cell_observers=[]), cells)

    def test_mutated_observer_rejected_before_kernel_construction(self):
        import asyncio
        import nbformat
        cells, contract = self.fixture()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "source-original.ipynb").write_text(nbformat.writes(nbformat.v4.new_notebook(cells=cells)))
            (self.root / "observe.py").write_text("changed")
            with patch("jupyter_client.AsyncKernelManager") as manager:
                with self.assertRaisesRegex(ValueError, "OBSERVER_HASH_MISMATCH"):
                    asyncio.run(execution._run_notebook(output, dict(contract=contract)))
                manager.assert_not_called()

    def test_public_observer_validation_precedes_environment_inspection(self):
        import nbformat
        cells, contract = self.fixture()
        raw = nbformat.writes(nbformat.v4.new_notebook(cells=cells)).encode()
        contract["source"] = dict(sha256=execution.digest(raw), cells=[
            dict(index=i, type=c.cell_type, sha256=execution.digest(c.source.encode())) for i, c in enumerate(cells)])
        (self.root / "contracts").mkdir()
        (self.root / "contracts/qb007.json").write_text(json.dumps(contract))
        (self.root / "original.ipynb").write_bytes(raw)
        (self.root / "observe.py").write_text("changed")
        with patch.object(execution, "contract_profile", return_value={"platform": "win32"}), patch.object(execution, "inspect_environment") as inspect:
            with self.assertRaisesRegex(ValueError, "OBSERVER_HASH_MISMATCH"):
                execution.validate_request(dict(contract="qb007", source=self.root / "original.ipynb", environment=self.root))
            inspect.assert_not_called()


class ProfileInventoryTests(unittest.TestCase):
    """Mock inventory/pip; never inspect an environment or import an SDK."""

    def line(self, requirement):
        return requirement + " --hash=sha256:" + "0" * 64

    def inspect(self, requirement, packages, exact=True):
        from types import SimpleNamespace
        identity = dict(python="3.12.10", platform="win32", architecture="64bit", packages=packages)
        profile = dict(python="3.12.10", platform="win32", architecture="64bit", lock="test.lock", exact_packages=exact)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "test.lock").write_text(self.line(requirement), encoding="utf-8")
            with patch.object(execution, "ROOT", root), patch.object(execution.subprocess, "run",
                    return_value=SimpleNamespace(stdout=json.dumps(identity))) as run:
                result = execution.inspect_environment(Path("synthetic-python"), profile)
                self.assertEqual(run.call_count, 2)
                compile(run.call_args_list[0].args[0][-1], "inventory-probe-not-executed", "exec")
                self.assertEqual(run.call_args_list[-1].args[0][-3:], ["-m", "pip", "check"])
                return result

    def test_qiskit_all_inventory_uses_distribution_name(self):
        result = self.inspect("qiskit[all]==2.6.1", [["qiskit", "2.6.1"]])
        self.assertEqual(result["packages"], {"qiskit": "2.6.1"})

    def test_normal_and_multiple_extras_and_name_canonicalization(self):
        for requirement in ("Some.Pkg==1.2.3", "Some_Pkg[one]==1.2.3", "Some-Pkg[one,two.extra]==1.2.3"):
            with self.subTest(requirement=requirement):
                self.assertEqual(self.inspect(requirement, [["SOME__pkg", "1.2.3"]])["packages"], {"some-pkg": "1.2.3"})

    def test_exact_inventory_missing_version_and_unexpected(self):
        for packages in ([], [["qiskit", "2.6.0"]], [["qiskit", "2.6.1"], ["unexpected", "1.0"]]):
            with self.subTest(packages=packages), self.assertRaises(ValueError):
                self.inspect("qiskit[all]==2.6.1", packages)
        self.assertEqual(len(self.inspect("qiskit==2.6.1", [["qiskit", "2.6.1"], ["extra", "1.0"]], exact=False)["packages"]), 2)

    def test_duplicate_expected_names_and_extra_collisions_rejected(self):
        for names in [("qiskit", "qiskit[all]"), ("some-pkg", "Some__Pkg"), ("some.pkg", "some_pkg")]:
            text = "\n".join(self.line(n+"==1.0") for n in names)
            with self.subTest(names=names), self.assertRaisesRegex(ValueError, "DUPLICATE_LOCK_DISTRIBUTION"):
                execution._locked_distribution_versions(text)
        for extras in ("one,one", "one-extra,One_Extra"):
            with self.subTest(extras=extras), self.assertRaisesRegex(ValueError, "DUPLICATE_LOCK_EXTRA"):
                execution._locked_distribution_versions(self.line("pkg["+extras+"]==1.0"))

    def test_observed_collisions_are_not_lost_in_dictionary_conversion(self):
        for rows in ([["pkg", "1"], ["pkg", "1"]], [["Some.Pkg", "1"], ["some_pkg", "2"]]):
            with self.subTest(rows=rows), self.assertRaisesRegex(ValueError, "DUPLICATE_INSTALLED_DISTRIBUTION"):
                self.inspect("pkg==1", rows)

    def test_malformed_and_unsupported_requirements_rejected(self):
        requirements = ["pkg>=1", "pkg~=1.0", "pkg===1", "pkg==1.*", "pkg==1,!=1.2",
                        "pkg[bad extra]==1", "pkg[]==1", "pkg[one,]==1", "pkg[,one]==1",
                        "pkg[one][two]==1", "-pkg==1", "pkg-==1", "pkg==banana",
                        "pkg @ https://example.invalid/file.whl", "pkg==1; python_version>'3'",
                        "--index-url=https://example.invalid", "pkg==1 # ignored?", "pkg==1 --no-deps"]
        for requirement in requirements:
            with self.subTest(requirement=requirement), self.assertRaisesRegex(ValueError, "UNSUPPORTED_LOCK_REQUIREMENT"):
                execution._locked_distribution_versions(self.line(requirement))
        for text in ("pkg==1", "pkg==1 --hash=sha256:bad", "pkg==1 --hash=md5:"+"0"*32):
            with self.subTest(text=text), self.assertRaises(ValueError):
                execution._locked_distribution_versions(text)
        with self.assertRaisesRegex(ValueError, "EMPTY_DEPENDENCY_LOCK"):
            execution._locked_distribution_versions("\n")

    def test_invalid_installed_rows_rejected(self):
        for rows in ({"pkg": "1"}, [None], [["pkg"]], [[None, "1"]], [["pkg", None]],
                     [["pkg[all]", "1"]], [["pkg", ""]], [["pkg", "1", "extra"]]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                execution._installed_distribution_versions(rows)

    def test_every_existing_lock_compatible_and_bytes_unchanged(self):
        paths = sorted(execution.ROOT.glob("*.lock"))
        self.assertGreaterEqual(len(paths), 5)
        for path in paths:
            with self.subTest(path=path.name):
                before = path.read_bytes()
                parsed = execution._locked_distribution_versions(execution.canonical(path).decode())
                self.assertEqual(len(parsed), len([line for line in before.decode().splitlines() if line.strip()]))
                self.assertEqual(path.read_bytes(), before)

    def test_finite_prerelease_local_versions_and_multiple_hashes(self):
        for version in ("1.0rc1", "1.0.post2", "1.0.dev3", "1!2.0", "2.0+local.1"):
            with self.subTest(version=version):
                text = self.line("pkg[one,two]=="+version) + " --hash=sha256:" + "1"*64
                self.assertEqual(execution._locked_distribution_versions(text), {"pkg": version})


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
        with patch.object(execution, "_launch_engine", side_effect=OSError("assignment test")):
            with self.assertRaisesRegex(OSError, "assignment test"):
                execution._supervise(self.output, config)
        self.assertFalse((self.output / "kernel.json").exists())
        self.assertEqual(json.loads((self.output / "status.json").read_bytes())["state"], "failed")

    def cleanup_failure(self, error):
        config = self.fixture(['42'])
        with patch.object(execution, '_launch_engine', side_effect=OSError('assignment test')), \
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
                process = execution._launch_engine(job, [sys.executable, '-I',
                    str(Path(execution.__file__).resolve()), '--engine', str(self.output)], stdout, stderr)
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
            try:
                if process is not None:
                    process.close()
            finally:
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


class WindowsLaunchTests(unittest.TestCase):
    """Injected caller checks only; no interpreter, SDK or Win32 call runs."""
    def fixture(self):
        import io
        from unittest.mock import Mock
        temporary = tempfile.TemporaryDirectory(prefix='owned-launch-unit-')
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        (output / 'source-original.ipynb').write_text('{"cells": []}', encoding='utf-8')
        (output / 'engine-result.json').write_text('{"state":"succeeded"}', encoding='utf-8')
        (output / 'kernel.json').write_text('{"pid": 123}', encoding='utf-8')
        process = Mock(pid=42, returncode=0, stdin=io.StringIO(),
                       identity={'launcher_pid': 42, 'specific_job_member': True})
        process.poll.side_effect = [None, 0]
        process.wait.return_value = 0
        job = Mock(handle=99)
        job.command.side_effect = lambda command: command
        job.active.return_value = 0
        job.contains.return_value = True
        config = dict(python='C:/Profile Ω/python.exe', identity={}, contract_sha256='fixture',
                      profile={'cancel_grace_seconds': 1},
                      contract={'id': 'fixture', 'source': {'sha256': 'fixture'}})
        return output, config, process, job

    def test_windows_dispatch_uses_owned_launch_and_never_assigns(self):
        import windows_lifecycle
        output, config, process, job = self.fixture()
        with patch.object(execution.sys, 'platform', 'win32'), \
                patch.object(execution, '_WindowsJob', return_value=job), \
                patch.object(windows_lifecycle, 'launch_owned', return_value=process) as launch, \
                patch.object(execution.subprocess, 'Popen', side_effect=AssertionError('NO_POPEN')), \
                patch.object(execution.time, 'sleep'):
            result = execution._supervise(output, config)
        self.assertEqual(result['state'], 'succeeded')
        self.assertIsNone(result['engine_pid'])
        self.assertEqual(result['launcher_pid'], 42)
        self.assertEqual(result['cleanup']['launcher_exit'], 0)
        self.assertIsNone(result['cleanup']['engine_exit'])
        self.assertEqual(launch.call_args.args[0][0], config['python'])
        self.assertEqual(launch.call_args.kwargs['job_handle'], 99)
        job.assign.assert_not_called()
        process.close.assert_called_once()
        job.close.assert_called_once()

    def test_constructor_failure_still_terminates_observes_and_closes_job(self):
        output, config, process, job = self.fixture()
        with patch.object(execution.sys, 'platform', 'win32'), \
                patch.object(execution, '_WindowsJob', return_value=job), \
                patch.object(execution, '_launch_engine', side_effect=OSError('constructor primary')):
            with self.assertRaisesRegex(OSError, 'constructor primary'):
                execution._supervise(output, config)
        job.terminate.assert_called_once()
        job.active.assert_called()
        job.close.assert_called_once()
        process.close.assert_not_called()

    def test_broken_start_pipe_preserves_primary_and_closes_both_owners(self):
        from unittest.mock import Mock
        output, config, process, job = self.fixture()
        process.stdin = Mock(closed=False)
        process.stdin.write.side_effect = BrokenPipeError('gate primary')
        process.close.side_effect = OSError('close secondary')
        job.terminate.side_effect = OSError('terminate secondary')
        with patch.object(execution.sys, 'platform', 'win32'), \
                patch.object(execution, '_WindowsJob', return_value=job), \
                patch.object(execution, '_launch_engine', return_value=process):
            with self.assertRaisesRegex(BrokenPipeError, 'gate primary'):
                execution._supervise(output, config)
        job.close.assert_called_once()
        process.close.assert_called_once()
        result = json.loads((output / 'status.json').read_bytes())
        self.assertTrue(result['cleanup']['unconfirmed'])
        self.assertIn('close_owned_process', [e['step'] for e in result['cleanup']['errors']])

    def test_publication_failure_cannot_skip_owned_handle_cleanup(self):
        output, config, process, job = self.fixture()
        def events(status):
            if status['state'] != 'starting':
                raise OSError('publication primary')
        with patch.object(execution.sys, 'platform', 'win32'), \
                patch.object(execution, '_WindowsJob', return_value=job), \
                patch.object(execution, '_launch_engine', return_value=process):
            with self.assertRaisesRegex(OSError, 'publication primary'):
                execution._supervise(output, config, events)
        process.close.assert_called_once()
        job.close.assert_called_once()

    def test_cleanup_baseexceptions_never_replace_original_failure(self):
        from unittest.mock import Mock
        for step in ('terminate', 'poll', 'wait', 'population'):
            with self.subTest(step=step):
                output, config, process, job = self.fixture()
                primary = OSError('original gate failure')
                process.stdin = Mock(closed=False)
                process.stdin.write.side_effect = primary
                target = {'terminate': job.terminate, 'poll': process.poll,
                          'wait': process.wait, 'population': job.active}[step]
                target.side_effect = KeyboardInterrupt('cleanup interruption')
                with patch.object(execution.sys, 'platform', 'win32'), \
                        patch.object(execution, '_WindowsJob', return_value=job), \
                        patch.object(execution, '_launch_engine', return_value=process):
                    with self.assertRaises(OSError) as caught:
                        execution._supervise(output, config)
                self.assertIs(caught.exception, primary)
                process.wait.assert_called_once()
                job.active.assert_called()
                process.close.assert_called_once()
                job.close.assert_called_once()
                status = json.loads((output / 'status.json').read_bytes())
                self.assertTrue(status['cleanup']['unconfirmed'])

    def test_constructor_primary_survives_cleanup_and_publication_baseexceptions(self):
        output, config, process, job = self.fixture()
        primary = OSError('original constructor failure')
        job.terminate.side_effect = KeyboardInterrupt('secondary terminate')
        def events(status):
            if status['state'] == 'failed':
                raise SystemExit('secondary publication')
        with patch.object(execution.sys, 'platform', 'win32'), \
                patch.object(execution, '_WindowsJob', return_value=job), \
                patch.object(execution, '_launch_engine', side_effect=primary):
            with self.assertRaises(OSError) as caught:
                execution._supervise(output, config, events)
        self.assertIs(caught.exception, primary)
        job.active.assert_called_once()
        job.close.assert_called_once()

    def test_close_failure_revokes_success_after_independent_job_close(self):
        output, config, process, job = self.fixture()
        process.close.side_effect = OSError('close failed')
        with patch.object(execution.sys, 'platform', 'win32'), \
                patch.object(execution, '_WindowsJob', return_value=job), \
                patch.object(execution, '_launch_engine', return_value=process), \
                patch.object(execution.time, 'sleep'):
            result = execution._supervise(output, config)
        self.assertEqual(result['state'], 'failed')
        self.assertTrue(result['cleanup']['unconfirmed'])
        job.close.assert_called_once()

    def test_linux_launch_retains_existing_popen_arguments(self):
        from unittest.mock import Mock
        job, stdout, stderr = Mock(), Mock(), Mock()
        with patch.object(execution.sys, 'platform', 'linux'), \
                patch.object(execution.subprocess, 'Popen') as popen:
            process = execution._launch_engine(job, ['systemd-run', 'command'], stdout, stderr)
        self.assertIs(process, popen.return_value)
        popen.assert_called_once_with(['systemd-run', 'command'], stdin=subprocess.PIPE,
                stdout=stdout, stderr=stderr, text=True, close_fds=True, creationflags=0)
        job.assign.assert_not_called()  # Supervisor still owns the assign/cleanup order.

    def test_linux_supervisor_still_assigns_before_gate_and_never_closes_owned_adapter(self):
        from unittest.mock import Mock
        import types
        output, config, process, job = self.fixture()
        config['profile']['service_runtime_seconds'] = 100
        job.engine_pid, job.client_pid = 123, 456
        job.client_exited.return_value = False
        job.observe.return_value = {'LoadState': 'loaded', 'Result': 'success'}
        order = []
        job.assign.side_effect = lambda p: order.append('assign')
        process.stdin = Mock(closed=False)
        process.stdin.write.side_effect = lambda text: order.append(text)
        module = types.SimpleNamespace(LinuxService=Mock(return_value=job))
        with patch.dict(sys.modules, {'linux_lifecycle': module}), \
                patch.object(execution.sys, 'platform', 'linux'), \
                patch.object(execution, '_launch_engine', return_value=process), \
                patch.object(execution.time, 'sleep'):
            result = execution._supervise(output, config)
        self.assertEqual(order[:2], ['assign', 'start\n'])
        self.assertEqual(result['engine_pid'], 123)
        self.assertEqual(result['client_pid'], 456)
        self.assertEqual(result['cleanup']['containment'], 'systemd_service')
        process.close.assert_not_called()

    def test_metadata_launches_share_canonical_lock_and_linux_does_not(self):
        import windows_lifecycle
        from contextlib import contextmanager
        entered = []
        @contextmanager
        def lock():
            entered.append('locked')
            yield
            entered.append('released')
        def run(*args, **kwargs):
            entered.append('run')
            return 'result'
        with patch.object(windows_lifecycle, 'launch_lock', lock), \
                patch.object(execution.subprocess, 'run', side_effect=run), \
                patch.object(execution.sys, 'platform', 'win32'):
            self.assertEqual(execution._supervisor_run(['p'], timeout=1), 'result')
        self.assertEqual(entered, ['locked', 'run', 'released'])
        entered.clear()
        with patch.object(windows_lifecycle, 'launch_lock', side_effect=AssertionError('LINUX_LOCK')), \
                patch.object(execution.subprocess, 'run', side_effect=run), \
                patch.object(execution.sys, 'platform', 'linux'):
            execution._supervisor_run(['p'], timeout=1)
        self.assertEqual(entered, ['run'])


class WindowsTerminationRaceTests(unittest.TestCase):
    """Full supervisor and real held-process methods against fake native calls."""
    def exercise(self, mode='terminal', code=1):
        import io
        import windows_lifecycle
        from test_windows_lifecycle import FakeAPI
        output, config, _, job = WindowsLaunchTests.fixture(self)
        api = FakeAPI()
        api.open.add(10)
        process = windows_lifecycle.OwnedProcess(api, ['fake'], 10, 42, io.StringIO(),
                                                 dict(launcher_pid=42, held_handle=True, specific_job_member=True))
        primary = ValueError('READY_PARENT_TYPE')
        native_error = OSError('access denied')
        native_error.winerror = 6 if mode == 'other_error' else 5
        original_poll = process.poll
        delivered = False
        def poll():
            nonlocal delivered
            if not delivered:
                delivered = True
                raise primary
            return original_poll()
        process.poll = poll
        def terminate(handle):
            api.event('terminate_process', handle)
            api.terminal, api.code = mode != 'alive', code
            if mode == 'query_error': api.fail = 'exit_code'
            raise native_error
        api.terminate_process = terminate
        if mode == 'close_error': api.fail = ('close', 10)
        if mode == 'alive': job.active.return_value = 1
        original_write = execution.atomic_json
        publications = []
        def publish(path, value):
            if path.name == 'status.json' and value['state'] == 'failed':
                publications.append(json.loads(json.dumps(value)))
                if mode == 'publication_error': raise OSError('failure publication')
            return original_write(path, value)
        with patch.object(execution.sys, 'platform', 'win32'), \
                patch.object(execution, '_WindowsJob', return_value=job), \
                patch.object(execution, '_launch_engine', return_value=process), \
                patch.object(execution, 'atomic_json', side_effect=publish), \
                patch.object(windows_lifecycle, '_NativeAPI', side_effect=AssertionError('NO_NATIVE')):
            with self.assertRaises(ValueError) as caught:
                execution._supervise(output, config)
        self.assertIs(caught.exception, primary)
        self.assertFalse((output/'cancel.request').exists())
        self.assertEqual(api.events.count(('terminate_process', 10)), 1)
        self.assertIn(('close', 10), api.events)
        job.terminate.assert_called_once(); job.close.assert_called_once()
        status = json.loads((output/'status.json').read_bytes())
        if mode == 'publication_error':
            self.assertNotEqual(status['state'], 'succeeded')
            self.assertTrue(publications[0]['cleanup']['launcher_termination']['terminal_confirmed'])
            return
        self.assertEqual(status['state'], 'failed')
        self.assertEqual(status['error'], 'READY_PARENT_TYPE')
        observation = status['cleanup']['launcher_termination']
        self.assertEqual(observation['error']['message'], str(native_error))
        self.assertEqual(observation['same_continuously_held_handle'], mode != 'other_error')
        if mode in ('terminal', 'close_error'):
            self.assertTrue(observation['terminal_confirmed'])
            self.assertEqual(observation['exit_code'], code)
            self.assertEqual(status['cleanup']['launcher_exit'], code)
            self.assertIsNone(status['cleanup']['engine_exit'])
            self.assertEqual(status['cleanup']['unconfirmed'], mode == 'close_error')
            if mode == 'terminal': self.assertEqual(status['cleanup']['errors'], [])
        else:
            self.assertFalse(observation['terminal_confirmed'])
            self.assertTrue(status['cleanup']['unconfirmed'])
            self.assertIn('terminate_owned_launcher', [e['step'] for e in status['cleanup']['errors']])

    def test_race_confirmation_published_before_close(self): self.exercise()
    def test_terminal259_confirmation(self): self.exercise(code=259)
    def test_alive_error_not_erased(self): self.exercise('alive')
    def test_query_failure_not_erased(self): self.exercise('query_error')
    def test_other_error_not_erased(self): self.exercise('other_error')
    def test_close_failure_remains_unconfirmed(self): self.exercise('close_error')
    def test_publication_failure_preserves_requester_and_closes(self): self.exercise('publication_error')


if __name__ == "__main__":
    unittest.main(verbosity=2)
