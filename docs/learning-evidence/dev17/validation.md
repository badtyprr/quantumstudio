# DEV-17 validation and integration handoff

## Integration-review correction: operator keyword labels

Integration review found that valid labels `not`, `and`, `or`, and `xor` were
accepted in declarations but rejected as unquoted trace selectors. The original
reviewer input, output and old worker hash are preserved in `keyword-original.json`;
`keyword-baseline.json` separately records 22 new failures and 112 prior passes.
No identifier-contract restriction was introduced to hide these failures.

Correction commits `4f5ba575f` and `8c07c7205` avoid expression reparsing only for
valid literal selectors containing an unquoted operator keyword. Quoted keyword
selectors retain expression parsing, preserving mixed assigned numeric variables
and quoted binders. Spec review caught that compatibility edge case in the first
correction; the assigned `k=0`, `[k,"not"]` regression is now checked exactly.
Test-only commit `8a379a275` adds single/double quoted and logical-selector coverage.

Final correction validation: 88 native named-subsystem checks, 212 worker checks,
538 notation checks, 116 subsystem checks and 249 TeX checks pass. Logs are
`keyword-native-final.log`, `keyword-corrected-final.json`, `keyword-notation.log`,
`keyword-subsystem.log`, and `keyword-tex.log`. The worker was rebuilt at
`8c07c7205`; `8a379a275` has identical product source. `keyword-provenance.json`
records exact revisions and binary hashes. These targeted regressions do not
replace the historical complete-suite record below or integrated CI.

All four keywords are tested bare, single/double quoted, in list/vector selectors
and in supported source TeX; multiple traced keyword labels and named/quoted
numeric binders are covered. Ordinary `not`, `and`, `or`, `xor` numeric selector
expressions retain their prior results. Complete expected matrices still derive
from the independent IBM mixture and product-state oracles.

Independent Spec review at `8c07c7205` reports zero outstanding findings after
the quoted-keyword correction. GUI Clipboard, integrated CI and release gates
remain open; none of these additional checks establishes those gates.

Implementation is reviewable on `codex/dev17-named-traces`, based on fetched
upstream `2fb33c4d435adaf3518b5c79da38392030c957ce`. This is not a released-artifact
claim. Product code was built at `fffb351a903c7138ac4a991cfcc488de8231cf10`;
`71159f2f1` changes only a native test. Later documentation commits do not change
the tested product. See [contract.md](contract.md) for semantics and independent
matrix expectations.

## Executed checks

All logs below are retained outside disposable checkouts at
`F:/src/libqalculate/cleanup-audit/dev17/`.

| Evidence | Result and boundary |
|---|---|
| `baseline.json` | Original named rejection and 16 exact numeric controls; released baseline, not this implementation. |
| `build-fixed.log`, `native-fixed-before-test-correction.log` | Full build and 79 registered tests: 77 passed, one existing thread test skipped, one test-only assertion failed. Distinct native/worker logs verified. |
| `native-control-character-failure.log`, `native-recheck.log` | Original failure retained. Calculator sanitizes control characters before translation, so the assertion was corrected to call `translateQuantum` directly. Failed-test recheck at `71159f2f1` passes all 62 native checks. This is a recheck, not another complete suite run. |
| `worker-fixed.json`, `native-fixed-worker.log` | 112/112 worker checks passed, including complete exact rational matrices and Copy-text re-entry. |
| `scope-probes-initial.json`, `scope-probes-fixed.json` | Original quoted-binder failure retained; six scope controls pass after protecting literal mapping labels. |
| `worker-initial.json`, `tex-label-spellings.json` | Original unsupported `\\mathsf{ancilla_2}` input retained. Correct indexed `\\mathsf{ancilla}_{2}` and plain `ancilla_2` pass. No claim that every TeX name spelling is supported. |
| `gui-session-only/result.txt` | 72 real application Calculate/session checks pass, including saved/reopened evaluated mappings. This supplementary driver reads the application's internal copy text: Windows Clipboard is explicitly NOT tested. |
| `gui-fixed`, `gui-retry`, `gui-diagnostic` | Full unchanged GUI Copy fixture fails because Windows denies clipboard access. Do not count these as GUI Copy passes. |
| `private-clipboard-probe.txt` | Child confirms private station/desktop; native OpenClipboard still returns error 5 and WPF returns 0x800401D0. |
| `preservation.json` | Root README hash and 41,752 pre-existing dist file size/timestamp records preserved. |

Worker SHA-256:
`8bc83389b29fd24ef4958a2d9d3a38db2392f066c2cbfda48eb84fc5d8638db1`.
The development GUI payload combines this worker with the released application
at `52c37a2abe8fce9770ad610f56bd5118a1d4bc39`, application SHA-256
`1803f0257983abb82bf1add484529e5c03e63d66bc4dca23d8533647ec4d8c2c`.
`development-payload.json` records paths and product-source hashes. It is not
a release package. GUI session-only provenance verifies both binaries after the
run. The four captures and saved `mapping.qsession` remain with that run.

The downloaded IBM-005 source body is retained as `IBM-005-source.html`, SHA-256
`bc7a9c17cdf89842354ac8ac516e14699c7940557f7879306fe88cc39144763c`.
Full original failing inputs remain in the baseline, initial worker and scope
reports. Source operator prefixes with explicit matrix adaptations do not
establish whole-lesson or notebook compatibility.

## Independent reviews

Standards review at `fffb351a9`: no documented-standard violations or mandatory
findings. One nonblocking duplication heuristic concerns dimension validation;
the existing numeric path was preserved to keep this change focused.
Spec review at the same revision: no outstanding implementation findings;
GUI clipboard, CI and release evidence remain separate completion gates.

## Unattended GUI gate

The user requires unattended builds without unlocking their desktop. The bounded
external experiment created a current-user-only private window station and
desktop, with no changes to WinSta0, lock policy, credentials or persistent ACLs.
Its clipboard probe still failed. These experimental helpers are evidence only,
not a supported runner or shipped product change. No elevation was performed,
and evidence does not establish that elevation alone would fix this restriction.

Proposed infrastructure: the main development agent should provision a dedicated
interactive Windows test environment (for example an isolated test VM), run the
unchanged GUI fixture there, and verify actual Copy/re-entry plus session reopening.
The environment must not require the user's workstation to be unlocked. Windows
documents [window stations and their per-station clipboards](https://learn.microsoft.com/en-us/windows/win32/winstation/window-stations)
and [clipboard access rights](https://learn.microsoft.com/en-us/windows/win32/winstation/window-station-security-and-access-rights);
our failed private-station experiment is not proof of a working unattended setup.

## Integration instructions

1. Integrate this branch's commits after the pinned base. Build-registration
   commits were supplied by the coordinator; avoid applying duplicate patches.
2. Reconcile AUD-01's separate numeric-token parenthesis-boundary fix in
   `QuantumNotation.cc`. DEV-17 does not include that independent fix. Preserve
   DEV-17 literal-label markers, binder protection and numeric selector handling.
3. Run `windows/build-native.sh` with the configured Python executable. Keep the
   native and worker test names distinct so Automake executes both.
4. Build/package the integrated application through the coordinator's release
   workflow. Run `windows/test-named-subsystems-gui.ps1` with fresh evidence,
   distribution path and exact worker revision in the dedicated GUI environment.
5. Obtain required CI and published-artifact evidence before marking DEV-17d
   or DEV-17 released. Keep IBM-005's remaining source coverage open.

Proposed central-checklist update (coordinator owns that file): mark DEV-17a/b/c
implemented with native/worker validation and link this evidence; overall status
partial pending real GUI Clipboard, integrated CI and release verification.
DEV-17d stays unchecked. Record the branch owner and integration revision without
changing IBM-005 to complete.

Retain the active DEV-17 checkout and `.tools/dev17-validation` until integration
and the outstanding GUI gate are resolved. They are current validation dependencies.
Before eventual disposal, preserve and verify unique commits/evidence under the
repository recovery rules. Root README/dist and retained DEV-13/DEV-16 work must
remain intact. No release or cleanup was performed by this branch.
