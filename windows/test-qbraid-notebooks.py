"""Audit downloaded, pinned qBraid notebooks without executing their Python.

Usage: python test-qbraid-notebooks.py SNAPSHOT_DIRECTORY
Snapshot paths/hashes are recorded in docs/qbraid-notebook-audit.json.
"""
import ast
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
snapshot = Path(sys.argv[1])
audit = json.loads((root/'docs/qbraid-notebook-audit.json').read_text(encoding='utf-8'))
spec = importlib.util.spec_from_file_location('adapter', root/'windows/qasm-import.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
passed = rejected = 0
for record in audit['reviewed']:
    data = (snapshot/record['path']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == record['sha256'], record['path']
    bell = record['path'] in ('qBraid-SDK/bell_circuit_examples.ipynb','Provider-Jobs/qbraid_runtime_rigetti_provider.ipynb')
    pure_bell = record['path'] in ('Provider-Jobs/qbraid_runtime_ionq_provider.ipynb','Provider-Jobs/qbraid_runtime_oqc_provider.ipynb')
    ghz = record['path'] == 'qBraid-QIR/qbraid_qir_sim_batch_jobs.ipynb'
    if not record['path'].startswith('PyQASM-Examples/') and not bell and not ghz and not pure_bell:
        continue
    for cell in json.loads(data)['cells']:
        if cell['cell_type'] != 'code':
            continue
        try:
            tree = ast.parse(''.join(cell['source']))
        except SyntaxError:  # Notebook magic is not Python or QASM.
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str) or 'OPENQASM' not in node.value:
                continue
            if not record['path'].endswith('deutsch_josza_unroll.ipynb') and not bell and not ghz and not pure_bell:
                try:
                    adapter.convert(node.value)
                except ValueError as error:
                    assert '1–8 qubits' in str(error), error
                    rejected += 1
                    continue
                raise AssertionError('Expected documented capacity gap: '+record['path'])
            circuit = adapter.convert(node.value)
            if ghz:
                assert circuit['Qubits'] in (3,4) and len(circuit['Steps'])==2*circuit['Qubits']
            else:
                assert (circuit['Qubits'],len(circuit['Steps'])) == ((2,2) if pure_bell else (2,4) if bell else (5,18))
            value = '|'+'0'*circuit['Qubits']+'>'
            for step in circuit['Steps']:
                wires = '['+','.join(map(str, step['Wires']))+']'
                if step['Gate'] == 'Measure':
                    value = f'dephase({value},{wires})'
                else:
                    assert not step['Angle']
                    value = f'apply({step["Gate"]},{value},{wires})'
            # Balanced parity oracle: data register is all ones, ancilla stays |->.
            expected = '(density(|00>)+density(|11>))/2' if bell else 'density((|11110>-|11111>)/sqrt(2))'
            if ghz:
                expected = '(density(|'+'0'*circuit['Qubits']+'>)+density(|'+'1'*circuit['Qubits']+'>))/2'
            if pure_bell:
                value='density('+value+')';expected='density((|00>+|11>)/sqrt(2))'
            expression = f'quantum:norm(vec(({value})-({expected})))'
            result = subprocess.run([str(root/'dist/QuantumStudio/quantum-worker.exe'),'--json','--approx'],
                                    input=expression,encoding='utf-8',capture_output=True,timeout=60)
            assert result.returncode == 0, result.stderr
            assert abs(float(json.loads(result.stdout)['text'].replace('\u2212','-'))) < 1e-12, result.stdout
            passed += 1
assert (passed,rejected) == (7,2), (passed,rejected)
print(f'PASS: seven pinned Deutsch-Jozsa/Bell/GHZ notebook density results; two ten-qubit capacity gaps reproduced; {len(audit["reviewed"])} notebook hashes verified.')
