# QB-008: original local Grover notebook

The runner executes all nine original code cells, preserving all 16 original cell sources, from `ibm_batch_jobs_grovers.ipynb` at revision `86787e1ba372facc224f925189755e69c479828b`. The original `USE_SIMULATOR = True` branch runs four three-qubit Aer circuits with 1,024 shots each. QB-008 remains open: the IBM provider branch, linked materials, editor/package acceptance and release gates are unverified.

## Execution and independent verification

Contract `qb008` uses exact Windows Python 3.12.10 profile `grover-win-py312`. Its 76 distributions satisfy 147 active requirements. PyQASM is pinned to 1.3.0: the initially resolved 1.4.0 lacks the `pyqasm.printer.draw` import used by qBraid 0.13.0's histogram implementation. The original notebook failed at cell13 under 1.4.0. Changing only this dependency to 1.3.0 made the isolated import and full original notebook pass. No original source or installed SDK was patched.

Separately labelled authored cells wrap `build_grover_qasm` after its original definition, capture its unchanged return values during original cell7, and restore the original function immediately afterward. Lifecycle cleanup also restores it on failure. These are the actual four original generated programs, not later regenerated substitutes. The original depth1 example and final depth3 source agree with their captures.

The witness binds the oracle, diffuser and measurement structure, compares loaded circuits with captured QASM, checks qubit-to-classical-bit mapping, and independently computes integer-amplitude Grover recurrence. Authored SDK statevector extraction agrees up to one global phase per state, with residual below 1e-12. Target101 probabilities at depths0–3 are 1/8, 25/32, 121/128 and 169/512. Every measured state's frequency is checked with a six-standard-deviation plus two-shot tolerance. Sampling remains unseeded.

## Evidence

Two integrated owned-kernel runs passed all nine original code cells; each terminated with zero owned processes. All 16 cell sources match the original. Run02 target101 counts were 130, 809, 963 and 366. Its four original cell13 histograms were visually inspected and agree with the captured counts.

Before/after run02 inventories match for all 26,715 files (631,735,605 bytes) across the environment, base interpreter and runner. This verifies endpoint integrity, not absence of transient writes. The 65 applicable unit/regression tests passed. An initial broad test invocation mistakenly used the dependency-free base interpreter and failed; it is not passing evidence. The existing `LifecycleTests` requires its own distinct exact profile and was excluded from the focused suite; the two actual QB-008 runs exercise this contract's kernel lifecycle.

The retained clean native worker from source `ae30847d2c5033638027097ee6966134b42742b4` imported the four captured QASM programs. Four exact distributions equal the independent rational probabilities, and four 10,000-shot distributions pass the sampling tolerance. This is separate native verification, not a GUI or released-package claim. The marked bitstring101 is palindromic; this example alone does not establish general bit-order behavior.

`index.json` binds retained evidence under `cleanup-audit/learning-coverage-20261117/qb008-notebook` and prerequisite dependency diagnostics. Paths are relative to that evidence root unless prefixed `../qb008-prerequisites/`. Local paths are not a portable release artifact. No cloud job was submitted and no release was published.
