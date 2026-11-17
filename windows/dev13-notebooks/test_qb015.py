"""Guard the distinction between LLVM verification and valid result references."""
import unittest
import json
from execution import witness_streams
from witnesses.qb015 import output_diagnostic


class WitnessStreamTests(unittest.TestCase):
    def test_interleaved_warning_does_not_corrupt_json(self):
        outputs = [dict(output_type='stream', name=name, text=text) for name, text in
                   [('stdout', '{"accepted":'), ('stderr', 'SDK warning\n'), ('stdout', 'true}')]]
        self.assertEqual(witness_streams(outputs), ({'accepted': True}, 'SDK warning\n'))

    def test_stderr_cannot_supply_acceptance(self):
        with self.assertRaises(json.JSONDecodeError):
            witness_streams([dict(output_type='stream', name='stderr', text='{"accepted":true}')])

    def test_non_json_stdout_still_fails(self):
        with self.assertRaises(json.JSONDecodeError):
            witness_streams([dict(output_type='stream', name='stdout', text='warning\n{"accepted":true}')])


class ResultReferenceTests(unittest.TestCase):
    def test_out_of_range_result_is_visible(self):
        text = ('attributes #0 = { "required_num_results"="1" }\n'
                'call void @__quantum__rt__result_record_output(ptr null, ptr null)\n'
                'call void @__quantum__rt__result_record_output(ptr inttoptr (i64 1 to ptr), ptr null)\n')
        result = output_diagnostic(text)
        self.assertEqual(result['recorded_result_ids'], [0, 1])
        self.assertEqual(result['out_of_range'], [1])

    def test_in_range_is_distinct_from_known_failure(self):
        text = ('attributes #0 = { "required_num_results"="2" }\n'
                'call void @__quantum__rt__result_record_output(ptr inttoptr (i64 1 to ptr), ptr null)\n')
        self.assertEqual(output_diagnostic(text)['out_of_range'], [])

    def test_unknown_scalar_call_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'UNRECOGNIZED_OUTPUT_CALL'):
            output_diagnostic('"required_num_results"="1"\n'
                'call void @__quantum__rt__result_record_output(ptr %dynamic, ptr null)\n')


if __name__ == '__main__':
    unittest.main()
