# QB003 clean native build follow-up

The native initial-reset fix at revision
`ae30847d2c5033638027097ee6966134b42742b4` now has clean-source Windows build
evidence in addition to the earlier overlay build. This exact revision predates
the selected-setup runtime change; it is not a clean-build claim for later commits.

A fresh Git archive supplied 793 tracked files in a new build directory. No
project object files or libraries were reused. The unchanged `windows/build-native.sh`
compiled the library and worker with the recorded MSYS2/UCRT64 toolchain and ran
the native suite: **94 passed, one existing `threadtest` skip, zero failures or
errors**. The fresh phase-circuit executable passed all 128 checks. Logs and
individual test verdicts are retained outside the build tree.

Both unchanged QB003 programs (original and PyQASM-unrolled) also passed exact
and sampled checks through the freshly built compiler/worker path and saved-model
reload: exact probability 1 and 10,000/10,000 shots at `10111`. The compiler is
the original Python source from this clean archive, executed in the retained
compiler environment; this is not a newly frozen compiler or GUI package.

Worker SHA-256:
`89694175ee99a6aa3a968c7f694c24c676ec7c8c0b88f5c82941f9dc8dd6c1ed`.
The retained worker copy and native-result records match that same hash.

All 793 original files were checked after the build. There were 22 changes,
limited to `ABOUT-NLS`, `INSTALL` and generated translation/documentation files
allowed by the packaging workflow; no other tracked input changed.

`make dist-gzip` generated `libqalculate-5.13.1.tar.gz`, SHA-256
`7d53aec33d73a3050211540f3cfd144ac4fc65034a16f1411b6afe028240605c`.
The unchanged source-distribution verifier then checked **461 quantum build,
test and research inputs** byte-for-byte and checked for forbidden build outputs. An isolated Git index loaded from the archived revision supplied
the tracked-file inventory for the exported source tree.

## Preserved attempts and limits

The first generic attempt was deliberately stopped before compilation in favor
of the repository's Windows build script. The second attempt completed native
build/tests and source-archive generation, but its final Python verifier could
not locate Git in the MSYS-launched environment and exited 1. That exit is
preserved. The final verifier rerun from the native environment, using the private
revision index, passed; no native rebuild or changed-source substitution was used.

The [evidence index](clean-build.json) binds 224 retained artifacts under
`cleanup-audit/learning-coverage-20261117/qb003-clean-build/`. The build source at
`.tools/qb003-clean-build-20261117/source` remains an active candidate dependency
for follow-on acceptance. Root `dist` was not used.

This closes the local clean-native-build gap for the QB003 reset fix. Hosted CI,
frozen-compiler/package verification, exact GUI acceptance and release remain
pending. QB003 and the broader learning checklist remain open.
