# IBM-020: finite Bernstein–Vazirani source audit

This increment checks the original four-bit secret `1011` and an explicitly
authored extension to the other 15 four-bit secrets. It does not complete IBM-020,
AUD-01, arbitrary-width families, original notation, SDK execution or application
GUI/session acceptance.

The pinned [original notebook](https://quantum.cloud.ibm.com/endpoints-docs-learning/raw/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-jozsa-algorithm.ipynb)
has SHA-256 `513398ae77d7502e7e8c2f2d4bdc85d4a7b5474d25f88a00eb1a2e8a8777586f`.
`fixtures.json` preserves all 14 display blocks in cell 13 (`89e58116`) with
original text, offsets and hashes. It also preserves the original code references:
cell 8 (`79ab8817`, `compile_circuit`), cell 15 (`11861a7e`, `bv_query("1011")`)
and cell 17 (`7db2ea99`, algorithm invocation). These Python cells are provenance,
not native calculator inputs. The [whole notebook inventory](../aud01-ibm020-audit/README.md)
accounts for the remaining formulas, code and media; this increment adds no new
source occurrences to its 168-formula inventory.

## Observations and separate adaptations

| Cohort | Requests | Fresh worker 577dbb65 observation |
|---|---:|---|
| Original display bodies, only outer delimiters removed and route prefix added | 14 | All rejected; exact diagnostics retained |
| Finite source-formula adaptations | 65 | 33 full values pass; 32 expanded double sums hit the complexity guard |
| Authored explicit-matrix controls | 32 | All full values pass |
| Authored native linear-gate controls | 16 | All 32-by-32 oracle matrices pass |
| Separately disclosed compact double-sum follow-ups | 32 | All full states pass |

The original plan contains 127 requests. The compact follow-ups add 32 requests,
for 159 replay records and **113 successful values plus 113 ordinary canonical
Copy/re-entry checks**. The 14 original rejections and 32 expanded-sum failures
remain failures. A successful compact form never replaces an expanded attempt.
No guard was relaxed and no product code changed.

The 65 source adaptations comprise a shared initial-state expression and four
expressions per secret: phase sum (M028), expanded function/dot double sum (M029),
expanded XOR/dot double sum (M041), and final tensor expression (M066).
They bind n=4, expand finite terms and annotate integer kets with dimension 16.
The compact follow-ups retain nested sums with integer x,y ranges 0..15, convert
them through four-bit `qbits`, and keep the native parity/XOR exponent. These are
explicit domain and dimension adaptations, not original unqualified set binders.
Intermediate derivations and distributivity equations retain separate original
literal/proof obligations; the finite terms do not cover every original display.

Explicit-matrix controls multiply a hand-constructed oracle by the initial state,
then apply the final Hadamard layer. They are separate from source-formula checks.
Native `qlineargate` controls construct the oracle from a 5-by-5 GF(2) map whose
first row is `[1,s3,s2,s1,s0]`, with unchanged data rows. They verify an existing
native operation, not execution of the original Qiskit function.

## Independent exact expectations

Basis index `16*b+x` places the ancilla leftmost and x0 least significant. This
matches the original Qiskit reversal of the displayed secret and its ancilla
wire 4. The visual diagram places the ancilla at the bottom; drawing order is
not algebraic tensor order.

For `f_s(x)=parity(s AND x)`, oracle column `16*b+x` has its unit entry at
`16*(b XOR f_s(x))+x`. Initial amplitudes are `(-1)^b*sqrt(2)/8`; queried
amplitudes are `(-1)^(b+f_s(x))*sqrt(2)/8`. The integer Walsh sum
`sum_x (-1)^(f_s(x)+parity(x AND y))` is 16 at y=s and zero otherwise:
when s XOR y is nonzero, pairing x with a bit-flipped partner cancels terms.
The final state therefore has `+sqrt(2)/2` at row s and `-sqrt(2)/2` at row 16+s.
For the original secret, these rows are **11 and 27**.

Every matrix/state entry, dimension and sign is compared in exact Q(sqrt(2));
there is no numerical tolerance or global-phase alignment. An independent
sequential-CNOT calculation and four exact Hadamard butterfly steps checked all
16 full operators and states. Independent review also checked all 8,192 expanded
double-sum term bindings. These reference checks are separate from native output.

## Replay and retained history

Run `probe.py --source PINNED_NOTEBOOK --worker ACTUAL_WORKER
--definitions MATCHING_DATA --output FRESH_DIRECTORY` on one line. The script uses
only Python's standard library. `--worker-revision` optionally records an
externally verified revision; source, script, fixtures, worker and definitions
are hashed. Original formula/code hashes are checked before execution. Worker
DLL dependencies must already be available on PATH; no installation or build
is performed. Each worker call has a 20-second timeout.

The runner pins return code and full diagnostic for each rejected original and
expanded expression, normalizing CRLF to LF only. Changed diagnostics, newly
accepted originals, wrong values, copy failures or changed worker/data fail the
replay and require review. A zero exit means the documented finite observations
reproduced, not that all expressions passed mathematically.

The worker deliberately omits its JSON cell array above 128 entries. The first
external pilot incorrectly treated the empty array for a 32-by-32 oracle as a
failed value. That attempt remains preserved. The corrected harness compares all
1,024 entries from the full canonical integer matrix and re-enters that actual
canonical output. No displayed/truncated matrix is used as an oracle. The three
historical pilot script versions were recovered and independently hash-verified
against their original recorded hashes. Later runs retain script snapshots.

`baseline-summary.json` links hashes for the original plan, all attempts, reviews
and script recovery. Native evidence used worker revision
`577dbb6572a9442e1d654e4b2264709f603d77ab`, SHA-256
`1d9fbc1e42a1b001d73665fee5f7cbf46df02fdf5eb180f9ebd73345bd1daff9`;
worker and definition hashes remained unchanged. Same-hash notebook execution
and recovered original media have separate evidence and limitations. Saved
sessions, actual GUI Clipboard, arbitrary n, remaining original syntax and whole
lesson completion are not established here. The coordinator owns registration,
central coverage updates, integration and release acceptance.

The packaged verifier reproduced all 159 saved responses and detected injected
unrelated diagnostics and wrong canonical oracle entries. These are verifier
checks using recorded outputs, not another native run. Final packaged native
replay and integration acceptance remain coordinator gates.
