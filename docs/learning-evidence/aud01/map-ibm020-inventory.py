"""Map the published IBM-020 inventory to a second, hash-pinned notebook.

Run with the historical and current notebook paths in that order.
The historical inventory commit must be available in this checkout.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
REVISION = "50034c421f0ffbbabaa4f3dec15ba78e468c53b1"
DIRECTORY = "docs/learning-evidence/aud01-ibm020-audit"
MATH = re.compile(r"(?<!\\)(\$\$|\$).*?(?<!\\)\1", re.DOTALL)


def inventory(name):
    data = subprocess.check_output(
        ["git", "show", f"{REVISION}:{DIRECTORY}/{name}.json"], cwd=HERE
    )
    return json.loads(data)


def load_cells(path, expected_hash):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_hash:
        raise ValueError(f"Unexpected notebook hash for {path}")
    return json.loads(data)["cells"]


def map_cells(old, new, records):
    cells = []
    for index, current in enumerate(new):
        previous = old[index]
        if (current["id"], current["cell_type"]) != (previous["id"], previous["cell_type"]):
            raise ValueError(f"Cell identity changed at {index}")
        before, after = ("".join(cell["source"]) for cell in (previous, current))
        row = {"index": index, "id": current["id"], "type": current["cell_type"]}
        if current["cell_type"] == "code":
            if before != after:
                raise ValueError(f"Code changed in cell {index}")
            row["source_sha256"] = hashlib.sha256(after.encode()).hexdigest()
        else:
            matches = list(MATH.finditer(after))
            ordered = sorted(records[index], key=lambda item: item[0])
            if len(ordered) != len(matches):
                raise ValueError(f"Formula count changed in cell {index}")
            row["formulas"] = []
            for (offset, record), match in zip(ordered, matches):
                literal = match.group()
                if (record["original"] != literal
                        or before[offset:offset + len(literal)] != literal
                        or hashlib.sha256(literal.encode()).hexdigest() != record["sha256"]):
                    raise ValueError(f"Formula changed at {record['id']}")
                row["formulas"].append([record["id"], match.start(), match.end()])
        cells.append(row)
    return cells


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("historical", type=Path)
    parser.add_argument("current", type=Path)
    args = parser.parse_args()
    original = inventory("inventory")
    current_receipt = json.loads((HERE / "ibm020-query-algorithms.json").read_bytes())
    old = load_cells(args.historical, original["source_sha256"])
    new = load_cells(args.current, current_receipt["sha256"])
    if len(old) != len(new) + 1 or old[-1]["id"] != "a1b8767d":
        raise ValueError("Unexpected change to notebook structure")
    records = defaultdict(list)
    for item in original["occurrences"]:
        records[item["cell_index"]].append((item["cell_offset"], item))
    for item in inventory("remainder-inventory")["records"]:
        if item["kind"] in ("inline_math", "display_math"):
            records[item["cell_index"]].append((item["offset"], item))
    cells = map_cells(old, new, records)
    result = dict(inventory_revision=REVISION, historical_sha256=original["source_sha256"],
                  current_sha256=current_receipt["sha256"], removed_cell=old[-1]["id"],
                  formula_fields=["historical_id", "start_code_point", "end_exclusive"],
                  cells=cells)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
