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
basic block ending in return. It declares 1–10 qubits and 0–64 result slots.
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

When all gates precede all measurements, all output records follow them, and
measurement/result slots and output records form a one-to-one correspondence,
measurements write directly to the corresponding output bits. This retains the
measurement order and output permutation without redundant classical copies.
Interleaved output, repeated result writes, duplicate records, partial outputs,
or gates after measurements keep the general snapshot lowering. The report's
`output_lowering` distinguishes these cases. Invalid result references still
reject before either lowering is selected.

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
worker and new evidence-directory paths. It checks 21 circuits in both input
formats through compilation, saved-model reload, and exact and sampled engines.
Cases cover Bell correlation, asymmetric outputs, permutation, overwrite,
duplicate output, discarded measurement, unitary-only input, and Bell inversion.
Empty-output cases establish output disposition only, not final state fidelity.

The width extension adds highest-wire basis states and GHZ correlations at every
width 5–10, bringing the native suite to 21 circuits. The ten-qubit bound matches
the existing native exact engine; the sampled engine's wider capacity does not
expand this importer contract. Other native execution budgets still apply: for
example, exact requests support at most 512 steps, while import validation permits
4,096 LLVM instructions. Import success alone does not guarantee execution.
The earlier snapshot lowering forced even terminal circuits into the general
density-matrix evaluator: nine-qubit GHZ timed out at 30 seconds, and ten-qubit
GHZ at 180 seconds. A longer baseline diagnostic was deliberately stopped after
the optimized lowering was implemented; no cell-budget error was experimentally
established for that interrupted run. Terminal measurement aliases allow the
existing published worker's exact phase evaluator to handle these circuits.
General snapshot cases retain their existing execution budgets and semantics.

The unchanged QB-015 generated text and bitcode still reject. Removing the former
four-qubit guard exposes `QIR_STATIC_ID:result` for their output record of slot 4
when only four slots are declared. No measurement or output is silently repaired.
See [width verification](dev14-qir-width.json) for the retained execution and
original-rejection evidence. Broader QIR and original provider acceptance remain open.

As a separate route, the unchanged OpenQASM generated from the original QB-015
definitions passes compilation, saved-model reload and native exact/sampled
execution: constant data output `0000`, balanced data output `1000`. These are
native classical-bit strings (highest bit first), not inferred provider strings.
The two generated programs each produce probability one and all 10,000 sampled
shots at the expected output. This is authored local execution of unchanged
generated OpenQASM; it does not repair or accept the faulty QIR or run the cloud
workflow. Both original definitions and all five qubits are retained.

The QB-017 source notebook's default generated program records two unmeasured
results. This importer rejects it as `QIR_UNMEASURED_OUTPUT`; it neither adds
measurements nor silently changes the upstream converter's output settings.
Authored measured circuits are separate controls, not acceptance of that source.

Review, hosted CI, packaging, release verification, broader QIR programs and
CUDA-Q compatibility remain required before the wider checklist can close.
