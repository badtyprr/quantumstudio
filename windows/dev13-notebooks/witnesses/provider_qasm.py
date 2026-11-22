"""Check the source header diagnostic and the Bell state after a one-line correction."""
import json
import math

from braket.devices import LocalSimulator
from pyqasm import loads
from pyqasm.exceptions import ValidationError
from qbraid import transpile


def verify(source):
    try:
        loads(source)
    except ValidationError as error:
        diagnostic = str(error)
        if "unsupported version '2'" not in diagnostic:
            raise
    else:
        raise AssertionError("Expected the pinned source header to be rejected")

    original_header = "OPENQASM 2;"
    if source.count(original_header) != 1 or not source.lstrip().startswith(original_header):
        raise AssertionError("Expected a single leading OpenQASM 2 header")
    corrected = source.replace(original_header, "OPENQASM 3.0;", 1)
    circuit = transpile(corrected, "braket")
    simulator = LocalSimulator("braket_sv")
    counts = dict(simulator.run(circuit, shots=100).result().measurement_counts)
    if set(counts) != {"00", "11"} or sum(counts.values()) != 100:
        raise AssertionError(counts)
    circuit.state_vector()
    vector = simulator.run(circuit, shots=0).result().values[0]
    expected = (math.sqrt(0.5), 0, 0, math.sqrt(0.5))
    if len(vector) != 4:
        raise AssertionError("Expected a two-qubit state")
    errors = [float(abs(value - target)) for value, target in zip(vector, expected)]
    if not all(math.isfinite(error) for error in errors):
        raise AssertionError("Expected finite Bell-state amplitudes")
    residual = max(errors)
    if not residual <= 1e-12:
        raise AssertionError(residual)
    return dict(accepted=True, original_diagnostic=diagnostic, corrected_header="OPENQASM 3.0;",
                backend="braket_sv", shots=100, counts=counts, state_residual=residual)


if __name__ == "__main__":
    print(json.dumps(verify(program), allow_nan=False))
