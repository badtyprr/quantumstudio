# AUD02 retained dependency classification — 2026-11-04

This increment classifies the surrounding source context of links in 47 retained non-notebook assets at Qiskit/documentation revision `a500b17f8b1f156a6bba42ab11f90f3104cad6d4`. It builds on the [dated discovery expansion](discovery-expansion-20261104.md), without changing its historical link count or the original source inventory. The [machine record](dependency-classification.json) supplies each asset's pinned source URL, exact SHA256/Git blob/size, review state, every classified link's source location and paraphrased rationale, target mapping and unresolved work.

All 47 files were read and independently rehashed: 18 overviews, 12 exam descriptions and 17 metadata files. They contain 333 of the earlier 485 lexical link occurrences. The remaining 152 occurrences belong to the separate IBM-138 Error correction II notebook and are not context-classified here. Known roles for links do not establish acceptance of their target contents.

| Classified role | Occurrences | Meaning |
|---|---:|---|
| Navigation | 221 | TOC, preview index, series-course or exam-description links |
| Media | 41 | Image references; appearance/content/accessibility not inspected |
| Optional | 59 | Recommended background/setup, surveys, privacy or instructor resources |
| Source-required, conditional | 12 | External exam required only to earn the optional course badge |

These are occurrence counts, not unique targets, lessons completed or a percentage of the goal. All 188 known source rows remain unchecked. No additional lesson ID is introduced and DISC-01/02 remain open.

## Source context and mapping

The TOC lesson/module destinations map to 150 existing IDs: IBM-001–138 and MOD-001–012. Existing overview/exam destinations map to stable IBM-ASSET keys; other references retain their IBM-LINK keys. IBM-138 was already adopted by the preceding expansion. Its TOC mapping now resolves to that ID rather than the earlier pending lesson key; no notebook acceptance follows. The three later-added qBraid IDs remain untouched.

Series membership and TOC ordering are navigation evidence, not inferred mandatory prerequisites. The Basics overview recommends subject familiarity and offers five alternative background sources; it does not require a particular textbook. Project leadership explicitly has no technical prerequisite and recommends Business Foundations. HPC explicitly calls Basics optional. Diagonalization suggests Basics for deeper background, while the practical course recommends Basics and two books. The VQE overview assumes Qiskit and some quantum-mechanics/operator knowledge, but no previous VQE experience; its Basics link is merely helpful. Topic assumptions are recorded separately from linked obligations.

HPC and diagonalization recommend local environment setup through `/docs/guides/`, stable key `IBM-LINK-9340b5f702ae2895`. Their prerequisite wording sits within a recommendation. This record preserves that strength as recommended setup, without inventing mandatory guide contents or current versions. The guide itself was not inspected. Classroom module overviews recommend small-matrix linear algebra/Python and initial instructor/group support; the instructor answer-key request is optional and unsubmitted.

All 12 exam descriptions state 20 questions, a 16-answer pass threshold and temporary lock after two unsuccessful attempts. These are dated source statements, not verified current rules. Completing reading/activities precedes the optional badging route, but actual activities/questions are not present in the descriptions. Relative maintenance notices do not establish current unavailability or an authentication requirement. No exam attempt, registration, survey submission or badge action was performed.

Video flags and prose mentioning video delivery do not enumerate playable resources in these files. Those player/component/media dependencies remain unknown. The 12 LaunchExamButton references identify hrefs only; implementation/rendered behavior and questions remain unreviewed. Hero/badge image roles come from Markdown/alt text, not inspected images. Referenced PDFs/books were not read. No production-page, current quota or provider-access claim follows from source text alone.

The preview index explicitly describes an open-source preview and repeats Tools for quantum advantage. It cannot replace production learning-path enumeration. The tools course's exam-under-development and lesson time-release statements are dated. The utility-scale overview's 14 lesson/lab event-replay description still requires per-lesson resource inventory. Source inconsistencies are preserved: VQE frontmatter 5 hours versus narrative 6–10, and the variational-design exam description mentioning chemistry despite its own title/body.

## Separate metadata additions

Recursive inspection of all 17 TOCs identifies **17 parentUrl occurrences**, not 19: 13 point to `/learning/courses`, two to `/learning`, two to `/learning/modules`. The earlier `toc-url` extractor omitted these fields. They are separately recorded as navigation additions with local stable keys and field locations where available; the historical 485 occurrence count remains unchanged.

The `/learning` target can be associated with the retained preview-index asset. This is repository identity mapping, not proof that production navigation renders the same content. Parent links add neither lesson rows nor acceptance credit.

## Remaining acceptance and retention

- Audit every existing lesson/module on its own formulas, code, interpretation, runtime and media requirements. TOC mapping closes none.
- Pin and inspect the recommended setup guide before deriving dependent runtime contracts; do not infer content from its link.
- Resolve actual video/player and image dependencies, including source identity and visual/accessibility checks, through separately scoped work.
- Keep questions, answer keys and current access unverified. Any later permitted viewing must avoid consuming attempts, registrations or submissions.
- Audit the separate IBM-138 notebook and its 152 lexical occurrences independently.
- Preserve the historical 485 count when reconciling the 17 new parent fields, and continue production path/catalog/media/tutorial discovery.

Raw snapshots/manifests remain in `cleanup-audit/notebook-lane-20261104/discovery-expansion/`. The two source audits and their hashes are recorded under `cleanup-audit/coordinator-20261104/` in the companion JSON. Those external snapshots are required to reproduce retained-byte checks and are not shipped by this documentation increment. Pinned repository links identify reviewed bytes, not future availability.

This is finite retained-context classification, not completion of DISC-01/02, AUD-03/04, any source row or any release. No remote content or account/provider actions were used for this increment. The companion JSON preserves the per-asset classifications and unresolved acceptance work behind this summary.
