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
   and Naimark completion: initial regression passed 83 assertions. Development
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
