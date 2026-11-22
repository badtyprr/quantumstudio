"""Replay worked density-matrix examples from the 45-page IBM-001 lecture deck."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
parser.add_argument("slides", type=Path)
parser.add_argument("report", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
slides_hash = hashlib.sha256(args.slides.read_bytes()).hexdigest()
if slides_hash != "cd4b365f01d989d5913d5ba94167d55dee9ed807de8c321cfa25b661d7acc390":
    raise ValueError("Expected IBM's 45-page Density matrices slide deck")

m = "[-4-9i,8,2+9i;-7,-4-9i,-9+7i;1-5i,8-6i,-4i]"
gram = "[172,34+169i,-6-71i;34-169i,261,13-69i;-6+71i,13+69i,231]"
v = "[(1+2i)/3;-2/3]"
mixed = "[3,1;1,1]/4"
pair = "[2,0,0,0;0,0,0,0;0,0,1,1;0,0,1,1]/4"
pure_pair = "(|00>+tensor(|+>,|1>))/sqrt(2)"


three_registers = "density((|000>+|101>+i*|111>)/sqrt(3))"


def rotated(a):
    return f"[cos({a});sin({a})]"

checks = [
    (4, "diagonal trace", f"Tr({gram})=664", "1"),
    (6, "positive Gram matrix", f"dagger({m})*({m})=({gram})", "1"),
    (7, "normalized trace", f"Tr(({gram})/664)=1", "1"),
    (9, "positive imaginary state", "density(|+i>)=[1,-i;i,1]/2", "1"),
    (10, "minus projector", "density(|->)=[1,-1;-1,1]/2", "1"),
    (11, "complex outer product", f"density({v})=[5,-2-4i;-2+4i,4]/9", "1"),
    (13, "global phase", f"density(i*({v}))=density({v})", "1"),
    (16, "nonorthogonal mixture", f"(density(|0>)+density(|+>))/2=({mixed})", "1"),
    (17, "mixed state in X basis", "(density(|+>)+density(|->))/2=I/2", "1"),
    (19, "classical distribution", "(density(|0>)+3*density(|1>))/4=[1,0;0,3]/4", "1"),
    (21, "spectral decomposition", f"cos(pi/8)^2*density({rotated('pi/8')})+sin(pi/8)^2*density({rotated('5*pi/8')})=({mixed})", "1"),
    (23, "pure Bloch state", "density([cos(pi/4);i*sin(pi/4)])=(I+Y)/2", "1"),
    (26, "south pole", "density(|1>)=(I-Z)/2", "1"),
    (27, "positive X axis", "density(|+>)=(I+X)/2", "1"),
    (29, "negative Y axis", "density(|-i>)=(I-Y)/2", "1"),
    (30, "rotation in XZ plane", f"density({rotated('pi/8')})=(I+sin(pi/4)*X+cos(pi/4)*Z)/2", "1"),
    (32, "Bloch center", "purity(I/2)=1/2", "1"),
    (33, "Bloch interior", f"({mixed})=(I+X/2+Z/2)/2", "1"),
    (34, "Bell coherences", "density((|00>+|11>)/sqrt(2))=[1,0,0,1;0,0,0,0;0,0,0,0;1,0,0,1]/2", "1"),
    (35, "classical correlation", "(density(|00>)+density(|11>))/2=tensor(I/2,I/2)", "0"),
    (38, "Bell marginal", "ptrace(density((|00>+|11>)/sqrt(2)),[1])=I/2", "1"),
    (38, "Bob projects onto one", "tensor(I,density(|1>))*((|00>+|11>)/sqrt(2))=|11>/sqrt(2)", "1"),
    (42, "nonorthogonal components", f"ptrace(density({pure_pair}),[1])=({mixed})", "1"),
    (44, "complementary reduction", f"ptrace(density({pure_pair}),[0])=[1,1/sqrt(2);1/sqrt(2),1]/2", "1"),
    (44, "trace B from ABC", f"ptrace({three_registers},[1])=[1,0,0,1;0,0,0,0;0,0,0,0;1,0,0,2]/3", "1"),
    (44, "trace AB from ABC", f"ptrace({three_registers},[0,1])=[1,0;0,2]/3", "1"),
    (44, "wrong subsystem control", f"ptrace({three_registers},[0,2])=[1,0;0,2]/3", "0"),
    (45, "first marginal", f"ptrace(({pair}),[1])=I/2", "1"),
    (45, "second marginal", f"ptrace(({pair}),[0])=({mixed})", "1"),
    (45, "swapped marginal control", f"ptrace(({pair}),[0])=I/2", "0"),
]
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
records = []
for page, label, equation, expected in checks:
    run = subprocess.run([worker, "--json"], input=("quantum:" + equation).encode(),
                         capture_output=True, timeout=30, env=env)
    value = json.loads(run.stdout)["copy_text"] if run.returncode == 0 else run.stderr.decode().strip()
    adapted = page in (4, 13, 19, 23, 42, 44) or label in ("Bloch center", "classical correlation", "rotation in XZ plane")
    records.append(dict(page=page, label=label, numerical_adaptation=adapted, negative_control=expected == "0", equation=equation, expected=expected, actual=value))
args.report.write_text(json.dumps(dict(slides_sha256=slides_hash, worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
                                      checks=records), indent=2) + "\n", encoding="utf8")
failed = [(r["label"], r["actual"]) for r in records if r["actual"] != r["expected"]]
if failed:
    raise SystemExit(failed)
print(f"{len(records)} slide checks passed")
