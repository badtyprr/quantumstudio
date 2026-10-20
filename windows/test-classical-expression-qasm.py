"""Compile generated typed expressions and optionally verify exact/sample outcomes."""
import argparse, ast, json, os, subprocess
from pathlib import Path
from fractions import Fraction

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument("--cases", type=Path, required=True)
parser.add_argument("--compiler", type=Path, default=root/"dist/QuantumStudio/qasm-import/qasm-import.exe")
parser.add_argument("--worker", type=Path)
parser.add_argument("--expected-cases", type=int, default=39)
args = parser.parse_args()
cases = json.loads(args.cases.read_text(encoding="utf-8-sig"))
assert len(cases) == args.expected_cases and len({r["name"] for r in cases}) == args.expected_cases
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
    assert 2 <= circuit["Version"] <= 10
    if case.get("runtime_range", False):
        assert circuit["Version"] == 10 and any(s["Kind"] == "ForRange" for s in circuit["Steps"]), (case["name"], circuit)
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
        if circuit["Version"] >= 7:
            protocol = (b"QEXACT8\n" if exact else b"QSAMPLE9\n") if circuit["Version"] >= 9 else (b"QEXACT7\n" if exact else b"QSAMPLE8\n") if circuit["Version"] >= 8 else (b"QEXACT6\n" if exact else b"QSAMPLE7\n")
            assert circuit["LoopConditionBudget"] == 1000000
            declarations += n(32)
        if circuit["Version"] >= 10:
            protocol = b"QEXACT9\n" if exact else b"QSAMPLE10\n"
        outputs = circuit["OutputBits"]
        payload = protocol+n(circuit["Qubits"])+(b"" if exact else n(10000,1731))+n(sum(r["Size"] for r in circuit["Registers"]))+declarations+n(len(outputs),*outputs,len(circuit["Steps"]))+steps(circuit["Steps"])
        result = subprocess.run([str(worker), "--exact-circuit" if exact else "--sample"], input=payload, capture_output=True, timeout=30,
                                env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data")))
        if case.get("runtime_error", False):
            assert result.returncode != 0 and result.stderr and not result.stdout, (case["name"], result.stdout, result.stderr)
            assert b"Integer variable read before initialization" in result.stderr, (case["name"], result.stderr)
            checks += 1
            continue
        assert result.returncode == 0 and not result.stderr, (case["name"],result.stderr)
        value = json.loads(result.stdout)
        if exact:
            if case.get("approximate_probabilities", False):
                # The pinned compiler lowers gate angles numerically. Exact
                # execution can retain exponential expressions in probabilities.
                for key in set(value["probabilities"]) | {case["expected"]}:
                    expression = "abs((" + value["probabilities"].get(key, "0") + ")-" + ("1" if key == case["expected"] else "0") + ")"
                    evaluated = subprocess.run([str(worker), "--json", "--approx"], input=expression.encode("utf-8"), capture_output=True, timeout=30,
                                               env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data")))
                    assert evaluated.returncode == 0 and not evaluated.stderr, (case["name"], evaluated.stderr)
                    error = float(json.loads(evaluated.stdout)["copy_text"].replace("\u2212", "-"))
                    assert 0 <= error < 1e-10, (case["name"], key, error)
            else:
                assert {k:Fraction(v) for k,v in value["probabilities"].items()} == {case["expected"]:Fraction(1)}, (case["name"],value)
        else:
            assert value["counts"] == {case["expected"]:10000}, (case["name"],value)
        checks += 1
print("PASS: "+str(checks)+" typed OpenQASM expression checks.")
