# IBM-020 remainder inventory and mathematical review

2026-11-04. Source-only work: no worker/build/GUI/SDK execution or shared edits. No new product failure is claimed. Existing reports and the first-analysis inventory remain unchanged.

`remainder-inventory.json` covers the **complement** of cell0 [2760,7763): both the preceding problem/circuit context and everything after that first Algorithm analysis. Including the prelude prevents its diagram and problem definition from becoming orphaned. It contains **122 math occurrences (15 display blocks,107 inline),8 original code cells,1 source image reference,3 stored-output image references and2 textual Figure containers**. Those Figure containers define problems; they are not circuit images. Original snippets, per-item hashes and source/output offsets are retained. Repeated symbols are not silently deduplicated; nested dollar text inside a display stays within that display. No first-analysis formula is counted again.

Notebook SHA-256 is `513398ae77d7502e7e8c2f2d4bdc85d4a7b5474d25f88a00eb1a2e8a8777586f`. Source is the pinned `source.ipynb` and [official lesson](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-jozsa-algorithm). Inventory SHA-256 at creation: `aecc1735ecfc172999f5b000164842f5392e7dc5f24ef92ad10983d1f3dea814`.

The code and image-reference originals are preserved verbatim. A reference's SHA is the hash of the reference text, **not the image bytes**. The external SVG and stored AVIF files were not fetched here. The notebook-lane handoff separately records three inspected newly generated drawings and the external source SVG retrieval failure; those are different artifacts.

## Region classification and next acceptance groups

| Region | Source location | Classification/next work |
|---|---|---|
| Introductory problem and circuit | cell0 `17463a96`, [0,2760) | One displayed 2-bit nonpromise truth table; textual promise/input/output figure; external circuit SVG. The table is an executable finite control after declaring f, not native declaration syntax by itself. |
| Deutsch-Jozsa Classical difficulty | same cell, [7763,9813) | Query lower bound and sampling-probability proof review; scalar numerical illustrations are optional adaptations. |
| Deutsch-Jozsa implementation | cells1–12 | Six original code cells (2,4,6,8,10,12), explanatory Markdown and two stored output image references; SDK/media dependency. |
| Bernstein-Vazirani problem and analysis | cell13 `89e58116`, [0,7153) | Fourteen displayed mathematical statements/derivations plus context; binary parity algebra, phase/Walsh calculation and classical query proof. |
| Bernstein-Vazirani implementation | cells14–17 | Two original code cells (15,17), explanatory Markdown and one stored output image reference; SDK/media dependency. |
| Nomenclature remark | cell18 `86c52e37` | Historical/complexity-theoretic context, including recursive Fourier sampling; not independently certified by elementary proof review here. |
| Copyright | cell19 | Attribution context. |

All display blocks are tagged as potential finite native targets **after explicit bindings**, while proof obligations and literal parsing remain distinct. Inline formulas are classified as proof/context, even when their scalar tokens could be evaluated separately. Each item has a unique ID and original offset in the JSON.

## Elementary proof review: Deutsch-Jozsa query bounds

Let N=2^n with n positive, oracle outputs one bit, and cost count black-box function queries. For an exact deterministic algorithm, an adversary answers zero on each distinct queried input. After at most N/2 such inputs, both the all-zero function and a balanced completion remain possible. Thus at least N/2+1 queries are required in the worst case. Querying N/2+1 distinct inputs is sufficient: seeing both outputs proves balanced; all equal excludes balanced. This proves the stated exact deterministic bound without running a calculator. Repeated queries provide no new information.

**Sampling-model qualification:** the stated error probability 2^(1-k) is exact for k independent uniform draws **with replacement** from a balanced truth table: all-zero and all-one events each have probability 2^(-k). The prose also says “different strings,” which suggests sampling without replacement. For uniformly sampled distinct inputs the exact error is instead

```text
2 * binomial(N/2,k) / binomial(N,k), for 1<=k<=N/2;
0 for N/2<k<=N.
```

The distinct-input expression is at most 2^(1-k), since each next matching-output conditional probability is at most1/2. Therefore the source's reliability conclusion is valid under either interpretation, but equality to2^(1-k) requires the independent-with-replacement interpretation. Preserve this source ambiguity; it is **not a native product defect**. At k=11 the latter error is1/1024, success1023/1024=0.9990234375, strictly above99.9%. For n<4,11distinct queries may be impossible, further reinforcing the need to specify the sampling model rather than silently assume distinctness.

The statement of an advantage must retain the model: exact quantum single-query classification versus exact deterministic classical worst case, or separately bounded-error randomized classical performance. Do not conflate success probabilities, distinct samples and query counts.

## Elementary proof review: Bernstein-Vazirani

The fourteen display blocks in cell13 have these acceptance groups:

| Inventory IDs | Mathematical obligation |
|---|---|
| R13-0-M004,M005 | Binary dot product is parity of coordinate products, not ordinary real inner product; equivalent odd/even definition. |
| M022 | H-layer coefficient identity. Reuse G2's independently derived Walsh matrix as a reference, but retain this occurrence's literal input. |
| M027,M028,M029 | Preparation, phase-kickback and final H layer. Reuse the mathematical formulas of G3 with distinct provenance; do not recount a prior actual execution as a fresh one. |
| M033,M037 | Substitute the promise f(x)=s·x; replacing integer sum by XOR is valid inside (-1)^exponent because only parity matters. |
| M038,M039,M040 | Distributivity of binary dot product over XOR, scalar-bit identity and expanded coordinate proof. |
| M041,M043,M066 | Character sum cancellation, final full state and unique secret output. |

All abbreviated M IDs in this table have prefix R13-0-. Full originals and hashes remain in the JSON.

Independent derivation: work over GF(2). For bits a,b,c, if c=0 both sides of `(ac) XOR (bc) = (a XOR b)c` vanish; if c=1 both sides equal a XOR b. Summing coordinate identities modulo2 proves `(s·x) XOR (y·x)=(s XOR y)·x`. The binary dot product is symmetric. Integer exponents differing by an even number give the same sign, so replacing the sum of two bit-valued dot products with XOR is valid here. It is not a general arithmetic-replacement rule outside the parity sign.

For any fixed n-bit z, define `K(z)=2^(-n)*sum_x (-1)^(z·x)`. If z=0, every term is1 and K=1. If z is nonzero, choose an index j with z_j=1. Pair each x with x XOR e_j; this fixed-point-free pairing reverses the sign, so the sum is exactly0. Therefore the final data amplitude at y is K(s XOR y), equal to1 at y=s and0 elsewhere. The full state is minus ancilla tensor |s>: at rows s and2^n+s the amplitudes are respectively+1/sqrt(2) and-1/sqrt(2), all others zero. No global-phase fitting or probability-only comparison is needed.

This is an elementary general proof under the source's oracle/bit-order assumptions, **not evidence that the native system proves or parses the parameterized formulas**. A finite native cohort can exhaust all s,x,y for n=2 or3, compare every intermediate coefficient and final full vector, and check all eight scalar-bit triples for M039. Keep original unqualified bound-ket attempts and disclosed dimension annotations separate, following G1's observed distinction. Do not silently interpret source `x·y` as real scalar multiplication.

For exact classical identification, a deterministic decision tree of depth k has at most2^k output transcripts but2^n possible secrets. Correctly identifying every secret requires k>=n. Querying each unit vector e_j gives f(e_j)=s_j, proving sufficiency. A rank formulation gives the same result: k linear equations leave at least2^(n-k) candidate secrets. The broad prose phrase “any classical query algorithm” needs its exact-success/worst-case qualification; randomized algorithms with a permitted chance of failure need a stated success criterion, and expected variable stopping time is another model. No universal randomized bound is inferred without those definitions.

## Code and media dependencies, reconciled separately

Eight code cells and exact source hashes are in the JSON; none was executed by this task. Same-hash notebook-lane evidence already records all eight original cells executed with unchanged source text/type/order, a disclosed authored seed0 preamble and separate independent witness, then semantically equal offline and isolated-kernel replay. Relevant records remain in `cleanup-audit/notebook-lane-20261104/HANDOFF.md`, `ibm020-probe/source-and-witness-verification.json`, `runtime-tests/replay-comparison.json` and `runtime-tests/isolated-comparison.json`.

Dependencies include Qiskit QuantumCircuit, AerSimulator, NumPy's random choice, matplotlib drawing support and notebook display. The seed changes random experiment selection, not source code. The original single-shot classifications are separate from the authored larger-shot and full-operator/Walsh witnesses. Five BV secrets checked by that lane are finite execution evidence, not all secrets at every width or native literal acceptance.

A source-code observation worth retaining: `dj_query` flips control bits wherever the selected binary state has1, surrounds an all-ones multi-control gate with those flips, then restores them. The triggered input is therefore the bitwise complement of the selected integer within n bits, rather than that integer itself. Complementing maps the selected half-set bijectively to another half-set, so the promise and uniform balanced-function distribution are preserved. This is not a product bug, and native oracle reconstruction must follow the actual gates rather than equate `on_states` with the final truth-table one set. A separately random output-bit X can complement the function again.

For `bv_query`, reversing the displayed secret before choosing Qiskit controls maps source q0 to its least-significant bit, consistent with displayed s. Full-state native adaptations must explicitly map to their own wire convention. Generated diagrams and native matrix translations do not certify the external original SVG or stored AVIF byte content.

No whole-source certification follows from this inventory, the elementary proof checks, G1/M24, planned G2–G4, or finite SDK runs. Remaining literal syntax, source diagrams, historical claims and wider mathematical/native acceptance stay explicit. Any new development task still requires a concrete reproduced native failure with independent expectations.
