# DEV-09 development evidence (unfinished)

Base: upstream master `0fed41cb5637c578737278bf13f59590a56d6cf4`, fetched 2026-11-01.
The root checkout, README changes, untracked files and root dist are preserved.
Development checkout: `.tools/dev09-implementation-clone`. External evidence:
`cleanup-audit/dev09-*`. No release or whole-lesson completion is claimed.

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

1. Native models, validity, ensemble averages, probabilities, instrument branches
   and Naimark completion: current regression passed 175 assertions. Development
   linkage uses retained dev08-build-base; it is not a clean package build.
2. Symbolic domains, substitutions, serialization/copy/re-entry, expanded source
   fixtures and actual GUI workflows: pending. Initial native checks do not
   close these requirements.
3. Independent Standards/Spec reviews, CI, guarded merges, clean build, actual
   payload tests, publication/download verification, documentation closure and
   verified clone cleanup: pending.

Current resource bounds: 64 labels, 64 Kraus matrices per outcome, dimensions up
to 64, total Naimark dimension up to 128. No whole-lesson coverage is inferred.
Symbolic declared-matrix shapes, singleton shapes and approximate inputs still
need adversarial validation. Numerical completion checks a 1e-10 unitary residual;
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
changes, CI, packaged artifacts and publication are separate gates.

## Workflow development checks

The worker contract suite passed 198 checks against the development worker. It
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
checks; final clean packaged results remain pending.
