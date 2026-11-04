# IBM-019 phase-kickback audit and DEV-05 single-bit complement

Work in progress; no release or whole-lesson claim. The coordinator owns the
central checklist and integration. Assigned base is
`02d5ca3f5713385818e80db15b1a58e3b518e569`.

## Source boundary

[IBM Deutsch's algorithm](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-algorithm),
“Further remarks on the phase kickback”, heading inclusive to the end of
markdown cell 0 (`7e5d320e`). The retained original notebook SHA-256 is
`c9d818b01277230bc0b7ecb64dc41fe54a53de8fcfc84c08818a5051d039567f`.
The section occupies decoded source offsets [7157,9425); its UTF-8 SHA-256 is
`50ee0688790ae063e2ef8e2b2e30ae8dafc03b860786cabf8fc27f6ff4e4c1c9`.
`inventory.py` verifies the original hash before extracting anything.

All 20 math occurrences are retained, including six display blocks and repeated
inline references. This section has no code cells, diagrams or embedded media.
The complete notebook's 17 cells are separately indexed and hashed for routing;
its eight code cells are unexecuted and outside this mathematics increment.
The notebook lane received their exact cell indexes and retained-source location.

Raw source remains outside disposable checkouts in
`F:/src/libqalculate/cleanup-audit/aud01-ibm019-analysis-20261102/source.ipynb`.
New complete outputs are under
`F:/src/libqalculate/cleanup-audit/math-lane-20261104/phase/`.

## Independent mathematical expectations

The basis order is |b a>; a is the rightmost bit. The oracle maps basis index
2b+a to 2(b XOR f(a))+a. Enumerating four source truth tables and both bits
therefore fixes every permutation-matrix entry without using calculator output.
X complements a basis bit. Its minus-state eigenvector has eigenvalue -1.
The final state is [s0,s1,-s0,-s1]/2 with sj=(-1)^f(j).

Every scalar and coefficient comparison is exact in Q(sqrt(2)); no numerical
tolerance is used. The unequal normalized [3/5;4/5] witness checks both sides
of the arbitrary-psi identity. Exhaustive basis columns justify the finite
linear-map identity mathematically, but do not certify arbitrary symbolic
state declarations or an SDK route. No complex witness is claimed.

## Released baseline

All 404 manifest payload files of released `52c37a2a` were verified before
execution. Worker SHA-256:
`ea0467a5ca5ce58d043c08bed80043361aca4305a5bb92d029781e4035e76913`.
The expanded `run-2` retains 20 literal attempts and 120 finite adaptations:
118 exact values and their canonical text re-entries pass; two complement
adaptations remain unresolved. Run-1's smaller 92-case inventory is historical.
These are fresh executions of retained release bytes, not a fresh build.

`negation-repro.py` reproduces the same gap with original TeX extraction:
`\vert \neg 0\rangle` and `\vert \neg 1\rangle`, and natural `|¬0>`/`|¬1>`,
return opaque named states. Four independent X/XOR controls pass. The source
symbol b has been explicitly substituted by each allowed bit; this is a
disclosed finite adaptation. The full original block stays in the inventory.
The red-capable reproducer intentionally exits 1 until the contract is met.

| Occurrences | Literal disposition and finite evidence |
|---|---|
| P01, P07 | Domain declarations; literal syntax rejected. Bit-domain constraints used explicitly in finite fixtures. |
| P02 | Symbolic XOR intentionally rejected. All four extracted literal XOR and X-power cases pass. |
| P03, P04, P08, P09 | Branch conditions, not standalone proof claims. Context is supplied in finite fixtures. |
| P05 | Full block rejected at symbolic XOR. Identity, unchanged basis, X and power terms pass; NOT terms expose the scoped gap. |
| P06 | Full symbolic oracle/XOR block rejected. All 16 basis mappings and all three extracted terms pass after truth-table substitution. |
| P10, P11 | Unbound oracle/psi has no source semantics. Both sides pass for a disclosed rational witness; basis controls separately justify linearity. |
| P12 | Full original rejected. All three terms pass for all eight (f,a) cases after explicit substitution. |
| P13 | Original eigenrelation evaluates true; both terms also independently checked as full exact vectors. |
| P14–P16 | Minus vector, X and -1 parse; alone these references do not prove the eigenrelation. |
| P17–P19 | Oracle and state-name references remain unbound. Their isolated parsing is not algorithm support. |
| P20 | Original aligned block rejected. All three extracted expressions pass for all four truth tables, including global signs. |

## Assigned finite implementation contract

The coordinator accepted this remaining DEV-05 P1 gap on 2026-11-04:
single-bit complement in ket and bra labels, using original TeX and natural
negation; concrete bits 0/1; symbolic scalar-bit substitution; strict bit-domain
rejection; exact Copy/re-entry; preserve opaque/non-bit labels and existing
notation/DEV-17 behavior. General Boolean formulas and arbitrary-width
complement are excluded. This is new supported semantics, not a claim that a
previously promised feature regressed.

Draft implementation recognizes the normalized `not` keyword only at a word
boundary in a label and lowers to existing `basis(1-b,2)`. Since 1-b is an
integer in [0,1] exactly when b is, existing basis validation enforces the bit
domain after substitution. Fractional, negative, greater-than-one and complex
controls were tested against this existing route before editing the parser.
Names follow existing scalar identifier semantics; no global bit declaration
or Boolean function binding is introduced. An explicit dimension suffix is
rejected because this operation already denotes one bit.

Product scope is `libqalculate/QuantumNotation.cc`,
`src/quantum-notation-test.cc` and the dedicated
`src/quantum-bit-complement-worker-test.py`. No algebra source edits are needed.
Build registration belongs to the coordinator. Standalone native notation
validation passes 562 checks (538 inherited and 24 new). The dedicated regression
passes 104 candidate checks; the same final harness on the unchanged parser has
66 failures among 80 attempts. Additional Copy checks run only after a value
passes, so those totals are not directly comparable test inventories. The
candidate parser SHA-256 is
`588872b5d877e694312bfbf7091dcb1f8689243ea3ed0ee568760987b135ad53`.
Final independent Standards/Spec reviews and integrated acceptance remain pending.
Actual GUI Clipboard and saved-session behavior require a separately scheduled
slot; canonical worker re-entry is not a substitute for them.

## Reproduction

From the checkout, run `inventory.py --source <retained source.ipynb> --output <new directory>`.
Run `probe.py --source <source> --package <verified package> --output <new directory>`
for original literals plus finite adaptations. It deliberately exits 1 when
any expectation remains unmet, including known unsupported complement semantics.
`negation-repro.py --package <package> --output <new report.json>` is the minimal
source-derived reproduction.

The dedicated worker regression takes `--worker`, `--definitions` and `--output`.
Its optional `--translator` route explicitly records a standalone parser plus
retained evaluator. Canonical function output is re-entered through the retained
quantum parser to preserve quantum symbol options; the retained parser never
sees the new complement spelling. It must never be reported as an integrated
worker build. Existing bras serialize as ordinary vectors, checked in full
against plain-bra controls. The initial harness incorrectly required matrix-row
metadata and used ordinary evaluation options; those failed runs are retained.
The first new opaque-label parser test also expected an evaluated function name
instead of its actual intermediate translation; its expectation was corrected.
The original full-lesson derivations, symbolic XOR, Boolean functions, arbitrary
psi, SDK cells, earlier introduction/circuit section and all other lessons remain
outside this bounded acceptance. IBM-019 and AUD-01 remain unchecked.
