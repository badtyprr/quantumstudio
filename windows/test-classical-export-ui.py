"""Validate edited-program export through the packaged GUI and frozen compiler."""
import argparse
import hashlib
import json
import subprocess
import uuid
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--package", type=Path)
parser.add_argument("--output", type=Path)
args = parser.parse_args()
repo = Path(__file__).resolve().parent.parent
package = (args.package or repo / "dist/QuantumStudio").resolve()
output = (args.output or repo / "dist/classical-export-validation" / uuid.uuid4().hex).resolve()
assert not output.exists(), "Use a fresh audit directory."
output.mkdir(parents=True)
app = package / "QuantumStudio.exe"
compiler = package / "qasm-import/qasm-import.exe"

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

hashes = {"gui": digest(app), "compiler": digest(compiler)}
source = output / "source α.qasm"
original = b'OPENQASM 3; include "stdgates.inc"; qubit q; bit c; x q; c=measure q;\n'
source.write_bytes(original)
report = output / "export"
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = 0
run = subprocess.run([str(app), "--classical-export-test", str(source), str(report)],
                     capture_output=True, timeout=120, startupinfo=startup)
assert run.returncode == 0 and report.exists(), (run.returncode, run.stderr)
assert report.read_text(encoding="utf-8").startswith("PASS:"), report.read_text(encoding="utf-8")
assert source.read_bytes() == original, "Export modified the imported source."
exported = Path(str(report) + ".qasm").read_bytes()
assert not exported.startswith(b"\xef\xbb\xbf")
rebuilt = subprocess.run([str(compiler), "--classical"], input=exported,
                         capture_output=True, timeout=30)
assert rebuilt.returncode == 0, rebuilt.stderr
assert json.loads(rebuilt.stdout)["Qubits"] == 1
captures = [Path(str(report) + suffix) for suffix in (".png", ".rejected.png", ".minimum.png")]
assert all(path.is_file() and path.stat().st_size > 0 for path in captures)
assert hashes == {"gui": digest(app), "compiler": digest(compiler)}
(output / "audit.json").write_text(json.dumps({
    "passed": True, "package": str(package), "hashes": hashes,
    "screenshots": {str(path): digest(path) for path in captures},
    "scope": "Edited export, compiler rejection, existing-file preservation, source/history, save/reopen; not general program equivalence."
}, indent=2) + "\n", encoding="utf-8")
print("PASS: frozen classical export GUI, compiler rejection, file/source/history preservation and save/reopen.")
