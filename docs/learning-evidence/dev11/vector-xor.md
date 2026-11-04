# DEV-11: source-backed vector XOR indexing

Source: IBM-062 CSS codes, notebook SHA-256
`e8b1deec5f914fc07cd75fcf26051712116a936dc50d38ed2149032b8487b4f5`,
[official notebook](https://quantum.cloud.ibm.com/endpoints-docs-learning/raw/learning/en/courses/foundations-of-quantum-error-correction/quantum-code-constructions/css-codes.ipynb).
Cell 0 `bd74fbe8` defines binary linear-code XOR closure and supplies the sixteen
seven-bit Hamming words in display eq002, lines 50–57, original block SHA-256
`777e4abe2e37d55e233a436c00f0a444bf55fac7f428a7aa54e6ebe3fd9400bd`.
The source and full original blocks are preserved externally in
`cleanup-audit/dev11-20261101-a7c4/sources/IBM-062.ipynb` and
`cleanup-audit/math-lane-20261104/dev11-hamming/originals.json`.

```
0000000 1100001 1010010 0110011
0110100 1010101 1100110 0000111
1111000 0011001 0101010 1001011
1001100 0101101 0011110 1111111
```

The native adaptation converts each literal word into an explicit seven-element
binary vector and applies existing `xor`. It preserves order and leading zeroes.
This is an authored adaptation, not literal TeX table execution. Original table
and set-expression attempts are retained in external `pilot.json`; unsupported
arrays/set templates and the decimal interpretation of unbound binary-looking
labels are not certified by the adaptation.

## Reproduction and finite contract

On frozen worker `d72b59ef52188cbf7b1603daecbe03649eec7f1e8e31d712d9e1de2d337cee12`
(commit `3fdf7ebd6141feec7c48005c4e3557229ed794c0`),
`xor([0,0],[1,0])` returns `vector(1,1)` rather than `vector(1,0)`.
Two repeated minimal runs fail identically; reversed operands, one-element
and scalar truth controls pass. The initial harness's one-element vector-shaped
expectation was corrected to the established scalar serialization; both attempts
are retained. Source baseline `02d5ca3f5713385818e80db15b1a58e3b518e569`
already contains the indexing defect, so this is inherited, not a new regression.

Ranked hypotheses were repeated second-operand indexing, incorrect logical truth
conversion, and serialization corruption. Changing only the second vector's
second bit leaves the wrong output unchanged; uniform second vectors pass;
operand reversal passes and scalar logical controls are correct. The vector loop
uses entry zero of its second operand for every position. The fix uses the matching
entry index and changes no truth or length policy.

The dedicated regression checks all 256 ordered pairs of literal codewords.
Independent expectations use bit-by-bit inequality (addition modulo two), check
closure against the literal table, and compare complete canonical vectors and
ordinary Copy/re-entry. It also checks asymmetric vectors in both orders,
unequal lengths, empty vectors, scalar integer XOR, logical conversion in vector
overlap, existing positive-only tail conversion, and symbolic substitution before
and after copying. All identities are exact; no numerical tolerance is used.

Vector overlap retains existing logical-XOR behavior; scalar operands retain
integer bitwise XOR. Longer vector tails retain their existing `>0` conversion,
including negative-entry behavior. This increment does not redefine those rules.
The separate existing `qbitxor` binary-only operation is a passing control.

Before the fix, the dedicated test exits 1 with 232 failures among 345 attempted
checks (copies are attempted only after successful values). Corrected fresh-worker
validation is pending. No green result, actual GUI or saved-session acceptance is
claimed yet. The one-line patch requires an assigned build slot and independent
Standards/Spec review. Coordinator owns build registration and integration.

## Separate composition evidence and remaining scope

The read-only pilot independently passes 792 existing scalar-composition checks
and their copied re-entries: all 256 closures, 16 generator subsets, eight dual
subsets, 384 parity bits for all 128 ambient words, and 128 complete dual-membership
decisions. Integer masks and explicit parity sums are disclosed adaptations;
source words and widths remain in the evidence. Generator and dual sets match the
literal source tables exactly. This success does not repair or excuse vector XOR.
External `composition.json` distinguishes source baseline02d5 and worker3fdf.

IBM-062 and DEV-11 remain partial. General decoding, topology, instruments,
dynamic/media circuits, arbitrary families and whole-source proof coverage remain
open. Released Steane/CNOT and Shor performance evidence is reused, not reopened.
