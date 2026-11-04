# IBM-020: explicit binary tensor repetition (M24)

Pinned official source: https://quantum.cloud.ibm.com/endpoints-docs-learning/raw/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-jozsa-algorithm.ipynb

Notebook SHA-256: `513398ae77d7502e7e8c2f2d4bdc85d4a7b5474d25f88a00eb1a2e8a8777586f`.
The original is retained outside the disposable build in
`cleanup-audit/math-lane-20261104/ibm020/source.ipynb`. The manifest records retrieval.
`inventory.json` preserves all 46 formula occurrences in cell 0's first Algorithm
analysis section, exact boundaries and hashes. That section has no code cells or
diagrams. The whole notebook has 20 cells, including eight code cells.

The finite native contract covers only M24, `$\vert 0^{\otimes n} \rangle$`.
`baseline.json` retains three failing literal count substitutions (n=1,2,3)
and three passing natural-spelling controls on released worker 52c37a2a.
Original TeX rejects before evaluation; natural `|0^n>` already evaluates.

Accept an explicit tensor marker in the existing repeated binary ket/bra route.
Supported counts remain integers 0 through 10. For positive n the independent
expectation is a 2^n-dimensional unit vector: index 0 for repeated zero and index
2^n-1 for repeated one. Bras use the established row-vector serialization.
Zero repetition preserves the existing scalar 1 convention. Copy and symbolic
substitution must retain the count constraints. Numerical tolerance: none;
these are exact integer identities and must report non-approximate results.

The dedicated worker test discloses authored adaptations: repeated-one and bra
controls, boundary counts, substitutions, bit flips and adjacent-register order.
These are regression expectations, not additional original IBM inputs. The
notation suite also checks malformed markers and algebraic count spelling.
No bare ellipsis count inference, general symbolic dimension promise, new tensor
algebra, or whole-section/whole-notebook completion is claimed.

Notebook lane reconciliation (2026-11-04): the same pinned notebook's eight
original code cells have executed, with original cell text/type/order unchanged;
seed 0 was a disclosed runtime adaptation. Its clean offline replay and independent
oracle/operator/Walsh/count checks are separate SDK evidence, retained in
`cleanup-audit/notebook-lane-20261104/runtime-tests/ibm020-clean-replay/`.
That success does not certify these native Markdown formulas. Historical inventory
'not executed' dispositions describe the original native analysis checkpoint.

Validation and independent review are pending for this increment. Actual GUI
entry, Clipboard, and saved-session checks require an available desktop and a
coordinator reservation; no GUI acceptance is currently claimed.
