"""Compile generated typed expressions and optionally verify exact/sample outcomes."""
import argparse, ast, json, os, subprocess
from pathlib import Path
from fractions import Fraction

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument("--cases", type=Path, required=True)
parser.add_argument("--compiler", type=Path, default=root/"dist/QuantumStudio/qasm-import/qasm-import.exe")
parser.add_argument("--worker", type=Path)
args = parser.parse_args()
cases = json.loads(args.cases.read_text(encoding="utf-8-sig"))
assert len(cases) == 39 and len({r["name"] for r in cases}) == 39
# Share the existing test protocol encoders without executing its independent suite.
tree = ast.parse((root/"windows/test-qasm-classical-expressions.py").read_text(encoding="utf-8"))
nodes = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in ("n", "expression", "integer_expression", "steps"))
         or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "ops" for t in n.targets))]
assert len(nodes) == 5
namespace = {}
exec(compile(ast.Module(body=nodes, type_ignores=[]), "existing-test-protocol", "exec"), namespace)
n, steps = namespace["n"], namespace["steps"]
checks = 0
for case in cases:
    run = subprocess.run([str(args.compiler.resolve()), "--classical"], input=case["source"].encode(), capture_output=True, timeout=30)
    assert run.returncode == 0, (case["name"], run.stderr.decode("utf-8",errors="replace"), case["source"])
    circuit = json.loads(run.stdout)
    assert 2 <= circuit["Version"] <= 6
    assert len(circuit["OutputBits"]) == len(case["expected"])
    checks += 1
    if args.worker is None:
        continue
    worker = args.worker.resolve()
    for exact in (True, False):
        protocol = (b"QEXACT3\n" if exact else b"QSAMPLE4\n") if circuit["Version"] == 4 else (b"QEXACT2\n" if exact else b"QSAMPLE3\n")
        declarations = b""
        if circuit["Version"] >= 5:
            protocol = (b"QEXACT5\n" if exact else b"QSAMPLE6\n") if circuit["Version"] == 6 else (b"QEXACT4\n" if exact else b"QSAMPLE5\n")
            declarations = n(len(circuit["Variables"])) + b"".join(n(0 if v["Signedness"] == "Signed" else 1,v["Width"]) for v in circuit["Variables"])
        outputs = circuit["OutputBits"]
        payload = protocol+n(circuit["Qubits"])+(b"" if exact else n(10000,1731))+n(sum(r["Size"] for r in circuit["Registers"]))+declarations+n(len(outputs),*outputs,len(circuit["Steps"]))+steps(circuit["Steps"])
        result = subprocess.run([str(worker), "--exact-circuit" if exact else "--sample"], input=payload, capture_output=True, timeout=30,
                                env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data")))
        assert result.returncode == 0 and not result.stderr, (case["name"],result.stderr)
        value = json.loads(result.stdout)
        if exact:
            assert {k:Fraction(v) for k,v in value["probabilities"].items()} == {case["expected"]:Fraction(1)}, (case["name"],value)
        else:
            assert value["counts"] == {case["expected"]:10000}, (case["name"],value)
        checks += 1
print("PASS: "+str(checks)+" typed OpenQASM expression checks.")
