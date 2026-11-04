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
