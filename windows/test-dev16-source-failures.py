"""Finite QB004 missing-source/reimport acceptance; requires a complete package.

The double-X/single-X wrapper is authored test input, not notebook completion.
Capture validation is mechanical; all 24 images require separate visual review.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import traceback
import zlib

FIXTURES = {
    "oracle.qasm": "00ca08a9b091c46c942bc1f1878ccc69e922a0500b61c79a11b87c8c4debc4b1",
    "bernvaz.qasm": "9f9eb3c6537bf209ff7c98fae8a5e2e77e1e135597d81569bf978498100f977e",
}
STATES = ("reopened", "reimported", "undone")
CAPTURES = ("blank", "unchanged", "missing", "changed", "reimported", "undone")


class OwnedTimeout(TimeoutError):
    def __init__(self, confirmed):
        super().__init__("Owned process timed out; cleanup confirmed=" + str(confirmed))
        self.cleanup_confirmed = confirmed


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def expected_state(module, changed):
    if module == "oracle":
        return "|0001>" if changed else "|1001>"
    require(module == "bernvaz", "Unknown module")
    return "(|1110>-|1111>)/sqrt(2)" if changed else "(|0110>-|0111>)/sqrt(2)"


def circuit_expression(document, classical):
    require(document["Format"] == "QuantumStudio.SourceCircuit", "Wrong document format")
    require(document["Classical"] is classical and document["PublishedU"] is False, "Import options changed")
    circuit = document["Circuit"]
    require(type(circuit["Qubits"]) is int and circuit["Qubits"] == 4, "Expected four qubits")
    require(isinstance(circuit["Steps"], list) and circuit["Steps"], "Missing saved gate sequence")
    value = "|0000>"
    for step in circuit["Steps"]:
        if classical:
            require(step.get("Kind") == "Gate", "Non-gate classical step")
        gate = step.get("Expression" if classical else "Gate")
        require(gate in ("H", "X", "CNOT"), "Unexpected gate")
        wires = step["Wires"]
        require(isinstance(wires, list) and len(wires) == (2 if gate == "CNOT" else 1), "Wrong gate arity")
        require(all(type(wire) is int and 0 <= wire < 4 for wire in wires) and len(set(wires)) == len(wires), "Invalid wires")
        require(not step.get("Angle"), "Unexpected angle")
        # Gate-only validation must not silently discard executable branch/noise payloads.
        allowed = {"Kind", "Expression", "Wires"} if classical else {"Gate", "Wires", "Angle"}
        for key, payload in step.items():
            if key not in allowed:
                require(payload is None or payload == "" or payload == [], "Unexpected executable payload: " + key)
        value = f"apply({gate},{value},[{','.join(map(str, wires))}])"
    return value


def source_bytes(document, entry):
    source = document["Source"]
    require(source["Entry"] == entry and source["ModuleHeaders"] is True, "Source import mode changed")
    files = {}
    for item in source["Files"]:
        name = item["Name"]
        require(name not in files and type(item["Bom"]) is bool, "Duplicate/invalid source")
        raw = (b"\xef\xbb\xbf" if item["Bom"] else b"") + item["Text"].encode("utf-8")
        require(hashlib.sha256(raw).hexdigest() == item["Sha256"], "Captured source hash mismatch")
        files[name] = raw
    return files


def png_record(path):
    raw = path.read_bytes()
    require(raw[:8] == b"\x89PNG\r\n\x1a\n", "Not PNG")
    offset, chunks, image_data = 8, [], bytearray()
    width = height = 0
    while offset < len(raw):
        require(offset + 12 <= len(raw), "Truncated PNG")
        size = struct.unpack_from(">I", raw, offset)[0]
        kind = raw[offset + 4:offset + 8]
        end = offset + 12 + size
        require(end <= len(raw), "Truncated PNG chunk")
        payload = raw[offset + 8:end - 4]
        require(zlib.crc32(kind + payload) & 0xffffffff == struct.unpack_from(">I", raw, end - 4)[0], "PNG CRC mismatch")
        chunks.append(kind)
        if kind == b"IHDR":
            require(len(chunks) == 1 and len(payload) == 13, "Invalid PNG header")
            width, height = struct.unpack_from(">II", payload)
            require(0 < width <= 10000 and 0 < height <= 10000, "Invalid PNG dimensions")
        if kind == b"IDAT":
            image_data.extend(payload)
        offset = end
        if kind == b"IEND":
            require(size == 0 and offset == len(raw), "Trailing PNG bytes")
            break
    require(chunks and chunks[0] == b"IHDR" and chunks[-1] == b"IEND" and image_data, "Incomplete PNG")
    decoded = zlib.decompress(image_data)
    require(decoded, "Empty PNG pixels")
    return dict(path=str(path), sha256=digest(path), width=width, height=height, visual_review="pending")


def plain_history(text):
    """Only compact, typed, unsourced H/X/CNOT CircuitFile history may reorder keys."""
    if not isinstance(text, str) or len(text) > 262144:
        return None
    def unique_members(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, "Duplicate history member")
            value[key] = item
        return value
    try:
        value = json.loads(text, object_pairs_hook=unique_members)
        if type(value) is not dict or set(value) != {"Version", "Qubits", "Steps"}:
            return None
        # Match the C# guard: no duplicate members, alternate numeric spelling,
        # whitespace normalization or other serialization changes are excused.
        if json.dumps(value, separators=(",", ":"), ensure_ascii=False) != text:
            return None
        if type(value["Version"]) is not int or value["Version"] != 1:
            return None
        if type(value["Qubits"]) is not int or not 1 <= value["Qubits"] <= 25:
            return None
        steps = value["Steps"]
        if type(steps) is not list or len(steps) > 512:
            return None
        for step in steps:
            if type(step) is not dict or set(step) != {"Gate", "Angle", "Wires"}:
                return None
            if type(step["Gate"]) is not str or step["Gate"] not in ("H", "X", "CNOT"):
                return None
            if type(step["Angle"]) is not str or step["Angle"] != "":
                return None
            wires = step["Wires"]
            if type(wires) is not list or len(wires) != (2 if step["Gate"] == "CNOT" else 1):
                return None
            if not all(type(wire) is int and 0 <= wire < value["Qubits"] for wire in wires):
                return None
            if len(set(wires)) != len(wires):
                return None
        return value
    except (ValueError, TypeError, RecursionError):
        return None


def history_entry_equal(left, right):
    if left == right:
        return True
    first, second = plain_history(left), plain_history(right)
    return first is not None and second is not None and first == second


def history_chain_equal(left, right):
    return len(left) == len(right) and all(history_entry_equal(a, b) for a, b in zip(left, right))


def history_equal(left, right):
    return (set(left) == set(right) == {"Current", "Undo", "Redo"}
            and left["Current"] == right["Current"]
            and history_chain_equal(left["Undo"], right["Undo"])
            and history_chain_equal(left["Redo"], right["Redo"]))


def check_history(records, saved):
    baseline, seeded = records["reopened"], records["seeded"]
    require(baseline["Current"] == saved["reopened"], "Reopened history mismatch")
    require(seeded["Current"] == baseline["Current"] and history_chain_equal(seeded["Undo"], baseline["Undo"]) and len(seeded["Redo"]) == 1, "Invalid seeded history")
    marker = json.loads(seeded["Redo"][0])
    original = json.loads(baseline["Current"])
    require(marker["Source"] == original["Source"], "Marker modified retained sources")
    require(marker["Circuit"]["Steps"][:-1] == original["Circuit"]["Steps"], "Marker changed existing steps")
    last = marker["Circuit"]["Steps"][-1]
    require(last.get("Expression" if original["Classical"] else "Gate") == "X" and last["Wires"] == [0], "Incorrect marker")
    for stage in ("blank", "unchanged", "missing-check", "missing-reimport", "restored", "changed"):
        require(history_equal(records[stage], seeded), stage + " lost document/history")
    replaced = records["reimported"]
    require(history_equal(replaced, dict(Current=saved["reimported"], Undo=[baseline["Current"]] + baseline["Undo"], Redo=[])), "Replacement history mismatch")
    undone = dict(Current=saved["undone"], Undo=baseline["Undo"], Redo=[replaced["Current"]])
    require(saved["undone"] == saved["reopened"] and history_equal(records["undone"], undone) and history_equal(records["final"], undone), "Undo history mismatch")
    require(history_equal(records["redone"], replaced) and records["fresh-root"] is True, "Redo/fresh-root mismatch")


def run_logged(command, prefix, *, timeout, input_bytes=None, env=None):
    write_json(Path(str(prefix) + ".command.json"), command)
    if input_bytes is not None:
        Path(str(prefix) + ".stdin").write_bytes(input_bytes)
    startup = None
    if os.name == "nt":
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, startupinfo=startup)
    try:
        stdout, stderr = process.communicate(input_bytes, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        Path(str(prefix) + ".stdout").write_bytes(error.stdout or b"")
        Path(str(prefix) + ".stderr").write_bytes(error.stderr or b"")
        write_json(Path(str(prefix) + ".exit.json"), dict(timeout=True, seconds=timeout))
        cleanup_status = dict(tree_confirmed=False, parent_reaped=False)
        try:
            if os.name == "nt":
                cleanup = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=15, startupinfo=startup)
                Path(str(prefix) + ".cleanup.stdout").write_bytes(cleanup.stdout)
                Path(str(prefix) + ".cleanup.stderr").write_bytes(cleanup.stderr)
                cleanup_status.update(tree_exit=cleanup.returncode, tree_confirmed=cleanup.returncode == 0)
        except Exception as cleanup_error:
            cleanup_status["tree_error"] = repr(cleanup_error)
            if isinstance(cleanup_error, subprocess.TimeoutExpired):
                Path(str(prefix) + ".cleanup.stdout").write_bytes(cleanup_error.stdout or b"")
                Path(str(prefix) + ".cleanup.stderr").write_bytes(cleanup_error.stderr or b"")
        finally:
            try:
                if process.poll() is None:
                    process.kill()
                cleanup_status["parent_exit"] = process.wait(timeout=10)
                cleanup_status["parent_reaped"] = True
            except Exception as reap_error:
                cleanup_status["parent_error"] = repr(reap_error)
            write_json(Path(str(prefix) + ".cleanup.json"), cleanup_status)
        raise OwnedTimeout(cleanup_status["tree_confirmed"] and cleanup_status["parent_reaped"]) from error
    Path(str(prefix) + ".stdout").write_bytes(stdout)
    Path(str(prefix) + ".stderr").write_bytes(stderr)
    write_json(Path(str(prefix) + ".exit.json"), dict(code=process.returncode))
    require(process.returncode == 0, "Command failed: " + str(prefix))
    return stdout


def residual_value(raw):
    value = complex(json.loads(raw)["text"].replace("−", "-").replace(" ", "").replace("i", "j"))
    require(math.isfinite(value.real) and math.isfinite(value.imag) and abs(value) < 1e-12, "State residual failed")
    return abs(value)


def package_hashes(package):
    paths = [package / "QuantumStudio.exe", package / "qasm-import/qasm-import.exe", package / "quantum-worker.exe"]
    require(all(path.is_file() for path in paths), "Missing packaged GUI/compiler/worker")
    data = sorted((package / "data").rglob("*"))
    require(any(path.is_file() for path in data), "Missing packaged definitions")
    paths += [path for path in data if path.is_file()]
    paths = sorted(path for path in package.rglob("*") if path.is_file())
    return {path.relative_to(package).as_posix(): digest(path) for path in paths}


def execute(package, output, repo, product_revision):
    require(output != package and package not in output.parents, "Audit output must be outside package")
    output.mkdir(parents=True, exist_ok=False)
    audit = dict(passed=False, product_revision=product_revision, harness_sha256=digest(Path(__file__)),
                 acceptance="finite authored source failure/reimport matrix", visual_review="pending", results=[])
    before = None
    try:
        contract_path = repo / "windows/fixtures/dev16-composer-contract.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        audit["contract_sha256"] = digest(contract_path)
        for filename, expected in FIXTURES.items():
            require(contract["fixtures"][filename] == expected, "Contract fixture identity changed")
            require(digest(repo / "windows/fixtures/qb004" / filename) == expected, "Original fixture identity changed")
        before = package_hashes(package)
        audit["package_before"] = before
        write_json(output / "audit.json", audit)
        for editor in ("composer", "classical"):
            for module in ("oracle", "bernvaz"):
                label = editor + "-" + module
                folder = output / (label + " Unicode κ")
                folder.mkdir()
                nested = folder / "nested modules λ"
                nested.mkdir()
                dependency = nested / (module + ".qasm")
                original_module = (repo / "windows/fixtures/qb004" / dependency.name).read_bytes()
                dependency.write_bytes(original_module)
                wrapper = folder / "wrapper.inc"
                wrapper.write_text(f'include "nested modules λ/{module}.qasm";\ngate after a {{ x a; x a; }}\n', encoding="utf-8", newline="")
                entry = folder / "main κ.qasm"
                prep = "x q[0]; " if module == "oracle" else ""
                entry.write_text('OPENQASM 3.0; include "stdgates.inc"; include "wrapper.inc"; qubit[3] q; qubit[1] ancilla; ' + prep + module + '(q,ancilla); after q[0];\n', encoding="utf-8-sig", newline="")
                initial = {path.relative_to(folder).as_posix(): path.read_bytes() for path in (entry, wrapper, dependency)}
                changed = dict(initial)
                changed["wrapper.inc"] = initial["wrapper.inc"].replace(b"x a; x a;", b"x a;")
                # Separate immutable authored-input copies survive GUI mutation/timeouts.
                retained = folder / "inputs"
                for name, raw in initial.items():
                    target = retained / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(raw)
                row = dict(name=label, passed=False, inputs={name: hashlib.sha256(raw).hexdigest() for name, raw in initial.items()}, semantic=[], captures=[])
                audit["results"].append(row)
                report = folder / "gui.txt"
                restore_allowed = True
                try:
                    run_logged([str(package / "QuantumStudio.exe"), "--dev16-source-failure-test", editor, str(entry), str(report)], folder / "gui-process", timeout=180)
                    require(report.read_text(encoding="utf-8-sig").startswith("PASS:"), "GUI assertion failure")
                    require(dependency.read_bytes() == original_module and entry.read_bytes() == initial[entry.name] and wrapper.read_bytes() == changed["wrapper.inc"], "Graph identity changed unexpectedly")
                    saved = {state: Path(str(report) + "." + state + ".qcircuit").read_text(encoding="utf-8-sig") for state in STATES}
                    check_history(json.loads(Path(str(report) + ".history.json").read_text(encoding="utf-8-sig")), saved)
                    for state in STATES:
                        document = json.loads(saved[state])
                        require(source_bytes(document, entry.name) == (changed if state == "reimported" else initial), "Captured source bytes differ")
                        expression = circuit_expression(document, editor == "classical")
                        expected = expected_state(module, state == "reimported")
                        query = f"quantum:norm(vec(({expression})-({expected})))"
                        raw = run_logged([str(package / "quantum-worker.exe"), "--json", "--approx"], folder / (state + "-worker"), timeout=30, input_bytes=query.encode("utf-8"), env=dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(package / "data")))
                        row["semantic"].append(dict(state=state, expected=expected, residual=residual_value(raw)))
                    row["captures"] = [png_record(Path(str(report) + "." + stage + ".png")) for stage in CAPTURES]
                    row["passed"] = True
                except OwnedTimeout as error:
                    restore_allowed = error.cleanup_confirmed
                    raise
                finally:
                    row["module_after_gui_sha256"] = digest(dependency) if dependency.exists() else None
                    # Preserve timeout/failure evidence before restoring the owned copy.
                    if restore_allowed:
                        dependency.write_bytes(original_module)
                        row["module_restored_sha256"] = digest(dependency)
                    else:
                        row["restoration_blocked"] = "Owned process tree termination unconfirmed; preserve graph for coordinator recovery."
                    write_json(output / "audit.json", audit)
        require(len(audit["results"]) == 4 and sum(len(row["semantic"]) for row in audit["results"]) == 12 and sum(len(row["captures"]) for row in audit["results"]) == 24, "Incomplete matrix")
        audit["passed"] = True
    except Exception:
        audit["failure"] = traceback.format_exc()
        raise
    finally:
        try:
            audit["package_after"] = package_hashes(package)
            require(before is not None and before == audit["package_after"], "Package identity changed or was not verified")
            audit["fixtures_after"] = {name: digest(repo / "windows/fixtures/qb004" / name) for name in FIXTURES}
            require(audit["fixtures_after"] == FIXTURES, "Original fixture identity changed")
        except Exception:
            audit["passed"] = False
            audit["identity_failure"] = traceback.format_exc()
        write_json(output / "audit.json", audit)
        write_json(output / "evidence-manifest.json", {path.relative_to(output).as_posix(): dict(bytes=path.stat().st_size, sha256=digest(path)) for path in sorted(output.rglob("*")) if path.is_file() and path.name != "evidence-manifest.json"})
    require(audit["passed"], "Matrix or identity verification failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--product-revision", required=True, help="Coordinator-verified 40-character product source revision; recorded, not inferred from executable")
    args = parser.parse_args()
    require(len(args.product_revision) == 40 and all(c in "0123456789abcdef" for c in args.product_revision), "Expected exact product revision")
    execute(args.package.resolve(), args.output.resolve(), Path(__file__).resolve().parent.parent, args.product_revision)
    print("PASS: four documents, 12 full-state checks, 24 captures; visual review remains required.")


if __name__ == "__main__":
    main()
