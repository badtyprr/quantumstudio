# QuantumStudio

A Windows desktop workspace for exploring quantum states, gates and algorithms,
powered by a quantum-notation extension to [libqalculate](https://github.com/Qalculate/libqalculate).
QuantumStudio combines a mathematical calculator with an editable circuit composer,
exact symbolic results and state visualizations.

## Development status

QuantumStudio is under active development. `master` contains the Windows application,
extended quantum calculator, and native/Windows CI. Verified Windows bundles are
built from reviewed merged commits; feature coverage remains incomplete.

Use the [prioritized development and learning checklist](docs/learning-coverage-checklist.md)
to choose the next code task and track IBM Quantum Learning and qBraid audits.
It separates implementation, release status, and whole-source verification, with
acceptance criteria and dependencies for each development item.

## Explore quantum computing

- **Mathematical input:** bra–ket notation, tensor products, matrices, adjoints,
  finite sums and products, and supported TeX fragments.
- **States and operators:** gates, density matrices, partial traces, quantum
  channels, measurement probabilities, entropy and state comparisons.
- **Circuit composer:** editable gates, undo/redo, save/open, and teaching examples
  for Bell states, teleportation, Grover search, phase estimation,
  Bernstein–Vazirani and Simon's algorithm.
- **Visual results:** formatted matrices, probability charts, Bloch vectors and
  Schmidt-coefficient inspection.
- **OpenQASM:** export circuits and import supported bounded OpenQASM 2/3 programs
  through the bundled qBraid PyQASM helper.
- **Everyday calculations:** retain libqalculate's arithmetic, symbolic expressions
  and unit conversion through the ordinary calculator mode.

In the application's **Quantum notation** mode, try:

```text
CNOT (H ⊗ I) |00⟩
⟨0|H|0⟩
|001 ⊕ 101⟩
\frac{1}{\sqrt{2}} (\ket{00}+\ket{11})
```

These produce a Bell state, a single-qubit transition amplitude, a literal
bitwise-XOR basis state, and the Bell state written as a TeX fragment, respectively.
For the development CLI, prefix quantum expressions with `quantum:`:

```powershell
.\dist\QuantumStudio\qalc.exe "quantum:<0|H|0>"
```

## Run a Windows test bundle

If you have a `QuantumStudio-Windows-x64.zip` test bundle, extract the **entire ZIP**
and run `QuantumStudio.exe` from the extracted folder. Keep the worker executable,
DLLs, data directories and `qasm-import` folder beside the application.

The packaged app does not require a separate MSYS2 or Python installation. It uses
Windows .NET Framework 4.x/WPF. A test bundle is not evidence of a published release;
approved releases will appear on the repository's
[Releases page](https://github.com/badtyprr/quantumstudio/releases).

## Build the Windows development application

Use Windows 11 x64 with .NET Framework 4.x/WPF and its C# compiler, MSYS2 UCRT64,
and Python for building the bundled importer. The importer dependencies are pinned
in `windows/qasm-import-requirements.txt`.

Start with the full development checkpoint:

```powershell
git clone https://github.com/badtyprr/quantumstudio.git
cd quantumstudio
git checkout --detach 9c7dc9ded4260ecaee490414e9980311b1943485
python -m venv .tools/qasm-venv
.\.tools\qasm-venv\Scripts\python.exe -m pip install -r windows/qasm-import-requirements.txt
```

In an **MSYS2 UCRT64** shell, install the native toolchain and dependencies:

```sh
pacman -S --needed autoconf automake libtool gettext-devel make \
  mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-gmp \
  mingw-w64-ucrt-x86_64-mpfr mingw-w64-ucrt-x86_64-libxml2 \
  mingw-w64-ucrt-x86_64-pkgconf
```

From the repository directory in that shell:

```sh
bash windows/build-native.sh
```

Then, from the repository directory in PowerShell, build and verify the portable
package. Adjust `-MsysRoot` to your MSYS2 installation:

```powershell
.\windows\package.ps1 -MsysRoot C:\msys64
```

Outputs are `dist/QuantumStudio/QuantumStudio.exe` and
`dist/QuantumStudio-Windows-x64.zip`. Packaging builds the GUI and importer,
collects runtime dependencies and licenses, and runs the release checks.

## Coverage and limits

Research and compatibility work draws on IBM Quantum Learning and qBraid learning
materials. **Complete coverage of their notation and programs has not been
achieved.** Supported syntax, conventions and limits are documented in the
[research and coverage notes](docs/quantum-notation.md)
and [Windows notation guide](windows/Notation-guide.html).
The packaged application also includes an offline guide.

The circuit composer currently supports 1–8 qubits and 512 steps. OpenQASM import
has corresponding circuit limits and a 256 KB source limit. It does not execute
general Python/SDK programs, runtime classical feedback, or pulse/timing programs.
Matrix and state operations have their own documented size and numerical limits;
some use floating-point approximations. QuantumStudio is not a hardware execution
service or an unrestricted symbolic quantum algebra system.

## Contributing and verification

Use small, focused pull requests. `master` requires native build/test CI and a
recorded scoped-review status; protections also apply to administrators. The current
review status records agent self-review, not independent human approval. Releases
must be built from a reviewed, merged revision after their checks pass.

On a Linux development system with the native dependencies installed, the default
branch's build and test path is:

```sh
autoreconf -fi
./configure --disable-shared --enable-static --without-libcurl --without-icu --disable-nls
make -j2
make check
```

The workflow and dependency list are in
[Native CI](.github/workflows/native-ci.yml). Native CI does not by itself verify
the Windows GUI or complete quantum-notation coverage.

## Foundation and license

QuantumStudio builds on the [Qalculate! project](https://qalculate.github.io/).
The underlying library and CLI remain named `libqalculate` and `qalc`; existing
upstream authorship and copyright notices are retained. The original library's
build and CLI documentation remains in [README](README).

The project is licensed under **GPL-2.0-or-later**; see [COPYING](COPYING) and the
source-file notices. Packaged third-party components retain their own licenses,
which are included with the Windows distribution.
