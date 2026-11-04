# QB030: selected original pulse and authored local simulation

Prepared on `a24352a11ca34434954ae37fd9e4761166efcd62`. This six-file increment
contains a contract, witness, SDK-free tests, new profile, exact acquisition lock
and this description. Actual SDK execution is pending. The coordinator owns the
new contract/profile allowlist entries and six distribution registrations; no
existing engine, lifecycle, profile or lock behavior is changed by this packet.

## Source and dependency identity

[Original QB-030 notebook](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/Provider-Jobs/qbraid_runtime_pasqal_provider.ipynb),
revision `86787e1ba372facc224f925189755e69c479828b`, SHA256
`0a4c3302bf7d89f6e40b184fb0b0fb51807443f74d945ab23724d4be09e41414`.
Only unchanged cell6 executes, SHA256
`3755c4578536cecdfc642df00432e7f362a4c2f17090f914eeb792b6c23d39ab`.
It constructs a single q0 atom at (0,0), AnalogDevice/global Rydberg channel,
1000ns Blackman area-pi pulse with zero detuning/phase, and draws the sequence.

| Original cells | Disposition |
|---|---|
| 6 | Selected unchanged construction/drawing; require an embedded image |
| 1 | Unpinned setup excluded; disclosed exact profile used |
| 3,4 | Credential/provider construction and remote discovery excluded |
| 7,8 | Original EMU_FREE200-shot job/result and histogram excluded |
| 0,2,5,9 | Markdown retained, not executable |

All ten identities remain in source-disposition evidence. Selected success never
claims whole-original execution. The source file remains byte-identical, with
original index6 distinguished from the authored witness. The source does not run
any local solver; every simulation below is an authored control.

The new `pulser-win-py312` profile uses Windows Python3.12.10 x64 and the observed
49-distribution binary closure. Its lock SHA256 is
`b04970f6b9552e416caaea4270d7da93089444c527076c2d4f83a61b641f6502`.
Roots include pulser-core/simulation1.10.0, QuTiP5.2.2, NumPy2.2.6,
SciPy1.15.3, Matplotlib3.10.7 and pinned notebook packages. This exact closure was
acquired and installed offline with successful metadata/pip-check reviews; it is
not a minimal profile or proof of SDK/ABI loading. Existing environments are
unchanged. No provider extras, credential object or remote job is used.

## Frozen finite acceptance matrix

The witness checks source register/channel/clock identities, duration, zero
detuning/phase, all1000 amplitude samples and the original sequence's abstract
serialization/reimport. It does not replace the original object for its original-pi
simulation. Reimport must preserve canonical JSON, duration and register order;
the source object's serialization must still match after all authored work.

| Case | Area/phase | Runs and expected outcome |
|---|---|---|
| Original source pulse | pi / 0 | Two authored noiseless, unmodulated simulations of the actual source object |
| Authored zero pulse | 0 / 0 | Two simulations; ground state |
| Authored half pulse | pi/2 / 0 | Two simulations; coherent half rotation |
| Authored phase control | pi/2 / pi/2 | Two simulations; real coherent superposition |
| Authored asymmetric phase | pi/2 /0.37 | Two simulations exposing phase sign |
| Authored over-amplitude control |2pi /0, still1000ns | Explicit ValueError at sequence addition; no simulation or substitution |

Thus five accepted constructions have two solver resolutions each: exactly ten
simulations, no measurement shots. The2pi control's peak14.974879rad/us exceeds
AnalogDevice's4pi≈12.566371rad/us limit plus1e-6validation tolerance. The original
pi peak7.487440fits. Preserve the unsupported case and its diagnostic; do not
stretch duration, change the device or omit the case to obtain a passing result.
The mathematical2pi reference remains valid independently of device rejection.

Both resolutions use pinned `QutipEmulator.from_sequence`, sampling_rate1.0,
evaluation_times Full, with_modulation False and explicit default NoiseModel.
Set all-ground initial state. The deprecated emulator API is intentional for this
versioned compatibility contract; capture its warning, rather than imply current
or future API support. Noiselessness requires an empty effective noise set and
zero collapse operators. Private read-only inspection is protected by hashes of
the installed implementation files; no wrappers or SDK monkey patches are used.

| Solver option | First | Refinement |
|---|---:|---:|
| method | adams | adams |
| atol |1e-10|1e-12|
| rtol |1e-9|1e-11|
| max_step, microseconds |0.001|0.0005|
| nsteps |1000000|1000000|
| store_states |true|true|

These parameters are fixed before execution. Output normalization remains disabled
by the inspected pinned emulator; retrieve raw final state with no basis reduction,
no global-phase removal and normalize=False. Require a two-component ket and
record dimensions, raw values, solver options and warnings. Do not normalize a
state before checking its norm. Failure is retained without adjusting bounds.

## Independent waveform, interpolation and state expectations

Standard-library cosine expansion independently normalizes the discrete Blackman
samples. Explicitly preserve nanoseconds for source duration and microseconds for
area/integration. The emulator coefficient grid must be exactly1001 points from0
to1us at0.001us intervals, with a zero amplitude/detuning endpoint and held phase.
Check actual arrays, not only constructor parameters.

The earlier independent reference has1000 piecewise-constant samples. Pinned
QuTiP instead interpolates coefficients cubically, using SciPy's not-a-knot
boundary condition. The witness implements a scalar second-derivative tridiagonal
solver and integrates each cubic segment analytically; it never asks SciPy/QuTiP
for the expected area. Retain both discrete and cubic areas. Published reference
hashes are embedded in the witness and frozen area values in tests. The independent
six-case reference found a maximum area difference about3.43e-10rad; that is not
an SDK result or a tolerance adjustment.

At seven fixed grid/interior points per simulation, compare all Hamiltonian matrix
entries to the independent cubic coefficient and phase. Public get_hamiltonian
accepts nanoseconds, unlike sampling_times in microseconds; conversion is explicit.
Basis checks require (r,g), r=[1,0], g=[0,1], initial g and unchanged q0 order.
For fixed phase/zero detuning, commuting Hamiltonians give
`(-i exp(i phase) sin(area/2), cos(area/2))`. Compare raw-state density/coherence
against both original-area and cubic-area endpoints; population alone is inadequate.

| Quantity | Predeclared bound |
|---|---:|
| Sample and interior Hamiltonian maximum error |1e-10rad/us|
| Original discrete area error |1e-10rad|
| Cubic minus discrete area |1e-7rad|
| Raw state norm error |1e-8|
| Density Frobenius error, each endpoint reference |1e-5|
| Two-resolution endpoint density difference |1e-7|
| Original pi excited population |at least1−1e-6|

These finite gates do not establish physical noise, modulation, hardware timing,
calibration, interactions, provider execution or universal numerical convergence.
If actual interpolation, channel or API behavior differs, stop and preserve that
unsupported outcome rather than adapt the original source or loosen criteria.

## Preparation and remaining gates

Eleven SDK-free tests run normally and under optimization. They verify source and
witness hashes, all cell dispositions, exact49-package lock, fixed cases/options,
frozen cubic areas, polynomial interpolation/integration, independent sequential
rotations/special points, phase/basis/norm mutations, nonfinite/shape rejection and
the device-limit precondition. Set QB030_ORIGINAL_SOURCE to the retained original
notebook before `python -B -m unittest -v test_qb030`; repeat with `-O`. These tests
do not import Pulser, QuTiP or any scientific SDK.

Independent final implementation and integrated-head reviews precede a reserved
SDK run. Actual acceptance must retain original figures for visual review,
serialization, all coefficients/states/errors, exact source/profile/environment
and owned cleanup. Existing lifecycle evidence can be reused where unchanged;
synthetic tests alone are not process-cleanup or SDK-compatibility evidence.
WholeQB030 additionally requires original setup/provider discovery/job/histogram
and full content interpretation. None is closed by selected local pulse success.
