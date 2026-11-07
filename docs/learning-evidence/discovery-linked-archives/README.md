# Linked archive access observations

The initial IBM109/IBM114 snapshot below added two reviewed access observations after the historical [discovery reconciliation](../discovery-reconciliation/README.md). Its original inventory remains unchanged: 149 sources, 1,241 occurrences and 872 canonical targets, including twelve ZIP targets. At that snapshot, two targets had retained acquisition evidence and the other ten ZIP statuses remained unchanged. Both requirements remain **ambiguous**: access does not make either archive a mandatory dependency.

[index.json](index.json) binds exact source anchors, archive/member identities, four independent review receipts and retained external evidence. Large payloads and signed transport URLs are not copied into the repository. Original sources are pinned to Qiskit documentation revision `a500b17f8b1f156a6bba42ab11f90f3104cad6d4`.

## IBM109: example molecule notebook

Stable target `IBM-LINK-8109d15d2cbf413f` occurs in original IBM109 cell 26 at Unicode offsets [5, 108). The source links an example molecule notebook showing setup and Hamiltonians for several molecules. The retained anonymous HTTP 200 receipt binds a 2,807-byte ZIP, SHA-256 `1e252c4acd4daaa2e806531cc5ed7b9d0c11eb922982b601a2493581c12031ad`.

Its sole member, `linked-example-molecules-pyscf.ipynb`, is 13,897 bytes with eight cells: seven code and one Markdown. Independent reviews verified seven code cells parsed as Python syntax without execution. Six stored Cholesky residual output records are historical, not reproduced results. Imports include Matplotlib, NumPy, PySCF and Qiskit. A source comment names PySCF 2.5.0; other dependency versions are unpinned. Full dependency resolution, notebook execution and independent mathematical/chemistry validation remain pending; no physical-ground-state correctness is certified.

The prior collector attempt recorded HTTP 200 but failed with `AttributeError` after EOF and retained no payload. Its receipt is preserved separately. The successful packet lacks a complete redirect-hop chain and collector implementation; reviewed static evidence does not independently establish runtime deadline enforcement.

## IBM114: introductory lecture archive

Stable target `IBM-LINK-d700ecaa16f91cd4` occurs in original IBM114 cell 0 at Unicode offsets [2009, 2103). The source links the introductory lecture PDF and warns that static-image code snippets may become deprecated. The retained anonymous HTTP 200 receipt binds a 2,671,408-byte ZIP, SHA-256 `d1f9fbe4ead2b513c2cf5e792d1ff7330d4a6f6a78eed937141d23d44d1d42e9`.

The sole member, `1_utility_lecture_Invitation_to_Utility_era.pdf`, is 2,953,157 bytes, SHA-256 `42d5ad74acc707ced1f9ecd4e2f75585e19f1349b74eda48bd866c9287a4ef27`. Independent reviews checked ZIP metadata, bounded in-memory decompression, member hash/CRC and PDF 1.7 magic only. No PDF parser, page count, content extraction, rendering, diagram interpretation or mathematics validation is credited.

## Remaining acceptance

These later observations supplement the earlier reconciliation; its statement about twelve unchanged ZIP statuses remains historical. Retained receipts are evidence of the recorded requests, not a fresh availability guarantee. Neither observation proves equality with archive bytes available when the original lesson was authored. No notebook, SDK, native, GUI or release acceptance follows, and no whole-source checkbox is promoted. External paths retain historical spellings and hashes describe raw retained bytes; these repository text proposals use LF.

## Later IBM117/IBM118 access snapshot

The two later observations below bring the retained total to four of the original twelve ZIP targets. The remaining eight statuses are unchanged, not newly verified. Earlier twelve/ten counts above and in `historical_context` remain historical. No all-cell readiness or execution accounting is included in this update. The original inventory and stable IDs remain unchanged.

## Later observation: IBM117

Stable target `IBM-LINK-6560dbd3a8590886` occurs in original IBM117 Markdown cell 0, Unicode offsets [268, 362). The original source links an original lecture PDF and warns static code snippets may become deprecated. Topic labels come from that source, not inspection of the unread PDF.

The retained anonymous HTTP 200 receipt binds a 599,445-byte ZIP, SHA-256 `712da30eccd274cffc3d15201715b189a8dc334191eab7ddd54124a2c3abae44`. Its sole member, `4_utility_lecture_Grover.pdf`, is 638,209 bytes, SHA-256 `1fe702263df476f28cbb16506798f238d3a29a923281dfb4dc77535e89e9606b`. Independent Standards and Spec reviews verified archive/member metadata, bounded in-memory decompression, hash/CRC and PDF 1.7 magic only. No PDF parser, page count, content extraction, rendering, mathematics or notebook execution is credited. Requirement remains **ambiguous**; no mandatory execution dependency or historical byte equality is inferred.

## Later observation: IBM118

Stable target `IBM-LINK-7cca562ac9e386c3` occurs in original IBM118 Markdown cell 0, Unicode offsets [387, 481). The original source links an original lecture PDF and warns static code snippets may become deprecated. Topic labels come from that source, not inspection of the unread PDF.

The retained anonymous HTTP 200 receipt binds a 948,181-byte ZIP, SHA-256 `001d0bdc042d352974a95d38739cc6563243226e6ccfecf208cb31207f9ce05c`. Its sole member, `5_utility_lecture_QPE.pdf`, is 1,317,790 bytes, SHA-256 `9a9b803442584b765faefd31c696c170141bb5987a84bbf28c884788d1565554`. Independent Standards and Spec reviews verified archive/member metadata, bounded in-memory decompression, hash/CRC and PDF 1.7 magic only. No PDF parser, page count, content extraction, rendering, mathematics or notebook execution is credited. Requirement remains **ambiguous**; no mandatory execution dependency or historical byte equality is inferred.

The retained downloader read deadline is checked around socket reads; it is not an external wall-clock watchdog. Review of these acquisitions does not certify a general downloader. Neither topic relevance nor a PDF signature establishes unread PDF content or whole-notebook acceptance.

## Later owner-accepted IBM115 access snapshot

The later IBM115 observation brings the retained total to **five of the original twelve ZIP targets**. Seven remain unattempted within the pinned retained-evidence scope. The earlier four/eight snapshot and accepted eight-target inventory are historical and remain unchanged; neither establishes current access restrictions for the remaining targets. Original inventory entries and stable IDs are preserved.

Stable target `IBM-LINK-1cee1fa9085dc5f2` occurs in original IBM115 Markdown cell 0 at Unicode codepoint offsets [247, 329), labelled “here”. The pinned a500 source links the original bits, gates, and circuits lecture PDF and warns that static-image code snippets may become deprecated. Requirement remains **ambiguous**; access and topic relevance do not establish a mandatory dependency.

The accepted anonymous HTTP 200 observation followed one HTTPS redirect. The retained ZIP is 284,339 bytes, SHA-256 `bb7e8da2f2a9b62bc603eb1b67f67ea533674a5978fa3690196de7b12008d76d`. Its sole member, `2_utility_lecture_gate_circuit_measurement.pdf`, is 343,345 bytes, SHA-256 `d98f2f6cc900c3e0b3a6ca694184c7b41661663b80ce0058b1a57708063325c2`, CRC32 `97d9889f`, with PDF 1.7 magic. Independent final Standards and Spec reviews verified the exact seven-file actual evidence set, bounded in-memory member decompression, hash/CRC/magic and input preservation. No PDF parser, content extraction, page count, rendering, diagram interpretation or mathematical validation is credited.

Owner acceptance binds the reviewed collector, DATA binding, issued ticket, exclusive staging receipt, complete successful supervisor evidence and actual raw-file hashes. The collector state was `acquired_and_archive_metadata_validated`; exit0 alone would not suffice because a caught acquisition failure can also return normally. The 60-second phase/64 KiB capture envelope is distinct from the collector’s 15-second socket/30-second cooperative read limits and does not claim a hard deadline for the entire invocation including audits and cleanup.

The appended `ibm115_access_snapshot` in [index.json](index.json) contains sanitized status/counts and external evidence paths/hashes. Payloads and signed redirect/header/error values remain outside the repository. This records the accepted request only, not current/future availability or equality with archive bytes from the lesson’s original publication. PDF content, lesson execution and whole-source acceptance remain open.

## Later owner-accepted IBM116 access snapshot

The accepted IBM116 observation brings the retained total to **six of the original twelve ZIP targets**. Six remain unattempted within the pinned retained-evidence scope. The IBM115 five-of-twelve snapshot and all earlier counts, observations and inventories remain historical and unchanged. No new access restriction or current availability conclusion is made for the remaining targets.

Stable target `IBM-LINK-fbb823b8d820b498` occurs in original IBM116 Markdown cell 0 at Unicode codepoint offsets [299, 393), labelled “Download the pdf”. The pinned a500 source concerns quantum teleportation and superdense coding, links the original lecture PDF and warns that static-image code snippets may become deprecated. Requirement remains **ambiguous**; neither successful access nor topic relevance makes the archive mandatory.

The retained anonymous HTTP 200 observation followed one HTTPS redirect. Its 583,556-byte ZIP has SHA-256 `72aac9aee30f951f56d1a44d8077607b204563131f5521a5190dcd5183860896`. The sole member, `3_utility_lecture_teleportation.pdf`, is 681,482 bytes, SHA-256 `02980390af86795623921b905290d2e3ad4ce1c82d3c0aacb56de63f4ffb7731`, CRC32 `1da5f0cd`, with PDF 1.7 magic. Final independent Standards and Spec reviews passed with no correctness findings, verifying the seven-file actual evidence set and bounded ZIP member decompression/hash/CRC/magic. No PDF parser, content extraction, rendering, page count, diagram interpretation or mathematical validation is credited.

Owner acceptance binds the accepted source, DATA, issued ticket, staging, complete successful supervisor receipt and verified raw acquisition evidence. The collector reached `acquired_and_archive_metadata_validated`; exit0 alone would not establish success. The accepted observation is finite evidence of that request, not current/future availability or historical archive-byte equality.

A separate **review-process limitation** is retained by the owner: both actual-review agents accidentally emitted signed transport URL text to tool output while treating redirect_hops as numeric. That output path was stopped; frozen artifacts were unchanged. This proposal and the review reports do not reproduce those signed values. Finite correctness acceptance does not erase the disclosure incident. Subsequent handling uses an explicit safe scalar allowlist and does not print raw redirects, headers, final URLs, errors or complete sensitive receipts.

The appended `ibm116_access_snapshot` in [index.json](index.json) records sanitized status/counts and external evidence paths/hashes, including the provisional and final owner receipts. Payloads and raw signed transport receipts are not copied into the repository. PDF content, lesson execution and whole-source acceptance remain open.

## Later accepted IBM122 part 1 access snapshot

The independently reviewed IBM122 part 1 observation brings the retained total to **seven of the original twelve ZIP targets**. Five remain unattempted within the pinned retained-evidence scope, including IBM122 part 2. All earlier snapshots, counts and observations remain historical and unchanged. No restriction or current availability conclusion is inferred for unattempted targets.

Stable target `IBM-LINK-9d7e7b5ba683260b` occurs in original IBM122 hardware notebook Markdown cell 0 at Unicode codepoint offsets [379, 472), labeled “Download part 1”. The original source explicitly splits its lecture PDF into two parts and warns that static-image code may become deprecated. This observation selects only part 1. Requirement remains **ambiguous**.

The retained anonymous HTTP 200 acquisition used one initial request and no retry. Its 1,751,551-byte ZIP has SHA-256 `625213940d20e06c9238d2c3ea87a9dce3c143b9f18c35b2c99848d7871c475a`. The sole member, `9_UTokyo_hardware_1.pdf`, is 1,894,818 bytes (1,751,335 compressed), SHA-256 `863d74c26d050479ff9549c77ae10b85f8e29fe2c652a3aeaaecd7db695a3453`, CRC32 `bcfe8df4`, with PDF 1.7 magic. Independent final Standards and Spec reviews returned zero findings, verifying all seven actual evidence files, 1,993 preserved input files, clean containment, complete receipts and bounded ZIP member hash/CRC/magic.

The collector reached `acquired_and_archive_metadata_validated`; exit0 alone is insufficient. The unchanged60-second phase/64KiB capture bounds remain distinct from collector15-second socket/30-second cooperative-read limits and do not guarantee total invocation time including audits and cleanup. No PDF content parser, extraction, rendering, page count, diagram interpretation or mathematical validation is credited.

The appended `ibm122_part1_access_snapshot` in [index.json](index.json) retains sanitized status/counts and external evidence pins. Signed transport URLs, headers, errors, raw captures and payloads are not copied here. This is finite access and archive-integrity evidence, not historical archive equality, current/future availability or whole-source completion.
