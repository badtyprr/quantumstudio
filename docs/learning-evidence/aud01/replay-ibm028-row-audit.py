"""Index the IBM-028 notebook, Windows replay and independently rerun value checks."""
import argparse
import hashlib
import json
from pathlib import Path


def load(path):
    return json.loads(path.read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


parser = argparse.ArgumentParser()
parser.add_argument("notebook", type=Path)
parser.add_argument("windows_records", type=Path)
parser.add_argument("suite_directory", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
directory = Path(__file__).parent
inventory = load(directory / "ibm028-inventory.json")
windows = load(directory / "ibm028-windows-replay.json")
assert digest(args.notebook) == inventory["source_sha256"] == windows["notebook_sha256"]
assert digest(args.windows_records) == windows["records_sha256"]
notebook = load(args.notebook)
assert all(c["cell_type"] == "markdown" for c in notebook["cells"])
records = {r["id"]: r for r in load(args.windows_records)}

# Suites here verify particular expectations in their source-specific cases.
suites = {
    "bit-fraction": [39], "bit-word": [103], "two-bit-arithmetic": [105],
    "fourier-basis": [118,119,123,128,130,133],
    "fourier-names": [128,130,132,133,187,188,189,190,191,217,219],
    "fraction-digits": [111,112,113,114], "geometric-series": [201,329],
    "ket-families": [214], "ket-lists": [127,134,135,179],
    "kickback-states": [14,15,17,21,22], "open-bits": [74,76],
    "orthogonality": [215], "phase-probability": [328],
    "rounded-values": [176,358], "signed-endpoints": [337,338,339,341,342],
    "state-action": [224],
}
suite_hashes = {}
links = {row["id"]: [] for row in inventory["rows"]}
for name in [*suites, "copy-meaning", "figures", "probability-plots"]:
    path = args.suite_directory / (name + ".json")
    batch = load(path)
    suite_hashes[name] = digest(path)
    if isinstance(batch, dict):
        assert batch["worker_sha256"] == windows["worker_sha256"], name
    if name in suites:
        for number in suites[name]:
            links[inventory["rows"][number-1]["id"]].append(name)

meaning = load(args.suite_directory / "copy-meaning.json")
for key in (*meaning["checks"], *meaning["structured"]):
    links[key].append("copy-meaning")
for group in meaning["repeated_expressions"].values():
    for key in group["rows"]:
        links[key].append("copy-meaning")
rows = []
for n, item in enumerate(inventory["rows"], 1):
    key = item["id"]
    src = "".join(notebook["cells"][item["cell"]]["source"])
    assert src[item["start"]:item["end"]] == item["literal"], key
    raw = records[key]
    result = records[key + "-dimension4"] if n == 119 else raw
    assert result["restored_same"] and result["label"] == result["reentry_label"] == "EXACT RESULT", key
    row = dict(id=key, cell=item["cell"], start=item["start"], end=item["end"], input=item["literal"],
               display=result["display"], copy=result["copy"], evidence=links[key])
    if result["second_copy"] != result["copy"]:
        row["copy_after_reentry"] = result["second_copy"]
    if n == 119:
        row["original_diagnostic"] = raw["display"]
        row["adapted_input"] = load(directory / "ibm028-fourier-basis.json")["m119_input"]
    if n == 123:
        row["declaration"] = "V is a 4 by 4 unitary"
    if str(n) in windows["modes"]:
        row["windows_mode"] = windows["modes"][str(n)]
    if n == 279:
        row["value_check_context"] = "Supply the dimension 4 to the resulting basis index for a two-qubit example."
    if n in (125,178):
        axis = "4" if n == 125 else "N"
        expected = f"{axis} × {axis}"
        copy_axis = "4" if n == 125 else "'N'"
        assert result["display"] == expected
        assert result["copy"] == result["second_copy"] == f"qmatrixdimensions({copy_axis},{copy_axis})"
        row["expected"] = expected
        links[key].append("row-audit")
    assert row["evidence"], key
    rows.append(row)
figures = load(args.suite_directory / "figures.json")["figures"] + load(args.suite_directory / "probability-plots.json")
expected_files = {Path(entry["path"]).name for entry in inventory["figures"]}
assert len(figures) == len(expected_files) == 17 and {entry["file"] for entry in figures} == expected_files
report = dict(source=inventory["source"], notebook_sha256=inventory["source_sha256"],
              worker_sha256=windows["worker_sha256"], windows_records_sha256=windows["records_sha256"],
              suites_sha256=suite_hashes, figures=sorted(expected_files), rows=rows)
args.output.write_bytes((json.dumps(report, indent=2, ensure_ascii=False)+"\n").encode())
