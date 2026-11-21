# IBM learning resource discovery

The immutable Qiskit documentation tree at `079769d205eb3b60e077820060274c7b0359c123` contains 203 learning source and navigation files. Each file was verified against its Git blob ID and independently hashed with SHA-256. Compared with the previously audited revision `f842259423a7adc9adeafd54153cdb5d3c5b680b`, no learning paths were added or removed in the repository tree. Forty-three files changed. Forty notebooks changed executable code and 21 changed Markdown cells. Earlier results remain evidence for their recorded revisions. Each changed path and both digests are in ibm-catalog-delta.json.

The public English course and module directories showed the same 15 course and 12 module URLs as the original October inventory. The public learning home linked six multi-resource path topics. Eleven level-specific routes were independently observed. On November 21 the public path dialogs listed one introductory path and eleven named levels across the other five topics. Expanding every lesson list recovered 116 lesson links under 49 ordered material entries across all twelve paths. The [path inventory](ibm-interactive-paths.json) retains placement and repeated appearances. It omits only the path-tracking parameter from destination URLs. The October inventory did not enumerate individual path placements, so their historical change dates are unknown. [Courses](https://quantum.cloud.ibm.com/learning/en/courses) · [Modules](https://quantum.cloud.ibm.com/learning/en/modules) · [Learning paths](https://quantum.cloud.ibm.com/learning/en)

## Resource queue

ibm-resource-inventory.json lists 1,446 typed targets. Each target has an ID derived from its type and address, references to its source files and zero-based notebook cells, and an audit task for its type. A zero cell for MDX or navigation JSON denotes the whole file. The origins array supplies source paths and digests. Notebook targets beginning with github: identify repository paths at the inventory revision. IBM video targets retain the component's video ID. Targets may have more than one source.

| Resource | Targets |
| --- | ---: |
| Exam | 26 |
| Image | 426 |
| Notebook | 141 |
| Overview | 19 |
| Practice | 139 |
| Reference | 574 |
| Tutorial | 15 |
| Video | 106 |

Practice detection includes explicitly headed questions, quizzes and exercises. A prose question without a label may require manual inventory. The queue includes the 69 distinct IBM video IDs, external video links, overview pages, assessment pages and launch destinations, notebook sources, illustrations and tutorial links. Ordinary links remain reference-review tasks. External destinations, authenticated assessment content, playback and exercises still require source-specific acceptance.

To rebuild, run fetch-learning-resources.py with a cache directory. Run inventory-learning-resources.py with that directory and an output JSON path using Python and markdown-it-py 3.0.0. The fetcher defaults to this immutable revision and verifies every expected blob. The generator skips fenced code and indexes prose inside MDX components. The public URL observations are recorded separately from repository content.

## Runtime API change checks

The updated source imports Sampler and Estimator from the Runtime executor modules. Using Runtime 0.50.0 with local Aer execution, the revised teleportation circuit recovered the input on all 10,000 shots, all four Grover examples matched the expected marked-state probabilities, and phase estimation reproduced the Fourier distributions for phases 1/8 and 1/3. The original requested shot counts were retained. Rerun replay-updated-runtime-examples.py with the source cache's sources directory, ibm-catalog-delta.json and a new output path.

The revised NMR notebook also produced all nine predicted spectral peaks across the AX and AX2 systems on the frozen Manila calibration. The shared replay-mod013-nmr.py runner validates the digest and uses each source revision's own sampler and estimator imports. The local backend replaces provider selection; explicit scheduling reproduces the delay experiments. The results for the newer revision are in mod013-updated-manila-results.json. Hardware verification remains open.

## Definitions stored in notebook metadata

The [supplementary registry](ibm-notebook-metadata.json) covers all 140 notebooks in this revision. It records each definition’s source cell, term, stable identifier and content digest. Rerun `inventory-notebook-metadata.py CACHE OUTPUT` with the same verified source cache as the resource inventory. The table counts occurrences, including repeated terms.

| Lesson | Glossary definitions | Formula definitions |
| --- | ---: | ---: |
| [IBM-090](https://github.com/Qiskit/documentation/blob/079769d205eb3b60e077820060274c7b0359c123/learning/courses/quantum-diagonalization-algorithms/introduction.ipynb) | 3 | 0 |
| [IBM-098](https://github.com/Qiskit/documentation/blob/079769d205eb3b60e077820060274c7b0359c123/learning/courses/quantum-machine-learning/data-encoding.ipynb) | 0 | 12 |
| [IBM-096](https://github.com/Qiskit/documentation/blob/079769d205eb3b60e077820060274c7b0359c123/learning/courses/quantum-machine-learning/introduction.ipynb) | 3 | 0 |
| [IBM-103](https://github.com/Qiskit/documentation/blob/079769d205eb3b60e077820060274c7b0359c123/learning/courses/variational-algorithm-design/ansaetze-and-variational-forms.ipynb) | 2 | 0 |
| [IBM-104](https://github.com/Qiskit/documentation/blob/079769d205eb3b60e077820060274c7b0359c123/learning/courses/variational-algorithm-design/cost-functions.ipynb) | 7 | 0 |
| [IBM-105](https://github.com/Qiskit/documentation/blob/079769d205eb3b60e077820060274c7b0359c123/learning/courses/variational-algorithm-design/optimization-loops.ipynb) | 3 | 0 |
| [IBM-102](https://github.com/Qiskit/documentation/blob/079769d205eb3b60e077820060274c7b0359c123/learning/courses/variational-algorithm-design/reference-states.ipynb) | 1 | 0 |
| [IBM-101](https://github.com/Qiskit/documentation/blob/079769d205eb3b60e077820060274c7b0359c123/learning/courses/variational-algorithm-design/variational-algorithms.ipynb) | 6 | 0 |

For each glossary entry, check its definition and replay embedded mathematical examples. Two computational-basis examples already have [Windows re-entry evidence](../IBM-090.md). For IBM-098, check the notation and spoken descriptions against the corresponding encoding, normalization and tensor-product examples. These are discovery records. Each source row tracks its own acceptance.
