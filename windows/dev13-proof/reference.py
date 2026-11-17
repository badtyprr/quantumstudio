"""Fixed QB-012 cell proof, not a notebook runner. No network/provider calls."""
import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
from pathlib import Path
import sys

NOTEBOOK_SHA = 'aa019f44a5dbcda11cb7a2307a2ceeb019a86ad84bee9b0568be024c1b9838c1'
CELL_SHA = 'e275067a2d9d843207e49a9f27a4cb7ffc883d4e9362f3b2258f7221df49387e'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = args.source.read_bytes()
    if hashlib.sha256(data).hexdigest() != NOTEBOOK_SHA:
        raise ValueError('SOURCE_HASH_MISMATCH: refusing to execute altered source')
    cell = ''.join(json.loads(data)['cells'][5]['source'])
    if hashlib.sha256(cell.encode()).hexdigest() != CELL_SHA:
        raise ValueError('CELL_HASH_MISMATCH')
    import numpy as np
    from qiskit import QuantumCircuit, qasm2
    from qiskit.circuit.exceptions import CircuitError
    from qiskit.primitives import StatevectorSampler
    from qiskit.quantum_info import Statevector
    ns = {}
    exec(compile(cell, 'QB-012:cell-5', 'exec'), ns)
    circuit = ns['qiskit_circuit']
    state = Statevector.from_instruction(circuit)
    # Independent algebra: H|0>=(|0>+|1>)/sqrt(2); CX maps |01> to |11>.
    expected = np.array([1/math.sqrt(2), 0, 0, 1/math.sqrt(2)], dtype=complex)
    amplitude_error = float(np.max(np.abs(state.data - expected)))
    assert amplitude_error < 1e-12, amplitude_error
    measured = circuit.copy()
    measured.measure_all()  # Authored measurement harness; not source cell.
    counts = StatevectorSampler(seed=1731).run([measured], shots=4096).result()[0].data.meas.get_counts()
    assert sum(counts.values()) == 4096 and set(counts) <= {'00', '11'}, counts
    deviation = max(abs(counts.get(k, 0)/4096 - .5) for k in ['00', '11'])
    assert deviation < .04, deviation  # Fixed in advance; >5 binomial standard errors.
    # Bell is permutation-symmetric: an additional asymmetric witness is essential.
    witness = QuantumCircuit(2, 2)
    witness.x(0)
    witness.measure([0, 1], [1, 0])
    mapped = StatevectorSampler(seed=1731).run([witness], shots=32).result()[0].data.c.get_counts()
    assert mapped == {'10': 32}, mapped  # c1 receives q0, string is c1,c0.
    errors = []
    def rejects(name, expected_type, operation):
        try:
            operation()
        except expected_type as exc:
            errors.append(dict(case=name, type=type(exc).__name__, message=str(exc)))
        else:
            raise AssertionError(name + ' did not reject')
    rejects('qubit-out-of-range', CircuitError, lambda: QuantumCircuit(2).x(2))
    rejects('non-normalized-state', ValueError, lambda: Statevector([1/3, 2/3]).sample_counts(10))
    rejects('malformed-qasm', qasm2.QASM2ParseError, lambda: qasm2.loads('OPENQASM 2.0; qreg q[2]; invalid q[0];'))
    result = dict(status='passed', kind='development-reference-proof', execution='external CPython process; no QuantumStudio invocation',
                  python=sys.version, executable=sys.executable, platform=platform.platform(),
                  packages={d.metadata['Name']:d.version for d in importlib.metadata.distributions()},
                  source_sha256=NOTEBOOK_SHA, cell_index=5, cell_sha256=CELL_SHA,
                  source_revision='86787e1ba372facc224f925189755e69c479828b',
                  base='0fed41cb5637c578737278bf13f59590a56d6cf4',
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  state=[[float(z.real),float(z.imag)] for z in state.data],
                  expected_state=[[float(z.real),float(z.imag)] for z in expected],
                  amplitude_error=amplitude_error, shots=4096, seed=1731, counts=counts,
                  frequency_tolerance=.04, frequency_deviation=deviation,
                  ordering_witness=mapped, expected_errors=errors,
                  claims_excluded=['unchanged notebook execution','qBraid conversion graph','provider execution','QuantumStudio Python support'])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
