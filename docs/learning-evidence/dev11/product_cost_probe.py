"""Minimize DEV-11 product cost against the pinned packaged worker."""
import argparse,hashlib,importlib.util,json,os,subprocess,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
ap=argparse.ArgumentParser();ap.add_argument('--suite',choices=['minimal','hypotheses','identity'],default='minimal');ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--timeout',type=float,default=12);a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=False)
spec=importlib.util.spec_from_file_location('oracle',Path(__file__).with_name('probe.py'));o=importlib.util.module_from_spec(spec);spec.loader.exec_module(o)
w=a.root/'dist/releases/35d9e753/QuantumStudio/quantum-worker.exe';assert hashlib.sha256(w.read_bytes()).hexdigest()==o.HASH
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(w.parent/'data'))
f=next(x for x in json.loads((a.root/'cleanup-audit/dev11-20261101-a7c4/complete/fixtures.json').read_text()) if x['id']=='060-recovery-shor-IIIIIIYII')
c,tail=f['expression'].split('*pauli',1);error,vec=tail.split(')*',1);error='pauli'+error+')'
cases=[('decoder-alone',c,'IIIIIIYII'),('remove-encoded-state',c+'*'+error,'I'*9),('remove-decoder-call','quantum:'+error+'*'+error,'I'*9)]
for n in [8,7,6,5,4,3]:
 word='I'*(n-3)+'YII';cases.append((f'reduce-to-{n}-qubits','quantum:'+o.pauli(word)+'*'+o.pauli(word),'I'*n))
if a.suite=='hypotheses':
 cases=[('real-X-square-9','quantum:pauli("IIIIIIXII")*pauli("IIIIIIXII")','I'*9),('trace-Y-square-9','quantum:trace(pauli("IIIIIIYII")*pauli("IIIIIIYII"))',512),('trace-Y-square-8','quantum:trace(pauli("IIIIIYII")*pauli("IIIIIYII"))',256),('Y-matrix-alone-9','quantum:pauli("IIIIIIYII")','IIIIIIYII'),('identity-output-9','quantum:qidentity(512)','I'*9)]
if a.suite=='identity':cases=[('identity-square-9','quantum:qidentity(512)*qidentity(512)','I'*9)]
records=[]
for label,expr,expected_word in cases:
 rec=dict(label=label,expression=expr,expected_pauli=expected_word,worker_revision=o.RELEASE,worker_sha256=o.HASH,timeout_seconds=a.timeout);start=time.perf_counter()
 try:
  p=subprocess.run([str(w),'--json'],input=expr.encode(),capture_output=True,env=env,cwd=a.output,timeout=a.timeout);rec['elapsed_seconds']=time.perf_counter()-start
  rec.update(returncode=p.returncode,stderr=p.stderr.decode(),stdout_file=label+'.json');(a.output/rec['stdout_file']).write_bytes(p.stdout)
  data=json.loads(p.stdout)
  if isinstance(expected_word,int):rec['correct']=data['text']==str(expected_word)
  else:
   actual=o.numeric_cells(data);expected=o.matrix(expected_word)
   rec['correct']=len(actual)==len(expected) and all(len(ar)==len(er) and all(abs(x-y)<1e-12 for x,y in zip(ar,er)) for ar,er in zip(actual,expected))
  rec['status']='completed'
 except subprocess.TimeoutExpired:rec.update(status='timeout',correct=None,elapsed_seconds=time.perf_counter()-start)
 records.append(rec);(a.output/'timings.json').write_text(json.dumps(records,indent=2),encoding='utf-8');print(label,rec['status'],round(rec['elapsed_seconds'],3),rec.get('correct'),flush=True)
