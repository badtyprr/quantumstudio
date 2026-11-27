# DEV-17 released acceptance reconciliation

DEV-17's finite named-subsystem contract shipped in [checkpoint-c5a456cd](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-c5a456cd), published November 15, 2026. This reconciles the older release-pending checklist with the final package's retained evidence. It does not complete IBM-005 or its linked notebook.

The tested source revision is `c5a456cde595b3e1211cfc51a233dea511322a56`, tree `6e197c88983875c2b4b29266e917c6693925bfbc`. Evidence is bound to fresh runs on that final non-Candidate package, not inherited from the older `f9f43bf9` candidate.

| Requirement | Released evidence |
| --- | --- |
| DEV-17a: ordered expression-local labels and dimensions | The released worker's 212 named-subsystem checks retain explicit mappings, errors and independent values. The original GUI fixture copies and re-enters the evaluated `[B,A]` declaration, then calculates a conflicting independent mapping. |
| DEV-17b: named and source TeX traces | Worker exact-matrix controls and the original GUI fixture verify both factors of the asymmetric mixture, Bell marginals, named/TeX entry and exact result re-entry. Expected matrices are asserted independently in the fixture. |
| DEV-17c: factor ordering and dimensions | Worker controls plus original GUI assertions cover unequal `[2,3]` dimensions, the middle factor and multiple traced labels. The documented scalar convention for retained dimension one remains unchanged. |
| DEV-17d: GUI, actual Clipboard and sessions | Fresh original fixture: 72 assertions. Supplemental keyword fixture: 377 assertions, including 71 assigned numeric-k assertions. All passed with zero Clipboard retries and empty stderr. Production Save/Open preserves original and numeric-k mappings and exact results after a conflicting intervening mapping. |
| Exact-head CI and release | All three required CI checks passed on the full release revision. The public non-draft release has the two verified assets below; retained credential-free downloads match current asset sizes and SHA-256 digests. |

## Binding and independent checks

- Application SHA-256: `1a881443b83e2098f77e4f6e68ac504cc39d37619629e6179b519fc25b7deea2`.
- Worker SHA-256: `87889ec52d136d4a39c755d4aa5967d5e0bc792b19ad7e4c3ef86f91e2192c33`.
- Windows ZIP: 82,790,916 bytes; SHA-256 `fc37b7d107a883afe2e06dc9ee438a7ac68533f5711db8e41d5439c4b39507f4`.
- Source archive: 5,012,600 bytes; SHA-256 `3e78894de44fa1d7f14651fe384ce702e3551f63a7a5a94406db2b4e14f93602`.

[Machine-readable reconciliation](release-reconciliation.json) records 20 final acceptance evidence hashes, 106 final GUI-review evidence hashes, 50 historically reviewed capture hashes, released source-file membership, CI links and the current public asset comparison. All matched during this reconciliation. The 50 captures cover the broader final package; the final visual review separately identifies the original DEV-17 and package-smoke captures. This is a recheck of retained evidence, not a new visual or GUI run.

The durable root is `F:/src/libqalculate/cleanup-audit/coordinator-20261104/`. Principal records are `dev05-final-actual-spec-review-20261115.json`, `dev05-final-actual-standards-review-20261115.json`, `dev05-final-visual-review-20261115.json`, `dev05-final-worker-supplements-20261115/named-worker.json`, and `dev05-public-download-20261115/verification.json`. The final GUI evidence is under `dev05-final-release-download-43741675632/artifact/_temp/dev17-acceptance/`; the original fixture's result, copied declaration, session and post-run binary provenance were inspected together with its source assertions.

The earlier `release-verification.json` and initial package `verification.json` contain pending fields from their preparation stage. Final independent reviews, acceptance and public-download records provide the subsequent evidence; those historical files are not rewritten or presented as final verdicts.

## Limits retained

Production Save/Open methods were tested, not native file dialogs. Viewport captures do not establish off-screen correctness; exact matrix Copy/re-entry assertions and raw semantic review provide that evidence. Named tracing remains limited to the explicit mapping contract, with no inferred label positions or global registry. Symbolic dimension identities, arbitrary set-indexed sums, block matrices, and whole-source notebook acceptance remain separate work. The generic function-wrapper alias limitation described in [numeric-k acceptance](numeric-k-gui.md) remains documented.

## November 27 active checklist verification

This checklist incorporates the release evidence from commit `b9a7e9ff`. A fresh run of the released Windows worker passed all 212 named-subsystem checks. The application and worker matched their entries in the published ZIP byte for byte. The four source archive members matched the retained hashes and matched the tagged source after normalizing line endings.

The current GitHub release asset sizes and digests matched both retained downloads. GitHub also confirmed successful native, Windows GUI and Windows OpenQASM checks on the release revision. Local rehashing matched all 20 acceptance records, 106 GUI review records and three supplemental records. The actual Clipboard and Save/Open evidence comes from the retained final-package runs described above.
