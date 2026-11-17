"""Authored GHZ-state witness; preserves the source's unconjugated comparison."""
import json
import math
from pathlib import Path

TOLERANCE = 1e-6

def verify_state(values, expected):
    values = [complex(x) for x in values]
    if len(values) != len(expected) or not all(math.isfinite(x.real) and math.isfinite(x.imag) for x in values):
        raise AssertionError('STATE_SHAPE_OR_FINITE')
    norm = sum(abs(x)**2 for x in values)
    overlap = sum(a.conjugate()*b for a, b in zip(expected, values))
    if abs(norm-1) > TOLERANCE or abs(abs(overlap)-1) > TOLERANCE:
        raise AssertionError('STATE_FIDELITY')
    phase = overlap / abs(overlap)
    residual = max(abs(value-phase*target) for value, target in zip(values, expected))
    if residual > TOLERANCE:
        raise AssertionError('STATE_RESIDUAL')
    return dict(norm=norm, overlap_abs=abs(overlap), residual=residual,
                vector=[[x.real, x.imag] for x in values])

expected = [0j] * 16
expected[0] = expected[-1] = 1/math.sqrt(2)
results = {
    'cirq_lowering': verify_state(cirq_sim.state_vector(main_loaded), expected),
    'qir_lowering': verify_state(pyq_sim.state_vector(squin_mod), expected),
    'direct_squin': verify_state(sim.state_vector(ghz, args=(4,)), expected),
}

# These are oracle controls, not additional SDK executions. They expose both
# false negatives and false positives of an unconjugated complex dot product.
complex_state = [1/math.sqrt(2), 1j/math.sqrt(2)]
verify_state(complex_state, complex_state)
verify_state([1j*x for x in complex_state], complex_state)
try:
    verify_state([x.conjugate() for x in complex_state], complex_state)
except AssertionError:
    rejected_orthogonal = True
else:
    raise AssertionError('ORACLE_ACCEPTED_ORTHOGONAL_STATE')
report = dict(accepted=True, authored_rerun_routes=results, tolerance=TOLERANCE,
              oracle_complex_controls=3, original_dot_product_unchanged=True,
              scope='authored re-execution of three four-qubit GHZ routes; source outputs audited separately; no general Squin or wire-order acceptance')
Path('qb018-state-evidence.json').write_bytes((json.dumps(report, indent=2)+'\n').encode())
print(json.dumps(report))
