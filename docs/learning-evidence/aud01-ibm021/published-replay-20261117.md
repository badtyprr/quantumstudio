# IBM-021 Simon finite published-worker replay

The preserved 44-case probe was replayed on 2026-11-17 against the verified published worker from `checkpoint-c5a456cd`. All 35 finite value checks passed, including all 35 ordinary canonical copies: 20 pilot adaptations, three joint-state adaptations and 12 authored GF(2) controls. The source's n=3 input bits, m=5 output bits and secret `011` remain the fixed finite case; no arbitrary-width or whole-source claim follows.

The [receipt](published-replay-20261117.json) binds original notebook, probe, inventory, fixtures, binary and definitions and indexes raw evidence. Worker, definitions and input files were unchanged. The probe's complete source-occurrence checks ran before evaluation; matrix comparisons consume complete canonical entries, including 256-entry joint-state columns, rather than truncated display cells.

## Literal observations remain failures

All nine original literals still reject. Eight reproduce their historical diagnostics. `IBM021-c0-M088` still returns exit 2 with finite-set, scalar-bar and scalar-XOR errors. Its old trailing explanatory message about the variable `r` is no longer emitted. The unchanged historical probe therefore returns exit 1 and records this case as `unexpected_failure`; those raw observations are preserved. The changed diagnostic is not mathematical acceptance and does not establish a current regression in the 35 finite value cases.

No fixture, oracle or historical baseline was rewritten to make that exit code green. The [historical inventory and adaptation rationale](README.md) remains the source for the finite scope. Its earlier statement that the consolidated probe had not been run refers to that historical integration; this replay supplies a later native run, without expanding accepted source coverage.

## Reproduction and limits

Run `probe.py` with the pinned notebook and explicit published worker/definitions paths, a verified worker revision, and a fresh output directory. The scoped LF attributes keep probe and JSON fixture bytes consistent with Git. Inspect per-case results and the diagnostic difference above; the original exit 1 is expected on this published worker. Raw evidence is retained under `cleanup-audit/learning-coverage-20261117/ibm021-published-replay`, outside disposable checkouts. The repository receipt indexes that evidence; a repository-only clone does not contain the retained binary or raw results.

This is exact worker-protocol validation. No new notebook execution, provider call, media rendering, GUI Clipboard or saved-session test occurred. The source inventory includes conceptual content and imagery; 35 finite adaptations do not exhaust it. Original notation, unrestricted families, random-sampling/recovery guarantees, classical complexity discussion and whole-lesson acceptance remain open. IBM-021 and AUD-01 stay unchecked.
