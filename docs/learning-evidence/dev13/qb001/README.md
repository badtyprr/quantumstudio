# QB-001: original Deutsch–Jozsa unrolling notebook

All nine cells of the [pinned notebook](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/PyQASM-Examples/deutsch_josza_unroll.ipynb)
are preserved, and all six code cells execute unchanged through the owned
notebook runner. Source SHA-256:
`a91a11fbe445b73631fecf42ea4d2aebba35f2eeeb6691898373dec514528f14`.
This is a fixed four-input parity oracle, with four data qubits and one ancilla.
It is not verification of arbitrary Deutsch–Jozsa oracles or general unrolling.
QB-001 stays open pending broader acceptance, CI and release.

## Original cells and actual results

| Cells | Observed coverage |
|---|---|
| 0 | Algorithm/unrolling introduction read. The linked Wikipedia article is not audited here. |
| 1 | Original `%pip install pyqasm --quiet` ran offline against the already installed locked environment; exit zero and before/after metadata unchanged. |
| 2–3 | Original imports and version expression executed. Captured version is `1.3.0`. |
| 4 | The prose calls this a four-qubit circuit; the code has four data qubits plus one ancilla, five total. |
| 5 | Original QASM string retained byte-for-byte, including custom gates, subroutine, constant width, loops and measurements. |
| 6–7 | Original load/unroll/dump calls executed. Printed output exactly matches the retained unrolled artifact, including the print newline. |
| 8 | License notice read; non-executable. |

The route reuses the existing `autoqasm-win-py312` profile because it supplies the
required PyQASM and notebook packages. This notebook does not call AutoQASM.
The profile contains 89 exact distributions, with 145 active dependency
requirements verified before and after execution. The original setup command
is observed without replacing its source. Pip operates offline, and the setup
observer verifies unchanged distribution metadata and RECORD files.

## Independent checks and native execution

An authored witness parses the actual unrolled QASM and checks its declarations,
14 ordered gates and four measurements. It requires X on the ancilla, five initial
Hadamards, four data-to-ancilla CNOTs, four final data Hadamards, and the original
measurement destinations. Unexpected statements, modifiers and wiring reject.

A separate integer-amplitude control follows those operations with each
Hadamard's denominator retained symbolically. Nine Hadamards give denominator
`sqrt(2)^9`; only little-endian basis indices 15 and 31 remain, with numerators
16 and −16. This predicts data `1111` with probability one and ancilla `|−⟩`.
It is an authored mathematical state check, not a native ancilla-state observation.
Six focused tests cover this state, missing ancilla preparation, a missing
oracle control, wrong measurement destinations, wrong controls and extra statements.

Both the unchanged original QASM and the captured unrolled QASM independently
pass source compilation, saved-model serialization/reload, and the published
`c5a456cde595b3e1211cfc51a233dea511322a56` worker. All four native checks return
data `1111`: exact probability one and 10,000/10,000 sampled shots. This symmetric
bitstring alone does not establish arbitrary wire ordering; the structural
checks establish this source's explicit target sequence.

## Environment evidence and limits

Before/after file inventories match exactly for 29,286 files totaling 741,369,386
bytes across the SDK environment, base interpreter and notebook runtime roots.
The snapshots show no added, removed or changed files in those roots; transient
changes between snapshots were not monitored. This does not assert that the entire machine or the separate native compiler
environment was unchanged. The owned kernel cleanup reports zero active processes.

The adjacent index binds raw notebook outputs, setup observations, source and
generated programs, native results, dependency checks and both full file inventories.
Artifacts live in `cleanup-audit/learning-coverage-20261117/qb001-notebook/` in
the main repository. Original execution, authored controls and native output checks
remain distinct. GUI interaction, the outgoing article, general parameter/oracle
coverage, hosted CI, packaging and release are not established by this evidence.
