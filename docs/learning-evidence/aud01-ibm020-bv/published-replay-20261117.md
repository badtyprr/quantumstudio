# IBM-020 Bernstein–Vazirani published-worker replay

The unchanged 159-request finite probe was replayed on 2026-11-17 against the verified published checkpoint `c5a456cde595b3e1211cfc51a233dea511322a56` worker. All historical observations reproduced: 81 planned exact values and 32 separately disclosed compact-form values passed, including 113 ordinary canonical copies. Fourteen original literal forms still reject; 32 expanded double sums still hit the expression-complexity guard. Exit status was zero because the historical observations reproduced, not because all requests succeeded.

The [receipt](published-replay-20261117.json) binds worker, original notebook, probe, fixtures and definitions, and indexes the raw external evidence. Worker and definition hashes remained unchanged. Source/probe Git bytes were checked against the preserved integration revision. No product code or parser budget changed for this replay.

The source's four-bit secret `1011` and authored extension to the other 15 secrets remain distinct. These are finite native adaptations; the pinned notebook's original SDK code was not executed by this probe. The compact expressions do not replace or close the failed expanded forms. General widths, original literal derivations, notebook/media and GUI/session acceptance remain open. IBM-020 and AUD-01 must remain unchecked.

This receipt concerns the unmodified published worker. The separately discovered flat-arithmetic stack crash and its proposed linker fix are a different validation stream and are not claimed resolved by this replay. Raw evidence is retained under `cleanup-audit/learning-coverage-20261117/ibm020-bv-published-replay` outside disposable clones; repository-only consumers need that evidence or a new replay.
