"""Execute saved circuits produced through the editor's actual controls."""
import argparse,base64,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--prefix',required=True);p.add_argument('--adapter',type=Path,required=True);p.add_argument('--worker',type=Path,required=True)
a=p.parse_args();worker=a.worker.resolve();env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
checks=0
for suffix,expected in (('real','1'),('integer','0'),('numeric','1')):
    circuit=Path(a.prefix+'.'+suffix+'.qcircuit').read_bytes()
    bridge=subprocess.run([str(a.adapter.resolve())],input=circuit,capture_output=True,timeout=30)
    assert bridge.returncode==0,bridge.stderr
    payloads=json.loads(bridge.stdout.decode('utf-8-sig'));checks+=1
    for exact in (True,False):
        payload=base64.b64decode(payloads['exact' if exact else 'sampled'])
        result=subprocess.run([str(worker),'--exact-circuit' if exact else '--sample'],input=payload,capture_output=True,timeout=30,env=env)
        assert result.returncode==0,result.stderr
        value=json.loads(result.stdout)
        if exact:
            for key in set(value['probabilities'])|{expected}:
                expression='abs(('+value['probabilities'].get(key,'0')+')-'+('1' if key==expected else '0')+')'
                check=subprocess.run([str(worker),'--json','--approx'],input=expression.encode(),capture_output=True,timeout=30,env=env)
                assert check.returncode==0,check.stderr
                assert float(json.loads(check.stdout)['copy_text'].replace('\u2212','-'))<1e-10,(suffix,key,check.stdout)
        else:assert value['counts']=={expected:10000},(suffix,value)
        checks+=1
print(f'PASS: {checks} editor-created runtime rotation save/load and worker checks.')
