"""Finite, reviewed notebook contracts and an owned Windows kernel lifecycle.

This is local execution, not a security sandbox. Only execute() is the public
run seam; the engine protocol is private and starts behind a process-job gate.
"""
import argparse
import asyncio
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import traceback

ROOT = Path(__file__).resolve().parent
TERMINAL = {"succeeded", "failed", "cancelled"}
CONTRACTS = {"ibm019", "ibm020", "qb017"}
PROFILES = {"qiskit-aer-win-py312", "qir-win-py312"}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(path):
    return path.read_text(encoding="utf-8").encode("utf-8")


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    # A Windows reader may briefly hold the target without FILE_SHARE_DELETE.
    # Keep the previous complete checkpoint and bound retries; never truncate it.
    deadline = time.monotonic() + 2
    while True:
        try:
            os.replace(temporary, path)
            break
        except PermissionError:
            if sys.platform != "win32" or time.monotonic() >= deadline:
                raise
            time.sleep(0.02)


def cell_text(cell):
    return "".join(cell["source"])


def profile_for(name):
    if name not in PROFILES:
        raise ValueError("UNKNOWN_PROFILE")
    profile = json.loads((ROOT / "profiles" / (name + ".json")).read_bytes())
    if digest(canonical(ROOT / profile["lock"])) != profile["lock_sha256"]:
        raise ValueError("LOCK_HASH_MISMATCH")
    return profile


def inspect_environment(python, profile, dependencies=True):
    code = ("import json,sys,platform,importlib.metadata as m; "
            "print(json.dumps(dict(python=platform.python_version(),platform=sys.platform,"
            "architecture=platform.architecture()[0],executable=sys.executable,"
            "packages={d.metadata['Name'].lower().replace('_','-'):d.version for d in m.distributions()})))")
    result = subprocess.run([str(python), "-I", "-c", code], capture_output=True, text=True, timeout=30, check=True)
    identity = json.loads(result.stdout)
    for key in ("python", "platform", "architecture"):
        if identity[key] != profile[key]:
            raise ValueError("ENVIRONMENT_MISMATCH: " + key)
    if dependencies:
        expected = {}
        for line in canonical(ROOT / profile["lock"]).decode().splitlines():
            name, version = line.split()[0].split("==")
            expected[name.lower().replace("_", "-")] = version
            if identity["packages"].get(name.lower().replace("_", "-")) != version:
                raise ValueError("DEPENDENCY_MISMATCH: " + name)
        if profile.get("exact_packages") and identity["packages"] != expected:
            raise ValueError("DEPENDENCY_INVENTORY_MISMATCH")
        subprocess.run([str(python), "-I", "-m", "pip", "check"], capture_output=True, text=True, timeout=30, check=True)
    return identity


def create_environment(profile_name, python, wheelhouse, destination):
    profile = profile_for(profile_name)
    inspect_environment(python, profile, dependencies=False)
    destination = Path(destination).resolve()
    wheelhouse = Path(wheelhouse).resolve(strict=True)
    destination.mkdir(parents=True, exist_ok=False)
    report = {"state": "starting", "profile": profile, "offline_only": True,
              "wheels": {p.name: digest(p.read_bytes()) for p in sorted(wheelhouse.glob("*.whl"))}}
    try:
        with (destination / "install.log").open("w", encoding="utf-8") as log:
            subprocess.run([str(python), "-I", "-m", "venv", str(destination)], stdout=log, stderr=log, check=True, timeout=120)
            target = destination / "Scripts" / "python.exe"
            subprocess.run([str(target), "-I", "-m", "pip", "--isolated", "install", "--no-index", "--no-cache-dir",
                            "--find-links", str(wheelhouse), "--require-hashes", "-r", str(ROOT / profile["lock"])],
                           stdout=log, stderr=log, check=True, timeout=300)
        report["identity"] = inspect_environment(target, profile)
        report["state"] = "succeeded"
    except Exception as error:
        report.update(state="failed", error=str(error))
        raise
    finally:
        atomic_json(destination / "environment.json", report)
    return report


def validate_request(request):
    name = request["contract"]
    if name not in CONTRACTS:
        raise ValueError("UNKNOWN_CONTRACT")
    contract_bytes = (ROOT / "contracts" / (name + ".json")).read_bytes()
    contract = json.loads(contract_bytes)
    profile = profile_for(contract["profile"])
    raw = Path(request["source"]).read_bytes()
    if digest(raw) != contract["source"]["sha256"]:
        raise ValueError("SOURCE_HASH_MISMATCH")
    original = json.loads(raw)
    cells = [{"index": i, "type": c["cell_type"], "sha256": digest(cell_text(c).encode("utf-8"))}
             for i, c in enumerate(original["cells"])]
    if cells != contract["source"]["cells"]:
        raise ValueError("SOURCE_CELL_MISMATCH")
    witness = canonical(ROOT / contract["witness"]["path"])
    if digest(witness) != contract["witness"]["sha256"]:
        raise ValueError("WITNESS_HASH_MISMATCH")
    setup = contract.get("setup")
    if setup:
        if digest(_setup_observer(setup["commands"]).encode("utf-8")) != setup["observer_sha256"]:
            raise ValueError("SETUP_OBSERVER_HASH_MISMATCH")
        if digest(SETUP_CHECK.encode("utf-8")) != setup["check_sha256"]:
            raise ValueError("SETUP_CHECK_HASH_MISMATCH")
    python = Path(request["environment"]).resolve() / "Scripts" / "python.exe"
    identity = inspect_environment(python, profile)
    return raw, dict(contract=contract, contract_sha256=digest(contract_bytes), profile=profile,
                     witness=witness.decode(), identity=identity, python=str(python))


def _setup_observer(commands):
    """Disclosed authored observation: execute the original IPython commands."""
    return '''import hashlib as _dev13_hashlib, importlib.metadata as _dev13_metadata
import json as _dev13_json, pathlib as _dev13_pathlib, sys as _dev13_sys
import os as _dev13_os, time as _dev13_time
def _dev13_inventory():
    return {d.metadata['Name'].lower().replace('_', '-'): {
        'version': d.version,
        'metadata_sha256': _dev13_hashlib.sha256((d.read_text('METADATA') or '').encode()).hexdigest(),
        'record_sha256': _dev13_hashlib.sha256((d.read_text('RECORD') or '').encode()).hexdigest()
    } for d in _dev13_metadata.distributions()}
_dev13_setup = {'commands': [], 'before': _dev13_inventory(), 'accepted': False}
def _dev13_save_setup():
    temporary = _dev13_pathlib.Path('setup-evidence.json.tmp')
    temporary.write_text(_dev13_json.dumps(_dev13_setup, indent=2), encoding='utf-8')
    deadline = _dev13_time.monotonic() + 2
    while True:
        try:
            _dev13_os.replace(temporary, 'setup-evidence.json')
            break
        except PermissionError:
            if _dev13_time.monotonic() >= deadline:
                raise
            _dev13_time.sleep(0.02)
_dev13_shell = get_ipython()
_dev13_real_system = _dev13_shell.system
_dev13_commands = ''' + repr(commands) + '''
def _dev13_observed_system(command):
    index = len(_dev13_setup['commands'])
    expected = ('"' + _dev13_sys.executable + '" -m pip ' + _dev13_commands[index]) if index < len(_dev13_commands) else None
    if command != expected:
        raise RuntimeError('UNREVIEWED_SETUP_COMMAND: ' + command)
    _dev13_shell.user_ns['_exit_code'] = None
    try:
        _dev13_real_system(command)
    finally:
        code = _dev13_shell.user_ns.get('_exit_code')
        _dev13_setup['commands'].append({'command': command, 'exit_code': code})
        _dev13_save_setup()
    if code != 0:
        raise RuntimeError('SETUP_COMMAND_FAILED: ' + str(code))
_dev13_shell.system = _dev13_observed_system
_dev13_save_setup()
'''


SETUP_CHECK = '''_dev13_shell.system = _dev13_real_system
_dev13_setup['after'] = _dev13_inventory()
_dev13_setup['accepted'] = (_dev13_setup['before'] == _dev13_setup['after'] and
    len(_dev13_setup['commands']) == len(_dev13_commands) and
    all(c['exit_code'] == 0 for c in _dev13_setup['commands']))
_dev13_save_setup()
if not _dev13_setup['accepted']:
    raise RuntimeError('SETUP_INVENTORY_DRIFT_OR_INCOMPLETE')
'''


def _kernel_environment(setup):
    environment = dict(os.environ)
    if setup:
        # IPython's original %pip launches a child without -I. Scrub its import
        # and pip settings too; this is offline pip policy, not network isolation.
        for key in list(environment):
            if key.upper().startswith(('PIP_', 'PYTHON')):
                del environment[key]
        environment.update(PIP_CONFIG_FILE=os.devnull, PIP_NO_INDEX="1", PIP_NO_CACHE_DIR="1",
                           PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_REQUIRE_VIRTUALENV="1",
                           PYTHONNOUSERSITE="1")
    environment["MPLBACKEND"] = "module://matplotlib_inline.backend_inline"
    return environment


class _WindowsJob:
    """Own only this run's descendants; no process-name or PID-tree killing."""

    def __init__(self):
        if sys.platform != "win32":
            raise RuntimeError("WINDOWS_PROFILE_REQUIRED")
        class Basic(ctypes.Structure):
            _fields_ = [("ProcessTime", ctypes.c_int64), ("JobTime", ctypes.c_int64),
                        ("Flags", wintypes.DWORD), ("MinWS", ctypes.c_size_t), ("MaxWS", ctypes.c_size_t),
                        ("ActiveLimit", wintypes.DWORD), ("Affinity", ctypes.c_size_t),
                        ("Priority", wintypes.DWORD), ("Scheduling", wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [("c" + str(i), ctypes.c_uint64) for i in range(6)]
        class Extended(ctypes.Structure):
            _fields_ = [("Basic", Basic), ("IO", IO)] + [("m" + str(i), ctypes.c_size_t) for i in range(4)]
        class Accounting(ctypes.Structure):
            _fields_ = [("t" + str(i), ctypes.c_int64) for i in range(4)] + [
                ("Faults", wintypes.DWORD), ("Total", wintypes.DWORD),
                ("Active", wintypes.DWORD), ("Terminated", wintypes.DWORD)]
        if (ctypes.sizeof(Basic), ctypes.sizeof(IO), ctypes.sizeof(Extended)) != (64, 48, 144):
            raise RuntimeError("UNSUPPORTED_JOB_ABI")
        self.accounting = Accounting
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "CreateJobObjectW": ([ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
            "SetInformationJobObject": ([wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
            "AssignProcessToJobObject": ([wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
            "QueryInformationJobObject": ([wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p], wintypes.BOOL),
            "TerminateJobObject": ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
            "OpenProcess": ([wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
            "IsProcessInJob": ([wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)], wintypes.BOOL),
            "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.api, name)
            function.argtypes, function.restype = args, result
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = Extended()
        limits.Basic.Flags = 0x2000  # KILL_ON_JOB_CLOSE; never allow breakaway.
        try:
            self.check(self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)))
        except BaseException:
            self.close()
            raise

    @staticmethod
    def check(ok):
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())

    def assign(self, process):
        # Borrowed CPython Windows Popen handle; never close it here.
        self.check(self.api.AssignProcessToJobObject(self.handle, int(process._handle)))

    def contains(self, pid):
        process = self.api.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not process:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            member = wintypes.BOOL()
            self.check(self.api.IsProcessInJob(process, self.handle, ctypes.byref(member)))
            return bool(member.value)
        finally:
            self.api.CloseHandle(process)

    def active(self):
        info = self.accounting()
        self.check(self.api.QueryInformationJobObject(self.handle, 1, ctypes.byref(info), ctypes.sizeof(info), None))
        return info.Active

    def terminate(self):
        self.check(self.api.TerminateJobObject(self.handle, 1))

    def close(self):
        if self.handle:
            self.check(self.api.CloseHandle(self.handle))
            self.handle = None


def cancel(directory):
    directory = Path(directory).resolve(strict=True)
    status = json.loads((directory / "status.json").read_bytes())
    if status["state"] not in TERMINAL:
        (directory / "cancel.request").touch(exist_ok=True)
    return status


def execute(request, events=None):
    """Validate a reviewed source, then return terminal evidence after cleanup.

    request: contract, source, environment, output. events receives supervisor
    state dictionaries; durable events.jsonl remains authoritative.
    """
    output = Path(request["output"]).resolve()
    if output.exists():
        raise FileExistsError(output)
    raw, config = validate_request(request)
    output.mkdir(parents=True, exist_ok=False)
    (output / "source-original.ipynb").write_bytes(raw)
    return _supervise(output, config, events)


def _supervise(output, config, events=None):
    atomic_json(output / "engine-request.json", config)
    status = dict(version=1, state="starting", contract=config["contract"]["id"], route="notebook",
                  source_sha256=config["contract"]["source"]["sha256"], contract_sha256=config["contract_sha256"],
                  identity=config["identity"], profile=config["profile"], original_execution="not_run",
                  authored_verification="not_run", external_resources="outstanding", interpretation="outstanding")

    def publish():
        atomic_json(output / "status.json", status)
        with (output / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(dict(time=time.time(), **status)) + "\n")
        if events is not None:
            events(dict(status))

    publish()
    try:
        job = _WindowsJob()
    except Exception as error:
        status.update(state="failed", error=str(error), cleanup={"method": "not_started"})
        publish()
        raise
    process = None
    requested = False
    forced = False
    membership = None
    try:
        with (output / "engine.stdout").open("w", encoding="utf-8") as stdout, (output / "engine.stderr").open("w", encoding="utf-8") as stderr:
            process = subprocess.Popen([config["python"], "-I", str(Path(__file__).resolve()), "--engine", str(output)],
                                       stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, text=True,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            job.assign(process)
            status["engine_pid"] = process.pid
            process.stdin.write("start\n")
            process.stdin.flush()
            status["state"] = "running"
            publish()
            deadline = None
            while process.poll() is None:
                if membership is None and (output / "kernel.json").exists():
                    kernel = json.loads((output / "kernel.json").read_bytes())
                    membership = job.contains(kernel["pid"])
                    if not membership:
                        raise RuntimeError("KERNEL_OUTSIDE_OWNED_JOB")
                if (output / "cancel.request").exists() and not requested:
                    requested = True
                    status["cancellation_requested"] = True
                    publish()
                    deadline = time.monotonic() + config["profile"]["cancel_grace_seconds"]
                    try:
                        process.stdin.write("cancel\n")
                        process.stdin.flush()
                    except (BrokenPipeError, OSError):
                        pass
                if deadline is not None and time.monotonic() >= deadline:
                    forced = True
                    job.terminate()
                    break
                time.sleep(0.05)
            process.wait(timeout=10)
        if job.active():
            forced = True
            job.terminate()
        deadline = time.monotonic() + 10
        while job.active() and time.monotonic() < deadline:
            time.sleep(0.05)
        remaining = job.active()
        result_path = output / "engine-result.json"
        if result_path.exists():
            status.update(json.loads(result_path.read_bytes()))
        status["cleanup"] = dict(active_processes=remaining, kernel_job_membership=membership,
                                 method="forced" if forced else "graceful", engine_exit=process.returncode)
        if requested:
            status["state"] = "cancelled"
            cells_path = output / "cells.json"
            if cells_path.exists():
                cells = json.loads(cells_path.read_bytes())
                for cell in cells:
                    if cell["state"] in {"running", "failed"}:
                        cell.update(state="interrupted", cancellation_requested=True)
                        cell.setdefault("error", {"type": "SupervisorCancellation",
                                        "message": "Run cancelled; only checkpointed outputs are available"})
                atomic_json(cells_path, cells)
                original_states = [cell["state"] for cell in cells
                                   if cell["original_index"] is not None and cell["type"] == "code"]
                status["original_execution"] = (
                    "succeeded" if original_states and all(s == "succeeded" for s in original_states)
                    else "incomplete" if any(s != "not_run" for s in original_states) else "not_run")
                if not result_path.exists():
                    status["authored_verification"] = cells[-1]["state"]
        elif process.returncode != 0 or status["state"] != "succeeded":
            status["state"] = "failed"
        if remaining or (status["state"] == "succeeded" and membership is not True):
            status.update(state="failed", error="CLEANUP_OR_MEMBERSHIP_UNCONFIRMED")
        publish()
        return status
    except BaseException as error:
        # Assignment failure leaves an engine behind its gate, with no children.
        if process is not None:
            if process.stdin:
                process.stdin.close()
            job.terminate()
            if process.poll() is None:
                process.kill()
            process.wait(timeout=10)
        status.update(state="failed", error=str(error), cleanup={"active_processes": job.active(), "method": "exception"})
        publish()
        raise
    finally:
        if process is not None and process.stdin and not process.stdin.closed:
            process.stdin.close()
        job.close()


async def _run_notebook(output, config):
    import nbformat
    from nbclient import NotebookClient
    from jupyter_client import AsyncKernelManager
    from jupyter_client.kernelspec import KernelSpecManager

    raw = (output / "source-original.ipynb").read_bytes()
    notebook = nbformat.reads(raw.decode("utf-8"), as_version=4)
    contract = config["contract"]
    original = [(c.cell_type, c.source) for c in notebook.cells]
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.outputs, cell.execution_count = [], None
            cell.metadata.pop("execution", None)
    original_cells = list(notebook.cells)
    notebook.cells = []
    records = []
    source_positions = {}

    def append(cell, original_index=None, role=None):
        index = len(notebook.cells)
        notebook.cells.append(cell)
        records.append(dict(index=index, original_index=original_index, authored_role=role,
                            type=cell.cell_type, source_sha256=digest(cell.source.encode("utf-8")),
                            state="not_run" if cell.cell_type == "code" else "not_executable"))
        if original_index is not None:
            source_positions[original_index] = index

    def authored(source, role):
        append(nbformat.v4.new_code_cell(source, metadata={"tags": ["authored-" + role]}), role=role)

    if contract["preamble"]:
        authored(contract["preamble"], "preamble")
    setup = contract.get("setup")
    for index, cell in enumerate(original_cells):
        if setup and index == setup["cell"]:
            authored(_setup_observer(setup["commands"]), "setup-observer")
        append(cell, original_index=index)
        if setup and index == setup["cell"]:
            authored(SETUP_CHECK, "setup-check")
    authored(config["witness"], "independent-witness")
    result = dict(state="failed", original_execution="not_run", authored_verification="not_run")

    def checkpoint():
        atomic_json(output / "executed.ipynb", notebook)
        atomic_json(output / "cells.json", records)

    checkpoint()
    with tempfile.TemporaryDirectory(prefix="dev13-kernel-") as temp:
        kernels = Path(temp) / "kernels"
        spec = kernels / "contract"
        spec.mkdir(parents=True)
        atomic_json(spec / "kernel.json", dict(argv=[sys.executable, "-I", "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                                               display_name="Pinned notebook contract", language="python",
                                               env={"MPLBACKEND": "module://matplotlib_inline.backend_inline"}))
        manager = AsyncKernelManager(kernel_name="contract", kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernels)]))
        client = NotebookClient(notebook, km=manager, timeout=config["profile"]["default_cell_timeout_seconds"],
                                allow_errors=False, interrupt_on_timeout=False, resources={"metadata": {"path": str(output)}})
        try:
            async with client.async_setup_kernel(cleanup_kc=True, env=_kernel_environment(setup)):
                atomic_json(output / "kernel.json", {"pid": manager.provisioner.pid, "executable": sys.executable})
                for i, cell in enumerate(notebook.cells):
                    if cell.cell_type != "code":
                        continue
                    records[i]["state"] = "running"
                    checkpoint()
                    started = time.monotonic()
                    try:
                        await client.async_execute_cell(cell, i)
                        records[i]["state"] = "succeeded"
                    except BaseException as error:
                        records[i].update(state="interrupted" if isinstance(error, asyncio.CancelledError) else "failed",
                                          error={"type": type(error).__name__, "message": str(error)})
                        raise
                    finally:
                        records[i]["elapsed_seconds"] = time.monotonic() - started
                        checkpoint()
            preserved = [(notebook.cells[source_positions[i]].cell_type, notebook.cells[source_positions[i]].source)
                         for i in range(len(original))]
            if preserved != original:
                raise AssertionError("SOURCE_CELLS_CHANGED")
            for index in contract["required_images"]:
                if not any(o.get("data", {}).get("image/png") for o in notebook.cells[source_positions[index]].outputs):
                    raise AssertionError("MISSING_DRAWING: " + str(index))
            for index, text in contract["required_text"].items():
                if not any(o.get("data", {}).get("text/plain") == text for o in notebook.cells[source_positions[int(index)]].outputs):
                    raise AssertionError("SOURCE_RESULT_MISMATCH: " + index)
            witness_text = "".join(o.get("text", "") for o in notebook.cells[-1].outputs if o.output_type == "stream")
            result.update(state="succeeded", original_execution="succeeded", authored_verification="succeeded",
                          independent_results=json.loads(witness_text), source_cells_preserved=True)
            if contract.get("acceptance_field"):
                if result["independent_results"].get(contract["acceptance_field"]) is not True:
                    raise AssertionError("SEMANTIC_ACCEPTANCE_FAILED")
        except BaseException as error:
            result["error"] = dict(type=type(error).__name__, message=str(error), traceback=traceback.format_exc())
            codes = [records[source_positions[i]]["state"] for i in contract["code_cells"]]
            result["state"] = "failed"
            result["original_execution"] = "succeeded" if all(x == "succeeded" for x in codes) else "incomplete"
            result["authored_verification"] = "failed" if records[-1]["state"] == "succeeded" else records[-1]["state"]
        finally:
            artifacts = {}
            for pattern in contract.get("output_artifacts", []):
                for path in output.glob(pattern):
                    if path.is_file() and path.resolve().parent == output.resolve():
                        artifacts[path.name] = dict(bytes=path.stat().st_size, sha256=digest(path.read_bytes()))
            result["output_artifacts"] = artifacts
            checkpoint()
            atomic_json(output / "engine-result.json", result)
    return result


def _engine(output):
    # No third-party runtime imports or child processes before ownership gate.
    if sys.stdin.readline() != "start\n":
        return 1
    config = json.loads((output / "engine-request.json").read_bytes())

    async def main():
        task = asyncio.create_task(_run_notebook(output, config))
        loop = asyncio.get_running_loop()

        def control():
            for line in sys.stdin:
                if line.strip() == "cancel":
                    try:
                        loop.call_soon_threadsafe(task.cancel)
                    except RuntimeError:
                        pass
                    return

        threading.Thread(target=control, daemon=True).start()
        return await task

    result = asyncio.run(main())
    return 0 if result["state"] == "succeeded" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", type=Path, required=True)
    sys.exit(_engine(parser.parse_args().engine))
