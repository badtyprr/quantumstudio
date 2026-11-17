# QB-002: original PyQASM transformations and source-count discrepancy

All 32 cells of the [pinned notebook](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/PyQASM-Examples/qasm_processing.ipynb)
are preserved, and its 21 code cells execute unchanged under PyQASM 1.3.0.
Source SHA-256: `4a82502bb158e79847b569785edbd470ce9d03b80773558ebb6d4996b1eba546`.
The route reuses `autoqasm-win-py312` for its locked PyQASM/notebook dependencies;
this source does not call AutoQASM. QB-002 remains open for broader acceptance,
GUI, CI, packaging and release.

## Source finding: QB002-SOURCE-01

Cells 12 and 16 say that qubit 6 is idle and that removing idle qubits leaves six
qubits. The original code applies `rx(0.5)` to `q[3:6]`, which includes 3, 4, 5
and 6 under the [OpenQASM 3.0 range definition](https://openqasm.com/versions/3.0/language/types.html#register-concatenation-and-slicing).
Only qubits 7–9 are idle, so the actual remaining width is **seven**. This is a
source-prose discrepancy, not an implementation defect to reproduce. The original
source remains unchanged; AUD-01 retains the finding rather than silently
changing the program or treating the six-qubit claim as acceptance.

## Original-cell coverage

| Cells | Actual evidence |
|---|---|
| 0 | Introduction read. The original linked SDK documentation URL could not be opened with the web tool; broader API-reference acceptance remains pending. |
| 1–3 | Original offline pip setup, imports and version expression executed; displayed version `1.3.0`. |
| 4–7 | Original QASM string retained exactly, loaded and validated. |
| 8–11 | Ten qubits, ten classical bits; original unrolling/list output and logical depth 5 verified. |
| 12–16 | Idle-qubit removal produces seven qubits and ten classical bits. Printed transformed program and counts agree with that result, not the prose. |
| 17–19 | Original measurement/barrier queries both return true; removal introduction read. |
| 20–23 | Barriers removed. Measurements remain in `module` and are absent from distinct `new_module`; both original printed lists verified. |
| 24–27 | Original module reverses wires by `q → 6−q`; classical measurement destinations stay unchanged. The measurement-free copy remains byte-identical. |
| 28–30 | Final counts `(7,10)` and logical depth 4 verified. |
| 31 | License notice read; non-executable. |

Four authored post-cell observations serialize states after cells 10, 13, 20 and
25 without replacing SDK methods. A finite witness checks every declaration,
gate target/angle, barrier and measurement destination at those points. A host
audit separately checks every original source cell, all scalar/list outputs,
and the original embedded QASM string. An authored critical-path model counts
each operation, including the barrier, as one layer and reproduces depths 5 and
4; this is not a physical timing or hardware-decomposition claim.

## Independent state and native output checks

The unitary-prefix witness uses seven logical wires, with idle original wires
7–9 omitted only from this authored mathematical control. Starting from zero,
the analytic state has uniform data bits 0 and 1, bit 2 equal to their AND, and
independent `Rx(0.5)` rotations on wires 3–6. Its amplitudes are products of
`1/2`, `cos(0.25)` and `−i sin(0.25)`. Direct gate evolution matches this formula
within `1e-12` before and after the transformations, undoing the final wire
permutation for comparison. This is not a native full-state observation.

Ten native checks cover original QASM, unrolled QASM, compacted QASM, barrier-free
QASM and reversed QASM in exact and sampled modes, through compilation and
saved-model reload. Their 32 possible measured outcomes follow the analytic
AND relation and three independent measured rotation probabilities. The native
worker's zero-initialization convention leaves unused classical bits zero.

Two additional **authored diagnostic** checks append seven measurements to the
captured measurement-free copy. These have 64 possible outcomes and expose the
rotation on wire 6, which is unmeasured in the original program. The added
measurements are saved separately and never represented as original input.

All 12 checks pass on published worker
`c5a456cde595b3e1211cfc51a233dea511322a56`. Exact-mode expressions are retained and
numerically evaluated against independent analytic probabilities with `1e-10`
tolerance. Sampled checks use 10,000 shots, reject impossible outcomes, require
per-outcome deviations within six binomial standard deviations plus one shot,
and total variation below 0.04. This is finite numerical agreement, not symbolic
proof of every probability expression. Six mutation/state tests also pass.

## Replay and remaining scope

Run02 repeats the complete notebook with the same seven QASM artifact byte strings
and checkpoint data as run01, whose artifacts supplied the native checks. Setup
metadata/RECORD comparisons pass, and 89 distributions satisfy 145 active
requirements. Before/after snapshots match for 29,291 files totaling 741,388,468
bytes across the SDK environment, base interpreter and notebook runtime. No
snapshot differences were found; transient changes and the entire machine were
not monitored. Owned-kernel cleanup reports zero remaining active processes.

The adjacent index binds evidence under
`cleanup-audit/learning-coverage-20261117/qb002-notebook/` in the main repository.
The OpenQASM range reference was read through the web tool; direct HTML snapshot
retrieval returned HTTP 403. General SDK transformations, arbitrary angles and
programs, linked-reference coverage, GUI, CI and release remain unverified.
