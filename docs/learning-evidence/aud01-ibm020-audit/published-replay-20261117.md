# IBM-020 finite audit on published checkpoint c5a456cd

On 2026-11-17, the preserved 186-case probe was replayed against the verified published `checkpoint-c5a456cd` worker. The [receipt](published-replay-20261117.json) binds source, probe, fixture and binary hashes and indexes raw external evidence. The seven imported historical audit files were checked against the exact Git bytes used for this replay before adding this reconciliation. Original fixtures and historical outcomes remain unchanged.

## Current finite results

All 164 primary exact-value cases and all ten context cases passed, including the two formerly failing scalar-set adaptations. Their 174 ordinary canonical numeric copies also passed. Two deferred contexts remain retained. These are finite expression checks, not 174 literal lesson examples or whole-source acceptance.

The historical probe returned exit 1 because five original-literal observations changed. That exit and the original `unexpected_failure` labels are retained; they do not establish five current mathematical regressions:

| Literal | Current result | Interpretation |
| --- | --- | --- |
| `g1-m02-literal` | Exact list `[1,1]` for two Hadamard equalities | Newly accepted literal derivation. Authored negative control changes the first equation and returns `[0,1]`; this checks the equality result is not unconditional. |
| `literal-M11` | Unsupported `\cdots`, byte 532 | Still unsupported; historical failure was an invalid summation index. |
| `literal-M18` | Unsupported `\cdots`, byte 105 | Still unsupported; diagnostic location differs from the earlier observation. |
| `literal-M19` | Unsupported `\cdots`, byte 136 | Still unsupported; diagnostic location differs from the earlier observation. |
| `literal-M23` | Unsupported `\cdots`, byte 86 | Still unsupported; diagnostic location differs from the earlier observation. |

Four other original literals retain their recorded rejections, and one retains its deferred observation. Literal failures are not converted to mathematical passes. Unrestricted indexed families and the complete written derivations remain open.

## Copy route and failed control

The successful multiline result produces TeX `gathered` copy text. Sending that directly through ordinary evaluation rejects it. The failed ordinary-route attempt is retained in `literal-copy-controls.json`; it must not be reported as a passing numeric copy. The documented Quantum-mode request (`quantum:` plus that text) returns the same display result. Existing multiline worker tests and the application's Quantum-mode request path use this route. This is worker protocol evidence, not actual GUI Clipboard or saved-session acceptance.

## Reproduction and remaining scope

The scoped `.gitattributes` keeps Python and JSON files at LF in normal checkouts so their bytes match the recorded Git blobs.

Run the unchanged `probe.py` with the pinned source, explicit published worker and definitions directory, and a fresh output directory. The historical probe is expected to return 1 for the five observation changes above; inspect exact values and raw results instead of treating exit status alone as coverage. Definitions were hashed before and after the replay and were unchanged. The external record retains raw stdout/stderr, fixture and script hashes, controls and per-case results. The repository receipt indexes these files; a repository-only clone lacks that retained raw evidence and published binary.

The tested source is the pinned IBM-020 notebook, not a later upstream revision. Eight Python cells and the remainder's mathematical occurrences are inventoried but not executed by this finite probe. Notebook execution, figures/media, remaining literal notation, Bernstein–Vazirani coverage, general families and source-specific GUI/session workflows require separate evidence. IBM-020 and AUD-01 stay unchecked.
