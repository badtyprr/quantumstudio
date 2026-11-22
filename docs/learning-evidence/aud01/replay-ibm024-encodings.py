"""Replay the two encoding tables in IBM-024. Pass the worker and pinned notebook."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

worker = Path(sys.argv[1]).resolve()
notebook = Path(sys.argv[2]).read_bytes()
baseline = json.loads(Path(__file__).with_name("ibm024-cost-baseline.json").read_bytes())
assert hashlib.sha256(notebook).hexdigest() == baseline["source_sha256"]
lines = [line for cell in json.loads(notebook)["cells"] for line in "".join(cell["source"]).splitlines()]


def table(header):
    start = lines.index(header) + 2
    result = []
    for line in lines[start:]:
        if not line.startswith("|"):
            break
        result.append([item.strip() for item in line.strip("|").split("|")])
    assert len(result) == 9
    return result


def evaluate(expression):
    result = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                            capture_output=True, timeout=15, check=True)
    value = json.loads(result.stdout)
    assert not value["approximate"]
    return value["copy_text"]


def verify_word(bits):
    copy = evaluate(f'bitstring("{bits}")')
    assert copy == f"qbitlabel({int(bits or '0', 2)},{len(bits)})"
    assert evaluate(copy) == copy


for n, (number, binary, length) in enumerate(table("| Number | Binary encoding | Length |")):
    assert int(number) == n and binary == format(n, "b")
    assert int(length) == len(binary) and evaluate(rf"$\operatorname{{lg}}({n})$") == length
    verify_word(binary)

for n, (number, unary, lexicographic) in enumerate(table("| Number | Unary encoding | Lexicographic encoding |")):
    assert int(number) == n
    for text, expected in ((unary, "0" * n), (lexicographic, format(n + 1, "b")[1:])):
        copy = evaluate("bitword:" + text)
        assert copy == f"qbitlabel({int(expected or '0', 2)},{len(expected)})"
        assert evaluate(copy) == copy
        verify_word(expected)

print("Verified all 18 table rows, including binary lengths, leading zeros, the empty string and copy/re-entry.")
