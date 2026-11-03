# DEV-12 variational and numerical coverage

Status: **Partial**. This is source-backed finite mathematical evidence, not
whole-lesson, SDK, optimizer-convergence or provider acceptance. Workstream
ownership is not a new set of DEV-12 subtask IDs.

## Variational design: existing-route evidence

Base fetched before checkout: `753bf16df56aeae0f6454f89999ef203665755f6`.
Fresh baseline probes used the previously released `checkpoint-c575cb7e` binary;
this is fresh testing of an existing package, not a new build or resumed release.
The new regression is `src/quantum-variational-test.py`. All 78 requests passed:
75 scalar/matrix requests and three separately assessed numerical sampling
requests. Worker SHA-256 is recorded with every saved run in the external
`cleanup-audit/dev12-20261102/variational/baseline-regression.json`.
The [tracked baseline summary](dev12/variational-baseline-summary.json) pins
the worker, build manifest, regression, source manifest and full run hashes;
all 388 manifest payload files were reverified.
Review, merge, CI and new-release status are pending; these results alone do not
claim delivery of a product change.

### Sources and inventory

[Pinned manifest](dev12/variational-source-manifest.json) records the URL,
retrieval time, complete notebook SHA-256, zero-based cell indexes, cell IDs,
per-cell source hashes and headings for eight source rows / 349 cells. The raw
notebooks are retained outside disposable checkouts at
`cleanup-audit/dev12-20261102/variational/`. The initial HTTP 403 responses are
preserved; downloading with a browser User-Agent succeeded. Content hashes pin
the retrieved revision because the IBM endpoint has no exposed commit ID.
Inventory is not execution: **zero of eight whole rows are certified**.

| Source | Selected adaptation | Still unaudited / outside this finite tranche |
|---|---|---|
| [IBM-101](https://quantum.cloud.ibm.com/learning/en/courses/variational-algorithm-design/variational-algorithms), cells 3–5 | Variational expectation semantics exercised through the concrete Hamiltonians below | General variational theorem/proofs; whole lesson |
| [IBM-102](https://quantum.cloud.ibm.com/learning/en/courses/variational-algorithm-design/reference-states), cells 3,5 | Three-qubit classical and entangled reference states | Template TwoLocal and feature-map examples; all SDK execution |
| [IBM-103](https://quantum.cloud.ibm.com/learning/en/courses/variational-algorithm-design/ansaetze-and-variational-forms), cells 2,3 | Rx, CX, X circuit at source angles pi/3, pi/2; extra negative-angle witness | Five-qubit NLocal/TwoLocal, EfficientSU2, full QAOA/ML circuits and diagrams |
| [IBM-104](https://quantum.cloud.ibm.com/learning/en/courses/variational-algorithm-design/cost-functions), cells 7,11,18 | H-state cost 2X−Z; two-qubit XX−3YY ansatz at three fixed parameter vectors | Original primitives, MaxCut workload, hardware/noise/mitigation/suppression examples |
| [IBM-105](https://quantum.cloud.ibm.com/learning/en/courses/variational-algorithm-design/optimization-loops), cells 2,9 | Eight-parameter cost/analytic gradients; five gradient-descent steps on the MOD-012 one-qubit cost | Original SLSQP/BFGS/COBYLA execution, convergence, bootstrapping and barren-plateau claims |
| [IBM-106](https://quantum.cloud.ibm.com/learning/en/courses/variational-algorithm-design/instances-and-extensions), cells 4,17,28 | Bell-state energies, weighted SSVQE cost and VQD overlap penalty | Complete iterative SSVQE/VQD, source sampler overlap circuit and QSR; provider execution |
| [IBM-107](https://quantum.cloud.ibm.com/learning/en/courses/variational-algorithm-design/examples-and-applications), cell 2 | Four analytic eigenstates of the first explicit Hamiltonian | Remaining custom optimizer runs, VQD, molecular workload, MaxCut/QAOA and performance comparisons |
| [MOD-012](https://quantum.cloud.ibm.com/learning/en/modules/computer-science/vqe), cells 13,15,43 | Supplied one-qubit H/H2 costs, rotations, derivatives; Rx/Rz sampling bases | Chemistry derivation, original optimizer/hardware calls, reaction-energy and overhead experiments; continuum oscillator exercise |

These are **manual adaptations into native notation/protocols**, not executions
of the original Python cells. No SDK packages or source notebooks were run.
The manifest deliberately keeps whole-cell execution unaudited even for cells
whose selected mathematics is covered in this table.

### Conventions and independent oracles

Native wire 0 is most significant. Qiskit wire 0 is least significant: for n
wires, the adaptation maps source q to native n−1−q. The source three-qubit
reference becomes `(ket(4)+ket(7))/sqrt(2)` in coordinate notation. The Rx
example instead has amplitudes cos(theta/2) at index 4 and
−i sin(theta/2) at index 7. Full complex vectors are compared; a relative or
global phase is not stripped from these tests. Normalization is checked
separately.

Angles are radians, with R_P(theta)=exp(−i theta P/2). For the two-qubit
TwoLocal adaptation, the reference is |01>; parameter order is the two Rz
angles, two Ry angles, CX(0,1) in source wire numbering, then the final two Rz
and two Ry angles. An independent Python state-vector oracle applies 2×2
matrices directly to bit-indexed amplitudes. XX−3YY couples 00↔11 with weight
4 and 01↔10 with weight −2. All eight gradients are checked using analytic
tangent propagation dR/dtheta=(−i/2)PR and dE=2 Re(dpsi†Hpsi), rather than
finite differences or a second call to the implementation's derivative.

For MOD-012's supplied H coefficients, C(x)=0.2355(cos(x)−1), C′(x)=
−0.2355 sin(x), C″(x)=−0.2355 cos(x). Parameter shifts are compared with this
analytic reference. The repeated-parameter witness Rx(2x) requires a factor
of two; naively shifting x by pi/2 would be wrong. Five steps use learning
rate 0.2 from x=1 and verify each parameter update and cost; they establish
neither global nor asymptotic convergence. For H2, C(x)=a+b cos(x)+c sin(x)
under Ry(x), with the source cell 43 coefficients. This checks the supplied
operator, not the physical accuracy of its chemistry mapping. MOD-012 prose
and code differ on H/H2 and basis/mapping descriptions; no chemical provenance
is inferred from these numerical coefficients.

For 2II−2XX+3YY−3ZZ, the Bell states phi+, phi−, psi+, psi− have energies
−6,4,6,4 by their Pauli eigenvalue signs. Tests verify both expectations and
full eigenvector residuals, weighted energies, self-overlap penalties and
orthogonal overlap. These finite identities are exact; numerical state,
cost and derivative comparisons use absolute tolerance 2e−12. The three
20,000-shot checks use seed 120105 and absolute frequency tolerance 0.025;
they are stochastic witnesses of Z/X/Y basis observation for Rx(0.7) then
Rz(−0.4), not exact arithmetic or derivative oracles.

### Existing routes and preserved failures

`expect`, rotations, local `apply`, matrix products, scalar `diff`, derivative
evaluation at a point, and numerical circuit sampling already work for the
tested inputs. Symbolic cost and derivative Copy/re-entry are checked twice,
then substituted at an independently evaluated point. No new variational API
is introduced.

Original probes are retained outside the checkout (`original-probes.json`,
`derivative-probes.json`, `derivative-at-point-probes.json`). Unquoted ASCII
`theta` is parsed as ordinary multiplied letters, whereas Greek theta, x or a
quoted symbol works. `replace(diff(f,x),x,value)` replaces the differentiation
symbol before differentiation and rejects; use the existing
`diff(f,x,1,value)` interface. Matrix-valued `diff(Rx(x),x)` remains unresolved;
this is not scalar-gradient support. No missing general optimizer or matrix
derivative implementation is inferred from the finite scalar audit.

The first regression attempt encountered `Division by zero` while formatting
an approximately zero cancellation of a normalized-vector norm. The test now
compares the returned scalar against the independent reference in Python,
without asking the product to format that cancellation. The original input
and response remain in `baseline-regression-attempt-1.json`; that numerical
cancellation diagnostic is unresolved and is not counted as newly supported.
Attempt 2 exposed a test-parser assumption that tiny complex residuals would
print as real; accepting complex numerical output corrected the harness.

## Machine learning: existing-route evidence

[Scoped ML evidence](dev12/ml-audit.md) inventories IBM-096–100 plus
IBM-119/QB-007, with zero full source rows certified. The final development
run passes 65 packaged-worker expressions and 65 actual canonical re-entries,
plus 15 native numerical circuits with 2,064 full amplitudes and probabilities
at absolute tolerance 1e−12. The native adapter is a separately built audit
executable, not a packaged GUI or original SDK execution. Existing numerical
state regression: 3,664 checks passed.

This includes finite seven-qubit feature-map/overlap matrices on pinned source
data, eight-qubit classifier circuits on two authored inputs, a disclosed
reduced QB-007 adaptation, and 32 source MaxCut basis energies. No ML product
gap was confirmed. Two dense quantum-notation inputs hit the existing
complexity guard; the ordinary calculator expectation route passes. Both
original failures and the working route are recorded. An initial review found
reversed source class labels; the final run corrects them to horizontal −1 /
vertical +1 and retains prior results. Separate final-head Standards and Spec
reviews report zero findings; integration CI/merge remain pending.

Original SDK/notebook execution, training, prediction quality, convergence,
untested encoding families, large-circuit scaling, source media and hardware
remain open. Ideal finite Gram-matrix positivity is not a certification of
finite-shot kernel positivity. These boundaries do not reduce the full task.

## Coordination and retained limits

Agent 2 owns chemistry and diagonalization, Agent 3 owns machine learning.
Only the integration owner edits this combined evidence, the central checklist
and shared build files. Ready ML evidence is linked above; chemistry evidence
will be linked when its implementation and audit are ready.

The retained DEV-13 owner confirmed QB-007 is static inventory only, at qBraid
revision `86787e1ba372facc224f925189755e69c479828b`, notebook SHA-256
`221d531613cbf4f74db1f9df4faf2c28d462c13480f28b5b559ec2ffc0f1697d`.
Its successful retained SDK proof concerns QB-012, not QB-007. Cirq/qsimcirq
execution, GPU setup and framework locks remain DEV-13-owned and pending.
Half-turn gate exponents, signed-coupling sandwiches, row-major measurement
order, unseeded field generation and shot randomness must be distinguished
in any QB-007 adaptation. Its implemented objective is diagonal Z/ZZ despite
the transverse-field wording; no X field is silently added.

DEV-11 remains Partial and its original 286 expectations are unchanged.
DEV-09's unresolved tetrahedral symbolic conditional state and DEV-10's
documented limits remain. No intentional rejection is relabeled as support.
