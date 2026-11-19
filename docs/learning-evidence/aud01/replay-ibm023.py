"""Replay IBM-023. Pass the pinned notebook and the Windows GUI worker paths.

Requires SymPy 1.14.0. The worker inherits the installation's DLL and
definition paths. JSON on stdout records failures as well as successes.
"""
import ast
import contextlib
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys

import sympy


notebook, worker = map(Path, sys.argv[1:])
source = notebook.read_bytes()
digest = hashlib.sha256(source).hexdigest()
if digest != "cf02361b6238447bf11a13732a81dc0009c3522e4c5de3721235d0a55bcf2fe3":
    sys.exit("Unrecognized notebook revision")
if sympy.__version__ != "1.14.0":
    sys.exit("Replay requires SymPy 1.14.0")

records = []
namespace = {}


def calculate(cell, mode, expression, expected):
    row = dict(cell=cell, mode=mode, input=expression, expected=expected)
    try:
        process = subprocess.run([worker.resolve(), "--json"], capture_output=True,
                                 input=("quantum:" + expression).encode(), timeout=60)
    except subprocess.TimeoutExpired:
        row.update(actual="timeout after 60 seconds", passed=False)
    else:
        if process.returncode:
            row.update(actual=process.stderr.decode().strip(), passed=False)
        else:
            value = json.loads(process.stdout)
            row.update(actual=value["copy_text"], approximate=value["approximate"],
                       passed=value["copy_text"] == expected and not value["approximate"])
    records.append(row)


math_expected = {"N": "'N'", "M": "'M'", r"N\geq 2": "('N')>=(2)",
                 r"12 = 2^2 \cdot 3": "1", **{n: n for n in ("1", "2", "3", "12")}}
for cell in json.loads(source)["cells"]:
    body = "".join(cell["source"])
    cell_id = cell["id"]
    if cell["cell_type"] == "markdown":
        for index, match in enumerate(re.finditer(r"\$\$.*?\$\$|\$[^$]+?\$", body, re.S), 1):
            text = match.group()
            calculate(f"{cell_id}-M{index:02}", "literal", text, math_expected[text.strip("$").strip()])
        continue
    assert cell["cell_type"] == "code"
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        exec(compile(body, f"IBM023-{cell_id}", "exec"), namespace)
    expected = "".join("".join(out["text"]) for out in cell["outputs"])
    actual = stdout.getvalue()
    if cell_id in ("9caf4516", "53f998fc"):
        passed = ast.literal_eval(actual) == ast.literal_eval(expected)
    else:
        passed = actual == expected
    records.append(dict(cell=cell_id, mode="Python", input=body, expected=expected,
                        actual=actual, passed=passed))
    if cell_id in ("9caf4516", "53f998fc"):
        factors = sorted(ast.literal_eval(expected).items())
        values = ",".join(str(n) for pair in factors for n in pair)
        calculate(cell_id, "adapted", f"factor({namespace['N']},2)", f"matrix({len(factors)},2,[{values}])")
    elif cell_id == "ae7a86db":
        calculate(cell_id, "adapted", str(namespace["RSA1024"]), expected.strip())
    elif cell_id == "c3c41fb4":
        calculate(cell_id, "adapted", f"{namespace['RSA250']}={namespace['p']}*{namespace['q']}", "1")
    elif cell_id == "9272ac2b":
        calculate(cell_id, "adapted", f"gcd({namespace['N']},{namespace['M']})", expected.strip())

print(json.dumps(dict(notebook_sha256=digest, worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
                      python=sys.version.split()[0], sympy=sympy.__version__, records=records), indent=2))
sys.exit(any(not row["passed"] for row in records))
