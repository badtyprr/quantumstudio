"""Check the two signed endpoints in IBM-028 and the precedence of adjacent terms."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
source = json.loads(Path(__file__).with_name("ibm028-inventory.json").read_bytes())
row = source["rows"][338]
assert row["id"].endswith("M339")


def run(text):
    return subprocess.run([worker, "--json"], input=("quantum:" + text).encode(),
                          env=env, capture_output=True, timeout=30)


def evaluate(text):
    result = run(text)
    assert result.returncode == 0, (text, result.stderr.decode())
    data = json.loads(result.stdout)
    assert not data["approximate"], data
    return data


original = evaluate(row["literal"])
gui = [["M339", row["literal"], "0"]]
cases = {"-1/2": "1", "1/2": "1", "0": "0", "1/4": "0", "-1": "0", "1": "0"}
for form in ["display_text", "copy_text"]:
    assert evaluate(original[form])["copy_text"] == original["copy_text"]
    for i, (candidate, expected) in enumerate(cases.items()):
        expression = f"replace(({original[form]}),δ,({candidate}))"
        assert evaluate(expression)["copy_text"] == expected, expression
        if form == "display_text":
            gui.append([f"M339-{i}-{expected}", expression, "0"])

# A trailing translation shifts both endpoints. Parentheses change the magnitude.
for rhs, endpoints in [("±2*3+1", {-5, 7}), ("1±2*3-4", {-9, 3}),
                       ("1±(2*3-4)", {-1, 3}), ("2±0", {2}), ("±(-2)", {-2, 2})]:
    for candidate in range(-10, 11):
        assert evaluate(f"{candidate}={rhs}")["copy_text"] == str(int(candidate in endpoints)), (candidate, rhs)
for invalid in ["x < ±1", "x = ±", "0=x=±1", "x=±1<3", "x=±1±2"]:
    assert run(invalid).returncode != 0, invalid

# The interval in M337 includes the interior. M339 identifies just its endpoints.
# The arc/chord quotient in M341 is undefined at zero.
geometry = {}
for number in (337, 338, 341, 342):
    item = source["rows"][number - 1]
    rec = evaluate(item["literal"])
    results = {}
    for value in ("-3/4", "-1/2", "-1/4", "0", "1/4", "1/2", "3/4"):
        if number == 341 and value == "0":
            continue
        outside = value in ("-3/4", "3/4")
        expected = "0" if outside and number != 338 else "1"
        for name in ("copy_text", "display_text"):
            test = f"replace(({rec[name]}),δ,({value}))"
            assert evaluate(test)["copy_text"] == expected, (number, value, name)
        if number == 337:
            gui.append([f"M337-{len(results)}-{expected}", test, "0"])
        results[value] = expected
    geometry[item["id"]] = dict(display=rec["display_text"], copy=rec["copy_text"], results=results)
    if number == 337:
        gui.append(["M337", item["literal"], "0"])
        assert evaluate(rec["display_text"])["copy_text"] == rec["copy_text"]

for bounds, expected in [("[0,1]", "111"), ("(0,1)", "010"), ("[0,1)", "110"), ("(0,1]", "011")]:
    for index, value in enumerate(("0", "1/2", "1")):
        assert evaluate(f"{value} ∈ {bounds}")["copy_text"] == expected[index]
        assert evaluate(f"{value} ∉ {bounds}")["copy_text"] == str(1 - int(expected[index]))
for value in ("-1/2", "1/2"):
    assert evaluate(f"(2*pi*abs({value}))/abs(exp(2*pi*i*({value}))-1)=pi/2")["copy_text"] == "1"

report = dict(source=source["source"], id=row["id"], literal=row["literal"],
              worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              display=original["display_text"], copy=original["copy_text"], candidates=cases, geometry=geometry)
args.output.write_bytes((json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode())
if args.gui_inputs:
    args.gui_inputs.write_bytes(json.dumps(gui, ensure_ascii=False).encode())
