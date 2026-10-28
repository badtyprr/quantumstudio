"""Exercise authored array documents through canonical save/load, export and workers."""
import argparse
import base64
import copy
import json
import os
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--adapter', type=Path, required=True)
parser.add_argument('--worker', type=Path, required=True)
args = parser.parse_args()
checks = 0
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(args.worker.resolve().parent / 'data'))

def integer(value):
    return dict(Kind='IntegerConstant', Signedness='Signed', Width=0, Value=str(value & ((1 << 64) - 1)))

def selection(*indices, array=0):
    return dict(Array=array, Indices=[integer(i) if isinstance(i, int) else i for i in indices], Source='model.qasm:3:2')

def element(*indices):
    return dict(Kind='IntegerArrayElement', Signedness='Signed', Width=0, Selection=selection(*indices))

def store(value, *indices):
    return dict(Kind='StoreInteger', ArrayTarget=selection(*indices), IntegerValue=integer(value))

def observe(value, expected):
    return dict(Kind='Assign', Wires=[0], ClassicalValue=dict(Kind='IntegerCompare', Operator='Equal', Left=value, Right=integer(expected)))

base = dict(Version=15, Qubits=0, Registers=[dict(Name='c', Size=1)], OutputBits=[0], LoopConditionBudget=1000000,
            Variables=[dict(Name='cell'+str(i), Signedness='Signed', Width=0) for i in range(6)], NumericVariables=[],
            Arrays=[dict(Name='values', Base=0, Dimensions=[2, 3], Signedness='Signed', Width=0)], Steps=[])

def run(document, expected=None, invalid=False, runtime_error=False):
    global checks
    result = subprocess.run([str(args.adapter.resolve())], input=json.dumps(document).encode(), capture_output=True, timeout=30)
    checks += 1
    if invalid:
        assert result.returncode and not result.stdout, result.stdout
        return
    assert result.returncode == 0, result.stderr
    encoded = json.loads(result.stdout)
    assert 'array[int[64], 2, 3] a0;' in encoded['source']
    for exact in (True, False):
        process = subprocess.run([str(args.worker.resolve()), '--exact-circuit' if exact else '--sample'],
                                 input=base64.b64decode(encoded['exact' if exact else 'sampled']), capture_output=True, env=env, timeout=30)
        checks += 1
        if runtime_error:
            assert process.returncode and not process.stdout, process.stdout
        else:
            assert process.returncode == 0, process.stderr
            payload = json.loads(process.stdout)
            values = payload['probabilities' if exact else 'counts']
            assert values == {expected: '1' if exact else 10000}, values

for indices in ((0, 0), (1, 2), (-1, -1), (-2, -3)):
    doc = copy.deepcopy(base)
    doc['Steps'] = [store(7, *indices), observe(element(*indices), 7)]
    run(doc, '1')

doc = copy.deepcopy(base)
doc['Steps'] = [store(2, 0, 0), dict(Kind='StoreInteger', ArrayTarget=selection(1, element(0, 0)), IntegerValue=integer(7)), observe(element(1, 2), 7)]
run(doc, '1')
doc['Steps'] = [observe(element(0, 0), 0)]
run(doc, runtime_error=True)
for indices in ((2, 0), (-3, 0), (0, 3), (0, -4)):
    doc = copy.deepcopy(base);doc['Steps'] = [store(1, *indices)]
    run(doc, runtime_error=True)

for mutate in (
    lambda d: d.update(Version=14),
    lambda d: d['Arrays'][0].update(Base=1),
    lambda d: d['Arrays'][0].update(Dimensions=[7]),
    lambda d: d['Arrays'][0].update(Dimensions=[]),
    lambda d: d['Arrays'][0].update(Dimensions=[1]*8),
    lambda d: d['Arrays'][0].update(Width=8),
    lambda d: d['Arrays'][0].update(NumericKind='Float'),
    lambda d: d['Arrays'][0].update(Name='cell0'),
    lambda d: d['Arrays'].append(dict(Name='overlap', Base=3, Dimensions=[3], Signedness='Signed', Width=0)),
    lambda d: d['Steps'][0]['ArrayTarget'].update(Array=1),
    lambda d: d['Steps'][0]['ArrayTarget'].update(Indices=[integer(0)]),
    lambda d: d['Steps'][0]['ArrayTarget'].update(Source='x'*513),
    lambda d: d['Steps'][0]['ArrayTarget'].update(Source='\0'),
    lambda d: d['Steps'][0].update(VariableSlot=0),
    lambda d: d['Steps'][0].update(Kind='ClearInteger', IntegerValue=None),
):
    doc = copy.deepcopy(base);doc['Steps'] = [store(7, 0, 0)]
    mutate(doc);run(doc, invalid=True)

print(f'PASS: {checks} runtime array model checks.')
