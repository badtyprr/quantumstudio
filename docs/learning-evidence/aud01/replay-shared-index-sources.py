"""Replay classified formula occurrences from a pinned Qiskit documentation checkout."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source_root", type=Path, help="Directory containing the learning tree")
parser.add_argument("worker", type=Path)
parser.add_argument("--baseline", action="store_true", help="Expect the baseline diagnostic named by the manifest")
parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name("shared-index-sources.json"))
args = parser.parse_args()
worker = args.worker.resolve()
env = os.environ.copy()
if (worker.parent / "data").is_dir():
    env.setdefault("QALCULATE_DEFINITIONS_DIR", str(worker.parent / "data"))
manifest = json.loads(args.manifest.read_bytes())
previous_diagnostic = manifest.get("previous_diagnostic", "Invalid summation index").encode()
counts = Counter()
cache = {}
for lesson in manifest["lessons"]:
    data = (args.source_root / lesson["source"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != lesson["source_sha256"]:
        raise ValueError(f"Wrong source for {lesson['lesson']}. Use revision {manifest['revision']}.")
    cells = json.loads(data)["cells"]
    for row in lesson["occurrences"]:
        source = "".join(cells[row["cell"]]["source"])
        literal = source[row["start"]:row["end"]].encode()
        if hashlib.sha256(literal).hexdigest() != row["literal_sha256"]:
            raise ValueError(f"Source occurrence moved in {lesson['lesson']} at {row['start']}")
        if literal not in cache:
            result = subprocess.run([worker, "--json"], input=b"quantum:" + literal,
                                    capture_output=True, timeout=30, env=env)
            if result.returncode == 0:
                response = json.loads(result.stdout)
                if not response["copy_text"]:
                    raise ValueError("Worker returned an empty result")
                outcome = "result"
            elif result.returncode == 2 and result.stderr.strip():
                outcome = ("previous diagnostic" if previous_diagnostic in result.stderr
                           else "diagnostic")
            else:
                raise RuntimeError((result.returncode, result.stderr))
            cache[literal] = outcome, result.stderr
        actual, diagnostic = cache[literal]
        expected = "previous diagnostic" if args.baseline else row["outcome"]
        if actual != expected:
            raise ValueError((lesson["lesson"], row["cell"], row["start"], actual, expected))
        if not args.baseline and "diagnostic_contains" in row and row["diagnostic_contains"].encode() not in diagnostic:
            raise ValueError((lesson["lesson"], row["cell"], row["start"], diagnostic))
        counts[actual] += 1
print(dict(counts))
