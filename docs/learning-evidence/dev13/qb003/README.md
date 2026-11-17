# QB-003: original notebook and initial-reset exact execution

Follow-up: the reset fix now has a [clean native build and complete native suite](clean-build.md)
at `ae30847d2c5033638027097ee6966134b42742b4`. The overlay evidence below is retained
as the earlier diagnostic stage; hosted CI, GUI/package and release remain pending.

All nine cells of the [pinned qBraid notebook](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/PyQASM-Examples/qasm_unroll.ipynb)
are preserved; its six code cells execute unchanged with PyQASM 1.3.0.
Source SHA-256: `ead11c7785b8996b8386fac69c63a710ef8bb2742533db14ca3bacd21f8536d4`.
The existing `autoqasm-win-py312` profile supplies the locked dependencies;
this notebook does not use AutoQASM. QB-003 remains unchecked pending broader
acceptance, GUI, CI, packaging and release of this change.

## Original execution and arithmetic

| Cells | Evidence |
|---|---|
| 0, 4 | Introduction and linked OpenQASM example read; input difference recorded below. |
| 1–3 | Original offline pip setup, import and version expression execute; version is `1.3.0`. |
| 5 | Original 833-byte embedded QASM retained exactly. |
| 6 | Original load, validation and unrolling execute. |
| 7 | Original displayed list equals the captured unrolled program's lines. |
| 8 | License notice read; non-executable. |

The notebook's `a_in={0,0,0,1}` sets `a[3]`, so the input is 8 and the sum is
8 + 15 = 23 (`10111`), despite its comment describing `0001`. The
[linked OpenQASM example](https://github.com/openqasm/openqasm/blob/9150b157df801702b02ac7c14979ace8aba53a85/examples/adder.qasm)
instead uses `uint[4] a_in=1`. The notebook's changed input is preserved; it is
not rewritten to reproduce the linked example's sum of 16. This source finding
continues the discrepancy already recorded in the earlier QB-003 fixture audit.
The paper cited by the program was checked at abstract level only, not fully audited.

An authored witness checks the ten resets, five preparation gates, 25-gate
adder core, declarations and five measurement destinations. An independent
integer-arithmetic expectation checks all 1,024 basis inputs of that core:
`b := (a+b+cin) mod 16`, `cout := cout XOR carry`, with `a` and `cin` preserved.
All output basis states are distinct. This is exhaustive for this finite
reversible Boolean core; it is not a native full-state observation or general
adder/unroller conformance. Six mutation/state tests pass.

## Exact execution gap and fix

Published worker `c5a456cde595b3e1211cfc51a233dea511322a56` samples the original
program correctly (10,000/10,000 at `10111`) but its exact request exceeded
180 seconds. An explicitly authored diagnostic removing only the initial reset
prefix returned exact probability 1 in 0.39 seconds. That diagnostic is not
presented as original-source acceptance.

The phase evaluator previously rejected every reset, selecting the general
density evaluator. It now validates and skips only a leading reset prefix:
its initial state is already zero. Resets after a gate or measurement, dynamic
wire selections, and other unsupported structure retain the general path.
The source program and imported circuit retain all resets.

The new leading-reset regression fails on the old evaluator (check 7), then
passes with the change. The phase suite passes 128 checks, the exact worker
protocol passes 71 checks, and the 55-gate inverse-QFT regression passes all
eight probability checks. Original and unrolled QB003 programs each pass
exact and sampled execution through compilation and saved-model reload:
probability 1 and 10,000/10,000 shots at `10111`. All four candidate requests
complete within the verifier's 30-second per-request bound.

These results use a **local candidate overlay build**, not a released worker.
The modified phase object is linked ahead of a retained static archive; 166
other library source/header files match its source tree byte-for-byte. Build
commands, archive/binary hashes, and the two modified files are recorded. This
does not substitute for a clean full-source build or release verification.
An initial test launch used an incomplete definitions directory and failed at
check 1; rerunning with the published definitions produced the actual regression
failure at check 7. An initial worker compile lacked an include path; the
corrected build and its commands are retained separately.

## Integrity and remaining scope

Before/after snapshots match for 29,295 files totaling 741,399,134 bytes across
the SDK environment, base interpreter and notebook runtime. Setup metadata and
RECORD comparisons pass; 89 distributions satisfy 145 active requirements.
These are interval snapshots, not monitoring of transient or whole-machine
changes. Owned kernel cleanup reports zero active processes.

The adjacent index binds local evidence under
`cleanup-audit/learning-coverage-20261117/qb003-notebook/`. Historical packaged
sampling/editor acceptance remains in [QB-003](../../QB-003.md); this new route,
reset optimization, exact GUI behavior, CI and release remain unreleased. The local
clean-native-build follow-up above does not establish those delivery gates.
No cloud/provider execution is claimed.
