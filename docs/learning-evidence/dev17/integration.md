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

## Fresh candidate validation -- 2026-11-03 Pacific

The clean PowerShell 7 package at source `02d5ca3f5713385818e80db15b1a58e3b518e569`
passed 78 native tests with one existing skip and zero failures/errors, including
88 native and 212 worker named-subsystem checks. The actual packaged worker
additionally passed the 30 exponent cases and 30 exact reentries, unchanged 65
audit fixtures, M10 true/true derivation and gathered-TeX reentry, and all 286
unchanged DEV-11 expectations. No timing claim follows.

Against these exact local candidate binaries, the unchanged original GUI fixture
passed 72 checks and the reviewed keyword supplement passed 306 checks, including
actual Copy controls, Windows Clipboard reads, re-entry and saved/reopened
mappings. Both recorded zero Clipboard retries and verified post-run binary hashes.
All eight GUI captures and the package smoke capture were visually inspected.
This local desktop pass does not prove locked-workstation or unattended operation.
This 306-check supplement did not exercise assigned numeric `k=0`. The new
[numeric-k supplement](numeric-k-gui.md) distinguishes the direct native oracle
from worker-route probes and pending actual-candidate GUI acceptance; see the
[final revision proposal](release-proposal.md) for the separate build/release gates.

Candidate ZIP SHA-256:
`77a044ab1c27c1f3bef93e25d229e2f42ae04cb6d6a0c1d97d04b65e25b3b938`.
Worker SHA-256:
`8e26bf5c1b991c896d0c168573d8f1c1207c166fd0796cb9b4a5fe3f8b5b8578`.
The external candidate evidence directory contains `package-audit.json`,
`fresh-native.json`, `worker-validation.json`, `baseline286-summary.json`,
`local-gui-original/`, `local-gui-keywords-attempt2/`, `local-visual-review.json`,
complete logs and archived artifacts. The initial supplemental compile-path
failure and the initial source-audit helper failure remain separately retained;
neither was a product test failure or overwritten by the corrected attempt.

## Hosted attempt and open release gates

[Hosted attempt 41781100599](https://github.com/badtyprr/quantumstudio/actions/runs/41781100599)
built a separate candidate successfully at PR merge revision
`6005e1de0e36c985a1319d6255274c430d06b634` (tree identical to reviewed `185ead319`).
Its native suite passed 78 tests, one existing skip, zero failures/errors. Actual
GUI execution never began: the Windows PowerShell 5 child inherited the PowerShell
7 module environment and could not resolve Get-FileHash. The original failure,
full artifact and independently verified package/source hashes remain under
`hosted-41781100599-attempt-1/` in the external evidence directory.

A reviewed narrow correction launches the original wrapper with the current
PowerShell 7 executable. The installed workflow rechecks the exact retained ZIP
`f655f8e09f64c16419b9e13bc33404417fe0ae93bd69e8855f00b6374b11ebcf`, with
pinned source archive and original fixture hashes. It does not rebuild or publish;
it fails closed if the retained artifact expires. Hosted Clipboard acceptance and repeatability subsequently passed in
[run 41787703905](https://github.com/badtyprr/quantumstudio/actions/runs/41787703905),
attempts 1 and 2. Each passed the original 72 and supplemental 306 actual Clipboard
checks with zero retries, unchanged payload/fixture hashes and inspected captures.
The provisioner worker IDs and runner IDs differ (westcentralus and eastus3);
the image hostname repeats and is not used as proof of guest independence.
Acceptance merge `d5f5bcbad629f133b4717aab91c54fa671b23086` has the exact tree of
independently reviewed head `97544c67cf13683af550a07f50f644fb2a6db3e0`.
All 16 acceptance captures and the hosted package smoke capture were inspected.
External `hosted-acceptance-summary.json`, `recheck-source.json` and each retained
attempt's `visual-review.json`, full logs and artifacts bind these results.

Hosted GUI SHA-256:
`e4ccc430852a196b23b69e451c55d93fb84838291ea67e45f438df0289250a6e`.
Hosted worker SHA-256:
`ef5bc7947b0df1f1fdfd41a3b03a2646db663598b671a7248b0cbfeaf573937d`.
The local extra audit/exponent/286 replay results above belong to the local
candidate; they are not relabeled as hosted execution. Final release coordination
and a tested final release revision remain open.

DEV-17 remains Partial and DEV-17d remains unchecked pending the tested release
revision and release gates. Internal copy-text checks and generic GUI CI do not
substitute for actual Clipboard acceptance. Neither PR427 nor PR428 publishes a
release. The source lesson, symbolic dimensions, set-indexed sums, block matrices
and notebook remain outside this finite acceptance claim. Historical DEV-09/10/11/12
limits are unchanged.
