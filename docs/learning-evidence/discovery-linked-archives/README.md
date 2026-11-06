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
