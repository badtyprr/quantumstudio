"""Read-only original-output validation for the finite QB013 contract.

This module never substitutes authored samples for original stdout. Its host
entry point verifies finite semantic evidence; visual, environment-byte and
lifecycle acceptance remain separately required.
"""
import re

_ROW = r'\[\s*(True|False)\s+(True|False)\s*\]'
_MATRIX = re.compile(r'\s*\[\s*(?:' + _ROW + r'\s*){10}\]\s*')


def parse_original_samples(stdout):
    """Parse exactly the complete original NumPy Boolean ten-by-two printout."""
    if not isinstance(stdout, str) or _MATRIX.fullmatch(stdout) is None:
        raise ValueError('ORIGINAL_SAMPLE_FORMAT')
    return [[int(a == 'True'), int(b == 'True')] for a, b in re.findall(_ROW, stdout)]


def audit_original_samples(stdout, occurrence_to_logical):
    """Require a proven two-occurrence bijection before checking Bell support.

The caller must establish the mapping from conversion evidence; symmetric Bell
rows alone cannot establish it. The unseeded ten shots need not contain both
allowed outcomes and do not test frequency balance or phase coherence.
"""
    if (not isinstance(occurrence_to_logical, (list, tuple))
            or len(occurrence_to_logical) != 2
            or any(type(x) is not int for x in occurrence_to_logical)
            or sorted(occurrence_to_logical) != [0, 1]):
        raise ValueError('UNPROVEN_MEASUREMENT_BIJECTION')
    rows = parse_original_samples(stdout)
    logical_rows = []
    for row in rows:
        logical = [None, None]
        for occurrence, bit in enumerate(row):
            logical[occurrence_to_logical[occurrence]] = bit
        logical_rows.append(logical)
    if any(row not in ([0, 0], [1, 1]) for row in logical_rows):
        raise ValueError('ORIGINAL_SAMPLE_FORBIDDEN_OUTCOME')
    return dict(shots=10, original_rows=rows, logical_rows=logical_rows,
                occurrence_to_logical=list(occurrence_to_logical),
                support_verified=True, balance_verified=False, coherence_verified=False)

ORIGINAL_CODE_INDICES = (0, 1, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14, 15, 17, 19, 21, 22)


def _read_bounded_bytes(path, limit=256*1024*1024):
    """Read at most limit+1 bytes, including when a file grows during the read."""
    from pathlib import Path
    with Path(path).open('rb') as stream:
        raw=stream.read(limit+1)
    if len(raw)>limit: raise ValueError('BUNDLE_ARTIFACT_TOO_LARGE')
    return raw


def read_execution_bundle(directory, contract_path, expected_contract_sha256):
    """Read a completed run under a separately trusted product descriptor hash.

    Hashes bind bytes and detect replacement during this read; they do not prove
    native semantics, visual interpretation or the producer's trustworthiness.
    """
    from pathlib import Path
    import hashlib
    import json
    root = Path(directory).resolve(strict=True)
    if not root.is_dir(): raise ValueError('BUNDLE_DIRECTORY')
    def parse(raw):
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result: raise ValueError('BUNDLE_DUPLICATE_JSON_KEY')
                result[key] = value
            return result
        def reject(value): raise ValueError('BUNDLE_NONFINITE_JSON:'+value)
        return json.loads(raw, object_pairs_hook=unique, parse_constant=reject)
    contract_bytes = _read_bounded_bytes(contract_path)
    if hashlib.sha256(contract_bytes).hexdigest() != expected_contract_sha256:
        raise ValueError('BUNDLE_CONTRACT_CHANGED')
    contract = parse(contract_bytes)
    if contract.get('id') != 'qb013' or contract.get('route') != 'notebook':
        raise ValueError('BUNDLE_CONTRACT_SCOPE')
    raw_files = {}; documents = {}; hashes = {}
    def read(name):
        path = root/name
        if path.is_symlink() or path.resolve(strict=True).parent != root or not path.is_file():
            raise ValueError('BUNDLE_ARTIFACT_PATH:'+name)
        raw = _read_bounded_bytes(path)
        raw_files[name] = raw
        hashes[name] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        documents[name] = parse(raw)
        return documents[name]
    engine = read('engine-result.json')
    required = {'setup-evidence.json','qb013-preamble.json','qb013-capture.json',
                'qb013-witness.json','qb013-wrapped-error.json'}
    required.update(f'qb013-control-{index:02d}.json' for index in range(18))
    artifacts = engine.get('output_artifacts')
    if type(artifacts) is not dict or set(artifacts) != required:
        raise ValueError('BUNDLE_ARTIFACT_SET')
    for name in sorted(required):
        read(name)
        metadata = artifacts[name]
        if (type(metadata) is not dict or type(metadata.get('bytes')) is not int
                or metadata != hashes[name]):
            raise ValueError('BUNDLE_ARTIFACT_CHANGED:'+name)
    for name in ('executed.ipynb','cells.json','kernel.json'): read(name)
    for name, raw in raw_files.items():
        if _read_bounded_bytes(root/name) != raw: raise ValueError('BUNDLE_CHANGED_DURING_READ:'+name)
    if _read_bounded_bytes(contract_path) != contract_bytes:
        raise ValueError('BUNDLE_CONTRACT_CHANGED_DURING_READ')
    return dict(contract=contract, contract_sha256=expected_contract_sha256,
                documents=documents, file_bindings=hashes, overall_semantic_acceptance=False)


def audit_setup_and_capture(bundle):
    """Check actual setup metadata and completed passive capture, not native math."""
    documents = bundle['documents']; contract = bundle['contract']
    setup = documents['setup-evidence.json']; kernel = documents['kernel.json']
    expected_command = '"'+kernel['executable']+'" -m pip '+contract['setup']['commands'][0]
    if (contract['setup']['commands'] != ['install qbraid qiskit stimcirq ply matplotlib']
            or setup.get('accepted') is not True or type(setup.get('before')) is not dict
            or not setup['before'] or setup['before'] != setup.get('after')
            or setup.get('commands') != [dict(command=expected_command,exit_code=0)]
            or type(setup['commands'][0]['exit_code']) is not int):
        raise ValueError('SETUP_METADATA_OR_COMMAND_MISMATCH')
    preamble = documents['qb013-preamble.json']
    if preamble.get('QISKIT_IGNORE_USER_SETTINGS',{}).get('authored_value') != 'TRUE':
        raise ValueError('PREAMBLE_ENVIRONMENT_CHOICE')
    def payload(name):
        journal = documents[name]
        if (type(journal.get('format_version')) is not int or journal['format_version'] != 1
                or type(journal.get('revision')) is not int or journal['revision'] < 1
                or type(journal.get('payload')) is not dict):
            raise ValueError('CAPTURE_JOURNAL_FORMAT:'+name)
        return journal['payload']
    capture = payload('qb013-capture.json')
    if (capture.get('active') is not False or capture.get('diagnostics') != []
            or capture.get('public_hooks_restored') is not True):
        raise ValueError('CAPTURE_NOT_RESTORED')
    cells = capture.get('postcells',[])
    if ([row.get('after_original_index') for row in cells] != [13,15,19,22]
            or any(row.get('state') != 'succeeded' for row in cells)):
        raise ValueError('CAPTURE_POSTCELL_PROTOCOL')
    records = capture.get('transpile_calls',[])
    if len(records) != 1: raise ValueError('CAPTURE_ORIGINAL_CALL_COUNT')
    call = records[0]
    if (call.get('state') != 'succeeded' or call.get('scopes_restored') is not True
            or call.get('conversion_diagnostics') != [] or call.get('parser_diagnostics') != []
            or call.get('input') != call.get('input_after') or call.get('graph_before') != call.get('graph_after')):
        raise ValueError('CAPTURE_ORIGINAL_CALL_FAILED')
    witness = payload('qb013-witness.json')
    if witness.get('state') != 'succeeded' or witness.get('native_accepted') is not True:
        raise ValueError('NATIVE_WITNESS_FAILED')
    return dict(setup_metadata_unchanged=True, original_command_succeeded=True,
                hooks_restored=True, capture=capture, witness=witness,
                module_bytes_verified=False, overall_semantic_acceptance=False)


def audit_saved_native_states(report, reference, programs):
    """Recompute finite density residuals from raw saved native vectors."""
    import math
    names = {'qiskit','cirq','stim'}
    if (set(programs) != names or report.get('state') != 'succeeded' or report.get('errors') != []
            or report.get('original_snapshots') != programs or report.get('final_original_snapshots') != programs
            or set(report.get('observations',{})) != names):
        raise ValueError('SAVED_NATIVE_REPORT_SCOPE')
    comparisons = {}
    for name in sorted(names):
        row = report['observations'][name]; expected = reference.state_from_snapshot(programs[name])['state']
        precision = 'complex64' if name == 'stim' else 'complex128'
        norm_limit,density_limit = (1e-6,1e-6) if name == 'stim' else (1e-12,1e-10)
        if (row.get('state') != 'succeeded' or row.get('dtype') != precision
                or row.get('original_unchanged') is not True or row.get('original_snapshot_after') != programs[name]):
            raise ValueError('SAVED_NATIVE_DISPOSITION:'+name)
        raw = row.get('raw_state')
        if (type(raw) is not list or len(raw) != len(expected) or any(type(pair) is not list or len(pair) != 2
                or any(type(value) not in (int,float) or not math.isfinite(value) for value in pair) for pair in raw)):
            raise ValueError('SAVED_NATIVE_VECTOR:'+name)
        actual = [complex(*pair) for pair in raw]
        norm = sum(abs(value)**2 for value in actual)
        residual = max(abs(expected[i]*expected[j].conjugate()-actual[i]*actual[j].conjugate())
                       for i in range(len(expected)) for j in range(len(expected)))
        if abs(norm-1) > norm_limit or residual > density_limit:
            raise ValueError('SAVED_NATIVE_MISMATCH:'+name)
        comparisons[name] = dict(norm_squared=norm,max_density_error=residual,
                                 norm_limit=norm_limit,density_limit=density_limit)
    return dict(comparisons=comparisons, raw_vectors_recomputed=True, global_phase_sensitive=False,
                overall_semantic_acceptance=False)


def expected_authored_controls(reference):
    """Independent host expectations; no circuit builder or SDK is consulted."""
    import math
    a=1/math.sqrt(2)
    rows=[]
    for name,state in (('onehot-q0',[0,1,0,0]),('onehot-q1',[0,0,1,0]),
                       ('bell',[a,0,0,a]),('phase-bell',[a,0,0,-a])):
        probabilities={i:abs(value)**2 for i,value in enumerate(state) if value}
        rows.append(dict(id=name,qubits=2,measured_qubits=[0,1],expected_state=state,
            expected_probabilities=probabilities,shots=4096,seed=1731,
            frequency_tolerance=0.05 if len(probabilities)>1 else 0.0))
    for case in reference.cases():
        n=case['qubits']; coefficients=reference.walsh_numerators(case['truth_table'])
        state=[coefficients[data]/(1<<n)*(-1 if ancilla else 1)/math.sqrt(2)
               for ancilla in range(2) for data in range(1<<n)]
        # Derive the deterministic result from the full character sum, not
        # a saved secret/result supplied by the native witness.
        support=[i for i,value in enumerate(coefficients) if value]
        if len(support)!=1 or abs(coefficients[support[0]]) != 1<<n:
            raise ValueError('HOST_CONTROL_NONDETERMINISTIC_EXPECTATION')
        rows.append(dict(id=case['id'],qubits=n+1,measured_qubits=list(range(n)),expected_state=state,
            expected_probabilities={support[0]:1.0},shots=128,seed=1731,frequency_tolerance=0.0))
    return rows


def audit_saved_control_samples(raw_rows, mapping, expected):
    """Recount complete raw rows using host-derived expectations and mapping."""
    width=len(expected['measured_qubits']); shots=expected['shots']
    if (not isinstance(mapping,(list,tuple)) or len(mapping)!=width
            or any(type(q) is not int for q in mapping) or sorted(mapping)!=list(range(width))):
        raise ValueError('SAVED_SAMPLE_MAPPING')
    if type(raw_rows) is not list or len(raw_rows)!=shots:
        raise ValueError('SAVED_SAMPLE_SHOTS')
    counts={}
    for row in raw_rows:
        if type(row) is not list or len(row)!=width or any(type(bit) is not bool for bit in row):
            raise ValueError('SAVED_SAMPLE_ROW')
        outcome=sum((1<<mapping[i]) for i,bit in enumerate(row) if bit)
        counts[outcome]=counts.get(outcome,0)+1
    probabilities=expected['expected_probabilities']
    residuals={key:abs(counts.get(key,0)/shots-value) for key,value in probabilities.items()}
    if set(counts)-set(probabilities) or any(value>expected['frequency_tolerance'] for value in residuals.values()):
        raise ValueError('SAVED_SAMPLE_SEMANTICS')
    return dict(counts={str(key):value for key,value in sorted(counts.items())},shots=shots,
                frequency_residuals={str(key):value for key,value in residuals.items()},
                raw_rows_recounted=True,coherence_verified=False)


def expected_wrapped_nonclifford_message(program):
    """Pinned NamedQubit/T representation and Stimcirq rejection, derived on host."""
    qubits=program.get('sorted_qubits',[]); operations=program.get('operations',[])
    if (program.get('format')!='cirq' or len(qubits)!=1
            or qubits[0].get('type')!='cirq.ops.named_qubit.NamedQubit'
            or type(qubits[0].get('text')) is not str or qubits[0].get('dimension')!=2
            or len(operations)!=1 or operations[0].get('gate_family')!='ZPowGate'
            or operations[0].get('qubits')!=[0] or operations[0].get('exponent')!=0.25
            or operations[0].get('global_shift')!=0):
        raise ValueError('HOST_WRAPPED_ERROR_INPUT')
    operation=f"cirq.T(cirq.NamedQubit({qubits[0]['text']!r}))"
    return (f"Don't know how to translate {operation} into stim gates.\n"
            "- It doesn't have a _decompose_ method that returns stim-compatible operations.\n"
            "- It doesn't have a _stim_conversion_ method.\n")


def audit_saved_wrapped_error(negative,record):
    """Validate the expected rejection independently of saved expectation text."""
    edges=record.get('conversions',[])
    expected_message=expected_wrapped_nonclifford_message(record.get('input',{}))
    if (negative.get('state')!='succeeded' or record.get('state')!='failed'
            or negative.get('conversion_calls')!=[record] or negative.get('input')!=record.get('input')
            or negative.get('explicit_path_limits')!=dict(max_path_attempts=1,max_path_depth=1)
            or negative.get('expected_inner_message')!=expected_message or negative.get('expected_inner_type')!='TypeError'
            or len(edges)!=1 or edges[0].get('source')!='cirq' or edges[0].get('target')!='stim'
            or edges[0].get('state')!='failed' or edges[0].get('function_identities')!=['cirq_to_stim']
            or edges[0].get('single_program_positional_call') is not True
            or edges[0].get('error')!=dict(type='TypeError',message=expected_message)
            or negative.get('actual_error',{}).get('type')!='ProgramConversionError'
            or record.get('original_error')!=dict(type='ProgramConversionError',message=negative['actual_error'].get('message'))
            or not negative['actual_error'].get('message','').startswith("Failed to convert 'cirq' to 'stim'")
            or 'TypeError: '+expected_message not in negative['actual_error'].get('message','')):
        raise ValueError('HOST_WRAPPED_ERROR_EVIDENCE')
    return dict(expected_error_verified=True)


def audit_execution_semantics(bundle, original_bytes, reference):
    """Compose host checks; rendering, module inventories and lifecycle stay open."""
    import math
    docs=bundle['documents']; contract=bundle['contract']; engine=docs['engine-result.json']
    for key in ('state','original_execution','authored_verification','authored_observation',
                'observer_bootstrap','observer_cleanup'):
        if engine.get(key)!='succeeded': raise ValueError('ENGINE_DISPOSITION:'+key)
    if engine.get('source_cells_preserved') is not True or engine.get('independent_results',{}).get('native_accepted') is not True:
        raise ValueError('ENGINE_SEMANTIC_RESULT')
    original=audit_source_dispositions(original_bytes,docs['executed.ipynb'],docs['cells.json'],contract)
    authored=audit_authored_dispositions(docs['executed.ipynb'],docs['cells.json'],contract)
    rich_outputs=audit_required_outputs(docs['executed.ipynb'],docs['cells.json'],contract)
    setup=audit_setup_and_capture(bundle); capture=setup['capture']; witness=setup['witness']
    call=capture['transpile_calls'][0]
    bell=[1/math.sqrt(2),0,0,1/math.sqrt(2)]
    analysis=analyze_conversion_states(reference,call['input'],call['output'],call['conversions'],call['parsers'],bell)
    if not analysis['reference_semantic_acceptance']: raise ValueError('HOST_ORIGINAL_REFERENCE_MISMATCH')
    samples=audit_original_samples(original['cell22_stdout'],analysis['route']['occurrence_to_logical'])
    native=audit_saved_native_states(witness['original_native_analysis'],reference,
        dict(qiskit=call['input'],cirq=call['parsers'][0]['parsed_circuit'],stim=call['output']))
    def journal(name):
        value=docs[name]
        if (type(value.get('format_version')) is not int or value['format_version']!=1
                or type(value.get('revision')) is not int or value['revision']<1 or type(value.get('payload')) is not dict):
            raise ValueError('HOST_JOURNAL_FORMAT:'+name)
        return value['payload']
    def observed(name):
        value=journal(name); rows=value.get('transpile_calls',[])
        if value.get('active') is not False or value.get('diagnostics')!=[] or len(rows)!=1:
            raise ValueError('HOST_CONTROL_CAPTURE:'+name)
        row=rows[0]
        if (row.get('scopes_restored') is not True or row.get('conversion_diagnostics')!=[]
                or row.get('parser_diagnostics')!=[] or row.get('input')!=row.get('input_after')
                or row.get('graph_before')!=row.get('graph_after')):
            raise ValueError('HOST_CONTROL_RESTORATION:'+name)
        return row
    controls=witness.get('controls',{}); saved=controls.get('controls',[])
    expectations=expected_authored_controls(reference)
    if controls.get('state')!='succeeded' or len(saved)!=len(expectations):
        raise ValueError('HOST_CONTROL_COUNT')
    control_results=[]
    for index,(row,expected) in enumerate(zip(saved,expectations)):
        metadata=row.get('case',{})
        for key in ('id','qubits','measured_qubits','shots','seed','frequency_tolerance'):
            if type(metadata.get(key)) is not type(expected[key]) or metadata[key]!=expected[key]:
                raise ValueError('HOST_CONTROL_METADATA:'+key)
        expected_pairs=[[complex(x).real,complex(x).imag] for x in expected['expected_state']]
        if (metadata.get('expected_state')!=expected_pairs
                or metadata.get('expected_probabilities')!={str(k):v for k,v in expected['expected_probabilities'].items()}):
            raise ValueError('HOST_CONTROL_EXPECTATION_CHANGED')
        record=observed(f'qb013-control-{index:02d}.json')
        if row.get('state')!='succeeded' or record.get('state')!='succeeded' or row.get('conversion')!=record:
            raise ValueError('HOST_CONTROL_CONVERSION')
        calculated=analyze_conversion_states(reference,record['input'],record['output'],
            record['conversions'],record['parsers'],expected['expected_state'])
        if not calculated['reference_semantic_acceptance']: raise ValueError('HOST_CONTROL_REFERENCE')
        native_control=audit_saved_native_states(row['native_analysis'],reference,
            dict(qiskit=record['input'],cirq=record['parsers'][0]['parsed_circuit'],stim=record['output']))
        raw=row['raw_samples']
        recounted=audit_saved_control_samples(raw,calculated['route']['occurrence_to_logical'],expected)
        if (row.get('sampling',{}).get('raw_rows')!=raw or row['sampling'].get('counts')!=recounted['counts']
                or row['sampling'].get('shots')!=recounted['shots']):
            raise ValueError('HOST_CONTROL_SAMPLE_RECORD_CHANGED')
        control_results.append(dict(id=expected['id'],native=native_control,sampling=recounted))
    negative=witness.get('wrapped_error',{}); record=observed('qb013-wrapped-error.json')
    audit_saved_wrapped_error(negative,record)
    return dict(original=original,authored=authored,rich_outputs=rich_outputs,original_reference=analysis,original_native=native,
                original_samples=samples,authored_controls=control_results,wrapped_error_preserved=True,
                finite_semantics_accepted=True,whole_notebook_complete=False,
                remaining=['Original rich outputs and graph visual interpretation',
                           'Before/after complete module inventories and dependency closure',
                           'Owned lifecycle and final actual-artifact independent reviews'])


def audit_required_outputs(executed, records, contract):
    """Bind required original display bytes; visual interpretation stays separate."""
    import base64,hashlib,struct
    positions={row['original_index']:row['index'] for row in records if row.get('original_index') is not None}
    def text(value): return value if type(value) is str else ''.join(value)
    def outputs(index): return executed['cells'][positions[index]].get('outputs',[])
    for index, expected in contract['required_text'].items():
        values=[text(row['data']['text/plain']) for row in outputs(int(index))
                if 'text/plain' in row.get('data',{})]
        if expected not in values: raise ValueError('ORIGINAL_DISPLAY_TEXT:'+index)
    for index in (4,7):
        if not any(row.get('data',{}).get('text/plain') or row.get('data',{}).get('image/png') for row in outputs(index)):
            raise ValueError('ORIGINAL_DISPLAY_MISSING:'+str(index))
    images=[]
    for index in contract['required_images']:
        values=[row['data']['image/png'] for row in outputs(index) if 'image/png' in row.get('data',{})]
        if not values: raise ValueError('ORIGINAL_GRAPH_IMAGE_MISSING:'+str(index))
        for ordinal,value in enumerate(values):
            raw=base64.b64decode(''.join(text(value).split()),validate=True)
            if (len(raw)<33 or raw[:8]!=b'\x89PNG\r\n\x1a\n' or raw[8:12]!=b'\0\0\0\r'
                    or raw[12:16]!=b'IHDR'):
                raise ValueError('ORIGINAL_GRAPH_PNG_HEADER')
            width,height=struct.unpack('>II',raw[16:24])
            if not width or not height: raise ValueError('ORIGINAL_GRAPH_PNG_DIMENSIONS')
            images.append(dict(original_index=index,ordinal=ordinal,sha256=hashlib.sha256(raw).hexdigest(),
                               bytes=len(raw),width=width,height=height))
    return dict(images=images,header_checks_only=True,decoded_pixels_verified=False,
                visually_interpreted=False,cell21_original_display_required=False)


def audit_authored_dispositions(executed, records, contract):
    """Bind every authored cell to the trusted descriptor and exact position.

    This supplements, never replaces, audit_source_dispositions. The caller
    must bind the descriptor bytes to the reviewed integrated product first.
    """
    import hashlib
    if (contract.get('id') != 'qb013' or contract.get('route') != 'notebook'
            or contract['setup']['cell'] != 0 or len(contract['source']['cells']) != 24):
        raise ValueError('AUTHORED_DESCRIPTOR_SCOPE')
    expected = []
    def authored(role, sha, after=None): expected.append((None, role, sha, after))
    authored('preamble', hashlib.sha256(contract['preamble'].encode('utf-8')).hexdigest())
    authored('observer-bootstrap', contract['observer_lifecycle']['bootstrap']['sha256'])
    observers = contract['post_cell_observers']
    if [row['after_original_index'] for row in observers] != [13, 15, 19, 22]:
        raise ValueError('AUTHORED_DESCRIPTOR_OBSERVERS')
    by_index = {row['after_original_index']:row for row in observers}
    for index in range(24):
        if index == 0: authored('setup-observer', contract['setup']['observer_sha256'])
        expected.append((index, None, None, None))
        if index == 0: authored('setup-check', contract['setup']['check_sha256'])
        if index in by_index:
            row=by_index[index]; authored(row['role'], row['sha256'], index)
    authored('observer-cleanup', contract['observer_lifecycle']['cleanup']['sha256'])
    authored('independent-witness', contract['witness']['sha256'])
    if len(records) != len(expected) or len(executed['cells']) != len(expected):
        raise ValueError('AUTHORED_CELL_COUNT')
    roles = []
    for position, (record, cell, target) in enumerate(zip(records, executed['cells'], expected)):
        original, role, sha, after = target
        if (type(record.get('index')) is not int or record['index'] != position
                or record.get('original_index') != original or record.get('authored_role') != role):
            raise ValueError('AUTHORED_CELL_POSITION')
        if role is None: continue
        text = cell['source'] if type(cell['source']) is str else ''.join(cell['source'])
        if (record.get('type') != 'code' or cell['cell_type'] != 'code'
                or record.get('state') != 'succeeded' or record.get('source_sha256') != sha
                or hashlib.sha256(text.encode('utf-8')).hexdigest() != sha
                or record.get('after_original_index') != after
                or cell.get('metadata', {}).get('tags') != ['authored-'+role]
                or any(output.get('output_type') == 'error' for output in cell.get('outputs', []))):
            raise ValueError('AUTHORED_CELL_EVIDENCE:'+role)
        roles.append(role)
    return dict(authored_cells=len(roles), roles=roles, source_and_position_bound=True,
                overall_semantic_acceptance=False)


def analyze_conversion_states(reference, original, final, conversions, parsers, expected_state):
    """Compose route evidence and independent zero-input state expectations.

    Return raw calculated states and failed comparisons without raising for a
    semantic mismatch, so callers can checkpoint before asserting acceptance.
    Native SDK observations and original notebook dispositions remain separate.
    """
    route = audit_conversion_route(original, final, conversions, parsers)
    programs = dict(qiskit=original, cirq=parsers[0]['parsed_circuit'], stim=final)
    reports = {}; comparisons = {}
    mapping = route['register_mapping']['sorted_qid_to_qiskit']
    for name, program in programs.items():
        result = reference.state_from_snapshot(program)
        state = result['state']
        reports[name] = dict(result, state=[[complex(x).real, complex(x).imag] for x in state])
        comparisons[name] = reference.compare_states(expected_state, state,
                            None if name == 'qiskit' else mapping)
    phase = reports['qiskit']['original_global_phase']
    return dict(route=route, calculated_states=reports, comparisons=comparisons,
                expected_state=[[complex(x).real, complex(x).imag] for x in expected_state],
                reference_semantic_acceptance=all(x['equivalent'] for x in comparisons.values()),
                annotations_preserved_in_report=True,
                original_global_phase=phase, global_phase_preservation_verified=False,
                native_execution_verified=False, overall_semantic_acceptance=False)


def audit_conversion_route(original, final, conversions, parsers):
    """Bind the finite observed three-edge route, without steering qBraid.

    Other routes or attempted fallbacks remain unsupported evidence. Callers
    must retain every raw record and original exception, not filter the input
    to make this gate pass. Gate/state equivalence is deliberately separate.
    """
    def require(ok, message):
        if not ok:
            raise ValueError(message)
    expected = [('qiskit', 'qasm2', 'qiskit_to_qasm2'),
                ('qasm2', 'cirq', 'qasm2_to_cirq'), ('cirq', 'stim', 'cirq_to_stim')]
    require(len(conversions) == 3 and len(parsers) == 1, 'UNSUPPORTED_OBSERVED_ROUTE')
    for index, (record, (source, target, identity)) in enumerate(zip(conversions, expected)):
        require(type(record.get('ordinal')) is int and record['ordinal'] == index
                and record.get('state') == 'succeeded' and record.get('source') == source
                and record.get('target') == target, 'OBSERVED_ROUTE_SEQUENCE')
        require(record.get('function_identities') == [identity], 'OBSERVED_FUNCTION_IDENTITY')
        require(type(record.get('positional_argument_count')) is int
                and record['positional_argument_count'] == 1 and record.get('keyword_names') == []
                and record.get('single_program_positional_call') is True, 'OBSERVED_CONVERTER_ARGUMENTS')
        require(record.get('input') is not None and record.get('output') is not None, 'MISSING_ROUTE_SNAPSHOT')
    require(conversions[0]['input'] == original and conversions[-1]['output'] == final,
            'ROUTE_ENDPOINT_CHANGED')
    require(all(conversions[i]['output'] == conversions[i+1]['input'] for i in range(2)),
            'ROUTE_INTERMEDIATE_CHANGED')
    qasm = conversions[0]['output']
    require(qasm.get('format') == 'qasm' and qasm.get('version') == '2.0'
            and type(qasm.get('text')) is str and bool(qasm['text']), 'ROUTE_QASM2_SNAPSHOT')
    parser = parsers[0]
    require(parser.get('state') == 'succeeded'
            and type(parser.get('normalized_parser_input')) is str and bool(parser['normalized_parser_input'])
            and parser.get('parsed_circuit') == conversions[1]['output'], 'ROUTE_PARSER_BINDING')
    registers = audit_qiskit_parser_measurements(original, parser)
    measurements = audit_cirq_stim_measurements(conversions[2]['input'], final)
    logical = [registers['sorted_qid_to_qiskit'][row['qubit']]
               for row in measurements['stim_occurrences']]
    require(logical == registers['occurrence_to_logical'], 'ROUTE_MEASUREMENT_COMPOSITION')
    return dict(route=[source for source, _, _ in expected] + ['stim'],
                route_correspondence_verified=True, default_stim_mapping_verified=True,
                register_mapping=registers, measurement_mapping=measurements,
                occurrence_to_logical=logical, occurrence_to_clbit=registers['occurrence_to_clbit'],
                normalization_observed=True, normalization_gate_equivalence_verified=False,
                overall_semantic_acceptance=False)


def audit_qiskit_parser_measurements(qiskit, parser_record):
    """Map the finite unchanged-register QASM route, including unused clbits.

    Reject renamed/reordered declarations instead of guessing correspondence.
    The source-gated parser emits NamedQubit(reg_index) and one measurement per
    classical destination key. This checks those captured facts against the
    original Qiskit measurement sequence; gate equivalence is a separate gate.
    """
    def require(ok, message):
        if not ok:
            raise ValueError(message)
    require(qiskit.get('format') == 'qiskit' and parser_record.get('state') == 'succeeded',
            'REGISTER_MAPPING_FORMAT')
    registers = parser_record['parsed_registers']; cirq = parser_record['parsed_circuit']
    require(cirq.get('format') == 'cirq' and registers.get('supported_format') is True
            and registers.get('qelib1_include') is True, 'REGISTER_MAPPING_PARSER')
    def names(kind, count):
        require(type(count) is int and count >= 0, 'REGISTER_MAPPING_COUNT')
        rows = qiskit[kind]
        require(isinstance(rows, list), 'REGISTER_MAPPING_ROWS')
        declared = []; mapping = {}; indices = []; seen = set()
        for row in rows:
            name = row['name']; size = row['size']; bits = row['indices']
            require(type(name) is str and bool(name) and name not in seen
                    and type(size) is int and size > 0 and isinstance(bits, list)
                    and len(bits) == size and all(type(x) is int and 0 <= x < count for x in bits),
                    'REGISTER_MAPPING_DECLARATION')
            seen.add(name); declared.append(dict(name=name, size=size)); indices.extend(bits)
            for position, bit in enumerate(bits):
                label = name + '_' + str(position)
                require(label not in mapping, 'REGISTER_MAPPING_NAME_COLLISION')
                mapping[label] = bit
        require(sorted(indices) == list(range(count)), 'REGISTER_MAPPING_BIT_COVERAGE')
        require(registers[kind] == declared, 'REGISTER_DECLARATIONS_CHANGED')
        return mapping
    quantum = names('qregs', qiskit['qubits']); classical = names('cregs', qiskit['clbits'])
    sorted_to_original = []
    for label in cirq['sorted_qubits']:
        require(label.get('type') == 'cirq.ops.named_qubit.NamedQubit'
                and label.get('dimension') == 2 and label.get('text') in quantum,
                'PARSER_QID_MAPPING')
        sorted_to_original.append(quantum[label['text']])
    require(sorted(sorted_to_original) == list(range(qiskit['qubits'])), 'PARSER_QID_COVERAGE')
    expected = []
    for operation in qiskit['operations']:
        if operation['name'] == 'measure':
            require(len(operation['qubits']) == len(operation['clbits']) == 1
                    and operation['params'] == [], 'QISKIT_MEASUREMENT_SHAPE')
            q, c = operation['qubits'][0], operation['clbits'][0]
            require(type(q) is int and 0 <= q < qiskit['qubits']
                    and type(c) is int and 0 <= c < qiskit['clbits'], 'QISKIT_MEASUREMENT_DOMAIN')
            expected.append((q, c))
    actual = []
    for operation in cirq['operations']:
        if 'measurement_key' in operation:
            qubits = operation['qubits']; key = operation['measurement_key']; mask = operation['invert_mask']
            require(isinstance(qubits, list) and len(qubits) == 1 and type(qubits[0]) is int
                    and 0 <= qubits[0] < len(sorted_to_original) and type(key) is str and key in classical
                    and isinstance(mask, list) and len(mask) <= 1
                    and all(type(x) is bool and x is False for x in mask), 'PARSER_MEASUREMENT_MAPPING')
            actual.append((sorted_to_original[qubits[0]], classical[key]))
    require(bool(expected) and actual == expected, 'QISKIT_PARSER_MEASUREMENTS_CHANGED')
    return dict(sorted_qid_to_qiskit=sorted_to_original,
                occurrence_to_logical=[q for q, _ in actual], occurrence_to_clbit=[c for _, c in actual],
                unused_clbits=sorted(set(range(qiskit['clbits'])) - {c for _, c in actual}),
                correspondence_verified=True, gate_equivalence_verified=False)


def audit_cirq_stim_measurements(cirq, stim):
    """Compare measurement occurrences under stimcirq's default sorted-Qid map.

    Consume captured programs, never generated replacement circuits. Preserve
    repeated keys and measurements in occurrence order, including inversion.
    This proves only this boundary's measurement correspondence. It does not
    prove gate equivalence or a mapping back to Qiskit classical destinations.
    The caller must separately prove that the observed converter used the
    pinned default mapping, rather than an explicit custom qubit_map.
    """
    def require(ok, message):
        if not ok:
            raise ValueError(message)
    require(cirq.get('format') == 'cirq' and stim.get('format') == 'stim', 'MEASUREMENT_FORMAT')
    labels = cirq['sorted_qubits']
    size = len(labels)
    require(size > 0 and all(q.get('dimension') == 2 for q in labels), 'MEASUREMENT_QID_DOMAIN')
    require(type(stim.get('qubits')) is int and stim['qubits'] == size, 'MEASUREMENT_QUBIT_COUNT')
    def valid_qubits(qubits):
        return (isinstance(qubits, list) and bool(qubits)
                and all(type(q) is int and 0 <= q < size for q in qubits))
    expected = []
    for operation_index, operation in enumerate(cirq['operations']):
        if 'measurement_key' not in operation:
            continue
        key = operation['measurement_key']; qubits = operation['qubits']; mask = operation['invert_mask']
        require(isinstance(key, str) and valid_qubits(qubits) and len(set(qubits)) == len(qubits),
                'CIRQ_MEASUREMENT_SHAPE')
        require(isinstance(mask, list) and len(mask) <= len(qubits)
                and all(type(value) is bool for value in mask), 'CIRQ_MEASUREMENT_MASK')
        mask = mask + [False] * (len(qubits) - len(mask))
        for key_bit, (qubit, inverted) in enumerate(zip(qubits, mask)):
            expected.append(dict(occurrence=len(expected), cirq_operation=operation_index,
                                 key=key, key_bit=key_bit, qubit=qubit, inverted=inverted))
    actual = []
    for operation_index, operation in enumerate(stim['operations']):
        if operation['name'] != 'M':
            continue
        qubits = operation['qubits']; mask = operation['inverted']
        require(valid_qubits(qubits) and isinstance(mask, list) and len(mask) == len(qubits)
                and all(type(value) is bool for value in mask) and operation.get('args') == [],
                'STIM_MEASUREMENT_SHAPE')
        for target_index, (qubit, inverted) in enumerate(zip(qubits, mask)):
            actual.append(dict(occurrence=len(actual), stim_operation=operation_index,
                               target_index=target_index, qubit=qubit, inverted=inverted))
    require(type(stim.get('measurements')) is int and stim['measurements'] == len(actual),
            'STIM_MEASUREMENT_COUNT')
    require(bool(expected) and [(x['qubit'], x['inverted']) for x in expected]
            == [(x['qubit'], x['inverted']) for x in actual], 'MEASUREMENT_OCCURRENCES_CHANGED')
    return dict(cirq_occurrences=expected, stim_occurrences=actual,
                correspondence_verified=True, mapping_basis='pinned default sorted Qid order',
                gate_equivalence_verified=False, qiskit_destination_mapping_verified=False)


def audit_source_dispositions(original_bytes, executed, records, contract):
    """Validate all original cells and return the actual cell22 stdout.

This is a component gate, not overall semantic or rendering acceptance.
The eventual entry point must bind the contract to the frozen product.
"""
    import hashlib
    import json
    def require(ok, message):
        if not ok:
            raise ValueError(message)
    def source(cell):
        value = cell['source']
        return value if isinstance(value, str) else ''.join(value)
    require(hashlib.sha256(original_bytes).hexdigest() == contract['source']['sha256'], 'ORIGINAL_BYTES_CHANGED')
    original = json.loads(original_bytes)
    require(len(original['cells']) == 24, 'ORIGINAL_CELL_COUNT')
    ledger = [dict(index=i, type=c['cell_type'], sha256=hashlib.sha256(source(c).encode()).hexdigest())
              for i, c in enumerate(original['cells'])]
    require(ledger == contract['source']['cells'], 'ORIGINAL_CELL_BINDING')
    require(tuple(i for i, c in enumerate(original['cells']) if c['cell_type'] == 'code') == ORIGINAL_CODE_INDICES,
            'ORIGINAL_CODE_SCOPE')
    require(len(executed['cells']) == len(records), 'EXECUTED_RECORD_COUNT')
    require(all(type(r.get('index')) is int for r in records) and [r.get('index') for r in records] == list(range(len(records))), 'RECORD_INDICES')
    originals = [r for r in records if r.get('original_index') is not None]
    require(all(type(r['original_index']) is int for r in originals)
            and [r['original_index'] for r in originals] == list(range(24)), 'ORIGINAL_DISPOSITION_ORDER')
    output_cell = None
    for record in originals:
        i = record['original_index']; old = original['cells'][i]
        cell = executed['cells'][record['index']]
        require(cell['cell_type'] == old['cell_type'] and source(cell) == source(old), 'SOURCE_CELL_CHANGED:'+str(i))
        require(record.get('source_sha256') == ledger[i]['sha256'] and record.get('type') == old['cell_type'],
                'RECORD_SOURCE_BINDING:'+str(i))
        require(record.get('authored_role') is None, 'ORIGINAL_MISLABELLED_AUTHORED:'+str(i))
        require(record['state'] == ('succeeded' if i in ORIGINAL_CODE_INDICES else 'not_executable'),
                'ORIGINAL_NOT_SUCCEEDED:'+str(i))
        require(not any(o.get('output_type') == 'error' for o in cell.get('outputs', [])), 'ORIGINAL_ERROR_OUTPUT:'+str(i))
        if i == 22:
            output_cell = cell
    streams = [o.get('text', '') for o in output_cell.get('outputs', [])
               if o.get('output_type') == 'stream' and o.get('name') == 'stdout']
    stdout = ''.join(value if isinstance(value, str) else ''.join(value) for value in streams)
    return dict(original_cells=24, original_code_cells=17, source_preserved=True,
                cell22_stdout=stdout, overall_semantic_acceptance=False)

def main():
    import argparse,hashlib,importlib.util,json
    from pathlib import Path
    parser=argparse.ArgumentParser(description='Read-only finite QB013 artifact audit')
    parser.add_argument('--directory',required=True)
    parser.add_argument('--source',required=True)
    parser.add_argument('--contract',required=True)
    parser.add_argument('--contract-sha256',required=True)
    args=parser.parse_args()
    bundle=read_execution_bundle(args.directory,args.contract,args.contract_sha256)
    root=Path(__file__).resolve().parent
    for alias,filename in (('audit','qb013_output_audit.py'),('reference','qb013_reference.py')):
        binding=bundle['contract']['embedded_sources'][alias]
        if (binding['path']!=filename or hashlib.sha256((root/filename).read_text(encoding='utf-8').encode('utf-8')).hexdigest()!=binding['sha256']):
            raise ValueError('HOST_IMPLEMENTATION_BINDING:'+alias)
    spec=importlib.util.spec_from_file_location('qb013_host_reference',root/'qb013_reference.py')
    reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
    result=audit_execution_semantics(bundle,_read_bounded_bytes(args.source),reference)
    result['contract_sha256']=bundle['contract_sha256']
    result['file_bindings']=bundle['file_bindings']
    print(json.dumps(result,allow_nan=False,ensure_ascii=False))


if __name__=='__main__': main()
