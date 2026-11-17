# IBM repository source reconciliation — 2026-11-17

This static discovery compares Qiskit documentation `a500b17f8b1f156a6bba42ab11f90f3104cad6d4` (retained 2026-11-04 research) with `f842259423a7adc9adeafd54153cdb5d3c5b680b`. It does not establish public website visibility or any lesson's execution acceptance. AUD-02 and DISC-01/02 remain open.

## Evidence and coverage

Both recursive tree responses were complete. The `learning/` subtree grew from 197 to 203 files: six additions, 63 modified blobs and no removals. All 149 original IBM source IDs still map to existing paths; 54 rows map to changed files. The [machine record](ibm-catalog-20261117.json) retains these mappings, immutable acquisition URLs, SHA-256 values and positional cell comparisons. All 69 current added/modified files and all 63 previous versions of modified files were downloaded and checked against their respective Git blob identities. The historical catalog evidence manifest's 18 files were rehashed successfully before reuse.

Of the 63 modified files, 48 are notebooks. One of those notebooks has no cell-type/source changes. Two have changed code cells; the remainder have only non-code source changes. Cell comparison is positional: an insertion can shift later indexes, so it is not semantic alignment. Mathematical prose and images still need review even where code is unchanged. Notebook outputs and metadata were not interpreted.

- `utility-scale-quantum-computing/bits-gates-and-circuits.ipynb`, cell 71: the job status request changes from `job_real.status(job_id)` to `job_real.status()`. This is an upstream code change; no provider call was made here.
- `utility-scale-quantum-computing/variational-quantum-algorithms.ipynb`, code cell 77: source bytes change but Python AST structure is equal. Several Markdown cells also change. No runtime compatibility follows from that equality.

Original checklist source URLs remain unchanged. New IDs below identify additional repository lessons; their public routes and complete source acceptance remain to be verified.

## Added resources and acceptance work

| Resource | Stable identity / audit scope |
| --- | --- |
| `courses/practical-near-term-qc/introduction.ipynb` | IBM-138; 11 Markdown cells, no code. Review conceptual claims, formulas, links and media with explicit non-executable rationale; absence of code does not complete the lesson. |
| `courses/tools-for-quantum-advantage/modern-workflows.mdx` | IBM-139; modern error-handling workflows, Samplomatic/addons and embedded IBM video ID 135107080. Inventory and inspect the video and linked references separately; prose says example workflows will be added later. |
| `modules/quantum-mechanics/nmr-with-qiskit.ipynb` | MOD-013; 52 cells, 17 code cells. Qiskit Runtime/Aer, NumPy, SciPy and plotting dependencies; real backend selection at cell 4 and hardware enabled at cell 6. Local mode still derives a simulator from the selected backend and calibration data. |
| `courses/practical-near-term-qc/index.mdx` | Overview discovery asset; lessons/exam described as under development. Not an extra completed lesson. |
| `courses/practical-near-term-qc/_toc.json` | Navigation metadata linking the overview and introduction. Not execution evidence. |
| `courses/tools-for-quantum-advantage/exam.mdx` | Exam landing page linking IBM Training; actual questions, access and badge workflow were not accessed. The page's descriptive text refers to another course in one sentence; retain that source discrepancy rather than treating it as a verified course mapping. |

For MOD-013, require separate evidence for Rabi probability sweeps, T1 decay, Ramsey/echo fitting, chemical-shift/J-coupling spectra, observables/layout mapping and Trotterized evolution. Preserve timing units, actual delay quantization, fit constraints and uncertainty. Source cells 21/31/34 depend on backend coherence/timing information; a noiseless gate-only simulation cannot prove relaxation behavior. Hardware execution, service access, outputs and figures are all unverified. Extracting local construction or providing synthetic calibration would be an explicit adaptation.

## Public access observations

A separate anonymous HTTP check on 2026-11-17 retained the landing, course and module catalog HTML. All returned 200; their extracted learning anchor sets were unchanged from the retained 2026-11-04 catalogs. This does not enumerate JavaScript/modal content, and neither the new near-term course nor NMR module appeared in those catalog HTML bytes.

Direct route checks returned 404 for the near-term course overview and introduction, and 200 for modern-workflows, its course exam landing page and the NMR module. The machine record includes exact URLs, statuses, final URLs, timestamps and response hashes. A 200 response is only an access observation: rendered content equivalence, embedded media, actual exam questions and execution are unverified. A 404 here does not erase the publicly available repository source or establish why the route is unavailable.

## Retention and remaining work

Raw current and prior sources are outside the disposable checkout under `cleanup-audit/learning-coverage-20261117/aud02-ibm-current-sources` and `aud02-ibm-prior-sources`. Repository JSON carries hashes and immutable URLs, not full upstream notebooks. Earlier mappings come from the preserved `cleanup-audit/notebook-lane-20261104/catalog-reconciliation.json`; this new comparison does not replace the original source baseline.

Complete public course/module/learning-path catalogs, the earlier 48 supplementary repository assets, exams/practice/video/download links, reference documentation and authorized qBook discovery remain open. The three appended lesson/module IDs bring tracked rows to 190 when combined with the qBraid reconciliation, with zero whole-source rows closed. No notebook execution, GUI/native test, service submission or release acceptance occurred in this static pass.
