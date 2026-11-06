import unittest
from qb013_output_audit import parse_original_samples, audit_original_samples

def printed(rows):
    return '['+'\n '.join('['+' '.join('True' if x else 'False' for x in row)+']' for row in rows)+']\n'

class OriginalSampleTests(unittest.TestCase):
    def test_complete_raw_rows_retained(self):
        rows=[[0,0],[1,1]]*5
        result=audit_original_samples(printed(rows),[0,1])
        self.assertEqual(result['original_rows'],rows)
        self.assertEqual(result['logical_rows'],rows)
        self.assertFalse(result['balance_verified'])
        self.assertFalse(result['coherence_verified'])
    def test_single_allowed_outcome_valid(self):
        for row in ([0,0],[1,1]):
            self.assertEqual(audit_original_samples(printed([row]*10),[1,0])['shots'],10)
    def test_row_count_and_width_not_truncated(self):
        for rows in ([[0,0]]*9,[[0,0]]*11,[[0]]*10,[[0,0,0]]*10):
            with self.assertRaisesRegex(ValueError,'ORIGINAL_SAMPLE_FORMAT'):parse_original_samples(printed(rows))
    def test_extra_or_malformed_tokens_rejected(self):
        good=printed([[0,0]]*10)
        for text in (good+'extra', 'prefix'+good,good+good,good.replace('False','0'),
                     good.replace('False','false'),good.replace('False False','False, False'),
                     good[:-2], '[]',good.replace('[False False]','... ',1)):
            with self.assertRaisesRegex(ValueError,'ORIGINAL_SAMPLE_FORMAT'):parse_original_samples(text)
    def test_forbidden_support_not_symmetry_mapping_proof(self):
        for mapping in ([0,1],[1,0]):
            with self.assertRaisesRegex(ValueError,'FORBIDDEN_OUTCOME'):
                audit_original_samples(printed([[0,0]]*9+[[0,1]]),mapping)
    def test_mapping_must_be_explicit_bijection(self):
        for mapping in (None,[],[0,0],[1,1],[0,2],[False,True],[0],[0,1,2]):
            with self.assertRaisesRegex(ValueError,'UNPROVEN_MEASUREMENT_BIJECTION'):
                audit_original_samples(printed([[0,0]]*10),mapping)



class ScopedConversionTests(unittest.TestCase):
    def observer(self, edges, snapshot=lambda value: value, known_functions=None, checkpoint=None):
        import importlib.util
        from pathlib import Path
        spec=importlib.util.spec_from_file_location('qb013_observer_test',Path(__file__).parent/'observers/qb013.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module.ScopedConversions(edges,snapshot,known_functions,checkpoint)
    def edge(self, fn):
        class Edge:
            source='qiskit';target='cirq'
            def __init__(self):self._conversion_func=fn
            def convert(self,*args,**kwargs):return self._conversion_func(*args,**kwargs)
        return Edge()
    def test_cached_bound_method_and_argument_result_identity(self):
        calls=[];value=object();result=object()
        def fn(*args,**kwargs):calls.append((args,kwargs));return result
        edge=self.edge(fn);cached=edge.convert;capture=self.observer([edge,edge],lambda v:id(v))
        with capture:
            self.assertIs(cached(value,flag=value),result)
        capture.require_complete()
        self.assertEqual(len(calls),1);self.assertIs(calls[0][0][0],value)
        self.assertIs(calls[0][1]['flag'],value);self.assertIs(edge._conversion_func,fn)
        self.assertEqual(len(capture.records),1)
    def test_capture_error_does_not_trigger_conversion_fallback(self):
        result=object();calls=[]
        def fn(value):calls.append(value);return result
        def broken(value):raise RuntimeError('capture only')
        edge=self.edge(fn);capture=self.observer([edge],broken)
        with capture:self.assertIs(edge.convert('source'),result)
        self.assertEqual(calls,['source']);self.assertIs(edge._conversion_func,fn)
        self.assertEqual(capture.records[0]['state'],'succeeded')
        with self.assertRaisesRegex(ValueError,'AUTHORED_CAPTURE_FAILED'):capture.require_complete()
    def test_function_identity_and_default_argument_shape_are_observed(self):
        def converter(program, **kwargs):return program
        edge=self.edge(converter);capture=self.observer([edge],known_functions={'stimcirq':converter})
        with capture:
            self.assertEqual(edge.convert('a'),'a')
            self.assertEqual(edge.convert('b',qubit_to_index_dict={0:1}),'b')
        capture.require_complete()
        self.assertEqual([r['ordinal'] for r in capture.records],[0,1])
        self.assertEqual(capture.records[0]['function_identities'],['stimcirq'])
        self.assertTrue(capture.records[0]['single_program_positional_call'])
        self.assertEqual(capture.records[1]['keyword_names'],['qubit_to_index_dict'])
        self.assertFalse(capture.records[1]['single_program_positional_call'])
    def test_same_named_different_function_does_not_prove_identity(self):
        def converter(program):return program
        def substitute(program):return program
        substitute.__name__=converter.__name__;substitute.__qualname__=converter.__qualname__
        edge=self.edge(substitute);capture=self.observer([edge],known_functions={'stimcirq':converter})
        with capture:self.assertEqual(edge.convert('a'),'a')
        capture.require_complete()
        self.assertEqual(capture.records[0]['function_identities'],[])
    def test_checkpoints_surround_original_and_record_restoration(self):
        from copy import deepcopy
        saved=[]
        def converter(value):
            self.assertEqual(saved[-1]['records'][0]['state'],'running')
            return value
        edge=self.edge(converter);capture=self.observer([edge])
        capture.checkpoint=lambda:saved.append(deepcopy(dict(records=capture.records,active=capture.active)))
        with capture:self.assertEqual(edge.convert('source'),'source')
        capture.require_complete()
        self.assertEqual([row['records'][0]['state'] for row in saved],['running','succeeded','succeeded'])
        self.assertFalse(saved[-1]['active'])
        self.assertIs(edge._conversion_func,converter)
    def test_checkpoint_failure_never_replaces_original_result_or_error(self):
        primary=RuntimeError('primary')
        for fail in (False,True):
            def converter(value):
                if fail:raise primary
                return value
            def broken():raise OSError('write failed')
            edge=self.edge(converter);capture=self.observer([edge],checkpoint=broken)
            if fail:
                with self.assertRaises(RuntimeError) as caught:
                    with capture:edge.convert('source')
                self.assertIs(caught.exception,primary)
                self.assertEqual(capture.records[0]['error']['message'],'primary')
            else:
                with capture:self.assertEqual(edge.convert('source'),'source')
            self.assertIs(edge._conversion_func,converter)
            self.assertTrue(all(d['stage']=='checkpoint' for d in capture.diagnostics))
            with self.assertRaisesRegex(ValueError,'AUTHORED_CAPTURE_FAILED'):capture.require_complete()
    def test_original_exception_identity_and_restoration(self):
        for error in (RuntimeError('conversion'),KeyboardInterrupt()):
            def fn(value):raise error
            edge=self.edge(fn);capture=self.observer([edge])
            try:
                with capture:edge.convert('source')
            except BaseException as observed:self.assertIs(observed,error)
            else:self.fail('Original exception swallowed')
            self.assertIs(edge._conversion_func,fn);capture.require_complete()
            self.assertEqual(capture.records[0]['state'],'failed')
    def test_unexpected_replacement_preserved_and_reported(self):
        fn=lambda v:v;replacement=lambda v:None
        edge=self.edge(fn);capture=self.observer([edge])
        with capture:edge._conversion_func=replacement
        self.assertIs(edge._conversion_func,replacement)
        with self.assertRaisesRegex(ValueError,'AUTHORED_CAPTURE_FAILED'):capture.require_complete()
    def test_partial_installation_restores_prior_edges(self):
        fn=lambda v:v;first=self.edge(fn);second=self.edge(None)
        capture=self.observer([first,second])
        with self.assertRaisesRegex(ValueError,'NONCALLABLE_CONVERSION'):
            with capture:pass
        self.assertIs(first._conversion_func,fn);self.assertFalse(capture.active)
    def test_nested_use_rejected_without_disrupting_outer_scope(self):
        edge=self.edge(lambda v:v);capture=self.observer([edge])
        with capture:
            with self.assertRaisesRegex(ValueError,'OBSERVER_ALREADY_USED'):
                with capture:pass
            self.assertTrue(capture.active);self.assertEqual(edge.convert(3),3)
        capture.require_complete()



class CaptureJournalTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'capture.json'
        self.journal=NormalizedParserTests().module().CaptureJournal(self.path)
    def test_updates_complete_unicode_json_and_monotone_revision(self):
        import json
        for number in (1,2):
            self.journal.write(dict(state='running' if number==1 else 'failed',detail='λ 空間'))
            value=json.loads(self.path.read_bytes())
            self.assertEqual(value['revision'],number)
            self.assertEqual(value['payload']['detail'],'λ 空間')
        self.assertEqual(list(self.path.parent.glob('*.tmp')),[])
    def test_serialization_failure_preserves_previous_checkpoint(self):
        self.journal.write(dict(state='running'));before=self.path.read_bytes()
        for value in (float('nan'),object()):
            with self.assertRaises((TypeError,ValueError)):self.journal.write(dict(value=value))
            self.assertEqual(self.path.read_bytes(),before)
            self.assertEqual(self.journal.revision,1)
    def test_replace_failure_preserves_checkpoint_and_temporary_evidence(self):
        from unittest.mock import patch
        self.journal.write(dict(state='running'));before=self.path.read_bytes()
        with patch('os.replace',side_effect=OSError('blocked')):
            with self.assertRaises(OSError):self.journal.write(dict(state='failed'))
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(self.journal.revision,1)
        self.assertEqual(len(list(self.path.parent.glob('*.tmp'))),1)
    def test_preexisting_or_changed_file_never_overwritten(self):
        self.path.write_text('foreign')
        with self.assertRaisesRegex(ValueError,'CAPTURE_PATH_ALREADY_EXISTS'):self.journal.write({})
        with self.assertRaisesRegex(ValueError,'FRESH_CAPTURE_PATH_REQUIRED'):
            type(self.journal)(self.path)
        self.assertEqual(self.path.read_text(),'foreign')
        other=type(self.journal)(self.path.with_name('other.json'));other.write({})
        other.path.write_text('changed')
        with self.assertRaisesRegex(ValueError,'CAPTURE_FILE_CHANGED_EXTERNALLY'):other.write({})
        self.assertEqual(other.path.read_text(),'changed')


class ReviewedInputsTests(unittest.TestCase):
    def test_exact_reviewed_reference_bytes_and_cases(self):
        import hashlib
        from pathlib import Path
        import qb013_reference
        raw=(Path(__file__).parent/'qb013_reference.py').read_bytes()
        self.assertEqual(hashlib.sha256(raw[:1937]).hexdigest(),'121ad49fc591583f739abbe9fe88cf9ea11404403bff1e8f9c3c6a7b82210312')
        self.assertEqual(len(qb013_reference.cases()),14)
    def test_profile_binds_exact_76_package_lock(self):
        import hashlib,json,re
        from pathlib import Path
        root=Path(__file__).parent
        raw=(root/'stim-requirements.lock').read_bytes()
        profile=json.loads((root/'profiles/stim-win-py312.json').read_bytes())
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'77ca89424d928dfae1267975702c0a524f385724b0aea7b5fc6c3e5868b21a44')
        self.assertEqual(profile['lock_sha256'],hashlib.sha256(raw).hexdigest())
        lines=raw.decode().splitlines();self.assertEqual(len(lines),76)
        self.assertTrue(all(re.fullmatch(r'[A-Za-z0-9_.-]+==[^ ]+ --hash=sha256:[0-9a-f]{64}',line) for line in lines))
        self.assertTrue(profile['offline_only']);self.assertTrue(profile['exact_packages'])
        self.assertEqual(profile['python'],'3.12.10')



class SourceDispositionTests(unittest.TestCase):
    def fixture(self):
        import copy,hashlib,json
        from qb013_output_audit import ORIGINAL_CODE_INDICES
        cells=[dict(cell_type='code' if i in ORIGINAL_CODE_INDICES else 'markdown',source='original '+str(i),outputs=[]) for i in range(24)]
        raw=json.dumps(dict(cells=cells)).encode()
        ledger=[dict(index=i,type=c['cell_type'],sha256=hashlib.sha256(c['source'].encode()).hexdigest()) for i,c in enumerate(cells)]
        records=[dict(index=i,original_index=i,authored_role=None,type=c['cell_type'],source_sha256=ledger[i]['sha256'],state='succeeded' if i in ORIGINAL_CODE_INDICES else 'not_executable') for i,c in enumerate(cells)]
        executed=dict(cells=copy.deepcopy(cells))
        executed['cells'][22]['outputs']=[dict(output_type='stream',name='stdout',text=printed([[0,0]]*10))]
        return raw,executed,records,dict(source=dict(sha256=hashlib.sha256(raw).hexdigest(),cells=ledger))
    def audit(self,fixture):
        from qb013_output_audit import audit_source_dispositions
        return audit_source_dispositions(*fixture)
    def test_all_original_cells_and_actual_stdout(self):
        result=self.audit(self.fixture())
        self.assertEqual(result['original_code_cells'],17)
        self.assertEqual(parse_original_samples(result['cell22_stdout']),[[0,0]]*10)
        self.assertFalse(result['overall_semantic_acceptance'])
    def test_missing_or_duplicate_original_rejected(self):
        for value in (None,0,True):
            f=self.fixture();f[2][1]['original_index']=value
            with self.assertRaisesRegex(ValueError,'ORIGINAL_DISPOSITION_ORDER'):self.audit(f)
    def test_changed_source_or_record_binding_rejected(self):
        f=self.fixture();f[1]['cells'][3]['source']='adapted'
        with self.assertRaisesRegex(ValueError,'SOURCE_CELL_CHANGED'):self.audit(f)
        f=self.fixture();f[2][3]['source_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'RECORD_SOURCE_BINDING'):self.audit(f)
    def test_failure_or_error_output_cannot_pass(self):
        f=self.fixture();f[2][19]['state']='failed'
        with self.assertRaisesRegex(ValueError,'ORIGINAL_NOT_SUCCEEDED'):self.audit(f)
        f=self.fixture();f[1]['cells'][19]['outputs']=[dict(output_type='error',ename='Failure')]
        with self.assertRaisesRegex(ValueError,'ORIGINAL_ERROR_OUTPUT'):self.audit(f)
    def test_only_actual_original_stdout_is_parsed(self):
        f=self.fixture();f[1]['cells'][22]['outputs']=[dict(output_type='stream',name='stderr',text=printed([[0,0]]*10))]
        result=self.audit(f)
        self.assertEqual(result['cell22_stdout'],'')
        with self.assertRaisesRegex(ValueError,'ORIGINAL_SAMPLE_FORMAT'):parse_original_samples(result['cell22_stdout'])
    def test_original_bytes_bound_before_dispositions(self):
        f=list(self.fixture());f[0]+=b' '
        with self.assertRaisesRegex(ValueError,'ORIGINAL_BYTES_CHANGED'):self.audit(f)



class ProgramSnapshotTests(unittest.TestCase):
    def setup_api(self):
        import importlib.util
        from pathlib import Path
        from types import SimpleNamespace as NS
        spec=importlib.util.spec_from_file_location('qb013_snapshot_test',Path(__file__).parent/'observers/qb013.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        class Qiskit:pass
        class Cirq:pass
        class Measurement:pass
        class Stim(list):pass
        class Instruction:pass
        api=NS(QuantumCircuit=Qiskit,CirqCircuit=Cirq,MeasurementGate=Measurement,
               StimCircuit=Stim,StimInstruction=Instruction,measurement_key_name=lambda op:op.gate.key)
        return module.ProgramSnapshot(api),api,NS
    def test_qiskit_unused_classical_registers_and_measurements(self):
        snapshot,api,NS=self.setup_api();program=api.QuantumCircuit()
        q=[object(),object()];c=[object() for _ in range(4)];indices={**dict(zip(q,range(2))),**dict(zip(c,range(4)))}
        class Register(list):
            def __init__(self,name,bits):super().__init__(bits);self.name=name
        program.num_qubits=2;program.num_clbits=4;program.global_phase=0
        program.qregs=[Register('q',q)];program.cregs=[Register('c',c[:2]),Register('meas',c[2:])]
        program.find_bit=lambda b:NS(index=indices[b])
        class Measure:pass
        api.qiskit_operations={'measure':Measure}
        program.data=[NS(operation=NS(name='measure',base_class=Measure,params=[]),qubits=[q[0]],clbits=[c[2]]),
                      NS(operation=NS(name='measure',base_class=Measure,params=[]),qubits=[q[1]],clbits=[c[3]])]
        result=snapshot(program)
        self.assertEqual(result['cregs'][0]['indices'],[0,1]);self.assertEqual(result['cregs'][1]['indices'],[2,3])
        self.assertEqual([row['clbits'] for row in result['operations']],[[2],[3]])
        program.data[0].operation.condition=('c',1)
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_QISKIT_OPERATION'):snapshot(program)
    def test_cirq_sorted_qubits_keys_and_inversion_preserved(self):
        snapshot,api,NS=self.setup_api()
        class Q:
            dimension=2
            def __init__(self,i):self.i=i
            def __lt__(self,other):return self.i<other.i
            def __str__(self):return 'q_'+str(self.i)
        q0,q1=Q(0),Q(1);program=api.CirqCircuit();gate=api.MeasurementGate();gate.key='meas_0';gate.invert_mask=(True,False)
        operation=NS(gate=gate,qubits=(q1,q0));program.all_qubits=lambda:{q1,q0};program.all_operations=lambda:iter([operation])
        result=snapshot(program)
        self.assertEqual(result['operations'][0]['qubits'],[1,0]);self.assertEqual(result['operations'][0]['measurement_key'],'meas_0')
        self.assertEqual(result['operations'][0]['invert_mask'],[True,False])
        operation.tags=('annotation',)
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_CIRQ_TAGS'):snapshot(program)
    def test_stim_target_order_and_inversions_preserved(self):
        snapshot,api,NS=self.setup_api();instruction=api.StimInstruction();instruction.name='M'
        targets=[NS(value=1,is_qubit_target=True,is_inverted_result_target=True),NS(value=0,is_qubit_target=True,is_inverted_result_target=False)]
        instruction.targets_copy=lambda:list(targets);instruction.gate_args_copy=lambda:[]
        program=api.StimCircuit([instruction]);program.num_qubits=2;program.num_measurements=2
        result=snapshot(program)
        self.assertEqual(result['operations'][0]['qubits'],[1,0]);self.assertEqual(result['operations'][0]['inverted'],[True,False])
        targets[0].is_qubit_target=False
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_STIM_TARGET'):snapshot(program)
        program[:]=[object()]
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_STIM_BLOCK'):snapshot(program)
    def test_qasm_text_is_not_rewritten(self):
        snapshot,api,NS=self.setup_api()
        for text in ('OPENQASM 2.0;\nqreg q[2];\n','OPENQASM 3;\nqubit[2] q;\n'):
            self.assertEqual(snapshot(text)['text'],text)
        with self.assertRaisesRegex(ValueError,'UNKNOWN_STRING_PROGRAM'):snapshot('arbitrary text')
    def test_unsupported_and_nonfinite_are_explicit(self):
        snapshot,api,NS=self.setup_api()
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_PROGRAM_TYPE'):snapshot(object())
        for value in (float('inf'),float('-inf'),float('nan')):
            with self.assertRaisesRegex(ValueError,'NONFINITE_PROGRAM_PARAMETER'):snapshot._number(value)
    def test_unknown_cirq_gate_not_dropped(self):
        snapshot,api,NS=self.setup_api();program=api.CirqCircuit()
        program.all_qubits=lambda:set();program.all_operations=lambda:iter([NS(gate=object(),qubits=())])
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_CIRQ_GATE'):snapshot(program)


    def test_cirq_pauli_subclass_uses_semantic_family(self):
        snapshot,api,NS=self.setup_api()
        class XPowGate:
            exponent=1;global_shift=0
        class _PauliX(XPowGate):pass
        api.XPowGate=XPowGate
        program=api.CirqCircuit();program.all_qubits=lambda:set()
        program.all_operations=lambda:iter([NS(gate=_PauliX(),qubits=())])
        row=snapshot(program)['operations'][0]
        self.assertEqual(row['gate_class'],'_PauliX');self.assertEqual(row['gate_family'],'XPowGate')
        self.assertEqual(row['exponent'],1)
    def test_measurement_confusion_not_silently_dropped(self):
        snapshot,api,NS=self.setup_api();program=api.CirqCircuit();gate=api.MeasurementGate()
        gate.key='m';gate.invert_mask=();gate.confusion_map={(0,):[[1,0],[0,1]]}
        program.all_qubits=lambda:set();program.all_operations=lambda:iter([NS(gate=gate,qubits=())])
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_CIRQ_MEASUREMENT_CONFUSION'):snapshot(program)


    def test_stim_noise_arguments_and_unknown_instructions_rejected(self):
        snapshot,api,NS=self.setup_api();instruction=api.StimInstruction()
        instruction.name='M';instruction.targets_copy=lambda:[];instruction.gate_args_copy=lambda:[0.1]
        program=api.StimCircuit([instruction]);program.num_qubits=2;program.num_measurements=2
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_STIM_ARGUMENTS'):snapshot(program)
        instruction.name='DEPOLARIZE1'
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_STIM_INSTRUCTION'):snapshot(program)
    def test_qiskit_same_named_custom_gate_rejected(self):
        snapshot,api,NS=self.setup_api()
        class HGate:pass
        class CustomH:pass
        api.qiskit_operations={'h':HGate}
        program=api.QuantumCircuit();program.data=[NS(operation=NS(name='h',base_class=CustomH,params=[]),qubits=[],clbits=[])]
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_QISKIT_OPERATION:h'):snapshot(program)



class CachedGraphTests(unittest.TestCase):
    def fixture(self):
        import importlib.util
        from pathlib import Path
        spec=importlib.util.spec_from_file_location('qb013_graph_test',Path(__file__).parent/'observers/qb013.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        class Edge:
            source='cirq';target='stim'
            def __init__(self):self._conversion_func=lambda value:value
            def convert(self,value):return self._conversion_func(value)
        edge=Edge()
        class Graph:
            def __init__(self):self.methods={(0,1):dict(func=edge.convert)};self.listed=[edge]
            def edge_list(self):return list(self.methods)
            def get_edge_data(self,a,b):return self.methods[a,b]
            def __getitem__(self,index):return ['cirq','stim'][index]
            def conversions(self):return self.listed
        return module,Edge,edge,Graph()
    def test_real_cached_instance_not_replaced_list_entry(self):
        module,Edge,edge,graph=self.fixture();replacement=Edge();graph.listed=[replacement]
        cached,evidence=module.cached_graph_inventory(graph,Edge.convert)
        self.assertIs(cached[0],edge);self.assertFalse(evidence['listed_and_cached_identity_sets_match'])
        self.assertEqual(evidence['listed_edge_ordinals'],[None])
        with module.ScopedConversions(cached,lambda v:v) as capture:
            self.assertEqual(graph.methods[0,1]['func']('original'),'original')
        self.assertEqual(len(capture.records),1);capture.require_complete()
    def test_matching_registry_is_explicit(self):
        module,Edge,edge,graph=self.fixture()
        cached,evidence=module.cached_graph_inventory(graph,Edge.convert)
        self.assertTrue(evidence['listed_and_cached_identity_sets_match'])
        self.assertEqual(evidence['cached_edges'][0]['source'],'cirq')
    def test_unknown_callable_and_endpoint_rejected(self):
        module,Edge,edge,graph=self.fixture();graph.methods[0,1]['func']=lambda value:value
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_CACHED_CONVERSION_CALLABLE'):
            module.cached_graph_inventory(graph,Edge.convert)
        module,Edge,edge,graph=self.fixture();edge.target='other'
        with self.assertRaisesRegex(ValueError,'CACHED_EDGE_ENDPOINT_MISMATCH'):
            module.cached_graph_inventory(graph,Edge.convert)
    def test_duplicate_registry_not_silently_accepted(self):
        module,Edge,edge,graph=self.fixture();graph.listed.append(edge)
        cached,evidence=module.cached_graph_inventory(graph,Edge.convert)
        self.assertFalse(evidence['listed_and_cached_identity_sets_match'])
        self.assertEqual(len(cached),1)



class NormalizedParserTests(unittest.TestCase):
    def module(self):
        import importlib.util
        from pathlib import Path
        spec=importlib.util.spec_from_file_location('qb013_parser_test',Path(__file__).parent/'observers/qb013.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module
    def test_actual_text_and_return_identity_no_regeneration(self):
        from types import SimpleNamespace
        calls=[];circuit=object();result=SimpleNamespace(circuit=circuit, qregs={'q':2},
            cregs={'c':2, 'meas':2}, supportedFormat=True, qelib1Include=True)
        class Parser:
            def parse(self,qasm):calls.append((self,qasm));return result
        original=Parser.parse;instance=Parser();text='OPENQASM 2.0;\n// exact normalized input\n'
        capture=self.module().ScopedQasmParser(Parser,lambda value:dict(identity=id(value)))
        with capture:self.assertIs(instance.parse(qasm=text),result)
        self.assertIs(Parser.parse,original);self.assertEqual(calls,[(instance,text)])
        self.assertEqual(capture.records[0]['normalized_parser_input'],text)
        self.assertEqual(capture.records[0]['parsed_circuit']['identity'],id(circuit));capture.require_complete()
        self.assertEqual(capture.records[0]['parsed_registers']['cregs'],
                         [dict(name='c',size=2),dict(name='meas',size=2)])
        result.cregs['later']=1
        self.assertEqual(len(capture.records[0]['parsed_registers']['cregs']),2)
    def test_invalid_registers_defer_error_without_changing_original(self):
        from types import SimpleNamespace
        for qregs,cregs,flag in (({'q':True},{},True),({'q':0},{},True),
                                 ({'q':2},{'q':1},True),({'q':2},{},1)):
            result=SimpleNamespace(circuit=object(),qregs=qregs,cregs=cregs,
                                   supportedFormat=flag,qelib1Include=True)
            class Parser:
                def parse(self,qasm):return result
            original=Parser.parse;capture=self.module().ScopedQasmParser(Parser,lambda value:{})
            with capture:self.assertIs(Parser().parse('unchanged'),result)
            self.assertIs(Parser.parse,original)
            self.assertEqual(capture.records[0]['state'],'succeeded')
            self.assertEqual(capture.diagnostics[0]['stage'],'parsed_registers')
            with self.assertRaisesRegex(ValueError,'AUTHORED_PARSER_CAPTURE_FAILED'):capture.require_complete()
    def test_capture_failure_deferred_original_return_preserved(self):
        from types import SimpleNamespace
        result=SimpleNamespace(circuit=object())
        class Parser:
            def parse(self,qasm):return result
        def broken(value):raise ValueError('capture')
        capture=self.module().ScopedQasmParser(Parser,broken)
        with capture:self.assertIs(Parser().parse('source'),result)
        self.assertEqual(capture.records[0]['state'],'succeeded')
        with self.assertRaisesRegex(ValueError,'AUTHORED_PARSER_CAPTURE_FAILED'):capture.require_complete()
    def test_original_error_identity_and_restore(self):
        failure=RuntimeError('original parser')
        class Parser:
            def parse(self,qasm):raise failure
        original=Parser.parse;capture=self.module().ScopedQasmParser(Parser,lambda value:value)
        try:
            with capture:Parser().parse('bad')
        except RuntimeError as error:self.assertIs(error,failure)
        else:self.fail('Original exception lost')
        self.assertIs(Parser.parse,original);capture.require_complete()
        self.assertEqual(capture.records[0]['original_error']['message'],'original parser')
    def test_unexpected_replacement_preserved(self):
        class Parser:
            def parse(self,qasm):return qasm
        replacement=lambda self,qasm:None
        capture=self.module().ScopedQasmParser(Parser,lambda value:value)
        with capture:Parser.parse=replacement
        self.assertIs(Parser.parse,replacement)
        with self.assertRaisesRegex(ValueError,'AUTHORED_PARSER_CAPTURE_FAILED'):capture.require_complete()
    def test_nested_scope_rejected(self):
        class Parser:
            def parse(self,qasm):return qasm
        capture=self.module().ScopedQasmParser(Parser,lambda value:value)
        with capture:
            with self.assertRaisesRegex(ValueError,'PARSER_OBSERVER_IDENTITY'):
                with capture:pass
            self.assertTrue(capture.active)
        capture.require_complete()

    def test_parser_checkpoints_preserve_running_failure_and_restore(self):
        from copy import deepcopy
        saved=[];primary=ValueError('parse failure')
        class Parser:
            def parse(self,qasm):
                if saved[-1]['records'][0]['state']!='running':raise RuntimeError('missing checkpoint')
                raise primary
        original=Parser.parse;capture=self.module().ScopedQasmParser(Parser,lambda value:value)
        capture.checkpoint=lambda:saved.append(deepcopy(dict(records=capture.records,active=capture.active)))
        with self.assertRaises(ValueError) as caught:
            with capture:Parser().parse('actual input')
        self.assertIs(caught.exception,primary);self.assertIs(Parser.parse,original)
        self.assertEqual([v['records'][0]['state'] for v in saved],['running','failed','failed'])
        self.assertFalse(saved[-1]['active']);capture.require_complete()

    def test_parser_write_failure_is_deferred_from_success(self):
        from types import SimpleNamespace
        result=SimpleNamespace(circuit=object(),qregs={},cregs={},supportedFormat=True,qelib1Include=True)
        class Parser:
            def parse(self,qasm):return result
        def broken():raise OSError('write failed')
        original=Parser.parse;capture=self.module().ScopedQasmParser(Parser,lambda value:{},broken)
        with capture:self.assertIs(Parser().parse('actual input'),result)
        self.assertIs(Parser.parse,original)
        self.assertEqual(capture.records[0]['state'],'succeeded')
        self.assertTrue(all(d['stage']=='checkpoint' for d in capture.diagnostics))
        with self.assertRaisesRegex(ValueError,'AUTHORED_PARSER_CAPTURE_FAILED'):capture.require_complete()

class ObservedTranspileTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        self.module,self.Edge,self.edge,self.graph=CachedGraphTests().fixture()
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'observed.json'
        self.calls=[]
        class Parser:
            def parse(self,qasm):
                return SimpleNamespace(circuit=qasm,qregs={},cregs={},supportedFormat=True,qelib1Include=True)
        self.Parser=Parser;self.original_parse=Parser.parse
        def conversion(value):
            Parser().parse('normalized')
            return value+' converted'
        self.conversion=conversion;self.edge._conversion_func=conversion
        self.api=SimpleNamespace(conversion_method=self.Edge.convert,QasmParser=Parser,
                                 known_conversion_functions={'cirq_to_stim':conversion})
        def original(program,target,conversion_graph=None):
            self.calls.append((program,target,conversion_graph))
            return conversion_graph.get_edge_data(0,1)['func'](program)
        self.original=original
    def observer(self, original=None, journal=None):
        return self.module.ObservedTranspile(original or self.original,self.api,
            lambda value:dict(value=value),journal or self.module.CaptureJournal(self.path))
    def test_complete_controller_records_and_restores(self):
        import json
        capture=self.observer()
        self.assertEqual(capture.wrapper('source','stim',conversion_graph=self.graph),'source converted')
        capture.require_complete();payload=json.loads(self.path.read_bytes())['payload']
        self.assertFalse(payload['active']);record=payload['transpile_calls'][0]
        self.assertEqual(self.calls,[('source','stim',self.graph)])
        self.assertEqual(record['state'],'succeeded')
        self.assertEqual(record['parsers'][0]['normalized_parser_input'],'normalized')
        self.assertEqual(record['conversions'][0]['function_identities'],['cirq_to_stim'])
        self.assertEqual(record['input'],record['input_after'])
        self.assertEqual(record['graph_before'],record['graph_after'])
        self.assertTrue(record['scopes_restored'])
        self.assertIs(self.edge._conversion_func,self.conversion);self.assertIs(self.Parser.parse,self.original_parse)
    def test_original_failure_saved_before_final_verification(self):
        import json
        primary=ValueError('original conversion')
        def original(program,target,conversion_graph=None):
            self.calls.append(program);raise primary
        capture=self.observer(original)
        with self.assertRaises(ValueError) as caught:capture.wrapper('source','stim',conversion_graph=self.graph)
        self.assertIs(caught.exception,primary);capture.require_complete()
        record=json.loads(self.path.read_bytes())['payload']['transpile_calls'][0]
        self.assertEqual(record['original_error']['message'],'original conversion')
        self.assertTrue(record['scopes_restored']);self.assertEqual(self.calls,['source'])
    def test_actual_outputs_retained_outside_json(self):
        import json
        value = object()
        self.edge._conversion_func = lambda program: value
        capture = self.module.ObservedTranspile(self.original, self.api,
            lambda item: dict(identity=id(item)), self.module.CaptureJournal(self.path))
        self.assertIs(capture.wrapper('source', 'stim', conversion_graph=self.graph), value)
        self.assertIs(capture.verified_native_outputs(0)[0], value)
        payload = json.loads(self.path.read_bytes())['payload']
        self.assertNotIn('native_calls', payload)
        self.assertNotIn('native_outputs', payload['transpile_calls'][0])
    def test_native_output_mutation_detected_before_and_after_analysis(self):
        value = ['before']
        self.edge._conversion_func = lambda program: value
        capture = self.module.ObservedTranspile(self.original, self.api,
            lambda item: dict(value=list(item) if isinstance(item, list) else item),
            self.module.CaptureJournal(self.path))
        capture.wrapper('source', 'stim', conversion_graph=self.graph)
        self.assertIs(capture.verified_native_outputs(0)[0], value)
        value.append('after')
        with self.assertRaisesRegex(ValueError, 'NATIVE_OUTPUT_MUTATED'):
            capture.verified_native_outputs(0)
    def test_failed_conversion_has_no_native_output_even_if_original_recovers(self):
        primary = ValueError('conversion failure')
        def broken(program): raise primary
        self.edge._conversion_func = broken
        def recovering(program, target, conversion_graph=None):
            try: self.original(program, target, conversion_graph)
            except ValueError as error: self.assertIs(error, primary)
            return 'recovered'
        capture = self.observer(recovering)
        self.assertEqual(capture.wrapper('source', 'stim', conversion_graph=self.graph), 'recovered')
        capture.require_complete()
        with self.assertRaisesRegex(ValueError, 'NATIVE_OUTPUTS_UNAVAILABLE'):
            capture.verified_native_outputs(0)
    def test_native_outputs_require_valid_ordinal_and_complete_capture(self):
        capture = self.observer()
        capture.wrapper('source', 'stim', conversion_graph=self.graph)
        for ordinal in (True, -1, 1, '0'):
            with self.assertRaisesRegex(ValueError, 'NATIVE_CALL_ORDINAL'):
                capture.verified_native_outputs(ordinal)
        capture.diagnostics.append(dict(stage='synthetic', type='CaptureFailure'))
        with self.assertRaisesRegex(ValueError, 'AUTHORED_TRANSPILE_CAPTURE_FAILED'):
            capture.verified_native_outputs(0)
    def test_capture_setup_failure_delegates_once_without_changing_result(self):
        def original(program,target,conversion_graph=None):
            self.calls.append(program);return program
        capture=self.observer(original)
        self.assertEqual(capture.wrapper('source','stim'),'source')
        self.assertEqual(self.calls,['source']);self.assertFalse(capture.active)
        self.assertEqual(capture.diagnostics[0]['stage'],'capture_setup')
        with self.assertRaisesRegex(ValueError,'AUTHORED_TRANSPILE_CAPTURE_FAILED'):capture.require_complete()
    def test_journal_failure_deferred_and_scopes_restored(self):
        class BrokenJournal:
            def write(self,payload):raise OSError('disk')
        capture=self.observer(journal=BrokenJournal())
        self.assertEqual(capture.wrapper('source','stim',conversion_graph=self.graph),'source converted')
        self.assertEqual(len(self.calls),1)
        self.assertIs(self.Parser.parse,self.original_parse);self.assertIs(self.edge._conversion_func,self.conversion)
        with self.assertRaisesRegex(ValueError,'AUTHORED_TRANSPILE_CAPTURE_FAILED'):capture.require_complete()
    def test_foreign_parser_replacement_preserved_and_rejected(self):
        replacement=lambda self,qasm:None
        def original(program,target,conversion_graph=None):
            self.Parser.parse=replacement;return program
        capture=self.observer(original)
        self.assertEqual(capture.wrapper('source','stim',conversion_graph=self.graph),'source')
        self.assertIs(self.Parser.parse,replacement)
        self.assertFalse(capture.records[0]['scopes_restored'])
        with self.assertRaisesRegex(ValueError,'AUTHORED_TRANSPILE_CAPTURE_FAILED'):capture.require_complete()


class SourceGatedBindingTests(unittest.TestCase):
    def setUp(self):
        import hashlib
        import importlib.util
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        spec=importlib.util.spec_from_file_location('qb013_binding_test',Path(__file__).parent/'observers/qb013.py')
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.hashes={}
        for relative in self.module.API_SOURCE_HASHES:
            path=self.root/relative;path.parent.mkdir(parents=True,exist_ok=True)
            raw=('fake source fixture '+relative).encode();path.write_bytes(raw)
            self.hashes[relative]=hashlib.sha256(raw).hexdigest()
        self.modules={name:SimpleNamespace(__file__=str(self.root/relative)) for name,relative in self.module.API_MODULE_PATHS.items()}
        classes={
            'qiskit.circuit.quantumcircuit':['QuantumCircuit'],
            'qiskit.circuit.measure':['Measure'],'qiskit.circuit.barrier':['Barrier'],
            'cirq.circuits.circuit':['AbstractCircuit'],'cirq.ops.identity':['IdentityGate'],
            'cirq.ops.measurement_gate':['MeasurementGate'],'stim':['Circuit','CircuitInstruction'],
            'cirq.ops.common_gates':['HPowGate','XPowGate','YPowGate','ZPowGate','CXPowGate','CZPowGate'],
            'qbraid.transpiler.edge':['Conversion'],
            'qbraid.transpiler.graph':['ConversionGraph'],
            'qbraid.transpiler.conversions.qasm2.cirq_qasm_parser':['QasmParser'],
        }
        for module,names in {'h':['HGate'],'x':['XGate','CXGate'],'y':['YGate'],'z':['ZGate','CZGate'],'s':['SGate','SdgGate'],'sx':['SXGate','SXdgGate'],'t':['TGate','TdgGate'],'i':['IGate']}.items():
            classes['qiskit.circuit.library.standard_gates.'+module]=names
        for module,names in classes.items():
            for name in names:setattr(self.modules[module],name,type(name,(),{}))
        self.modules['qbraid.transpiler.edge'].Conversion.convert=lambda self,program:program
        self.modules['qbraid.transpiler.graph'].ConversionGraph.add_conversion=lambda self,edge,overwrite=False:None
        self.modules['qbraid.transpiler.graph'].ConversionGraph.has_path=lambda self,source,target:True
        transpile=lambda program,target,conversion_graph=None:program
        self.modules['qbraid.transpiler'].transpile=transpile
        self.modules['qbraid.transpiler.converter'].transpile=transpile
        self.modules['qbraid.transpiler.conversions.qasm2.cirq_qasm_parser'].QasmParser.parse=lambda self,qasm:qasm
        self.modules['cirq.protocols.measurement_key_protocol'].measurement_key_name=lambda value:'fake-key'
        self.modules['stimcirq._cirq_to_stim'].cirq_circuit_to_stim_circuit=lambda program:program
        self.modules['qbraid.transpiler.conversions.qiskit.qiskit_to_qasm2'].qiskit_to_qasm2=lambda program:program
        self.modules['qbraid.transpiler.conversions.qasm2.qasm2_to_cirq'].qasm2_to_cirq=lambda program:program
        self.calls=[]
    def importer(self,name):
        self.calls.append(name)
        return self.modules[name]
    def bind(self):
        return self.module._bind_observation_api(self.root,self.hashes,self.importer)
    def test_typed_api_and_unmodified_graph_parser_methods(self):
        conversion=self.modules['qbraid.transpiler.edge'].Conversion.convert
        parser=self.modules['qbraid.transpiler.conversions.qasm2.cirq_qasm_parser'].QasmParser.parse
        api=self.bind()
        self.assertEqual(self.calls,list(self.module.API_MODULE_PATHS))
        self.assertIs(api.conversion_method,conversion)
        self.assertIs(api.QasmParser.parse,parser)
        self.assertIs(api.QuantumCircuit,self.modules['qiskit.circuit.quantumcircuit'].QuantumCircuit)
        self.assertIs(api.CirqCircuit,self.modules['cirq.circuits.circuit'].AbstractCircuit)
        self.assertEqual(set(api.qiskit_operations),{'h','x','y','z','s','sdg','sx','sxdg','t','tdg','cx','cz','id','measure','barrier'})
        self.assertEqual(api.source_evidence['source_hashes'],self.hashes)
        self.assertEqual(api.source_evidence['compiled_source_correspondence'],'unproved')
    def test_missing_gate_prevents_every_import(self):
        self.hashes.pop(next(iter(self.hashes)))
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_API_SOURCE_GATES'):self.bind()
        self.assertEqual(self.calls,[])
    def test_changed_source_prevents_every_import(self):
        (self.root/'stim/__init__.py').write_text('changed')
        with self.assertRaisesRegex(ValueError,'API_SOURCE_CHANGED'):self.bind()
        self.assertEqual(self.calls,[])
    def test_missing_source_prevents_every_import(self):
        (self.root/'stim/__init__.py').unlink()
        with self.assertRaises(FileNotFoundError):self.bind()
        self.assertEqual(self.calls,[])
    def test_foreign_import_origin_rejected(self):
        self.modules['stim'].__file__=str(self.root/'qiskit/__init__.py')
        with self.assertRaisesRegex(ValueError,'API_MODULE_ORIGIN_MISMATCH:stim'):self.bind()
    def test_changed_imported_source_rejected(self):
        def importer(name):
            if name=='stim':(self.root/'stim/__init__.py').write_text('changed during import')
            return self.importer(name)
        with self.assertRaisesRegex(ValueError,'API_SOURCE_CHANGED_DURING_IMPORT'):
            self.module._bind_observation_api(self.root,self.hashes,importer)
    def test_changed_other_gate_during_import_rejected(self):
        def importer(name):
            if name=='stim':(self.root/'stim/__init__.pyi').write_text('changed non-module gate')
            return self.importer(name)
        with self.assertRaisesRegex(ValueError,'API_SOURCE_CHANGED_DURING_BINDING'):
            self.module._bind_observation_api(self.root,self.hashes,importer)
    def test_missing_class_or_callable_rejected(self):
        self.modules['qiskit.circuit.measure'].Measure=None
        with self.assertRaisesRegex(ValueError,'API_CLASS_MISSING'):self.bind()
        self.modules['qiskit.circuit.measure'].Measure=type('Measure',(),{})
        self.modules['cirq.protocols.measurement_key_protocol'].measurement_key_name=None
        with self.assertRaisesRegex(ValueError,'API_CALLABLE_MISSING'):self.bind()
    def test_public_entry_uses_fixed_hashes_and_no_hooks(self):
        from unittest.mock import patch
        sentinel=object()
        with patch.object(self.module,'_bind_observation_api',return_value=sentinel) as binding:
            self.assertIs(self.module.bind_observation_api(self.root),sentinel)
        args=binding.call_args.args
        self.assertEqual(args[0],self.root)
        self.assertIs(args[1],self.module.API_SOURCE_HASHES)
        self.assertEqual(args[2].__name__,'import_module')
    def test_public_transpile_identity_mismatch_rejected(self):
        self.modules['qbraid.transpiler'].transpile=lambda *args:None
        with self.assertRaisesRegex(ValueError,'TRANSPILE_API_IDENTITY'):self.bind()


class NotebookCaptureTests(unittest.TestCase):
    def setUp(self):
        from types import SimpleNamespace
        self.base=ObservedTranspileTests();self.base.setUp();self.addCleanup(self.base.doCleanups)
        self.graph=self.base.graph;self.api=self.base.api;self.namespace={};self.add_calls=[]
        def add_conversion(graph,edge,overwrite=False):
            self.add_calls.append((edge,overwrite))
            if getattr(graph,'fail_next',False):
                graph.fail_next=False
                raise ValueError('original add failure')
            graph.methods[0,1]=dict(func=edge.convert);graph.listed=[edge]
        def has_path(graph,source,target):return source in ('cirq','qiskit') and target=='stim'
        # Match the real method's bound argument spelling.
        def add_method(self,edge,overwrite=False):return add_conversion(self,edge,overwrite)
        def path_method(self,source,target):return has_path(self,source,target)
        graph_type=type(self.graph);graph_type.add_conversion=add_method;graph_type.has_path=path_method
        self.add_original=add_method;self.path_original=path_method
        self.api.ConversionGraph=graph_type;self.api.transpile=self.base.original
        self.api.public_module=SimpleNamespace(transpile=self.base.original)
        self.api.converter_module=SimpleNamespace(transpile=self.base.original)
        self.api.source_evidence=dict(fixture=True)
        self.capture=self.base.module.NotebookCapture(self.api,self.namespace,
            self.base.module.CaptureJournal(self.base.path),lambda value:dict(value=value))
        self.addCleanup(self.capture.restore)
    def test_public_import_alias_graph_events_and_restore(self):
        import json
        self.assertIs(self.api.public_module.transpile,self.base.original)
        self.capture.install()
        self.graph.add_conversion(self.base.edge,overwrite=True)
        self.assertTrue(self.graph.has_path('cirq','stim'))
        self.namespace['transpile']=self.api.public_module.transpile
        self.assertEqual(self.namespace['transpile']('source','stim',conversion_graph=self.graph),'source converted')
        self.capture.restore();self.capture.require_complete()
        self.assertIs(self.namespace['transpile'],self.base.original)
        self.assertIs(self.api.public_module.transpile,self.base.original)
        self.assertIs(self.api.converter_module.transpile,self.base.original)
        self.assertIs(type(self.graph).add_conversion,self.add_original)
        self.assertIs(type(self.graph).has_path,self.path_original)
        payload=json.loads(self.base.path.read_bytes())['payload']
        self.assertTrue(payload['public_hooks_restored'])
        self.assertEqual([x['method'] for x in payload['public_events']],['add_conversion','has_path'])
        self.assertEqual(payload['public_events'][0]['function_identities'],['cirq_to_stim'])
        self.assertEqual(self.add_calls,[(self.base.edge,True)])
    def test_original_add_failure_and_fallback_remain_distinct(self):
        self.graph.fail_next=True;self.capture.install()
        with self.assertRaisesRegex(ValueError,'original add failure'):
            self.graph.add_conversion(self.base.edge,overwrite=True)
        self.graph.add_conversion(self.base.edge)
        self.capture.restore();self.capture.require_complete()
        events=self.capture.controller.public_events
        self.assertEqual([x['state'] for x in events],['failed','succeeded'])
        self.assertEqual([x['overwrite'] for x in events],[True,False])
        self.assertEqual(len(self.add_calls),2)
    def test_foreign_public_hook_and_alias_not_overwritten(self):
        replacement=lambda *args:None
        self.capture.install();self.api.public_module.transpile=replacement;self.namespace['transpile']=replacement
        self.capture.restore()
        self.assertIs(self.api.public_module.transpile,replacement)
        self.assertIs(self.namespace['transpile'],replacement)
        with self.assertRaisesRegex(ValueError,'AUTHORED_TRANSPILE_CAPTURE_FAILED'):self.capture.require_complete()
    def test_partial_install_failure_restores_prior_own_hook(self):
        replacement=lambda *args:None;self.api.converter_module.transpile=replacement
        with self.assertRaisesRegex(ValueError,'PUBLIC_HOOK_IDENTITY'):self.capture.install()
        self.assertIs(self.api.public_module.transpile,self.base.original)
        self.assertIs(self.api.converter_module.transpile,replacement)
        self.assertIs(type(self.graph).add_conversion,self.add_original)
        with self.assertRaisesRegex(ValueError,'AUTHORED_TRANSPILE_CAPTURE_FAILED'):self.capture.require_complete()
    def test_missing_foreign_hook_does_not_prevent_other_restoration(self):
        self.capture.install();del self.api.public_module.transpile
        self.capture.restore()
        self.assertFalse(hasattr(self.api.public_module,'transpile'))
        self.assertIs(self.api.converter_module.transpile,self.base.original)
        self.assertIs(type(self.graph).add_conversion,self.add_original)
        with self.assertRaisesRegex(ValueError,'AUTHORED_TRANSPILE_CAPTURE_FAILED'):self.capture.require_complete()
    def test_deleted_imported_alias_after_call_is_not_preimport_absence(self):
        self.capture.install();self.namespace['transpile']=self.api.public_module.transpile
        self.namespace['transpile']('source','stim',conversion_graph=self.graph)
        del self.namespace['transpile']
        self.capture.restore()
        self.assertNotIn('transpile',self.namespace)
        self.assertTrue(self.capture.controller.public_alias_seen)
        self.assertFalse(self.capture.controller.public_hooks_restored)
        self.assertIs(self.api.public_module.transpile,self.base.original)
        with self.assertRaisesRegex(ValueError,'AUTHORED_TRANSPILE_CAPTURE_FAILED'):self.capture.require_complete()
    def test_never_installed_is_not_successful_restoration(self):
        self.capture.restore()
        with self.assertRaisesRegex(ValueError,'PUBLIC_HOOKS_NOT_RESTORED'):self.capture.require_complete()
    def test_reuse_rejected_and_cleanup_before_source_import_preserves_namespace(self):
        self.capture.install()
        with self.assertRaisesRegex(ValueError,'NOTEBOOK_CAPTURE_ALREADY_USED'):self.capture.install()
        self.capture.restore();self.capture.require_complete()
        self.assertNotIn('transpile',self.namespace)

class ParserRegisterMappingTests(unittest.TestCase):
    def fixtures(self):
        qiskit = dict(format='qiskit', qubits=2, clbits=4,
            qregs=[dict(name='z',size=1,indices=[0]),dict(name='a',size=1,indices=[1])],
            cregs=[dict(name='c',size=2,indices=[0,1]),dict(name='meas',size=2,indices=[2,3])],
            operations=[dict(name='measure',qubits=[0],clbits=[2],params=[]),
                        dict(name='measure',qubits=[1],clbits=[3],params=[])])
        parser = dict(state='succeeded', parsed_registers=dict(
            qregs=[dict(name='z',size=1),dict(name='a',size=1)],
            cregs=[dict(name='c',size=2),dict(name='meas',size=2)],
            supported_format=True,qelib1_include=True), parsed_circuit=dict(format='cirq',
            sorted_qubits=[dict(type='cirq.ops.named_qubit.NamedQubit',text=name,dimension=2)
                           for name in ('a_0','z_0')],
            operations=[dict(measurement_key='meas_0',qubits=[1],invert_mask=[]),
                        dict(measurement_key='meas_1',qubits=[0],invert_mask=[])]))
        return qiskit, parser

    def audit(self, qiskit, parser):
        from qb013_output_audit import audit_qiskit_parser_measurements
        return audit_qiskit_parser_measurements(qiskit, parser)

    def test_actual_qid_order_and_unused_classical_bits(self):
        result=self.audit(*self.fixtures())
        self.assertEqual(result['sorted_qid_to_qiskit'],[1,0])
        self.assertEqual(result['occurrence_to_logical'],[0,1])
        self.assertEqual(result['occurrence_to_clbit'],[2,3])
        self.assertEqual(result['unused_clbits'],[0,1])
        self.assertFalse(result['gate_equivalence_verified'])

    def test_renamed_removed_or_reordered_registers_rejected(self):
        for rows in ([dict(name='renamed',size=2),dict(name='meas',size=2)],
                     [dict(name='meas',size=2)],
                     [dict(name='meas',size=2),dict(name='c',size=2)]):
            qiskit,parser=self.fixtures();parser['parsed_registers']['cregs']=rows
            with self.assertRaisesRegex(ValueError,'REGISTER_DECLARATIONS_CHANGED'):self.audit(qiskit,parser)

    def test_reordered_destinations_or_targets_rejected(self):
        for field,value in (('measurement_key','c_0'),('qubits',[0])):
            qiskit,parser=self.fixtures();parser['parsed_circuit']['operations'][0][field]=value
            with self.assertRaisesRegex(ValueError,'QISKIT_PARSER_MEASUREMENTS_CHANGED'):self.audit(qiskit,parser)

    def test_invalid_aliases_indices_labels_and_masks_rejected(self):
        mutations=[lambda q,p:q['cregs'][0].update(indices=[0,0]),
                   lambda q,p:q['cregs'][0].update(indices=[False,1]),
                   lambda q,p:p['parsed_circuit']['sorted_qubits'][0].update(text='foreign_0'),
                   lambda q,p:p['parsed_circuit']['sorted_qubits'][0].update(type='custom.NamedQubit'),
                   lambda q,p:p['parsed_circuit']['operations'][0].update(invert_mask=[True]),
                   lambda q,p:p['parsed_circuit']['operations'][0].update(invert_mask=[0]),
                   lambda q,p:q['operations'][0].update(clbits=[True])]
        for mutation in mutations:
            qiskit,parser=self.fixtures();mutation(qiskit,parser)
            with self.assertRaises(ValueError):self.audit(qiskit,parser)

    def test_no_measurement_is_not_vacuous_success(self):
        qiskit,parser=self.fixtures();qiskit['operations']=[];parser['parsed_circuit']['operations']=[]
        with self.assertRaisesRegex(ValueError,'QISKIT_PARSER_MEASUREMENTS_CHANGED'):self.audit(qiskit,parser)


class ConversionRouteTests(unittest.TestCase):
    def fixtures(self):
        from copy import deepcopy
        original,parser=ParserRegisterMappingTests().fixtures()
        parser['normalized_parser_input']='OPENQASM 2.0; // captured normalized input'
        qasm=dict(format='qasm',version='2.0',text='OPENQASM 2.0; // captured exporter output')
        final=dict(format='stim',qubits=2,measurements=2,operations=[
            dict(name='M',qubits=[1,0],inverted=[False,False],args=[])])
        edges=[('qiskit','qasm2','qiskit_to_qasm2',original,qasm),
               ('qasm2','cirq','qasm2_to_cirq',qasm,parser['parsed_circuit']),
               ('cirq','stim','cirq_to_stim',parser['parsed_circuit'],final)]
        records=[dict(ordinal=i,state='succeeded',source=s,target=t,function_identities=[fn],
                      positional_argument_count=1,keyword_names=[],single_program_positional_call=True,
                      input=deepcopy(before),output=deepcopy(after))
                 for i,(s,t,fn,before,after) in enumerate(edges)]
        return original,final,records,[parser]

    def audit(self, values):
        from qb013_output_audit import audit_conversion_route
        return audit_conversion_route(*values)

    def test_composes_actual_occurrences_with_unused_slots(self):
        result=self.audit(self.fixtures())
        self.assertEqual(result['occurrence_to_logical'],[0,1])
        self.assertEqual(result['occurrence_to_clbit'],[2,3])
        self.assertTrue(result['default_stim_mapping_verified'])
        self.assertFalse(result['overall_semantic_acceptance'])
        self.assertFalse(result['normalization_gate_equivalence_verified'])

    def test_failed_extra_or_other_route_never_filtered(self):
        for kind in ('failed','extra','other'):
            values=list(self.fixtures());records=values[2]
            if kind=='failed':records[0]['state']='failed'
            elif kind=='extra':records.insert(0,dict(state='failed'))
            else:records[1]['target']='other'
            with self.assertRaises(ValueError):self.audit(values)

    def test_function_spoof_custom_map_and_boolean_count_rejected(self):
        for field,value in (('function_identities',[]),('function_identities',['cirq_to_stim','alias']),
                            ('keyword_names',['qubit_to_index_dict']),('positional_argument_count',True),
                            ('single_program_positional_call',False)):
            values=list(self.fixtures());values[2][2][field]=value
            with self.assertRaises(ValueError):self.audit(values)

    def test_intermediate_endpoint_and_parser_mismatch_rejected(self):
        for kind in ('intermediate','endpoint','parser','missing_parser'):
            values=list(self.fixtures())
            if kind=='intermediate':values[2][1]['input']['text']='different'
            elif kind=='endpoint':values[2][0]['input']['clbits']=5
            elif kind=='parser':values[3][0]['parsed_circuit']['operations']=[]
            else:values[3]=[]
            with self.assertRaises(ValueError):self.audit(values)


class MeasurementCorrespondenceTests(unittest.TestCase):
    def fixtures(self):
        cirq = dict(format='cirq', sorted_qubits=[dict(dimension=2), dict(dimension=2)],
                    operations=[dict(gate_family='HPowGate', qubits=[0]),
                                dict(measurement_key='z_10', qubits=[1], invert_mask=[]),
                                dict(measurement_key='a_2', qubits=[0], invert_mask=[True])])
        stim = dict(format='stim', qubits=2, measurements=2,
                    operations=[dict(name='H', qubits=[0], inverted=[False], args=[]),
                                dict(name='M', qubits=[1, 0], inverted=[False, True], args=[])])
        return cirq, stim

    def audit(self, cirq, stim):
        from qb013_output_audit import audit_cirq_stim_measurements
        return audit_cirq_stim_measurements(cirq, stim)

    def test_order_is_occurrence_not_key_sort_and_merged_targets(self):
        result = self.audit(*self.fixtures())
        self.assertEqual([x['key'] for x in result['cirq_occurrences']], ['z_10', 'a_2'])
        self.assertEqual([x['qubit'] for x in result['stim_occurrences']], [1, 0])
        self.assertFalse(result['gate_equivalence_verified'])
        self.assertFalse(result['qiskit_destination_mapping_verified'])

    def test_short_invert_mask_pads_false(self):
        cirq, stim = self.fixtures()
        cirq['operations'] = [dict(measurement_key='both', qubits=[1, 0], invert_mask=[True])]
        stim['operations'][1]['inverted'] = [True, False]
        result = self.audit(cirq, stim)
        self.assertEqual([x['key_bit'] for x in result['cirq_occurrences']], [0, 1])
        self.assertEqual([x['inverted'] for x in result['cirq_occurrences']], [True, False])

    def test_repeated_key_and_qubit_preserve_distinct_occurrences(self):
        cirq, stim = self.fixtures()
        cirq['operations'] = [dict(measurement_key='same', qubits=[1], invert_mask=[])] * 2
        stim['operations'][1].update(qubits=[1, 1], inverted=[False, False])
        result = self.audit(cirq, stim)
        self.assertEqual([x['occurrence'] for x in result['cirq_occurrences']], [0, 1])

    def test_reordered_dropped_or_changed_inversion_rejects(self):
        for qubits, mask in (([0, 1], [False, True]), ([1], [False]), ([1, 0], [False, False])):
            cirq, stim = self.fixtures()
            stim['operations'][1].update(qubits=qubits, inverted=mask)
            stim['measurements'] = len(qubits)
            with self.assertRaisesRegex(ValueError, 'MEASUREMENT_OCCURRENCES_CHANGED'):
                self.audit(cirq, stim)

    def test_invalid_domains_masks_and_noisy_measurements_reject(self):
        mutations = [lambda c, s: s.update(qubits=True),
                     lambda c, s: s.update(measurements=True),
                     lambda c, s: c['sorted_qubits'][0].update(dimension=3),
                     lambda c, s: c['operations'][1].update(qubits=[True]),
                     lambda c, s: c['operations'][1].update(qubits=[1, 1]),
                     lambda c, s: c['operations'][1].update(invert_mask=[False, False]),
                     lambda c, s: c['operations'][1].update(invert_mask=[0]),
                     lambda c, s: s['operations'][1].update(inverted=[False, 1]),
                     lambda c, s: s['operations'][1].update(args=[0.01]),
                     lambda c, s: s['operations'][1].update(qubits=[1, 2])]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                cirq, stim = self.fixtures(); mutation(cirq, stim)
                with self.assertRaises(ValueError): self.audit(cirq, stim)

    def test_empty_measurements_cannot_pass_vacuously(self):
        cirq, stim = self.fixtures()
        cirq['operations'] = []; stim.update(operations=[], measurements=0)
        with self.assertRaisesRegex(ValueError, 'MEASUREMENT_OCCURRENCES_CHANGED'):
            self.audit(cirq, stim)


class CombinedStateAuditTests(unittest.TestCase):
    def fixtures(self):
        import math
        from copy import deepcopy
        original,final,records,parsers=ConversionRouteTests().fixtures()
        original['global_phase']=0.0
        original['operations'][:0]=[dict(name='h',qubits=[0],clbits=[],params=[]),
                                    dict(name='cx',qubits=[0,1],clbits=[],params=[]),
                                    dict(name='barrier',qubits=[0,1],clbits=[],params=[])]
        parsers[0]['parsed_circuit']['operations'][:0]=[
            dict(gate_family='HPowGate',qubits=[1],exponent=1,global_shift=0),
            dict(gate_family='CXPowGate',qubits=[1,0],exponent=1,global_shift=0)]
        final['operations'][:0]=[dict(name='H',qubits=[1],inverted=[False],args=[]),
                                 dict(name='CX',qubits=[1,0],inverted=[False,False],args=[]),
                                 dict(name='TICK',qubits=[],inverted=[],args=[])]
        records[0]['input']=deepcopy(original)
        records[1]['output']=deepcopy(parsers[0]['parsed_circuit'])
        records[2]['input']=deepcopy(parsers[0]['parsed_circuit'])
        records[2]['output']=deepcopy(final)
        return [original,final,records,parsers,[1/math.sqrt(2),0,0,1/math.sqrt(2)]]
    def analyze(self, values):
        import qb013_reference
        from qb013_output_audit import analyze_conversion_states
        return analyze_conversion_states(qb013_reference,*values)
    def test_reference_acceptance_with_raw_states_is_not_native_acceptance(self):
        import json
        result=self.analyze(self.fixtures())
        json.dumps(result,allow_nan=False)
        self.assertTrue(result['reference_semantic_acceptance'])
        self.assertFalse(result['native_execution_verified'])
        self.assertFalse(result['overall_semantic_acceptance'])
        self.assertEqual(result['calculated_states']['qiskit']['annotations'][0]['kind'],'barrier')
        self.assertEqual(result['calculated_states']['stim']['annotations'][0]['kind'],'TICK')
        self.assertEqual(result['route']['occurrence_to_clbit'],[2,3])
    def test_matching_route_with_wrong_phase_returns_raw_failed_comparison(self):
        from copy import deepcopy
        values=self.fixtures();circuit=values[3][0]['parsed_circuit']
        circuit['operations'].insert(2,dict(gate_family='ZPowGate',qubits=[0],exponent=1,global_shift=0))
        values[2][1]['output']=deepcopy(circuit);values[2][2]['input']=deepcopy(circuit)
        result=self.analyze(values)
        self.assertFalse(result['reference_semantic_acceptance'])
        self.assertFalse(result['comparisons']['cirq']['equivalent'])
        self.assertTrue(result['comparisons']['qiskit']['equivalent'])
        self.assertTrue(result['comparisons']['stim']['equivalent'])
        self.assertEqual(len(result['calculated_states']['cirq']['state']),4)
    def test_global_phase_is_retained_but_not_claimed_preserved(self):
        from copy import deepcopy
        values=self.fixtures();values[0]['global_phase']=0.4;values[2][0]['input']=deepcopy(values[0])
        result=self.analyze(values)
        self.assertTrue(result['reference_semantic_acceptance'])
        self.assertEqual(result['original_global_phase'],0.4)
        self.assertFalse(result['global_phase_preservation_verified'])


class PostcellProtocolTests(unittest.TestCase):
    """Synthetic checkpoint-protocol tests, not native conversion execution."""
    def setUp(self):
        from copy import deepcopy
        import qb013_reference,qb013_output_audit
        self.reference=qb013_reference;self.audit=qb013_output_audit
        self.base=NotebookCaptureTests();self.base.setUp();self.addCleanup(self.base.doCleanups)
        self.capture=self.base.capture;self.namespace=self.base.namespace
        self.capture.controller.snapshot=deepcopy
        self.base.api.stim_converter=self.base.base.conversion
        self.namespace.update(graph=self.base.graph,conversion=self.base.base.edge)
        self.capture.install()
    def check(self,index):return self.capture.check_after(index,self.reference,self.audit)
    def registration(self):
        self.base.graph.add_conversion(self.base.base.edge,overwrite=True)
        self.check(13)
        self.base.graph.has_path('qiskit','stim')
        self.check(15)
    def observed_conversion(self, bad_phase=False):
        from copy import deepcopy
        original,final,conversions,parsers,_=CombinedStateAuditTests().fixtures()
        if bad_phase:
            circuit=parsers[0]['parsed_circuit']
            circuit['operations'].insert(2,dict(gate_family='ZPowGate',qubits=[0],exponent=1,global_shift=0))
            conversions[1]['output']=deepcopy(circuit);conversions[2]['input']=deepcopy(circuit)
        self.namespace.update(qiskit_circuit=original,stim_circuit=final,transpile=self.capture.controller.wrapper)
        self.capture.controller.public_alias_seen=True
        self.capture.controller.records.append(dict(state='succeeded',target='stim',input=deepcopy(original),
            input_after=deepcopy(original),output=deepcopy(final),conversions=conversions,parsers=parsers,
            scopes_restored=True,conversion_diagnostics=[],parser_diagnostics=[]))
    def test_ordered_original_steps_leave_sampling_for_host(self):
        self.registration();self.observed_conversion();self.check(19);last=self.check(22)
        self.assertTrue(last['original_sample_output_pending_host_audit'])
        self.assertFalse(last['native_execution_verified'])
        self.assertEqual([r['after_original_index'] for r in self.capture.controller.postcells],[13,15,19,22])
        self.capture.restore();self.capture.require_complete()
    def test_skipping_or_repeating_step_rejected(self):
        with self.assertRaisesRegex(ValueError,'QB013_POSTCELL_ORDER'):self.check(19)
        self.base.graph.add_conversion(self.base.base.edge,overwrite=True);self.check(13)
        with self.assertRaisesRegex(ValueError,'QB013_POSTCELL_ORDER'):self.check(13)
    def test_unobserved_or_wrong_cached_conversion_rejected(self):
        self.base.graph.add_conversion(self.base.base.edge,overwrite=True)
        self.namespace['conversion']=self.base.base.Edge()
        with self.assertRaisesRegex(ValueError,'ORIGINAL_CONVERSION_CACHED'):self.check(13)
        self.assertEqual(self.capture.controller.postcells[0]['state'],'failed')
    def test_missing_exact_path_call_cannot_pass(self):
        self.base.graph.add_conversion(self.base.base.edge,overwrite=True);self.check(13)
        self.base.graph.has_path('other','stim')
        with self.assertRaisesRegex(ValueError,'ORIGINAL_PATH_TRUE'):self.check(15)
    def test_semantic_failure_retained_before_postcell_raises(self):
        import json
        self.registration();self.observed_conversion(bad_phase=True)
        with self.assertRaisesRegex(ValueError,'REFERENCE_STATE_MISMATCH'):self.check(19)
        payload=json.loads(self.base.base.path.read_bytes())['payload']
        last=payload['postcells'][-1]
        self.assertEqual(last['state'],'failed')
        self.assertFalse(last['analysis']['comparisons']['cirq']['equivalent'])
        self.assertEqual(len(last['analysis']['calculated_states']['cirq']['state']),4)
        with self.assertRaisesRegex(ValueError,'QB013_POSTCELL_ORDER'):self.check(22)
    def test_new_checkpoint_failure_stops_same_postcell(self):
        self.base.graph.add_conversion(self.base.base.edge,overwrite=True)
        class Broken:
            def write(self,payload):raise OSError('disk failed now')
        self.capture.controller.journal=Broken()
        with self.assertRaisesRegex(ValueError,'AUTHORED_TRANSPILE_CAPTURE_FAILED'):self.check(13)
        self.assertEqual(self.capture.controller.postcells[-1]['state'],'failed')


class NativeStateComparisonTests(unittest.TestCase):
    def setUp(self):
        import importlib.util
        from pathlib import Path
        spec = importlib.util.spec_from_file_location('qb013_native_test', Path(__file__).parent/'witnesses/qb013.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        self.module = module
        self.compare = module.compare_native_state
    def test_float32_bell_rounding_retained_without_renormalization(self):
        import math, struct
        exact = 1/math.sqrt(2)
        rounded = struct.unpack('f', struct.pack('f', exact))[0]
        result = self.compare([exact, 0, 0, exact], [rounded, 0, 0, rounded], [0, 1], 'complex64')
        self.assertTrue(result['equivalent']); self.assertFalse(result['renormalized'])
        self.assertEqual(result['actual_state'][0][0], rounded)
        self.assertGreater(result['max_density_error'], 1e-10)
        with self.assertRaisesRegex(ValueError, 'NATIVE_STATE_NORMALIZATION'):
            self.compare([exact, 0, 0, exact], [rounded, 0, 0, rounded], [0, 1], 'complex128')
    def test_phase_coherence_and_asymmetric_mapping(self):
        import math
        a = 1/math.sqrt(2)
        self.assertFalse(self.compare([a, 0, 0, a], [a, 0, 0, -a], [0, 1], 'complex64')['equivalent'])
        self.assertTrue(self.compare([0, 1, 0, 0], [0, 0, 1j, 0], [1, 0], 'complex128')['equivalent'])
        self.assertFalse(self.compare([0, 1, 0, 0], [0, 0, 1, 0], [0, 1], 'complex64')['equivalent'])
    def test_invalid_observations_rejected_instead_of_normalized(self):
        for actual in ([2, 0], [float('nan'), 0], [float('inf'), 0], [True, 0]):
            with self.assertRaisesRegex(ValueError, 'NATIVE_STATE_'):
                self.compare([1, 0], actual, [0], 'complex64')
        for mapping in ([True], [], [1], [0, 0]):
            with self.assertRaisesRegex(ValueError, 'NATIVE_STATE_MAPPING'):
                self.compare([1, 0], [1, 0], mapping, 'complex64')
        with self.assertRaisesRegex(ValueError, 'NATIVE_STATE_PRECISION'):
            self.compare([1, 0], [1, 0], [0], 'anything')
    def test_expected_state_remains_strict_even_for_float32_observation(self):
        with self.assertRaisesRegex(ValueError, 'NATIVE_STATE_NORMALIZATION'):
            self.compare([1.0000001, 0], [1, 0], [0], 'complex64')


class NativeObservationTests(unittest.TestCase):
    setUp = NativeStateComparisonTests.setUp
    def fixture(self):
        from types import SimpleNamespace as NS
        from unittest.mock import Mock
        from copy import deepcopy
        values = CombinedStateAuditTests().fixtures()
        class Vector:
            def __init__(self, dtype): self.dtype = dtype
            def tolist(self): return values[-1][:]
        class Measure: pass
        measurement = NS(gate=Measure()); gate = NS(gate=object())
        class Cirq:
            def all_qubits(self): return {1, 0}
            def __iter__(self): return iter([NS(operations=[gate]), NS(operations=[measurement])])
        q = NS(qubits=[0, 1], num_qubits=2)
        q.remove_final_measurements = Mock(return_value=NS(qubits=q.qubits[:], num_qubits=2, data=[]))
        s = NS(copy=Mock(return_value=object()))
        programs = dict(qiskit=q, cirq=Cirq(), stim=s)
        snapshots = {id(q): values[0], id(programs['cirq']): values[3][0]['parsed_circuit'], id(s): values[1]}
        def snapshot(program): return deepcopy(snapshots[id(program)])
        class Tableau:
            def __len__(self): return 2
            def to_state_vector(self, *, endian):
                self_test.assertEqual(endian, 'little'); return Vector('complex64')
        self_test = self
        simulator = NS(simulate=Mock(return_value=NS(final_state_vector=Vector('complex128'))))
        api = NS(Statevector=NS(from_instruction=Mock(return_value=NS(data=Vector('complex128')))),
                 CirqCircuit=lambda moments: list(moments), CirqMoment=lambda ops: list(ops),
                 MeasurementGate=Measure, complex128=object(), Simulator=Mock(return_value=simulator),
                 Tableau=NS(from_circuit=Mock(return_value=Tableau())))
        return api, programs, snapshots, snapshot, simulator, gate
    def observe(self, fixture):
        from copy import deepcopy
        import qb013_reference
        self.checkpoints = []
        api, programs, _, snapshot, _, _ = fixture
        return self.module.observe_native_states(api, qb013_reference, snapshot, programs,
                                                  lambda report:self.checkpoints.append(deepcopy(report)))
    def test_copies_explicit_order_and_measurement_filter_without_native_imports(self):
        fixture = self.fixture(); api, programs, _, _, simulator, gate = fixture
        report = self.observe(fixture)
        self.assertEqual(report['state'], 'succeeded')
        self.assertFalse(report['overall_semantic_acceptance'])
        programs['qiskit'].remove_final_measurements.assert_called_once_with(inplace=False)
        args, kwargs = simulator.simulate.call_args
        self.assertEqual(args[0], [[gate], []]); self.assertEqual(kwargs, dict(qubit_order=[1, 0], initial_state=0))
        api.Simulator.assert_called_once_with(dtype=api.complex128)
        api.Tableau.from_circuit.assert_called_once_with(programs['stim'].copy.return_value,
            ignore_measurement=True, ignore_noise=False, ignore_reset=False)
        self.assertTrue(all(row['original_unchanged'] for row in report['observations'].values()))
    def test_primary_native_error_and_mutation_both_retained_and_stop(self):
        fixture = self.fixture(); api, programs, snapshots, _, _, _ = fixture
        def fail(_):
            snapshots[id(programs['qiskit'])]['global_phase'] = 1.0
            raise RuntimeError('native failure')
        api.Statevector.from_instruction.side_effect = fail
        report = self.observe(fixture)
        self.assertEqual(report['state'], 'failed')
        self.assertEqual(list(report['observations']), ['qiskit'])
        self.assertEqual(report['observations']['qiskit']['error']['message'], 'native failure')
        self.assertEqual(report['errors'][0]['type'], 'NativeObservationMutatedOriginal')
        api.Simulator.assert_not_called()
    def test_unsupported_semantics_fail_before_any_native_copy(self):
        fixture = self.fixture(); _, programs, snapshots, _, _, _ = fixture
        snapshots[id(programs['qiskit'])]['operations'].append(dict(name='x', qubits=[0], clbits=[], params=[]))
        with self.assertRaises(ValueError): self.observe(fixture)
        programs['qiskit'].remove_final_measurements.assert_not_called()
    def test_native_mismatch_keeps_raw_state_and_fails_acceptance(self):
        fixture = self.fixture(); api = fixture[0]
        from types import SimpleNamespace as NS
        api.Statevector.from_instruction.return_value = NS(data=NS(dtype='complex128', tolist=lambda:[1,0,0,0]))
        report = self.observe(fixture)
        self.assertEqual(report['state'], 'failed')
        row = report['observations']['qiskit']
        self.assertEqual(row['raw_state'], [[1,0],[0,0],[0,0],[0,0]])
        self.assertFalse(row['comparison']['equivalent'])
    def test_later_backend_mutating_previously_checked_original_is_rejected(self):
        fixture = self.fixture(); _, programs, snapshots, _, simulator, _ = fixture
        result = simulator.simulate.return_value
        def simulate(*args, **kwargs):
            snapshots[id(programs['qiskit'])]['global_phase'] = 1.0
            return result
        simulator.simulate.side_effect = simulate
        report = self.observe(fixture)
        self.assertEqual(report['state'], 'failed')
        self.assertTrue(report['observations']['qiskit']['original_unchanged'])
        self.assertIn(dict(program='qiskit', stage='final_snapshot', type='NativeObservationMutatedOriginal'),
                      report['errors'])
    def test_nonfinite_native_failure_persists_with_strict_json_checkpoint(self):
        import json, qb013_reference
        from types import SimpleNamespace as NS
        for value, tag in ((float('nan'), 'NaN'), (float('inf'), 'Infinity'), (-float('inf'), '-Infinity')):
            for amplitude in (complex(value, 0), complex(0, value)):
                fixture = self.fixture(); api, programs, _, snapshot, _, _ = fixture
                api.Statevector.from_instruction.return_value = NS(data=NS(dtype='complex128',
                    tolist=lambda:[amplitude, 0, 0, 0]))
                persisted = []
                result = self.module.observe_native_states(api, qb013_reference, snapshot, programs,
                    lambda report:persisted.append(json.loads(json.dumps(report, allow_nan=False))))
                self.assertEqual(result['state'], 'failed')
                row = persisted[-1]['observations']['qiskit']
                self.assertEqual(row['error']['message'], 'NATIVE_STATE_NONFINITE')
                self.assertIn({'nonfinite':tag}, row['raw_state'][0])
                self.assertTrue(row['original_unchanged'])
                self.assertEqual(list(persisted[-1]['observations']), ['qiskit'])
                api.Simulator.assert_not_called()


class AuthoredControlTests(unittest.TestCase):
    setUp = NativeStateComparisonTests.setUp
    def controls(self, reference=None):
        import qb013_reference
        class Circuit:
            def __init__(self, n, c):
                self.snapshot = dict(format='qiskit', qubits=n, clbits=c, global_phase=0.0, operations=[])
            def gate(self, name, qubits, clbits=()):
                self.snapshot['operations'].append(dict(name=name, qubits=list(qubits), clbits=list(clbits), params=[]))
            def x(self, q): self.gate('x', [q])
            def h(self, q): self.gate('h', [q])
            def z(self, q): self.gate('z', [q])
            def cx(self, q, r): self.gate('cx', [q, r])
            def measure(self, q, c): self.gate('measure', [q], [c])
        return self.module.build_control_cases(Circuit, reference or qb013_reference)
    def test_all_eighteen_circuits_match_independent_states_and_walsh_expectations(self):
        import qb013_reference
        controls = self.controls()
        self.assertEqual(len(controls), 18); self.assertEqual(len({case['id'] for _,case in controls}), 18)
        self.assertEqual(sum(case['family']=='Deutsch-Jozsa' for _,case in controls), 8)
        self.assertEqual(sum(case['family']=='Bernstein-Vazirani' for _,case in controls), 6)
        for circuit, case in controls:
            state = qb013_reference.state_from_snapshot(circuit.snapshot)
            self.assertTrue(qb013_reference.compare_states(case['expected_state'], state['state'])['equivalent'])
            self.assertEqual([x['qubits'][0] for x in state['measurements']], case['measured_qubits'])
    def test_nonlinear_oracle_is_explicitly_unsupported(self):
        from types import SimpleNamespace
        reference = SimpleNamespace(cases=lambda:[dict(qubits=2,truth_table=[0,0,0,1])])
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_NONAFFINE_CONTROL_ORACLE'):
            self.controls(reference)
    def test_mapping_deterministic_algorithms_and_asymmetric_rows(self):
        for _, case in self.controls():
            if len(case['expected_probabilities']) != 1: continue
            outcome = next(iter(case['expected_probabilities'])); mapping = list(reversed(case['measured_qubits']))
            row = [bool((outcome >> q) & 1) for q in mapping]
            result = self.module.audit_authored_samples([row[:] for _ in range(case['shots'])], mapping, case)
            self.assertTrue(result['accepted']); self.assertEqual(sum(result['counts'].values()), case['shots'])
            wrong = [row[:] for _ in range(case['shots'])]; wrong[-1][0] = not wrong[-1][0]
            self.assertFalse(self.module.audit_authored_samples(wrong, mapping, case)['accepted'])
    def test_bell_frequency_is_additional_authored_evidence_not_coherence(self):
        case = dict(self.controls()[2][1]); rows = [[False,False]]*2048+[[True,True]]*2048
        result = self.module.audit_authored_samples(rows,[0,1],case)
        self.assertTrue(result['accepted']); self.assertFalse(result['original_sample'])
        self.assertFalse(result['coherence_verified'])
        self.assertFalse(self.module.audit_authored_samples([[False,False]]*4096,[0,1],case)['accepted'])
    def test_rows_and_mapping_cannot_be_truncated_or_coerced(self):
        case = self.controls()[0][1]; good = [[True,False]]*4096
        for rows in (good[:-1], good+[[True,False]], [[1,0]]*4096, [[True]]*4096):
            with self.assertRaisesRegex(ValueError, 'AUTHORED_SAMPLE_'):
                self.module.audit_authored_samples(rows,[0,1],case)
        for mapping in ([False,True], [0,0], [0]):
            with self.assertRaisesRegex(ValueError, 'AUTHORED_SAMPLE_MAPPING'):
                self.module.audit_authored_samples(good,mapping,case)


class ControlRunnerTests(unittest.TestCase):
    setUp = NativeStateComparisonTests.setUp
    def fixture(self, failed_index=None, sample_override=None):
        from types import SimpleNamespace as NS
        from unittest.mock import Mock
        from copy import deepcopy
        controls = AuthoredControlTests(); controls.setUp()
        prepared = controls.controls(); pairs = []; calls = []; journals = []; checkpoints = []
        def snapshot(program): return dict(identity=program.identity)
        for i, (_, case) in enumerate(prepared):
            program = NS(identity='qiskit'+str(i), index=i, case=case)
            pairs.append((program, case))
        class Controller:
            def __init__(self, original, api, snap, journal):
                self.snapshot = snap; self.records = []; self.journal = journal
            def wrapper(self, program, target, conversion_graph=None):
                calls.append((program.index, target, conversion_graph)); case = program.case
                if program.index == failed_index: raise RuntimeError('authored conversion failed')
                outcomes = list(case['expected_probabilities']); mapping = case['measured_qubits']
                rows = [[bool((outcomes[j % len(outcomes)] >> q) & 1) for q in mapping] for j in range(case['shots'])]
                if sample_override is not None: rows = sample_override
                result = NS(identity='stim'+str(program.index), compile_sampler=Mock(
                    return_value=NS(sample=Mock(return_value=NS(tolist=lambda:deepcopy(rows))))))
                self.outputs = ('qasm', NS(identity='cirq'+str(program.index)), result)
                self.records = [dict(state='succeeded', input=snapshot(program), input_after=snapshot(program),
                    output=snapshot(result), conversions=[dict(mapping=mapping)], parsers=[],graph_before={},graph_after={})]
                return result
            def require_complete(self): pass
            def verified_native_outputs(self, ordinal): return self.outputs
        capture = NS(api=NS(QuantumCircuit=object(), transpile=object()),
                     controller=Controller(None,None,snapshot,None), require_complete=Mock())
        audit = NS(analyze_conversion_states=lambda ref, before, after, conversions, parsers, expected:
            dict(reference_semantic_acceptance=True, route=dict(occurrence_to_logical=conversions[0]['mapping'])))
        def journal(index): journals.append(index); return object()
        def checkpoint(report):
            import json
            checkpoints.append(json.loads(json.dumps(report, allow_nan=False)))
        return pairs,capture,audit,journal,checkpoint,calls,journals,checkpoints
    def test_all_controls_use_separate_journals_and_preserve_original_records(self):
        from unittest.mock import patch
        fixture = self.fixture(); pairs,capture,audit,journal,checkpoint,calls,journals,saved = fixture
        graph = object()
        with patch.object(self.module,'build_control_cases',return_value=pairs), \
                patch.object(self.module,'observe_native_states',return_value=dict(state='succeeded')) as native:
            result = self.module.run_authored_controls(capture,graph,object(),object(),audit,journal,checkpoint)
        self.assertEqual(result['state'],'succeeded'); self.assertEqual(journals,list(range(18)))
        self.assertEqual(capture.controller.records,[])
        self.assertTrue(all(call[2] is graph for call in calls)); self.assertEqual(native.call_count,18)
        self.assertEqual([c.kwargs['required_qubits'] for c in native.call_args_list],[case['qubits'] for _,case in pairs])
        self.assertFalse(result['original_notebook_execution']); self.assertEqual(saved[-1]['state'],'succeeded')
    def test_conversion_failure_stops_without_replacing_primary_error(self):
        from unittest.mock import patch
        fixture = self.fixture(failed_index=1); pairs,capture,audit,journal,checkpoint,calls,journals,saved = fixture
        with patch.object(self.module,'build_control_cases',return_value=pairs), \
                patch.object(self.module,'observe_native_states',return_value=dict(state='succeeded')):
            result = self.module.run_authored_controls(capture,object(),object(),object(),audit,journal,checkpoint)
        self.assertEqual(result['state'],'failed'); self.assertEqual(journals,[0,1])
        self.assertEqual(result['controls'][-1]['error']['message'],'authored conversion failed')
        self.assertEqual(result['controls'][0]['state'],'succeeded'); self.assertEqual(len(calls),2)
    def test_native_failure_stops_before_sampling_or_next_conversion(self):
        from unittest.mock import patch
        fixture = self.fixture(); pairs,capture,audit,journal,checkpoint,calls,journals,saved = fixture
        with patch.object(self.module,'build_control_cases',return_value=pairs), \
                patch.object(self.module,'observe_native_states',return_value=dict(state='failed')):
            result = self.module.run_authored_controls(capture,object(),object(),object(),audit,journal,checkpoint)
        self.assertEqual(result['state'],'failed'); self.assertEqual(len(calls),1)
        self.assertNotIn('sampling',result['controls'][0])
    def test_malformed_sampling_is_persisted_before_rejection(self):
        from unittest.mock import patch
        for rows in ([[1,0]]*4096, [[True]]*4096, [[True,False]]*3, [[float('nan'),False]]*4096):
            fixture = self.fixture(sample_override=rows)
            pairs,capture,audit,journal,checkpoint,calls,journals,saved = fixture
            with patch.object(self.module,'build_control_cases',return_value=pairs), \
                    patch.object(self.module,'observe_native_states',return_value=dict(state='succeeded')):
                result = self.module.run_authored_controls(capture,object(),object(),object(),audit,journal,checkpoint)
            self.assertEqual(result['state'],'failed'); self.assertEqual(len(calls),1)
            row = saved[-1]['controls'][0]
            self.assertEqual(row['raw_samples'],self.module.sample_evidence(rows))
            self.assertIn('sample_container',row)
            self.assertRegex(row['error']['message'],'AUTHORED_SAMPLE_')
            self.assertTrue(any('raw_samples' in state['controls'][0] and
                state['controls'][0]['state']=='running' for state in saved if state['controls']))


class WrappedErrorTests(unittest.TestCase):
    setUp = NativeStateComparisonTests.setUp
    def run_case(self, variant='valid'):
        from types import SimpleNamespace as NS
        from unittest.mock import Mock
        import json
        class ConversionError(Exception): pass
        class Gate:
            def __init__(self, exponent): self.exponent=exponent
            def on(self,qid): return 'T-operation'
        expected = ("Don't know how to translate 'T-operation' into stim gates.\n"
                    "- It doesn't have a _decompose_ method that returns stim-compatible operations.\n"
                    "- It doesn't have a _stim_conversion_ method.\n")
        calls=[]; saved=[]
        class Controller:
            def __init__(self, original, api, snapshot, journal): self.snapshot=snapshot; self.records=[]
            def wrapper(self, program, target, **kwargs):
                calls.append(kwargs)
                edge=dict(source='cirq',target='stim',state='failed',function_identities=['cirq_to_stim'],
                    single_program_positional_call=True,error=dict(type='TypeError',message=expected))
                self.records=[dict(state='failed',input=program,input_after=program,
                    graph_before={},graph_after={},conversions=[edge])]
                if variant=='wrong-inner': edge['error']['message']='different failure'
                if variant=='mutated': self.records[0]['input_after']='changed'
                if variant=='fallback': self.records[0]['conversions'].append(dict(edge))
                if variant=='success': self.records[0]['state']='succeeded'; return object()
                error_type=TypeError if variant=='wrong-outer' else ConversionError
                raise error_type("Failed to convert 'cirq' to 'stim'\nTypeError: "+expected)
            def require_complete(self): pass
        api=NS(converter_module=NS(ProgramConversionError=ConversionError),ZPowGate=Gate,transpile=object())
        capture=NS(api=api,controller=Controller(None,None,lambda x:x,None),require_complete=Mock())
        native=NS(ProgramConversionError=ConversionError,CirqCircuit=lambda operation:operation)
        result=self.module.observe_wrapped_nonclifford(capture,object(),native,object(),object(),
            lambda report:saved.append(json.loads(json.dumps(report,allow_nan=False))))
        return result,calls,saved,capture
    def test_actual_inner_and_outer_errors_and_explicit_authored_limits(self):
        result,calls,saved,capture=self.run_case()
        self.assertEqual(result['state'],'succeeded'); self.assertEqual(len(calls),1)
        self.assertEqual(calls[0]['max_path_attempts'],1); self.assertEqual(calls[0]['max_path_depth'],1)
        self.assertEqual(capture.controller.records,[])
        self.assertIn('actual_error',saved[-1]); self.assertEqual(len(result['conversion_calls']),1)
    def test_wrong_error_fallback_mutation_and_unexpected_success_rejected(self):
        for variant in ('wrong-inner','wrong-outer','fallback','mutated','success'):
            result,_,saved,_=self.run_case(variant)
            self.assertEqual(result['state'],'failed',variant)
            self.assertIn('verification_error',saved[-1]); self.assertIn('conversion_calls',saved[-1])


class NotebookWitnessTests(unittest.TestCase):
    setUp = NativeStateComparisonTests.setUp
    def fixture(self):
        from types import SimpleNamespace as NS
        from unittest.mock import Mock
        import json
        self.saved=[]
        outer=self
        class Journal:
            def __init__(self,path): self.path=path
            def write(self,report): outer.saved.append(json.loads(json.dumps(report,allow_nan=False)))
        q=NS(name='qiskit'); s=NS(name='stim'); c=NS(all_qubits=lambda:[0,1])
        record=dict(input='qiskit',output='stim',conversions=[],parsers=[])
        controller=NS(journal=Journal(None),snapshot=lambda value:value.name,records=[record],
            postcells=[dict(after_original_index=i,state='succeeded') for i in (13,15,19,22)],
            verified_native_outputs=Mock(return_value=('qasm',c,s)))
        capture=NS(controller=controller,require_complete=Mock())
        audit=NS(analyze_conversion_states=Mock(return_value=dict(reference_semantic_acceptance=True)))
        return capture,q,s,audit
    def run_mocked(self,fixture,fail_native=False):
        from types import SimpleNamespace as NS
        from unittest.mock import patch
        capture,q,s,audit=fixture
        def native(*args,**kwargs):
            result=dict(state='failed' if fail_native else 'succeeded'); args[4](result); return result
        def controls(*args,**kwargs):
            result=dict(state='succeeded'); args[6](result); return result
        def negative(*args,**kwargs):
            result=dict(state='succeeded'); args[5](result); return result
        with patch.object(self.module,'bind_native_api',return_value=NS(source_evidence={})) as bind, \
                patch.object(self.module,'observe_native_states',side_effect=native), \
                patch.object(self.module,'run_authored_controls',side_effect=controls) as run_controls, \
                patch.object(self.module,'observe_wrapped_nonclifford',side_effect=negative):
            result=self.module.run_notebook_witness(capture,object(),q,s,object(),audit)
            return result,bind.call_count,run_controls.call_count
    def test_success_is_native_only_with_all_raw_component_reports(self):
        result,bindings,controls=self.run_mocked(self.fixture())
        self.assertTrue(result['native_accepted']); self.assertFalse(result['whole_notebook_complete'])
        self.assertTrue(result['original_stdout_pending_host_audit']); self.assertEqual((bindings,controls),(1,1))
        for key in ('original_reference_analysis','original_native_analysis','controls','wrapped_error'):
            self.assertIn(key,self.saved[-1])
    def test_failed_original_native_stops_authored_controls(self):
        result,_,controls=self.run_mocked(self.fixture(),fail_native=True)
        self.assertFalse(result['native_accepted']); self.assertEqual(controls,0)
        self.assertEqual(self.saved[-1]['error']['message'],'ORIGINAL_NATIVE_MISMATCH')
    def test_incomplete_original_protocol_stops_before_sdk_binding(self):
        fixture=self.fixture(); fixture[0].controller.postcells.pop()
        result,bindings,controls=self.run_mocked(fixture)
        self.assertFalse(result['native_accepted']); self.assertEqual((bindings,controls),(0,0))


class AuthoredDispositionTests(unittest.TestCase):
    def fixture(self):
        import json,hashlib,importlib.util
        from pathlib import Path
        root=Path(__file__).parent; contract=json.loads((root/'contracts/qb013.json').read_bytes())
        spec=importlib.util.spec_from_file_location('authored_disposition_engine',root/'execution.py')
        engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
        cells=[];records=[]
        def append(text,role=None,original=None,kind='code',after=None):
            cells.append(dict(source=text,cell_type=kind,metadata=dict(tags=['authored-'+role]) if role else {},outputs=[]))
            record=dict(index=len(records),original_index=original,authored_role=role,type=kind,
                source_sha256=hashlib.sha256(text.encode()).hexdigest(),state='succeeded' if kind=='code' else 'not_executable')
            if after is not None:record['after_original_index']=after
            records.append(record)
        def source(key): return (root/key['path']).read_text(encoding='utf-8')
        append(contract['preamble'],'preamble')
        append(source(contract['observer_lifecycle']['bootstrap']),'observer-bootstrap')
        append(engine._setup_observer(contract['setup']['commands']),'setup-observer')
        for index in range(24):
            append('original'+str(index),original=index,kind=contract['source']['cells'][index]['type'])
            if index==0:append(engine.SETUP_CHECK,'setup-check')
            for row in contract['post_cell_observers']:
                if row['after_original_index']==index:append(source(row),row['role'],after=index)
        append(source(contract['observer_lifecycle']['cleanup']),'observer-cleanup')
        append(source(contract['witness']),'independent-witness')
        return dict(cells=cells),records,contract
    def audit(self,fixture):
        from qb013_output_audit import audit_authored_dispositions
        return audit_authored_dispositions(*fixture)
    def test_every_authored_source_role_and_position_is_bound(self):
        result=self.audit(self.fixture())
        self.assertEqual(result['authored_cells'],10)
        self.assertFalse(result['overall_semantic_acceptance'])
    def test_changed_authored_code_cannot_hide_behind_success(self):
        fixture=self.fixture();fixture[0]['cells'][-1]['source']+='\n#changed'
        with self.assertRaisesRegex(ValueError,'AUTHORED_CELL_EVIDENCE'):self.audit(fixture)
    def test_reordered_or_missing_authored_cells_rejected(self):
        fixture=self.fixture();fixture[1][0]['authored_role']='observer-bootstrap'
        with self.assertRaisesRegex(ValueError,'AUTHORED_CELL_POSITION'):self.audit(fixture)
        fixture=self.fixture();fixture[1].pop()
        with self.assertRaisesRegex(ValueError,'AUTHORED_CELL_COUNT'):self.audit(fixture)
    def test_failed_hidden_error_and_wrong_postcell_attachment_rejected(self):
        fixture=self.fixture();fixture[1][-2]['state']='failed'
        with self.assertRaisesRegex(ValueError,'AUTHORED_CELL_EVIDENCE'):self.audit(fixture)
        fixture=self.fixture();fixture[0]['cells'][-1]['outputs']=[dict(output_type='error')]
        with self.assertRaisesRegex(ValueError,'AUTHORED_CELL_EVIDENCE'):self.audit(fixture)
        fixture=self.fixture();row=next(row for row in fixture[1] if row.get('after_original_index')==13)
        row['after_original_index']=15
        with self.assertRaisesRegex(ValueError,'AUTHORED_CELL_EVIDENCE'):self.audit(fixture)


class BundleReaderTests(unittest.TestCase):
    def fixture(self):
        import tempfile,json,hashlib
        from pathlib import Path
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
        contract=root/'contract.json';contract.write_text(json.dumps(dict(id='qb013',route='notebook')))
        names=['setup-evidence.json','qb013-preamble.json','qb013-capture.json','qb013-witness.json',
               'qb013-wrapped-error.json']+[f'qb013-control-{i:02d}.json' for i in range(18)]
        artifacts={}
        for name in names:
            raw=b'{}';(root/name).write_bytes(raw)
            artifacts[name]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        (root/'engine-result.json').write_text(json.dumps(dict(output_artifacts=artifacts)))
        for name in ('executed.ipynb','cells.json','kernel.json'):(root/name).write_bytes(b'{}')
        return root,contract,hashlib.sha256(contract.read_bytes()).hexdigest()
    def read(self,fixture):
        from qb013_output_audit import read_execution_bundle
        return read_execution_bundle(*fixture)
    def test_exact_artifact_set_bound_without_semantic_claim(self):
        result=self.read(self.fixture())
        self.assertEqual(len(result['file_bindings']),27)
        self.assertFalse(result['overall_semantic_acceptance'])
    def test_changed_contract_or_artifact_rejected(self):
        f=self.fixture();f[1].write_bytes(f[1].read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'BUNDLE_CONTRACT_CHANGED'):self.read(f)
        f=self.fixture();(f[0]/'qb013-control-00.json').write_bytes(b'{"changed":true}')
        with self.assertRaisesRegex(ValueError,'BUNDLE_ARTIFACT_CHANGED'):self.read(f)
    def test_missing_or_traversing_metadata_names_rejected(self):
        import json
        for replacement in (None,'../outside.json'):
            f=self.fixture();path=f[0]/'engine-result.json';value=json.loads(path.read_bytes())
            old=value['output_artifacts'].pop('qb013-control-00.json')
            if replacement:value['output_artifacts'][replacement]=old
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError,'BUNDLE_ARTIFACT_SET'):self.read(f)
    def test_ambiguous_or_nonfinite_json_is_rejected_before_semantics(self):
        for raw,label in ((b'{"output_artifacts":{},"output_artifacts":{}}','DUPLICATE'),
                          (b'{"output_artifacts":NaN}','NONFINITE')):
            f=self.fixture();(f[0]/'engine-result.json').write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'BUNDLE_'+label):self.read(f)
    def test_bounded_reader_never_requests_whole_file(self):
        from qb013_output_audit import _read_bounded_bytes
        from unittest.mock import patch,Mock
        stream=Mock();stream.read.return_value=b'abcd'
        handle=Mock();handle.__enter__=Mock(return_value=stream);handle.__exit__=Mock(return_value=False)
        with patch('pathlib.Path.open',return_value=handle):
            with self.assertRaisesRegex(ValueError,'BUNDLE_ARTIFACT_TOO_LARGE'):
                _read_bounded_bytes('synthetic',3)
        stream.read.assert_called_once_with(4)
    def test_initial_reads_and_rechecks_do_not_use_unbounded_read_bytes(self):
        from unittest.mock import patch
        f=self.fixture()
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('unbounded read')):
            self.assertEqual(len(self.read(f)['file_bindings']),27)


class SetupCaptureAuditTests(unittest.TestCase):
    def fixture(self):
        from copy import deepcopy
        journal=lambda payload:dict(format_version=1,revision=1,payload=payload)
        original,final,records,parsers,_=CombinedStateAuditTests().fixtures()
        call=dict(state='succeeded',scopes_restored=True,conversion_diagnostics=[],parser_diagnostics=[],
                  input=original,input_after=deepcopy(original),output=final,graph_before={},graph_after={})
        capture=dict(active=False,diagnostics=[],public_hooks_restored=True,transpile_calls=[call],
                     postcells=[dict(after_original_index=i,state='succeeded') for i in (13,15,19,22)])
        command='install qbraid qiskit stimcirq ply matplotlib'
        docs={'kernel.json':dict(executable='X:/env/python.exe'),
              'setup-evidence.json':dict(accepted=True,before={'example':{'version':'1'}},after={'example':{'version':'1'}},
                  commands=[dict(command='"X:/env/python.exe" -m pip '+command,exit_code=0)]),
              'qb013-preamble.json':dict(QISKIT_IGNORE_USER_SETTINGS=dict(authored_value='TRUE')),
              'qb013-capture.json':journal(capture),'qb013-witness.json':journal(dict(state='succeeded',native_accepted=True))}
        return dict(documents=docs,contract=dict(setup=dict(commands=[command])))
    def audit(self,bundle):
        from qb013_output_audit import audit_setup_and_capture
        return audit_setup_and_capture(bundle)
    def test_metadata_scope_explicitly_excludes_module_bytes_and_semantics(self):
        result=self.audit(self.fixture())
        self.assertTrue(result['setup_metadata_unchanged']); self.assertTrue(result['hooks_restored'])
        self.assertFalse(result['module_bytes_verified']); self.assertFalse(result['overall_semantic_acceptance'])
    def test_setup_drift_wrong_executable_or_boolean_exitcode_rejected(self):
        for kind in ('drift','command','bool'):
            f=self.fixture();setup=f['documents']['setup-evidence.json']
            if kind=='drift':setup['after']['example']['version']='2'
            elif kind=='command':setup['commands'][0]['command']='fake pip'
            else:setup['commands'][0]['exit_code']=False
            with self.assertRaisesRegex(ValueError,'SETUP_'):self.audit(f)
    def test_failed_or_unrestored_capture_and_incomplete_postcells_rejected(self):
        for kind in ('diagnostics','hooks','postcells','revision'):
            f=self.fixture();journal=f['documents']['qb013-capture.json'];capture=journal['payload']
            if kind=='diagnostics':capture['diagnostics'].append({'error':'failed'})
            elif kind=='hooks':capture['public_hooks_restored']=False
            elif kind=='postcells':capture['postcells'].pop()
            else:journal['revision']=True
            with self.assertRaisesRegex(ValueError,'CAPTURE_'):self.audit(f)


class SavedNativeAuditTests(unittest.TestCase):
    def fixture(self):
        import qb013_reference
        from copy import deepcopy
        original,final,_,parsers,_=CombinedStateAuditTests().fixtures()
        programs=dict(qiskit=original,cirq=parsers[0]['parsed_circuit'],stim=final)
        report=dict(state='succeeded',errors=[],original_snapshots=deepcopy(programs),
                    final_original_snapshots=deepcopy(programs),observations={})
        for name,program in programs.items():
            vector=qb013_reference.state_from_snapshot(program)['state']
            report['observations'][name]=dict(state='succeeded',dtype='complex64' if name=='stim' else 'complex128',
                original_unchanged=True,original_snapshot_after=deepcopy(program),
                raw_state=[[complex(x).real,complex(x).imag] for x in vector],comparison=dict(equivalent=True))
        return report,qb013_reference,programs
    def audit(self,fixture):
        from qb013_output_audit import audit_saved_native_states
        return audit_saved_native_states(*fixture)
    def test_raw_vectors_recomputed_independently_of_saved_pass_flags(self):
        f=self.fixture();f[0]['observations']['stim']['comparison']['equivalent']=False
        result=self.audit(f)
        self.assertTrue(result['raw_vectors_recomputed']);self.assertFalse(result['overall_semantic_acceptance'])
    def test_false_saved_success_cannot_hide_phase_error_or_norm_error(self):
        for kind in ('phase','norm'):
            f=self.fixture();raw=f[0]['observations']['stim']['raw_state']
            raw[-1][0] *= -1 if kind=='phase' else 1.01
            with self.assertRaisesRegex(ValueError,'SAVED_NATIVE_MISMATCH'):self.audit(f)
    def test_nonfinite_tag_wrong_precision_and_mutated_original_rejected(self):
        for kind in ('nan','tag','dtype','mutation'):
            f=self.fixture();row=f[0]['observations']['stim']
            if kind=='nan':row['raw_state'][0][0]=float('nan')
            elif kind=='tag':row['raw_state'][0][0]={'nonfinite':'NaN'}
            elif kind=='dtype':row['dtype']='complex128'
            else:row['original_snapshot_after']={}
            with self.assertRaisesRegex(ValueError,'SAVED_NATIVE_'):self.audit(f)


class SavedControlAuditTests(unittest.TestCase):
    def test_host_expectations_match_all_scalar_control_states(self):
        import qb013_reference
        from qb013_output_audit import expected_authored_controls
        fixture=AuthoredControlTests();fixture.setUp()
        controls=fixture.controls();expected=expected_authored_controls(qb013_reference)
        self.assertEqual(len(expected),18)
        for (circuit,case),row in zip(controls,expected):
            self.assertEqual(row['id'],case['id'])
            self.assertEqual(row['expected_probabilities'],case['expected_probabilities'])
            state=qb013_reference.state_from_snapshot(circuit.snapshot)['state']
            self.assertTrue(qb013_reference.compare_states(row['expected_state'],state)['equivalent'])
    def test_recounts_raw_asymmetric_and_algorithm_results(self):
        import qb013_reference
        from qb013_output_audit import expected_authored_controls,audit_saved_control_samples
        for row in expected_authored_controls(qb013_reference):
            outcomes=list(row['expected_probabilities']);mapping=list(reversed(row['measured_qubits']))
            samples=[[bool((outcomes[i%len(outcomes)]>>q)&1) for q in mapping] for i in range(row['shots'])]
            result=audit_saved_control_samples(samples,mapping,row)
            self.assertEqual(sum(result['counts'].values()),row['shots']);self.assertTrue(result['raw_rows_recounted'])
    def test_false_pass_cannot_hide_forbidden_support_shape_or_mapping(self):
        import qb013_reference
        from qb013_output_audit import expected_authored_controls,audit_saved_control_samples
        row=expected_authored_controls(qb013_reference)[0]
        for samples,mapping in (([[False,True]]*4096,[0,1]),([[True,False]]*4095,[0,1]),
                                ([[1,0]]*4096,[0,1]),([[True,False]]*4096,[True,False])):
            with self.assertRaisesRegex(ValueError,'SAVED_SAMPLE_'):
                audit_saved_control_samples(samples,mapping,row)


class CompleteMockBundleTests(unittest.TestCase):
    """Full host wiring with authored mock bytes, never native/notebook proof."""
    def fixture(self):
        import json,hashlib,math
        from copy import deepcopy
        fixture=AuthoredControlTests();fixture.setUp()
        journal=lambda payload:dict(format_version=1,revision=1,payload=payload,fixture='AUTHORED MOCK')
        def native(programs,state):
            return dict(state='succeeded',errors=[],original_snapshots=deepcopy(programs),
                final_original_snapshots=deepcopy(programs),fixture='AUTHORED MOCK, NOT SDK OUTPUT',
                observations={name:dict(state='succeeded',dtype='complex64' if name=='stim' else 'complex128',
                    original_unchanged=True,original_snapshot_after=deepcopy(program),
                    raw_state=[[complex(x).real,complex(x).imag] for x in state])
                    for name,program in programs.items()})
        def call(original,final,conversions,parsers,state='succeeded'):
            return dict(state=state,input=original,input_after=deepcopy(original),output=final,
                conversions=conversions,parsers=parsers,scopes_restored=True,
                conversion_diagnostics=[],parser_diagnostics=[],
                graph_before={'fixture':'authored mock graph'},graph_after={'fixture':'authored mock graph'})
        bundle=SetupCaptureAuditTests().fixture();docs=bundle['documents']
        original,final,conversions,parsers,bell=CombinedStateAuditTests().fixtures()
        capture=docs['qb013-capture.json']['payload']
        capture['transpile_calls']=[call(original,final,conversions,parsers)]
        witness=docs['qb013-witness.json']['payload']
        witness['original_native_analysis']=native(dict(qiskit=original,cirq=parsers[0]['parsed_circuit'],stim=final),bell)
        saved=[]
        for index,(circuit,case) in enumerate(fixture.controls()):
            qiskit=deepcopy(circuit.snapshot);n=qiskit['qubits'];m=qiskit['clbits']
            qiskit.update(qregs=[dict(name='q',size=n,indices=list(range(n)))],
                          cregs=[dict(name='c',size=m,indices=list(range(m)))])
            cirq=dict(format='cirq',sorted_qubits=[dict(type='cirq.ops.named_qubit.NamedQubit',
                      text=f'q_{i}',dimension=2) for i in range(n)],operations=[])
            stim=dict(format='stim',qubits=n,measurements=m,operations=[])
            families={'h':'HPowGate','x':'XPowGate','z':'ZPowGate','cx':'CXPowGate'}
            for operation in qiskit['operations']:
                name=operation['name'];qubits=operation['qubits'][:]
                if name=='measure':
                    cirq['operations'].append(dict(measurement_key='c_'+str(operation['clbits'][0]),
                                                  qubits=qubits,invert_mask=[]))
                    stim_name='M'
                else:
                    cirq['operations'].append(dict(gate_family=families[name],qubits=qubits,exponent=1,global_shift=0))
                    stim_name=name.upper()
                stim['operations'].append(dict(name=stim_name,qubits=qubits,inverted=[False]*len(qubits),args=[]))
            parser=dict(state='succeeded',normalized_parser_input='AUTHORED MOCK parser input',parsed_circuit=cirq,
                        parsed_registers=dict(qregs=[dict(name='q',size=n)],cregs=[dict(name='c',size=m)],
                                              supported_format=True,qelib1_include=True))
            qasm=dict(format='qasm',version='2.0',text='AUTHORED MOCK exporter text')
            edges=[('qiskit','qasm2','qiskit_to_qasm2',qiskit,qasm),
                   ('qasm2','cirq','qasm2_to_cirq',qasm,cirq),('cirq','stim','cirq_to_stim',cirq,stim)]
            conversions=[dict(ordinal=i,state='succeeded',source=s,target=t,function_identities=[fn],
                positional_argument_count=1,keyword_names=[],single_program_positional_call=True,
                input=deepcopy(before),output=deepcopy(after)) for i,(s,t,fn,before,after) in enumerate(edges)]
            record=call(qiskit,stim,conversions,[parser])
            docs[f'qb013-control-{index:02d}.json']=journal(dict(active=False,diagnostics=[],transpile_calls=[record]))
            outcomes=list(case['expected_probabilities'])
            rows=[[bool((outcomes[i%len(outcomes)]>>q)&1) for q in case['measured_qubits']]
                  for i in range(case['shots'])]
            counts={str(value):sum(outcomes[i%len(outcomes)]==value for i in range(case['shots'])) for value in outcomes}
            metadata=deepcopy(case)
            metadata['expected_state']=[[complex(x).real,complex(x).imag] for x in case['expected_state']]
            metadata['expected_probabilities']={str(k):v for k,v in case['expected_probabilities'].items()}
            saved.append(dict(state='succeeded',case=metadata,conversion=deepcopy(record),raw_samples=rows,
                sampling=dict(raw_rows=deepcopy(rows),counts=counts,shots=case['shots']),
                native_analysis=native(dict(qiskit=qiskit,cirq=cirq,stim=stim),case['expected_state'])))
        witness['controls']=dict(state='succeeded',controls=saved)
        negative,record=SavedWrappedErrorTests().fixture()
        record.update(input_after=deepcopy(record['input']),scopes_restored=True,conversion_diagnostics=[],
                      parser_diagnostics=[],graph_before={},graph_after={})
        negative['conversion_calls']=[deepcopy(record)]
        witness['wrapped_error']=negative
        docs['qb013-wrapped-error.json']=journal(dict(active=False,diagnostics=[],transpile_calls=[record]))
        executed,records,contract=AuthoredDispositionTests().fixture()
        source_cells=[]
        rich,_,_=RequiredOutputAuditTests().fixture()
        for record in records:
            index=record['original_index']
            if index is None:continue
            cell=executed['cells'][record['index']]
            cell['source']=f'# AUTHORED MOCK source cell {index}; never executed'
            record['source_sha256']=hashlib.sha256(cell['source'].encode()).hexdigest()
            source_cells.append(deepcopy(cell))
            cell['outputs']=rich['cells'][index]['outputs']
            if index==22:cell['outputs']=[dict(output_type='stream',name='stdout',text=printed([[0,0]]*10))]
        original_bytes=json.dumps(dict(cells=source_cells,fixture='AUTHORED MOCK; NOT PINNED NOTEBOOK')).encode()
        contract['source'].update(sha256=hashlib.sha256(original_bytes).hexdigest(),url='authored-mock://host-wiring',
            cells=[dict(index=i,type=cell['cell_type'],sha256=hashlib.sha256(cell['source'].encode()).hexdigest())
                   for i,cell in enumerate(source_cells)])
        bundle['contract']=contract
        docs['executed.ipynb']=executed;docs['cells.json']=records
        docs['engine-result.json']=dict(state='succeeded',original_execution='succeeded',authored_verification='succeeded',
            authored_observation='succeeded',observer_bootstrap='succeeded',observer_cleanup='succeeded',
            source_cells_preserved=True,independent_results=dict(native_accepted=True),fixture='AUTHORED MOCK')
        # Serialized artifacts do not share mutable Python objects across journals.
        return json.loads(json.dumps(bundle,allow_nan=False)),original_bytes

    def audit(self,fixture):
        import qb013_reference
        from qb013_output_audit import audit_execution_semantics
        return audit_execution_semantics(fixture[0],fixture[1],qb013_reference)

    def test_full_positive_composition_without_mocking_any_audit_boundary(self):
        result=self.audit(self.fixture())
        self.assertTrue(result['finite_semantics_accepted'])
        self.assertFalse(result['whole_notebook_complete'])
        self.assertEqual(result['original']['original_code_cells'],17)
        self.assertEqual(result['original']['original_cells'],24)
        self.assertEqual(result['authored']['authored_cells'],10)
        self.assertEqual(len(result['authored_controls']),18)
        self.assertTrue(result['wrapped_error_preserved'])
        self.assertFalse(result['rich_outputs']['decoded_pixels_verified'])

    def test_complete_bundle_reader_and_cli_main(self):
        import json,tempfile,hashlib,io,sys
        from pathlib import Path
        from contextlib import redirect_stdout
        from unittest.mock import patch
        import qb013_output_audit
        bundle,source=self.fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);docs=bundle['documents'];artifacts={}
            for name,value in docs.items():
                if name=='engine-result.json':continue
                raw=json.dumps(value,allow_nan=False).encode();(root/name).write_bytes(raw)
                if name not in ('executed.ipynb','cells.json','kernel.json'):
                    artifacts[name]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
            docs['engine-result.json']['output_artifacts']=artifacts
            (root/'engine-result.json').write_text(json.dumps(docs['engine-result.json']),encoding='utf-8')
            contract=root/'mock-contract.json';contract.write_text(json.dumps(bundle['contract']),encoding='utf-8')
            original=root/'authored-mock-source.ipynb';original.write_bytes(source)
            expected=hashlib.sha256(contract.read_bytes()).hexdigest()
            before={p.name:p.read_bytes() for p in root.iterdir()}
            stdout=io.StringIO()
            with patch.object(sys,'argv',['audit','--directory',str(root),'--source',str(original),
                    '--contract',str(contract),'--contract-sha256',expected]),redirect_stdout(stdout):
                qb013_output_audit.main()
            result=json.loads(stdout.getvalue())
            self.assertTrue(result['finite_semantics_accepted'])
            self.assertEqual(len(result['file_bindings']),27)
            self.assertEqual(before,{p.name:p.read_bytes() for p in root.iterdir()})

    def test_join_tampering_rejected_in_complete_bundle(self):
        mutations=[
            ('source',lambda d:d['executed.ipynb']['cells'][3].update(source='changed')),
            ('setup',lambda d:d['setup-evidence.json']['commands'][0].update(exit_code=1)),
            ('restoration',lambda d:d['qb013-capture.json']['payload'].update(public_hooks_restored=False)),
            ('graph',lambda d:d['qb013-control-00.json']['payload']['transpile_calls'][0]['graph_after'].update(changed=True)),
            ('count',lambda d:d['qb013-witness.json']['payload']['controls']['controls'][0]['sampling']['counts'].update({'1':0})),
            ('vector',lambda d:d['qb013-witness.json']['payload']['controls']['controls'][3]['native_analysis']['observations']['stim']['raw_state'][3].__setitem__(0,1.0)),
            ('journal',lambda d:d['qb013-control-17.json']['payload']['transpile_calls'][0].update(output={})),
            ('error',lambda d:d['qb013-witness.json']['payload']['wrapped_error'].update(expected_inner_message='forged')),
            ('status',lambda d:d['cells.json'][-1].update(state='failed')),
            ('image',lambda d:d['executed.ipynb']['cells'][next(r['index'] for r in d['cells.json'] if r['original_index']==9)].update(outputs=[])),
        ]
        for name,mutate in mutations:
            with self.subTest(boundary=name):
                f=self.fixture();mutate(f[0]['documents'])
                with self.assertRaises(ValueError):self.audit(f)


class HostCompositionTests(unittest.TestCase):
    def fixture(self):
        import qb013_reference
        from qb013_output_audit import expected_authored_controls
        from copy import deepcopy
        f=SetupCaptureAuditTests().fixture();docs=f['documents']
        original,final,conversions,parsers,_=CombinedStateAuditTests().fixtures()
        capture=docs['qb013-capture.json']['payload']
        capture['transpile_calls'][0].update(input=original,input_after=deepcopy(original),output=final,
                                             conversions=conversions,parsers=parsers)
        witness=docs['qb013-witness.json']['payload']
        witness['original_native_analysis']=SavedNativeAuditTests().fixture()[0]
        witness['controls']=dict(state='succeeded',controls=[dict(case={}) for _ in expected_authored_controls(qb013_reference)])
        docs['engine-result.json']=dict(state='succeeded',original_execution='succeeded',authored_verification='succeeded',
            authored_observation='succeeded',observer_bootstrap='succeeded',observer_cleanup='succeeded',
            source_cells_preserved=True,independent_results=dict(native_accepted=True))
        docs['executed.ipynb']={};docs['cells.json']=[]
        return f
    def audit(self,bundle):
        import qb013_reference,qb013_output_audit
        from unittest.mock import patch
        # Original/authored dispositions have separate real artifact tests;
        # this composition fixture supplies only their proven output boundary.
        with patch.object(qb013_output_audit,'audit_source_dispositions',return_value=dict(cell22_stdout=printed([[0,0]]*10))), \
                patch.object(qb013_output_audit,'audit_authored_dispositions',return_value={}), \
                patch.object(qb013_output_audit,'audit_required_outputs',return_value={}):
            return qb013_output_audit.audit_execution_semantics(bundle,b'fixture',qb013_reference)
    def test_engine_failure_cannot_be_hidden_by_witness_pass(self):
        for key in ('state','original_execution','authored_verification','authored_observation','observer_cleanup'):
            f=self.fixture();f['documents']['engine-result.json'][key]='failed'
            with self.assertRaisesRegex(ValueError,'ENGINE_DISPOSITION'):self.audit(f)
    def test_actual_original_native_vectors_checked_before_control_metadata(self):
        f=self.fixture();native=f['documents']['qb013-witness.json']['payload']['original_native_analysis']
        native['observations']['stim']['raw_state'][-1][0]*=-1
        with self.assertRaisesRegex(ValueError,'SAVED_NATIVE_MISMATCH'):self.audit(f)
    def test_control_names_and_order_cannot_be_supplied_by_saved_pass_flag(self):
        with self.assertRaisesRegex(ValueError,'HOST_CONTROL_METADATA:id'):self.audit(self.fixture())


class SavedWrappedErrorTests(unittest.TestCase):
    def fixture(self):
        from qb013_output_audit import expected_wrapped_nonclifford_message
        program=dict(format='cirq',sorted_qubits=[dict(type='cirq.ops.named_qubit.NamedQubit',text='q_0',dimension=2)],
            operations=[dict(gate_family='ZPowGate',qubits=[0],exponent=0.25,global_shift=0.0)])
        message=expected_wrapped_nonclifford_message(program)
        outer="Failed to convert 'cirq' to 'stim' due to the following error(s):\n\nTypeError: "+message
        record=dict(state='failed',input=program,original_error=dict(type='ProgramConversionError',message=outer),
            conversions=[dict(source='cirq',target='stim',state='failed',function_identities=['cirq_to_stim'],
                              single_program_positional_call=True,error=dict(type='TypeError',message=message))])
        negative=dict(state='succeeded',input=program,conversion_calls=[record],expected_inner_type='TypeError',
            explicit_path_limits=dict(max_path_attempts=1,max_path_depth=1),expected_inner_message=message,
            actual_error=dict(type='ProgramConversionError',message=outer))
        return negative,record
    def audit(self,fixture):
        from qb013_output_audit import audit_saved_wrapped_error
        return audit_saved_wrapped_error(*fixture)
    def test_fixed_error_template_from_named_qubit_not_saved_expectation(self):
        self.assertTrue(self.audit(self.fixture())['expected_error_verified'])
        from qb013_output_audit import expected_wrapped_nonclifford_message
        program=self.fixture()[1]['input'];program['sorted_qubits'][0]['text']="wire ' λ"
        message=expected_wrapped_nonclifford_message(program)
        self.assertIn('cirq.T(cirq.NamedQubit("wire \' λ"))',message)
    def test_consistently_forged_saved_error_does_not_pass(self):
        negative,record=self.fixture();forged='unrelated TypeError'
        negative['expected_inner_message']=forged;record['conversions'][0]['error']['message']=forged
        outer="Failed to convert 'cirq' to 'stim'\nTypeError: "+forged
        negative['actual_error']['message']=outer;record['original_error']['message']=outer
        with self.assertRaisesRegex(ValueError,'HOST_WRAPPED_ERROR_EVIDENCE'):self.audit((negative,record))
    def test_missing_outer_prefix_and_wrong_input_gate_rejected(self):
        negative,record=self.fixture();outer='TypeError: '+negative['expected_inner_message']
        negative['actual_error']['message']=outer;record['original_error']['message']=outer
        with self.assertRaisesRegex(ValueError,'HOST_WRAPPED_ERROR_EVIDENCE'):self.audit((negative,record))
        negative,record=self.fixture();record['input']['operations'][0]['exponent']=0.5
        with self.assertRaisesRegex(ValueError,'HOST_WRAPPED_ERROR_INPUT'):self.audit((negative,record))


class RequiredOutputAuditTests(unittest.TestCase):
    def fixture(self):
        import base64,struct
        # Only a synthetic header: the auditor must not claim decoded pixels.
        raw=b'\x89PNG\r\n\x1a\n'+struct.pack('>I',13)+b'IHDR'+struct.pack('>II',12,8)+b'\0'*9
        cells=[dict(outputs=[]) for _ in range(24)]
        for index in (9,14):cells[index]['outputs']=[dict(data={'image/png':base64.b64encode(raw).decode()})]
        for index,value in ((4,'circuit'),(7,'registry'),(15,'True')):cells[index]['outputs']=[dict(data={'text/plain':value})]
        return dict(cells=cells),[dict(index=i,original_index=i) for i in range(24)],dict(required_images=[9,14],required_text={'15':'True'})
    def audit(self,f):
        from qb013_output_audit import audit_required_outputs
        return audit_required_outputs(*f)
    def test_hashes_original_images_without_claiming_visual_review(self):
        result=self.audit(self.fixture());self.assertEqual(len(result['images']),2)
        self.assertFalse(result['decoded_pixels_verified']);self.assertFalse(result['visually_interpreted'])
        self.assertFalse(result['cell21_original_display_required'])
    def test_missing_original_text_or_image_rejected(self):
        for index in (4,7,9,14,15):
            f=self.fixture();f[0]['cells'][index]['outputs']=[]
            with self.assertRaisesRegex(ValueError,'ORIGINAL_'):self.audit(f)
    def test_wrong_path_result_and_invalid_png_rejected(self):
        f=self.fixture();f[0]['cells'][15]['outputs'][0]['data']['text/plain']='False'
        with self.assertRaisesRegex(ValueError,'ORIGINAL_DISPLAY_TEXT'):self.audit(f)
        f=self.fixture();f[0]['cells'][9]['outputs'][0]['data']['image/png']='bm90IHB uZw=='
        with self.assertRaisesRegex(ValueError,'ORIGINAL_GRAPH_PNG_HEADER'):self.audit(f)


class NotebookDescriptorTests(unittest.TestCase):
    def test_bound_owned_files_and_engine_observer_protocol(self):
        import importlib.util,json,hashlib
        from pathlib import Path
        root=Path(__file__).parent
        contract=json.loads((root/'contracts/qb013.json').read_bytes())
        spec=importlib.util.spec_from_file_location('qb013_descriptor_engine',root/'execution.py')
        engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
        cells=[dict(cell_type=row['type']) for row in contract['source']['cells']]
        self.assertEqual(engine._execution_indices(contract,cells),list(range(24)))
        observers,lifecycle=engine._observer_sources(contract,cells)
        self.assertEqual(list(observers),[13,15,19,22]); self.assertIn('bootstrap',lifecycle)
        for artifact in [contract['witness'],*contract['embedded_sources'].values()]:
            self.assertEqual(hashlib.sha256((root/artifact['path']).read_text(encoding='utf-8').encode()).hexdigest(),artifact['sha256'])
        self.assertEqual(engine.digest(engine._setup_observer(contract['setup']['commands']).encode()),contract['setup']['observer_sha256'])
        self.assertEqual(contract['required_images'],[9,14]); self.assertEqual(contract['acceptance_field'],'native_accepted')
    def test_preamble_embeds_reference_and_audit_without_sdk_imports(self):
        import os,json,tempfile
        from pathlib import Path
        from unittest.mock import patch
        root=Path(__file__).parent; contract=json.loads((root/'contracts/qb013.json').read_bytes())
        previous=Path.cwd()
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{},clear=False):
            try:
                os.chdir(folder); namespace={}
                exec(compile(contract['preamble'],'authored-preamble','exec'),namespace)
                self.assertEqual(len(namespace['_qb013_reference'].cases()),14)
                self.assertTrue(callable(namespace['_qb013_audit'].analyze_conversion_states))
                self.assertEqual(os.environ['QISKIT_IGNORE_USER_SETTINGS'],'TRUE')
                self.assertEqual(json.loads(Path('qb013-preamble.json').read_bytes())['QISKIT_IGNORE_USER_SETTINGS']['authored_value'],'TRUE')
                with self.assertRaises(FileExistsError): exec(compile(contract['preamble'],'authored-preamble','exec'),{})
            finally: os.chdir(previous)


class NativeBindingTests(unittest.TestCase):
    setUp = NativeStateComparisonTests.setUp
    def fixture(self):
        import tempfile, hashlib
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import patch
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        root = Path(temp.name); hashes = {}; modules = {}
        names = dict(Statevector=type('Statevector', (), {}), Circuit=type('Circuit', (), {}),
                     Moment=type('Moment', (), {}), Simulator=type('Simulator', (), {}),
                     MeasurementGate=type('MeasurementGate', (), {}), Tableau=type('Tableau', (), {}),
                     complex128=complex, ProgramConversionError=type('ProgramConversionError', (Exception,), {}))
        for name, relative in self.module.NATIVE_MODULE_PATHS.items():
            path = root/relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(name.encode())
            hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
            modules[name] = SimpleNamespace(__file__=str(path), **names)
        patcher = patch.object(self.module, 'NATIVE_SOURCE_HASHES', hashes); patcher.start(); self.addCleanup(patcher.stop)
        return root, modules
    def test_source_failure_prevents_any_import(self):
        from unittest.mock import Mock
        root, modules = self.fixture()
        (root/next(iter(self.module.NATIVE_SOURCE_HASHES))).write_bytes(b'changed')
        importer = Mock(side_effect=modules.__getitem__)
        with self.assertRaisesRegex(ValueError, 'NATIVE_SOURCE_CHANGED'):
            self.module._bind_native_api(root, importer)
        importer.assert_not_called()
    def test_wrong_origin_and_import_time_change_rejected(self):
        root, modules = self.fixture()
        name = next(iter(modules)); saved = modules[name].__file__
        modules[name].__file__ = modules['numpy'].__file__
        with self.assertRaisesRegex(ValueError, 'NATIVE_MODULE_ORIGIN'):
            self.module._bind_native_api(root, modules.__getitem__)
        modules[name].__file__ = saved
        def importing(key):
            if key == 'numpy': (root/'numpy/__init__.py').write_bytes(b'changed during import')
            return modules[key]
        with self.assertRaisesRegex(ValueError, 'NATIVE_SOURCE_CHANGED'):
            self.module._bind_native_api(root, importing)
    def test_complete_binding_exposes_exact_classes_and_provenance(self):
        root, modules = self.fixture()
        api = self.module._bind_native_api(root, modules.__getitem__)
        self.assertIs(api.Statevector, modules['qiskit.quantum_info.states.statevector'].Statevector)
        self.assertIs(api.Tableau, modules['stim'].Tableau)
        self.assertEqual(api.source_evidence['source_hashes'], self.module.NATIVE_SOURCE_HASHES)
        self.assertEqual(api.source_evidence['compiled_source_correspondence'], 'unproved')


class NotebookEntrypointTests(unittest.TestCase):
    def setUp(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        # Load the module through the existing test fixture without SDK imports.
        self.base = ObservedTranspileTests(); self.base.setUp(); self.addCleanup(self.base.doCleanups)
        self.module = self.base.module
        self.capture = Mock()
        self.namespace = dict(_qb013_reference=SimpleNamespace(state_from_snapshot=lambda: None),
                              _qb013_audit=SimpleNamespace(analyze_conversion_states=lambda: None))
    def start(self):
        from unittest.mock import patch
        with patch.object(self.module, 'CaptureJournal') as journal, \
                patch.object(self.module, 'bind_observation_api') as bind, \
                patch.object(self.module, 'NotebookCapture', return_value=self.capture) as factory:
            result = self.module.start_notebook_capture(self.namespace)
            factory.assert_called_once_with(bind.return_value, self.namespace, journal.return_value)
            return result
    def test_bootstrap_installs_checks_and_returns_owned_capture(self):
        self.assertIs(self.start(), self.capture)
        self.capture.install.assert_called_once_with()
        self.capture.controller.require_complete.assert_called_once_with()
        self.capture.restore.assert_not_called()
    def test_checkpoint_failure_restores_before_bootstrap_propagates(self):
        primary = ValueError('capture failure')
        self.capture.controller.require_complete.side_effect = primary
        with self.assertRaises(ValueError) as caught: self.start()
        self.assertIs(caught.exception, primary)
        self.capture.restore.assert_called_once_with()
    def test_namespace_and_preamble_fail_before_binding(self):
        from unittest.mock import patch
        for namespace in ({}, dict(self.namespace, _qb013_capture=object())):
            with patch.object(self.module, 'bind_observation_api') as bind:
                with self.assertRaisesRegex(ValueError, 'NOTEBOOK_CAPTURE_'):
                    self.module.start_notebook_capture(namespace)
                bind.assert_not_called()
    def test_postcell_script_maps_exact_four_ordered_calls(self):
        from pathlib import Path
        from types import SimpleNamespace
        calls = []; rows = []
        def check(index, reference, audit):
            calls.append((index, reference, audit)); rows.append(index)
        capture = SimpleNamespace(controller=SimpleNamespace(postcells=rows), check_after=check)
        namespace = dict(self.namespace, __name__='__main__', _qb013_capture=capture)
        source = (Path(__file__).parent/'observers/qb013_checkpoint.py').read_text()
        for _ in range(4): exec(compile(source, 'checkpoint', 'exec'), namespace)
        self.assertEqual([row[0] for row in calls], [13, 15, 19, 22])
        self.assertTrue(all(row[1] is self.namespace['_qb013_reference'] and
                            row[2] is self.namespace['_qb013_audit'] for row in calls))
        with self.assertRaises(IndexError): exec(compile(source, 'checkpoint', 'exec'), namespace)
    def test_cleanup_restores_before_verifying_and_propagates_failure(self):
        from pathlib import Path
        from unittest.mock import call
        primary = ValueError('incomplete capture')
        self.capture.require_complete.side_effect = primary
        source = (Path(__file__).parent/'observers/qb013_cleanup.py').read_text()
        with self.assertRaises(ValueError) as caught:
            exec(compile(source, 'cleanup', 'exec'), dict(__name__='__main__', _qb013_capture=self.capture))
        self.assertIs(caught.exception, primary)
        self.assertEqual(self.capture.mock_calls, [call.restore(), call.require_complete()])


class IndependentStateTests(unittest.TestCase):
    def qiskit(self, n, operations, phase=0):
        return dict(format='qiskit',qubits=n,clbits=n,global_phase=phase,
                    operations=[dict(name=name,qubits=list(qubits),clbits=[],params=[])
                                for name,qubits in operations])
    def state(self, program):
        from qb013_reference import state_from_snapshot
        return state_from_snapshot(program)
    def assertVector(self, actual, expected):
        self.assertEqual(len(actual),len(expected))
        for x,y in zip(actual,expected):self.assertLess(abs(x-y),1e-12)
    def test_bell_state_and_terminal_measurements_annotations(self):
        import math
        program=self.qiskit(2,[('h',[0]),('cx',[0,1]),('barrier',[0,1])])
        program['clbits']=4
        program['operations'] += [dict(name='measure',qubits=[q],clbits=[q+2],params=[]) for q in (0,1)]
        result=self.state(program)
        self.assertVector(result['state'],[1/math.sqrt(2),0,0,1/math.sqrt(2)])
        self.assertEqual([m['clbits'] for m in result['measurements']],[[2],[3]])
        self.assertEqual(result['annotations'][0]['kind'],'barrier')
    def test_clifford_phases_and_inverses(self):
        for a,b in (('h','h'),('x','x'),('y','y'),('z','z'),('s','sdg'),('sx','sxdg'),('t','tdg')):
            for bit in (0,1):
                ops=([('x',[0])] if bit else [])+[(a,[0]),(b,[0])]
                expected=[0j,0j];expected[bit]=1
                self.assertVector(self.state(self.qiskit(1,ops))['state'],expected)
        self.assertVector(self.state(self.qiskit(1,[('y',[0])]))['state'],[0,1j])
        self.assertVector(self.state(self.qiskit(1,[('sx',[0])]))['state'],[(1+1j)/2,(1-1j)/2])
    def test_control_target_direction_all_basis_inputs(self):
        for basis in range(4):
            for control,target in ((0,1),(1,0)):
                prepare=[('x',[q]) for q in range(2) if basis & (1<<q)]
                out=basis ^ ((1<<target) if basis & (1<<control) else 0)
                expected=[0]*4;expected[out]=1
                self.assertVector(self.state(self.qiskit(2,prepare+[('cx',[control,target])]))['state'],expected)
                expected=[0]*4;expected[basis]=-1 if basis==3 else 1
                self.assertVector(self.state(self.qiskit(2,prepare+[('cz',[control,target])]))['state'],expected)
    def test_all_fourteen_algorithm_states_against_exact_walsh_reference(self):
        import math
        from qb013_reference import cases
        for case in cases():
            n=case['qubits'];table=case['truth_table'];constant=table[0]
            secret=[table[1<<q]^constant for q in range(n)]
            self.assertTrue(all(table[x]==(constant ^ (sum(secret[q]*((x>>q)&1) for q in range(n))%2))
                                for x in range(1<<n)))
            ops=[('x',[n])]+[('h',[q]) for q in range(n+1)]
            if constant:ops.append(('x',[n]))
            ops += [('cx',[q,n]) for q in range(n) if secret[q]]
            ops += [('h',[q]) for q in range(n)]
            expected=[a/case['amplitude_denominator']/math.sqrt(2) for a in case['amplitude_numerators']]
            expected += [-a for a in expected]
            self.assertVector(self.state(self.qiskit(n+1,ops))['state'],expected)
    def test_cirq_eigenphase_and_named_order_mapping(self):
        import cmath,math
        from qb013_reference import compare_states
        cirq=dict(format='cirq',sorted_qubits=[dict(dimension=2)],operations=[
            dict(gate_family='XPowGate',qubits=[0],exponent=0.5,global_shift=-0.5)])
        actual=self.state(cirq)['state'];phase=cmath.exp(-1j*math.pi/4)
        self.assertVector(actual,[phase*(1+1j)/2,phase*(1-1j)/2])
        cirq.update(sorted_qubits=[dict(dimension=2)]*2,operations=[
            dict(gate_family='XPowGate',qubits=[1],exponent=1,global_shift=0)])
        actual=self.state(cirq)['state'];expected=[0,1,0,0]
        self.assertTrue(compare_states(expected,actual,[1,0])['equivalent'])
        self.assertFalse(compare_states(expected,actual,[0,1])['equivalent'])
    def test_cirq_bell_matches_qiskit_without_sdk(self):
        from qb013_reference import compare_states
        cirq=dict(format='cirq',sorted_qubits=[dict(dimension=2)]*2,operations=[
            dict(gate_family='HPowGate',qubits=[0],exponent=1,global_shift=0),
            dict(gate_family='CXPowGate',qubits=[0,1],exponent=1,global_shift=0),
            dict(measurement_key='m',qubits=[0,1],invert_mask=[True])])
        expected=self.state(self.qiskit(2,[('h',[0]),('cx',[0,1])]))['state']
        result=self.state(cirq)
        self.assertTrue(compare_states(expected,result['state'])['equivalent'])
        self.assertEqual(result['measurements'][0]['inverted'],[True,False])
    def test_stim_batched_gates_and_annotations(self):
        program=dict(format='stim',qubits=4,measurements=4,operations=[
            dict(name='H',qubits=[0,2],inverted=[False,False],args=[]),
            dict(name='CX',qubits=[0,1,2,3],inverted=[False]*4,args=[]),
            dict(name='TICK',qubits=[],inverted=[],args=[]),
            dict(name='QUBIT_COORDS',qubits=[0],inverted=[False],args=[1,2]),
            dict(name='M',qubits=[0,1,2,3],inverted=[False,True,False,False],args=[])])
        result=self.state(program);expected=[0]*16
        for index in (0,3,12,15):expected[index]=0.5
        self.assertVector(result['state'],expected)
        self.assertEqual(len(result['measurements']),4)
        self.assertEqual([a['kind'] for a in result['annotations']],['TICK','QUBIT_COORDS'])
    def test_phase_coherence_is_not_count_support(self):
        import math
        from qb013_reference import compare_states
        bell=[1/math.sqrt(2),0,0,1/math.sqrt(2)]
        phase=[1/math.sqrt(2),0,0,-1/math.sqrt(2)]
        self.assertEqual([abs(x)**2 for x in bell],[abs(x)**2 for x in phase])
        self.assertFalse(compare_states(bell,phase)['equivalent'])
        result=compare_states(bell,[1j*x for x in bell])
        self.assertTrue(result['equivalent']);self.assertFalse(result['global_phase_sensitive'])
        self.assertFalse(result['all_input_unitary_equivalence'])
    def test_midcircuit_measurement_and_unsupported_semantics_reject(self):
        program=self.qiskit(1,[])
        program['operations']=[dict(name='measure',qubits=[0],clbits=[0],params=[]),
                               dict(name='x',qubits=[0],clbits=[],params=[])]
        with self.assertRaisesRegex(ValueError,'POST_MEASUREMENT'):self.state(program)
        for name in ('reset','unknown'):
            with self.assertRaisesRegex(ValueError,'UNSUPPORTED_REFERENCE_GATE'):
                self.state(self.qiskit(1,[(name,[0])]))
        stim=dict(format='stim',qubits=1,measurements=1,operations=[
            dict(name='M',qubits=[0],inverted=[False],args=[0.1])])
        with self.assertRaisesRegex(ValueError,'NOISY_MEASUREMENT'):self.state(stim)
    def test_invalid_state_domains_and_relaxed_tolerance_reject(self):
        from qb013_reference import compare_states
        for program in (self.qiskit(True,[]),self.qiskit(5,[]),self.qiskit(1,[('cx',[0,0])]),
                        self.qiskit(1,[('x',[True])]),self.qiskit(1,[],float('nan'))):
            with self.assertRaises(ValueError):self.state(program)
        for actual in ([0,0],[float('nan'),0],[True,0]):
            with self.assertRaises(ValueError):compare_states([1,0],actual)
        for mapping in ([False],[1],[0,0]):
            with self.assertRaises(ValueError):compare_states([1,0],[1,0],mapping)
        with self.assertRaises(ValueError):compare_states([1,0],[1,0],tolerance=1e-3)


if __name__=='__main__':unittest.main()
