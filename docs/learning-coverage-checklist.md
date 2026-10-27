# Learning coverage and development priorities

Updated: 2026-10-26. This is the decision queue for the full IBM Quantum Learning and qBraid goal, not a reduction of its scope.

## Choose the next development task

P0 = broken release, data loss or incorrect established behavior: stop feature work and repair it. P1 = current algorithm workflows and shared prerequisites. P2 = broader mathematical and notebook coverage. P3 = external runtime/compiler integrations. Priority reflects the requested emphasis on circuits and algorithms; it is editable, not a promise about effort.

Effort is a rough relative size: S = one scoped change; M = several changes; L = an epic that must be split after a source reproduction. No calendar estimate is implied. Dependencies name prerequisites, not automatic proof that every linked lesson needs that feature.

Recommended order: DEV-05a–d shipped in REL-10 and DEV-05e shipped in REL-11. Run AUD-01 and AUD-02 alongside code work, then choose the first ready P1 item supported by a failing source fixture among the remaining DEV-08 work. The demonstrated QB-005 inverse-QFT exact-execution and large-result display gap is resolved in REL-13; do not prioritize its historical timeout as unfinished implementation. Its remaining notebook/provider acceptance stays open. Compiler-resolved arrays shipped in REL-14. Scalar runtime subroutine arguments and locals shipped in REL-16, bit arguments/local storage in REL-17, and returned values/early exits in REL-18. Bounded DEV-08b4 source acceptance shipped in REL-19: concatenated measured parity and separately audited unchanged qBraid controls. Fixed quantum-register parameters shipped in REL-20 / [#370](https://github.com/badtyprr/quantumstudio/pull/370). Bounded constant widths, bounded literal-range quantum-call loop indices, and declared orthonormal bases shipped in REL-21. DEV-03 is complete; dynamic alias/subroutine binding, runtime arrays and remaining subroutine parameter forms remain separate work. DEV-06 runtime gate parameters, numeric types and the selected unchanged-source audit shipped in REL-22. DEV-07 bounded runtime wire selection shipped in REL-23; the next work is the remaining DEV-08 constructs. Promote newly discovered widespread failures above isolated features.

| ID | Priority | Size | State | Depends on | Work |
|---|---|---|---|---|---|
| [DEV-01](#dev-01) | P1 | S | Released | None | Compact bound-index products |
| [DEV-02](#dev-02) | P1 | L | Released | DEV-01 | Domain-preserving symbolic Fourier expansion |
| [DEV-03](#dev-03) | P1 | L | Released | None | Declared orthonormal bases |
| [DEV-04](#dev-04) | P1 | L | Released | DEV-03 | Symbolic operator assumptions and identities |
| [DEV-05](#dev-05) | P1 | M | Partial | None | Register dimensions and symbolic bit strings |
| [DEV-06](#dev-06) | P1 | L | Released | None | Runtime gate parameters |
| [DEV-07](#dev-07) | P1 | L | Released | None | Dynamic wire indexing |
| [DEV-08](#dev-08) | P1 | L | Partial; scalar, bit and return calls released through REL-18 | DEV-07 for dynamic indexing | Array/set iteration and subroutine-local storage |
| [DEV-09](#dev-09) | P2 | L | Partial | DEV-03 | Symbolic ensembles, instruments and POVMs |
| [DEV-10](#dev-10) | P2 | L | Partial | DEV-05 | Symbolic domains, sets and indexed families |
| [DEV-11](#dev-11) | P2 | L | Partial | DEV-04 | Error-correction lesson operations |
| [DEV-12](#dev-12) | P2 | L | Partial | DEV-04 | Variational and numerical operator coverage |
| [DEV-13](#dev-13) | P2 | L | Discovery needed | AUD-02 | Python/SDK notebook execution route |
| [DEV-14](#dev-14) | P3 | L | Not implemented | DEV-13 | QIR and CUDA-Q compatibility |
| [DEV-15](#dev-15) | P3 | L | Not implemented | DEV-13 | Cloud/provider and pulse workflows |
| [DEV-16](#dev-16) | P1 | M | Partial | None | Local OpenQASM include dependencies |
| [DEV-17](#dev-17) | P2 | M | Not implemented | None; explicit subsystem mapping required | Named subsystem partial traces |
| [AUD-01](#aud-01) | P1 | M | Pending | None | Audit algorithms first |
| [AUD-02](#aud-02) | P1 | M | Pending | None | Complete source discovery |
| [AUD-03](#aud-03) | P2 | M | Pending | AUD-01 | Audit remaining mathematical lessons |
| [AUD-04](#aud-04) | P2 | M | Pending | AUD-02 | Audit remaining notebooks end to end |

## Release queue

- [x] REL-01: Release `92f80696`: 70 packaged audit groups, 262 verified visual captures, 340 manifest files. ZIP SHA-256 `d621438711c3ff6a58f819b3c3d559db547b187d3b2c5f5f099e87c71bdb3323`.
- [x] REL-02: Published [checkpoint `14ed45e2`](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-14ed45e2), including matrix declarations/assumptions, Gram positivity, Fourier display and the package-smoke repair. Validation: 74 packaged audit groups, 266 verified visual captures, 340 manifest files. ZIP SHA-256 `6b1a7e5df9d40904ff5ce4d26367a67c24c55741db631f325ebb4aa3122e5f4d`.
- [x] REL-03: Published [checkpoint `d7acc12b`](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-d7acc12b). Includes [#292](https://github.com/badtyprr/quantumstudio/pull/292), [#293](https://github.com/badtyprr/quantumstudio/pull/293), [#295](https://github.com/badtyprr/quantumstudio/pull/295), [#296](https://github.com/badtyprr/quantumstudio/pull/296), [#297](https://github.com/badtyprr/quantumstudio/pull/297) and built-in `|GHZ>` in [#298](https://github.com/badtyprr/quantumstudio/pull/298). Required merged-tip CI, 79 packaged audit groups and 271 visual captures passed. ZIP SHA-256 `cb0b035a17da593f22ef056481cba05c903f4c34cd2a3df00a62f8a7e9241af4`.
- [x] REL-04: Published [checkpoint `0e52ca9e`](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-0e52ca9e), including symbolic binary labels and the local-include compiler CLI in [#299](https://github.com/badtyprr/quantumstudio/pull/299), [#300](https://github.com/badtyprr/quantumstudio/pull/300) and [#301](https://github.com/badtyprr/quantumstudio/pull/301). Required CI, 81 packaged audit groups, 272 visual captures and 340 payload hashes passed. Native suite: 48 passed, one existing thread test skipped, zero failures. ZIP SHA-256 `10f70826ee1c77e0579be98df87ee2ef78d6c504d7dbab713c751f8f7900b2ff`. This does not complete DEV-05 or DEV-16.
- [x] REL-05: Published [checkpoint `52875710`](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-52875710), including the source-document model, classical history and editor controls in [#303](https://github.com/badtyprr/quantumstudio/pull/303), [#304](https://github.com/badtyprr/quantumstudio/pull/304) and [#305](https://github.com/badtyprr/quantumstudio/pull/305). Required CI, 82 packaged audit groups, 399 verified visual captures and 340 payload hashes passed. Native suite: 48 passed, one existing thread test skipped, zero failures. Uploaded ZIP digest matches the tested artifact: `738e751d0e6c3252c07031561b8137dbbdc67eca077e9a068f257603c30a5bb0`.
- [x] REL-06: Published [checkpoint `22e4dca9`](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-22e4dca9), including numerical-composer source preservation in [#307](https://github.com/badtyprr/quantumstudio/pull/307) and the sampling-shutdown observation/cleanup repair in [#314](https://github.com/badtyprr/quantumstudio/pull/314). The first release attempt at `06269770` failed the shutdown check and was not published. The repaired merged revision passed all three required CI checks, 83 packaged audit groups, 408 verified visual captures and 340 payload hashes. Native suite: 48 passed, one existing thread test skipped, zero failures. The uploaded ZIP is the tested artifact: SHA-256 `27a433270cd0a5c3ffe4bf9090da43473bf2c2e3b1204ce2c332ae3cc3580df2`.
- [x] REL-07: Published [checkpoint `88abaa73`](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-88abaa73), the source-workflow batch: [#308](https://github.com/badtyprr/quantumstudio/pull/308), [#310](https://github.com/badtyprr/quantumstudio/pull/310), [#311](https://github.com/badtyprr/quantumstudio/pull/311), [#312](https://github.com/badtyprr/quantumstudio/pull/312), [#313](https://github.com/badtyprr/quantumstudio/pull/313), [#315](https://github.com/badtyprr/quantumstudio/pull/315), [#316](https://github.com/badtyprr/quantumstudio/pull/316), [#317](https://github.com/badtyprr/quantumstudio/pull/317). Includes dependency checks/reimport, original-file diagnostics, compile-time subroutine locals, unchanged classical module import tests, shared gate serialization and Boolean-to-bit cast fixes. Each merged head passed required CI and exact-head self-review; actual merge parents/trees were verified. All three merged-tip CI checks, 84 package audit groups, 432 visual captures and 340 payload hashes passed. Native suite: 48 passed, one existing thread test skipped, zero failures. Uploaded ZIP SHA-256 matches the tested artifact: `de54840bb8e153002a8250a251da1dba6d29cfe7dbcb7a7eff8c408a1cb583ec`.

- [x] REL-08: Published [checkpoint `0ee22bfe`](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-0ee22bfe), including [#318](https://github.com/badtyprr/quantumstudio/pull/318), [#319](https://github.com/badtyprr/quantumstudio/pull/319), [#320](https://github.com/badtyprr/quantumstudio/pull/320), [#321](https://github.com/badtyprr/quantumstudio/pull/321), [#322](https://github.com/badtyprr/quantumstudio/pull/322) and [#323](https://github.com/badtyprr/quantumstudio/pull/323). Required CI, 84 packaged audit groups, 432 verified captures and 340 payload hashes passed. Native suite: 48 passed, one existing thread test skipped, zero failures. Uploaded ZIP SHA-256 matches the tested artifact: `b2512eb4fdbc76c2b3fa98328884bbbd0c2ecab84b46bc71e5dd5360fce97ecd`. This release contains the export prerequisites, not the classical-editor export command.

- [x] REL-09: Published [checkpoint `6f079092`](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-6f079092), including program serialization, the classical-editor export command and observable QB-004 module export/reimport checks in PRs #324–#327. Required CI, 85 packaged audit groups, 474 verified visual captures and 340 payload hashes passed. Native suite: 48 passed, one existing thread test skipped, zero failures. Uploaded ZIP SHA-256 matches the tested artifact: `2bfd30346932843aec49e7f55302637186d11ae720360adc764971a0f749337e`. Whole-notebook coverage and runtime subroutine storage remain incomplete.

- [x] REL-10: Published [checkpoint `7c66ed79`](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-7c66ed79), including fixed indexed registers, nested matrix copy/re-entry, explicit dimension checks and symbolic tensor repetition in PRs #328–#332. All required merged-tip CI checks passed. The tested package passed 86 audit groups, 480 verified visual captures and 340 payload hashes. Windows native suite: 48 passed, one existing thread test skipped, zero failures; 1,784 worker checks. Linux native CI: 49 passed, no skips or failures. Uploaded ZIP SHA-256 matches the tested artifact: `3354aa3344f628f5523a109abb188bd39c2f250c810b558c3a72d2ab7ace97fd`. This does not complete variable-length families or general symbolic register-width equations.

- [x] REL-11: DEV-05e from [#333](https://github.com/badtyprr/quantumstudio/pull/333) shipped in [checkpoint-3254e5d4](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-3254e5d4), revision `3254e5d4fa63b7e87394711dc1281f32bf6aa75f`. Final-head and merged-tip CI passed; Linux native tests: 49 passed, zero skips/failures; Windows: 48 passed, one existing thread-test skip, zero failures. The clean merged-tip package passed 1,832 worker checks, 87 artifact audit groups and 482 visual checks; all 340 payload hashes and 341 ZIP entries verified. Published ZIP SHA-256: `625b92b87341edb25c2fe6d3118b1a64c32ae41303d144faed8ce0fb39d94882`. Four feature self-review rounds resolved two medium findings; two checklist self-review rounds found none. A stale promotion-verifier count was corrected from 510 to the reviewed 526 notation checks in one additional helper self-review; the failed attempt was retained and the ZIP was unchanged. These were self-reviews, not independent review.

- [x] REL-12: Runtime Rx/Ry/Rz import, editing, saved circuits, export and execution from PRs #338–#348, plus the UTF-8 BOM worker fix in [#349](https://github.com/badtyprr/quantumstudio/pull/349), shipped in [checkpoint-5b982f1f](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-5b982f1f), revision `5b982f1f8cea66ea12d37c8f03e1e289f7ac5442`. Required merged-tip CI passed. Windows native suite: 52 passed, one existing thread-test skip, zero failures/errors. The package passed 1,840 worker checks, 552 adapter checks, 119 runtime-angle protocol checks, 125 import/export checks, six editor-created rotation checks, 88 artifact audit groups and 516 verified visual captures. All 340 payload hashes and 341 ZIP entries verified. Published ZIP SHA-256: `e4dd16b34d5bee201e4d1f6613ece5113fc183c99df419c989f2cbdadf668a4f`. Scoped self-review was used, not independent review. The prior package attempt failed the encoding check and was retained; the fixed merged revision was rebuilt. Artifact audit failures from optional-null DTO fields and two stale prefix counts were then corrected and reviewed; all groups passed against unchanged ZIP bytes. Broader gates/types and source-lesson acceptance remain DEV-06d–f.

- [x] REL-13: Bounded exact phase execution and large-result previews from PRs #352–#355 shipped in [checkpoint-66a5dd79](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-66a5dd79), revision `66a5dd790022ed2673632647b064e2de8f5fef58`. All three merged-tip CI checks passed. Windows native suite: 56 passed, one existing thread-test skip, zero failures/errors. The normal package regression pipeline passed; the full pinned 55-gate inverse-QFT source then passed frozen import, exact worker execution (6.297 seconds, eight outcomes), GUI display and complete JSON/TSV checks. Eight affected/smoke captures were visually inspected, and all 340 payload hashes and 341 ZIP entries verified. Published ZIP SHA-256: `3a507a09285a7c0194a42d7edc8499520e71f44303a464a11c3b21b93fe0cde6`. Two scoped self-review rounds each for the worker integration and GUI follow-up resolved one medium and two minor findings in total; no outstanding findings in those changes. This was not independent review. Full QB-005 notebook/provider coverage remains unchecked; [scope and evidence](learning-evidence/QB-005.md#shipped-exact-execution-and-result-display).

- [x] REL-14: Compiler-resolved array import from [#357](https://github.com/badtyprr/quantumstudio/pull/357) shipped in [checkpoint-982e5abe](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-982e5abe), revision `982e5abe1b08b0ca48bd48fbb8339b91a1a1f934`. Three merged-tip CI checks passed; native tests: 56 passed, one existing thread skip, zero failures/errors. Full packaging, 46 source/frozen array checks, unchanged-adder editor/sampling acceptance, five inspected GUI captures and all 341 ZIP entries passed. Published ZIP SHA-256: `96af6246a93ad010e23d19c08e70c5c68b9890b5deac203a968f04bf9e2e1202`. Three scoped self-reviews resolved one high-severity prototype issue and one minor CI expectation issue; no outstanding findings. Runtime arrays and full notebook coverage remain open; [evidence](learning-evidence/QB-003.md).
- [x] REL-15: Published [checkpoint `a1d85f61`](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-a1d85f61). Explicit unitary/Hermitian/projector domains, guarded identities and natural matrix-property controls in [#360](https://github.com/badtyprr/quantumstudio/pull/360), [#361](https://github.com/badtyprr/quantumstudio/pull/361), and [#362](https://github.com/badtyprr/quantumstudio/pull/362). Required CI and the merged-tip package pipeline passed; 1,992 worker checks, packaged property-editor interaction/session/history checks, three inspected captures and 340 payload hashes verified. Native: 56 passed, one existing thread-test skip, zero failures/errors. ZIP SHA-256 `1cb453630fb0a2798860f8c481b2b6b5608276782666f9105b32c305d007c488`. [DEV-04 evidence](learning-evidence/DEV-04.md).

- [x] REL-16: Published [checkpoint `96595d01`](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-96595d01), runtime scalar subroutine calls and export lifetime reconstruction in [#364](https://github.com/badtyprr/quantumstudio/pull/364). All required reviewed-head and merged-tip CI passed. Clean package: 1,992 worker, 568 sampling, 71 exact-circuit, 1,576 classical-expression and 1,458 compiler checks; 35 export cases, 13 rejection cases and 105 export semantic checks passed. Packaged GUI export/history/file preservation and exact exported feedback probabilities passed; three captures inspected and 340 payload hashes verified. Native: 56 passed, one existing thread-test skip, zero failures/errors. ZIP SHA-256 `031f7c53b3eae58ec1c6f1c2d7ea18c00750bcb401802c09504bb376ea338008`. [DEV-08b evidence](learning-evidence/DEV-08b.md).

- [x] REL-17: Published [checkpoint `9975e211`](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-9975e211), bit runtime arguments and activation-local storage in [#366](https://github.com/badtyprr/quantumstudio/pull/366). Reviewed-head and merged-tip CI passed. Clean package: 1,992 worker and 1,504 compiler checks; two actual GUI exports and four original/exported exact distributions passed; six captures inspected. Native: 56 passed, one existing thread skip, zero failures/errors. All 340 payload hashes and 341 ZIP entries verified. ZIP SHA-256 `6e25ed7b7d06c13cb2a0d8a164a75ae1137d8acdb80fabbd8d653fa15b21ba62`.

- [x] REL-18: Published [checkpoint `abb947c0`](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-abb947c0), typed runtime returns and early exits in [#367](https://github.com/badtyprr/quantumstudio/pull/367). Reviewed-head and merged-tip CI passed. Clean package: 1,992 worker and 1,608 compiler checks; three actual GUI exports and six original/exported exact distributions passed; nine captures inspected. One initial returned-range export encountered an IOException replacing an existing file; the identical targeted rerun passed. Cause unconfirmed; failure retained. Native: 56 passed, one existing thread skip, zero failures/errors. All 340 payload hashes and 341 ZIP entries verified. ZIP SHA-256 `802ad97058b477ee8a2fbc5e805d315ad6304b385c2cfe42ba2ce77498ed1065`. [DEV-08b evidence](learning-evidence/DEV-08b.md).

- [x] REL-19: Published [checkpoint `3663fa58`](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-3663fa58), concatenated bit arguments in [#368](https://github.com/badtyprr/quantumstudio/pull/368). All three reviewed-head and merged-tip CI checks passed. Clean package: 1,992 worker and 1,648 compiler checks; 56 native passes, one existing thread skip, zero failures/errors. Two packaged GUI exports, four exact original/exported distributions and six inspected captures passed; three unchanged numerical controls and three existing classical rejections matched. All 340 payload hashes and the ZIP were verified. Uploaded ZIP SHA-256 `6511b256872342df2ab5be0374e889bc9b0537625177e1e15598b509b2dca63c`. [Source boundaries and review](learning-evidence/DEV-08b4.md).

- [x] REL-20: Published [checkpoint `b4cc7ee0`](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-b4cc7ee0), fixed quantum-register parameters in [#370](https://github.com/badtyprr/quantumstudio/pull/370). All three reviewed-head and merged-tip CI checks passed. Clean package: 1,992 worker and 1,710 compiler checks; 56 native passes, one existing thread skip, zero failures/errors. Three packaged GUI exports, six exact original/exported distributions and nine inspected captures passed. Three unchanged numerical controls matched; the unchanged four-H classical control now passes, while dynamic-index and float controls retain their rejections. All 340 payload hashes and 341 ZIP entries verified. Uploaded ZIP SHA-256 `f439732f52a4b9f1331a932123e4ced564b7c95edea5ea1fd9f27def5e8148fc`. [Evidence and remaining parameter forms](learning-evidence/DEV-08b5-registers.md).

- [x] REL-21: Published [e9e01c5a](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-e9e01c5a), including bounded constant quantum-register widths ([#373](https://github.com/badtyprr/quantumstudio/pull/373)), bounded quantum-call loop indices ([#375](https://github.com/badtyprr/quantumstudio/pull/375)), and complete DEV-03 declared-basis support ([#376](https://github.com/badtyprr/quantumstudio/pull/376)). Required CI, clean packaging and actual-payload audits passed: 2,178 worker checks; 56 native passes, one existing thread skip, zero failures/errors; basis calculation/save/open/history verification; six circuit GUI exports and twelve exact original/exported results; twenty inspected captures. All payload and archive hashes verified. ZIP SHA-256 `4dc6ab77e5b551efc7d3721d93a5a39bf9776a6f9e64bc5260f33c30db066419`. The earlier layout timeout is retained as a historical intermittent issue. [PR #377](https://github.com/badtyprr/quantumstudio/pull/377) adds bounded recovery for transient atomic export refusal; the underlying filesystem cause remains unidentified. [Basis evidence](learning-evidence/DEV-03.md), [register/loop evidence](learning-evidence/DEV-08b5-registers.md).

- [x] REL-22: Published [1666b09a](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-1666b09a), completing the finite DEV-06 contract through PRs #379–#382. All required reviewed-head and merged-tip CI gates, clean packaging and actual-payload audit passed. Clean package: 61 native passes, one existing thread skip, zero failures/errors; 2,178 worker checks; 285 source inputs verified byte for byte. Audit: 340 numeric and 197 gate protocol checks; 337 typed numeric import/model/export checks; 128 pinned-source checks; nine editor-created execution checks; five inspected GUI captures. All payload and archive hashes verified. ZIP SHA-256 `d9679429503ed9a08e981b25ad1f53f42360696b0ca1b77300e3436387635c26`. [Evidence and explicit limits](learning-evidence/DEV-06.md).

- [x] REL-23: Published [afca2fe6](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-afca2fe6), completing bounded DEV-07 wire selection through PRs #384–#385. Reviewed-head and merged-tip CI, clean packaging and immutable-payload audit passed: 280 wire protocol checks; 270 wire import/model/export checks; 31 pinned-source checks; 12 editor-created execution checks and seven visually inspected captures. All payload/archive hashes match the tested artifact. ZIP SHA-256 `7a6224e40467616fe1ca9b65cd556f2d368afcf34dda78c155a19308c9d10deb`. [Evidence and explicit limits](learning-evidence/DEV-07.md).

## Acceptance criteria by development item

### DEV-01

- [x] **Compact bound-index products** — P1; Released; size S; dependencies: None.
- Source focus: Fundamentals: phase estimation; IBM Fourier double sum. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Finish xy parsing without changing quoted names, pi or nested index declarations. Verify QFT residuals for N=1..4 in exact/approximate modes and symbolic copy round trips.
- Evidence: IBM Fourier double-sum reproduction; [#292](https://github.com/badtyprr/quantumstudio/pull/292) merged as `48115b3ca953f80747df0e05df478c1a92788666`, released in REL-03. Nested index declarations, lexical constants and parser complexity limits have regression coverage. Tests: `src/quantum-worker-test.py`, `src/quantum-notation-test.cc`. Packaged audit: 32 mathematical checks and four GUI checks. Owner: unassigned.

### DEV-02

- [x] **Domain-preserving symbolic Fourier expansion** — P1; Released; size L; dependencies: DEV-01.
- Source focus: Fundamentals: phase estimation and factoring. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Simplify QFT_N|x>_N to a capture-free normalized Fourier sum with IBM positive phase. Preserve integer/range constraints after substitution: x=N, fractional x and invalid N must still reject. Test inverse and N=1.
- Evidence: [#293](https://github.com/badtyprr/quantumstudio/pull/293) merged as `61e04203bbfecb606dea1ea68352cdada6786f29`, released in REL-03. Regression coverage in `src/quantum-worker-test.py` and `src/quantum-algebra-test.cc`: forward/inverse sums, invalid substitution, cancellation, fresh indices and canonical copy. Packaged audit: 96 mathematical checks and four GUI checks. Completion covers this acceptance criterion; the source lessons remain separately unchecked. Owner: unassigned.

### DEV-03

- [x] **Declared orthonormal bases** — P1; Released; size L; dependencies: None.
- Source focus: Basics and general formulation: states and measurements. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Declare a named basis and dimension; reduce inner products to Kronecker delta and complete projector sums to identity. Unknown bases must stay unresolved. Verify declarations survive save/load and copy.
- Released in REL-03: [#295](https://github.com/badtyprr/quantumstudio/pull/295) adds scoped finite named declarations and within-basis contractions; [#296](https://github.com/badtyprr/quantumstudio/pull/296) adds full finite projector sums. Distinct bases retain unknown overlaps. [#376](https://github.com/badtyprr/quantumstudio/pull/376) completes symbolic indexed families, guarded deltas and identities, and dedicated basis editing with session/history preservation. Verified in [e9e01c5a](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-e9e01c5a). The full declared-basis acceptance is covered by [DEV-03 evidence](learning-evidence/DEV-03.md).
- Evidence: primary sources, reproducers, tests, exact reviewed head, CI jobs, immutable package hashes and released revision are recorded in the linked acceptance evidence. Broader lesson and roadmap coverage remains separate.

### DEV-04

- [x] **Symbolic operator assumptions and identities** — P1; Released in REL-15; size L; dependencies: DEV-03.
- Source focus: General formulation: unitary operations and channels. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Add explicit unitary/Hermitian/projector assumptions with dimension checks; simplify U†U and projector products only when justified. Reject incompatible substitutions and preserve noncommuting order.
- Implementation: [#360](https://github.com/badtyprr/quantumstudio/pull/360), [#361](https://github.com/badtyprr/quantumstudio/pull/361), and [#362](https://github.com/badtyprr/quantumstudio/pull/362). [Source and acceptance evidence](learning-evidence/DEV-04.md) maps assumptions, guarded identities, incompatible substitutions and noncommuting order to regressions. Released in REL-15 with all explicit acceptance criteria verified. This does not claim complete lesson/channel coverage.

### DEV-05

- [ ] **Register dimensions and symbolic bit strings** — P1; Partial; size M; dependencies: None.
- Source focus: Fundamentals: query algorithms and Fourier algorithms. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Carry widths through tensor products, basis labels and bit operations. Test leading zeros, empty registers, concatenation, indexed registers, and contradictory dimensions; ambiguous widths remain symbolic.
- Released portion in REL-04: [#299](https://github.com/badtyprr/quantumstudio/pull/299) preserves typed symbolic binary labels through operations, set kets and copy/substitution, including deferred cardinality when labels may become equal. Required CI and packaged validation passed, including 1,540 worker checks and 18 symbolic-label GUI checks.
- Source fixture: [IBM Deutsch–Jozsa, Algorithm analysis](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-jozsa-algorithm). Its Hadamard layer uses high-to-low indexed binary registers. Fixing the width to two bits is an explicit adaptation, not whole-lesson coverage.
- Delivery order (all P1; keep unchecked until merged and released):
  - [x] **DEV-05a — Fixed indexed registers:** [#328](https://github.com/badtyprr/quantumstudio/pull/328), released in REL-10. `|x_1 x_0>` remains symbolic, preserves leading zeros, and retains per-bit basis constraints.
  - [x] **DEV-05b — Copy/re-entry of nested matrices:** [#329](https://github.com/badtyprr/quantumstudio/pull/329), released in REL-10; depends on DEV-05a. Copying `tensor(H,H)|x_1 x_0>` preserves its four-row state after substitution.
  - [x] **DEV-05c — Declared register dimensions:** [#330](https://github.com/badtyprr/quantumstudio/pull/330), released in REL-10; depends on DEV-05b. Reject incompatible explicit shapes such as `H|x_1 x_0>`, retain `tensor(H,H)|x_1 x_0>`, and defer genuinely unknown dimensions.
  - [x] **DEV-05d — Symbolic tensor repetition:** [#332](https://github.com/badtyprr/quantumstudio/pull/332), released in REL-10; depends on DEV-05c. Preserve unresolved `H^{\otimes n}` and natural `tensorpow(H,n)` through copy and substitution, including zero repetitions and invalid-count checks. Copy and saved sessions retain readable notation.
  - [x] **DEV-05e — Variable-length indexed families:** [#333](https://github.com/badtyprr/quantumstudio/pull/333), released in REL-11. Natural `|x_(n-1) ... x_0>` and IBM TeX ellipses preserve descending inclusive bounds, bit assignments and explicit trailing-bit constraints. Packaged validation included 1,832 worker checks, 526 notation checks, 249 TeX checks and 12 dedicated family GUI calculations; independent two-bit Hadamard controls included. Concrete expansion supports one through ten qubits. This does not establish whole-lesson coverage.
- Regression locations for DEV-05a–e: `src/quantum-worker-test.py` and `src/quantum-notation-test.cc`. REL-10 records released DEV-05a–d evidence; REL-11 records released DEV-05e evidence. Remaining scope includes general symbolic register-width equations, symbolic domains, arbitrary indexed ellipsis patterns and widths beyond the finite numerical limit.

### DEV-06

- [x] **Runtime gate parameters** — P1; Released in REL-22; size L; dependencies: None. Complete for the documented finite gate/type contract and selected source audit; whole-notebook coverage remains separate.
- Source focus: qBraid PyQASM examples and algorithm notebooks. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Preserve a supported runtime arithmetic angle through importer, circuit model, save/load and executor. Compare small numerical circuits with a reference; reject unavailable types and invalid angles clearly.
- Work in priority order:
  - [x] **DEV-06a — Execution and worker protocol:** PRs [#338](https://github.com/badtyprr/quantumstudio/pull/338), [#339](https://github.com/badtyprr/quantumstudio/pull/339), [#340](https://github.com/badtyprr/quantumstudio/pull/340), and [#341](https://github.com/badtyprr/quantumstudio/pull/341) merged. Bounded binary64 arithmetic over current integer/measurement values; Rx/Ry/Rz execution in exact and sampled modes. Exact gates preserve the binary64 angle as a rational, without snapping approximate pi. **Released in REL-12.**
  - [x] **DEV-06b — Integrate and release the end-to-end path:** adapter [#342](https://github.com/badtyprr/quantumstudio/pull/342), saved circuits [#343](https://github.com/badtyprr/quantumstudio/pull/343), importer [#344](https://github.com/badtyprr/quantumstudio/pull/344), export [#345](https://github.com/badtyprr/quantumstudio/pull/345). Merged after exact-head review and required CI; the reviewed merged package is published as REL-12 (`5b982f1f`). Its uploaded digest matches the tested ZIP.
  - [x] **DEV-06c — Editor interaction:** display the rotation axis and angle; allow creating and editing expressions without JSON; preserve integer versus real division. Test selection, replacement, invalid input, undo/redo, save/reopen, and execution in both modes. Imported operations must not appear as an unlabeled generic rotation. Released in REL-12 through [#347](https://github.com/badtyprr/quantumstudio/pull/347) and [#348](https://github.com/badtyprr/quantumstudio/pull/348); six packaged editor-created circuit checks and normal/minimum rotation captures passed.
  - [x] **DEV-06d — Broader gates:** [#379](https://github.com/badtyprr/quantumstudio/pull/379), released in REL-22. Phase/global-phase, U3/published-U, controls/negative controls, inverses and integer powers -64 through 64; parameter snapshots and evaluation errors are preserved through both engines and export.
  - [x] **DEV-06e — Runtime arithmetic/types:** [#380](https://github.com/badtyprr/quantumstudio/pull/380) and [#381](https://github.com/badtyprr/quantumstudio/pull/381), released in REL-22. Finite float32/64 variables, typed mathematical functions, angle1–64 modular values and explicit casts, scoped storage, editor and saved model13. Exact rational-pi phases retain conjugate cancellation. Remaining subroutine activation parameter forms stay DEV-08b.
  - [x] **DEV-06f — Source evidence:** [#382](https://github.com/badtyprr/quantumstudio/pull/382), released in REL-22. Eleven unchanged pinned qBraid programs pass independent complete-operator and scalar-value references; four additional originals retain explicit rejection records. Authored dynamic feedback/math probes are distinguished from source acceptance. [Provenance, reference method, review, CI and release](learning-evidence/DEV-06.md).
- Regression evidence: `src/quantum-runtime-rotation-test.cc`, `src/quantum-exact-runtime-rotation-test.cc`, `src/quantum-runtime-angle-request-test.py`, `windows/ClassicalExpressionTests.cs`, `windows/ClassicalCircuitTests.cs`, and `windows/test-qasm-runtime-angles.py`. The export branch passed 125 source/frozen/import-export/worker checks, including feedback, mutation, integer/real division, broadcasting, phase interference, branch-local variables and runtime ranges. REL-12 repeats the 125 checks against the packaged compiler, adapter and worker; this verifies the implemented path without completing source-lesson coverage.

### DEV-07

- [x] **Dynamic wire indexing** — P1; Released in REL-23; size L; dependencies: None. Complete for bounded scalar indices into declared registers and existing fixed aliases; dynamic alias creation and subroutine actual binding remain DEV-08b.
- Source focus: qBraid PyQASM and generated circuits. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Evaluate bounded runtime wire indices consistently in import and execution; test in-range, negative, out-of-range, aliases and multi-qubit collisions. Keep source-local diagnostics.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. PRs: [#384](https://github.com/badtyprr/quantumstudio/pull/384), [#385](https://github.com/badtyprr/quantumstudio/pull/385). [Evidence and limits](learning-evidence/DEV-07.md). Released [afca2fe6](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-afca2fe6).

### DEV-08

- [ ] **Array/set iteration and subroutine-local storage** — P1; Partial, scalar, bit and return calls released through REL-18; size L; dependencies: DEV-07 for dynamic indexing, not for the reproduced constant-index subroutine case.
- Source focus: qBraid PyQASM examples and the unchanged QB-004 generated `oracle.qasm` and `bernvaz.qasm` fixtures.
- Reproduced blocker: the published REL-05 compiler resolves both local includes with `--module-headers`, but `--classical` rejects both fixtures' local integer declarations. Numerical import produces three and ten operations respectively. See [QB-004 follow-up evidence](learning-evidence/QB-004.md#follow-up-local-includes-and-classical-subroutine-storage).
- Acceptance: Implement one supported construct per PR. Prioritize subroutine-local lifetimes and shadowing for QB-004, then bounded arrays/set loops. Test repeated/nested calls, distinct activations, loop transfers, cleanup, serialization and resource limits. Do not change the generated fixtures to inline or remove their local variables to claim acceptance.
- [x] DEV-08a: Released compile-time subroutine locals in [#313](https://github.com/badtyprr/quantumstudio/pull/313), merged as `f4736029d957c8353108beedab00c02e8e45574a` from reviewed head `3eebec87b54c34edf016991dacc4150aaa0788f2`. Both unchanged QB-004 modules compile in classical mode; repeated/nested calls, lexical shadowing, mutable-global rejection and call limits have regression coverage. Initial frozen validation passed 15 file-import methods and 1,286 classical-expression checks. Updated-head CI passed before merge. REL-07 passed frozen-package import of both unchanged modules, retained source bytes, editor history/save/reopen and visual checks.
- [ ] DEV-08b: Complete runtime subroutine activation storage. Scalar arguments/locals, bit-register storage and returned values are released; complete source-example acceptance and remaining parameter forms stay open. [Evidence and limits](learning-evidence/DEV-08b.md).
  - [x] **DEV-08b1 — Scalar runtime calls:** REL-16 / [#364](https://github.com/badtyprr/quantumstudio/pull/364). By-value int/uint/bool arguments, nested/repeated calls, scalar locals, lexical constants, bounded expansion and export of proven local lifetimes.
  - [x] **DEV-08b2 — Bit arguments and local storage:** REL-17 / [#366](https://github.com/badtyprr/quantumstudio/pull/366). Measured bit/bit-register arguments and activation-local storage; snapshots, repeated/nested activations, measurements, shadowing, initialization and packaged export/reimport verified. Source-driver additions remain disclosed in the evidence.
  - [x] **DEV-08b3 — Returned values and early return:** REL-18 / [#367](https://github.com/badtyprr/quantumstudio/pull/367). Integer/Boolean/bit returns, measurement results, missing-return errors, short-circuit effects, returned conditions/bounds and void early exits through nested branches/loops verified. Runtime floating-point/angle returns remain outside this released subset.
  - [x] **DEV-08b4 — Bounded source acceptance:** REL-19 / [#368](https://github.com/badtyprr/quantumstudio/pull/368). The measured-parity invocation and operations pass with disclosed driver and accumulator initialization; concatenation is a documented grammar compatibility extension. Three unchanged qBraid strings match numerical gate/wire/angle oracles; existing classical-mode rejections remain. [Evidence and limits](learning-evidence/DEV-08b4.md). This closes this bounded audit, not all source examples or notebooks.
  - [ ] **DEV-08b5 — Remaining parameter forms:** P1, M/L; source-led. Runtime angle/float parameters coordinate with DEV-06; array references and dynamic indices coordinate with DEV-08c/DEV-07. Preserve type-specific aliasing and mutation rules.
- [ ] DEV-08c: Implement arrays/set iteration with bounded runtime behavior and dynamic indexing where needed; retain the full acceptance criteria above. Compiler-resolved arrays and the unchanged QB-003 adder shipped in REL-14 through [#357](https://github.com/badtyprr/quantumstudio/pull/357); 46 source/frozen array checks and packaged editor/sampling acceptance passed. Runtime storage and dynamic indexing remain open. See [QB-003 evidence](learning-evidence/QB-003.md).
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned.

### DEV-09

- [ ] **Symbolic ensembles, instruments and POVMs** — P2; Partial; size L; dependencies: DEV-03.
- Source focus: General formulation: general measurements. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Represent labeled outcomes and post-measurement states; verify normalization, probabilities and partial trace. Add automatic Naimark construction with explicit ancilla dimensions and rejection of invalid POVMs.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### DEV-10

- [ ] **Symbolic domains, sets and indexed families** — P2; Partial; size L; dependencies: DEV-05.
- Source focus: General formulation and fundamentals. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Support required Cartesian alphabets, symbolic membership/cardinality and lesson-specific indexed families. Preserve singleton/empty sets, binder scopes and unresolved equality. Add actual failing source fixtures before implementing each extension.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### DEV-11

- [ ] **Error-correction lesson operations** — P2; Partial; size L; dependencies: DEV-04.
- Source focus: Foundations of quantum error correction. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Audit every stabilizer/CSS/logical-operator example; turn unsupported encodings, syndromes and recovery operations into separate small tasks. Compare logical action and syndrome tables against source examples.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### DEV-12

- [ ] **Variational and numerical operator coverage** — P2; Partial; size L; dependencies: DEV-04.
- Source focus: Variational design; chemistry; diagonalization; ML. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Inventory unsupported objectives, derivatives, matrix functions and eigensolvers from source examples. Verify small reference problems and report numerical tolerances independently of exact arithmetic.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### DEV-13

- [ ] **Python/SDK notebook execution route** — P2; Discovery needed; size L; dependencies: AUD-02.
- Source focus: qBraid SDK, algorithms and IBM code examples. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Specify and implement a reproducible notebook/program import or execution route for each required framework. Distinguish direct execution from manual QASM adaptation. Pin dependencies and test equivalent states, counts and errors.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### DEV-14

- [ ] **QIR and CUDA-Q compatibility** — P3; Not implemented; size L; dependencies: DEV-13.
- Source focus: qBraid QIR and CUDA-Q notebooks. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Audit entry points and program semantics; implement explicit supported imports/execution and verify small circuits. Unsupported compiler/runtime features must be recorded per notebook, not silently dropped.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### DEV-15

- [ ] **Cloud/provider and pulse workflows** — P3; Not implemented; size L; dependencies: DEV-13.
- Source focus: qBraid Runtime/Provider-Jobs; IBM utility-scale courses. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Separate local mathematical semantics from credentials, hardware jobs and pulse/timing dependencies. Define tested adapters and observable unsupported cases; use deterministic offline fixtures, and record any required external verification.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### DEV-16

- [ ] **Local OpenQASM include dependencies** — P1; Partial; size M; dependencies: None.
- Source: [QB-004 evidence](learning-evidence/QB-004.md), generated oracle and algorithm subroutine instructions. The original reproduction showed direct includes failing while explicit inlining imported successfully; REL-04 resolves the compiler CLI portion.
- Acceptance: Resolve dependencies relative to a selected source file with an explicit policy for external paths and paste-only input. Preserve standard includes; diagnose missing files, cycles and duplicate declarations with file/line context. Bound depth and total bytes; preserve dependency identity through save/load/export and detect changed dependencies. Verify both generated subroutines and numerical equivalence to inlining, nested includes and paths containing spaces.
- Priority rationale: This blocks a demonstrated local circuit workflow and does not depend on runtime wire indexing or cloud access. Source-aware import context is part of this task.
- Released in REL-04: [#300](https://github.com/badtyprr/quantumstudio/pull/300) captures bounded dependency snapshots; [#301](https://github.com/badtyprr/quantumstudio/pull/301) adds the source-aware compiler CLI and generated-module adapter. Both unchanged QB-004 subroutine fixtures match explicitly inlined circuit documents in Python and the frozen compiler.
- Ordered remaining steps:
  - [x] DEV-16a: Released classical-editor source preservation through import, save/reopen and undo/redo in REL-05. Validation includes 49 document checks, 99 history checks, six frozen C# bridge checks, and a packaged GUI round-trip with two byte-verified source files and three inspected layouts. These are scoped checks, not whole-notebook coverage.
  - [x] DEV-16b: Published the numerical composer migration to the same source-bearing document model (REL-06). Released implementation preserves provenance through edits, history and failures while keeping runtime requests circuit-only. Validation includes 17 source-preservation checks, 102 circuit-file checks, and three frozen-compiler GUI import/export cases.
  - [x] DEV-16c: Published explicit changed/missing-dependency checks and reimport (REL-07). PR #308 requires a newly selected source root, reports dependency status without mutating the saved snapshot, and provides atomic reimport with undo. A saved source root must not silently authorize filesystem reads. Validation includes 15 source-bundle tests, 15 file-import test methods, 13 frozen C# bridge checks and both editors' packaged GUI workflows, including failed-reimport preservation and undoable successful reimport.
  - [ ] DEV-16d: Map compiler diagnostics to the original dependency file and line, including module-header adaptation. PRs [#310](https://github.com/badtyprr/quantumstudio/pull/310), [#311](https://github.com/badtyprr/quantumstudio/pull/311) and [#312](https://github.com/badtyprr/quantumstudio/pull/312) cover source coordinates, compiler diagnostics and adapter preflight failures; all are released in REL-07 after packaged validation. Later lowering/emission errors without spans still need coverage.
  - [ ] DEV-16e: Verify standalone export and numerical equivalence for both unchanged QB-004 generated subroutines through both editors, including nested includes, spaces, Unicode and failure recovery. Numerical-composer acceptance is in REL-06. Classical import is released in REL-07 through DEV-08a; [#315](https://github.com/badtyprr/quantumstudio/pull/315) adds actual frozen-compiler classical GUI import, undo/redo, edits and save/reopen checks for both fixtures (3/10 expected gates, original source bytes, six inspected captures). The same imports and source-preservation workflows passed the REL-07 package audit; classical export and observable module export/reimport checks are now published in REL-09. Remaining source-specific acceptance must be reconciled against the released evidence. Do not mark this step complete from numerical-only results. Merged [#316](https://github.com/badtyprr/quantumstudio/pull/316) extracts shared gate serialization; it does not implement classical-statement export.
- Evidence: original reproduction in `docs/learning-evidence/QB-004.md`; released tests `windows/test-qasm-source-bundle.py` and `windows/test-qasm-file-import.py`; REL-05 adds `windows/test-source-import-bridge.ps1`. DEV-16 and QB-004 remain incomplete. Owner: unassigned.

#### Classical-editor export delivery steps

Keep DEV-16e unchecked until the complete editor workflow is released.
REL-08 and REL-09 publish the prerequisites and exporter. Each row below is P1;
work in dependency order, keeping compiler support, serialization and GUI
integration in separate scoped PRs.

| ID | Size | State / dependency | Acceptance |
|---|---|---|---|
| DEV-16e.1 | S | Merged [#318](https://github.com/badtyprr/quantumstudio/pull/318); released in REL-08 | Accept unsigned typed shift counts without narrowing the count to the shifted register width; reject signed counts and width mismatches. Development validation: 1,332 source/frozen/worker checks. |
| DEV-16e.2 | S | Merged [#319](https://github.com/badtyprr/quantumstudio/pull/319); released in REL-08 | Serialize all existing typed bit/integer expression nodes with explicit width, signedness and promotion. Development validation: 39 generated expressions, 117 compiler/exact/sampled checks and four invalid-context checks. This is an internal component, not an export command. |
| DEV-16e.3 | S | Merged [#320](https://github.com/badtyprr/quantumstudio/pull/320) and [#322](https://github.com/badtyprr/quantumstudio/pull/322); released in REL-08 | Preserve explicit `output bit`/`output bit[n]` selection on import while retaining ordinary registers as working storage. Exclude local bit storage from program results, including empty outputs. Development validation: 1,404 source/frozen/worker checks. Runtime inputs and non-bit outputs remain separate gaps. |
| DEV-16e.4 | M | Merged [#323](https://github.com/badtyprr/quantumstudio/pull/323); released in REL-08 | Map saved output indices to exported storage without changing ordering or adding final measurements. Twelve generated programs passed 36 compiler/exact/sampled checks, covering empty/subset/permuted outputs, overlapping assignments, all 64 storage bits, undefined reads and early `end`; 13 invalid contexts rejected. No duplicate bit bank or final output copy. |
| DEV-16e.5 | M | Merged [#324](https://github.com/badtyprr/quantumstudio/pull/324); released in REL-09 | Emit declarations and program statements, preserving branch/loop behavior, variable lifetimes, simultaneous assignments and early termination. Cover undefined reads, clear operations, loop limits and transfers. Any unsupported matrix, noise or control semantics must produce a specific error before writing a file; never silently drop an operation. |
| DEV-16e.6 | S | Merged [#325](https://github.com/badtyprr/quantumstudio/pull/325); released in REL-09 | Add the classical editor's export action. Export the current edited circuit, retain its original source snapshot, preserve the file on validation/write failure, and expose unsupported-operation errors. Verify normal/minimum layouts and undo/save/reopen behavior. |
| DEV-16e.7 | M | Merged [#326](https://github.com/badtyprr/quantumstudio/pull/326); released in REL-09 | Import each unchanged QB-004 module, export from the classical editor, reimport with the frozen compiler, and compare independently expected exact and sampled outcomes. Use test preparations and observations that exercise the oracle and algorithm; equality of empty-output results cannot prove circuit equivalence. Include nested includes, spaces/Unicode, edits, failure recovery, selected outputs and early termination. Keep source/module acceptance distinct from whole-notebook execution. |
| DEV-16e.8 | S | Released in REL-09 | Merge reviewed exact heads after required CI, validate the merged Windows package and its captures, then publish the exact tested ZIP. Attach the release revision and artifact digest before completing DEV-16e. |

Development evidence (not a release claim): e.5 passed 31 generated program cases with 93 compiler/exact/sample checks. e.6 passed 17 atomic file checks and the real frozen-compiler GUI workflow; CI found missing test-build dependencies, now fixed with the full local GUI suite passing. e.7 passed six unchanged-module GUI runs, 12 compiler round trips, 24 exact/sample checks and 18 verified captures. These oracle and algorithm probes do not complete either notebook. PRs #324–#326 passed required CI on their updated heads and merged with verified parents/trees. The merged artifact is published in REL-09 with all packaged audits passing.

REL-08 ships the prerequisites in e.1–e.4; REL-09 ships the reviewed GUI
implementation and merged-package validation. DEV-16e remains unchecked pending
reconciliation of every source-specific acceptance item; neither release completes QB-004 as a whole notebook.

Design evidence: [OpenQASM output declarations](https://openqasm.com/versions/3.0/language/directives.html#input-output)
select returned variables; [register concatenation and slicing](https://openqasm.com/versions/3.0/language/types.html#register-concatenation-and-slicing)
refer to existing storage. The current importer still rejects classical aliases,
and direct concatenation in an assignment failed the pinned parser probe.
The storage component uses explicit outputs and local scratch blocks; retain
those semantics when adding whole-program serialization.

### DEV-17

- [ ] **Named subsystem partial traces** — P2; Not implemented; size M. Numeric partial traces already provide the arithmetic baseline; define explicit subsystem names, order and dimensions before implementing named syntax.
- Source and reproduction: [IBM-005 evidence](learning-evidence/IBM-005.md), published revision `3254e5d4`. With the explicit matrix `R` in that evidence, `ptrace(R,1)` returns `identity(2)/2`, while `\operatorname{Tr}_{\mathsf{B}}(R)` rejects its named subscript. This is a literal source operator prefix with an adapted operand, not a whole-lesson compatibility test.
- [ ] DEV-17a: Define how users bind ordered subsystem labels and dimensions to an expression. Document scope, persistence and conflicts. Never guess positions from alphabetical names; distinguish the factors being traced out from the factors retained.
- [ ] DEV-17b: Accept human-entered named trace syntax and the source TeX form using that mapping. Compare full exact matrices for Bell marginals, the asymmetric IBM mixture and a product-state ordering control. Unknown or duplicate labels and incompatible dimensions must produce specific errors.
- [ ] DEV-17c: Cover unequal dimensions `[2,3]`, a middle factor in three systems, and tracing multiple factors. Preserve remaining-factor order. Test renamed/permuted labels so accidental A-to-0/B-to-1 assumptions cannot pass.
- [ ] DEV-17d: Verify GUI entry, copied expressions and saved/reopened declarations retain the same mapping and result. Attach exact-head tests, required CI and the tested release revision before marking this feature released.
- Boundaries: Symbolic dimension identities, set-indexed sums, block matrices and the linked notebook remain separate unverified IBM-005 coverage. Successful numeric adaptations cannot complete that lesson. Owner: unassigned; implementation PR: unassigned.

### AUD-01

- [ ] **Audit algorithms first** — P1; Pending; size M; dependencies: None.
- Source focus: IBM fundamentals + qBraid Algorithms and PyQASM. These are audit targets, not a claim that every page has the same gap.
- Acceptance: For every formula/code cell in these rows, record input, expected result, actual result, mode, fixture and revision; create a DEV item for each failure. Re-run selected existing tests instead of calling a whole lesson complete.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### AUD-02

- [ ] **Complete source discovery** — P1; Pending; size M; dependencies: None.
- Source focus: All IBM/qBraid catalogs. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Reconcile the pinned inventory with current catalogs. Inventory overviews, exams, videos, downloads, linked examples, SDK references and qBook chapters. Track access-blocked sources explicitly; a missing chapter cannot count as covered.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### AUD-03

- [ ] **Audit remaining mathematical lessons** — P2; Pending; size M; dependencies: AUD-01.
- Source focus: Remaining IBM sections/modules. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Use the same per-example evidence contract; prioritize shared parser/algebra failures before isolated special cases. Record non-executable conceptual content with a reviewed rationale.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

### AUD-04

- [ ] **Audit remaining notebooks end to end** — P2; Pending; size M; dependencies: AUD-02.
- Source focus: All remaining qBraid notebooks. These are audit targets, not a claim that every page has the same gap.
- Acceptance: Execute/import every relevant cell through the documented route, including setup and output interpretation. Preserve source commit/hash and distinguish adaptations from unchanged notebook execution.
- Evidence to attach: source URL/section or notebook cell, minimal reproducer, expected result, automated test path, reviewed PR/head, CI run, and released revision. Owner: unassigned. PR: unassigned.

## Source checklist

The pinned inventory contains **137 IBM course sections, 12 IBM modules and 35 qBraid notebooks (184 rows)**. All whole-source audits below remain open: existing feature tests prove selected examples, not exhaustive coverage. These counts are inventory counts, not a percentage of the full goal. IDs below are stable; append new IDs when sources are discovered.

Each row closes only after an evidence record lists every relevant formula/code cell, direct input versus adaptation, exact/approximate results, copy/save/import behavior where relevant, and all failures linked to development IDs. Mark access restrictions as blocked with a reason. Do not check a row merely because its title or one example is supported.

For each completed audit, add `docs/learning-evidence/<ID>.md` containing: source URL and date/revision/hash; example table (location, input, expected, actual, status, test path); unresolved DEV dependencies; reviewed commit/CI; release revision. Until then, unchecked means unproven, not necessarily unsupported.

Pinned URLs and notebook hashes: [source inventory](learning-source-inventory.json). Existing partial evidence: [notation support and limits](quantum-notation.md), [worker regressions](../src/quantum-worker-test.py), [parser integration tests](../src/quantum-parser-integration-test.cc), [QASM import tests](../windows/test-qasm-import.py), [classical import tests](../windows/test-qasm-classical-expressions.py).

### general-formulation-of-quantum-information

- [ ] **IBM-001** [density-matrices/introduction](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/density-matrices/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-002** [density-matrices/density-matrix-basics](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/density-matrices/density-matrix-basics) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-003** [density-matrices/convex-combinations](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/density-matrices/convex-combinations) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-004** [density-matrices/bloch-sphere](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/density-matrices/bloch-sphere) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-005** [density-matrices/multiple-systems](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/density-matrices/multiple-systems) — P1 / AUD-01; partial audit: five adapted numeric probes passed on published `3254e5d4`; named trace rejection tracked in DEV-17. Full lesson/notebook coverage remains open; [evidence](learning-evidence/IBM-005.md).
- [ ] **IBM-006** [quantum-channels/introduction](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/quantum-channels/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-007** [quantum-channels/quantum-channel-basics](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/quantum-channels/quantum-channel-basics) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-008** [quantum-channels/representations-of-channels](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/quantum-channels/representations-of-channels) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-009** [quantum-channels/representation-equivalence](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/quantum-channels/representation-equivalence) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-010** [general-measurements/introduction](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/general-measurements/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-011** [general-measurements/formulations-of-measurements](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/general-measurements/formulations-of-measurements) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-012** [general-measurements/naimark-theorem](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/general-measurements/naimark-theorem) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-013** [general-measurements/discrimination-and-tomography](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/general-measurements/discrimination-and-tomography) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-014** [purifications-and-fidelity/introduction](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/purifications-and-fidelity/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-015** [purifications-and-fidelity/purifications](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/purifications-and-fidelity/purifications) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-016** [purifications-and-fidelity/fidelity](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/purifications-and-fidelity/fidelity) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
### fundamentals-of-quantum-algorithms

- [ ] **IBM-017** [quantum-query-algorithms/introduction](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-018** [quantum-query-algorithms/query-model-of-computation](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/query-model-of-computation) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-019** [quantum-query-algorithms/deutsch-algorithm](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-algorithm) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-020** [quantum-query-algorithms/deutsch-jozsa-algorithm](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-jozsa-algorithm) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-021** [quantum-query-algorithms/simon-algorithm](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/simon-algorithm) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-022** [quantum-algorithmic-foundations/introduction](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-algorithmic-foundations/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-023** [quantum-algorithmic-foundations/factoring-and-gcd](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-algorithmic-foundations/factoring-and-gcd) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-024** [quantum-algorithmic-foundations/measuring-computational-cost](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-algorithmic-foundations/measuring-computational-cost) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-025** [quantum-algorithmic-foundations/simulating-classical-computations](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-algorithmic-foundations/simulating-classical-computations) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-026** [phase-estimation-and-factoring/introduction](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/phase-estimation-and-factoring/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-027** [phase-estimation-and-factoring/phase-estimation-problem](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/phase-estimation-and-factoring/phase-estimation-problem) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-028** [phase-estimation-and-factoring/phase-estimation-procedure](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/phase-estimation-and-factoring/phase-estimation-procedure) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-029** [phase-estimation-and-factoring/shor-algorithm](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/phase-estimation-and-factoring/shor-algorithm) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-030** [grover-algorithm/introduction](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/grover-algorithm/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-031** [grover-algorithm/unstructured-search](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/grover-algorithm/unstructured-search) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-032** [grover-algorithm/grover-algorithm-description](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/grover-algorithm/grover-algorithm-description) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-033** [grover-algorithm/analysis](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/grover-algorithm/analysis) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-034** [grover-algorithm/number-of-iterations](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/grover-algorithm/number-of-iterations) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-035** [grover-algorithm/concluding-remarks](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/grover-algorithm/concluding-remarks) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
### basics-of-quantum-information

- [ ] **IBM-036** [single-systems/introduction](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/single-systems/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-037** [single-systems/classical-information](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/single-systems/classical-information) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-038** [single-systems/quantum-information](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/single-systems/quantum-information) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-039** [single-systems/qiskit-implementation](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/single-systems/qiskit-implementation) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-040** [multiple-systems/introduction](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/multiple-systems/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-041** [multiple-systems/classical-information](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/multiple-systems/classical-information) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-042** [multiple-systems/quantum-information](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/multiple-systems/quantum-information) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-043** [multiple-systems/qiskit-implementation](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/multiple-systems/qiskit-implementation) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-044** [quantum-circuits/introduction](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/quantum-circuits/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-045** [quantum-circuits/circuits](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/quantum-circuits/circuits) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-046** [quantum-circuits/inner-products-and-projections](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/quantum-circuits/inner-products-and-projections) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-047** [quantum-circuits/limitations-on-quantum-information](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/quantum-circuits/limitations-on-quantum-information) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-048** [entanglement-in-action/introduction](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/entanglement-in-action/introduction) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-049** [entanglement-in-action/quantum-teleportation](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/entanglement-in-action/quantum-teleportation) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-050** [entanglement-in-action/superdense-coding](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/entanglement-in-action/superdense-coding) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-051** [entanglement-in-action/chsh-game](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/entanglement-in-action/chsh-game) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **IBM-052** [entanglement-in-action/qiskit-implementation](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/entanglement-in-action/qiskit-implementation) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
### foundations-of-quantum-error-correction

- [ ] **IBM-053** [correcting-quantum-errors/introduction](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/correcting-quantum-errors/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-054** [correcting-quantum-errors/repetition-codes](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/correcting-quantum-errors/repetition-codes) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-055** [correcting-quantum-errors/shor-code](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/correcting-quantum-errors/shor-code) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-056** [correcting-quantum-errors/discretization-of-errors](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/correcting-quantum-errors/discretization-of-errors) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-057** [stabilizer-formalism/introduction](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/stabilizer-formalism/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-058** [stabilizer-formalism/pauli-operations-and-observables](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/stabilizer-formalism/pauli-operations-and-observables) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-059** [stabilizer-formalism/repetition-code-revisited](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/stabilizer-formalism/repetition-code-revisited) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-060** [stabilizer-formalism/stabilizer-codes](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/stabilizer-formalism/stabilizer-codes) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-061** [quantum-code-constructions/introduction](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/quantum-code-constructions/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-062** [quantum-code-constructions/css-codes](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/quantum-code-constructions/css-codes) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-063** [quantum-code-constructions/toric-code](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/quantum-code-constructions/toric-code) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-064** [quantum-code-constructions/other-code-families](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/quantum-code-constructions/other-code-families) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-065** [fault-tolerant-quantum-computing/introduction](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/fault-tolerant-quantum-computing/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-066** [fault-tolerant-quantum-computing/approach-to-fault-tolerance](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/fault-tolerant-quantum-computing/approach-to-fault-tolerance) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-067** [fault-tolerant-quantum-computing/controlling-error-propagation](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/fault-tolerant-quantum-computing/controlling-error-propagation) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-068** [fault-tolerant-quantum-computing/threshold-theorem](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction/fault-tolerant-quantum-computing/threshold-theorem) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### use-a-qc-today

- [ ] **IBM-069** [build-and-run-your-first-quantum-program](https://quantum.cloud.ibm.com/learning/en/courses/use-a-qc-today/build-and-run-your-first-quantum-program) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-070** [quantum-mechanics-basics](https://quantum.cloud.ibm.com/learning/en/courses/use-a-qc-today/quantum-mechanics-basics) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-071** [your-first-quantum-experiment](https://quantum.cloud.ibm.com/learning/en/courses/use-a-qc-today/your-first-quantum-experiment) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-072** [quantum-computing-context](https://quantum.cloud.ibm.com/learning/en/courses/use-a-qc-today/quantum-computing-context) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-073** [continue-your-learning-journey](https://quantum.cloud.ibm.com/learning/en/courses/use-a-qc-today/continue-your-learning-journey) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### quantum-computing-in-practice

- [ ] **IBM-074** [introduction](https://quantum.cloud.ibm.com/learning/en/courses/quantum-computing-in-practice/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-075** [running-quantum-circuits](https://quantum.cloud.ibm.com/learning/en/courses/quantum-computing-in-practice/running-quantum-circuits) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-076** [utility-scale-qaoa](https://quantum.cloud.ibm.com/learning/en/courses/quantum-computing-in-practice/utility-scale-qaoa) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-077** [applications-of-qc](https://quantum.cloud.ibm.com/learning/en/courses/quantum-computing-in-practice/applications-of-qc) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-078** [mapping](https://quantum.cloud.ibm.com/learning/en/courses/quantum-computing-in-practice/mapping) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-079** [simulating-nature](https://quantum.cloud.ibm.com/learning/en/courses/quantum-computing-in-practice/simulating-nature) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### tools-for-quantum-advantage

- [ ] **IBM-080** [introduction](https://quantum.cloud.ibm.com/learning/en/courses/tools-for-quantum-advantage/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-081** [noise-and-errors](https://quantum.cloud.ibm.com/learning/en/courses/tools-for-quantum-advantage/noise-and-errors) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-082** [error-suppression](https://quantum.cloud.ibm.com/learning/en/courses/tools-for-quantum-advantage/error-suppression) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-083** [error-mitigation](https://quantum.cloud.ibm.com/learning/en/courses/tools-for-quantum-advantage/error-mitigation) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-084** [error-correction-i](https://quantum.cloud.ibm.com/learning/en/courses/tools-for-quantum-advantage/error-correction-i) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### integrating-quantum-and-high-performance-computing

- [ ] **IBM-085** [introduction](https://quantum.cloud.ibm.com/learning/en/courses/integrating-quantum-and-high-performance-computing/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-086** [compute-resources](https://quantum.cloud.ibm.com/learning/en/courses/integrating-quantum-and-high-performance-computing/compute-resources) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-087** [programming-models](https://quantum.cloud.ibm.com/learning/en/courses/integrating-quantum-and-high-performance-computing/programming-models) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-088** [sqd-skqd](https://quantum.cloud.ibm.com/learning/en/courses/integrating-quantum-and-high-performance-computing/sqd-skqd) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-089** [next-steps](https://quantum.cloud.ibm.com/learning/en/courses/integrating-quantum-and-high-performance-computing/next-steps) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### quantum-diagonalization-algorithms

- [ ] **IBM-090** [introduction](https://quantum.cloud.ibm.com/learning/en/courses/quantum-diagonalization-algorithms/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-091** [vqe](https://quantum.cloud.ibm.com/learning/en/courses/quantum-diagonalization-algorithms/vqe) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-092** [krylov](https://quantum.cloud.ibm.com/learning/en/courses/quantum-diagonalization-algorithms/krylov) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-093** [sqd-overview](https://quantum.cloud.ibm.com/learning/en/courses/quantum-diagonalization-algorithms/sqd-overview) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-094** [sqd-implementation](https://quantum.cloud.ibm.com/learning/en/courses/quantum-diagonalization-algorithms/sqd-implementation) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-095** [skqd](https://quantum.cloud.ibm.com/learning/en/courses/quantum-diagonalization-algorithms/skqd) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### quantum-machine-learning

- [ ] **IBM-096** [introduction](https://quantum.cloud.ibm.com/learning/en/courses/quantum-machine-learning/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-097** [classical-ml-review](https://quantum.cloud.ibm.com/learning/en/courses/quantum-machine-learning/classical-ml-review) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-098** [data-encoding](https://quantum.cloud.ibm.com/learning/en/courses/quantum-machine-learning/data-encoding) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-099** [quantum-kernel-methods](https://quantum.cloud.ibm.com/learning/en/courses/quantum-machine-learning/quantum-kernel-methods) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-100** [qvc-qnn](https://quantum.cloud.ibm.com/learning/en/courses/quantum-machine-learning/qvc-qnn) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### variational-algorithm-design

- [ ] **IBM-101** [variational-algorithms](https://quantum.cloud.ibm.com/learning/en/courses/variational-algorithm-design/variational-algorithms) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-102** [reference-states](https://quantum.cloud.ibm.com/learning/en/courses/variational-algorithm-design/reference-states) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-103** [ansaetze-and-variational-forms](https://quantum.cloud.ibm.com/learning/en/courses/variational-algorithm-design/ansaetze-and-variational-forms) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-104** [cost-functions](https://quantum.cloud.ibm.com/learning/en/courses/variational-algorithm-design/cost-functions) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-105** [optimization-loops](https://quantum.cloud.ibm.com/learning/en/courses/variational-algorithm-design/optimization-loops) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-106** [instances-and-extensions](https://quantum.cloud.ibm.com/learning/en/courses/variational-algorithm-design/instances-and-extensions) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-107** [examples-and-applications](https://quantum.cloud.ibm.com/learning/en/courses/variational-algorithm-design/examples-and-applications) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### quantum-chem-with-vqe

- [ ] **IBM-108** [introduction](https://quantum.cloud.ibm.com/learning/en/courses/quantum-chem-with-vqe/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-109** [hamiltonian-construction](https://quantum.cloud.ibm.com/learning/en/courses/quantum-chem-with-vqe/hamiltonian-construction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-110** [ansatz](https://quantum.cloud.ibm.com/learning/en/courses/quantum-chem-with-vqe/ansatz) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-111** [classical-optimizers](https://quantum.cloud.ibm.com/learning/en/courses/quantum-chem-with-vqe/classical-optimizers) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-112** [ground-state](https://quantum.cloud.ibm.com/learning/en/courses/quantum-chem-with-vqe/ground-state) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-113** [geometry](https://quantum.cloud.ibm.com/learning/en/courses/quantum-chem-with-vqe/geometry) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### utility-scale-quantum-computing

- [ ] **IBM-114** [introduction](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-115** [bits-gates-and-circuits](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/bits-gates-and-circuits) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-116** [teleportation](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/teleportation) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-117** [grovers-algorithm](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/grovers-algorithm) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-118** [quantum-phase-estimation](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/quantum-phase-estimation) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-119** [variational-quantum-algorithms](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/variational-quantum-algorithms) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-120** [quantum-simulation](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/quantum-simulation) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-121** [classical-simulation](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/classical-simulation) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-122** [hardware](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/hardware) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-123** [quantum-circuit-optimization](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/quantum-circuit-optimization) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-124** [error-mitigation](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/error-mitigation) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-125** [utility-i](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/utility-i) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-126** [utility-ii](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/utility-ii) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-127** [utility-iii](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/utility-iii) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### quantum-business-foundations

- [ ] **IBM-128** [start-your-quantum-journey](https://quantum.cloud.ibm.com/learning/en/courses/quantum-business-foundations/start-your-quantum-journey) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-129** [introduction-to-quantum-computing](https://quantum.cloud.ibm.com/learning/en/courses/quantum-business-foundations/introduction-to-quantum-computing) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-130** [quantum-computing-fundamentals](https://quantum.cloud.ibm.com/learning/en/courses/quantum-business-foundations/quantum-computing-fundamentals) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-131** [quantum-technology](https://quantum.cloud.ibm.com/learning/en/courses/quantum-business-foundations/quantum-technology) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-132** [business-impacts](https://quantum.cloud.ibm.com/learning/en/courses/quantum-business-foundations/business-impacts) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-133** [how-to-become-quantum-ready](https://quantum.cloud.ibm.com/learning/en/courses/quantum-business-foundations/how-to-become-quantum-ready) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### designing-and-leading-quantum-projects

- [ ] **IBM-134** [introduction](https://quantum.cloud.ibm.com/learning/en/courses/designing-and-leading-quantum-projects/introduction) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-135** [early-stages](https://quantum.cloud.ibm.com/learning/en/courses/designing-and-leading-quantum-projects/early-stages) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-136** [standing-up-team](https://quantum.cloud.ibm.com/learning/en/courses/designing-and-leading-quantum-projects/standing-up-team) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **IBM-137** [grant-writing](https://quantum.cloud.ibm.com/learning/en/courses/designing-and-leading-quantum-projects/grant-writing) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### ibm_module

- [ ] **MOD-001** [quantum-mechanics/get-started-with-qiskit](https://quantum.cloud.ibm.com/learning/en/modules/quantum-mechanics/get-started-with-qiskit) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **MOD-002** [quantum-mechanics/superposition-with-qiskit](https://quantum.cloud.ibm.com/learning/en/modules/quantum-mechanics/superposition-with-qiskit) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **MOD-003** [quantum-mechanics/stern-gerlach-measurements-with-qiskit](https://quantum.cloud.ibm.com/learning/en/modules/quantum-mechanics/stern-gerlach-measurements-with-qiskit) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **MOD-004** [quantum-mechanics/exploring-uncertainty-with-qiskit](https://quantum.cloud.ibm.com/learning/en/modules/quantum-mechanics/exploring-uncertainty-with-qiskit) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **MOD-005** [quantum-mechanics/bells-inequality-with-qiskit](https://quantum.cloud.ibm.com/learning/en/modules/quantum-mechanics/bells-inequality-with-qiskit) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **MOD-006** [computer-science/deutsch-jozsa](https://quantum.cloud.ibm.com/learning/en/modules/computer-science/deutsch-jozsa) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **MOD-007** [computer-science/grovers](https://quantum.cloud.ibm.com/learning/en/modules/computer-science/grovers) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **MOD-008** [computer-science/quantum-teleportation](https://quantum.cloud.ibm.com/learning/en/modules/computer-science/quantum-teleportation) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **MOD-009** [computer-science/quantum-key-distribution](https://quantum.cloud.ibm.com/learning/en/modules/computer-science/quantum-key-distribution) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **MOD-010** [computer-science/qft](https://quantum.cloud.ibm.com/learning/en/modules/computer-science/qft) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **MOD-011** [computer-science/shors-algorithm](https://quantum.cloud.ibm.com/learning/en/modules/computer-science/shors-algorithm) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
- [ ] **MOD-012** [computer-science/vqe](https://quantum.cloud.ibm.com/learning/en/modules/computer-science/vqe) — P2 / AUD-03; full audit pending; evidence: not yet recorded.
### qbraid_notebook

- [ ] **QB-001** [PyQASM-Examples/deutsch_josza_unroll.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/PyQASM-Examples/deutsch_josza_unroll.ipynb) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **QB-002** [PyQASM-Examples/qasm_processing.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/PyQASM-Examples/qasm_processing.ipynb) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **QB-003** [PyQASM-Examples/qasm_unroll.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/PyQASM-Examples/qasm_unroll.ipynb) — P1 / AUD-01; unchanged adder passes packaged classical import, editor source/history/save/reopen and sampled result 10111 in REL-14; complete notebook and runtime-array acceptance remain open; [evidence](learning-evidence/QB-003.md).
- [ ] **QB-004** [qBraid-Algorithms/bernstein_vazirani.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Algorithms/bernstein_vazirani.ipynb) — P1 / AUD-01; partial cell audit; include support is partial; remaining editor export/equivalence work is DEV-16; notebook/cloud execution remains DEV-13/15; [evidence](learning-evidence/QB-004.md).
- [ ] **QB-005** [qBraid-Algorithms/qft.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Algorithms/qft.ipynb) — P1 / AUD-01; partial source audit; numerical unitary checks passed. Full imported inverse-QFT exact measurement execution and GUI result handling passed in REL-13; the historical timeout is resolved. Python execution, provider/submission/results/histogram cells and complete notebook workflow remain unverified; [evidence](learning-evidence/QB-005.md).
- [ ] **QB-006** [qBraid-Algorithms/qpe.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Algorithms/qpe.ipynb) — P1 / AUD-01; original three-counting-qubit program passes shipped exact execution and eight-probability reference checks; external generator still omits eigenstate preparation, so the intended notebook result remains unverified; original and diagnostic sampling recorded; [evidence](learning-evidence/QB-006.md).
- [ ] **QB-007** [qBraid-Algorithms/cirq_vqe.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Algorithms/cirq_vqe.ipynb) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **QB-008** [qBraid-Algorithms/ibm_batch_jobs_grovers.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Algorithms/ibm_batch_jobs_grovers.ipynb) — P1 / AUD-01; full audit pending; evidence: not yet recorded.
- [ ] **QB-009** [qBraid-SDK/bell_circuit_examples.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-SDK/bell_circuit_examples.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-010** [qBraid-SDK/qbraid_sdk_devices.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-SDK/qbraid_sdk_devices.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-011** [qBraid-SDK/qbraid_sdk_transpiler.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-SDK/qbraid_sdk_transpiler.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-012** [qBraid-SDK/qbraid_sdk_transpiler_braket_qiskit.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-SDK/qbraid_sdk_transpiler_braket_qiskit.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-013** [qBraid-SDK/qbraid_sdk_transpiler_cirq_stim.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-SDK/qbraid_sdk_transpiler_cirq_stim.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-014** [qBraid-SDK/qbraid_visualization.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-SDK/qbraid_visualization.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-015** [qBraid-QIR/autoqasm_deutsch_jozsa.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-QIR/autoqasm_deutsch_jozsa.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-016** [qBraid-QIR/qbraid_qir_sim_batch_jobs.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-QIR/qbraid_qir_sim_batch_jobs.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-017** [qBraid-QIR/qbraid_transpiler_braket_to_qir.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-QIR/qbraid_transpiler_braket_to_qir.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-018** [qBraid-QIR/qir_to_squin_conversion.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-QIR/qir_to_squin_conversion.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-019** [qBraid-Runtime/aws_sim_qiskit_bernstein_vazirani.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Runtime/aws_sim_qiskit_bernstein_vazirani.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-020** [qBraid-Runtime/ibm_quantum_jobs_with_runtime.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Runtime/ibm_quantum_jobs_with_runtime.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-021** [qBraid-Runtime/qbraid_pulser_pasqal.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Runtime/qbraid_pulser_pasqal.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-022** [qBraid-Runtime/qbraid_runtime_batch_jobs.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Runtime/qbraid_runtime_batch_jobs.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-023** [qBraid-Runtime/qbraid_runtime_bloqade_aquila.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Runtime/qbraid_runtime_bloqade_aquila.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-024** [qBraid-Runtime/qbraid_runtime_qbraid_provider_aws_devices.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Runtime/qbraid_runtime_qbraid_provider_aws_devices.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-025** [qBraid-Runtime/quobly_alloy_forge_quickstart.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Runtime/quobly_alloy_forge_quickstart.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-026** [qBraid-Runtime/quobly_ghz_noise_benchmark.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Runtime/quobly_ghz_noise_benchmark.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-027** [Provider-Jobs/qbraid_runtime_braket_provider.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/Provider-Jobs/qbraid_runtime_braket_provider.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-028** [Provider-Jobs/qbraid_runtime_ionq_provider.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/Provider-Jobs/qbraid_runtime_ionq_provider.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-029** [Provider-Jobs/qbraid_runtime_oqc_provider.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/Provider-Jobs/qbraid_runtime_oqc_provider.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-030** [Provider-Jobs/qbraid_runtime_pasqal_provider.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/Provider-Jobs/qbraid_runtime_pasqal_provider.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-031** [Provider-Jobs/qbraid_runtime_qiskit_provider.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/Provider-Jobs/qbraid_runtime_qiskit_provider.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-032** [Provider-Jobs/qbraid_runtime_quantinuum_provider.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/Provider-Jobs/qbraid_runtime_quantinuum_provider.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-033** [Provider-Jobs/qbraid_runtime_rigetti_provider.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/Provider-Jobs/qbraid_runtime_rigetti_provider.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-034** [qBraid-CUDAQ/cuda_quantum_qpu_benchmarking.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-CUDAQ/cuda_quantum_qpu_benchmarking.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.
- [ ] **QB-035** [qBraid-CUDAQ/cuda_quantum_quickstart.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-CUDAQ/cuda_quantum_quickstart.ipynb) — P2 / AUD-04; full audit pending; evidence: not yet recorded.

## Discovery checklist (outside the 184 pinned rows)

- [ ] DISC-01 — Reconcile all current IBM course/module/learning-path catalogs with the 2026-10-14 inventory; record added/removed/changed URLs.
- [ ] DISC-02 — Inventory IBM overview pages, exams, practice content, videos, downloadable notebooks and linked tutorials; assign stable IDs and source-specific audit tasks.
- [ ] DISC-03 — Reconcile qBraid demo repository HEAD with the pinned `86787e1ba372facc224f925189755e69c479828b` snapshot; record changed notebook hashes and new/deleted paths.
- [ ] DISC-04 — Inventory qBraid SDK, PyQASM, QIR, Algorithms and runtime syntax references beyond demonstration notebooks; separate syntax support from provider execution.
- [ ] DISC-05 — Inventory qBook courses and chapters through authorized access; record unavailable/account-only content as access-blocked rather than complete.

Catalog entry points checked 2026-10-19: [IBM Learning](https://quantum.cloud.ibm.com/learning/en), [qBraid documentation](https://docs.qbraid.com/v2/home/introduction), [qBraid demos](https://github.com/qBraid/qbraid-lab-demo). This check confirms entry points only, not that their entire content has been audited.

## Updating priorities and progress

1. Select a ready ID from the priority table. Add an owner and a linked issue/PR when work starts; split L items into independently testable child IDs.
2. Link the exact source example and failing regression before changing code. Record whether it needs parsing, algebra, GUI, importer, or execution work.
3. Review the final commit and run risk-appropriate CI. Fix release regressions before additional feature work.
4. Record implementation, merge and release separately. Tick a development item only after its acceptance criteria and released-artifact checks pass.
5. Update affected source evidence records, then tick only fully audited source rows. Report completed/total inventoried rows alongside unresolved discovery tasks; never label that ratio overall goal completion.
