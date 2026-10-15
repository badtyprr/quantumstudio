"""Bell-state labels, exact phases, and orthonormality."""
import subprocess,json,os
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data'))
def check(e,v):
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode==0,(e,p.stderr)
 assert json.loads(p.stdout)['text']==v,(e,ascii(p.stdout))
checks=0
for family,names,left,right in [('phi',['Phi','phi','Φ','φ','ϕ',r'\Phi',r'\phi',r'\varphi'],'00','11'),('psi',['Psi','psi','Ψ','ψ',r'\Psi',r'\psi'],'01','10')]:
 for name in names:
  for sign,super in [('+','⁺'),('-','⁻')]:
   suffixes=[sign,'^'+sign,'^{'+sign+'}','_'+sign,'_{'+sign+'}',super]
   for suffix in suffixes:
    check('norm(|'+name+suffix+'>-(|'+left+'>'+sign+'|'+right+'>)/sqrt(2))','0');checks+=1
labels=['Φ+','Φ-','Ψ+','Ψ-']
for a in labels:
 for b in labels:check('<'+a+'|'+b+'>',str(int(a==b)));checks+=1
for e in [r'norm((I@X)|Φ+>-|Ψ+>)',r'norm((Z@I)|Φ+>-|Φ->)',r'norm(SWAP|Ψ->+|Ψ->)',r'norm(vec(ptrace(density(|Φ+>),0)-I/2))',r'norm(vec(density(|Φ+>)+density(|Φ->)+density(|Ψ+>)+density(|Ψ->)-identity(4)))']:
 check(e,'0');checks+=1
for e in [r'|Φ±>',r'|Ψ^2>',r'|Phi+>_4',r'X⁺',r'X_+(1)']:
 p=subprocess.run([str(worker),'--json'],input='quantum:'+e,capture_output=True,encoding='utf-8',env=env,timeout=30)
 assert p.returncode!=0,(e,ascii(p.stdout))
print(f'PASS: {checks} exact Bell-label, orthogonality, phase, and density checks; malformed and ambiguous forms rejected.')
