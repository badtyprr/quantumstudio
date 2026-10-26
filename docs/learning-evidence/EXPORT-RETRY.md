# Transient atomic export replacement

The first clean DEV-03 package at `26bed7a5da1a03b44b6e715dcffd39a4b77590e6` stopped in `test-classical-module-export.py`, case `oracle-0`. The saved GUI report identifies `ClassicalQasmExport.SaveTo` and Windows error 1175 (unable to remove the replaced file). This is the same intermittent export failure previously recorded during GUI checks.

## Diagnosis and acceptance

The minimized probe invokes the actual `ClassicalQasmExport.SaveTo` with a prepared byte snapshot, a newly written destination, and no GUI or compiler. In 1,000 attempts it reproduced 37 failures, all code 1175. Every failure preserved the original destination and every immediate repeated operation succeeded. A separate initial 100-attempt probe reproduced one failure with the original preserved.

Hypotheses considered: a transient filesystem/access race after closing the destination; an application-owned handle leak; a persistent path/permission failure. Reproduction without the GUI or compiler excludes their handle lifetimes as a prerequisite. Recovery on the same path excludes a persistent permission/path failure in these cases. The identity of the underlying filesystem or external process causing the transient refusal is not established.

[Microsoft's ReplaceFile contract](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilea) specifies that error 1175 retains both original filenames. Errors 1176 and 1177 can change the file layout and must not be retried as if the original state were intact.

Acceptance: retain the flushed temporary snapshot and retry sharing violations (32), lock violations (33), and error 1175 at most five times after the initial attempt, with 200 ms between attempts. Preserve atomic replacement. Persistent or other errors must propagate; failed writes must clean up the temporary and preserve the original where the filesystem contract permits it. Do not change source validation, GUI test deadlines, compiler behavior, or destination selection.

`windows/ClassicalQasmExportTests.cs` retains the persistent exclusive-lock and invalid-destination checks, and adds a temporary exclusive lock released by another thread. The temporary-lock test failed against the original implementation before adding the retry. This exercises the real save path and file-sharing behavior, not a mocked retry counter.

After the fix, all 18 atomic export checks passed, including persistent-lock preservation and temporary-lock recovery. The same minimized 1,000-attempt probe reported zero failures. Full GUI/module-export validation, scoped review, CI and a fresh release package remain delivery gates; a passing probe does not identify or repair the underlying source of transient filesystem refusal.
