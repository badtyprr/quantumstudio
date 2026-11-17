# IBM static circuit timing: source and retained-output audit

This records all eight cells of the pinned static timing guide. Both original
code cells executed unchanged through the instrumented notebook route. This is
local source evidence, not DEV-15 completion, a hardware run, or released support.

Source: [visualize-circuit-timing.ipynb at a500b17f](https://github.com/Qiskit/documentation/blob/a500b17f8b1f156a6bba42ab11f90f3104cad6d4/docs/guides/visualize-circuit-timing.ipynb).
SHA-256: `fea8aac0228da80e41db72aec8de00d153286f2e44d61789f1b7c21eba56b6d0`.
The retained run used the restored runtime at `4c1e36d4a2f9782483232c6f80e4e91ebde3772d`
and `timing-win-py312`: Python 3.12.10, Qiskit 2.6.1, Windows x64.
The profile describes a 62-distribution closure including two custom pure-Python
wheels. The supplementary replay below checks before/after integrity of the
retained environment; it does not establish a fresh install or wheel provenance.

## Cell-by-cell disposition

Indices are zero-based. Every original source string and cell type matches the
executed notebook. Instrumentation, checkpoint cells and controls are additions;
this is not an uninstrumented run of the original file.

| Cell | Source requirement | Actual result / disposition |
|---|---|---|
| 0 | Title and purpose: visualize circuit timing | Non-executable framing; the two original figures are retained and inspected. |
| 1 | Qiskit package requirement | Declares `qiskit[all]~=2.6.1`; run uses the pinned timing profile. Supplementary replay checks exact pins, dependency closure and file integrity. |
| 2 | Static scheduling, idle time, dynamic-circuit warning and default style | Interpretation retained: static fake-backend durations, with no dynamic scheduling or hardware accuracy claim. Linked content is classified below. |
| 3 | Build H/CX circuit, five-qubit fake backend, transpile, draw | Passed unchanged. RZ/SX/RZ/CX preserves the Bell density; SX 258 plus CX 1179 gives horizon 1437 cycles. PNG is present in this original cell's output. |
| 4 | Debug stylesheet heading | Non-executable introduction to cell 5. |
| 5 | H/CX plus final measurements, transpile, debugging-style draw | Passed unchanged. SX 256 plus CX 1365 ends at 1621. Measurement durations 5650/5830 end at 7451; q0 starts at 1801, leaving a 180-cycle gap. PNG is present in this original cell's output. |
| 6 | Custom generator/layout functions and API reference | Conceptual extension point, with no inline executable example. API linked below; custom generators/layouts are not executed by this evidence. |
| 7 | Further visualization recommendations | Links are reachable and classified below; their additional examples remain separate audit work. |

`GenericBackendV2(5)` has no seed in either original cell. The numbers above are
the actual retained targets, not constants promised across reruns. Each run must
be checked against its own target durations. The recorded time quantum is
`2.22e-10` seconds and timing constraints are all one cycle.

## Verification of the actual artifacts

Evidence root: `cleanup-audit/learning-coverage-20261117/` in the main repository,
outside the development worktree. `dev13-shared-runtime/ibm-timing/` contains 15
retained files. `timing-source-audit/audit.py` and `result.json` bind their hashes
and repeat the scalar verification without importing Qiskit.

The host audit checks all eight source cells, both embedded PNGs against their
extracted files, target-to-integer duration conversion, both ALAP schedules and
all generated idle intervals. It recomputes both circuits' pre-measurement Bell
density after each transpilation stage. Six separate authored controls exercise
logical q0, logical q1 and a phased Bell state under nontrivial placement; their
two transpilation stages also match the independently constructed density.
Final measurement mappings are checked; measurements are not sampled by the
scalar state calculation.

Both actual PNGs were viewed. The default figure shows the SX/CX sequence and
unused q2–q4 lanes. The debugging figure shows the unequal measurements,
180-cycle gap and 7451-cycle idle lanes. Early RZ/SX labels overlap in the
debugging image. Exact values come from captured records and scalar arithmetic,
not pixel geometry. PNG extraction proves association with the original output
cell; interception does not establish a byte-level formatter-to-Figure lineage.

The launcher recorded kernel membership in its Windows job, zero active
processes after forced cleanup, and exit zero. This is not a graceful-shutdown
claim. Compiled-extension source correspondence remains unverified.

## Linked content, checked 2026-11-17

- [Circuit visualization guide](https://quantum.cloud.ibm.com/docs/en/qiskit/visualize-circuits): text, Matplotlib and LaTeX rendering, saving and styling. These are distinct drawing examples; LaTeX also requires external tooling. None is executed by the two timing cells.
- [Timeline API](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.visualization.timeline_drawer): backend targets supply durations; controls cover style, lanes, labels, axes and output files. The API also documents custom formatting/generator/layout options. The source exercises default/debug styles only; broader API options remain unaudited.
- [Runtime timing guide](https://quantum.cloud.ibm.com/docs/en/ibm-quantum-compute/qiskit-runtime-circuit-timing): dynamic timing comes from Sampler job metadata requested with `scheduler_timing`, including branch/channel records. Its Plotly drawing route is separate. The current guide mentions dry-run jobs, but no service connection, job submission or dry-run was performed here.

These live pages supplement the pinned source; they do not replace it or inherit
its execution evidence. Remaining gates include broader linked examples,
hosted CI, package/release verification and provider workflows.
No source checklist row or development checkbox closes in this change.

## Supplementary environment replay

A fresh execution at `31bb6fc379854973a2827a79cdcdf066b0e2ea26` reused the existing
timing environment. All 62 installed distributions matched exact pins; Python
requirements and 129 active dependency requirements, including requested extras,
were satisfied. Installed module files were checked against available RECORD
hashes. The 14,353-module inventory was identical before and after execution.
All 26,953 files (701,444,778 bytes) across the environment, base interpreter and
notebook runtime retained their bytes: zero additions, removals or changes.
This checks consistency against installed metadata, not independent authenticity
of the custom wheels or compiled-extension correspondence to upstream source.

The new run again preserved eight original cells, executed both code cells and
passed six authored controls. The host audit recomputed schedules, idle intervals
and state comparisons from this run's records. Its random fake-backend targets
gave horizons 1364 and 7790 cycles; the second q0 idle gap was 866 cycles, followed
by a 4589-cycle measurement finishing alongside q1's 5455-cycle measurement.
Both new original-output PNGs were inspected; early labels still overlap.
Cleanup again reported job membership and zero active processes after forced
termination. No hardware jobs were submitted.

The full before/after inventories, dependency results, original outputs, scalar
audit and comparison are in `timing-environment-replay/` under the evidence root.
The committed JSON includes their hashes. The earlier run and its different
durations remain intact; their evidence is not overwritten by this replay.
