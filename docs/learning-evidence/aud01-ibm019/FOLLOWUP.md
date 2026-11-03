# AUD-01 P1 follow-up — 2026-11-02

The user requested completion of the remaining parser defect and fallback-clone cleanup. The historical ledger and original failing runs remain unchanged. This follow-up is authoritative for the new work; it does not change what released 52c37a2a did in the original audit.

## Fix and ownership

The coordinator and DEV-17 owner explicitly allocated the single numeric-token/function-call dispatch condition in `QuantumNotation.cc::Parser::atom()` to this workstream. DEV-17's subsystem-label parsing, trace routing and scope metadata were not edited. Its frozen build was not modified.

Root cause: the parser consumed a numeric token followed by parentheses as a function call. Inside a power, this swallowed an adjacent multiplicative factor into the exponent. The defect is also present without TeX sizing commands. Numeric tokens now bypass the function-call branch; the existing product parser handles their adjacent factors at the correct precedence. Named function calls retain their route.

Product fix: `ed03a4607015dd3281f88eaf3168657621d9b29d`.
Final acceptance-script correction: `33e6bf8054ad5d5374960fb65b9e86119c75a528`.
Final independent Standards and Spec reviews at 33e6bf805: **zero actionable findings on each axis**.

## Verified results

| Check | Baseline | Corrected parser |
|---|---:|---:|
| Numeric boundaries, signs, decimal/scientific/binary literals, grouped/chained/rational powers, implicit products, actual function calls | 19/30 | 30/30 |
| Exact Copy/re-entry for the corrected boundary results | — | 30/30 |
| Original finite audit fixtures, unchanged inputs and expectations | historical 65/65 | 65/65 |
| Original M10 source derivation, unchanged | incorrect expressions | two true statements |
| Existing native notation suite, unchanged | not rerun in this follow-up | 538 passed |

The baseline and corrected boundary checks used separately compiled parsers and the **same retained released evaluator**. Every coefficient, sign, exactness flag and matrix shape is checked. The original M10 fragment translates to two exact true statements, represented as `vector(1,1)` by the ordinary evaluator. This does not test GUI multiline rendering.

The native notation suite compiles the actual corrected parser and unchanged existing tests. GCC 16.2.0, C++17, `-O2`, static linkage. All compile commands, source hashes, tool version and binary hashes are preserved in external `parser-build/build-manifest.json`.

Corrected parser SHA-256: `317f86df3c0a4eddcab89427dccdc0d7eed78169bdbbd1f9630f5803662b00bb`.
Evaluator revision: `52c37a2abe8fce9770ad610f56bd5118a1d4bc39`.
Evaluator SHA-256: `ea0467a5ca5ce58d043c08bed80043361aca4305a5bb92d029781e4035e76913`.

This is **not an integrated worker build or a new release**. The coordinator owns integrated worker validation, build/distribution registration, integration and any release. The standalone route is explicitly identified in each result's `evaluator_input`.

## Reproduction and handoff

Evidence root: `F:/src/libqalculate/cleanup-audit/aud01-ibm019-analysis-20261102`.

- `followup-red.json`: original 18-case reproduction, 9 failed.
- `followup-red-translated.json`: final 30-case baseline, 11 failed.
- `followup-green-final.json`: corrected 30 cases and all Copy/re-entry outputs.
- `followup-65-fixtures-final.json`: unchanged audit fixture replay.
- `followup-M10-final.json`: exact original source and true/true result.
- `parser-build/build-validation.py`: baseline/fixed parser and existing native-suite build commands.
- `replay-fixed.py`: verifies the original fixture list is unchanged, then replays all 65 and M10.
- `followup-reviews-final.json`, `followup-manifest.json`: final review and provenance records.

Integrated acceptance command (coordinator; omit `--translator`):

```powershell
python -X utf8 docs/learning-evidence/aud01-ibm019/exponent-regression.py --worker <integrated-worker.exe> --definitions <matching-data-directory> --output <evidence>/numeric-boundary-integrated.json
```

The script imports `Q` and `parse_cell` from the unchanged sibling `run.py`; distribute both. For standalone reproduction, append `--translator <evidence-root>/parser-build/fixed-parser.exe` and use released 52c37a2a as the evaluator. Run `python -X utf8 <evidence-root>/replay-fixed.py` for the full finite-fixture and original-derivation replay. Its recorded local paths are intentional; no source download or floating dependency is needed.

Validation was coordinated with the performance owner: the bounded run was authorized during DEV-17's already non-quiet tests. Completion was explicitly reported; further compiler/worker jobs were held for the reserved phase timings.

Initial harness issues are preserved separately. An unoptimized standalone suite exhausted the default stack (`0xc00000fd`); the standard repository `-O2` configuration passed all 538 tests. The first comparison helper did not recognize the multiplication glyph in `7·sqrt(2)`, and initially expected matrix cells for M10's ordinary vector result. Those were harness representation errors, corrected without modifying the product fix or the original audit evidence.

## Cleanup remains policy-blocked

The user renewed authorization to finish cleanup. Automatic approval review still rejected the native PowerShell removal before execution, stating only **“blocked by policy.”** No alternative deletion route was attempted.

The retained fallback clone is `F:/src/libqalculate/.tools/aud01-ibm019-analysis`. Fresh read-only verification found no staged, unstaged or untracked changes; every ref points to baseline `2fb33c4d435adaf3518b5c79da38392030c957ce`, verified present in the main repository. See `cleanup-followup.json`. The managed review checkout and verified recovery bundle remain preserved. A user action or policy change is required to remove the redundant clone.

## Checklist proposal addendum

Keep IBM-019 and AUD-01 unchecked. Note that the identified unbraced-exponent bug has a reviewed fix and passing standalone validation, with integrated worker/release status pending coordinator verification. Preserve the original literal-support findings and every other source boundary. Neither the Boolean-function semantics gap nor whole-lesson coverage was added to this fix's scope.
