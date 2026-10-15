"""Independent state-amplitude checks for the OpenQASM adapter and frozen helper."""
import argparse
import importlib.util
import json
import math
import cmath
import logging
logging.getLogger("pyqasm").setLevel(logging.CRITICAL)
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('qasm_import', root/'windows/qasm-import.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
logging.disable(logging.CRITICAL)
parser = argparse.ArgumentParser()
parser.add_argument('--worker', type=Path, default=root/'dist/QuantumStudio/quantum-worker.exe')
parser.add_argument('--helper', type=Path, default=root/'dist/QuantumStudio/qasm-import/qasm-import.exe')
options = parser.parse_args()
worker, helper = options.worker.resolve(), options.helper.resolve()
header = 'OPENQASM 3.0; include "stdgates.inc"; '
checks = 0
phase_sources = []

def expression(circuit):
    value = '|' + '0'*circuit['Qubits'] + '>'
    for step in circuit['Steps']:
        gate, angle, wires = step['Gate'], step['Angle'], step['Wires']
        indices = '['+','.join(map(str,wires))+']'
        if gate in ('Reset','Measure'):
            value = ('reset' if gate=='Reset' else 'dephase')+'('+value+','+indices+')'
        else:
            op = '(exp(i*('+angle+'))*I)' if gate=='GPhase' else gate+('('+angle+')' if angle else '')
            value = 'apply('+op+','+value+','+indices+')'
    return value

def verify(source, expected, published_u=False):
    global checks
    circuit = adapter.convert(source, published_u=published_u)
    value = expression(circuit)
    result = subprocess.run([str(worker),'--json','--approx'],input='quantum:norm(vec(('+value+')-('+expected+')))' ,
                            encoding='utf-8',capture_output=True,timeout=30)
    assert result.returncode==0, (source,result.stderr)
    residual=complex(json.loads(result.stdout)['text'].replace(chr(0x2212),'-').replace(' ','').replace('i','j'))
    assert abs(residual)<1e-12, (source,residual)
    if 'gphase' in source or published_u or 'ctrl @ U' in source:
        phase_sources.append((source,published_u))
    checks += 1

# Coherent controls expose a lost relative phase that basis probabilities miss.
for selection, bits in [('0:1','11000'),('0:0','10000'),('0:2:4','10101'),
                        ('4:-2:0','10101'),(':2','11100'),('2:','00111'),
                        (':','11111'),('0:3:4','10010'),('4:-3:0','01001')]:
    source=header+'qubit[5] q; x q['+selection+'];'
    verify(source,'|'+bits+'>');phase_sources.append((source,False))
source=header+'qubit[2] q; bit[2] c; h q; c[0:1]=measure q[0:1];'
verify(source,'identity(4)/4');phase_sources.append((source,False))
source=header+'qubit[2] q; x q; reset q[1:-1:0];'
verify(source,'density(|00>)');phase_sources.append((source,False))

for gate, angle in [('s','pi/2'),('sdg','-pi/2'),('t','pi/4'),('tdg','-pi/4')]:
    for modifier, factor, negative in [('ctrl @ ',1,False),('negctrl @ ',1,True),
                                      ('inv @ ctrl @ ',-1,False),('ctrl @ inv @ ',-1,False),
                                      ('pow(-3) @ ctrl @ ',-3,False),('ctrl @ pow(2) @ ',2,False)]:
        phase=f'exp(i*({factor})*({angle}))'
        expected=f'[1;{phase};1;1]/2' if negative else f'[1;1;1;{phase}]/2'
        source=header+f'qubit[2] q; h q; {modifier}{gate} q[0],q[1];'
        verify(source,expected);phase_sources.append((source,False))
    # The same gate through a custom definition and a reversed physical order.
    source=header+f'gate custom a {{ {gate} a; }} qubit[3] q; h q; ctrl @ custom q[2],q[0];'
    verify(source,f'[1;1;1;1;1;exp(i*({angle}));1;exp(i*({angle}))]/sqrt(8)')
    phase_sources.append((source,False))

verify(header+'qubit q; U(pi/2,pi/4,pi/3) q;', '(|0>+exp(i*pi/4)|1>)/sqrt(2)')
verify(header+'qubit q; gphase(pi/3); h q;', 'exp(i*pi/3)|+>')
verify(header+'qubit q; inv @ U(pi/2,pi/4,pi/3) q;', '(|0>-exp(-i*pi/3)|1>)/sqrt(2)')
verify(header+'qubit[2] a; qubit b; x a[1]; negctrl @ ctrl @ x a[0],a[1],b;', '|011>')
verify(header+'qubit q; inv @ sx q;', 'SXdg|0>')
verify(header+'qubit q; pow(3) @ x q;', '|1>')
for theta in ('pi/3', '-pi/7', '2*pi'):
    verify(header+f'qubit q; h q; ctrl @ gphase({theta}) q;', f'P({theta})|+>')
    verify(header+f'qubit q; h q; negctrl @ gphase({theta}) q;', f'X P({theta}) X |+>')
    verify(header+f'qubit[2] q; h q; ctrl(2) @ gphase({theta}) q[1],q[0];', f'CP({theta})|++>')
    verify(header+f'qubit[3] q; h q; ctrl(2) @ gphase({theta}) q[2],q[0];', f'[1;1;1;1;1;exp(i*({theta}));1;exp(i*({theta}))]/sqrt(8)')
    verify(header+f'qubit[2] q; h q; negctrl @ ctrl @ gphase({theta}) q[1],q[0];', f'(I@X) CP({theta}) (I@X)|++>')
    verify(header+f'gate phased a {{gphase({theta}); x a;}} qubit[2] q; h q; ctrl @ phased q[0],q[1];', f'CNOT (P({theta})@I)|++>')
    verify(header+f'gate phased a {{gphase({theta}); x a;}} qubit[2] q; h q; inv @ ctrl @ phased q[0],q[1];', f'CNOT (P(-({theta}))@I)|++>')
    verify(header+f'qubit q; h q; pow(2) @ ctrl @ gphase({theta}) q;', f'P(2*({theta}))|+>')
verify('OPENQASM 2.0; include "qelib1.inc"; qreg a[2]; creg c[2]; h a[0]; cx a[0],a[1]; measure a -> c;', '[1/2,0,0,0;0,0,0,0;0,0,0,0;0,0,0,1/2]')

# Independent matrix entries from the two published definitions; include both
# columns and coherent inputs so a missing phase cannot hide in probabilities.
def column(values):
    return '['+';'.join(f'({v.real:.17g})+({v.imag:.17g})*i' for v in values)+']'

# iSWAP exchanges odd-parity basis states with phase i. Exercise every column,
# coherent inputs, inverse placement, integer powers and a non-leading control.
for modifier,power in [('',1),('inv @ ',-1),('pow(2) @ ',2),('pow(-3) @ ',-3),('inv @ inv @ ',1),('pow(0) @ ',0)]:
    for basis in range(4):
        prep=''.join(f'x q[{w}];' for w in range(2) if basis & (1<<(1-w)))
        target=basis ^ 3 if basis in (1,2) and power%2 else basis
        phase=1j**power if basis in (1,2) else 1
        expected=[0j]*4;expected[target]=phase
        verify(header+f'qubit[2] q;{prep}{modifier}iswap q[0],q[1];',column(expected))
    expected=[.5,(1j**power)*.5,(1j**power)*.5,.5]
    source=header+f'qubit[2] q;h q;{modifier}iswap q[1],q[0];'
    verify(source,column(expected));phase_sources.append((source,False))

for polarity in ('ctrl','negctrl'):
    for modifier,power in [(polarity+' @ ',1),('inv @ '+polarity+' @ ',-1),
                           (polarity+' @ inv @ ',-1),('pow(-2) @ '+polarity+' @ ',-2)]:
        # q[2] is the control; target order is q[1],q[0].
        for basis in range(8):
            prep=''.join(f'x q[{w}];' for w in range(3) if basis & (1<<(2-w)))
            active=(basis&1)==(1 if polarity=='ctrl' else 0)
            odd=((basis>>1)&1)!=((basis>>2)&1)
            target=basis^6 if active and odd and power%2 else basis
            expected=[0j]*8;expected[target]=1j**power if active and odd else 1
            verify(header+f'qubit[3] q;{prep}{modifier}iswap q[2],q[1],q[0];',column(expected))
        expected=[(1j**power if ((b&1)==(1 if polarity=='ctrl' else 0) and ((b>>1)&1)!=((b>>2)&1)) else 1)/math.sqrt(8) for b in range(8)]
        source=header+f'qubit[3] q;h q;{modifier}iswap q[2],q[1],q[0];'
        verify(source,column(expected));phase_sources.append((source,False))

# A source-defined gate takes precedence over the primitive of the same name.
verify(header+'gate iswap a,b {x a;} qubit[2] q;iswap q[0],q[1];','|10>')

for theta,phi,lam in [(math.pi/2,0,math.pi),(.37,-.49,.81),(-1.2,.7,-.2)]:
    for published in (False,True):
        if published:
            e=cmath.exp(1j*theta)
            matrix=[[(1+e)/2,-1j*cmath.exp(1j*lam)*(1-e)/2],
                    [1j*cmath.exp(1j*phi)*(1-e)/2,cmath.exp(1j*(phi+lam))*(1+e)/2]]
        else:
            matrix=[[math.cos(theta/2),-cmath.exp(1j*lam)*math.sin(theta/2)],
                    [cmath.exp(1j*phi)*math.sin(theta/2),cmath.exp(1j*(phi+lam))*math.cos(theta/2)]]
        for inverse in (False,True):
            operation = [[complex(matrix[c][r]).conjugate() for c in range(2)] for r in range(2)] if inverse else matrix
            mod='inv @ ' if inverse else ''
            for prep,initial in [('',[1,0]),('x q;',[0,1]),('h q;',[2**-.5,2**-.5]),('h q;s q;',[2**-.5,1j*2**-.5])]:
                expected=[sum(operation[r][c]*initial[c] for c in range(2)) for r in range(2)]
                verify(header+f'qubit q; {prep} {mod}U({theta},{phi},{lam}) q;',column(expected),published)
            for polarity in ('ctrl','negctrl'):
                # Target q0, control q1; use |++> so both control branches matter.
                expected=[.5+0j]*4
                bit=1 if polarity=='ctrl' else 0
                for r in range(2):
                    expected[2*r+bit]=sum(operation[r][c]*.5 for c in range(2))
                verify(header+f'qubit[2] q;h q;{mod}{polarity} @ U({theta},{phi},{lam}) q[1],q[0];',column(expected),published)

verify(header+'gate custom(a,b,c) q {U(a,b,c) q;} qubit q; custom(pi/2,0,pi) q;', 'exp(i*pi/4)|+>', True)
verify(header+'qubit q; pow(2) @ U(pi/2,0,pi) q;', 'i|0>', True)
try:
    adapter.convert('OPENQASM 2.0; qreg q[1]; U(0,0,0) q[0];',published_u=True)
except ValueError:
    pass
else:
    raise AssertionError('Published OpenQASM 3 mode accepted a version 2 program.')

# A reusable subroutine with nested loops, classical expressions, and controlled
# phase gates. Analytic Fourier columns check bit order and phase, not just probs.
for n in range(1,5):
    for basis in range(2**n):
        prep = ''.join(f'x q[{i}];' for i in range(n) if basis & (1 << (n-1-i)))
        body = f'''def transform(qubit[{n}] r) {{
          for int i in [0:{n}-1] {{ h r[i];
            for int j in [i+1:{n}-1] {{ cp(pi/(2**(j-i))) r[j],r[i]; }}
          }}
          for int i in [0:{n//2}-1] {{ swap r[i],r[{n}-1-i]; }}
        }}'''
        # OpenQASM descending empty ranges are tool-dependent: emit only loops
        # with nonempty bounds; the inner final iteration is likewise guarded.
        body = body.replace(f'for int j in [i+1:{n}-1]',f'if (i < {n}-1) for int j in [i+1:{n}-1]')
        if n==1:
            body=body.replace('for int i in [0:0-1] { swap r[i],r[1-1-i]; }','')
        source=header+body+f'qubit[{n}] q;'+prep+'transform(q);'
        expected='['+';'.join(f'exp(2*pi*i*{basis*k}/{2**n})/sqrt({2**n})' for k in range(2**n))+']'
        verify(source,expected)

for secret in range(8):
    source=header+f'''qubit[3] q; qubit anc;
    x anc; h anc;
    for int i in [0:2] {{ h q[i]; if (({secret} >> (2-i)) & 1) {{cx q[i],anc;}} }}
    h q;'''
    verify(source,'|'+format(secret,'03b')+'>@|->')

invalid = [
    *[header+'qubit[3] q; x q['+selection+'];' for selection in ('0:0:2','0:3','-1:1','0:1.5')],
    header+'qubit[9] q; h q[0];', header+'qubit q; for int i in [0:512] {x q;}',
    header+'qubit[2] q; bit b; b=measure q[0]; if(b) x q[1];',
    header+'qubit q; unknown q;', header+'qubit q; delay[10ns] q;',
    header+'qubit q; rx q;', header+'qubit[2] q; cx q[0],q[0];',
    header+'qubit q; pow(0.5) @ x q;', header+'include "private.inc"; qubit q;',
    header+'qubit[3] q; ctrl(3) @ gphase(pi/3) q[0],q[1],q[2];',
    header+'qubit q; iswap q;',
    header+'qubit[2] q; iswap(pi) q[0],q[1];',
    header+'qubit[2] q; iswap q[0],q[0];',
    header+'qubit[4] q; ctrl(2) @ iswap q[0],q[1],q[2],q[3];',
]
for source in invalid:
    try:
        adapter.convert(source)
    except Exception:
        pass
    else:
        raise AssertionError('Accepted unsupported program: '+source)

fixture=header+'''gate quarter a {p(pi/2) a;}
def entangle(qubit[2] a) {h a[0]; cx a[0],a[1];}
qubit[2] q; entangle(q); quarter q[1]; gphase(pi/4);'''
(root/'.tools').mkdir(exist_ok=True)
(root/'.tools/qasm-import-fixture.qasm').write_text(fixture,encoding='utf-8')
frozen=subprocess.run([str(helper)],input=fixture,encoding='utf-8',capture_output=True,timeout=30)
assert frozen.returncode==0, frozen.stderr
assert json.loads(frozen.stdout)==adapter.convert(fixture)
for source,published in phase_sources:
    command=[str(helper)]+(['--published-u'] if published else [])
    frozen=subprocess.run(command,input=source,encoding='utf-8',capture_output=True,timeout=30)
    assert frozen.returncode==0, frozen.stderr
    assert json.loads(frozen.stdout)==adapter.convert(source,published_u=published), source
print(f'PASS: {checks} amplitude/density comparisons, {len(invalid)} rejected programs, {len(phase_sources)+1} frozen compiler parity checks.')

# Check the executable's byte limit before BOM removal and UTF-8 decoding.
valid_source = (header+'qubit q; h q;').encode('utf-8')
for data in (b' '+valid_source+b' '*(262145-len(valid_source)-1),
             b'\xef\xbb\xbf'+valid_source+b' '*(262145-len(valid_source)-3),
             b'\xc3\x28'):
    rejected = subprocess.run([str(helper)], input=data, capture_output=True, timeout=30)
    assert rejected.returncode != 0 and not rejected.stdout, rejected.stdout
bom_result = subprocess.run([str(helper)], input=b'\xef\xbb\xbf'+valid_source, capture_output=True, timeout=30)
assert bom_result.returncode == 0, bom_result.stderr
assert json.loads(bom_result.stdout) == adapter.convert(valid_source.decode('utf-8'))
print('PASS: 4 frozen compiler input boundary checks.')
