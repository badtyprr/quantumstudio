"""Mutation controls against retained SDK snapshots of the original notebook."""
import json
import math
from pathlib import Path
import unittest
from witnesses.qb002 import audit, expected_operations, unitary_state


class TransformationWitnessTests(unittest.TestCase):
    def snapshots(self):
        return json.loads((Path(__file__).parent/'fixtures/qb002-transformations.json').read_text(encoding='utf-8'))

    def test_captured_chain(self):
        result = audit(self.snapshots())
        self.assertEqual(result['actual_remaining_qubits'], 7)
        self.assertFalse(result['source_claim_six_qubits'])

    def test_six_qubit_prose_cannot_override_actual_program(self):
        snapshots = self.snapshots()
        snapshots[1]['qubits'] = 6
        with self.assertRaisesRegex(AssertionError, 'RESOURCE_METADATA'):
            audit(snapshots)

    def test_lost_range_endpoint_rejected(self):
        snapshots = self.snapshots()
        snapshots[0]['qasm'] = snapshots[0]['qasm'].replace('rx(0.5) q[6];\n', '')
        with self.assertRaisesRegex(AssertionError, 'TRANSFORMATION_OPERATIONS'):
            audit(snapshots)

    def test_measurement_destinations_must_not_reverse(self):
        snapshots = self.snapshots()
        snapshots[3]['qasm'] = snapshots[3]['qasm'].replace('c[0] = measure q[6]', 'c[6] = measure q[6]')
        with self.assertRaisesRegex(AssertionError, 'TRANSFORMATION_OPERATIONS'):
            audit(snapshots)

    def test_reversal_must_not_mutate_copy(self):
        snapshots = self.snapshots()
        snapshots[3]['new_qasm'] = snapshots[3]['new_qasm'].replace('h q[0];', 'h q[6];')
        with self.assertRaisesRegex(AssertionError, 'COPY_ISOLATION_OR_MEASUREMENT_REMOVAL'):
            audit(snapshots)

    def test_range_endpoint_is_observable_in_full_state(self):
        full = unitary_state(expected_operations())
        missing = unitary_state([op for op in expected_operations() if op != ('rx', (6,), (0.5,))])
        self.assertAlmostEqual(abs(full[64]), math.sin(.25)*math.cos(.25)**3/2)
        self.assertEqual(missing[64], 0)
        self.assertEqual(full[3], 0)


if __name__ == '__main__':
    unittest.main()
