"""Check Cirq power-gate conventions against rotation/phase operators.

Sources: qBraid cirq_vqe notebook and Google Quantum AI XPowGate/CZPowGate
reference. Tests retain global phase and test its relative effect under control.
"""
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent.parent
worker = root / 'dist/QuantumStudio/quantum-worker.exe'
checks = 0

def calculate(expression):
    return subprocess.run([str(worker), '--json', '--approx'],
                          input='quantum:' + expression, encoding='utf-8',
                          capture_output=True, timeout=30)

def equal(left, right):
    global checks
    result = calculate('norm(vec((' + left + ')-(' + right + ')))')
    assert result.returncode == 0, (left, result.stderr)
    residual = complex(json.loads(result.stdout)['text'].replace('\u2212', '-').replace(' ', '').replace('i', 'j'))
    assert abs(residual) < 1e-12, (left, right, residual)
    checks += 1

for t in ('-3/2', '-1', '0', '1/10', '1/2', '1', '7/3'):
    for s in ('-1/2', '0', '1/3'):
        references = {
            'XPowGate': f'exp(i*pi*({t})*(({s})+1/2))*Rx(pi*({t}))',
            'ZPowGate': f'exp(i*pi*({t})*({s}))*P(pi*({t}))',
            'CZPowGate': f'exp(i*pi*({t})*({s}))*CP(pi*({t}))',
        }
        for name, reference in references.items():
            call = f'{name}(exponent={t},global_shift={s})'
            equal(call, reference)
            equal(f'controlled({call})', f'controlled({reference})')
            equal(f'{name}(global_shift={s},exponent={t})', call)
            equal(f'{name}({t},{s})', call)

for name, base in [('XPowGate', 'X'), ('ZPowGate', 'Z'), ('CZPowGate', 'CZ')]:
    equal(name+'()', base)
    equal(name+'(1/2)^2', base)
equal('XPowGate(exponent=1/2)', 'SX')
equal('XPowGate(exponent=3/10,global_shift=-1/2)', 'Rx(3*pi/10)')
equal('ZPowGate(exponent=1/4)', 'T')
equal('CZPowGate(exponent=1/2)', 'controlled(S)')

invalid = ['XPowGate(exponent=1,exponent=2)', 'ZPowGate(foo=1)',
           'CZPowGate(global_shift=0,1)', 'XPowGate(1,2,3)',
           'XPowGate(exponent=)', 'ZPowGate(global_shift=)',
           'XPowGate(dimension=3)', 'XPowGate(1,global_shift=0,global_shift=1)']
for source in invalid:
    result = calculate(source)
    assert result.returncode != 0, (source, result.stdout)
print(f'PASS: {checks} phase-sensitive power-gate identities and {len(invalid)} malformed calls.')
