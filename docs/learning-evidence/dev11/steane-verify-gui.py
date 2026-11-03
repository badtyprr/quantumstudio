"""Independently compare frozen compiler input/export and saved source bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--helper", type=Path, required=True)
parser.add_argument("--fixtures", type=Path, required=True)
parser.add_argument("--evidence", type=Path, required=True)
args = parser.parse_args()
results = []
for name in ("column-0", "column-1", "column-2", "column-3", "coherent-echo"):
    paths = [args.fixtures / (name + ".qasm"), args.evidence / (name + ".qasm")]
    circuits = []
    for index, path in enumerate(paths):
        run = subprocess.run([str(args.helper)], input=path.read_bytes(), capture_output=True, timeout=60)
        (args.evidence / (name + f".compiler-{index}.stdout")).write_bytes(run.stdout)
        (args.evidence / (name + f".compiler-{index}.stderr")).write_bytes(run.stderr)
        assert run.returncode == 0, run.stderr
        circuits.append(json.loads(run.stdout))
    original, exported = circuits
    assert original["Qubits"] == exported["Qubits"] == 14
    # Composer exports explicit zero initialization. Source/worker execution
    # also starts in zero; only these leading resets are removed for comparison.
    assert [s["Wires"] for s in exported["Steps"][:14]] == [[q] for q in range(14)]
    assert all(s["Gate"] == "Reset" for s in exported["Steps"][:14])
    normalize = lambda steps: [(s["Gate"], s["Wires"], s.get("Angle") or "") for s in steps]
    assert normalize(original["Steps"]) == normalize(exported["Steps"][14:])
    saved = json.loads((args.evidence / (name + ".qcircuit")).read_text(encoding="utf-8-sig"))
    assert saved["Format"] == "QuantumStudio.SourceCircuit" and not saved["Classical"]
    source_file = saved["Source"]["Files"][0]
    assert source_file["Text"].encode() == paths[0].read_bytes()
    assert source_file["Sha256"] == hashlib.sha256(paths[0].read_bytes()).hexdigest()
    results.append(dict(name=name, exact_gate_order=True, original_source_bytes=True,
                        saved_sha256=hashlib.sha256((args.evidence / (name + ".qcircuit")).read_bytes()).hexdigest()))
(args.evidence / "serialization-verification.json").write_text(json.dumps(dict(
    helper_sha256=hashlib.sha256(args.helper.read_bytes()).hexdigest(), results=results), indent=2))
print("PASS: five saved source documents and frozen reimports preserve full ordered circuits")
