# The notebook reuses braket_circuit for the second conversion.
_qb012_first_operator = braket_circuit.to_unitary().copy()
_qb012_first_log = _qb012_routes.getvalue()
_qb012_routes.seek(0)
_qb012_routes.truncate()
