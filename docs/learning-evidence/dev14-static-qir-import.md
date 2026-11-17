# DEV-14: finite static QIR import

This developer CLI translates a deliberately limited QIR program to OpenQASM 3.
It does not execute LLVM. DEV-14 and the source notebook audit remain open:
there is no general QIR, CUDA-Q, GUI, packaged-release, or hosted-CI acceptance.

## Contract

`windows/dev13-notebooks/qir_import.py` accepts UTF-8 LLVM IR, or bitcode with
`--bitcode`, using PyQIR 0.12.6 from the existing `qir-win-py312` profile and
`qir-requirements.lock` (Python 3.12.10, Windows x64). The CLI assumes that
environment; it does not install or validate the complete dependency profile.

Input is at most 1 MiB, verified LLVM, QIR 1.0 or 1.1, with both dynamic resource
flags false. Exactly one entry point must be void, argument-free, and have one
basic block ending in return. It declares 1–4 qubits and 0–64 result slots.
The block has at most 4,096 instructions, including return. Calls must be direct
to external, void, nonvariadic declarations with pointer arguments.

Supported calls are H, X, Y, Z, S, S-adjoint, T, T-adjoint, CNOT, CZ, MZ,
optional first-call runtime initialization with null data, and result output
with a null label. Resource IDs must be constant and in range; two-qubit gate
targets must differ. All other entry instructions and calls reject the input.
This includes branching, allocation, reset, rotations, result reads, output
containers, labels, and user function calls. Unused functions are not executed.

Every output must refer to a previously measured result. Each output call
snapshots its value at that point, including repeated records and overwritten
result slots. Chronological output order is left-to-right in native bitstrings;
the generated output array therefore uses reversed indices. At most 64 records
are accepted, and declared result slots plus records must fit 64 classical bits
when records exist. Without records, measurements are retained as discarded
measurements and no classical outputs are invented.

The report includes the source SHA-256, source format, entry name, resource
counts, generated OpenQASM, output convention, and `execution_performed=false`.
Validation finishes before an optional output file is opened exclusively;
existing files are refused. Translation is an explicit adaptation of the input.

## Invocation and verification

Run the profile's Python with `-E -s -B`, followed by the importer path and a
source `.ll` file; add `--bitcode` for `.bc` and `--output new-file.qasm` to save.
Pass the generated OpenQASM to `windows/qasm-import.py --classical` in its own
compiler environment before native execution.

`test_qir_import.py` tests real LLVM text/bitcode, rejection boundaries, output
snapshots and CLI file preservation. `build-qir-import-test.ps1 -OutputPath`
builds the dedicated saved-model adapter from `QirImportBridgeTests.cs`.
`test_qir_import_native.py` takes explicit compiler Python, compiler, adapter,
worker and new evidence-directory paths. It checks nine circuits in both input
formats through compilation, saved-model reload, and exact and sampled engines.
Cases cover Bell correlation, asymmetric outputs, permutation, overwrite,
duplicate output, discarded measurement, unitary-only input, and Bell inversion.
Empty-output cases establish output disposition only, not final state fidelity.

The QB-017 source notebook's default generated program records two unmeasured
results. This importer rejects it as `QIR_UNMEASURED_OUTPUT`; it neither adds
measurements nor silently changes the upstream converter's output settings.
Authored measured circuits are separate controls, not acceptance of that source.

Review, hosted CI, packaging, release verification, broader QIR programs and
CUDA-Q compatibility remain required before the wider checklist can close.
