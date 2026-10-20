"""Exercise the real source-files dialog through both editors and frozen compiler."""
import argparse
from pathlib import Path
import subprocess

repo = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument("--package", type=Path, default=repo / "dist/QuantumStudio")
parser.add_argument("--output", type=Path, default=repo / "dist/source-files-validation")
args = parser.parse_args()
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
report = output / "source-files.txt"
if report.exists():
    raise SystemExit("Use a fresh output directory; preserve earlier GUI evidence.")
result = subprocess.run(
    [str(args.package.resolve() / "QuantumStudio.exe"), "--source-files-test",
     str(output / "Unicode κ sources"), str(report)],
    timeout=90, capture_output=True,
)
assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
assert report.read_text(encoding="utf-8").startswith("PASS:"), report.read_text(encoding="utf-8")
for editor in ("composer", "classical"):
    for state in ("unchanged", "changed", "minimum"):
        image = Path(str(report) + f".{editor}.{state}.png")
        assert image.stat().st_size > 1000, image
print(report.read_text(encoding="utf-8"))
print("Six captures generated; visual inspection is separate from these assertions.")
