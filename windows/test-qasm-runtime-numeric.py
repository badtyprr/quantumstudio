"""Typed numeric import/model/export/execution checks with independent results."""
import argparse,base64,importlib.util,json,math,os,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--adapter',type=Path,required=True);parser.add_argument('--worker',type=Path);parser.add_argument('--frozen',type=Path)
args=parser.parse_args();spec=importlib.util.spec_from_file_location('numeric_import',root/'qasm-import.py');compiler=importlib.util.module_from_spec(spec);spec.loader.exec_module(compiler)
checks=0
header='OPENQASM 3.0; include "stdgates.inc"; '
def compile(source,published=False):
 global checks
 result=compiler.convert(source,classical=True,published_u=published);checks+=1
 if args.frozen:
  p=subprocess.run([str(args.frozen.resolve()),'--classical']+(['--published-u'] if published else []),input=source.encode(),capture_output=True,timeout=30)
  assert p.returncode==0,p.stderr
  assert json.loads(p.stdout)==result;checks+=1
 return result
def adapt(circuit):
 global checks
 p=subprocess.run([str(args.adapter.resolve())],input=json.dumps(circuit).encode(),capture_output=True,timeout=30)
 assert p.returncode==0,p.stderr.decode(errors='replace');checks+=1
 return json.loads(p.stdout)
def run(payload,exact):
 global checks
 env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(args.worker.resolve().parent/'data'))
 p=subprocess.run([str(args.worker.resolve()),'--exact-circuit' if exact else '--sample'],input=base64.b64decode(payload),capture_output=True,timeout=45,env=env)
 assert p.returncode==0,p.stderr;checks+=1
 result=json.loads(p.stdout)
 if not exact:return {k:v/10000 for k,v in result['counts'].items()}
 probabilities={}
 for k,value in result['probabilities'].items():
  p=subprocess.run([str(args.worker.resolve()),'--json','--approx'],input=value.encode(),capture_output=True,timeout=30,env=env)
  assert p.returncode==0,p.stderr
  probabilities[k]=float(json.loads(p.stdout)['text'].replace('\u2212','-'))
 return probabilities
cases=[
 ('float[32] f=16777216;f+=1;bit[8] c=bit[8](uint[8](f-16777216.0));',{'00000000':1}),
 ('float[64] f=16777216;f+=1;bit[8] c=bit[8](uint[8](f-16777216.0));',{'00000001':1}),
 ('angle[8] a=angle[8]("11111010");a+=angle[8]("00001010");bit[8] c=bit[8](a);',{'00000100':1}),
 ('float[32] f=3;while(f>0){f-=1;}bit c=bool(f==0);',{'1':1}),
 ('float[32] f=1;bit c;if(f>0){float[32] f=9;f=sqrt(f);c=bool(f==3);}',{'1':1}),
 ('float[32] f=1;bit c;for int i in [0:1]{float[32] local=4;local=sqrt(local);f+=local;}c=bool(f==5);',{'1':1}),
 ('qubit[2] q;h q[0];bit c=measure q[0];float[32] f=float[32](uint[1](c));ry(pi*f) q[1];bit d=measure q[1];',{'00':.5,'11':.5}),
 ('angle[64] a=angle[64]("1000000000000000000000000000000000000000000000000000000000000000");qubit q;ry(a) q;bit c=measure q;',{'1':1}),
 ('float[32] f=1;bit c;if(false){f=sqrt(-1.0);}c=bool(f==1);',{'1':1}),
 ('float[32] f=mod(17.0,5.0);f=f**3;bit[8] c=bit[8](uint[8](f));',{'00001000':1}),
 ('angle[8] a=angle[8]("11001000");a/=uint[8](3);bit[8] c=bit[8](a);',{'01000010':1}),
 ('angle[8] a=angle[8]("11001000");uint[8] n=a/angle[8]("00000011");bit[8] c=bit[8](n);',{'01000010':1}),
 ('float[32] f;bit c;if(false && bool(sqrt(f))){c=1;}',{'0':1}),
]
for function,argument,expected in [('sin','0.0',0),('cos','0.0',1),('tan','0.0',0),('arcsin','0.0',0),('arccos','1.0',0),('arctan','0.0',0),('exp','0.0',1),('log','1.0',0),('sqrt','9.0',3),('floor','3.9',3),('ceiling','3.1',4)]:
 cases.append((f'float[32] f={function}({argument});bit[8] c=bit[8](uint[8](f));',{format(expected,'08b'):1}))
for source,expected in cases:
 original=compile(header+source);assert original['Version']==13,original
 exported=adapt(original);reimported=compile(exported['source']);roundtrip=adapt(reimported)
 if args.worker:
  for exact in (True,False):
   for encoded in (exported,roundtrip):
    actual=run(encoded['exact' if exact else 'sampled'],exact)
    assert all(abs(actual.get(k,0)-expected.get(k,0))<(1e-10 if exact else .025) for k in set(actual)|set(expected)),(source,actual,expected,exported['source'])
# Odd modular values need an additional phase bit. P(theta) inv@Rz(theta)
# retains it, while integer division of the angle by two would truncate it.
source=header+'angle[8] a=angle[8]("10000001");qubit[2] q;h q[0];ctrl @ U(a,0.3,0.7) q[0],q[1];h q[0];bit c=measure q[0];'
encoded=adapt(compile(source,True));assert 'inv @ ctrl @ pow(' in encoded['source'] and 'rz(n0)' in encoded['source'],encoded['source']
expected={'0':(1+math.cos(math.pi*129/256)**2)/2,'1':(1-math.cos(math.pi*129/256)**2)/2}
for convention in (False,True):
 roundtrip=adapt(compile(encoded['source'],convention))
 if args.worker:
  for exact in (True,False):
   for item in (encoded,roundtrip):
    actual=run(item['exact' if exact else 'sampled'],exact)
    assert all(abs(actual.get(k,0)-v)<(1e-10 if exact else .025) for k,v in expected.items()),(actual,expected)
print(f'PASS: {checks} runtime numeric import/model/export checks.')
