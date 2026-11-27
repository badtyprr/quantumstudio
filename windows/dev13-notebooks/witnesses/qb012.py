"""Compare both converted operators with H on qubit zero followed by controlled X."""
import json
import numpy as np


def verify(first, second):
    # Columns are the images of 00, 01, 10 and 11 in Braket basis order.
    expected = np.array([[1, 0, 1, 0], [0, 1, 0, 1],
                         [0, 1, 0, -1], [1, 0, -1, 0]]) / np.sqrt(2)
    errors = []
    for operator in (first, second):
        if operator.shape != expected.shape:
            raise ValueError("Expected a two-qubit operator")
        phase = np.vdot(expected, operator) / 4
        error = float(np.max(np.abs(operator - phase * expected)))
        if not np.isclose(abs(phase), 1, rtol=0, atol=1e-12) or not error <= 1e-12:
            raise ValueError("Conversion changed the Bell-preparation operator")
        errors.append(error)
    return errors


if __name__ == "__main__":
    errors = verify(_qb012_first_operator, braket_circuit.to_unitary())
    path = graph.find_shortest_conversion_path("qiskit", "braket")
    if path != [conversion.convert]:
        raise ValueError("The graph did not select the notebook's custom direct edge")
    _qb012_logger.removeHandler(_qb012_handler)
    _qb012_handler.close()
    routes = []
    prefix = "Successfully transpiled using conversions: "
    for log in (_qb012_first_log, _qb012_routes.getvalue()):
        successful = [line[len(prefix):] for line in log.splitlines() if line.startswith(prefix)]
        if not successful:
            raise ValueError("No successful route reported by the transpiler")
        routes.append(successful[-1])
    if routes[1] != "qiskit -> braket":
        raise ValueError("The custom direct conversion fell back to another route")
    print(json.dumps(dict(accepted=True, operator_max_errors=errors, routes=routes), allow_nan=False))
