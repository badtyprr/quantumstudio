# DEV-11f reconciliation (Partial)

This tranche reconciles the original 16-row inventory against pinned notebook
content, the 88 headings / 118 displayed equations / 61 image references in the
unchanged source map, and the new finite diagram checks. The machine-readable
[remaining-source-ledger.json](remaining-source-ledger.json) preserves each
heading/equation location and separates **retrieved**, **visually inspected** and
**untested** images. Retrieval alone is not compatibility evidence. No whole
source row is certified. The original 286 fixtures are unchanged.

## Feasible executions

[family-audit.py](family-audit.py) executes 1,920 native recovery adaptations:
all 64 choices of no X or one X in each Shor block, crossed with no Z or Z on
any of nine wires, on both encoded basis states and a complex superposition.
The IBM-055 source location is “Simultaneous bit- and phase-flip errors,” markdown
cell 0 `8b06b8f1`. Original source claim/reproducer: independently correct up to
one X per block and a Z in any position. This is a **finite expansion of prose**,
not 1,920 IBM circuits. Two ancillas are measured and reset for each inner parity
pair; the original simplified phase extraction follows. Corrections use the
source syndrome table and block rule. Expected full recovered vectors come from
the independent GHZ-block formula, including the minus sign when X and Z overlap.
All 1,920 pass; leakage and relative phases are checked on the full physical state.
The broader family allowing multiple Z errors with at most one odd-parity block
is still untested here.

Twenty-four scalar adaptations execute on the hash-pinned released worker
`214e6866`, exact mode: all eight classical majority strings (IBM-054 “Classical
encoding and decoding”); three repetition-noise probabilities (independent
Bernoulli enumeration versus the source polynomial); ten threshold recurrence
instances with C=2 or 3, p=1/100, k=0…4 (IBM-068 “Threshold theorem”); and three
evaluations of IBM-055's displayed binomial tail. All pass. The threshold oracle
uses repeated rational squaring independently of the closed-form expression.
Chosen C/p/k values are labeled adaptations; they are **not physical threshold
estimates**, proof of the theorem, or noisy-gadget experiments. The Shor scalar
checks validate the displayed expression against a binomial tail only; they do
not establish exact logical failure for every higher-weight error pattern.

Portable results are `family-results.json.gz` and `family-fixtures.json.gz`;
raw evidence is outside the checkout under
`F:/src/libqalculate/cleanup-audit/dev11ef-20261102/`. The native adapter uses the
pinned upstream numerical core; this is not a new application build/release.
The source notebook hashes are rechecked, and worker/native executable hashes
are recorded. The diagram audit separately reports actual exporter/importer
round trips; none is claimed for these dynamically corrected family fixtures.

## Remaining inventory and triage

| Source / scope | Classification and next evidence needed |
|---|---|
| IBM-053,057,061,065 introductions | Context/roadmap, not an additional executable example. Lesson videos/slides remain untested. |
| IBM-054 repetition | Finite original encoders/extractions/recovery now checked; classical majority and three noise-polynomial instances checked. General noisy-channel executions remain untested. |
| IBM-055 Shor | Encoders, both phase extractions, physical Z sweep and expanded X/Z family checked. Other propagation drawings and error-probability graph retrieved but not visually certified. Multiple-Z parity family and complete stochastic logical channel remain untested. |
| IBM-056 discretization | General unitary/Kraus recovery and entangled-reference instruments belong to DEV-11d. This tranche adds no channel-completeness claim. Generalization to arbitrary errors is a mathematical argument, not finite executable acceptance. |
| IBM-058 Pauli observables | Historical finite products/projector action retained. Full finite group enumeration, spectral decomposition, four original measurement diagrams and nondestructive instrument semantics remain untested here; coordinate DEV-11d. |
| IBM-059 repetition revisited | Historical full Pauli partition retained. Two original diagrams and complete joint sector instruments remain untested here. Do not substitute deterministic syndrome algebra. |
| IBM-060 stabilizer codes | Original Steane encoder now checked. Five-qubit/Bell/repetition/phase/Shor/Steane historical finite examples retained. Generic synthesis, distance proofs, code-space dimension proof and arbitrary-error guarantees remain mathematical/untested surfaces. Conceptual lowest-weight picture inspected, not a circuit. |
| IBM-062 CSS | Historical Steane codeword/isometry evidence retained. All 16 Hamming words, classical closure, general dual construction and generic combined-error decoding remain untested. Parameterized CSS statements need proof review, not a fabricated simulation test. |
| IBM-063 toric topology | Original picture is L=9, 162 physical qubits. DEV-11b's L=3, 18-qubit checks are a finite adaptation owned by the lead. Fourteen topology/error diagrams remain untested here. Neither the old dense Pauli rejection nor L=3 checks certify the L=9 picture. |
| IBM-063 decoder | Endpoint pairing, shortest paths, minimum-weight perfect matching, homology failure/ties and noise-dependent decoder performance remain untested. No concrete decoder failure was executed, so there is no new implementation task claiming a missing decoder. |
| IBM-064 surface codes | Rough/smooth boundaries, one logical qubit, left/right X and top/bottom Z chains, and rotated distance-five checks remain untranscribed/untested. No inferred generator table or verified rank/distance. |
| IBM-064 color codes | Q6…Q0 Steane face geometry and the 19-vertex [[19,1,5]] example remain untested. Reversing IBM-062 words for the Steane encoder does not certify these geometric diagrams. |
| IBM-064 gross code | [[144,12,12]], weight-six checks: source summary, not a supplied full construction/decoder. No concrete implementation failure demonstrated. Error Correction Zoo is an onward resource, outside this finite inventory. |
| IBM-066 fault-tolerance approach | Teleportation/encoded gadget diagrams and correction insertions remain untested. Five-wire blocks are illustrative, not a fully specified five-qubit implementation. Independent/correlated noise assumptions and reliable classical processing are theoretical/model assumptions. |
| IBM-067 transversal gadgets | Historical single-block logical actions retained. Two-block Steane CNOT belongs to DEV-11c lead. Cascade diagrams and full single-fault-location enumeration remain untested here; single CNOT identities do not certify protected gadgets. |
| IBM-067 magic states and correction | T/S injection measurement branches, encoded injection, classical postprocessing, distillation, Shor cat-state verification and Steane correction gadgets remain untested. Eight linked images are not retrieved in this tranche. Coordinate instrument owner before product edits. |
| IBM-068 threshold | Ten finite scalar recurrence instances pass. Formal noise model, concatenation guarantees, overhead O(N log^c N), parameterized induction and physical threshold estimates remain theoretical/unverified. The lesson explicitly omits formal model details. Survey is noncomputational. |

## Access failures, untested material and product tasks

The original IBM-057 Box slide URL
`https://ibm.box.com/public/static/umposbds8d27cv8rnpsayyaj1k2aw88o.pdf`
has a **historical retrieval-route failure**, not proof that the slide is absent.
No fresh slide/video retrieval or playback is claimed. Of 61 image references,
27 were retrieved and pinned, 18 inspected, and 34 have no retrieval attempt in
this tranche. Untested is not inaccessible. All official notebook snapshots are
available and hash-verified; they contain no code cells.

**New confirmed product failures: zero. New implementation tasks: zero.** All
completed new comparisons pass. Source omissions, abstract diagrams, access
failures and proofs are not promoted into product failures. Historical intentional
14/18-qubit dense-constructor limits remain separately documented DEV-11b/c
tasks; this tranche does not reclassify them or infer that all runtime routes fail.
The existing numerical core executes the eleven-wire Shor ancilla circuits.

If a future concrete example fails, create one task per reproduced failure with:
source URL/hash/cell/section, original input/circuit and wire conventions,
explicit adaptation, independent expected full result, actual exit/stdout/stderr
or timeout, product/source/binary hashes, and finite acceptance criteria that
replay the original input. Preserve failures even when a workaround passes.
Agree implementation ownership with the lead before editing shared product code.

## Proposed central-checklist handoff (lead-owned; not applied)

> Keep DEV-11 Partial and every IBM-053–068 row open. Link this tranche and the
> original diagram audit. Record 216 manual numerical checks, 50 actual unitary
> exporter/importer semantic round trips, 1,920 expanded Shor recovery cases and
> 24 exact scalar instances. Distinguish manual transcription from original
> executable source/import support. Remaining dynamic importer, all-media,
> code-family, topology/decoder, gadget/noise, scaling and proof surfaces stay
> open. DEV-11b/c/d outcomes require their owners' separate evidence.

No shared checklist, DEV-11 summary, product code, build list or notation was
edited. Integration, guarded merge and publication belong to the lead. Retain
the isolated checkout until integration or verified recovery. Root README,
untracked files, dist, and retained DEV-13/AUD-02/DEV-16 work were not modified.
