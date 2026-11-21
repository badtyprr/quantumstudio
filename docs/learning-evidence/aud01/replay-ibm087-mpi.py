"""Replay the notebook's two MPI ranks and verify the message payload."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

notebook, launcher, output = map(Path,sys.argv[1:])
inventory=json.loads(Path(__file__).with_name("ibm087-inventory.json").read_bytes())
data=notebook.read_bytes()
assert hashlib.sha256(data).hexdigest()==inventory["source_sha256"]
blocks=[b for c in json.loads(data)["cells"] for b in re.findall(r"^```python[ \t]*\n(.*?)^```","".join(c["source"]),re.M|re.S) if "MPI.COMM_WORLD" in b]
assert len(blocks)==1
# The published copy includes two trailing Vim empty-line markers.
code=re.sub(r"\n~\n~\n?$","\n",blocks[0])
assert code!=blocks[0]
ast.parse(code)
launcher=launcher.resolve()
env=dict(os.environ)
args=[str(launcher)]
if os.name=="nt":
    env["I_MPI_ROOT"]=str(launcher.parent.parent)
    env["PATH"]=str(launcher.parent)+os.pathsep+env["PATH"]
    args.append("-localonly")
with TemporaryDirectory() as tmp:
    script=Path(tmp)/"mpi-hello-world.py"
    script.write_text(code,encoding="utf8")
    result=subprocess.run(args+["-n","2",sys.executable,str(script)],env=env,capture_output=True,text=True,timeout=60,check=True)
lines=result.stdout.splitlines()
for rank in range(2):
    assert f"[Rank {rank}] Hello from process {rank} of 2!" in lines
payload={"answer":42,"pi":3.14}
for rank,action in enumerate(("Sending","Received")):
    prefix=f"[Rank {rank}] {action}: "
    assert [ast.literal_eval(line[len(prefix):]) for line in lines if line.startswith(prefix)]==[payload]
output.write_bytes((json.dumps(dict(source_sha256=inventory["source_sha256"],ranks=2,
    launch="local MPI",discarded_vim_markers=2,output=lines),indent=2)+"\n").encode())
print("Both MPI ranks ran and rank 1 received the notebook's dictionary from rank 0.")

