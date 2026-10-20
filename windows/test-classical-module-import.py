"""Verify unchanged QB-004 modules through the actual classical editor."""
import argparse
import hashlib
import json
import subprocess
import uuid
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--package", type=Path)
parser.add_argument("--output", type=Path)
args = parser.parse_args()
repo = Path(__file__).resolve().parent.parent
package = (args.package or repo / "dist/QuantumStudio").resolve()
output = (args.output or repo / "dist/classical-module-validation" / uuid.uuid4().hex).resolve()
assert not output.exists(), "Use a fresh output directory."
output.mkdir(parents=True)
app = package / "QuantumStudio.exe"
compiler = package / "qasm-import/qasm-import.exe"
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
hashes = {"gui": digest(app), "compiler": digest(compiler)}
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = 0
expected = {
    "oracle": [("CNOT", [0, 3]), ("CNOT", [1, 3]), ("CNOT", [2, 3])],
    "bernvaz": [("H", [0]), ("H", [1]), ("H", [2]), ("X", [3]),
                ("H", [3]), ("CNOT", [1, 3]), ("CNOT", [2, 3]),
                ("H", [0]), ("H", [1]), ("H", [2])],
}
results = []
for name, gates in expected.items():
    folder = output / (name + " Unicode κ")
    folder.mkdir()
    dependency = folder / (name + ".qasm")
    dependency.write_bytes((repo / "windows/fixtures/qb004" / dependency.name).read_bytes())
    entry = folder / "main κ.qasm"
    entry.write_text('OPENQASM 3.0; include "stdgates.inc"; '
                     f'include "{dependency.name}"; qubit[3] q; qubit[1] ancilla; '
                     f'{name}(q,ancilla);\n', encoding="utf-8-sig")
    source_bytes = {path.name: path.read_bytes() for path in (entry, dependency)}
    report = folder / "classical.txt"
    run = subprocess.run([str(app), "--classical-qasm-test", str(entry), str(report), "modules"],
                         capture_output=True, timeout=90, startupinfo=startup)
    assert run.returncode == 0 and report.exists(), (name, run.returncode, run.stderr)
    assert report.read_text(encoding="utf-8-sig").startswith("PASS:"), report.read_text(encoding="utf-8-sig")
    document = json.loads(Path(str(report) + ".source.qcircuit").read_text(encoding="utf-8-sig"))
    assert document["Format"] == "QuantumStudio.SourceCircuit" and document["Classical"]
    assert not document["PublishedU"]
    circuit = document["Circuit"]
    assert circuit["Qubits"] == 4 and circuit["Version"] == 2
    # The C# serializer emits null optional fields and canonicalizes CX to CNOT.
    steps = [{key: value for key, value in step.items() if value is not None}
             for step in circuit["Steps"]]
    assert steps == [dict(Kind="Gate", Expression=gate, Wires=wires) for gate, wires in gates]
    assert circuit["Registers"] == [] and circuit["OutputBits"] == []
    assert json.loads(Path(str(report) + ".qcircuit").read_text(encoding="utf-8-sig")) == circuit
    source = document["Source"]
    assert source["Entry"] == entry.name and source["ModuleHeaders"]
    files = {f["Name"]: f for f in source["Files"]}
    assert set(files) == set(source_bytes)
    for name_, raw in source_bytes.items():
        item = files[name_]
        assert (b"\xef\xbb\xbf" if item["Bom"] else b"") + item["Text"].encode("utf-8") == raw
        assert item["Sha256"] == hashlib.sha256(raw).hexdigest()
        assert (folder / name_).read_bytes() == raw
    screenshots = [Path(str(report) + suffix) for suffix in (".png", ".edited.png", ".minimum.png")]
    assert all(path.is_file() for path in screenshots)
    results.append(dict(name=name, passed=True, operations=len(gates), source_files=2,
                        screenshots=[dict(path=str(path), sha256=digest(path)) for path in screenshots]))
assert digest(app) == hashes["gui"] and digest(compiler) == hashes["compiler"]
(output / "audit.json").write_text(json.dumps(dict(
    passed=True, package=str(package), hashes=hashes, results=results,
    scope="Classical editor import, undo/redo, edits and save/reopen. No OpenQASM export or complete notebook claim."
), indent=2) + "\n", encoding="utf-8")
print("PASS: two frozen QB-004 classical editor imports, expected gates and retained source bytes.")
