"""Actual worker copy/reentry for bounded indexed scalar products."""
import json
import base64
import os
from pathlib import Path
import subprocess
import sys

worker = Path(sys.argv[1] if len(sys.argv) > 1 else "quantum-worker" + (".exe" if os.name == "nt" else "")).resolve()
records = []
output = Path(os.environ["SCALAR_PRODUCT_RESULTS"]) if "SCALAR_PRODUCT_RESULTS" in os.environ else None
source = r"x_{n-1}y_{n-1} + \cdots + x_0 y_0"


def run(expression, success=True, expected_stderr=""):
    record = dict(input=expression, status="started", returncode=None)
    records.append(record)

    def persist(stdout=b"", stderr=b""):
        record.update(stdout=stdout.decode("utf-8", errors="replace"),
                      stderr=stderr.decode("utf-8", errors="replace"),
                      stdout_base64=base64.b64encode(stdout).decode("ascii"),
                      stderr_base64=base64.b64encode(stderr).decode("ascii"))
        if output:
            output.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")

    persist()
    try:
        result = subprocess.run([str(worker), "--json"], input=expression.encode("utf-8"), capture_output=True, timeout=10)
    except subprocess.TimeoutExpired as error:
        record.update(status="timeout", timeout_seconds=error.timeout)
        persist(error.stdout or b"", error.stderr or b"")
        raise
    except OSError as error:
        record.update(status="launch_error", error=str(error))
        persist()
        raise
    record.update(status="completed", returncode=result.returncode)
    persist(result.stdout, result.stderr)
    if (result.returncode == 0) != success or (not success and (result.returncode != 2 or result.stdout or not result.stderr)):
        raise RuntimeError(f"Unexpected worker outcome: {record}")
    if success and record["stderr"].replace("\r\n", "\n") != expected_stderr:
        raise RuntimeError(f"Unexpected worker diagnostics: {record}")
    if not success:
        return None
    response = json.loads(result.stdout)
    if set(response) != {"text", "display_text", "copy_text", "approximate", "rows", "columns", "cells", "probabilities", "bloch"}:
        raise RuntimeError(f"Unexpected worker response fields: {response}")
    if response["rows"] or response["columns"] or response["cells"] or response["probabilities"] or response["bloch"] or response["approximate"]:
        raise RuntimeError(f"Scalar expression returned a non-exact or nonscalar response: {response}")
    return response


def value(expression, expected, expected_stderr=""):
    actual = run(expression, expected_stderr=expected_stderr)
    if actual["copy_text"] != expected:
        raise RuntimeError(f"Expected {expected}, got {actual}: {expression}")
    return actual


def copied(expression):
    original = run(expression)
    # Deliberately use the actual copy text with no quantum prefix. The
    # expected canonical string is never substituted for the worker's output.
    ordinary = run(original["copy_text"])
    quantum = run("quantum:" + ordinary["copy_text"])
    if ordinary["copy_text"] != original["copy_text"] or quantum["copy_text"] != ordinary["copy_text"]:
        raise RuntimeError(f"Copy changed meaning or canonical form: {original}, {ordinary}, {quantum}")
    return quantum["copy_text"]


symbolic = copied("quantum:" + source)
value("quantum:replace(" + symbolic + ",vector(n,x_0,x_1,y_0,y_1),vector(2,1,1,1,1))", "2")
value("quantum:replace(" + symbolic + ',vector("n","x_0","x_1","y_0","y_1"),vector(2,1,1,1,1))', "2")
value("quantum:bitdot(bitstring(3,2),bitstring(3,2))", "0")
# The n=1 iteration intentionally receives assignments for excluded index 1.
value("quantum:sum(replace(" + symbolic + ",vector(x_0,x_1,y_0,y_1),vector(1,1,1,1)),1,2,n)", "3",
      "Original value was not found during quantum substitution.\n")
value('quantum:sum(qscalarproductsum("x_","x_",1,vector(1,0,3)),0,1,"x_0")', "18")
value('quantum:sum(qscalarproductsum("x_",\'x_\',1,vector(1,0,3)),0,1,"x_0")', "18")
value('quantum:sum(qscalarproductsum("x_","x_",1,vector((1),(0),3)),0,1,"x_0")', "18")

# Copy every partially supplied state, in both width-first and width-last
# order. This exposes dropped early bindings and metadata serialization bugs.
for assignments in (
    [("n", "2"), ("x_0", "1"), ("x_1", "1"), ("y_0", "1"), ("y_1", "1")],
    [("x_0", "1"), ("x_1", "1"), ("y_0", "1"), ("y_1", "1"), ("n", "2")],
):
    state = symbolic
    for name, replacement in assignments:
        state = copied(f"quantum:replace({state},{name},{replacement})")
    if state != "2":
        raise RuntimeError(f"Partial-copy assignment sequence returned {state}")

value(r'quantum:replace(u_{m-1}v_{m-1}+\cdots+u_0 v_0,vector(m,u_0,v_0),vector(1,3,4))', "12")
value(r'quantum:replace(u_{i-1}v_{i-1}+\cdots+u_0 v_0,vector("i",u_0,v_0),vector(1,3,4))', "12")
value(r'quantum:sum(replace(x_0 y_0+\cdots+x_0 y_0,y_0,1),0,1,"x_0")', "1")
for bad in ("0", "-1", "1/2", "1025"):
    run(f"quantum:replace({symbolic},n,{bad})", success=False)
for bad in ("[1;2]", "interval(0,1)", "infinity"):
    run(f"quantum:replace({symbolic},x_0,{bad})", success=False)
run(f'qreplace({symbolic},"x_0",2*m)', success=False)
# Quantum notation treats m as a free scalar name; ordinary syntax treats m
# as a unit. Keep both domains explicit instead of conflating their spellings.
pending = copied(f"quantum:replace({symbolic},x_0,2*m)")
value(f"quantum:replace({pending},vector(m,n,y_0),vector(3,1,1))", "6")

print(f"PASS: {len(records)} scalar-product worker calls")
