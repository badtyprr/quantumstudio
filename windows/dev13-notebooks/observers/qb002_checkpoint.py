"""Read serialized intermediate states; never replace original SDK methods."""
import json as _qb002_json
from pathlib import Path as _qb002_Path

_qb002_snapshots = globals().setdefault('_qb002_snapshots', [])
_qb002_stages = (10, 13, 20, 25)
if len(_qb002_snapshots) >= len(_qb002_stages):
    raise AssertionError('UNEXPECTED_QB002_CHECKPOINT')
_qb002_stage = _qb002_stages[len(_qb002_snapshots)]
_qb002_row = dict(after_original_cell=_qb002_stage, qubits=module.num_qubits,
                 classical_bits=module.num_clbits, qasm=dumps(module))
_qb002_Path(f'after-{_qb002_stage}.qasm').write_bytes(_qb002_row['qasm'].encode())
if _qb002_stage >= 20:
    _qb002_row.update(new_qasm=dumps(new_module), distinct_objects=module is not new_module)
    _qb002_Path(f'new-after-{_qb002_stage}.qasm').write_bytes(_qb002_row['new_qasm'].encode())
_qb002_snapshots.append(_qb002_row)
_qb002_Path('transformations.json').write_bytes((_qb002_json.dumps(_qb002_snapshots, indent=2)+'\n').encode())
