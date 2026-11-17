# QB-015: finite mathematical audit and source discrepancies

This audits mathematical claims in the [pinned AutoQASM Deutsch–Jozsa notebook](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-QIR/autoqasm_deutsch_jozsa.ipynb).
Its SHA-256 is `b7b1ed883412dc54375ae4fbbae533dde6a14782077d12d0a8d50865c34dddfd`.
The original 23-cell notebook is preserved outside the worktree. No AutoQASM
source cell, compiler or provider job is executed by this audit. QB-015 remains
open; these results must not be substituted for its cloud workflow.

## Exact finite results

`probe.py` enumerates every promised constant or balanced truth table for input
widths 1–4: respectively 4, 8, 72 and 12,872 tables, totaling 12,956. An integer
Walsh transform is checked against a separately computed Boolean character sum.
Every transformed state has the expected normalization, and its zero-result
probability is exactly one for constant tables and zero for balanced tables.
Every individual truth table and coefficient vector is retained.

For balanced tables the audit also counts when a fixed sequence of distinct
queries first observes a differing output. The largest count is `2^(n-1)+1`.
This supports the deterministic worst-case argument in cell 2 within the tested
widths. More generally, after at most half the domain has returned the same value,
both a constant completion and a balanced completion remain possible; one further
distinct query distinguishes them in the worst case.

The published `c5a456cde595b3e1211cfc51a233dea511322a56` worker separately passed
40 authored scalar cases in exact evaluation, copy/re-entry and approximate modes
(120 requests). Exact checks use rational `copy_text`, not rounded display text.
Expected values come from Python rational arithmetic; approximate residuals must
be below `1e-12`. The report binds the actual worker binary hash. These are scalar
instantiations and derived counterexamples, not unchanged source TeX or native
execution of the notebook's circuits.

## Findings that must remain visible

| ID / source cell | Finding and disposition |
|---|---|
| QB015-MATH-01 / 4 | The displayed post-oracle denominator is `sqrt(2^n+1)`. There are `2*2^n` orthogonal terms, so its squared norm is `2*2^n/(2^n+1)`, giving `32/17` at n=4. The separately labeled correction `sqrt(2^(n+1))` gives norm one. This is a source normalization error, not a calculator defect; never silently substitute the correction as literal acceptance. |
| QB015-MATH-02 / 3 | The probability discussion needs a sampling model. For uniform distinct queries of a balanced function, exhausting the deterministic budget has probability `2/binomial(N,N/2)`. At N=16 this is `1/6435`, whereas the source's expression gives `1/8`. |
| QB015-MATH-03 / 3 | For independent uniform draws with replacement, `1-2^(1-k)` is the probability of observing both outputs when the function is balanced. It is not a posterior probability that the function is constant without a prior. For distinct draws, the probability all k outputs agree is instead `2*binomial(N/2,k)/binomial(N,k)` when k≤N/2, and zero afterward. At N=16,k=2 these agreement probabilities are respectively `1/2` and `7/15`. Preserve the distinction rather than treating “confidence” as an executable equality. |
| QB015-EXEC-01 / 11,16,18,21 | Both definitions explicitly measure four data qubits, while the outcome prose uses a five-bit ket. An authored scalar interpretation of the gate order ends at full little-endian basis index 16 for the constant case and 24 for the balanced case: ancilla 1, data index 0 or 8. Actual generated outputs and provider result-string conventions remain unverified. |

The scalar circuit controls include both rounds of five Hadamards, including
the ancilla, as written in cells 11/18. The mathematical description applies its
last Hadamards only to the data register. That difference changes the ancilla
state but not the data distribution in these examples. The state formula after
the final data transform can be read as the first-register state with its
separable ancilla omitted; it is not a full five-qubit vector.

These source discrepancies do not justify implementing incorrect mathematics.
They remain associated with AUD-01/AUD-04. DEV-13/DEV-14 still track the missing
AutoQASM/QIR execution route, and DEV-15 tracks external-provider verification.

## Cell coverage and outstanding execution

| Cells | Coverage |
|---|---|
| 0–1 | Scope and constant/balanced promise read; finite promised tables enumerated. |
| 2–5 | Finite mathematical identities, deterministic queries and normalization/probability interpretation audited above. General symbolic source input, original-notation parsing and GUI behavior are not established here. |
| 6,9,12,17 | Implementation/provider introductions and the threshold oracle read; no provider observation inferred. |
| 7–8,10–11,18 | Installation, imports and algorithm definitions remain unexecuted. The two scalar gate interpretations are authored controls. |
| 13–15,19–20 | Authentication, device discovery, job submissions/results and histograms remain unexecuted. No local simulator is represented as the requested provider. |
| 16,21 | Outcome prose requires reconciliation with generated measurement/result ordering. |
| 22 | License notice read; non-executable. |

Run the probe with explicit `--source`, `--worker` and a new `--output` directory.
Evidence is at `cleanup-audit/learning-coverage-20261117/qb015-source-audit/` in the
main repository. `run02` is the final audit, with per-case source-cell attribution;
`run01` is retained. The index binds results, all truth tables, source and probe.
Independent review, hosted CI and whole-notebook acceptance remain open. The
calculator used is already published; this audit itself is not a new release.
