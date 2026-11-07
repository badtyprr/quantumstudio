# DEV-17 final revision proposal

This proposal extends draft [PR #428](https://github.com/badtyprr/quantumstudio/pull/428)
with assigned numeric-k GUI acceptance. It does not authorize merging or publication.
DEV-17 remains Partial and DEV-17d remains unchecked.

## Selected candidate path

Build the reviewed PR head containing the numeric-k supplement and this proposal
using `.github/workflows/dev17-release-candidate.yml`. The checkout explicitly uses
the PR head SHA, not the moving PR merge ref. The unchanged PowerShell 7
`windows/package.ps1 -Candidate` runs the complete packaging pipeline on an isolated
hosted Windows runner. Its source record pins the full commit and tree. The candidate
manifest, source archive and ZIP identify the same source revision.

Verify the ZIP against its manifest, extract it, and run the unchanged original
GUI fixture followed by the extended supplement against those extracted binaries.
Actual Calculate and Copy controls, Windows Clipboard reads, exact re-entry and
saved/reopened mappings are required. Preserve full results and failures, inspect
captures, and verify payload and archive hashes after acceptance. Generic GUI CI
and internal copy-text checks do not replace this acceptance.

The final head must also have independent Standards and Spec reviews and all
three required CI checks. Download hosted evidence before its 14-day expiry;
retain logs, `.trs` results, complete package outputs, source/toolchain provenance,
fixture/driver hashes and the run/attempt metadata outside disposable checkouts.
Replay the packaged-worker named-subsystem, exponent, 65-fixture, M10 and unchanged
286-case checks on these new bytes. Record these as new executions only when they
actually finish. No performance or reproducible-build claim is implied.

## Result binding and release gates

The durable coordinator record is
`F:/src/libqalculate/cleanup-audit/dev17-release-revision-20261103/HANDOFF.md`;
the independent verification report is under
`F:/src/libqalculate/cleanup-audit/dev17-release-verification-20261103/`.
The PR body and those records bind the selected full head, workflow run/attempt,
artifact hashes, independent reviews, CI and completed acceptance. They distinguish
pending checks from passes. This source document specifies the process; it does
not predeclare that a future build or test has passed.

After the release owner approves the exact reviewed head and merge, verify the
actual merged revision and its required CI. Build a release from that clean master
revision using the unchanged package command without `-Candidate`; rerun package
and relevant actual-candidate acceptance and bind its new hashes. The pre-merge
candidate has `candidate: true` and must not be renamed or relabeled as that release.
Tagging, publication and download verification remain separately authorized gates.

The earlier local candidate at `02d5ca3f5713385818e80db15b1a58e3b518e569` and hosted
candidate at `6005e1de0e36c985a1319d6255274c430d06b634` retain their own results and
hashes in the sealed `dev17-candidate-20261103` evidence. The old retained-artifact
workflow remains a finite recheck of those bytes, not the new candidate build.
Preserve original failures, root README/dist, retained DEV-13/DEV-16 work and active
dependencies. No cleanup is part of this proposal. Source-lesson, symbolic-dimension,
set-indexed-sum, block-matrix, notebook and existing DEV-09/10/11/12 limits remain.
