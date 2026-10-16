"""Exercise the worker process and JSON contract used by the Windows GUI."""
import json
import os
from pathlib import Path
import subprocess
import sys

worker = Path(sys.argv[1] if len(sys.argv) > 1 else "quantum-worker" + (".exe" if os.name == "nt" else "")).resolve()
checks = 0

def run(expression, *flags, success=True):
    global checks
    result = subprocess.run([str(worker), *flags], input=expression.encode("utf-8"), capture_output=True, timeout=30)
    assert (result.returncode == 0) == success, (expression[:100], result.returncode, result.stderr)
    checks += 1
    return result

def data(expression, *flags):
    result = run(expression, "--json", *flags)
    value = json.loads(result.stdout.decode("utf-8"))
    assert set(value) == {"text", "approximate", "rows", "columns", "cells", "probabilities", "bloch"}
    return value

for flags in [(), ("--approx",)]:
    for bare, grouped in [("|x>_N", "|x>_{N}"), ("<x|_N", "<x|_{N}"),
                          ("QFT_N|x>_N", "QFT_N|x>_{N}"),
                          ("|x>_N^2", "(|x>_{N})^2")]:
        assert data("quantum: " + bare, *flags) == data("quantum: " + grouped, *flags)

# Quantum amplitudes and error bounds remain symbolic even in approximate mode.
for flags in [(), ("--approx",)]:
    for command, letter in [("Sigma", "Σ"), ("Pi", "Π"), ("Gamma", "Γ"),
                            ("Delta", "Δ"), ("Omega", "Ω"), ("tau", "τ"),
                            ("xi", "ξ"), ("varpi", "ϖ"), ("varsigma", "ς")]:
        assert data("quantum: \\" + command, *flags) == data("quantum: " + letter, *flags)
    for letter in "αβγδεζηθικλμνξορστυφχψωΓΔΘΛΞΠΣΦΨΩ":
        result = data("quantum: " + letter, *flags)
        assert result["text"] == "'" + letter + "'" and not result["approximate"]
    state = data(r"quantum: \alpha|0>+\beta|1>", *flags)
    assert state["cells"] == [["'α'"], ["'β'"]]
    assert data(r"quantum: \ket{x}_\alpha", *flags) == data(r"quantum: |x>_{α}", *flags)
assert data("quantum: δ(1)")["text"] == "0"
assert data(r"quantum: \sum_{\alpha=0}^{1}{|\alpha>_2}")["cells"] == [["1"], ["1"]]
assert data(r"quantum: \sum_{\delta=0}^{2}{\delta^2}")["text"] == "5"
assert data(r"quantum: replace(\alpha,\alpha,1/2)")["text"] == "0.5"
assert data("α", "--approx")["approximate"]

assert data("quantum: alpha", "--approx")["approximate"]

for flags in [(), ("--approx",)]:
    for expression in [r"\cos^2(\pi\theta)", r"\sin^2(\pi\theta)",
                       r"\frac{1}{\sqrt{2}}|0>+\frac{e^{2\pi i\theta}}{\sqrt{2}}|1>"]:
        assert "θ" in data("quantum: " + expression, *flags)["text"]
    assert data(r"quantum: \ket{x}_\theta", *flags) == data(r"quantum: |x>_{θ}", *flags)
assert data("quantum: θ(1)")["text"] == "1"
assert data("quantum: θ(-1)")["text"] == "0"

for flags in [(), ("--approx",)]:
    symbolic = data(r"quantum: \sum_{k=0}^{N-1}{k}", *flags)
    assert "qsum(" in symbolic["text"] and "N" in symbolic["text"]
    assert data(r"quantum: replace(\sum_{k=0}^{N-1}{k},N,4)", *flags)["text"] == "6"
    assert data(r"quantum: replace(\sum_{k=0}^{N-1}{|k>_4},N,4)", *flags)["cells"] == [["1"], ["1"], ["1"], ["1"]]
for expression in [r"\sum_{k=0.5}^{N}{k}", r"\sum_{k=0}^{1.5}{k}", r"\sum_{k=2}^{1}{k}", "qsum(k,0,[1,2],k)"]:
    assert run("quantum: " + expression, "--json", success=False).stdout == b""

assert run("1+1").stdout.decode("utf-8").strip() == "2"
assert data("1+1")["text"] == "2"
assert data("sqrt(2)", "--approx")["approximate"] is True
matrix = data("[1,2;3,4]")
assert (matrix["rows"], matrix["columns"], matrix["cells"]) == (2, 2, [["1", "2"], ["3", "4"]])
large = data("identity(12)")
assert (large["rows"], large["columns"], large["cells"]) == (12, 12, [])
assert data("[1/4;3/4]", "--probabilities")["probabilities"] == [0.25, 0.75]
assert data("[1;1]", "--probabilities")["probabilities"] == []
assert data("[-1;2]", "--probabilities")["probabilities"] == []
assert data("[i;1]", "--probabilities")["probabilities"] == []
assert data("[0;0;1]", "--bloch")["bloch"] == [0, 0, 1]
assert data("[0;0;2]", "--bloch")["bloch"] == []
assert data("[i;0;0]", "--bloch")["bloch"] == []
assert data("1" + " " * 32767)["text"] == "1"
assert b"32768" in run("1" + " " * 32768, success=False).stderr
assert b"32768" in run("x" * 1000000, success=False).stderr
assert b"Usage:" in run("1", "--unknown", success=False).stderr
assert run("qmul([1,0;0,1],[1;2;3])", "--json", success=False).stdout == b""
def state_request(definitions, expression):
    # Each record has two decimal byte lengths, followed by the raw fields.
    value = "QSTATES1\n" + str(len(definitions)) + "\n"
    for name, definition in definitions:
        value += f"{len(name.encode('utf-8'))}\n{len(definition.encode('utf-8'))}\n{name}{definition}"
    return value + expression


definitions = [("Bell", "|Phi+>"), ("after CZ", "CZ|Bell>")]
for flags in [(), ("--approx",)]:
    for expression, expected in [("<Bell|Bell>", 1), ("<Bell|after CZ>", 0), ("<after CZ|after CZ>", 1)]:
        assert abs(float(data(state_request(definitions, "quantum:" + expression), "--states", *flags)["text"]) - expected) < 1e-12
assert data(state_request([("weighted", "2|0>")], "quantum:<weighted|weighted>"), "--states")["text"] == "4"
assert data(state_request([("symbolic", "[a;b]")], "quantum:|symbolic>"), "--states")["rows"] == 2
assert data(state_request([("état", "|1>")], "quantum:<état|état>"), "--states")["text"] == "1"
assert data(state_request([], "1+1"), "--states")["text"] == "2"
assert data(state_request([("Bell", "[1;\n0;0;1]/sqrt(2)")], "quantum:<Bell|Bell>"), "--states")["text"] == "1"
assert data(state_request([("Bell", "[1;\r\n0;0;1]/sqrt(2)")], "quantum:<Bell|Bell>"), "--states")["text"] == "1"
# Definitions belong to one request and never silently normalize a vector.
assert "qketstate" in data("quantum:|Bell>")["text"]
for invalid_definitions in [
    [("Bell", "|Phi+>"), ("Bell", "|0>")],
    [("after CZ", "CZ|Bell>"), ("Bell", "|Phi+>")],
    [("Bell", "|after CZ>"), ("after CZ", "|Bell>")],
    [("Bell", "|Bell>")], [("Bell", "|missing>")],
    [("Bell", "1")], [("Bell", "[1,0;0,1]")],
    [("Bell", "[infinity;0]")], [("Bell", "[undefined;0]")],
    [("0", "|1>")], [("Phi+", "|0>")], [("today", "|0>")],
    [(" Bell", "|0>")], [("Bell ", "|0>")], [("bad\nname", "|0>")],
    [("bad|name", "|0>")], [("bad\x00name", "|0>")],
    [("Bell", "|0>\x00ignored")],
    [("a" * 129, "|0>")], [("Bell", "x" * 32769)],
    [("state" + str(i), "|0>") for i in range(33)],
]:
    assert run(state_request(invalid_definitions, "1"), "--states", success=False).stdout == b""
for malformed in [
    "", "QSTATES2\n0\n1", "QSTATES1\n-1\n1", "QSTATES1\n0",
    "QSTATES1\n999999999999999999\n1", "QSTATES1\n1\n4\n8\nBell",
    "QSTATES1\n1\n0\n1\n01", "QSTATES1\n0\n",
    "QSTATES1\n0\n" + "x" * 32769, "x" * 1100001,
    "QSTATES1\n0\n1\x002",
]:
    assert run(malformed, "--states", success=False).stdout == b""
print(f"PASS: {checks} worker process checks")
