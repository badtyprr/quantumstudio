# DEV-11: finite classical Hamming decoder composition

Existing native binary operations decode the concrete IBM-062 seven-bit Hamming
example for all128 transmissions formed from its16 literal codewords and either
no error or one flipped bit. This is a finite classical decoder composition,
not a new decoder API, generic CSS recovery, an instrument or a topology solver.

[Original CSS notebook](https://quantum.cloud.ibm.com/endpoints-docs-learning/raw/learning/en/courses/foundations-of-quantum-error-correction/quantum-code-constructions/css-codes.ipynb)
SHA-256: `e8b1deec5f914fc07cd75fcf26051712116a936dc50d38ed2149032b8487b4f5`.
Cell0 `bd74fbe8` contains the literal words (eq002, lines50–57), parity rows
(eq006, lines121–127) and single-error correction discussion (lines274–305).
The probe verifies the complete notebook hash and preserves the full selected
original blocks, offsets, hashes and correction section in its output.

Original word order is retained:

```
0000000 1100001 1010010 0110011
0110100 1010101 1100110 0000111
1111000 0011001 0101010 1001011
1001100 0101101 0011110 1111111
```

Parity rows are1111000,1100110,1010101. Printed leftmost bit is position1.
Columns at positions1 through7 have syndromes111,110,101,100,011,010,001.
No error has syndrome000. The independent oracle computes binary parity sums
and searches this literal column table; it does not call product functions.

## Native computation and expectations

Each received word is an authored explicit seven-element binary vector. Native
`qbitdot` computes its three syndrome bits. The product converts that syndrome
with `qbitvalue`, selects position0 for syndrome0 and otherwise8 minus the
syndrome integer, and selects correction mask0 or2^(syndrome−1). Native `qbits`
restores width7, and `qbitxor` applies the correction. This arithmetic selection
is specific to the source's descending parity-column order.

The host records native intermediate values but never injects its oracle-chosen
position or mask. The checks compare complete syndromes, positions, masks and
corrected words against independently derived expectations. All successful
results undergo ordinary canonical Copy/re-entry and must remain exact.
No numerical tolerance or approximate evaluation is used.

All128 received words are distinct, exhausting the seven-bit ambient space.
For each transmitted codeword, the no-error and seven single-bit-error cases
recover that exact original word. This does not establish correctness for an
unknown number of errors: every received word is close to some codeword, which
need not be the transmitted one.

An explicit limit check transmits0000000, flips the first two bits to1100000,
and observes decoded1100001. The decoder chooses the syndrome's single-bit
correction at position7, thereby miscorrecting this two-bit error. The test
preserves that expected failure outside the single-error contract; it is not
reported as a native defect or as successful two-bit recovery.

## Reproduction and evidence

Run `hamming-decoder-probe.py` with `--source` pointing to the exact notebook,
`--worker` to the real worker and `--output` to a fresh evidence directory.
`--definitions` overrides the worker-adjacent data directory. Optional
`--worker-revision` records an independently established source revision; the
actual worker hash is always recorded. The script uses only Python's standard
library, no translator, build or SDK environment.

Output preserves source, script, worker and definition hashes, raw requests,
stdout/stderr, every expected value and actual copied re-entry. Existing output
is not overwritten. The initial reusable run passes513 checks and513 copies
on frozen worker3fdf7ebd, SHA-256
`d72b59ef52188cbf7b1603daecbe03649eec7f1e8e31d712d9e1de2d337cee12`,
distinct from inspected source baseline02d5ca3f. External evidence is retained in
`cleanup-audit/math-lane-20261104/dev11-decoder/reusable-final/`.

All native function spellings, finite substitutions and bit-vector representations
are disclosed adaptations. Literal TeX tables and set templates were attempted
separately in `cleanup-audit/math-lane-20261104/dev11-hamming/pilot.json`;
this successful composition does not erase their unsupported dispositions.
`qbitxor` already works on this worker, independently of the inherited generic
vector `xor` indexing defect and its separately reviewed fix.

Independent final reviews, combined-worker replay and actual GUI/session
acceptance remain pending. IBM-062 and DEV-11 remain partial: arbitrary CSS
families, coherent quantum recovery, all error channels, instruments, toric
matching/homology, other topologies, dynamic/media circuits and whole lessons
are not certified. The coordinator owns registration, central coverage updates,
integration and publication.
