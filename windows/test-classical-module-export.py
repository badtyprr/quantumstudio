"""Export unchanged qBraid modules through the editor with observable oracles."""
import argparse
import hashlib
import json
import subprocess
import sys
import uuid
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--package", type=Path)
parser.add_argument("--output", type=Path)
parser.add_argument("--worker", type=Path)
args = parser.parse_args()
repo = Path(__file__).resolve().parent.parent
package = (args.package or repo / "dist/QuantumStudio").resolve()
output = (args.output or repo / "dist/classical-module-export" / uuid.uuid4().hex).resolve()
assert not output.exists(), "Use a fresh audit directory."
output.mkdir(parents=True)
app = package / "QuantumStudio.exe"
compiler = package / "qasm-import/qasm-import.exe"
worker = args.worker or (package / "quantum-worker.exe" if (package / "quantum-worker.exe").exists() else None)
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
hashes = {"gui": digest(app), "compiler": digest(compiler)}
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = 0
cases, results = [], []
# Basis probes distinguish each of the oracle's three controls. The algorithm
# probe observes its secret; the extra case checks early termination separately.
for name, value, early in [
    ("oracle", 0, False), ("oracle", 1, False),
    ("oracle", 2, False), ("oracle", 4, False),
    ("bernvaz", 0, False), ("oracle", 1, True),
]:
    label = f"{name}-{value}" + ("-end" if early else "")
    folder = output / (label + " Unicode κ")
    modules = folder / "nested modules"
    modules.mkdir(parents=True)
    dependency = modules / (name + ".qasm")
    dependency.write_bytes((repo / "windows/fixtures/qb004" / dependency.name).read_bytes())
    wrapper = folder / "wrapper.qasm"
    wrapper.write_text(f'include "nested modules/{name}.qasm";\n', encoding="utf-8")
    entry = folder / "main κ.qasm"
    prepare = "".join(f"x q[{bit}]; " for bit in range(3) if value & (1 << bit))
    # Only declared outputs are observed. Assign ancilla/q2/q1/q0 to
    # increasing indices; OpenQASM register output is high-to-low, so the
    # expected display string below reverses that assignment order.
    # BV leaves its ancilla in |->, so observe only its deterministic secret.
    observations = ("output bit[3] result; result[0]=measure q[2]; "
                    "result[1]=measure q[1]; result[2]=measure q[0];"
                    if name == "bernvaz" else
                    "output bit[4] result; result[0]=measure ancilla[0]; "
                    "result[1]=measure q[2]; result[2]=measure q[1]; result[3]=measure q[0];")
    source = ('OPENQASM 3; include "stdgates.inc"; include "wrapper.qasm"; '
              'qubit[3] q; qubit[1] ancilla; bit scratch; '
              + prepare + f"{name}(q,ancilla); " + observations)
    if early:
        source += " end; result=0;"
    entry.write_text(source + "\n", encoding="utf-8-sig")
    originals = {path: path.read_bytes() for path in (entry, wrapper, dependency)}
    report = folder / "export"
    run = subprocess.run([str(app), "--classical-export-test", str(entry), str(report), "modules"],
                         capture_output=True, timeout=120, startupinfo=startup)
    assert run.returncode == 0 and report.exists(), (label, run.returncode, run.stderr)
    assert report.read_text(encoding="utf-8").startswith("PASS:"), report.read_text(encoding="utf-8")
    document = json.loads(Path(str(report) + ".qcircuit").read_text(encoding="utf-8-sig"))
    assert document["Source"]["ModuleHeaders"] and document["Classical"]
    captured = {row["Name"]: row for row in document["Source"]["Files"]}
    assert len(captured) == 3
    for path, raw in originals.items():
        assert path.read_bytes() == raw
        item = captured[path.relative_to(folder).as_posix()]
        assert (b"\xef\xbb\xbf" if item["Bom"] else b"") + item["Text"].encode("utf-8") == raw
        assert item["Sha256"] == hashlib.sha256(raw).hexdigest()
    for edited, suffix in ((False, ".original.qasm"), (True, ".qasm")):
        # The GUI hook prepends X(q0). For a basis oracle this toggles input
        # bit zero and parity; for BV it toggles secret bit zero.
        prepared = value ^ int(edited)
        expected = (f"{6 ^ int(edited):03b}" if name == "bernvaz" else
                    str(prepared.bit_count() % 2) + f"{prepared:03b}")
        cases.append(dict(name=label + ("-edited" if edited else "-original"),
                          source=Path(str(report) + suffix).read_text(encoding="utf-8"),
                          expected=expected[::-1]))
    screenshots = [Path(str(report) + suffix) for suffix in (".png", ".rejected.png", ".minimum.png")]
    assert all(path.is_file() for path in screenshots)
    results.append(dict(name=label, screenshots={str(path): digest(path) for path in screenshots}))
case_path = output / "cases.json"
case_path.write_text(json.dumps(cases, indent=2) + "\n", encoding="utf-8")
command = [sys.executable, str(repo / "windows/test-classical-expression-qasm.py"),
           "--cases", str(case_path), "--compiler", str(compiler), "--expected-cases", "12"]
if worker:
    command.extend(["--worker", str(worker.resolve())])
subprocess.run(command, check=True, timeout=180)
assert hashes == {"gui": digest(app), "compiler": digest(compiler)}
(output / "audit.json").write_text(json.dumps(dict(
    passed=True, hashes=hashes, results=results, cases=12,
    semantic_checks=24 if worker else 0, worker_sha256=digest(worker) if worker else None,
    scope="Unchanged QB-004 module export with basis/algorithm probes, edits, selected outputs and early end; not complete notebooks."
), indent=2) + "\n", encoding="utf-8")
print("PASS: six module GUI exports and twelve compiler round trips; "
      + ("24 exact/sample checks." if worker else "worker semantics not run."))
