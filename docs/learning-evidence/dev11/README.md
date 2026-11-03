# DEV-11 source inventory and executable gap audit

Status: this page preserves the original finite audit and its historical results. DEV-11 remains partial. The subsequent DEV-11a implementation, Copy/re-entry correction, scoped DEV-11b/c release and finite DEV-11d/e/f audits and current task status are recorded in [DEV-11 delivery evidence](../DEV-11.md). Historical no-implementation statements below apply to the original audit only.

Integration review tightened the runner to require exit code 2 and the exact
expected diagnostic for each rejection. `test_probe.py` rejects crashes and
unrelated errors. Historical output archives remain unchanged; their six
rejection diagnostics satisfy the stricter check. Dates and binary provenance
below describe the original audit, not a fresh run against later releases.

## Revisions and boundaries

- Verified remote `origin/master` and isolated source base: `0fed41cb5637c578737278bf13f59590a56d6cf4`.
- Dedicated branch: `codex/dev11-inventory-20261101-a7c4`; checkout: `F:/src/libqalculate/.tools/dev11-inventory-20261101-a7c4`.
- Tested released worker: `35d9e753af19372a8f6472404726955eeba2190e`; SHA-256 `a62b058870263d33c979a84a274f6a0b37779c8a72fd91e146e2ec201aa194a8`.
- `git diff 35d9e753..0fed41cb` contains documentation and an archive-list change, no product implementation changes. This audit executed the named released binary, not a new build of the source base.
- Mode: packaged `quantum-worker.exe --json`, default exact evaluation. Numeric comparison of exact printed radicals uses an independent Python parser and tolerance `1e-12`. No GUI, circuit importer, simulator sampling, cloud service, or notebook-code execution is claimed.
- Root checkout, README, untracked files and `dist` preserved. DEV-08 was not resumed. Active DEV-09 branch `codex/dev09-measurement-validity` owned edits to `QuantumMeasurement.cc`, `QuantumInstruments.*`, and its Makefile; none was touched. No expensive builds or GUI sessions were started.

## Sources and inventory

Read [primary-inventory.md](primary-inventory.md) for the complete source-row and example-family inventory, including what remains unaudited. All 16 Foundations rows IBM-053 through IBM-068 were located in the verified-base checklist. [source-map.json](source-map.json) indexes 88 headings, 118 display-equation blocks (hash, cell and line), and 61 linked-image references; it links matching fixture families without certifying untested equations. [source-manifest.json](source-manifest.json) records source URLs, official notebook URLs, retrieval timestamps, byte hashes and cell counts. Direct HTML downloads returned 403; all 16 official notebook downloads succeeded. These notebooks contain markdown and linked media, **zero code cells**. The source notation is in markdown cell 0, whose cell ID and section are attached to each generated fixture; original notebooks are preserved outside the checkout. Adapted expressions must not be described as original IBM executable code.

Source snapshots and initial/final audit evidence are retained at `F:/src/libqalculate/cleanup-audit/dev11-20261101-a7c4/`. No full third-party notebook is committed. Retrieval dates/hashes pin the fetched content, not a claim of an upstream Git revision. Videos, diagrams and slides are separate audit surfaces; notebook retrieval does not establish visual circuit equivalence.

## Observed results

286 recorded fixtures, with the following mutually exclusive classifications:

| Classification | Count | Meaning |
|---|---:|---|
| Already-supported adaptation | 268 | Expected full result matched |
| Execution timeout | 12 | Original left-associated Shor recovery products exceeded 90 seconds each |
| Missing-operation capacity | 2 | 14- and 18-qubit Pauli representations reject at the documented nine-qubit limit |
| Unsupported adaptation syntax | 1 | Invented variadic `tensor(X,Y,Z)` rejects; nested binary tensor and source-style Unicode tensors pass |
| Validated rejection | 3 | Noncommuting generators, a group containing negative identity, and invalid CSS checks correctly reject |

There are **no confirmed incorrect numerical results** in completed comparisons. 274 fixtures meet their recorded expectations; the 12 timeouts remain failures to complete and intentionally keep the runner exit status at 1. This is not 274 source examples or whole-lesson coverage.

[comparison-tables.md](comparison-tables.md) contains the full 4-column repetition, 16-column five-qubit, 22-column Steane and 28-column Shor syndrome tables, including the identity. All 70 columns match. An additional 60 repetition-code Paulis complete its entire 64-element partition: each of the four syndromes contains 16 Paulis, for 130 syndrome comparisons in total. Recovery compares both encoded basis columns in the physical Hilbert space, including leakage. One common global phase across both columns is allowed; independent column phases are not. All five-qubit and Steane recovery checks pass. The Shor checks pass either directly or using the explicitly recorded right-associated follow-up.

Full logical-action checks pass for Shor logical X/Z, Steane logical X/Z/H/S, the Steane CSS encoder and both coset vectors, and repetition/phase-repetition encoding isometries. In particular physical `Sdg` on all seven Steane qubits gives logical S. All 16 two-qubit Pauli CNOT conjugations pass. **This does not execute transversal CNOT on two encoded Steane blocks.**

Twelve left-associated Shor expressions `C*E*V` timed out; equivalent `C*(E*V)` expressions all completed and matched the expected full 512-by-2 action. The likely issue is intermediate dense multiplication cost; it is an inference, not a profiled root cause. The first timed-out error is `IIIIIIYII`; the other two last-block Y errors and all nine Z errors also timed out. Preserve these observations rather than converting them into passes because a workaround exists.

The first harness misread symbolic radicals and omitted JSON cell arrays. The worker emits `cells` only for at most 128 entries; larger matrices remain complete in `copy_text`. The corrected harness safely parses canonical numeric matrices. Initial results under `probes/` and intermediate `verified/` are historical harness evidence, not product-bug claims. Final results are under `complete/`; a separate offline `complete-replay/` reproduced all final classifications.

## Ranked development and audit queue

Current status: DEV-11a and scoped DEV-11b/c are released; finite DEV-11d/e/f audits have been added, with wider source coverage still open. The descriptions below preserve the original scoped acceptance and ownership proposals; see [current delivery evidence](../DEV-11.md) for implementation and release results.

1. **DEV-11a — Avoid the observed Shor recovery multiplication cost (confirmed performance gap, P2).** Minimal fixture: `060-recovery-shor-IIIIIIYII`, with matching `060-associated-recovery-shor-IIIIIIYII` in fixtures. Separate decoder construction from matrix association during profiling. Acceptance: all 12 original expressions complete under the existing 90-second per-case audit bound on the same host, match both full logical columns with one common phase, and preserve the 70 syndrome columns and invalid-generator rejection checks. Likely owners: matrix evaluation (`MathStructure-matrixvector.cc` and related evaluation code), quantum expression evaluation, with `QuantumStabilizer.cc` reviewed only if profiling implicates decoder construction. Do not presume DEV-09 ownership or change its files.
2. **DEV-11b — A compact Pauli representation for finite larger codes (confirmed representation limit, P2).** `063-capacity-18` rejects an 18-letter label. Acceptance: represent an 18-qubit toric Pauli without a dense 2^18-square matrix; construct the 3x3 torus checks, verify commutation and two dependencies, rank 16, dimension 4, distance 3, all 54 one-site error syndromes and noncontractible logical-loop commutation. Likely owners: a new compact Pauli/stabilizer module plus notation boundary. The current rejection is a deliberate finite contract, not wrong arithmetic. A general decoder remains a separate task.
3. **DEV-11c — Execute a two-block Steane transversal CNOT (confirmed dense representation limit; execution route still needs discovery, P2).** `067-capacity-14` confirms that the present Pauli constructor cannot represent the 14-qubit block. Acceptance: all four encoded input columns obey logical CNOT, including relative phases and leakage; add a coherent superposition witness. Investigate an existing circuit or compact stabilizer route before extending dense algebra. Likely owners: compact Clifford/circuit execution and its source adapter. Do not claim all alternative runtime routes are absent from this capacity sentinel alone.
4. **DEV-11d — Joint stabilizer instruments and coherent recovery (unaudited dependency, not a confirmed missing feature, P2).** Coordinate with DEV-09's measurement/instrument owner. IBM-058 ZZ has two rank-two outcome projectors; acceptance must preserve Bell coherence, record both outcome probabilities and post-measurement states, then validate syndrome-controlled recovery and the IBM-056 Pauli-error discretization channel including an entangled reference. Existing projector action and deterministic syndrome algebra passing do not satisfy this task. No direct edits to DEV-09-owned files.
5. **DEV-11e — Original encoder and syndrome circuit fixtures (unaudited source surface, P2).** Transcribe and independently verify IBM-054/055/060 diagrams with their wire conventions; compare full encoding isometries, ancilla syndrome distributions and recovery, and test actual import/export if used. Algebraic adaptations in this audit are not evidence of diagram import compatibility. Likely owners: audit fixtures and circuit/importer tests; identify overlap before product changes.
6. **DEV-11f — Remaining source families and scaling (unaudited, P2).** Complete inventory items for toric topology/decoder, other code families, fault-tolerance gadgets and threshold examples. Split each sourced reproducer into an individual task only after execution identifies a concrete failure. Keep parameterized proofs, inaccessible linked slides, videos and visual diagrams explicitly open.

The variadic tensor rejection warrants a small documentation example if useful; it is not a source incompatibility and does not justify a new symbolic feature by itself. General stabilizer syndrome, correction, CSS states and CSS encoders already exist and should not be reimplemented from this audit.

## Reproduction

Use Python 3, standard library only. Run from the retained isolated checkout (PowerShell examples):

```powershell
$dev11 = 'docs/learning-evidence/dev11'
python "$dev11/fetch_sources.py" --output F:/src/libqalculate/cleanup-audit/dev11-fresh/sources
python "$dev11/probe.py" --worker F:/src/libqalculate/dist/releases/35d9e753/QuantumStudio/quantum-worker.exe --sources F:/src/libqalculate/cleanup-audit/dev11-fresh/sources --output F:/src/libqalculate/cleanup-audit/dev11-fresh/results
```

The retrieval target must not exist. Retrieval fails on source hash drift, and the runner rechecks every pinned notebook hash and the worker hash. A complete fresh run includes the costly timeout fixtures. For inexpensive verification, use preserved uncompressed evidence:

```powershell
python "$dev11/probe.py" --worker F:/src/libqalculate/dist/releases/35d9e753/QuantumStudio/quantum-worker.exe --sources F:/src/libqalculate/cleanup-audit/dev11-20261101-a7c4/sources --output F:/src/libqalculate/cleanup-audit/dev11-new-replay --replay F:/src/libqalculate/cleanup-audit/dev11-20261101-a7c4/complete/results.json
```

Replay verifies cached expressions and oracles against regenerated fixtures. An output directory should be dedicated to this run. `fixtures.json.gz` and `results.json.gz` are gzip copies of final raw evidence for portable review; decompress them into the same directory to use replay. Each fixture includes source location, notation, adaptation, expected result and expression; each result includes actual stdout/stderr or timeout, execution mode, binary hash and revision. The timestamped manifest distinguishes fresh runs from offline comparisons.

## Integration and checklist proposal

Review this branch's **documentation and fixture files only**. Fetch the branch from the retained local clone and cherry-pick its final audit commit into an integration checkout based on current master. There are no build, installation or runtime dependencies on this clone. Keep it until review/integration or verified recovery is complete. Evidence and notebook snapshots are already outside it. Do not merge or publish a release as part of this audit.

Proposed central-checklist change, for the integrator to apply separately:

> DEV-11 remains Partial. Link this inventory, complete finite comparison tables and reproducible fixture runner. Record 16/16 source rows inventoried, 0/16 certified as fully audited, and the explicit remaining media/operational/scaling gaps. Queue DEV-11a performance work and DEV-11b/c representation/runtime work; coordinate DEV-11d with DEV-09. Keep all source-row checkboxes open. No new released implementation is claimed.

The central checklist was not edited. CI and code review remain integration steps; this local audit does not claim a reviewed PR or released DEV-11 completion.

## Performance follow-up

[The isolated timing diagnosis](performance-followup.md) reduces the Shor slowdown to ordinary dense Pauli multiplication, rules out complex arithmetic and output formatting as necessary causes, and refines DEV-11a acceptance tests. Shared implementation remains unchanged.
