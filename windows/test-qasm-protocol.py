"""Check source and frozen compiler process contracts without a calculation worker."""
import json
import os
import subprocess
import sys
import importlib.util
from pathlib import Path

root = Path(__file__).resolve().parent.parent
commands = [[sys.executable, str(root/'windows/qasm-import.py')],
            [str(root/'dist/QuantumStudio/qasm-import/qasm-import.exe')]]
header = 'OPENQASM 3.0; include "stdgates.inc"; '
checks = 0

# Verify the opt-in branch-preserving unroller before exposing version-2 import.
spec = importlib.util.spec_from_file_location('adapter', root/'windows/qasm-import.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
original_branch = adapter.QasmVisitor._visit_branching_statement
for predicate in ['c==2', 'c!=2', 'c[1]', '!c[1]']:
    source = header+'qubit[2] q; bit[2] c; c=measure q; if('+predicate+') {reset q[0]; c[0]=measure q[0]; x q[1];} else {z q[1];}'
    module = adapter.pyqasm.loads(source)
    adapter.unroll_preserving_phase(module, {'x', 'z'}, preserve_branches=True)
    branch = module.unrolled_ast.statements[-1]
    assert isinstance(branch, adapter.ast.BranchingStatement)
    assert len(branch.if_block) == 3 and len(branch.else_block) == 1
    assert isinstance(branch.if_block[1], adapter.ast.QuantumMeasurementStatement)
    if predicate in ['c==2', 'c!=2']:
        assert branch.condition.lhs.name == 'c' and branch.condition.rhs.value == 2
        assert branch.condition.op.name == predicate[1:3]
    assert adapter.QasmVisitor._visit_branching_statement is original_branch
for predicate in ['c==d', 'c>1']:
    module = adapter.pyqasm.loads(header+'qubit q; bit[2] c; bit[2] d; if('+predicate+') x q;')
    adapter.unroll_preserving_phase(module, {'x'}, preserve_branches=True)
    branch=module.unrolled_ast.statements[-1]
    assert isinstance(branch,adapter.ast.BranchingStatement) and branch.condition.op.name==('==' if predicate=='c==d' else '>')
    assert adapter.QasmVisitor._visit_branching_statement is original_branch
print('PASS: 6 classical branch preservation checks.')

def run(command, source, expected=None, arguments=(), diagnostic=None):
    global checks
    data = source.encode('utf-8') if isinstance(source, str) else source
    # Reproduce a Windows locale that cannot write UTF-8 by default, even on
    # developer machines whose Python runtime enables UTF-8 mode globally.
    result = subprocess.run(command+list(arguments), input=data, capture_output=True, timeout=30,
                            env=dict(os.environ, PYTHONIOENCODING='cp1252'))
    stderr = result.stderr.decode('utf-8')
    if expected is None:
        assert result.returncode != 0 and not result.stdout and result.stderr, (command, result)
        if diagnostic is not None:
            assert stderr.strip() == diagnostic, (command, stderr)
    else:
        assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
        assert json.loads(result.stdout) == expected, result.stdout
    checks += 1

bell = {'Version': 1, 'Qubits': 2, 'Steps': [
    {'Gate': 'H', 'Angle': '', 'Wires': [0]},
    {'Gate': 'CNOT', 'Angle': '', 'Wires': [0, 1]}]}
source = header+'qubit[2] q; h q[0]; cx q[0],q[1];'
for command in commands:
    run(command, 'OPENQASM 2.0; include "qelib1.inc"; qreg q[1]; creg c[1]; if(c==0) x q[0]; measure q[0] -> c[0];',
        {'Version':2,'Qubits':1,'Registers':[{'Name':'c','Size':1}],'OutputBits':[0],
         'Steps':[{'Kind':'Branch','Mask':'1','Value':'0','WhenTrue':[{'Kind':'Gate','Expression':'X','Wires':[0]}],'WhenFalse':[]}, {'Kind':'Measure','Wires':[0],'ClassicalBit':0}]}, arguments=['--classical'])
    measure = {'Kind':'Measure','Wires':[0],'ClassicalBit':3}
    run(command, header+'qubit q; bit[4] c; c[3]=measure q;',
        {'Version':2,'Qubits':1,'Registers':[{'Name':'c','Size':4}],'OutputBits':[3,2,1,0],'Steps':[measure]}, arguments=['--classical'])
    run(command, header+'qubit q; bit[2] c; if(c==2) {x q;} else {reset q;}',
        {'Version':2,'Qubits':1,'Registers':[{'Name':'c','Size':2}],'OutputBits':[1,0],
         'Steps':[{'Kind':'Branch','Mask':'3','Value':'2','WhenTrue':[{'Kind':'Gate','Expression':'X','Wires':[0]}],'WhenFalse':[{'Kind':'Reset','Wires':[0]}]}]}, arguments=['--classical'])
    run(command, header+'qubit q; measure q;',
        {'Version':2,'Qubits':1,'Registers':[],'OutputBits':[],'Steps':[{'Kind':'Channel','Expression':'phase_damping(1)','Wires':[0]}]}, arguments=['--classical'])
    for body in ['qubit q; bit c=2;', 'qubit q; bit c; c=-1;', 'qubit q; bit[65] c;',
                 'qubit q; bit[2] c; if(c>4) x q;', 'qubit q; bit[2] c; bit[3] d; if(c==d) x q;']:
        run(command, header+body, arguments=['--classical'])
    run(command, source, bell)
    run(command, b'\xef\xbb\xbf'+source.encode('utf-8'), bell)
    run(command, source+' // Unicode comment: \u03c0', bell)
    run(command, source+' '*(262144-len(source.encode('utf-8'))), bell)
    run(command, 'OPENQASM 2.0; include "qelib1.inc"; qreg q[2]; h q[0]; cx q[0],q[1];', bell)
    run(command, header+'qubit q; reset q; bit b; b=measure q;',
        {'Version': 1, 'Qubits': 1, 'Steps': [
            {'Gate': 'Reset', 'Angle': '', 'Wires': [0]},
            {'Gate': 'Measure', 'Angle': '', 'Wires': [0]}]})
    run(command, header+'qubit[2] q; ctrl @ t q[0],q[1];',
        {'Version': 1, 'Qubits': 2, 'Steps': [{'Gate': 'CP', 'Angle': '0.78539816339744828', 'Wires': [0,1]}]})
    for count in (65, 512):
        run(command, header+f'qubit q; for int i in [0:{count-1}] {{x q;}}',
            {'Version': 1, 'Qubits': 1, 'Steps': [{'Gate': 'X', 'Angle': '', 'Wires': [0]}]*count})
    for width in (9, 10, 11, 25):
        run(command, header+f'qubit[{width}] q; x q[{width-1}];',
            {'Version': 1, 'Qubits': width, 'Steps': [{'Gate': 'X', 'Angle': '', 'Wires': [width-1]}]})
    for invalid in [source+' '*(262145-len(source)),
                    b'\xef\xbb\xbf'+source.encode()+b' '*(262145-len(source)-3),
                    b'\xc3\x28', header+'include "private.inc"; qubit q;',
                    header+'qubit[26] q;', header+'qubit q; for int i in [0:512] {x q;}',
                    header+'qubit[2] q; bit b; b=measure q[0]; if(b) x q[1];',
                    header+'qubit q; delay[10ns] q;']:
        run(command, invalid)
    run(command, source, arguments=['--unknown-option'])
    run(command, header+'qubit[26] q;',
        diagnostic='The circuit editor currently supports 1–25 qubits.')
print(f'PASS: {checks} source/frozen OpenQASM process checks.')

# The termination dispatch adapter must not leak into subsequent imports.
original_map=adapter.QasmVisitor._construct_visit_map
for source in [header+'bit c;end;c=1;', header+'bit c;end;missing q;']:
    try:
        adapter.convert(source,classical=True)
    except Exception:
        assert 'missing' in source
    else:
        assert 'missing' not in source
    assert adapter.QasmVisitor._construct_visit_map is original_map
print('PASS: 2 termination compiler-hook restoration checks.')
