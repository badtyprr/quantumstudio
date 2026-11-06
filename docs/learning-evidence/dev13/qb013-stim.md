# QB013: Qiskit → Cirq → Stim notebook contract

Status: implementation in progress. The source notebook has not yet been
executed through this full contract. SDK-free component tests do not establish
native execution or whole-notebook completion.

## Original provenance

The pinned qBraid example is `qbraid_sdk_transpiler_cirq_stim.ipynb`, revision
`86787e1ba372facc224f925189755e69c479828b`, original SHA-256
`5b5ae29f1a5813111d1474d60a13aac6c06c2ef1904f75de73ec75a7224c8145`.
It contains 24 cells: 17 code and seven Markdown. Original saved outputs are
empty. Preserve every original cell's source, ordering and copyright notice.

The retained source and provenance inventory are in
`cleanup-audit/dev13-aud02-20261101-b6e2`; the notebook lane's external evidence
is in `cleanup-audit/notebook-lane-20261104`. These audit files are not runtime
dependencies. The implementation is based on
`f11715b966b8c6302f7962c70deb7a5d6465a365`; it has no new product commit yet.

## Execution and interpretation

| Original cells | Required disposition and interpretation |
| --- | --- |
| 0 | Run unchanged captured pip command against the pinned offline environment; record its actual success and unchanged environment inventory. Preinstallation alone does not complete this cell. |
| 1 | Preserve logging and warning settings. A suppressed conversion warning does not prove that no semantics were dropped. |
| 2–4 | Preserve introduction/import; construct and display the actual Bell circuit. `measure_all()` adds a measurement register: the two initially allocated classical bits remain unused. |
| 5–9 | Preserve conversion-graph introduction, registry display, graph creation and original graph rendering. Inspect the actual image; do not infer an edge from layout proximity. |
| 10–13 | Preserve custom-conversion explanation/import and both original add-edge branches. Missing stimcirq or skipped conditional bodies cannot satisfy semantic acceptance. Record which branch actually ran. |
| 14–15 | Render the changed graph and display the actual path result. A true path predicate alone does not prove that conversion succeeds. |
| 16–19 | Preserve explanation/import; execute original transpile call with the actual custom graph and retain its output type and conversion trace. |
| 20–22 | Preserve sampling explanation, diagram call and unseeded ten-shot output. Cell 21 discards the diagram return value inside an `if`; absence of an original display is expected. Do not insert a display and call it original output. |
| 23 | Retain attribution and license notice; its external license reference is provenance, not a quantum execution dependency. |

This is direct Python notebook execution containing an SDK conversion. It is
not native OpenQASM execution or a manual QASM rewrite. QASM2 text encountered
inside the SDK route is an observed intermediate. Capture actual normalized
parser input, register declarations and measurement occurrences; do not replace
them with a reconstructed circuit and claim the original route ran.

## Finite acceptance

1. All 24 original cells are accounted for, with all 17 code cells successful,
   unchanged source hashes and no hidden error outputs. Authored cells have
   separate roles and cannot substitute for original success.
2. Setup uses the pinned 76-package Windows CPython 3.12.10 profile. Actual
   setup receipts, package metadata and module inventories demonstrate no drift.
3. The observed route is exactly Qiskit → QASM2 → Cirq → Stim using the pinned
   converter function identities. Retain all attempts and original errors;
   unsupported fallback routes cannot be filtered into an acceptable trace.
4. Original quantum/classical register mapping, unused classical bits, actual
   sorted Cirq Qids, readout inversion and Stim measurement-event order agree.
   A renamed or reordered declaration outside the finite mapping is rejected.
5. Independent scalar calculations and actual native premeasurement observations
   agree with the Bell state, modulo global phase. Qiskit barriers and Stim
   TICK/coordinate annotations remain distinct. No general unitary equivalence,
   global-phase preservation or physical execution is claimed.
6. Native observations use separately authored copies. Qiskit strips final
   measurements on a copy; Cirq filters validated terminal measurement gates
   without applying readout flips; Stim builds a tableau ignoring only validated
   terminal measurements. Reject noise, reset, feedback and unsupported gates
   before these operations. Verify all original snapshots afterward.
7. Stim's pinned tableau vector is complex64: fixed absolute norm and density
   bounds are `1e-6`. Authored Cirq requests complex128; Qiskit/Cirq bounds are
   `1e-12` for norm and `1e-10` for density. These prospective bounds are separate
   from the unchanged strict scalar reference. Never renormalize observations
   to pass. Preserve tagged NaN/infinity evidence while rejecting it.
8. Audit the actual complete ten-by-two Boolean stdout matrix from cell 22.
   Its mapped rows must be 00 or 11; ten unseeded shots need not include both
   outcomes and do not establish frequency balance, phase or wire order.
9. Separately authored asymmetric, phase, seeded-count, unsupported-operation
   and 14 Deutsch–Jozsa/Bernstein–Vazirani controls must pass independent
   expectations. They are additional evidence, not original notebook cells.
10. Inspect required graph images and circuit output, verify hook restoration,
    environment invariance, terminal execution artifacts and independent
    Standards/Spec reviews at the exact integrated commit.

## Remaining work and limitations

The authored control suite, descriptor/preamble and host semantic audit are
implemented but have not been exercised on an actual full notebook run. A
complete authored mock bundle now exercises all host audit joins and the CLI
entry point without patching audit boundaries, including 24 original-shaped
cells, 10 authored cells, 18 controls, and tamper rejection. These synthetic
source cells, vectors, samples, and PNG headers are explicitly mock data; they
provide wiring coverage, not original-source execution or native evidence. The
integrated commit, reserved runtime execution, complete environment-byte audit,
visual interpretation and actual-artifact independent reviews remain pending.
Compiled extension hashes establish bytes, not correspondence to upstream C++
source. No provider credentials, paid jobs or hardware execution are needed for
this finite local notebook contract. Broader framework/provider and AUD-04
coverage remains separate.
