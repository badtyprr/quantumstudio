# DEV-16 released-evidence reconciliation

Date: 2026-11-03 (America/Los_Angeles). Documentation-only increment agreed with
the main development coordinator. Review base:
`02d5ca3f5713385818e80db15b1a58e3b518e569` (fetched `origin/master`).
No parser, compiler, editor, serialization, build or central-checklist changes.

## Decision and evidence boundary

Correct QB-004's stale claim that classical module export awaits release.
Do not change any completion checkbox. REL-08 shipped exporter prerequisites;
REL-09 shipped the exporter and observable module acceptance. Neither completes
the notebook. This increment resolves that reporting discrepancy, not the
remaining implementation or cross-editor acceptance work.

Original notebook: qBraid/qbraid-lab-demo revision
`86787e1ba372facc224f925189755e69c479828b`,
`qBraid-Algorithms/bernstein_vazirani.ipynb`, notebook SHA-256
`9a9ed236328a272a4858f5ac6af1019c8857eeee4fbf41544bf01bb140d34cce`.
This provenance is inherited from the original QB-004 audit, not a fresh notebook
execution or download. Unchanged generated fixtures are under
`windows/fixtures/qb004/`; the oracle generator input is `111`, the algorithm
input is `011`. Preserve their local `s`, `n`, loop variables and headers.
Their exact hashes are in [verification.json](verification.json).

## Requirement-by-requirement gap list

| Requirement | Evidence already present | Remaining limit / disposition |
| --- | --- | --- |
| Resolve local dependencies | DEV-16a–c, REL-04–07; file-import/source-bundle tests, explicit module-header option | Shipped; do not reimplement. Strict mode and adapted generated-module mode remain distinct. |
| Both original modules | REL-09 classical module and numerical composer reports below, fixture hashes unchanged | Covers generated modules, not execution of all 33 notebook cells. |
| Nested includes, spaces and Unicode | Classical export fixture graph: BOM `main κ.qasm` → `wrapper.qasm` → `nested modules/{oracle,bernvaz}.qasm`, inside spaced Unicode directories | Numerical composer module suite uses direct includes; this report does not infer full nested composer coverage from shared compiler tests. |
| Preserve original sources | Both suites compare original UTF-8/BOM bytes and SHA-256, retaining snapshots through edits/history | Shipped scoped evidence; adapters do not rewrite fixtures. |
| Standalone export/reimport | REL-06 composer route, repeated in REL-09; REL-09 classical original and edited exports recompiled by frozen importer | Composer compares explicit reset prefix and circuit structure; classical route additionally checks independently expected outputs. |
| Numerical equivalence | Classical six preparations × original/edited = 12 nonempty expected results; 24 exact/sample checks | No independent nested-module numerical-composer output matrix established by the examined suite. Structural equality is useful but narrower. |
| Edits and history | Composer undo/edit/save/reopen; classical prepended X, undo and saved source checks | Finite hooks, not arbitrary editing equivalence. |
| Saved state | Editor `.qcircuit` source-document save/reopen in both suites | Complete source-specific application `.qsession` restoration is not established here. Clarify/assign this acceptance separately; do not silently equate the two formats. |
| Failure recovery | REL-09 export rejection preserves destination/source/history; source-workflow audit checks changed/missing dependencies, failed atomic reimport and undo of success | Generic source-workflow evidence is not every QB-004 × editor × failure combination. Missing matrix entries remain unverified, not proven product defects. |
| Diagnostic attribution | REL-07 maps parser/preflight errors; retained DEV-16d patch adds bounded assignment/range spans | Four retained unmapped probes and other later-emission paths remain. No DEV-16d closure. |
| Clipboard / GUI | Historical editor hooks and recorded captures; release record says captures inspected | No fresh GUI run or visual review, no actual Clipboard test. Worker and internal-state checks cannot supply this acceptance. |
| Notebook / provider | Original partial cell inventory in QB-004 | DEV-13/15; excluded from this increment. |

## Released evidence and verification

REL-08: `0ee22bfea53c29ffdbc8b4662ec3494a810d547f`, prerequisite PRs
#318–323; retained release record reports 84 audit groups and ZIP SHA-256
`b2512eb4fdbc76c2b3fa98328884bbbd0c2ecab84b46bc71e5dd5360fce97ecd`.
This increment did not rehash the REL-08 package.

REL-09: `6f0790927533e9d5007a544a24a02597a74ff5b6`, PRs #324–327.
[Export report](rel09-export.json), [module report](rel09-modules.json) and
[composer report](rel09-composer.json) are byte-for-byte copies of retained
historical audit JSON, including their original paths. Historical deleted-clone
paths are provenance, not instructions to recreate or read that clone.
The release record and full package log report 85 passing groups, 474 inspected
captures and the final published ZIP. The export audit accounts for 21 captures
(18 module plus three generic exporter); the composer audit accounts for nine.
These are historical inspection claims, not new inspections.

[verification.json](verification.json) records this increment's checks:
340 retained REL-09 payload hashes match the build manifest, the ZIP matches
`2bfd30346932843aec49e7f55302637186d11ae720360adc764971a0f749337e`,
and both fixture hashes match retained module inputs. Release binaries:

| Binary | SHA-256 |
| --- | --- |
| GUI | `0cfdcf497fe0ad2883f5b98aa914ded642a009514c39cc60809747b4f4a35947` |
| Worker | `162f76124a32ec0f6d4356f564dfc884117385e48d7b14c8f9fdb28b19db5c00` |
| Importer | `66a2ec429d2c7bcbeeae75fb3a64ab24f93a6b589ad7527e72ace31973efeacb` |

The original oracle applies CX from each data wire to ancilla. For input integer
v with ancilla zero, data is unchanged and ancilla is parity(v). The export
harness assigns result[0]=ancilla and result[1..3]=q2,q1,q0; high-to-low display
is therefore reversed three-bit v followed by parity. Prepending X(q0) replaces
v by v xor 1. The algorithm fixture uses s=6 and leaves data q2q1q0=110;
its selected high-to-low display is 011, or 111 after the prepended X. Ancilla
is deliberately unobserved for this phase-kickback circuit. The early-end
oracle must retain observations rather than execute the later result=0.
All 12 retained expected strings were checked against these independent rules.
This validates the expected strings, not a new execution of the exported code.

## Retention and integration

Full raw results, original wrappers/exports/saved documents/captures, release
logs, manifests and prior handoffs were copied without alteration to
`F:/src/libqalculate/cleanup-audit/dev16-reconcile-20261103/`.
Its `verification.json` lists 141 copied file records and hashes; `reconcile.py`
records the exact verification procedure. Nothing was deleted. Original failing
inputs in QB-004 and retained DEV-16d `remaining-probes.json` remain intact.

Retained DEV-16d checkout `.tools/dev16d-diagnostics-20261101-a` at
`114c3d8194359ad9b7fc260e0e3e75d3b610b3d7` has untracked build/cache files.
Its handoff calls it unreleased; it is not adopted by this increment. Retained
DEV-13 checkout `.tools/dev13-aud02-20261101-b6e2` at
`026a7ab60c1c6d9e41cc6574c8bca2bdddb42386` was clean. Both were inspected and
left unchanged. Root README/untracked work and dirty DEV-17 integration checkout
were preserved. No base was selected from those dirty checkouts.

Coordinator owns central checklist/build/release integration. Proposed wording:
keep DEV-16, DEV-16e and QB-004 unchecked; replace QB-004's obsolete “remaining
editor export/equivalence work” with “released module export/reimport; remaining
cross-editor source-specific acceptance in DEV-16; notebook/cloud in DEV-13/15”.
Link this reconciliation from DEV-16e. No status upgrade is proposed.

After independent Standards and Spec review, cherry-pick this documentation
commit onto the coordinator's intended integration base. No build or publication
is required for this evidence-only correction. Do not cherry-pick retained DEV-16d
or DEV-13 commits implicitly. Future GUI-dependent matrix work must be scoped
with the unattended-GUI agent; no GUI resources were used by this increment.
