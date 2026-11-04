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
import re
import subprocess
import sys
import tempfile
import threading
import time
import traceback

ROOT = Path(__file__).resolve().parent
TERMINAL = {"succeeded", "failed", "cancelled"}
CONTRACTS = {"ibm019", "ibm020", "qb017", "qb007", "qb027", "qb030", "ibm-timing"}
SELECTED_ROUTE = "selected-cells/direct-native-execution"
PROFILES = {"qiskit-aer-win-py312", "qir-win-py312", "notebook-linux-py312", "qiskit-aer-linux-py312", "pulser-win-py312", "timing-win-py312"}


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


def contract_profile(contract):
    """Choose only a reviewed profile for the current host platform."""
    profiles = contract.get("profiles")
    if profiles is None:
        name = contract["profile"]
    else:
        if not isinstance(profiles, dict) or any(key not in {"win32", "linux"} for key in profiles):
            raise ValueError("INVALID_PLATFORM_PROFILES")
        if sys.platform not in profiles:
            raise ValueError("UNSUPPORTED_CONTRACT_PLATFORM")
        name = profiles[sys.platform]
        if not isinstance(name, str):
            raise ValueError("INVALID_PLATFORM_PROFILES")
    profile = profile_for(name)
    if profile["platform"] != sys.platform:
        raise ValueError("UNSUPPORTED_CONTRACT_PLATFORM")
    return profile


_DISTRIBUTION_NAME = r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"
# Deliberately finite exact-pin grammar, not a resolver or general requirement parser.
_LOCK_VERSION = (r"(?:[0-9]+!)?[0-9]+(?:\.[0-9]+)*(?:(?:a|b|rc)[0-9]+)?"
                 r"(?:\.post[0-9]+)?(?:\.dev[0-9]+)?(?:\+[a-z0-9]+(?:[._-][a-z0-9]+)*)?")
_LOCK_LINE = re.compile(
    rf"(?P<name>{_DISTRIBUTION_NAME})(?:\[(?P<extras>{_DISTRIBUTION_NAME}(?:,{_DISTRIBUTION_NAME})*)\])?"
    rf"==(?P<version>{_LOCK_VERSION})(?: --hash=sha256:[0-9a-f]{{64}})+", re.IGNORECASE)


def _distribution_name(name):
    if type(name) is not str or re.fullmatch(_DISTRIBUTION_NAME, name) is None:
        raise ValueError("INVALID_DISTRIBUTION_NAME")
    return re.sub(r"[-_.]+", "-", name).lower()


def _locked_distribution_versions(text):
    """Extras remain in the lock for pip; inventory uses canonical base names."""
    expected = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        match = _LOCK_LINE.fullmatch(line)
        if match is None:
            raise ValueError("UNSUPPORTED_LOCK_REQUIREMENT: " + line)
        name = _distribution_name(match['name'])
        extras = [_distribution_name(extra) for extra in (match['extras'] or '').split(',') if extra]
        if len(extras) != len(set(extras)):
            raise ValueError("DUPLICATE_LOCK_EXTRA: " + name)
        if name in expected:
            raise ValueError("DUPLICATE_LOCK_DISTRIBUTION: " + name)
        expected[name] = match['version']
    if not expected:
        raise ValueError("EMPTY_DEPENDENCY_LOCK")
    return expected


def _installed_distribution_versions(rows):
    if type(rows) is not list:
        raise ValueError("INVALID_INSTALLED_DISTRIBUTIONS")
    packages = {}
    for row in rows:
        if (type(row) is not list or len(row) != 2 or type(row[1]) is not str or not row[1]):
            raise ValueError("INVALID_INSTALLED_DISTRIBUTION")
        name = _distribution_name(row[0])
        if name in packages:
            raise ValueError("DUPLICATE_INSTALLED_DISTRIBUTION: " + name)
        packages[name] = row[1]
    return packages


def inspect_environment(python, profile, dependencies=True):
    code = ("import json,sys,platform,importlib.metadata as m; "
            "print(json.dumps(dict(python=platform.python_version(),platform=sys.platform,"
            "architecture=platform.architecture()[0],executable=sys.executable,"
            "packages=[[d.metadata['Name'],d.version] for d in m.distributions()])))")
    result = subprocess.run([str(python), "-I", "-c", code], capture_output=True, text=True, timeout=30, check=True)
    identity = json.loads(result.stdout)
    identity["packages"] = _installed_distribution_versions(identity["packages"])
    for key in ("python", "platform", "architecture"):
        if identity[key] != profile[key]:
            raise ValueError("ENVIRONMENT_MISMATCH: " + key)
    if dependencies:
        expected = _locked_distribution_versions(canonical(ROOT / profile["lock"]).decode())
        for name, version in expected.items():
            if identity["packages"].get(name) != version:
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
            target = environment_python(destination, profile)
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


def environment_python(destination, profile):
    if profile['platform'] == 'win32':
        return Path(destination) / 'Scripts' / 'python.exe'
    if profile['platform'] == 'linux':
        return Path(destination) / 'bin' / 'python'
    raise ValueError('UNSUPPORTED_PROFILE_PLATFORM')


def validate_request(request):
    name = request["contract"]
    if name not in CONTRACTS:
        raise ValueError("UNKNOWN_CONTRACT")
    contract_bytes = (ROOT / "contracts" / (name + ".json")).read_bytes()
    contract = json.loads(contract_bytes)
    profile = contract_profile(contract)
    raw = Path(request["source"]).read_bytes()
    if digest(raw) != contract["source"]["sha256"]:
        raise ValueError("SOURCE_HASH_MISMATCH")
    original = json.loads(raw)
    cells = [{"index": i, "type": c["cell_type"], "sha256": digest(cell_text(c).encode("utf-8"))}
             for i, c in enumerate(original["cells"])]
    if cells != contract["source"]["cells"]:
        raise ValueError("SOURCE_CELL_MISMATCH")
    _execution_indices(contract, original["cells"])
    _observer_sources(contract, original["cells"])
    witness = canonical(ROOT / contract["witness"]["path"])
    if digest(witness) != contract["witness"]["sha256"]:
        raise ValueError("WITNESS_HASH_MISMATCH")
    setup = contract.get("setup")
    if setup:
        if digest(_setup_observer(setup["commands"]).encode("utf-8")) != setup["observer_sha256"]:
            raise ValueError("SETUP_OBSERVER_HASH_MISMATCH")
        if digest(SETUP_CHECK.encode("utf-8")) != setup["check_sha256"]:
            raise ValueError("SETUP_CHECK_HASH_MISMATCH")
    python = environment_python(Path(request["environment"]).resolve(), profile)
    identity = inspect_environment(python, profile)
    return raw, dict(contract=contract, contract_sha256=digest(contract_bytes), profile=profile,
                     witness=witness.decode(), identity=identity, python=str(python))


def _execution_indices(contract, cells):
    """Validate selection before launch; whole routes still retain every cell."""
    route = contract.get("route", "notebook")
    if route == "notebook":
        if "selected_cells" in contract or "excluded_code_cells" in contract:
            raise ValueError("SELECTION_REQUIRES_SELECTED_ROUTE")
        return list(range(len(cells)))
    if route != SELECTED_ROUTE:
        raise ValueError("UNKNOWN_EXECUTION_ROUTE")
    selected = contract.get("selected_cells")
    if (type(selected) is not list or not selected
            or any(type(i) is not int or not 0 <= i < len(cells) for i in selected)
            or selected != sorted(set(selected))
            or any(cells[i]["cell_type"] != "code" for i in selected)
            or type(contract.get("code_cells")) is not list
            or any(type(i) is not int for i in contract["code_cells"])
            or contract["code_cells"] != selected or contract.get("setup")):
        raise ValueError("INVALID_CELL_SELECTION")
    omitted = {str(i) for i, c in enumerate(cells) if c["cell_type"] == "code" and i not in selected}
    reasons = contract.get("excluded_code_cells")
    if (type(reasons) is not dict or set(reasons) != omitted
            or any(type(reason) is not str or not reason.strip() for reason in reasons.values())):
        raise ValueError("INVALID_EXCLUSION_DISPOSITION")
    images, texts = contract.get("required_images", []), contract.get("required_text", {})
    if (type(images) is not list or type(texts) is not dict
            or any(type(i) is not int or i not in selected for i in images)
            or any(type(i) is not str or i not in {str(s) for s in selected} for i in texts)):
        raise ValueError("OUTPUT_REQUIREMENT_OUTSIDE_SELECTION")
    return selected[:]


def _observer_sources(contract, cells):
    """Load finite reviewed authored cells before any kernel starts.

    Hash canonical source text, as for witnesses, and resolve paths inside the
    fixed runtime root. Revalidate in the engine so post-validation edits fail.
    """
    descriptors = contract.get("post_cell_observers", [])
    if type(descriptors) is not list:
        raise ValueError("INVALID_POST_CELL_OBSERVERS")
    indices = _execution_indices(contract, cells)
    loaded, previous = {}, -1

    def source(descriptor):
        path, expected = descriptor.get("path"), descriptor.get("sha256")
        if (type(path) is not str or not path or Path(path).is_absolute()
                or Path(path).drive or ".." in Path(path).parts
                or type(expected) is not str or len(expected) != 64
                or any(c not in "0123456789abcdef" for c in expected)):
            raise ValueError("INVALID_OBSERVER_SOURCE")
        target = (ROOT / path).resolve(strict=True)
        if not target.is_relative_to(ROOT.resolve()) or not target.is_file():
            raise ValueError("OBSERVER_PATH_ESCAPE")
        raw = canonical(target)
        if digest(raw) != expected:
            raise ValueError("OBSERVER_HASH_MISMATCH")
        return raw.decode("utf-8")

    for descriptor in descriptors:
        if type(descriptor) is not dict or set(descriptor) != {"after_original_index", "path", "sha256", "role"}:
            raise ValueError("INVALID_POST_CELL_OBSERVER")
        index = descriptor["after_original_index"]
        if (type(index) is not int or index <= previous or index not in indices
                or cells[index]["cell_type"] != "code"
                or descriptor["role"] not in ("postcell-observer", "timing-postcell")):
            raise ValueError("INVALID_POST_CELL_OBSERVER")
        loaded[index] = dict(source=source(descriptor), role=descriptor["role"])
        previous = index
    lifecycle = contract.get("observer_lifecycle")
    if lifecycle is None:
        return loaded, None
    if (not loaded or type(lifecycle) is not dict
            or set(lifecycle) != {"bootstrap", "cleanup", "cleanup_timeout_seconds"}
            or type(lifecycle["cleanup_timeout_seconds"]) is not int
            or not 1 <= lifecycle["cleanup_timeout_seconds"] <= 5):
        raise ValueError("INVALID_OBSERVER_LIFECYCLE")
    for name in ("bootstrap", "cleanup"):
        if type(lifecycle[name]) is not dict or set(lifecycle[name]) != {"path", "sha256"}:
            raise ValueError("INVALID_OBSERVER_LIFECYCLE")
    return loaded, dict(bootstrap=source(lifecycle["bootstrap"]),
                        cleanup=source(lifecycle["cleanup"]),
                        cleanup_timeout_seconds=lifecycle["cleanup_timeout_seconds"])


def _observation_progress(records):
    observers = [r for r in records if r.get("authored_role") in ("postcell-observer", "timing-postcell")]
    if not observers:
        return {}
    states = [r["state"] for r in observers]
    outcome = ("failed" if "failed" in states else "interrupted" if "interrupted" in states
               else "succeeded" if all(s == "succeeded" for s in states)
               else "incomplete" if any(s != "not_run" for s in states) else "not_run")
    result = dict(authored_observation=outcome)
    for role, key in (("observer-bootstrap", "observer_bootstrap"), ("observer-cleanup", "observer_cleanup")):
        matches = [r for r in records if r.get("authored_role") == role]
        if matches:
            result[key] = matches[0]["state"]
    return result


def _scope_progress(route, outcome):
    if route == SELECTED_ROUTE:
        return dict(route=route, source_scope="selected_cells", whole_notebook_complete=False,
                    original_execution="not_executed_as_whole", selected_execution=outcome)
    return dict(original_execution=outcome)


def _original_outcome(records):
    states = [r["state"] for r in records if r["original_index"] is not None and r["type"] == "code"]
    return ("succeeded" if states and all(s == "succeeded" for s in states)
            else "incomplete" if any(s != "not_run" for s in states) else "not_run")


def _initialize_disposition(output, contract, cells):
    indices = _execution_indices(contract, cells)
    if contract.get("route") != SELECTED_ROUTE:
        return
    rows = []
    for index, cell in enumerate(cells):
        included = index in indices
        state = "not_run" if included else "excluded_by_contract" if cell["cell_type"] == "code" else "not_executable"
        rows.append(dict(original_index=index, type=cell["cell_type"],
                         source_sha256=digest(cell_text(cell).encode("utf-8")), state=state,
                         reason=None if included else contract["excluded_code_cells"].get(str(index), "Markdown retained in original source; not executable")))
    atomic_json(output / "source-disposition.json", dict(route=SELECTED_ROUTE,
                whole_notebook_complete=False, selected_cells=indices, cells=rows))


def _update_disposition(output, records):
    path = output / "source-disposition.json"
    if not path.exists():
        return
    disposition = json.loads(path.read_bytes())
    by_index = {r["original_index"]: r for r in records if r["original_index"] is not None}
    for row in disposition["cells"]:
        if row["original_index"] in by_index:
            record = by_index[row["original_index"]]
            if record["source_sha256"] != row["source_sha256"] or record["type"] != row["type"]:
                raise ValueError("DISPOSITION_SOURCE_MISMATCH")
            row["state"] = record["state"]
    atomic_json(path, disposition)


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
        self.engine_pid = process.pid

    def command(self, command):
        return command

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
    _initialize_disposition(output, config["contract"], json.loads((output / "source-original.ipynb").read_bytes())["cells"])
    atomic_json(output / "engine-request.json", config)
    status = dict(version=1, state="starting", contract=config["contract"]["id"], route="notebook",
                  source_sha256=config["contract"]["source"]["sha256"], contract_sha256=config["contract_sha256"],
                  identity=config["identity"], profile=config["profile"], original_execution="not_run",
                  authored_verification="not_run", external_resources="outstanding", interpretation="outstanding")
    status.update(_scope_progress(config["contract"].get("route"), "not_run"))

    def publish():
        atomic_json(output / "status.json", status)
        with (output / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(dict(time=time.time(), **status)) + "\n")
        if events is not None:
            events(dict(status))

    publish()
    try:
        if sys.platform == 'linux':
            from linux_lifecycle import LinuxService
            job = LinuxService(output, config['profile']['service_runtime_seconds'])
        else:
            job = _WindowsJob()
    except Exception as error:
        status.update(state="failed", error=str(error), cleanup={"method": "not_started"})
        publish()
        raise
    process = None
    requested = False
    forced = False
    membership = None
    launcher_lost = False
    try:
        with (output / "engine.stdout").open("w", encoding="utf-8") as stdout, (output / "engine.stderr").open("w", encoding="utf-8") as stderr:
            command = job.command([config["python"], "-I", str(Path(__file__).resolve()), "--engine", str(output)])
            process = subprocess.Popen(command,
                                       stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, text=True,
                                       close_fds=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
            job.assign(process)
            status["engine_pid"] = job.engine_pid
            status['launcher_pid'] = process.pid
            if sys.platform == 'linux':
                status['client_pid'] = job.client_pid
            process.stdin.write("start\n")
            process.stdin.flush()
            status["state"] = "running"
            publish()
            deadline = None
            while process.poll() is None:
                if sys.platform == 'linux' and job.client_exited() and job.active():
                    launcher_lost = True
                    _close_control_pipe(process)
                    job.terminate()
                    break
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
            if sys.platform == 'linux':
                _close_control_pipe(process)
                unit = job.observe()
                status['service_result'] = unit.get('Result') if unit.get('LoadState') != 'not-found' else 'unit_collected'
                if job.active():
                    launcher_lost = True
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
        else:
            _recover_checkpoint_disposition(output, status)
        status["cleanup"] = dict(active_processes=remaining, kernel_job_membership=membership,
                                 method="forced" if forced else "graceful", engine_exit=process.returncode)
        if sys.platform == 'linux':
            status['cleanup'].update(containment='systemd_service', population_semantics='zero or populated indicator',
                                     launcher_exit=process.returncode, engine_exit=None)
            if status.get('service_result') == 'timeout':
                status.update(state='failed', failure_cause='service_runtime_timeout')
            elif launcher_lost:
                status.update(state='failed', failure_cause='launcher_loss', launcher_lost_with_live_service=True)
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
                _update_disposition(output, cells)
                status.update(_scope_progress(status.get("route"), _original_outcome(cells)))
                status.update(_observation_progress(cells))
                if not result_path.exists():
                    status["authored_verification"] = cells[-1]["state"]
        elif process.returncode != 0 or status["state"] != "succeeded":
            status["state"] = "failed"
        if remaining or (status["state"] == "succeeded" and membership is not True):
            status.update(state="failed", error="CLEANUP_OR_MEMBERSHIP_UNCONFIRMED")
        publish()
        return status
    except BaseException as error:
        cleanup_errors = []

        def attempt(label, operation):
            try:
                return operation()
            except Exception as cleanup_error:
                cleanup_errors.append(dict(step=label, error=str(cleanup_error)))

        if process is not None:
            _close_control_pipe(process)
            attempt('terminate_owned_containment', job.terminate)
            if process.poll() is None:
                if sys.platform == 'linux':
                    attempt('terminate_verified_client', job.stop_client)
                else:
                    attempt('terminate_owned_launcher', process.kill)
            attempt('collect_owned_launcher', lambda: process.wait(timeout=10))
        remaining = attempt('observe_population', job.active)
        if not (output / 'engine-result.json').exists():
            attempt('recover_checkpoints', lambda: _recover_checkpoint_disposition(output, status))
        status.update(state="failed", error=str(error), cleanup={"active_processes": remaining, "method": "exception",
                      'errors': cleanup_errors, 'unconfirmed': remaining is None or bool(remaining) or bool(cleanup_errors)})
        publish()
        raise
    finally:
        _close_control_pipe(process)
        try:
            job.close()
        except Exception as error:
            status['state'] = 'failed'
            status.setdefault('cleanup', {})['unconfirmed'] = True
            status['cleanup'].setdefault('errors', []).append(dict(step='close_containment', error=str(error)))
            publish()


def _close_control_pipe(process):
    if process is not None and process.stdin and not process.stdin.closed:
        try:
            process.stdin.close()
        except OSError:
            pass  # Teardown still has to stop the owned job/service.


def _recover_checkpoint_disposition(output, status):
    path = output / 'cells.json'
    if not path.exists():
        return
    cells = json.loads(path.read_bytes())
    for cell in cells:
        if cell['state'] == 'running':
            cell.update(state='interrupted', error=dict(type='EngineReportMissing',
                        message='Engine stopped before a terminal report; last checkpoint retained'))
    status.update(_scope_progress(status.get('route'), _original_outcome(cells)))
    witness = [cell for cell in cells if cell.get('authored_role') == 'independent-witness']
    status['authored_verification'] = witness[0]['state'] if witness else 'not_run'
    status.update(_observation_progress(cells))
    status['terminal_engine_report_missing'] = True
    atomic_json(path, cells)
    _update_disposition(output, cells)


async def _run_notebook(output, config, control_state=None):
    import nbformat
    from nbclient import NotebookClient
    from nbclient.exceptions import DeadKernelError
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
    execution_indices = _execution_indices(contract, original_cells)
    observers, lifecycle = _observer_sources(contract, original_cells)
    if contract.get("route") == SELECTED_ROUTE and not (output / "source-disposition.json").exists():
        _initialize_disposition(output, contract, original_cells)
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

    def authored(source, role, after_original_index=None):
        append(nbformat.v4.new_code_cell(source, metadata={"tags": ["authored-" + role]}), role=role)
        if after_original_index is not None:
            records[-1]["after_original_index"] = after_original_index

    if contract["preamble"]:
        authored(contract["preamble"], "preamble")
    if lifecycle:
        authored(lifecycle["bootstrap"], "observer-bootstrap")
    setup = contract.get("setup")
    for index in execution_indices:
        cell = original_cells[index]
        if setup and index == setup["cell"]:
            authored(_setup_observer(setup["commands"]), "setup-observer")
        append(cell, original_index=index)
        if setup and index == setup["cell"]:
            authored(SETUP_CHECK, "setup-check")
        if index in observers:
            authored(observers[index]["source"], observers[index]["role"], index)
    cleanup_index = None
    if lifecycle:
        cleanup_index = len(notebook.cells)
        authored(lifecycle["cleanup"], "observer-cleanup")
    authored(config["witness"], "independent-witness")
    result = dict(state="failed", original_execution="not_run", authored_verification="not_run")
    result.update(_scope_progress(contract.get("route"), "not_run"))

    def checkpoint():
        atomic_json(output / "executed.ipynb", notebook)
        atomic_json(output / "cells.json", records)
        _update_disposition(output, records)

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
                async def execute_cell(i):
                    cell = notebook.cells[i]
                    records[i]["state"] = "running"
                    checkpoint()
                    started = time.monotonic()
                    try:
                        if i == cleanup_index:
                            await asyncio.wait_for(client.async_execute_cell(cell, i),
                                                   timeout=lifecycle["cleanup_timeout_seconds"])
                        else:
                            await client.async_execute_cell(cell, i)
                        records[i]["state"] = "succeeded"
                    except BaseException as error:
                        interrupted = isinstance(error, asyncio.CancelledError) or bool(control_state)
                        records[i].update(state="interrupted" if interrupted else "failed",
                                          error={"type": type(error).__name__, "message": str(error)})
                        raise
                    finally:
                        records[i]["elapsed_seconds"] = time.monotonic() - started
                        checkpoint()

                try:
                    for i, cell in enumerate(notebook.cells):
                        if cell.cell_type == "code":
                            await execute_cell(i)
                except BaseException as primary:
                    # Cleanup is an authored cell, never a replacement for the
                    # original exception. Do not send more work to a timed-out,
                    # dead or cancelled kernel; owned shutdown remains in charge.
                    if cleanup_index is not None and records[cleanup_index]["state"] == "not_run":
                        if (not isinstance(primary, (asyncio.CancelledError, TimeoutError, DeadKernelError))
                                and not control_state):
                            try:
                                await execute_cell(cleanup_index)
                            except BaseException:
                                pass  # Exact cleanup error is retained in its checkpoint.
                        else:
                            records[cleanup_index]["skip_reason"] = "kernel_interrupted_or_unavailable"
                            checkpoint()
                    raise
            preserved = [(notebook.cells[source_positions[i]].cell_type, notebook.cells[source_positions[i]].source)
                         for i in execution_indices]
            if preserved != [original[i] for i in execution_indices]:
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
            result.update(_scope_progress(contract.get("route"), "succeeded"))
            if contract.get("acceptance_field"):
                if result["independent_results"].get(contract["acceptance_field"]) is not True:
                    raise AssertionError("SEMANTIC_ACCEPTANCE_FAILED")
        except BaseException as error:
            result["error"] = dict(type=type(error).__name__, message=str(error), traceback=traceback.format_exc())
            codes = [records[source_positions[i]]["state"] for i in contract["code_cells"]]
            result["state"] = "failed"
            result.update(_scope_progress(contract.get("route"), "succeeded" if all(x == "succeeded" for x in codes) else "incomplete"))
            result["authored_verification"] = "failed" if records[-1]["state"] == "succeeded" else records[-1]["state"]
        finally:
            result.update(_observation_progress(records))
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
        control_state = {}
        task = asyncio.create_task(_run_notebook(output, config, control_state))
        loop = asyncio.get_running_loop()
        control_event = None

        def interrupt(reason):
            nonlocal control_event
            if not task.done() and control_event is None:
                control_event = reason
                control_state['reason'] = reason
                task.cancel()

        def control():
            reason = "control_eof"
            for line in sys.stdin:
                if line.strip() == "cancel":
                    reason = "cancel_requested"
                    break
            try:
                loop.call_soon_threadsafe(interrupt, reason)
            except RuntimeError:
                pass  # Execution finished and the loop has already closed.

        threading.Thread(target=control, daemon=True).start()
        try:
            result = await task
        except asyncio.CancelledError:
            result = dict(state="failed", original_execution="not_run", authored_verification="not_run")
            result.update(_scope_progress(config["contract"].get("route"), "not_run"))
        if control_event is not None:
            result.update(state="failed", control_event=control_event)
            atomic_json(output / "engine-result.json", result)
        return result

    result = asyncio.run(main())
    return 0 if result["state"] == "succeeded" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", type=Path, required=True)
    sys.exit(_engine(parser.parse_args().engine))
