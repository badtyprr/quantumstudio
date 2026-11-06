# IBM024 source inventory and finite reference proposals

Assigned base: `45d3155`. This is external source analysis only, not native validation, source acceptance, or a product gap report. No calculator, SDK, original code, or GUI was executed. No media was fetched. Independent Standards and Spec reviews remain to be requested by the integration owner.

## Provenance and inventory

The original [notebook](source.ipynb) was copied byte-for-byte from the notebook lane's pinned source body. SHA256: `554cc9694595ec167fb501776310e6bfdfe0a87a5c638d2c79ba8a4fdf09bbcd`; 38,061 bytes; Git blob `64cad0ea97326a7b997b171ae529a15a46322312`. Both hashes were checked against the existing manifest. Its immutable [official source](https://raw.githubusercontent.com/Qiskit/documentation/a500b17f8b1f156a6bba42ab11f90f3104cad6d4/learning/courses/fundamentals-of-quantum-algorithms/quantum-algorithmic-foundations/measuring-computational-cost.ipynb) is at revision `a500b17f8b1f156a6bba42ab11f90f3104cad6d4`. Historical baseline-body equivalence is not claimed by that manifest.

[manifest.json](manifest.json) retains the complete upstream entry and upstream manifest hash. [inventory.json](inventory.json) retains the complete cell source and every matched formula, image reference, textual Figure, heading and table, with original strings, offsets and UTF-8 SHA256 hashes. All are marked unverified. Offsets are zero-based half-open Unicode character offsets within concatenated original cell source, without newline normalization.

There is one Markdown cell, ID `5c5b90e6`, 33,535 characters, source SHA256 `0ec8d1aa74bb17d98020e44ffa9eee6e8523250fb30ae3a5a252904fd4a5806c`. Counts: **170 math occurrences (8 display, 162 inline), zero code cells, six SVG references, four textual Figures, 17 headings and two tables**. Inline mathematical tokens include contextual variables; this count is not 170 executable requirements. No original notebook runtime dependency exists.

## Original encoding contracts and proposed finite checks

The binary table starts at 1847. Original encodings of integers 0 through 8 are `0,1,10,11,100,101,110,111,1000`, with lengths `1,1,2,2,3,3,3,3,4`. Leading-zero permission begins at 2189. Authored checks could compare `1`, `01`, `0001`: equal numeric value, unequal string lengths.

The alternative-encoding table starts at 2818 and the empty-string explanation at 3078. Its unary representation of integer N, for the displayed N=0..8, contains N zero symbols. Thus unary `0` represents one; binary `0` represents zero; epsilon is the empty string, with length zero. The displayed lexicographic encodings are `epsilon,0,1,00,01,10,11,000,001`. This is length-first order, not unrestricted dictionary order. An inferred, disclosed extension is to remove the leading 1 from the binary representation of N+1; the table alone is not an explicit general definition.

The display at [4004,4112) gives minimal binary length: lg(0)=1 and lg(N)=1+floor(log2(N)) for N>=1. This is the canonical encoding length, not the length of every padded representation. Proposed exact boundary checks are 0 and 2^j-1, 2^j, 2^j+1 for a declared finite set of positive j. An independent oracle uses integer power-of-two inequalities, avoiding floating-point logarithms. Negative integers require a separately chosen sign encoding; the source mentions a sign bit without defining a complete scheme.

### Existing released zero-width evidence

These source leads do not establish a new missing empty-string or zero-width operation. [DEV-10 evidence at the assigned base](https://github.com/badtyprr/quantumstudio/blob/45d3155/docs/learning-evidence/DEV-10.md) records the released typed-set correction for the zero-width binary alphabet and singleton ranges, including the authored empty-word cardinality-one expectation, Copy/re-entry and saved-session checks. Its final release is [checkpoint-7d8b5c15](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-7d8b5c15). Distinguish the empty word, the singleton set containing that word, the empty set, and numeric zero. Reuse that finite evidence before considering any new reproduction; it does not certify IBM024 as a whole.

## Addition and width

The addition Figure is [18147,18233), the operand bound [18538,18566), and the output-width requirement begins at 18568. Nonnegative operands use n bits, allowing leading zeros; output uses n+1 bits even for a small result. Authored four-bit fixtures, motivated by the source diagram, are:

| Inputs | Five-bit result |
|---|---|
| 0000 + 0000 | 00000 |
| 0001 + 0010 | 00011 |
| 0111 + 0001 | 01000 |
| 1111 + 1111 | 11110 |

An exhaustive 256-pair four-bit check would be an authored finite extension, not a proof about all widths. The half-adder construction assumes n>=1; n=0 substitutions into its gate-count polynomial are outside that construction.

The gate-count identity [20629,20660) is 21(n-1)+10=21n-11. Alternate gate conventions give 9n-5 and 5n-3; at n=4 these are 73,31,17. Arithmetic evaluation verifies the expressions only, not the diagram's connectivity, correct operation, or gate count. Half/full-adder truth tables and an independently transcribed netlist would be separate diagram-backed checks.

## Original arithmetic boundaries

Division Figure [24317,24468) requires M!=0, N=qM+r and 0<=r<abs(M). This is nonnegative Euclidean remainder for both divisor signs. Proposed authored exact fixtures are (N,M;q,r): (7,3;2,1), (7,-3;-2,1), (-7,3;-3,2), (-7,-3;3,2), and (0,3;0,0). Each is justified by substitution and the remainder bounds. Truncation toward zero or divisor-signed remainder must not silently replace this contract.

Modular-exponentiation Figure [25364,25527) permits integer N, K>=0 and M>=1; the remainder explanation begins at 25529. Proposed exact fixtures include (-2)^3 mod5=2, 2^0 mod5=1, and every defined power modulo1 giving zero. The written domain includes N=K=0 but does not explicitly settle 0^0: record the convention before testing that boundary. Negative exponents and zero modulus are outside this contract. Small repeated multiplication plus Euclidean division is an independent oracle for these finite cases; no numerical tolerance applies to exact integer identities.

The multiplication Figure [23228,23319) states a general integer product, while subsequent bit-complexity discussion needs a specified representation for signs. No source claim here authorizes treating an n-bit unsigned input as signed two's complement.

## Remaining circuit, proof and media obligations

The six SVG references, all uninspected, are:

| Offset | Dependency |
|---|---|
| [674,834) | standard-computation.svg |
| [10778,10921) | deferred-measurement.svg |
| [12303,12446) | Boolean-circuit-XOR.svg |
| [19266,19389) | half-adder.svg |
| [20006,20129) | full-adder.svg |
| [20439,20600) | addition-circuit.svg |

The four Figures are textual problem contracts, not images. Their strings and every media URL are retained separately in the inventory.

Display equations at [17781,17819), [21806,21833), [22401,22432), [27418,27467), and [28951,28989) concern circuit-size definitions, asymptotic inequalities, or complexity classes. A finite numerical substitution cannot establish an asymptotic statement. The Big-O formulation is used for nonnegative computational costs; extending it to arbitrary signed functions requires additional care. The number-field-sieve estimate is explicitly described as believed rather than rigorously proven. Hardware timing and statements about presently known algorithms are contextual, not native arithmetic acceptance criteria.

Universal gates [6832,10175), deferred measurement [10175,11806), size/depth [11806,15932), and circuit families [16155,17961) retain separate proof/model obligations. The deferred-measurement discussion assumes fresh ancillary storage and accounts for overwritten classical bits; matching one output distribution would not prove arbitrary adaptive-circuit equivalence. Universality means approximation to arbitrary accuracy, not an efficient gate bound or exact synthesis of arbitrary matrices.

The final section [31743,33535) explicitly notes that polynomial circuit size alone does not ensure an efficiently obtainable family: uniformity matters. Width-four arithmetic examples or even exhaustive finite truth tables cannot certify uniformity or an infinite family. Source-only inventory completion therefore leaves native routes, original notation handling, diagrams, applicable Copy/re-entry/session/GUI checks, independent reviews and whole-source audit open. No defect has been reproduced in this work.

## Approved finite reference appendix

[reference.py](reference.py) uses only Python's standard library and checks the pinned notebook hash before producing [reference-results.json](reference-results.json). The successful run retains every case and exact result: nine original encoding-table rows; 256 authored four-bit ripple additions compared with integer addition (always five output bits); 97 authored binary-length boundary occurrences (zero plus j=1..32 and offsets -1,0,1); 528 authored signed divisions for N=-16..16 and nonzero M=-8..8; and 1,368 authored modular-power cases for N=-8..8, K=0..8, M=1..9, omitting all nine ambiguous 0^0 cases.

The independent checks use bitwise carry propagation versus integer addition, repeated-division binary encoding versus exact power-of-two inequalities, Euclidean divmod versus exhaustive bounded quotient search, and repeated integer multiplication versus three-argument modular pow. The finite division domain guarantees quotient magnitude at most 16; the search covers -32..32 and requires exactly one valid pair. Binary-length occurrences deliberately retain overlapping input values at small boundaries. All arithmetic is exact, with no tolerance. Empty strings remain empty JSON strings, distinct from numeric zero. These checks establish reference expectations only: they execute no calculator and validate no media, circuit wiring, gate count, infinite family, asymptotic bound or native feature.
