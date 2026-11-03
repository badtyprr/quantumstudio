# AUD-01: IBM-019 Analysis audit

Audited on 2026-11-02 (America/Los_Angeles). Evidence-only delivery. No implementation, central checklist, release, or other owner's files changed.

The bounded audit found one concrete incorrect parse, two instances of the same defect, while all 65 finite checks passed after explicit adaptations. The literal subsection is **not supported in full**. IBM-019 and AUD-01 must remain unchecked.

## Source and boundary

[IBM Deutsch's algorithm — Analysis](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-algorithm#analysis), from the Analysis heading through the final measurement sentence, excluding Further remarks on the phase kickback. IBM's linked notebook cell ID is `7e5d320e`. The notebook is only a source-text snapshot; its Python cells were not audited or executed.

The pre-test inventory contains **26 math occurrences (seven display blocks), one circuit diagram, and zero executable code cells**. Inline references and repeated variables are retained rather than silently omitted. Equality terms and case branches have distinct finite fixtures within the per-occurrence ledger. The four Boolean truth tables from the introduction are prerequisites, not an audit of that introduction.

Pinned notebook SHA-256: `c9d818b01277230bc0b7ecb64dc41fe54a53de8fcfc84c08818a5051d039567f`.
Pinned subsection SHA-256: `cb6dc2822a9de883f43e309c233556a8b22ad5a50067eb673fd107f6db3ae2a3`.
Inventory SHA-256: `9c4c15fea3d546a7079c0f6ffb1a78df80b932f85f18ade2bed2795c56c6e3b4`.
HTML, SVG, repository guidance, and inventory hashes are in `source-manifest.json`.

Source snapshots and all original runs are outside disposable checkouts at:
`F:/src/libqalculate/cleanup-audit/aud01-ibm019-analysis-20261102`.

Ownership was checked against current checklist/evidence, active chats and DEV-12/DEV-13 coordination records. IBM-019 was unclaimed. DEV-12 variational/chemistry/ML, DEV-17 named traces, and retained DEV-13/AUD-02 work are excluded. An initially delayed managed-checkout request completed; the managed checkout is the review checkout. See external `coordination.json` for setup history.

## Results and provenance

- 65 finite exact checks passed, including all four Boolean functions, all intermediate vectors, both parity branches, both global-phase signs, and right-factor measurement probabilities. These include extracted/translated expressions; they are not 65 literal source examples.
- 28 selected existing worker checks passed unchanged: exponent/trace parsing and multiline derivations, including exact/approximate and Copy/re-entry checks already present in those tests. This does not test GUI clipboard interaction.
- Two minimal unbraced-exponent cases return incorrect expressions; two braced controls pass.
- Literal-occurrence dispositions: 4 pass, 1 incorrect-result block, 4 intentional rejections, 5 unsupported, 12 conceptual/contextual. Every occurrence has a saved literal attempt, even when evaluation of a contextual symbol alone cannot prove anything.
- No unresolved execution-environment blocker remains. Earlier missing data-directory configuration and console encoding failures were setup errors. No selected occurrence is omitted from the ledger. Material outside the boundary remains unaudited.

Audit source base: `2fb33c4d435adaf3518b5c79da38392030c957ce`.
Tested release: `52c37a2abe8fce9770ad610f56bd5118a1d4bc39`.
Worker SHA-256: `ea0467a5ca5ce58d043c08bed80043361aca4305a5bb92d029781e4035e76913`.
All **404** package-manifest files were independently hashed before replay. The diff from the release to the audit base contains documentation and distribution-list changes only; no product source changed. This is a test of the retained released binary, not a fresh build.

Execution route: `quantum-worker.exe --json`, `quantum:` input prefix, default exact mode, and `QALCULATE_DEFINITIONS_DIR=<package>/data`. Complete stdout, stderr, exit status, actual JSON, expectations, adaptation, and binary revision are preserved in `ledger.json` and `checks.json`.

## Independent expectation derivation

Use basis order `|b a>`: oracle target/ancilla is the left factor, query bit is the right factor. Initial vector is `[0,0,1,0]`. Apply the standard two-term Hadamard butterfly independently to each bit to obtain `[1,1,-1,-1]/2`. Build each oracle independently as the permutation `index -> index XOR (f(index AND 1) << 1)`.

For `s0=(-1)^f(0)` and `s1=(-1)^f(1)`, the second state is `[s0,s1,-s0,-s1]/2`. Applying H to the right factor gives coefficients `s0/sqrt(2)` at index `p` and `-s0/sqrt(2)` at index `p+2`, with `p=f(0) XOR f(1)`; other coefficients vanish. This gives probability one for right bit `p`. Global phase is compared, not discarded.

The runner implements these operations with exact pairs `a+b*sqrt(2)` using Python Fraction, separately from product expressions. It compares every returned coefficient and rejects approximate results. No product-computed expected state, Qiskit, numerical tolerance, or stochastic oracle is used. The four Boolean functions exhaust this algorithm's finite inputs. For the generic integer-parity sentence, write `k=2m+r` and use `(-1)^(2m)=1`; that is a mathematical rationale, not a claim of symbolic proof automation.

## Per-occurrence summary

The complete machine-readable ledger contains original TeX, exact source offsets, literal input/output, expected meaning, explicit adaptations with their full outputs, fixtures, and binary revision. This table is only an index.

| ID | Meaning | Literal disposition | Finite evidence |
|---|---|---|---|
| M01 | Initial ket | Pass | initial |
| M02 | First-state equality chain | Unsupported full paste | pi1-0..2 |
| M03 | Oracle reference | Conceptual | oracle-1..4 |
| M04 | Repeated oracle reference | Conceptual | oracle-1..4 |
| M05 | Boolean-function symbol | Conceptual | all four truth tables |
| M06 | First-state reference | Conceptual | pi1-0..2 |
| M07 | XOR-label second state | Intentional symbolic-label rejection | pi2-xor-1..4 |
| M08 | Bit phase identity | Intentional symbolic-label rejection | xor-0/1-0..2 |
| M09 | Bit-domain statement | Conceptual | both possible bits exhausted |
| M10 | Explicit two-case derivation | Incorrect result | two red exponent probes; six extracted terms pass |
| M11 | Second-state reference | Conceptual | pi2-phase fixtures |
| M12 | Distributed/factored second state | Unsupported full paste | both terms for all four functions |
| M13 | Oracle reference in prose | Conceptual | oracle-1..4 |
| M14 | Minus ancilla ket | Pass | minus; complete second states |
| M15 | Repeated oracle reference | Conceptual | oracle-1..4 |
| M16 | Oracle-dependent global phase | Unsupported function semantics | phase-1..4 |
| M17 | Second-state reference | Conceptual | pi2-factor fixtures |
| M18 | Factoring and parity branches | Intentional scalar-XOR rejection | both forms for all four functions |
| M19 | Parity expression | Intentional scalar-XOR rejection | exhaustive substituted parities |
| M20 | Minus-one scalar | Pass | minus-one |
| M21 | Difference of function values | Unsupported function semantics | difference-1..4 |
| M22 | Generic integer power | Conceptual; appropriate symbolic result | sign-equivalence-1..4 and parity proof |
| M23 | Integer variable reference | Conceptual | same proof |
| M24 | Repeated variable reference | Conceptual | same proof |
| M25 | Final-state cases | Unsupported full paste | pi3-1..4, circuit-1..4 |
| M26 | Unit-probability conclusion | Scalar passes; claim needs separate check | measure-1..4 |

The diagram is exercised through explicit matrix translation for all four oracles. It is not a GUI import, source-code execution, or drawing-fidelity check. Source state names and an undeclared `f` are not automatically bound by earlier prose. Successful parsing of their symbols is not successful evaluation of the algorithm.

## Ranked development handoff

1. **P1 — unbraced TeX exponent absorbs the next factor (incorrect result).** `quantum:(-1)^0 \bigl( \vert 0\rangle - \vert 1\rangle \bigr)` returns `(-1)^[0;0]`, expected `[1;-1]`. Exponent 1 returns `(-1)^[1;-1]`, expected `[-1;1]`. The same expressions with `{0}`/`{1}` return the expected vectors. `regressions.py` preserves both red cases and controls. Proposed tests must compare dimensions and every exact coefficient, then Copy/re-enter; keep existing trace-exponent regressions. Route to quantum-notation/parser owner. Sent to active DEV-17 developer for shared-parser-owner routing, explicitly without expanding named-trace scope.
2. **P2 — source Boolean-function semantics are absent from this literal route.** Bare `f(0)` evaluates as zero, and `(-1)^{f(0)}` as one, because it is treated as multiplication, not an arbitrary Boolean function. This is an unsupported source interpretation, not proof that established calculator multiplication is wrong. Proposed regression/feature contract: an explicit Boolean-function declaration for all four truth tables must distinguish both signs and validate its domain; preserve ordinary implicit multiplication. Route to symbolic-function/DEV-05 coordinator. Finite substitution is a workaround only.
3. **P2 — full source derivations need expression extraction and/or a defined binding/piecewise contract.** M02, M12 and M25 reject in original form. Preserve their full originals before minimizing formatting, state-label binding and cases separately; do not infer one root cause from the first diagnostic. Proposed tests: source block plus separately extracted expressions, all four functions and both branches, with source state names explicitly declared if required. Route to notation coordinator. The smaller P1 failure above is the proven wrong parse.

Symbolic XOR rejections are **intentional current limits**, not regressions. A domain-preserving symbolic extension is optional future DEV-05 work; it must retain literal-width validation and reject out-of-domain substitutions. The generic integer-parity argument and symbol references are conceptual, not missing execution features.

The kickoff coordinator chat was archived, so its notification was rejected. No chat was reopened. The reviewable proposal is in `CHECKLIST-PROPOSAL.md`; the P1 failure was handed to the active developer. No central checklist was edited.

## Reproduction

From this repository checkout, with Python 3 and the retained package available:

```powershell
python -X utf8 docs/learning-evidence/aud01-ibm019/run.py --evidence F:/src/libqalculate/cleanup-audit/aud01-ibm019-analysis-20261102 --package F:/src/libqalculate/dist/releases/52c37a2a/QuantumStudio --output F:/src/libqalculate/cleanup-audit/aud01-ibm019-analysis-20261102/replay
python -X utf8 docs/learning-evidence/aud01-ibm019/regressions.py --source . --package F:/src/libqalculate/dist/releases/52c37a2a/QuantumStudio --output F:/src/libqalculate/cleanup-audit/aud01-ibm019-analysis-20261102/replay-regressions
```

`run.py` checks source and payload hashes, saves originals before adapted executions, and requires all 65 finite comparisons to pass. `regressions.py` runs selected original AST test blocks unchanged and requires the two known red cases plus two passing controls to remain observable; a fix causes it to request ledger reassessment. It is an audit reproduction, not a CI acceptance test that blesses wrong behavior.

The first retained run had 12 adaptation failures: explicit `*` used for a tensor product and missing projector grouping. Those were audit-fixture mistakes, corrected without product edits. `run-1` remains historical evidence; `final` is authoritative. No whole lesson, general notebook route, arbitrary oracle declaration, GUI workflow, or release certification is claimed.
