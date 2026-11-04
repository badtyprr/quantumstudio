# Original IBM019/020 Linux profile

The public `ibm019` and `ibm020` contracts select `qiskit-aer-win-py312` on Windows and `qiskit-aer-linux-py312` on Linux. Unsupported platforms reject before source or environment access. Stable contract IDs, every original source and cell hash, authored preamble and witness, required outputs, and Windows profile and lock remain unchanged. QB017 retains its Windows-only profile. No arbitrary profile override or unrestricted notebook execution is added.

The Linux profile uses CPython 3.12.10 on x86_64, Qiskit 2.2.3 and CPU Aer 0.18.2. Its exact 54-package lock is the observed `requirements.lock` from acquisition run `41883503640`, attempt 1, source commit `890eb5b99fc4035fc3fb8144c744ff79bda4d387`, artifact `13350182532`.

- Archive: 117,705,532 bytes; SHA-256 `0ca0632ef9fc390126f52743dc7967c4e6107f9b8428ae5bc8e7d8859ee5d40b`.
- Lock SHA-256: `39206d4cf230cd8b21d46698b72a3092fd4c0d2a5f4eccc7dd18ec2b1ad16769`.
- All 53 public wheel digests and the one retained custom pylatexenc 2.10 wheel were independently verified.
- Resolver pip 26.3 and installed, locked pip 25.3 are distinct recorded versions.
- All 51 Windows package versions are retained, with pexpect, ptyprocess and pip added. This is explicit version parity, not minimal dependency closure.

The custom wheel SHA-256 is `7211b83dc685ec8e5e25d09c5538d867279a4bb41058c00ab12fa8a8250bfcd2`. It is preserved from the original Windows proof. Its pure-Python files match the published source archive, SHA-256 `3dd8fd84eb46dc30bee1e23eaab8d8fb5a7f507347b23e5f38ad9675c84f40d3`. This is an audited retained artifact, not a public PyPI wheel or a claim of byte-reproducible rebuilding.

Create the environment through `run.py environment` with profile `qiskit-aer-linux-py312`, the exact Python version, retained wheelhouse and a fresh destination. It installs offline with hashes and requires the exact inventory. Use the existing public `run` command with contract `ibm019` or `ibm020`, unchanged retained source, that environment and a fresh output directory. The verified systemd backend remains unchanged: a nonroot engine, held startup gate, owned-cgroup cleanup, 120-second per-cell limit, 5-second cancellation grace and 600-second whole-service ceiling.

Acquisition evidence verifies fresh offline installation, the exact 54-distribution inventory and imports of Qiskit, Aer, pylatexenc and nbclient from that environment. Separate authored Linux lifecycle run `41877660516` verified 14 finite cases at product commit `110669471`. Neither gate establishes original IBM notebook execution. At preparation, original Linux code-cell execution and output, state and count comparisons remain **pending**.

Hosted source acceptance must execute all eight original code cells of each notebook unchanged and preserve all 17 or 20 source cells. IBM019 requires images at cells 7 and 11 and the balanced output at cell 15. IBM020 requires images at cells 6, 12 and 15, the balanced output at cell 12 and `1011` at cell 17, retaining its disclosed authored seed-0 preamble. Existing independent witnesses must remain separate, and their results must be compared with retained Windows expectations. Retain original outputs and errors, source hashes, exact environment identity and owned cleanup. Missing or corrupt input must reject without replacement source or relaxed dependencies.

Whole-notebook interpretation, Markdown and page rendering, external mathematical requirements and historical cloud-image equivalence remain separate obligations. No CUDA-Q, provider, hardware, release or whole-lesson acceptance follows from this profile.
