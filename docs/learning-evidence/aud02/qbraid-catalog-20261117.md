# qBraid demo catalog reconciliation — 2026-11-17

This is static discovery for DISC-03/AUD-02. No notebook was executed, no provider was contacted, and no whole-source acceptance box is closed.

## Revisions and method

The checklist's original 35 notebooks are pinned at `86787e1ba372facc224f925189755e69c479828b`. The current `main` snapshot is `4deeced918b79c10a4f7585fafbc65d4250dc6e7`. The GitHub recursive tree response was not truncated. Every `.ipynb` blob path was enumerated, and all 38 notebooks were acquired from immutable raw URLs and hashed. The [machine-readable inventory](qbraid-catalog-20261117.json) records every current URL, notebook SHA-256, code-cell index/hash, original hash where applicable, and stable checklist ID.

There are 33 byte-identical notebooks, two modified notebooks, three additions and no removals. Existing IDs and their original pinned links remain unchanged; additions receive QB-036–038. Original notebook bytes and current copies remain outside the checkout under `cleanup-audit/dev13-aud02-20261101-b6e2/sources` and `cleanup-audit/learning-coverage-20261117/aud02-current-qbraid-sources` respectively.

QB-025 changes code cell 5. QB-026 changes code cells 2, 4, 6, 8, 9, 11 and 13. Each changed code cell parses to the same Python AST with location attributes excluded: these source-text changes are formatting/comment spacing. This comparison establishes source-structure equality, not provider compatibility or unchanged execution results. Byte hashes remain distinct.

## Newly discovered source requirements

All cell indices are zero-based. All three notebooks use an unpinned `%pip install 'qbraid[qiskit,visualization]'` in cell 1 and `QbraidProvider` in cell 3. Their provider setup expects a qBraid API key; provider access and network availability are unverified. Provider submissions, metadata requests and billing behavior were not exercised. Source pricing statements are historical source content, not a verified current service quote. Local circuit extraction would be an adaptation.

| ID | Source and cells | Required acceptance evidence |
| --- | --- | --- |
| QB-036 | GPU state-vector quickstart: GHZ construction at 7; submitted results at 8/12/14/16; rotation batch at 19 and plot at 20. | Preserve wire/bit order, check GHZ support and sampling uncertainty, verify precision/seed metadata and same-release reproducibility, and retain ordered batch results. Validate the wide 30-qubit case through its intended route; a small local Bell proof cannot replace it. |
| QB-037 | GPU tensor-network quickstart: 100-qubit GHZ at 5; result metadata at 7; mirror circuit at 9 and exact-mode comparison at 11; seeded sampling at 13 and widths 50/100/200/400 batch at 15. | Separate approximate MPS from exact contraction; retain truncation settings and quantify mirror-circuit all-zero probability. Check all GHZ bits agree and result ordering at every batch width. No wide-state capability is inferred for QuantumStudio. |
| QB-038 | QPerfect MIMIQ quickstart: SV/MPS metadata at 3/4; local GHZ construction at 8; SV submission at 9; 100-qubit MPS at 13; fidelity metadata at 15; tuned MPS at 17; seeded runs at 19; rotation batch at 22 and plots at 23/25. | Record engine, approximation settings and optional fidelity bound. Verify GHZ support, bit order, batch order and RY probabilities against sin²(theta/2), with sampling uncertainty. The source notes correlated samples across batch circuits; do not assume independent trials across circuits. |

The original source-specific audit contract still applies: setup, every relevant code cell, output interpretation, notebook rendering, explicit adaptations, expected errors, reviewed implementation and released application route all need evidence. These newly discovered examples have none of that execution evidence yet.

## Remaining discovery

This reconciliation covers `.ipynb` files in one complete repository tree. AUD-02 still requires IBM catalogs and overview/exam/video/download content, linked examples, SDK/PyQASM/QIR/Algorithms/runtime references, and authorized qBook chapter discovery. Non-notebook assets and links are not made complete by the notebook path inventory.

## Independent Git verification

A fresh Git fetch resolved the public repository HEAD to the same revision. The pinned and current root tree IDs are respectively `8894b2d89ff98d3dd2a34584b943b86acd17ed61` and `bc15f35492cf56e1fc9aff83ffa7ac1ab24be6dc`. Recursive Git tree listings yielded 35 and 38 notebook paths. For each of the 73 entries, hashing the retained file bytes with the Git blob header reproduced the tree's object ID, and SHA-256 matched the inventory. All current code-cell indices and text hashes matched the notebooks, and all 38 IDs were unique. Comparing the two path-to-blob maps independently reproduced every change classification. This closes the dated DISC-03 source comparison. Execution and application release evidence are tracked on the individual source rows.
