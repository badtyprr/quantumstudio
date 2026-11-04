"""Linux containment capability probe; notebook backend acceptance is separate."""
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import uuid


def _command(args, timeout=10):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return dict(args=args, exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)


def _unit_snapshot(unit):
    properties = ["Id", "Description", "LoadState", "ActiveState", "SubState", "MainPID", "ControlGroup",
                  "User", "Type", "ExitType", "RemainAfterExit", "Restart", "KillMode", "SendSIGKILL",
                  "TimeoutStartUSec", "TimeoutStopUSec", "RuntimeMaxUSec", "Result", "ExecMainStatus"]
    result = _command(["systemctl", "show", unit, "--no-pager", "--property=" + ",".join(properties)])
    result["properties"] = dict(line.split("=", 1) for line in result["stdout"].splitlines() if "=" in line)
    return result


def _owned_cgroup(control_group, unit):
    root = Path("/sys/fs/cgroup").resolve(strict=True)
    relative = Path(control_group)
    if not relative.is_absolute() or ".." in relative.parts or relative.name != unit:
        raise RuntimeError("UNEXPECTED_CONTROL_GROUP")
    path = (root / control_group.lstrip("/")).resolve(strict=True)
    if root not in path.parents:
        raise RuntimeError("CONTROL_GROUP_OUTSIDE_CGROUP_MOUNT")
    return path


def _empty_group(path):
    if not path.exists():
        return {"empty": True, "observation": "previously_verified_cgroup_removed"}
    events = dict(line.split() for line in (path / "cgroup.events").read_text().splitlines())
    return {"empty": events.get("populated") == "0", "observation": "cgroup.events", "events": events}


def _close_control(process, report):
    if process is not None and process.stdin:
        try:
            process.stdin.close()
        except OSError as error:
            report.update(state="failed", control_close_error=str(error))


class LinuxService:
    """One gated engine and its descendants, owned by a unique systemd service.

    The launcher is not the engine. active() reports subtree population, not an
    exact process count; zero is established only from the verified cgroup.
    """

    def __init__(self, output, runtime_seconds):
        if sys.platform != "linux":
            raise RuntimeError("LINUX_REQUIRED")
        import pwd
        if os.geteuid() == 0:
            raise RuntimeError("NONROOT_RUNNER_REQUIRED")
        if type(runtime_seconds) is not int or not 2 <= runtime_seconds <= 3600:
            raise ValueError("INVALID_SERVICE_RUNTIME_BOUND")
        if Path('/proc/1/comm').read_text().strip() != 'systemd' or not Path('/sys/fs/cgroup/cgroup.controllers').is_file():
            raise RuntimeError('SYSTEMD_CGROUP_V2_REQUIRED')
        self.account = pwd.getpwuid(os.geteuid())
        self.output = Path(output).resolve(strict=True)
        self.runtime = runtime_seconds
        self.unit = 'qalculate-notebook-' + uuid.uuid4().hex + '.service'
        self.description = 'Qalculate owned engine ' + self.unit
        self.group = None
        self.engine_pid = None
        self.requested = False
        self.evidence = dict(unit=self.unit, description=self.description, runtime_seconds=self.runtime,
                             population_semantics='cgroup subtree populated indicator, not process count')
        if _command(['sudo', '-n', 'true'])['exit_code']:
            raise RuntimeError('NONINTERACTIVE_SUDO_REQUIRED')
        self.evidence['before'] = _unit_snapshot(self.unit)
        if self.evidence['before']['properties'].get('LoadState') != 'not-found':
            raise RuntimeError('UNIT_NAME_NOT_PROVEN_UNUSED')
        self.save()

    def save(self):
        temporary = self.output / 'service.json.tmp'
        temporary.write_text(json.dumps(self.evidence, indent=2), encoding='utf-8')
        os.replace(temporary, self.output / 'service.json')

    def command(self, command):
        self.python = Path(command[0]).resolve(strict=True)
        self.requested = True
        # env -i removes inherited manager variables as well as caller settings.
        # env execs Python in place, so the gated Python remains MainPID.
        return ['sudo', '-n', 'systemd-run', '--quiet', '--pipe', '--wait', '--expand-environment=no',
                '--unit=' + self.unit, '--description=' + self.description,
                '--property=User=' + self.account.pw_name, '--property=Type=exec',
                '--property=ExitType=main', '--property=RemainAfterExit=no', '--property=Restart=no',
                '--property=KillMode=control-group', '--property=SendSIGKILL=yes',
                '--property=TimeoutStartSec=10s', '--property=TimeoutStopSec=5s',
                '--property=RuntimeMaxSec=' + str(self.runtime) + 's',
                '--property=WorkingDirectory=' + str(self.output),
                '/usr/bin/env', '-i', 'PATH=/usr/local/bin:/usr/bin:/bin',
                'HOME=' + self.account.pw_dir, 'LANG=C.UTF-8', 'TZ=UTC', *command]

    def assign(self, process):
        self.evidence['launcher_pid'] = process.pid
        deadline = time.monotonic() + 10
        while True:
            snapshot = _unit_snapshot(self.unit)
            props = snapshot['properties']
            self.evidence['at_gate'] = snapshot
            pid = int(props.get('MainPID', '0'))
            if pid:
                try:
                    if Path(f'/proc/{pid}/exe').resolve(strict=True) == self.python:
                        break
                except FileNotFoundError:
                    pass
            if process.poll() is not None or time.monotonic() >= deadline:
                self.save()
                raise RuntimeError('SERVICE_DID_NOT_REACH_GATE')
            time.sleep(0.05)
        for key, value in {'Id': self.unit, 'Description': self.description, 'User': self.account.pw_name,
                           'Type': 'exec', 'ExitType': 'main', 'RemainAfterExit': 'no', 'Restart': 'no',
                           'KillMode': 'control-group', 'SendSIGKILL': 'yes', 'TimeoutStartUSec': '10s',
                           'TimeoutStopUSec': '5s'}.items():
            if props.get(key) != value:
                raise RuntimeError('SERVICE_PROPERTY_MISMATCH: ' + key)
        # systemctl humanizes long durations; inspect the numeric D-Bus value.
        duration = _command(['busctl', 'get-property', 'org.freedesktop.systemd1',
                             '/org/freedesktop/systemd1/unit/' + self.unit.replace('-', '_2d').replace('.', '_2e'),
                             'org.freedesktop.systemd1.Service', 'RuntimeMaxUSec'])
        if duration['exit_code'] or duration['stdout'].strip() != 't ' + str(self.runtime * 1000000):
            raise RuntimeError('SERVICE_RUNTIME_BOUND_UNCONFIRMED')
        self.group = _owned_cgroup(props['ControlGroup'], self.unit)
        self.engine_pid = pid
        membership = Path(f'/proc/{pid}/cgroup').read_text()
        uid = next(line for line in Path(f'/proc/{pid}/status').read_text().splitlines() if line.startswith('Uid:'))
        if not self.contains(pid) or any(int(value) != os.geteuid() for value in uid.split()[1:]):
            raise RuntimeError('ENGINE_OWNERSHIP_MISMATCH')
        if Path(f'/proc/{pid}/exe').resolve(strict=True) != self.python:
            raise RuntimeError('ENGINE_EXECUTABLE_MISMATCH')
        if (self.output / 'kernel.json').exists():
            raise RuntimeError('KERNEL_STARTED_BEFORE_GATE')
        self.evidence.update(engine_pid=pid, engine_cgroup=membership, engine_uid=uid,
                             runtime_property=duration, gate_held=True)
        self.save()

    def contains(self, pid):
        if self.group is None:
            return False
        membership = Path(f'/proc/{int(pid)}/cgroup').read_text().splitlines()
        expected = '/' + self.group.relative_to(Path('/sys/fs/cgroup').resolve()).as_posix()
        return any(line == '0::' + expected or line.startswith('0::' + expected + '/') for line in membership)

    def active(self):
        if self.group is None:
            if not self.requested:
                return 0
            snapshot = _unit_snapshot(self.unit)
            self.evidence['unverified_population'] = snapshot
            self.save()
            if snapshot['properties'].get('LoadState') == 'not-found':
                return 0
            return 1
        observation = _empty_group(self.group)
        self.evidence['population'] = observation
        self.save()
        return 0 if observation['empty'] else 1

    def observe(self):
        snapshot = _unit_snapshot(self.unit)
        self.evidence['last_unit'] = snapshot
        self.save()
        return snapshot['properties']

    def terminate(self):
        if not self.requested:
            return
        props = self.observe()
        if props.get('LoadState') == 'not-found':
            if self.group is not None and self.active():
                raise RuntimeError('MISSING_UNIT_WITH_POPULATED_GROUP')
            return
        if props.get('Description') != self.description or props.get('User') != self.account.pw_name:
            raise RuntimeError('UNIT_OWNERSHIP_NOT_CONFIRMED')
        stopped = _command(['sudo', '-n', 'systemctl', 'stop', self.unit], timeout=15)
        self.evidence['stop'] = stopped
        self.save()
        if stopped['exit_code']:
            raise RuntimeError('OWNED_SERVICE_STOP_FAILED')

    def close(self):
        if not self.requested:
            return
        if self.active():
            self.terminate()
        props = self.observe()
        if props.get('Description') == self.description and props.get('User') == self.account.pw_name:
            self.evidence['reset'] = _command(['sudo', '-n', 'systemctl', 'reset-failed', self.unit])
            self.save()


def preflight(output):
    """Probe one uniquely owned disposable service without framework imports.

    This proves only startup/gate/user/membership/ordinary cleanup. It is not the
    later kernel/cancellation/crash/escaped-descendant lifecycle test suite.
    """
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = dict(scope=preflight.__doc__, state="failed", python=platform.python_version(),
                  executable=sys.executable, platform=sys.platform, kernel=platform.release(),
                  architecture=platform.machine(), capabilities={})
    unit = "qalculate-notebook-probe-" + uuid.uuid4().hex + ".service"
    description = "Qalculate owned probe " + unit
    process = None
    group = None
    requested = False

    def save():
        temporary = output / "capabilities.json.tmp"
        temporary.write_text(json.dumps(report, indent=2), encoding="utf-8")
        os.replace(temporary, output / "capabilities.json")

    try:
        if sys.platform != "linux":
            raise RuntimeError("LINUX_REQUIRED")
        import pwd
        if os.geteuid() == 0:
            raise RuntimeError("NONROOT_RUNNER_REQUIRED")
        user = pwd.getpwuid(os.geteuid()).pw_name
        report.update(uid=os.geteuid(), user=user, unit=unit,
                      runner_image={name: os.environ.get(name) for name in ("ImageOS", "ImageVersion", "RUNNER_OS", "RUNNER_ARCH")},
                      os_release=Path("/etc/os-release").read_text(),
                      pid1=Path("/proc/1/comm").read_text().strip(),
                      memory=Path("/proc/meminfo").read_text(),
                      disk_free_bytes=shutil.disk_usage(output).free,
                      supervisor_cgroup=Path("/proc/self/cgroup").read_text())
        if report["pid1"] != "systemd" or not Path("/sys/fs/cgroup/cgroup.controllers").is_file():
            raise RuntimeError("SYSTEMD_CGROUP_V2_REQUIRED")
        report["capabilities"]["systemd_version"] = _command(["systemctl", "--version"])
        report["capabilities"]["sudo"] = _command(["sudo", "-n", "true"])
        if report["capabilities"]["sudo"]["exit_code"]:
            raise RuntimeError("NONINTERACTIVE_SUDO_REQUIRED")
        before = _unit_snapshot(unit)
        report["unit_before"] = before
        if before["properties"].get("LoadState") != "not-found":
            raise RuntimeError("UNIT_NAME_NOT_PROVEN_UNUSED")
        marker = output / "gate-released.txt"
        script = ("import pathlib,sys; "
                  "line=sys.stdin.readline(); "
                  "sys.exit(7) if line != 'start\\n' else None; "
                  "pathlib.Path(sys.argv[1]).write_text('gate released',encoding='utf-8')")
        args = ["sudo", "-n", "systemd-run", "--quiet", "--pipe", "--wait", "--unit=" + unit,
                "--description=" + description, "--property=User=" + user, "--property=Type=exec",
                "--property=ExitType=main", "--property=RemainAfterExit=no", "--property=Restart=no",
                "--property=KillMode=control-group", "--property=SendSIGKILL=yes",
                "--property=TimeoutStartSec=10s", "--property=TimeoutStopSec=5s",
                "--property=RuntimeMaxSec=30s", "--property=WorkingDirectory=" + str(output),
                sys.executable, "-I", "-c", script, str(marker)]
        with (output / "service.stdout").open("w") as stdout, (output / "service.stderr").open("w") as stderr:
            process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, text=True, close_fds=True)
            requested = True
            report["launcher_pid"] = process.pid
            deadline = time.monotonic() + 10
            while True:
                snapshot = _unit_snapshot(unit)
                properties = snapshot["properties"]
                report["unit_at_gate"] = snapshot
                if int(properties.get("MainPID", "0")):
                    break
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("SERVICE_DID_NOT_REACH_GATE")
                time.sleep(0.05)
            for key, value in {"Id": unit, "Description": description, "User": user, "Type": "exec",
                               "ExitType": "main", "RemainAfterExit": "no", "Restart": "no",
                               "KillMode": "control-group", "SendSIGKILL": "yes", "TimeoutStartUSec": "10s",
                               "TimeoutStopUSec": "5s", "RuntimeMaxUSec": "30s"}.items():
                if properties.get(key) != value:
                    raise RuntimeError("SERVICE_PROPERTY_MISMATCH: " + key)
            engine_pid = int(properties["MainPID"])
            group = _owned_cgroup(properties["ControlGroup"], unit)
            membership = Path(f"/proc/{engine_pid}/cgroup").read_text()
            uid_line = next(line for line in Path(f"/proc/{engine_pid}/status").read_text().splitlines() if line.startswith("Uid:"))
            if f"0::{properties['ControlGroup']}" not in membership.splitlines() or int(uid_line.split()[1]) != os.geteuid():
                raise RuntimeError("ENGINE_OWNERSHIP_MISMATCH")
            if marker.exists():
                raise RuntimeError("GATE_RELEASED_EARLY")
            report.update(engine_pid=engine_pid, engine_cgroup=membership, engine_uid=uid_line, gate_held=True)
            save()
            process.stdin.write("start\n")
            process.stdin.flush()
            process.wait(timeout=15)
        report["launcher_exit"] = process.returncode
        report["unit_after"] = _unit_snapshot(unit)
        report["cleanup"] = _empty_group(group)
        if process.returncode != 0 or not marker.exists() or not report["cleanup"]["empty"]:
            raise RuntimeError("GATE_OR_CLEANUP_ACCEPTANCE_FAILED")
        report["state"] = "succeeded"
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        _close_control(process, report)
        if requested:
            try:
                snapshot = _unit_snapshot(unit)
                if snapshot["properties"].get("Description") == description:
                    report["owned_teardown"] = _command(["sudo", "-n", "systemctl", "stop", unit], timeout=15)
                    report["owned_reset"] = _command(["sudo", "-n", "systemctl", "reset-failed", unit])
                elif snapshot["properties"].get("LoadState") != "not-found":
                    report.update(state="failed", teardown_error="OWNERSHIP_NOT_CONFIRMED; unit was not stopped")
            except Exception as error:
                report.update(state="failed", teardown_error=str(error))
        if process is not None:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                report.update(state="failed", launcher_cleanup="forced; service state requires retained evidence")
                try:
                    process.kill()  # Only the directly owned launcher, not a unit or PID search.
                    process.wait(timeout=5)
                except Exception as error:
                    report["launcher_cleanup_error"] = str(error)
            except Exception as error:
                report.update(state="failed", launcher_cleanup_error=str(error))
        save()
    return report
