# Learning coverage and development priorities

Updated: 2026-10-20. This is the decision queue for the full IBM Quantum Learning and qBraid goal, not a reduction of its scope.

## Choose the next development task

P0 = broken release, data loss or incorrect established behavior: stop feature work and repair it. P1 = current algorithm workflows and shared prerequisites. P2 = broader mathematical and notebook coverage. P3 = external runtime/compiler integrations. Priority reflects the requested emphasis on circuits and algorithms; it is editable, not a promise about effort.

Effort is a rough relative size: S = one scoped change; M = several changes; L = an epic that must be split after a source reproduction. No calendar estimate is implied. Dependencies name prerequisites, not automatic proof that every linked lesson needs that feature.

Recommended order: finish REL-03 publication; run AUD-01 and AUD-02 alongside code work; then finish DEV-05 and the reproduced DEV-16 include gap, followed by the remaining DEV-03/04/06/07/08 work. Choose the first ready P1 item supported by a failing source fixture. Promote newly discovered widespread failures above isolated features.

| ID | Priority | Size | State | Depends on | Work |
|---|---|---|---|---|---|
| [DEV-01](#dev-01) | P1 | S | Implemented; release pending | None | Compact bound-index products |
| [DEV-02](#dev-02) | P1 | L | Implemented; release pending | DEV-01 | Domain-preserving symbolic Fourier expansion |
| [DEV-03](#dev-03) | P1 | L | Partial | None | Declared orthonormal bases |
| [DEV-04](#dev-04) | P1 | L | Partial | DEV-03 | Symbolic operator assumptions and identities |
| [DEV-05](#dev-05) | P1 | M | Partial | None | Register dimensions and symbolic bit strings |
| [DEV-06](#dev-06) | P1 | L | Not implemented | None | Runtime gate parameters |
| [DEV-07](#dev-07) | P1 | L | Not implemented | None | Dynamic wire indexing |
| [DEV-08](#dev-08) | P1 | L | Not implemented | DEV-07 | Array/set iteration and subroutine-local storage |
| [DEV-09](#dev-09) | P2 | L | Partial | DEV-03 | Symbolic ensembles, instruments and POVMs |
| [DEV-10](#dev-10) | P2 | L | Partial | DEV-05 | Symbolic domains, sets and indexed families |
| [DEV-11](#dev-11) | P2 | L | Partial | DEV-04 | Error-correction lesson operations |
| [DEV-12](#dev-12) | P2 | L | Partial | DEV-04 | Variational and numerical operator coverage |
| [DEV-13](#dev-13) | P2 | L | Discovery needed | AUD-02 | Python/SDK notebook execution route |
| [DEV-14](#dev-14) | P3 | L | Not implemented | DEV-13 | QIR and CUDA-Q compatibility |
| [DEV-15](#dev-15) | P3 | L | Not implemented | DEV-13 | Cloud/provider and pulse workflows |
| [DEV-16](#dev-16) | P1 | M | Implementation in review | None | Local OpenQASM include dependencies |
| [AUD-01](#aud-01) | P1 | M | Pending | None | Audit algorithms first |
| [AUD-02](#aud-02) | P1 | M | Pending | None | Complete source discovery |
| [AUD-03](#aud-03) | P2 | M | Pending | AUD-01 | Audit remaining mathematical lessons |
| [AUD-04](#aud-04) | P2 | M | Pending | AUD-02 | Audit remaining notebooks end to end |

## Release queue

- [x] REL-01: Release `92f80696`: 70 packaged audit groups, 262 verified visual captures, 340 manifest files. ZIP SHA-256 `d621438711c3ff6a58f819b3c3d559db547b187d3b2c5f5f099e87c71bdb3323`.
- [x] REL-02: Published [checkpoint `14ed45e2`](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-14ed45e2), including matrix declarations/assumptions, Gram positivity, Fourier display and the package-smoke repair. Validation: 74 packaged audit groups, 266 verified visual captures, 340 manifest files. ZIP SHA-256 `6b1a7e5df9d40904ff5ce4d26367a67c24c55741db631f325ebb4aa3122e5f4d`.
- [ ] REL-03: Publish merged revision `d7acc12b39c729b3c460ccbe3c224c02c19ed393` after artifact verification. Includes [#292](https://github.com/badtyprr/quantumstudio/pull/292), [#293](https://github.com/badtyprr/quantumstudio/pull/293), [#295](https://github.com/badtyprr/quantumstudio/pull/295), [#296](https://github.com/badtyprr/quantumstudio/pull/296), [#297](https://github.com/badtyprr/quantumstudio/pull/297) and built-in `|GHZ>` in [#298](https://github.com/badtyprr/quantumstudio/pull/298). Required merged-tip CI passed. Package build/audit progress does not establish publication.
- [ ] REL-04: Integrate and release the reviewed symbolic-label and local-include changes after REL-03. [#299](https://github.com/badtyprr/quantumstudio/pull/299) has passed required CI; [#300](https://github.com/badtyprr/quantumstudio/pull/300) and [#301](https://github.com/badtyprr/quantumstudio/pull/301) remain gated on their exact commits' checks. None is included in REL-02 or REL-03.

## Acceptance criteria by development item

### DEV-01

- [ ] **Compact bound-index products** — P1; Implemented; release pending; size S; dependencies: None.
- Source focus: Fundamentals: phase estimation; IBM Fourier double sum. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Finish xy parsing without changing quoted names, pi or nested index declarations. Verify QFT residuals for N=1..4 in exact/approximate modes and symbolic copy round trips.
- Evidence: IBM Fourier double-sum reproduction; [#292](https://github.com/badtyprr/quantumstudio/pull/292) merged as `48115b3ca953f80747df0e05df478c1a92788666`; release pending in REL-03. Nested index declarations, lexical constants and parser complexity limits have regression coverage. Tests: `src/quantum-worker-test.py`, `src/quantum-notation-test.cc`. Owner: unassigned.

### DEV-02

- [ ] **Domain-preserving symbolic Fourier expansion** — P1; Implemented; release pending; size L; dependencies: DEV-01.
- Source focus: Fundamentals: phase estimation and factoring. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Simplify QFT_N|x>_N to a capture-free normalized Fourier sum with IBM positive phase. Preserve integer/range constraints after substitution: x=N, fractional x and invalid N must still reject. Test inverse and N=1.
- Evidence: [#293](https://github.com/badtyprr/quantumstudio/pull/293) merged as `61e04203bbfecb606dea1ea68352cdada6786f29`; release pending in REL-03. Regression coverage in `src/quantum-worker-test.py` and `src/quantum-algebra-test.cc`: forward/inverse sums, invalid substitution, cancellation, fresh indices and canonical copy. Owner: unassigned.

### DEV-03

- [ ] **Declared orthonormal bases** — P1; Partial; size L; dependencies: None.
- Source focus: Basics and general formulation: states and measurements. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Declare a named basis and dimension; reduce inner products to Kronecker delta and complete projector sums to identity. Unknown bases must stay unresolved. Verify declarations survive save/load and copy.
- Merged, release pending in REL-03: [#295](https://github.com/badtyprr/quantumstudio/pull/295) adds scoped finite named declarations and within-basis contractions; [#296](https://github.com/badtyprr/quantumstudio/pull/296) adds full finite projector sums. Distinct bases retain unknown overlaps; symbolic families and dedicated editing remain outstanding. The full DEV-03 item remains partial.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### DEV-04

- [ ] **Symbolic operator assumptions and identities** — P1; Partial; size L; dependencies: DEV-03.
- Source focus: General formulation: unitary operations and channels. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Add explicit unitary/Hermitian/projector assumptions with dimension checks; simplify U†U and projector products only when justified. Reject incompatible substitutions and preserve noncommuting order.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### DEV-05

- [ ] **Register dimensions and symbolic bit strings** — P1; Partial; size M; dependencies: None.
- Source focus: Fundamentals: query algorithms and Fourier algorithms. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Carry widths through tensor products, basis labels and bit operations. Test leading zeros, empty registers, concatenation, indexed registers, and contradictory dimensions; ambiguous widths remain symbolic.
- In review: [#299](https://github.com/badtyprr/quantumstudio/pull/299) preserves typed symbolic binary labels through operations, set kets and copy/substitution, including deferred cardinality when labels may become equal. Required CI passed; 1,540 worker checks and 18 GUI checks passed locally. Not merged or released. Indexed-register concatenation, general symbolic domains and widths beyond the finite limit remain outstanding.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### DEV-06

- [ ] **Runtime gate parameters** — P1; Not implemented; size L; dependencies: None.
- Source focus: qBraid PyQASM examples and algorithm notebooks. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Preserve a supported runtime arithmetic angle through importer, circuit model, save/load and executor. Compare small numerical circuits with a reference; reject unavailable types and invalid angles clearly.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### DEV-07

- [ ] **Dynamic wire indexing** — P1; Not implemented; size L; dependencies: None.
- Source focus: qBraid PyQASM and generated circuits. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Evaluate bounded runtime wire indices consistently in import and execution; test in-range, negative, out-of-range, aliases and multi-qubit collisions. Keep source-local diagnostics.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### DEV-08

- [ ] **Array/set iteration and subroutine-local storage** — P1; Not implemented; size L; dependencies: DEV-07.
- Source focus: qBraid PyQASM examples. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Implement one supported construct per PR: bounded arrays/set loops, then local lifetimes and shadowing. Test nested calls, loop transfers, cleanup, serialization, and resource limits.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### DEV-09

- [ ] **Symbolic ensembles, instruments and POVMs** — P2; Partial; size L; dependencies: DEV-03.
- Source focus: General formulation: general measurements. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Represent labeled outcomes and post-measurement states; verify normalization, probabilities and partial trace. Add automatic Naimark construction with explicit ancilla dimensions and rejection of invalid POVMs.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### DEV-10

- [ ] **Symbolic domains, sets and indexed families** — P2; Partial; size L; dependencies: DEV-05.
- Source focus: General formulation and fundamentals. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Support required Cartesian alphabets, symbolic membership/cardinality and lesson-specific indexed families. Preserve singleton/empty sets, binder scopes and unresolved equality. Add actual failing source fixtures before implementing each extension.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### DEV-11

- [ ] **Error-correction lesson operations** — P2; Partial; size L; dependencies: DEV-04.
- Source focus: Foundations of quantum error correction. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Audit every stabilizer/CSS/logical-operator example; turn unsupported encodings, syndromes and recovery operations into separate small tasks. Compare logical action and syndrome tables against source examples.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### DEV-12

- [ ] **Variational and numerical operator coverage** — P2; Partial; size L; dependencies: DEV-04.
- Source focus: Variational design; chemistry; diagonalization; ML. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Inventory unsupported objectives, derivatives, matrix functions and eigensolvers from source examples. Verify small reference problems and report numerical tolerances independently of exact arithmetic.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### DEV-13

- [ ] **Python/SDK notebook execution route** — P2; Discovery needed; size L; dependencies: AUD-02.
- Source focus: qBraid SDK, algorithms and IBM code examples. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Specify and implement a reproducible notebook/program import or execution route for each required framework. Distinguish direct execution from manual QASM adaptation. Pin dependencies and test equivalent states, counts and errors.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### DEV-14

- [ ] **QIR and CUDA-Q compatibility** — P3; Not implemented; size L; dependencies: DEV-13.
- Source focus: qBraid QIR and CUDA-Q notebooks. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Audit entry points and program semantics; implement explicit supported imports/execution and verify small circuits. Unsupported compiler/runtime features must be recorded per notebook, not silently dropped.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### DEV-15

- [ ] **Cloud/provider and pulse workflows** — P3; Not implemented; size L; dependencies: DEV-13.
- Source focus: qBraid Runtime/Provider-Jobs; IBM utility-scale courses. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Separate local mathematical semantics from credentials, hardware jobs and pulse/timing dependencies. Define tested adapters and observable unsupported cases; use deterministic offline fixtures, and record any required external verification.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### DEV-16

- [ ] **Local OpenQASM include dependencies** — P1; Implementation in review; size M; dependencies: None.
- Source: [QB-004 evidence](learning-evidence/QB-004.md), generated oracle and algorithm subroutine instructions. Direct includes fail while explicit inlining imports successfully.
- Acceptance: Resolve dependencies relative to a selected source file with an explicit policy for external paths and paste-only input. Preserve standard includes; diagnose missing files, cycles and duplicate declarations with file/line context. Bound depth and total bytes; preserve dependency identity through save/load/export and detect changed dependencies. Verify both generated subroutines and numerical equivalence to inlining, nested includes and paths containing spaces.
- Priority rationale: This blocks a demonstrated local circuit workflow. Select after the queued Fourier/basis release and DEV-05; it does not depend on runtime wire indexing or cloud access. Source-aware import context is part of this task.
- In review: [#300](https://github.com/badtyprr/quantumstudio/pull/300) captures bounded dependency snapshots; [#301](https://github.com/badtyprr/quantumstudio/pull/301) adds the source-aware compiler CLI and generated-module adapter. Both unchanged QB-004 subroutine fixtures match explicitly inlined circuit documents in Python and the frozen compiler. Neither change is merged or released.
- Still required: retain source identity in both editors and undo/history; surface changed dependencies; map compiler diagnostics to original source; verify save/load, standalone export and failure recovery. The CLI route alone does not close DEV-16 or QB-004.
- Evidence: release `92f80696` importer reproduction in `docs/learning-evidence/QB-004.md`; proposed tests `windows/test-qasm-source-bundle.py` and `windows/test-qasm-file-import.py`. Owner: unassigned.

### AUD-01

- [ ] **Audit algorithms first** — P1; Pending; size M; dependencies: None.
- Source focus: IBM fundamentals + qBraid Algorithms and PyQASM. These are audit targets, not a claim that every page has the same gap.
- Acceptance: For every formula/code cell in these rows, record input, expected result, actual result, mode, fixture and revision; create a DEV item for each failure. Re-run selected existing tests instead of calling a whole lesson complete.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### AUD-02

- [ ] **Complete source discovery** — P1; Pending; size M; dependencies: None.
- Source focus: All IBM/qBraid catalogs. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Reconcile the pinned inventory with current catalogs. Inventory overviews, exams, videos, downloads, linked examples, SDK references and qBook chapters. Track access-blocked sources explicitly; a missing chapter cannot count as covered.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### AUD-03

- [ ] **Audit remaining mathematical lessons** — P2; Pending; size M; dependencies: AUD-01.
- Source focus: Remaining IBM sections/modules. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Use the same per-example evidence contract; prioritize shared parser/algebra failures before isolated special cases. Record non-executable conceptual content with a reviewed rationale.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### AUD-04

- [ ] **Audit remaining notebooks end to end** — P2; Pending; size M; dependencies: AUD-02.
- Source focus: All remaining qBraid notebooks. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Execute/import every relevant cell through the documented route, including setup and output interpretation. Preserve source commit/hash and distinguish adaptations from unchanged notebook execution.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

## Source checklist

The pinned inventory contains **137 IBM course sections, 12 IBM modules and 35 qBraid notebooks (184 rows)**. All whole-source audits below remain open: existing feature tests prove selected examples, not exhaustive coverage. These counts are inventory counts, not a percentage of the full goal. IDs below are stable; append new IDs when sources are discovered.

Each row closes only after an evidence record lists every relevant formula/code cell, direct input versus adaptation, exact/approximate results, copy/save/import behavior where relevant, and all failures linked to development IDs. Mark access restrictions as blocked with a reason. Do not check a row merely because its title or one example is supported.

For each completed audit, add `docs/learning-evidence/<ID>.md` containing: source URL and date/revision/hash; example table (location, input, expected, actual, status, test path); unresolved DEV dependencies; reviewed commit/CI; release revision. Until then, unchecked means unproven, not necessarily unsupported.

Pinned URLs and notebook hashes: [source inventory](learning-source-inventory.json). Existing partial evidence: [notation support and limits](quantum-notation.md), [worker regressions](../src/quantum-worker-test.py), [parser integration tests](../src/quantum-parser-integration-test.cc), [QASM import tests](../windows/test-qasm-import.py), [classical import tests](../windows/test-qasm-classical-expressions.py).

### general-formulation-of-quantum-information

- [ ] **IBM-001** [density-matrices/introduction](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/density-matrices/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-002** [density-matrices/density-matrix-basics](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/density-matrices/density-matrix-basics) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-003** [density-matrices/convex-combinations](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/density-matrices/convex-combinations) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-004** [density-matrices/bloch-sphere](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/density-matrices/bloch-sphere) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-005** [density-matrices/multiple-systems](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/density-matrices/multiple-systems) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-006** [quantum-channels/introduction](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/quantum-channels/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-007** [quantum-channels/quantum-channel-basics](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/quantum-channels/quantum-channel-basics) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-008** [quantum-channels/representations-of-channels](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/quantum-channels/representations-of-channels) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-009** [quantum-channels/representation-equivalence](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/quantum-channels/representation-equivalence) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-010** [general-measurements/introduction](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/general-measurements/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-011** [general-measurements/formulations-of-measurements](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/general-measurements/formulations-of-measurements) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-012** [general-measurements/naimark-theorem](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/general-measurements/naimark-theorem) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-013** [general-measurements/discrimination-and-tomography](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/general-measurements/discrimination-and-tomography) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-014** [purifications-and-fidelity/introduction](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/purifications-and-fidelity/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-015** [purifications-and-fidelity/purifications](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/purifications-and-fidelity/purifications) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-016** [purifications-and-fidelity/fidelity](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/purifications-and-fidelity/fidelity) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
### fundamentals-of-quantum-algorithms

- [ ] **IBM-017** [quantum-query-algorithms/introduction](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-018** [quantum-query-algorithms/query-model-of-computation](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/query-model-of-computation) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-019** [quantum-query-algorithms/deutsch-algorithm](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-algorithm) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-020** [quantum-query-algorithms/deutsch-jozsa-algorithm](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-jozsa-algorithm) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-021** [quantum-query-algorithms/simon-algorithm](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/simon-algorithm) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-022** [quantum-algorithmic-foundations/introduction](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-algorithmic-foundations/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-023** [quantum-algorithmic-foundations/factoring-and-gcd](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-algorithmic-foundations/factoring-and-gcd) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-024** [quantum-algorithmic-foundations/measuring-computational-cost](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-algorithmic-foundations/measuring-computational-cost) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-025** [quantum-algorithmic-foundations/simulating-classical-computations](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-algorithmic-foundations/simulating-classical-computations) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-026** [phase-estimation-and-factoring/introduction](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/phase-estimation-and-factoring/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-027** [phase-estimation-and-factoring/phase-estimation-problem](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/phase-estimation-and-factoring/phase-estimation-problem) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-028** [phase-estimation-and-factoring/phase-estimation-procedure](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/phase-estimation-and-factoring/phase-estimation-procedure) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-029** [phase-estimation-and-factoring/shor-algorithm](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/phase-estimation-and-factoring/shor-algorithm) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-030** [grover-algorithm/introduction](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/grover-algorithm/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-031** [grover-algorithm/unstructured-search](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/grover-algorithm/unstructured-search) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-032** [grover-algorithm/grover-algorithm-description](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/grover-algorithm/grover-algorithm-description) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-033** [grover-algorithm/analysis](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/grover-algorithm/analysis) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-034** [grover-algorithm/number-of-iterations](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/grover-algorithm/number-of-iterations) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-035** [grover-algorithm/concluding-remarks](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/grover-algorithm/concluding-remarks) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
### basics-of-quantum-information

- [ ] **IBM-036** [single-systems/introduction](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/single-systems/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-037** [single-systems/classical-information](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/single-systems/classical-information) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-038** [single-systems/quantum-information](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/single-systems/quantum-information) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-039** [single-systems/qiskit-implementation](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/single-systems/qiskit-implementation) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-040** [multiple-systems/introduction](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/multiple-systems/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-041** [multiple-systems/classical-information](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/multiple-systems/classical-information) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-042** [multiple-systems/quantum-information](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/multiple-systems/quantum-information) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-043** [multiple-systems/qiskit-implementation](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/multiple-systems/qiskit-implementation) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-044** [quantum-circuits/introduction](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/quantum-circuits/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-045** [quantum-circuits/circuits](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/quantum-circuits/circuits) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-046** [quantum-circuits/inner-products-and-projections](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/quantum-circuits/inner-products-and-projections) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-047** [quantum-circuits/limitations-on-quantum-information](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/quantum-circuits/limitations-on-quantum-information) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-048** [entanglement-in-action/introduction](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/entanglement-in-action/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-049** [entanglement-in-action/quantum-teleportation](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/entanglement-in-action/quantum-teleportation) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-050** [entanglement-in-action/superdense-coding](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/entanglement-in-action/superdense-coding) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-051** [entanglement-in-action/chsh-game](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/entanglement-in-action/chsh-game) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-052** [entanglement-in-action/qiskit-implementation](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/entanglement-in-action/qiskit-implementation) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
### foundations-of-quantum-error-correction

- [ ] **IBM-053** [correcting-quantum-errors/introduction](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/correcting-quantum-errors/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-054** [correcting-quantum-errors/repetition-codes](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/correcting-quantum-errors/repetition-codes) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-055** [correcting-quantum-errors/shor-code](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/correcting-quantum-errors/shor-code) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-056** [correcting-quantum-errors/discretization-of-errors](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/correcting-quantum-errors/discretization-of-errors) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-057** [stabilizer-formalism/introduction](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/stabilizer-formalism/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-058** [stabilizer-formalism/pauli-operations-and-observables](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/stabilizer-formalism/pauli-operations-and-observables) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-059** [stabilizer-formalism/repetition-code-revisited](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/stabilizer-formalism/repetition-code-revisited) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-060** [stabilizer-formalism/stabilizer-codes](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/stabilizer-formalism/stabilizer-codes) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-061** [quantum-code-constructions/introduction](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/quantum-code-constructions/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-062** [quantum-code-constructions/css-codes](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/quantum-code-constructions/css-codes) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-063** [quantum-code-constructions/toric-code](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/quantum-code-constructions/toric-code) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-064** [quantum-code-constructions/other-code-families](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/quantum-code-constructions/other-code-families) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-065** [fault-tolerant-quantum-computing/introduction](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/fault-tolerant-quantum-computing/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-066** [fault-tolerant-quantum-computing/approach-to-fault-tolerance](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/fault-tolerant-quantum-computing/approach-to-fault-tolerance) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-067** [fault-tolerant-quantum-computing/controlling-error-propagation](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/fault-tolerant-quantum-computing/controlling-error-propagation) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-068** [fault-tolerant-quantum-computing/threshold-theorem](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/fault-tolerant-quantum-computing/threshold-theorem) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### use-a-qc-today

- [ ] **IBM-069** [build-and-run-your-first-quantum-program](https://quantum.cloud.ibm.com/learning/en/courses/use-a-qc-today/build-and-run-your-first-quantum-program) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-070** [quantum-mechanics-basics](https://quantum.cloud.ibm.com/learning/en/courses/use-a-qc-today/quantum-mechanics-basics) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-071** [your-first-quantum-experiment](https://quantum.cloud.ibm.com/learning/en/courses/use-a-qc-today/your-first-quantum-experiment) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-072** [quantum-computing-context](https://quantum.cloud.ibm.com/learning/en/courses/use-a-qc-today/quantum-computing-context) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-073** [continue-your-learning-journey](https://quantum.cloud.ibm.com/learning/en/courses/use-a-qc-today/continue-your-learning-journey) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### quantum-computing-in-practice

- [ ] **IBM-074** [introduction](https://quantum.cloud.ibm.com/learning/en/courses/quantum-computing-in-practice/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-075** [running-quantum-circuits](https://quantum.cloud.ibm.com/learning/en/courses/quantum-computing-in-practice/running-quantum-circuits) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-076** [utility-scale-qaoa](https://quantum.cloud.ibm.com/learning/en/courses/quantum-computing-in-practice/utility-scale-qaoa) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-077** [applications-of-qc](https://quantum.cloud.ibm.com/learning/en/courses/quantum-computing-in-practice/applications-of-qc) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-078** [mapping](https://quantum.cloud.ibm.com/learning/en/courses/quantum-computing-in-practice/mapping) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-079** [simulating-nature](https://quantum.cloud.ibm.com/learning/en/courses/quantum-computing-in-practice/simulating-nature) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### tools-for-quantum-advantage

- [ ] **IBM-080** [introduction](https://quantum.cloud.ibm.com/learning/en/courses/tools-for-quantum-advantage/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-081** [noise-and-errors](https://quantum.cloud.ibm.com/learning/en/courses/tools-for-quantum-advantage/noise-and-errors) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-082** [error-suppression](https://quantum.cloud.ibm.com/learning/en/courses/tools-for-quantum-advantage/error-suppression) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-083** [error-mitigation](https://quantum.cloud.ibm.com/learning/en/courses/tools-for-quantum-advantage/error-mitigation) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-084** [error-correction-i](https://quantum.cloud.ibm.com/learning/en/courses/tools-for-quantum-advantage/error-correction-i) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### integrating-quantum-and-high-performance-computing

- [ ] **IBM-085** [introduction](https://quantum.cloud.ibm.com/learning/en/courses/integrating-quantum-and-high-performance-computing/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-086** [compute-resources](https://quantum.cloud.ibm.com/learning/en/courses/integrating-quantum-and-high-performance-computing/compute-resources) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-087** [programming-models](https://quantum.cloud.ibm.com/learning/en/courses/integrating-quantum-and-high-performance-computing/programming-models) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-088** [sqd-skqd](https://quantum.cloud.ibm.com/learning/en/courses/integrating-quantum-and-high-performance-computing/sqd-skqd) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-089** [next-steps](https://quantum.cloud.ibm.com/learning/en/courses/integrating-quantum-and-high-performance-computing/next-steps) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### quantum-diagonalization-algorithms

- [ ] **IBM-090** [introduction](https://quantum.cloud.ibm.com/learning/en/courses/quantum-diagonalization-algorithms/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-091** [vqe](https://quantum.cloud.ibm.com/learning/en/courses/quantum-diagonalization-algorithms/vqe) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-092** [krylov](https://quantum.cloud.ibm.com/learning/en/courses/quantum-diagonalization-algorithms/krylov) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-093** [sqd-overview](https://quantum.cloud.ibm.com/learning/en/courses/quantum-diagonalization-algorithms/sqd-overview) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-094** [sqd-implementation](https://quantum.cloud.ibm.com/learning/en/courses/quantum-diagonalization-algorithms/sqd-implementation) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-095** [skqd](https://quantum.cloud.ibm.com/learning/en/courses/quantum-diagonalization-algorithms/skqd) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### quantum-machine-learning

- [ ] **IBM-096** [introduction](https://quantum.cloud.ibm.com/learning/en/courses/quantum-machine-learning/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-097** [classical-ml-review](https://quantum.cloud.ibm.com/learning/en/courses/quantum-machine-learning/classical-ml-review) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-098** [data-encoding](https://quantum.cloud.ibm.com/learning/en/courses/quantum-machine-learning/data-encoding) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-099** [quantum-kernel-methods](https://quantum.cloud.ibm.com/learning/en/courses/quantum-machine-learning/quantum-kernel-methods) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-100** [qvc-qnn](https://quantum.cloud.ibm.com/learning/en/courses/quantum-machine-learning/qvc-qnn) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### variational-algorithm-design

- [ ] **IBM-101** [variational-algorithms](https://quantum.cloud.ibm.com/learning/en/courses/variational-algorithm-design/variational-algorithms) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-102** [reference-states](https://quantum.cloud.ibm.com/learning/en/courses/variational-algorithm-design/reference-states) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-103** [ansaetze-and-variational-forms](https://quantum.cloud.ibm.com/learning/en/courses/variational-algorithm-design/ansaetze-and-variational-forms) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-104** [cost-functions](https://quantum.cloud.ibm.com/learning/en/courses/variational-algorithm-design/cost-functions) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-105** [optimization-loops](https://quantum.cloud.ibm.com/learning/en/courses/variational-algorithm-design/optimization-loops) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-106** [instances-and-extensions](https://quantum.cloud.ibm.com/learning/en/courses/variational-algorithm-design/instances-and-extensions) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-107** [examples-and-applications](https://quantum.cloud.ibm.com/learning/en/courses/variational-algorithm-design/examples-and-applications) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### quantum-chem-with-vqe

- [ ] **IBM-108** [introduction](https://quantum.cloud.ibm.com/learning/en/courses/quantum-chem-with-vqe/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-109** [hamiltonian-construction](https://quantum.cloud.ibm.com/learning/en/courses/quantum-chem-with-vqe/hamiltonian-construction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-110** [ansatz](https://quantum.cloud.ibm.com/learning/en/courses/quantum-chem-with-vqe/ansatz) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-111** [classical-optimizers](https://quantum.cloud.ibm.com/learning/en/courses/quantum-chem-with-vqe/classical-optimizers) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-112** [ground-state](https://quantum.cloud.ibm.com/learning/en/courses/quantum-chem-with-vqe/ground-state) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-113** [geometry](https://quantum.cloud.ibm.com/learning/en/courses/quantum-chem-with-vqe/geometry) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### utility-scale-quantum-computing

- [ ] **IBM-114** [introduction](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-115** [bits-gates-and-circuits](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/bits-gates-and-circuits) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-116** [teleportation](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/teleportation) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-117** [grovers-algorithm](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/grovers-algorithm) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-118** [quantum-phase-estimation](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/quantum-phase-estimation) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-119** [variational-quantum-algorithms](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/variational-quantum-algorithms) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-120** [quantum-simulation](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/quantum-simulation) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-121** [classical-simulation](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/classical-simulation) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-122** [hardware](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/hardware) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-123** [quantum-circuit-optimization](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/quantum-circuit-optimization) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-124** [error-mitigation](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/error-mitigation) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-125** [utility-i](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/utility-i) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-126** [utility-ii](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/utility-ii) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-127** [utility-iii](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/utility-iii) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### quantum-business-foundations

- [ ] **IBM-128** [start-your-quantum-journey](https://quantum.cloud.ibm.com/learning/en/courses/quantum-business-foundations/start-your-quantum-journey) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-129** [introduction-to-quantum-computing](https://quantum.cloud.ibm.com/learning/en/courses/quantum-business-foundations/introduction-to-quantum-computing) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-130** [quantum-computing-fundamentals](https://quantum.cloud.ibm.com/learning/en/courses/quantum-business-foundations/quantum-computing-fundamentals) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-131** [quantum-technology](https://quantum.cloud.ibm.com/learning/en/courses/quantum-business-foundations/quantum-technology) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-132** [business-impacts](https://quantum.cloud.ibm.com/learning/en/courses/quantum-business-foundations/business-impacts) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-133** [how-to-become-quantum-ready](https://quantum.cloud.ibm.com/learning/en/courses/quantum-business-foundations/how-to-become-quantum-ready) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### designing-and-leading-quantum-projects

- [ ] **IBM-134** [introduction](https://quantum.cloud.ibm.com/learning/en/courses/designing-and-leading-quantum-projects/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-135** [early-stages](https://quantum.cloud.ibm.com/learning/en/courses/designing-and-leading-quantum-projects/early-stages) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-136** [standing-up-team](https://quantum.cloud.ibm.com/learning/en/courses/designing-and-leading-quantum-projects/standing-up-team) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-137** [grant-writing](https://quantum.cloud.ibm.com/learning/en/courses/designing-and-leading-quantum-projects/grant-writing) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### ibm_module

- [ ] **MOD-001** [quantum-mechanics/get-started-with-qiskit](https://quantum.cloud.ibm.com/learning/en/modules/quantum-mechanics/get-started-with-qiskit) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **MOD-002** [quantum-mechanics/superposition-with-qiskit](https://quantum.cloud.ibm.com/learning/en/modules/quantum-mechanics/superposition-with-qiskit) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **MOD-003** [quantum-mechanics/stern-gerlach-measurements-with-qiskit](https://quantum.cloud.ibm.com/learning/en/modules/quantum-mechanics/stern-gerlach-measurements-with-qiskit) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **MOD-004** [quantum-mechanics/exploring-uncertainty-with-qiskit](https://quantum.cloud.ibm.com/learning/en/modules/quantum-mechanics/exploring-uncertainty-with-qiskit) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **MOD-005** [quantum-mechanics/bells-inequality-with-qiskit](https://quantum.cloud.ibm.com/learning/en/modules/quantum-mechanics/bells-inequality-with-qiskit) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **MOD-006** [computer-science/deutsch-jozsa](https://quantum.cloud.ibm.com/learning/en/modules/computer-science/deutsch-jozsa) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **MOD-007** [computer-science/grovers](https://quantum.cloud.ibm.com/learning/en/modules/computer-science/grovers) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **MOD-008** [computer-science/quantum-teleportation](https://quantum.cloud.ibm.com/learning/en/modules/computer-science/quantum-teleportation) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **MOD-009** [computer-science/quantum-key-distribution](https://quantum.cloud.ibm.com/learning/en/modules/computer-science/quantum-key-distribution) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **MOD-010** [computer-science/qft](https://quantum.cloud.ibm.com/learning/en/modules/computer-science/qft) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **MOD-011** [computer-science/shors-algorithm](https://quantum.cloud.ibm.com/learning/en/modules/computer-science/shors-algorithm) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **MOD-012** [computer-science/vqe](https://quantum.cloud.ibm.com/learning/en/modules/computer-science/vqe) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### qbraid_notebook

- [ ] **QB-001** [PyQASM-Examples/deutsch_josza_unroll.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/PyQASM-Examples/deutsch_josza_unroll.ipynb) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **QB-002** [PyQASM-Examples/qasm_processing.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/PyQASM-Examples/qasm_processing.ipynb) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **QB-003** [PyQASM-Examples/qasm_unroll.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/PyQASM-Examples/qasm_unroll.ipynb) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **QB-004** [qBraid-Algorithms/bernstein_vazirani.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Algorithms/bernstein_vazirani.ipynb) — P1 / AUD-01; partial cell audit; includes blocked by DEV-16; notebook/cloud execution remains DEV-13/15; [evidence](learning-evidence/QB-004.md).
- [ ] **QB-005** [qBraid-Algorithms/qft.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Algorithms/qft.ipynb) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **QB-006** [qBraid-Algorithms/qpe.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Algorithms/qpe.ipynb) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **QB-007** [qBraid-Algorithms/cirq_vqe.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Algorithms/cirq_vqe.ipynb) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **QB-008** [qBraid-Algorithms/ibm_batch_jobs_grovers.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Algorithms/ibm_batch_jobs_grovers.ipynb) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **QB-009** [qBraid-SDK/bell_circuit_examples.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-SDK/bell_circuit_examples.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-010** [qBraid-SDK/qbraid_sdk_devices.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-SDK/qbraid_sdk_devices.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-011** [qBraid-SDK/qbraid_sdk_transpiler.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-SDK/qbraid_sdk_transpiler.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-012** [qBraid-SDK/qbraid_sdk_transpiler_braket_qiskit.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-SDK/qbraid_sdk_transpiler_braket_qiskit.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-013** [qBraid-SDK/qbraid_sdk_transpiler_cirq_stim.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-SDK/qbraid_sdk_transpiler_cirq_stim.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-014** [qBraid-SDK/qbraid_visualization.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-SDK/qbraid_visualization.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-015** [qBraid-QIR/autoqasm_deutsch_jozsa.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-QIR/autoqasm_deutsch_jozsa.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-016** [qBraid-QIR/qbraid_qir_sim_batch_jobs.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-QIR/qbraid_qir_sim_batch_jobs.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-017** [qBraid-QIR/qbraid_transpiler_braket_to_qir.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-QIR/qbraid_transpiler_braket_to_qir.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-018** [qBraid-QIR/qir_to_squin_conversion.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-QIR/qir_to_squin_conversion.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-019** [qBraid-Runtime/aws_sim_qiskit_bernstein_vazirani.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Runtime/aws_sim_qiskit_bernstein_vazirani.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-020** [qBraid-Runtime/ibm_quantum_jobs_with_runtime.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Runtime/ibm_quantum_jobs_with_runtime.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-021** [qBraid-Runtime/qbraid_pulser_pasqal.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Runtime/qbraid_pulser_pasqal.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-022** [qBraid-Runtime/qbraid_runtime_batch_jobs.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Runtime/qbraid_runtime_batch_jobs.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-023** [qBraid-Runtime/qbraid_runtime_bloqade_aquila.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Runtime/qbraid_runtime_bloqade_aquila.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-024** [qBraid-Runtime/qbraid_runtime_qbraid_provider_aws_devices.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Runtime/qbraid_runtime_qbraid_provider_aws_devices.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-025** [qBraid-Runtime/quobly_alloy_forge_quickstart.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Runtime/quobly_alloy_forge_quickstart.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-026** [qBraid-Runtime/quobly_ghz_noise_benchmark.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Runtime/quobly_ghz_noise_benchmark.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-027** [Provider-Jobs/qbraid_runtime_braket_provider.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/Provider-Jobs/qbraid_runtime_braket_provider.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-028** [Provider-Jobs/qbraid_runtime_ionq_provider.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/Provider-Jobs/qbraid_runtime_ionq_provider.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-029** [Provider-Jobs/qbraid_runtime_oqc_provider.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/Provider-Jobs/qbraid_runtime_oqc_provider.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-030** [Provider-Jobs/qbraid_runtime_pasqal_provider.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/Provider-Jobs/qbraid_runtime_pasqal_provider.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-031** [Provider-Jobs/qbraid_runtime_qiskit_provider.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/Provider-Jobs/qbraid_runtime_qiskit_provider.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-032** [Provider-Jobs/qbraid_runtime_quantinuum_provider.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/Provider-Jobs/qbraid_runtime_quantinuum_provider.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-033** [Provider-Jobs/qbraid_runtime_rigetti_provider.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/Provider-Jobs/qbraid_runtime_rigetti_provider.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-034** [qBraid-CUDAQ/cuda_quantum_qpu_benchmarking.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-CUDAQ/cuda_quantum_qpu_benchmarking.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-035** [qBraid-CUDAQ/cuda_quantum_quickstart.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-CUDAQ/cuda_quantum_quickstart.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.

## Discovery checklist (outside the 184 pinned rows)

- [ ] DISC-01 — Reconcile all current IBM course/module/learning-path catalogs with the 2026-10-14 inventory; record added/removed/changed URLs.
- [ ] DISC-02 — Inventory IBM overview pages, exams, practice content, videos, downloadable notebooks and linked tutorials; assign stable IDs and source-specific audit tasks.
- [ ] DISC-03 — Reconcile qBraid demo repository HEAD with the pinned `86787e1ba372facc224f925189755e69c479828b` snapshot; record changed notebook hashes and new/deleted paths.
- [ ] DISC-04 — Inventory qBraid SDK, PyQASM, QIR, Algorithms and runtime syntax references beyond demonstration notebooks; separate syntax support from provider execution.
- [ ] DISC-05 — Inventory qBook courses and chapters through authorized access; record unavailable/account-only content as access-blocked rather than complete.

Catalog entry points checked 2026-10-19: [IBM Learning](https://quantum.cloud.ibm.com/learning/en), [qBraid documentation](https://docs.qbraid.com/v2/home/introduction), [qBraid demos](https://github.com/qBraid/qbraid-lab-demo). This check confirms entry points only, not that their entire content has been audited.

## Updating priorities and progress

1. Select a ready ID from the priority table. Add an owner and a linked issue/PR when work starts; split L items into independently testable child IDs.
2. Link the exact source example and failing regression before changing code. Record whether it needs parsing, algebra, GUI, importer, or execution work.
3. Review the final commit and run risk-appropriate CI. Fix release regressions before additional feature work.
4. Record implementation, merge and release separately. Tick a development item only after its acceptance criteria and released-artifact checks pass.
5. Update affected source evidence records, then tick only fully audited source rows. Report completed/total inventoried rows alongside unresolved discovery tasks; never label that ratio overall goal completion.
