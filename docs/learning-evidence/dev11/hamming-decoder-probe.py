"""Finite IBM-062 classical single-error decoder using existing native operations."""
import argparse,hashlib,json,re,os,subprocess
from pathlib import Path
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--worker',type=Path,default=Path(os.environ.get('QUANTUM_WORKER','quantum-worker.exe' if os.name=='nt' else 'quantum-worker')))
ap.add_argument('--definitions',type=Path)
ap.add_argument('--worker-revision',help='Optional externally verified source revision; hash is always recorded')
ap.add_argument('--source',type=Path,required=True,help='Pinned original IBM-062 notebook')
ap.add_argument('--output',type=Path,required=True)
args=ap.parse_args();r=args.output;r.mkdir(parents=True,exist_ok=True)
if (r/'results.json').exists():raise SystemExit('Use a fresh evidence directory')
source=args.source;raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()=='e8b1deec5f914fc07cd75fcf26051712116a936dc50d38ed2149032b8487b4f5'
cell=''.join(json.loads(raw)['cells'][0]['source']);blocks=list(re.finditer(r'\$\$(.*?)\$\$',cell,re.S))
words=re.findall(r'(?<![01])[01]{7}(?![01])',blocks[1].group());checks=re.findall(r'(?<![01])[01]{7}(?![01])',blocks[5].group())
assert len(words)==len(set(words))==16 and len(checks)==3
columns=[tuple(int(h[j]) for h in checks) for j in range(7)];assert len(set(columns))==7 and (0,0,0) not in columns
w=args.worker.resolve();definitions=(args.definitions or w.parent/'data').resolve()
if not definitions.is_dir():raise SystemExit('Definition directory not found')
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(definitions));records=[];cases=[]
def vec(a):return 'vector('+','.join(map(str,a))+')'
def run(name,expr,expected):
 p=subprocess.run([str(w),'--json'],input=expr.encode(),capture_output=True,env=env,timeout=15)
 d=dict(id=name,input=expr,expected=expected,exit=p.returncode,stdout=p.stdout.decode(),stderr=p.stderr.decode());a=json.loads(p.stdout) if p.returncode==0 else {};d['passed']=a.get('approximate') is False and a.get('copy_text')==expected
 if d['passed']:
  q=subprocess.run([str(w),'--json'],input=a['copy_text'].encode(),capture_output=True,env=env,timeout=15);b=json.loads(q.stdout) if q.returncode==0 else {};d['copy']=dict(exit=q.returncode,stdout=q.stdout.decode(),stderr=q.stderr.decode());d['passed']=b.get('approximate') is False and b.get('copy_text')==expected
 records.append(d);return a.get('copy_text')
received=set()
for word in words:
 for position in range(8):
  bits=list(map(int,word));error=[int(j==position-1) for j in range(7)]
  altered=[a^b for a,b in zip(bits,error)];received.add(tuple(altered))
  syndrome=tuple(sum(a*int(b) for a,b in zip(altered,h))%2 for h in checks)
  decoded=0 if syndrome==(0,0,0) else columns.index(syndrome)+1
  assert decoded==position
  name=word+'-error-'+str(position);expr='vector('+','.join(f'qbitdot({vec(altered)},{vec(h)})' for h in checks)+')'
  s=run(name+'-syndrome',expr,vec(syndrome))
  if s is None:continue
  # The descending source columns encode the syndrome as 8 minus position.
  # This native expression chooses a mask; the host does not inject the oracle mask.
  native_s='qbitvalue('+s+')'
  selected=f'if({native_s}=0,0,8-{native_s})'
  run(name+'-position',selected,str(position))
  mask=f'qbits(if({native_s}=0,0,2^({native_s}-1)),7)'
  run(name+'-mask',mask,vec(error))
  result=run(name+'-corrected',f'qbitxor({vec(altered)},{mask})',vec(bits))
  cases.append(dict(original_word=word,error_position=position,received_word=''.join(map(str,altered)),oracle_syndrome=syndrome,native_corrected=result))
assert len(received)==128
# Explicit out-of-contract two-bit error: columns1 XOR2 equals column7.
a=[1,1,0,0,0,0,0];s='vector('+','.join(f'qbitdot({vec(a)},{vec(h)})' for h in checks)+')';native_s=f'qbitvalue({s})';mask=f'qbits(if({native_s}=0,0,2^({native_s}-1)),7)'
run('two-bit-limit',f'qbitxor({vec(a)},{mask})','vector(1,1,0,0,0,0,1)')
summary=dict(transmissions=len(cases),unique_received_words=len(received),checks=len(records),passed=sum(x['passed'] for x in records),copies=sum('copy' in x for x in records),failures=[x['id'] for x in records if not x['passed']])
result=dict(summary=summary,source_sha256=hashlib.sha256(raw).hexdigest(),cell_id=json.loads(raw)['cells'][0]['id'],source_blocks=[dict(id=f'eq{i+1:03}',offset=blocks[i].start(),original=blocks[i].group(),sha256=hashlib.sha256(blocks[i].group().encode()).hexdigest()) for i in [1,5]],source_section=cell[cell.index('## Error detection and correction'):cell.index('## Code spaces of CSS codes')],worker_commit=args.worker_revision,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),worker_sha256=hashlib.sha256(w.read_bytes()).hexdigest(),source_baseline='02d5ca3f5713385818e80db15b1a58e3b518e569',data_sha256={str(p.relative_to(definitions)):hashlib.sha256(p.read_bytes()).hexdigest() for p in definitions.rglob('*') if p.is_file()},classification='authored classical single-error decoding composition; not literal source/circuit/instrument execution',cases=cases,records=records)
(r/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(summary));raise SystemExit(int(bool(summary['failures'])))
