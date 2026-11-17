"""Local build diagnostics for original QB015 definitions, never a provider job."""
import hashlib
import json
from pathlib import Path
import re


def output_diagnostic(llvm):
    """Inspect this pinned compiler's scalar output ABI, not arbitrary LLVM."""
    declared = re.search(r'"required_num_results"="(\d+)"', llvm)
    if declared is None:
        raise ValueError('MISSING_RESULT_COUNT')
    slots = int(declared.group(1))
    calls = re.findall(r'call void @__quantum__rt__result_record_output\((.*?)\)\n', llvm)
    ids = []
    for call in calls:
        if call == 'ptr null, ptr null':
            ids.append(0)
        else:
            match = re.fullmatch(r'ptr inttoptr \(i64 (\d+) to ptr\), ptr null', call)
            if match is None:
                raise ValueError('UNRECOGNIZED_OUTPUT_CALL')
            ids.append(int(match.group(1)))
    return dict(declared_results=slots, recorded_result_ids=ids,
                out_of_range=[i for i in ids if i >= slots])


def run(constant, balanced):
    from braket.devices import LocalSimulator
    from braket.ir.openqasm import Program
    from qbraid_qir.qasm3 import qasm3_to_qir

    observations = []
    for name, algorithm in [('constant', constant), ('balanced', balanced)]:
        built = algorithm.build()
        qasm = built.to_ir()
        # These observations are authored calls, separate from original cells14/19.
        Path(name + '.qasm').write_bytes(qasm.encode())
        module = qasm3_to_qir(qasm, name='qb015_' + name)
        if module.verify() is not None:
            raise AssertionError('LLVM_VERIFICATION_FAILED')
        llvm = str(module)
        Path(name + '.ll').write_bytes(llvm.encode())
        Path(name + '.bc').write_bytes(module.bitcode)
        diagnostic = output_diagnostic(llvm)
        if diagnostic != dict(declared_results=4, recorded_result_ids=[0, 1, 2, 3, 4],
                              out_of_range=[4]):
            raise AssertionError('PINNED_COMPILER_DIAGNOSTIC_CHANGED')
        try:
            LocalSimulator().run(Program(source=qasm), shots=32).result()
        except ValueError as error:
            message = str(error)
            if 'Measurements were recorded into 4 classical registers:' not in message:
                raise
        else:
            raise AssertionError('PINNED_LOCAL_SIMULATOR_DIAGNOSTIC_CHANGED')
        observations.append(dict(case=name, qasm_sha256=hashlib.sha256(qasm.encode()).hexdigest(),
            llvm_verifies=True, qir_semantically_accepted=False, output_diagnostic=diagnostic,
            local_simulator_error=message, local_simulator_counts=None))
    return dict(accepted=True, acceptance_scope='selected definitions build and pinned failures reproduced',
        selected_source_cells=[8, 10, 11, 18], whole_notebook_complete=False,
        provider_jobs_submitted=False, observations=observations,
        limitations=['Build, serialization, conversion and local simulation calls are authored observations',
                    'LLVM verification does not establish QIR semantic validity',
                    'No corrected source, successful circuit execution or cloud result is claimed'])


if __name__ == '__main__':
    print(json.dumps(run(deutsch_jozsa_constant, deutsch_jozsa_balanced)))
