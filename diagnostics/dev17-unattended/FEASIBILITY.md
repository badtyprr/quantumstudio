# DEV-17 unattended GUI feasibility — 2026-11-03 Pacific

Historical initial status (superseded by the coordinator update below): **blocked on an authorized, provisioned test environment; no unattended GUI acceptance claimed.** This is a diagnostic/provisioning handoff with an unproven runner proposal, not a product fix or supported runner. Base upstream: `02d5ca3f5713385818e80db15b1a58e3b518e569` (fetched this session). The original `windows/Dev17GuiTests.cs` and `windows/test-named-subsystems-gui.ps1` are unchanged.

## Evidence and limits

Evidence root: `F:/src/libqalculate/cleanup-audit/dev17-unattended-20261103/`, outside the isolated checkout. `input-hashes.json` pins the original fixture and preserved failed-run records. Earlier runs remain untouched in `cleanup-audit/dev17/`.

- `local-feasibility/environment.json`: SIBERIAN, Windows 11 Pro build 22631, session 1, WinSta0/Default, current user Simeon. Native OpenClipboard succeeded and its handle was closed. No Clipboard text was read or written. This says nothing about Copy correctness or locked operation; `quser Active` is not proof of an unlocked desktop. There was no request to lock/unlock the workstation and no change to its desktop policy.
- Earlier private-station probe reports native error 5 and WPF 0x800401D0. Original GUI runs fail after ten actual Copy/Clipboard attempts. The different current observation does not invalidate those failures or prove elevation necessary/sufficient.
- No Hyper-V management module/Get-VM/vmms found; virtualization CIM namespace unavailable. HypervisorPresent=true alone does not establish a usable guest. CPU virtualization fields under an active hypervisor are not a reliable firmware verdict.
- VMware Workstation exists outside PATH; `vmrun list` reports zero running VMs. Per-user inventory lists Gentoo Linux only, at a missing D:/Virtual Machines path. This bounded inventory does not prove no Windows image exists anywhere on disk.
- `github-runners.json`: authenticated repository REST GET `/repos/badtyprr/quantumstudio/actions/runners` reports zero self-hosted runners. Organization-wide inventory and external machines were not exhaustively searched. Coordinator knows no authorized remote interactive Windows runner.
- Existing Windows GUI CI uses `windows-2025-vs2026` and `windows/test-gui.ps1`; its passing status is not evidence for the named-subsystem Clipboard fixture.
- Development payload under `.tools/dev17-validation` mixes released GUI revision 52c37a2 with older DEV-17 worker fffb351. It is unsuitable for final integrated acceptance. Coordinator owns a fresh candidate at the pinned upstream revision and will supply its manifest.

Reproduce bounded local checks (fresh directory required):

```powershell
pwsh -NoProfile -File diagnostics/dev17-unattended/Inspect-Environment.ps1 -Evidence F:/src/libqalculate/cleanup-audit/dev17-unattended-20261103/local-feasibility-next
```

The inspector only queries configuration and briefly opens/closes the native Clipboard handle. It creates evidence files and compiles an in-process identity helper; it does not test or change Clipboard content. Unavailable queries are recorded rather than converted to success. Do not interpret its exit code as GUI acceptance.

## Concrete next route: hosted candidate experiment

The coordinator requested a single isolated, manually dispatched GitHub-hosted Windows job using the existing runner label. `hosted-workflow.yml.proposed` is the exact proposed new workflow file; the coordinator owns installing it under `.github/workflows/`. It builds a new hosted candidate with unchanged `windows/package.ps1 -Candidate`, then calls `Run-Acceptance.ps1` against those same bytes. The following download route remains an alternative if local-byte acceptance is later required. This avoids installing a local hypervisor or touching workstation security. It is a **candidate experiment**, not a documented guarantee that this fixture's Clipboard works. GitHub documents fresh Windows VMs; Microsoft separately requires interactive agents for desktop UI tests. Neither source proves this application's fixture will pass.

Coordinator owns all workflow edits. Before dispatch, obtain authorization for the artifact transfer/destination, workflow change and any billable runtime. Confirm repository visibility/billing; do not assume free capacity. The download-only experiment can use a 15-minute bound; the supplied full-build proposal has one 120-minute job, no retries, contents-read only, no secrets exposed to the guest, no privileged install or ACL change. An early failed environment gate must upload diagnostics and stop.

1. Wait for coordinator's clean candidate build to finish. Export its ZIP plus externally pinned SHA-256, complete payload manifest, exact source/worker revision and build logs to an agreed non-release artifact location. Do not publish a release as transport.
2. Pin workflow source and both original fixture hashes. Download candidate into an empty per-job directory; verify ZIP and every payload hash against the independently supplied manifest, then extract with path-traversal rejection. Do not rebuild GUI/worker on the runner. For downloaded payloads, install nothing unless separately reviewed and authorized; the fixture requires x64 .NET Framework WPF and csc.
3. Run the inspector on the runner; record run/job ID, runner image/version, OS, process/session identity, window station and desktop. Native Clipboard open is a preflight only. If denied, preserve evidence and fail without retries/elevation/security edits.
4. Invoke the unchanged real fixture with absolute distribution/evidence paths and the coordinator-pinned WorkerRevision:

   `powershell -NoProfile -File windows/test-named-subsystems-gui.ps1 -Distribution <verified-payload> -Evidence <fresh-run>/original -WorkerRevision 02d5ca3f5713385818e80db15b1a58e3b518e569`

   That fixture clicks actual Calculate and Copy controls, reads Windows Clipboard, compares all exact cells, re-enters expressions, and saves/reopens the mapping. Internal copyText is used only as a freshness comparison; never substitute it as observed Clipboard text. Require zero process exit, PASS result, verified_after_run=true, expected captures and mapping.qsession, and pre/post hashes of GUI, worker, compiled driver and driver source. Inspect all four captures. Preserve logs even on failure.
5. Add separately reviewed supplemental keyword coverage; do not modify or replace the original fixture. For each `not`, `and`, `or`, `xor`, use the contract's asymmetric rho mapped as `[keyword,A]` and `[A,keyword]`. Actual Calculate/Copy/re-entry must equal respectively `matrix(2,2,[3/4,1/4,1/4,1/4])` and `matrix(2,2,[1/2,0,0,1/2])`. Cover bare, single/double quoted, list/vector and supported TeX selectors, plus saved/reopened evaluated keyword mappings. Preserve the assigned numeric `k=0`, `[k,"not"]` compatibility case against the independently specified native/worker oracle. `KeywordGuiTests.cs` now implements keyword, selector spelling, asymmetric-order, multiple-keyword and saved-mapping cases. It compiles locally but is not yet executed. The assigned numeric compatibility case remains covered only by prior native integration evidence, not this GUI supplement. Keyword acceptance remains OPEN until independent review and actual execution pass. Original fixture alone is insufficient for the expanded user acceptance.
6. Run a second fresh job with identical payload and hashes after first success to establish repeatability. Host workstation must be irrelevant to job execution: no RDP/clipboard redirection or desktop interaction from it. Record that isolation; do not claim the physical host was observed locked unless lock-state evidence exists. On a deliberately scheduled locked-host run, gather read-only host lock-state evidence at start/end without asking for an unlock or changing policy.
7. Always export logs, captures, saved session, exact source hashes, payload manifest, session identity, exit status, timeout and cleanup record before the ephemeral guest is discarded. Record child process IDs; on timeout terminate only the driver and its descendants, not arbitrary shared workers. Do not assume the original timeout wrapper kills worker descendants. Verify no owned process remains. Keep failed runs immutable. Coordinator retains external evidence and handles artifact retention.

## Alternative: dedicated Windows VM provisioning proposal

If hosted Clipboard fails, select an existing approved Windows VM host first. Local VMware is installed but there is no inventoried Windows guest. Proposed guest: x64 Windows with valid license/image provenance, 2 vCPU, 4–8 GiB RAM, 64 GiB thin disk, local non-administrator test account, isolated network, no host Clipboard/shared-folder redirection or production secrets. These are proposed limits, not provisioned resources.

Approval package must specify VM host/path, image/license, storage/runtime budget, owner, credential provisioning channel, allowed network access, guest interactive-login mechanism, and retention/teardown. Do not store credentials in scripts, command lines or evidence. Do not enable autologon, suppress lock policy, open RDP/firewall, enable Hyper-V/reboot, or grant privileges without explicit authorization. If an approved interactive session cannot remain available for a bounded job under the existing policy, stop and report that blocker; never relax workstation security to obtain a pass.

After approval, an administrator creates only that guest, installs the required runtime and isolated test account, establishes an approved guest console login, and registers a bounded task under that interactive user's token (not a service/S4U session). A remote command channel may start an already approved interactive task but is not itself proof of an interactive Windows desktop. Copy the verified candidate without Clipboard redirection, execute steps 3–7 above, then stop the guest after verified evidence export. Repeat from the same image in a new run. Image reproducibility includes VM identity/configuration and snapshot/image hash. Never reuse a stale PASS directory.

Do not delete the guest or checkout until its unique work and evidence have verified recovery copies. Repository deletions must be resolved beneath `.tools`; the managed checkout is outside `.tools` and is retained. Root dist and all original failed runs remain intact.

## Ownership and current decision

GUI owner changes only new `diagnostics/dev17-unattended/` files and external evidence/coordination notes. Coordinator owns CI, packaging, central checklist and release. No heavy builds, persistent infrastructure changes, product changes, credential requests, publication or cleanup were performed here. The precise current blocker is absence of a provisioned/authorized environment and successful unchanged Clipboard execution independent of the workstation, plus unexecuted supplemental keyword acceptance. This handoff satisfies the evidenced-blocker branch of the task, not the GUI pass branch.

Primary references, checked 2026-11-03 Pacific:

- [Windows window stations](https://learn.microsoft.com/en-us/windows/win32/winstation/window-stations): per-station Clipboard and interactive WinSta0.
- [Microsoft UI testing considerations](https://learn.microsoft.com/en-us/azure/devops/pipelines/test/ui-testing-considerations?view=azure-devops): desktop UI needs special interactive-agent setup; Azure hosted visible UI limitations must not be generalized into a tested verdict about GitHub.
- [GitHub hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners): Windows VM lifecycle and billing distinctions; no application Clipboard guarantee.
- [PowerShell Direct](https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/powershell-direct): host administrator and guest credentials required; a command session alone does not establish GUI acceptance.

## Hosted build proposal implementation status

The workflow uses the existing Python 3.12.10/action pins and a separately pinned MSYS2 setup action. It installs UCRT64 native dependencies and the repository-pinned Python requirements into the ephemeral runner, with the Python environment outside the source tree so package.ps1's clean-source precondition can pass. Its `-Candidate` switch avoids fetch/master-release checks and does not publish. Package.ps1 is parameterized for these roots and has no known local-machine path requirement in the inspected call chain, but the full hosted build has **not been executed**; package/test failure is a possible evidenced outcome. Tool versions are recorded because MSYS package resolution is time-dependent. No runtime/reproducible-build guarantee is claimed.

Run-Acceptance verifies every manifest-listed payload file before/after, uses the unchanged original wrapper, separately compiles/runs the keyword driver, records process/session identity and driver/application/worker hashes, and requires original post-run verification plus captures/sessions. Visual review stays pending. Descendant polling is best-effort and explicitly cannot prove containment of short-lived parents; use a dedicated single-job guest, retain process records, and regard guest disposal as final containment. Do not run this runner on a shared workstation until stronger containment is implemented or its limitations are accepted for a bounded local evidence run.

Local validation: read-only inventory executed; supplemental C# compilation passed; PowerShell syntax parsed; no GUI driver or package executed here. The first compilation command used a relative slash path that csc misparsed and failed before compilation; a corrected absolute-path command passed. No original failed fixture evidence was replaced.

These files are infrastructure diagnostics, not product/distribution files. No source-archive registration is proposed: hosted source checkout includes them, while original shipped GUI fixture registration remains untouched. If the coordinator elects to ship this runner, source-distribution registration and tests require a separate reviewed shared-file change. Artifact upload is a new proposed use of a pinned upload-artifact action; the current workflows contain no existing upload pattern. Artifact retention is 14 days; export evidence to the external audit directory before expiry.

## Coordinator integration decision — 2026-11-03

The coordinator verified that badtyprr/quantumstudio is public and selected the
existing standard hosted Windows runner under the requested CI/candidate work.
The integrated workflow also runs for pull requests changing this workflow or
its diagnostics, so its first run can be reviewed before any master merge.
It retains the 120-minute bound, read-only repository permissions, no secrets,
no retries and 14-day artifact retention. No release transport or publication
is authorized. The proposal above remains historical context; the installed
workflow is the executable source of truth. Newly built hosted bytes require
their own acceptance and local artifact verification.

## Coordinator retained-candidate recheck -- 2026-11-03 Pacific

The initial full hosted build completed successfully in run 41781100599. Its
acceptance launch failed before GUI execution because Windows PowerShell 5 could
not resolve Get-FileHash in the inherited PowerShell 7 module environment.
The reviewed child-shell fix uses the current process executable; Test-ChildShell
reproduces the original failure and checks hashing, shell identity, exit-code
propagation and owned-descendant cleanup. Original failure evidence is retained.

The installed workflow now reuses that exact archived candidate, pins both archive
hashes and unchanged original fixture hashes, verifies the payload manifest, and
runs actual Clipboard acceptance within a 20-minute bound. It has read-only
contents/actions permissions, no rebuild, no publication and 14-day evidence
retention. Artifact expiry is a hard failure; this finite recovery workflow is not
a permanent new-candidate build workflow. The full-build proposal and Git history
preserve the original recipe. Hosted acceptance and repeatability are pending.

The separate local clean package has now passed original 72 and keyword 306 actual
Clipboard checks with zero retries; all captures were inspected. That result is
bound to the local candidate and says nothing about a locked host. See the current
[coordinator record](../../docs/learning-evidence/dev17/integration.md) for hashes,
new validation and still-open release gates. Earlier sections retain the initial
investigation and proposal as historical context, not current acceptance claims.
