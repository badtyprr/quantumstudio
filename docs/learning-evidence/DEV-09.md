# DEV-09: released ensembles, instruments and POVMs

Base: upstream master `0fed41cb5637c578737278bf13f59590a56d6cf4`, fetched 2026-11-01.
The root checkout, README changes, untracked files and root dist are preserved.
Development checkout: `.tools/dev09-implementation-clone`. External evidence:
`cleanup-audit/dev09-*`. Released as [e5ed358a](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-e5ed358a) (REL-25).
This closes the documented DEV-09 feature contract, not whole-lesson coverage.

## Sources and original inputs

The repository inventory pins IBM URLs, not historical content hashes. Browser
retrieval succeeded for the following pages on 2026-11-01. A direct Python HTML
snapshot request returned HTTP 403; no snapshot hashes are claimed.

- [Measurement formulations](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/general-measurements/formulations-of-measurements), General measurements / Example 2: original effects P0=[2,1;1,1]/3, P1=[1,-1;-1,2]/3 and state |+><+|. Independent multiplication and trace give 5/6 and 1/6. Adaptation: new API spellings `povm(labels,effects)` and `probabilities(povm,state)` are not IBM code.
- Same source, convex mixtures: rho=sum_k p_k |psi_k><psi_k|. Diagnostic specialization uses weights 1/3,2/3 and states |0>,|+>. Expanding outer products gives [2/3,1/3;1/3,1/3]. This is a disclosed finite witness, not an unchanged lesson example.
- [Naimark theorem](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/general-measurements/naimark-theorem), Theorem statement and proof: the first n columns of U stack sqrt(P_a), with ancilla preceding system and initialized to |0>. The API supplies ancilla dimension explicitly. Tests inspect the full unitary and independently sum output-block probabilities, including an extra dimension-three ancilla outcome of probability zero.
- Same source, Non-destructive measurements: an instrument determines poststates. A diagnostic projective instrument gives |0><0| and |1><1|; a separate grouped two-Kraus reset witness gives |0><0| for |+> input. A POVM alone must not silently select an instrument.

## Reproductions and scoped delivery

`cleanup-audit/dev09-baseline.json` records released-worker inputs, outputs and
binary hash. Unknown API names became symbolic products, not measurement objects.
The Born control passed. The initial partial-trace control had the wrong public
spelling and argument order; retain it as a failed control. Corrected native
qptracedim(rho,0,[2,2]) yields I/2 for a Bell state.

1. Native models, tri-state validity, ensemble averages, labeled probabilities,
   instrument branches/poststates and full Naimark completion shipped through
   [PR #409](https://github.com/badtyprr/quantumstudio/pull/409). The clean build's
   native regression passed 175 assertions.
2. Symbolic substitutions, serialization/copy/re-entry, independent tetrahedral
   dilation checks and actual GUI/package gates shipped through
   [PR #410](https://github.com/badtyprr/quantumstudio/pull/410). Actual packaged
   binaries passed 214 measurement checks and 2,178 general worker checks.
3. Both scoped Standards and Spec reviews passed with zero outstanding findings.
   All three required CI jobs passed for each reviewed head and the released
   merged revision. Clean packaging, actual GUI tests, payload verification,
   publication and public download/hash verification passed. Documentation
   closure and subsequent verified disposal are tracked separately in the audit.

Current resource bounds: 64 labels, 64 Kraus matrices per outcome, dimensions up
to 64, total Naimark dimension up to 128. No whole-lesson coverage is inferred.
Symbolic declared-matrix shapes, singleton/rectangular shapes and approximate
inputs have regression coverage; unproved conditions remain pending. Numerical completion checks a 1e-10 unitary residual;
two-dimensional positive roots use the exact determinant/trace formula.

## Numerical policy and review corrections

Exact normalization and completeness are strict. Approximate-mode normalization
and completeness allow an absolute residual of 1e-12 for decimal copy/re-entry.
Positivity is not relaxed by that tolerance. Numerical unitary completion uses
1e-10; exact negative effects remain rejected. These tolerances do not establish
validity for unknown symbolic expressions.

The first independent Spec review identified hidden negative diagonal entries,
loss of symbolic label distinctness, approximate-root dispatch, and rejection of
declared symbolic matrices. Corrective regressions cover each finding. Standards
reported no documented violations and two naming/duplication suggestions; shared
label validation and the positiveSemidefinite name address those suggestions.
Final native exact-head reviews of `617dec706d5c4b34c7ca2ccfffceebe3315ba150`
report zero Standards violations/heuristics and zero Spec findings. Workflow
head `7053448572307bcc3a1bbf9b9c42aa02a0fbc061` also passed both reviews.
CI, packaged artifacts and publication were verified separately.

## Workflow development checks

The worker contract suite passed 214 checks against the actual packaged worker. It
covers exact/approximate copy and re-entry, label substitution, unknown outcome
selection, invalid nonfinite Kraus matrices, singleton/rectangular dimensions,
and partial traces of conditional Bell-state outputs. A failing symbolic-selector
copy exposed matrix separators lost inside arithmetic; recursive serialization
now retains those dimensions and separators.

The Naimark source's tetrahedral states are |0> and
(|0>+sqrt(2)*exp(i*phi)|1>)/sqrt(3), phi=0,+2*pi/3,-2*pi/3.
Effects are half their projectors. For |0> the independent probabilities are
1/2,1/6,1/6,1/6. Python complex arithmetic checks every entry of U-adjoint U
and every compressed effect of the constructed 8-by-8 unitary, using independent
state vectors. A disclosed instrument adaptation uses the rank-one identity
sqrt(P/2)=P/sqrt(2); all four conditional |0> input outputs equal their respective
projectors. The general square-root form was also tried with |i> input; the
fourth conditional state stayed pending. The rank-one form has the same pending
result for that input: the scalar engine does not establish positivity of its
exact probability. This limitation remains explicit and has a copy/re-entry
regression; it is not counted as successful evaluation or whole-lesson coverage.

A preview GUI using the development worker passed 21 checks through actual Run
and Copy buttons, clipboard re-entry, session save/open, invalid-input recovery,
and poststate/Naimark matrix display. Five screenshots were inspected. This uses
the previous released GUI with the development worker, not the final package.
The package pipeline now includes the worker suite and actual measurement GUI
checks. The final clean package passed the same 21 actual GUI checks, and all
five final captures were inspected. At minimum size, the result panel scrolls;
the full matrix is not simultaneously visible in that capture.

The workflow Spec review found pending comparisons lost nested matrix separators
and the Windows payload omitted the linked feature guide. Recursive comparison
serialization and substitution regressions address the first; packaging the guide
and its evidence addresses the second. The broader worker suite also caught a
Fourier-display regression, so arithmetic serialization is restricted to expressions
containing literal vectors. Final review of these corrections passed. The full
2,178-check worker suite passed after the correction and against the package.

## Acceptance trace and remaining limits

| Acceptance | Evidence |
| --- | --- |
| Labeled outcomes and poststates | Native instrument/ensemble tests; worker label ordering and substitutions; actual GUI display and session round-trip |
| Normalization, probabilities and partial traces | Invalid weights/states/completeness rejected; IBM 5/6,1/6 and tetrahedral 1/2,1/6,1/6,1/6 references; conditional Bell-state partial trace |
| Automatic Naimark with explicit ancilla | Full 4-by-4 and 8-by-8 unitaries; padded ancilla; independent Python U-adjoint U and every compressed effect |
| Invalid POVMs/dimensions and unknown validity | Negative/non-Hermitian/nonfinite/incomplete effects and incompatible dimensions rejected; declared symbolic shapes, unknown labels/selectors and conditions retained through substitution and copy |

Automated paths: `src/quantum-instruments-test.cc`,
`src/quantum-instruments-worker-test.py`, `windows/MeasurementGuiTests.cs`,
`windows/test-measurements-gui.ps1`. The Windows package pipeline executes the
worker and real GUI gates; its source archive includes these inputs.

The fourth tetrahedral outcome for the diagnostic |i> input has independently
positive probability (3-sqrt(6))/12, but the exact scalar sign prover leaves its
conditional state pending. This is a disclosed evaluation limitation, not a
successful evaluation claim. Symbolic unresolved calls are conservative; the
resource bounds and numerical tolerances above remain part of the contract.
IBM-011 and IBM-012 have selected-example evidence only. IBM-013 and full-lesson
coverage remain unaudited by this work.

## Verified release

Revision: `e5ed358ab533fbe72e3264e0047b8aa1d309873e`. [Public release](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-e5ed358a).

Clean native suite: 69 passes, 1 existing skip, zero failures/errors. Source archive: 329 inputs verified byte for byte. Payload: 387 files plus its manifest; 388 ZIP files.

Packaging initially stopped in the existing shutdown-observation count check under Windows PowerShell 5.1: its direct JSON pipeline counted zero despite three recorded missing-path observations. The same report counts three under PowerShell 7.6.5 and explicitly enumerated PowerShell 5.1. The final observer and unchanged packaging tail were resumed under the established PowerShell 7 host; all tested payload bytes and the source archive remained unchanged. This was a clean-source build completed through a documented final-gate resumption, not an uninterrupted successful invocation. The initial log, diagnosis, independent resumption review and byte-preservation record remain in `cleanup-audit/dev09-release-build-initial.log`, `dev09-shutdown-diagnosis.json`, `dev09-resumption-review.json` and `dev09-build-resumption.json`.

Required merged-revision CI: [Native build and tests](https://github.com/badtyprr/quantumstudio/actions/runs/41340542639/job/124949387643), [Windows GUI build and tests](https://github.com/badtyprr/quantumstudio/actions/runs/41340542668/job/124949387552), [Windows OpenQASM build and tests](https://github.com/badtyprr/quantumstudio/actions/runs/41340542707/job/124949388097).

- [QuantumStudio-Windows-x64.zip](https://github.com/badtyprr/quantumstudio/releases/download/checkpoint-e5ed358a/QuantumStudio-Windows-x64.zip): SHA-256 `ffd1485bd4bd54689659526e25853c02bfbe5292ac915dd1809fd6658e3e8f91`; 82035279 bytes, downloaded and verified.
- [QuantumStudio-source.tar.gz](https://github.com/badtyprr/quantumstudio/releases/download/checkpoint-e5ed358a/QuantumStudio-source.tar.gz): SHA-256 `f847c0a77e96eb11ef85fcb0466db650296f01fa55ceda27ca3ddea7226734e1`; 4265289 bytes, downloaded and verified.

External records: `cleanup-audit/dev09-native-pr.json`,
`dev09-workflow-pr.json`, `dev09-release.json`, `dev09-build-manifest.json`,
`dev09-release-build.log`, `dev09-release-native.log`,
`dev09-release-test-suite.log`, and `dev09-release-gui/`. The published package
contains the pre-publication development evidence; this closure records the final
verified results without modifying the tested binaries or archives.
