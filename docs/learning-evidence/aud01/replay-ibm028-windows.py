"""Prepare the Windows replay, or validate its saved sessions and report every Copy change."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("gui_directory", type=Path)
parser.add_argument("--package", type=Path)
parser.add_argument("--report", type=Path)
args = parser.parse_args()
directory = args.gui_directory
evidence = Path(__file__).parent
inventory = json.loads((evidence / "ibm028-inventory.json").read_bytes())
annotated = json.loads((evidence / "ibm028-fourier-basis.json").read_bytes())["m119_input"]
modes = {74: 4, 76: 4, 103: 5, 111: 4, 112: 4, 113: 4, 114: 4, 125: 3, 178: 3}
inputs = []
for number, row in enumerate(inventory["rows"], 1):
    assert row["id"].endswith(f"M{number:03d}")
    inputs.append([row["id"], row["literal"], str(modes.get(number, 0))])
    if number == 119:
        inputs.append([row["id"] + "-dimension4", annotated, "0"])

if not args.report:
    directory.mkdir(exist_ok=True, parents=True)
    (directory / "inputs.json").write_bytes(json.dumps(inputs, ensure_ascii=False).encode())
    raise SystemExit(0)

assert args.package and json.loads((directory / "inputs.json").read_bytes()) == inputs
suite = json.loads((directory / "result.json").read_bytes())
records = json.loads((directory / "records.json").read_bytes())
assert suite["passed"] and suite["clipboardRestored"] and suite["calls"] == len(records) == len(inputs) == 397
changes = []
diagnostics = []
for (key, expression, mode), row in zip(inputs, records):
    assert row["id"] == key
    if key.endswith("-M119"):
        assert row["label"] == "CHECK YOUR EXPRESSION" and "dimension" in row["display"].lower()
        diagnostics.append(dict(id=key, message=row["display"]))
        continue
    assert row["label"] == row["reentry_label"] == "EXACT RESULT" and row["restored_same"], key
    session = json.loads((directory / (key + ".qsession")).read_bytes().decode("utf-8-sig"))
    assert session["Expression"] == expression and session["Mode"] == int(mode), key
    matrices = [dict(Name="V", Rows="4", Columns="4", Property="Unitary")] if key.endswith("-M123") else []
    assert session["Matrices"] == matrices, key
    if row["copy"] != row["second_copy"]:
        changes.append(dict(id=key, first_copy=row["copy"], second_copy=row["second_copy"]))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


report = dict(source=inventory["source"], notebook_sha256=inventory["source_sha256"],
              worker_sha256=digest(args.package / "quantum-worker.exe"),
              application_sha256=digest(args.package / "QuantumStudio.exe"),
              records_sha256=digest(directory / "records.json"), suite=suite,
              source_expressions=len(inventory["rows"]), original_exact=395,
              adjusted_dimension_cases=1, restored_exact=396, exact_after_reentry=396,
              stable_copy_text=396-len(changes), modes=modes,
              original_diagnostics=diagnostics, changed_copy_text=changes)
args.report.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode())
