"""Authored observation of original builder returns, without changing them."""
_qb008_captures = []
_qb008_original_builder = None
_qb008_builder_restored = False


def _qb008_observed_builder(n_qubits, depth):
    value = _qb008_original_builder(n_qubits, depth)
    _qb008_captures.append(dict(qubits=n_qubits, depth=depth, source=value))
    return value
