"""Focused DEV-11 timing probe. No product edits/builds; timeout is an observation."""
import argparse,hashlib,importlib.util,json,os,subprocess,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--timeout',type=float,default=12);a=ap.parse_args()
a.output.mkdir(parents=True,exist_ok=False)
d=Path(__file__).parent;spec=importlib.util.spec_from_file_location('oracle',d/'probe.py');oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
worker=a.root/'dist/releases/35d9e753/QuantumStudio/quantum-worker.exe';digest=hashlib.sha256(worker.read_bytes()).hexdigest();assert digest==oracle.HASH
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
fs=json.loads((a.root/'cleanup-audit/dev11-20261101-a7c4/complete/fixtures.json').read_text());cases={f['id']:f for f in fs}
left=cases['060-recovery-shor-IIIIIIYII'];right=cases['060-associated-recovery-shor-IIIIIIYII']
records=[]
for label,f in [('original-left',left),('equivalent-right',right),('original-left-repeat',left),('equivalent-right-repeat',right)]:
 start=time.perf_counter();rec=dict(label=label,expression=f['expression'],worker_revision=oracle.RELEASE,worker_sha256=digest,timeout_seconds=a.timeout)
 try:
  p=subprocess.run([str(worker),'--json'],input=f['expression'].encode(),capture_output=True,env=env,cwd=a.output,timeout=a.timeout)
  rec.update(returncode=p.returncode,stdout=p.stdout.decode(),stderr=p.stderr.decode())
  actual=oracle.numeric_cells(json.loads(rec['stdout']));expected=[[complex(*v) for v in row] for row in f['expected']]
  assert len(actual)==len(expected) and all(len(x)==len(y) for x,y in zip(actual,expected))
  x,y=next((x,y) for ar,er in zip(actual,expected) for x,y in zip(ar,er) if abs(y)>1e-12);phase=x/y
  err=max(abs(x-phase*y) for ar,er in zip(actual,expected) for x,y in zip(ar,er));rec.update(max_residual=err,common_phase=[phase.real,phase.imag],correct=err<1e-12 and abs(abs(phase)-1)<1e-12,status='completed')
 except subprocess.TimeoutExpired:rec.update(status='timeout',correct=None)
 rec['elapsed_seconds']=time.perf_counter()-start;records.append(rec)
 (a.output/'timings.json').write_text(json.dumps(records,indent=2),encoding='utf-8');print(label,rec['status'],round(rec['elapsed_seconds'],3),rec.get('correct'),flush=True)
red=all(x['status']=='timeout' for x in records[::2]) and all(x['status']=='completed' and x['correct'] for x in records[1::2])
green=all(x['status']=='completed' and x['correct'] for x in records)
print('REPRODUCED_ASSOCIATION_SLOWDOWN',red);raise SystemExit(1 if red else 0 if green else 2)
