# IBM learning resource discovery

The immutable Qiskit documentation tree at `079769d205eb3b60e077820060274c7b0359c123` contains 203 learning source and navigation files. Each file was verified against its Git blob ID and independently hashed with SHA-256. Compared with the previously audited revision `f842259423a7adc9adeafd54153cdb5d3c5b680b`, no learning paths were added or removed in the repository tree. Forty-three files changed. Forty notebooks changed executable code and 21 changed Markdown cells. Earlier results remain evidence for their recorded revisions. Each changed path and both digests are in ibm-catalog-delta.json.

The public English course and module directories showed the same 15 course and 12 module URLs as the original October inventory. The public learning home linked six multi-resource path topics. Eleven level-specific routes were independently observed. On November 21 the public path dialogs listed one introductory path and eleven named levels across the other five topics. Expanding every lesson list recovered 116 lesson links under 49 ordered material entries across all twelve paths. The [path inventory](ibm-interactive-paths.json) retains placement and repeated appearances. It omits only the path-tracking parameter from destination URLs. The October inventory did not enumerate individual path placements, so their historical change dates are unknown. [Courses](https://quantum.cloud.ibm.com/learning/en/courses) · [Modules](https://quantum.cloud.ibm.com/learning/en/modules) · [Learning paths](https://quantum.cloud.ibm.com/learning/en)

## Resource queue

ibm-resource-inventory.json lists 1,752 typed targets. Each target has an ID derived from its type and address, references to its source files and zero-based notebook cells, and an audit task for its type. A zero cell for MDX or navigation JSON denotes the whole file. The origins array supplies source paths and digests. Notebook targets beginning with github: identify repository paths at the inventory revision. IBM video targets retain the component's video ID. Targets may have more than one source.

| Resource | Targets |
| --- | ---: |
| Exam | 26 |
| Image | 426 |
| Notebook | 141 |
| Overview | 19 |
| Practice headings | 148 |
| Code cells marked for the learner | 10 |
| Practice assigned in ordinary paragraphs | 49 |
| Tasks within numbered exercises | 4 |
| Solutions within numbered exercises | 3 |
| Expandable answers, hints and practice questions | 178 |
| Expandable readings | 19 |
| Reference | 606 |
| Tutorial | 17 |
| Video | 106 |

The ten code cells retain explicit learner markers. Several already contain IBM's solution, including the XX, HH and HZH circuits. Each cell has one target even when the marker appears on several lines. The first thirteen prose paragraphs explicitly assign independent work, including a commutator calculation, a channel check and five parts of the utility-scale simulation. Fourteen additional paragraphs ask learners to carry out a specific task, including constructing a teleportation circuit, trying different kernel feature maps, and deriving a measurement identity. Their resource IDs use the notebook cell and a digest of the paragraph, so earlier assignments retain their IDs. A prompt and its solution cell can be separate targets. Additional exercise wording and external resources remain under review.

Nine numbered section headings identify exercises, including a QFT calculation and a second-order Suzuki–Trotter simulation. Its four tasks cover circuit construction, evolution, plotting and comparison with exact results. Three solution sections are indexed under the phase-estimation and variational exercises. Practice detection covers explicit exercise headings and all 197 expandable panels in this revision. Panels include 171 answer keys, two sets of hints, one guidance panel, four questions named in their titles, and 19 supplementary readings. Each panel has a source location and a separate audit task. A question heading and its answer panel can belong to the same exercise. A prose question without a label may require manual inventory. The queue includes the 69 distinct IBM video IDs, external video links, overview pages, assessment pages and launch destinations, notebook sources, illustrations and tutorial links. Ordinary links remain reference-review tasks. External destinations, authenticated assessment content, playback and exercises still require source-specific acceptance.

To rebuild, run fetch-learning-resources.py with a cache directory. Run inventory-learning-resources.py with that directory and an output JSON path using Python with markdown-it-py 3.0.0, linkify-it-py 2.0.3 and uc-micro-py 1.0.3. The fetcher defaults to this immutable revision and verifies every expected blob. The generator skips fenced code and indexes prose inside MDX components. The public URL observations are recorded separately from repository content.

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

### Verification prompts

The November 27 pass found 22 further learner prompts across 11 notebooks. These include verifying channel completeness, identifying an oracle from measurements, decrypting a short message with different keys, and proving individual gate identities. Each prompt has a content-derived identifier and a source-cell location. Regenerating the inventory preserved all 1,696 prior resource records. A numbered instruction in Shor's factoring procedure to check a modular condition was reviewed as an algorithm step.

On published checkpoint `c5a456cd`, the XY4 exercise in cell 24 gave 1 for `Y*X*Y*X==-I`, 0 for equality with the positive identity, and 0 for `Y*X*Y==-I` with one pulse omitted. The matrix comparison covers arbitrary inputs. The source's intermediate expansion of the plus state omits its common normalization factor. [Pinned exercise](https://github.com/Qiskit/documentation/blob/079769d205eb3b60e077820060274c7b0359c123/learning/courses/tools-for-quantum-advantage/error-suppression.ipynb)

### CNOT twirling exercise

Cell 26 of the error-suppression notebook asks for a second sequence that preserves CNOT. With the control as the first tensor factor, the supplied answer puts Z on the target before CNOT and Z on both wires afterward. The worker returned 1 for `qtensor(Z,Z)*CNOT*qtensor(I,Z) = CNOT`. It also returned 1 for the worked fourth panel, `qtensor(Y,Z)*CNOT*qtensor(X,Y) = CNOT`. Omitting the final control Z gave 0 for `qtensor(I,Z)*CNOT*qtensor(I,Z) = CNOT`: the two amplitudes with control 1 changed sign. These exact matrix comparisons cover all input states on candidate `897b5681`. [Pinned exercise and answers](https://github.com/Qiskit/documentation/blob/079769d205eb3b60e077820060274c7b0359c123/learning/courses/tools-for-quantum-advantage/error-suppression.ipynb).

### Web addresses in lesson prose

The generator also recognizes explicit web addresses written as ordinary text.
This recovered 32 references and two tutorials, including the Rustworkx
betweenness-centrality exercise and Quantinuum's Fe4N2 example. All 43 added
source locations were checked against the literal addresses in 13 pinned files.
The registry records where learners encounter each address and the follow-up
task for its resource type. The Rustworkx tutorial passed all four original code blocks. An independent NetworkX calculation matched all 48 node scores on the 63-edge lattice, and all three graph drawings rendered. The Quantinuum example remains open. [Rustworkx execution evidence](rustworkx-centrality-replay.json).
