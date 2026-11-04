# DEV-17 integrated source status — 2026-11-03

[PR #427](https://github.com/badtyprr/quantumstudio/pull/427) merged at
`02d5ca3f5713385818e80db15b1a58e3b518e569`, with the same product tree
`0bbf9fe440e755378675d485e7ae6bd62843b106` as reviewed head
`2322b0fc7142d0f2440b24aa76654e991d609801`.
Independent Standards and Spec reviews had zero outstanding mandatory findings;
Standards retained an optional dimension-validation duplication observation.

The coordinator rechecked live GitHub state on 2026-11-03 (Pacific time): all
three required checks succeeded on both the reviewed and merged heads. Merged
head jobs: [native](https://github.com/badtyprr/quantumstudio/actions/runs/41606306135/job/125816870696),
[GUI](https://github.com/badtyprr/quantumstudio/actions/runs/41606306244/job/125816870639),
and [OpenQASM](https://github.com/badtyprr/quantumstudio/actions/runs/41606306387/job/125816871184).
The GUI CI job does not establish real Clipboard acceptance.

## Historical integration validation

The corrected integrated native run recorded 79 tests: 78 pass, one existing
thread-test skip, zero failures and zero errors. Separate native and Python
worker logs establish that 88 native named-subsystem and 212 worker checks ran.
The integrated worker additionally passed 30 exponent-boundary cases and 30
exact reentries, the unchanged 65 audit fixtures, the original M10 true/true
derivation and its gathered-TeX reentry, and all 286 unchanged DEV-11 expectations.
No performance claim follows from these runs.

Worker SHA-256:
`ffacef75b0e9a126270c0b93709dbaf64f5c8ba73fdfb78aea37f195d10cb1e7`.
Initial clean compilation was followed by an incremental correction and a
complete test rerun with fresh logs. This was not a clean packaged-release build.
On 2026-11-03 the coordinator reverified all 176 recorded log, evidence and worker
hashes against retained files; all matched. This verifies historical evidence,
not newly executed candidate tests.

Evidence is retained outside disposable checkouts at
`F:/src/libqalculate/cleanup-audit/dev17-integration-20261103/`, including
`local-validation.json`, `merge.json`, `merge-reviews.json`, original interrupted
build logs and `M10-integrated.json`. The initial M10 harness incorrectly expected
the standalone evaluator's vector spelling on the multiline integrated route;
`M10-integrated-corrected.json` records the reviewed correction without replacing
the failed assertion. Earlier keyword, scope and Clipboard failures remain in
the [validation record](validation.md).

The current recheck is retained in
`F:/src/libqalculate/cleanup-audit/dev17-candidate-20261103/`:
`upstream-current.json` and `historical-reverification.json`.

## Open release gates

DEV-17 remains Partial and DEV-17d remains unchecked. Actual Windows Clipboard
Copy/re-entry against candidate binaries, inspected captures, and fresh packaged
release validation remain open. Internal copy-text checks and generic GUI CI do
not close this gate. A fresh PowerShell 7 package attempt is being recorded
separately; no result from it is claimed here.

Neither PR427 nor this evidence update publishes a release. The source lesson,
symbolic dimensions, set-indexed sums, block matrices and notebook remain outside
this finite acceptance claim. Historical DEV-09/10/11/12 limits are unchanged.
