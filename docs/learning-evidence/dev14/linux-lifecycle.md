# Hosted Linux notebook lifecycle

Status: implementation candidate; actual lifecycle acceptance is pending. The earlier hosted capability/dependency probe is verified, but does not certify this backend.

## Source and dependency provenance

Bootstrap run41872076629 at bfe2c8944e329a3b47157593b3601103d3a4a879 used Ubuntu24 image20261101.360.1, Python3.12.10 x86_64. Artifact13343839049 SHA25656070077ff4f05db60ff3ce5681d53dc65162d3f75ff2f8bd3572c8730b5ad9b contains the46binarywheels, original published metadata, exact offline installed inventory, capability evidence and manifest. All were independently verified by both lanes. The committed lock SHA256 is18848dd56acfa26d5a107454eeb30fb38c1388f3eff532254fed9d2b11eba4c4. This profile contains notebook/plotting dependencies only, not CUDA-Q or a quantum framework.

## Proposed implementation boundary

The existing shared run/environment/cancel engine selects LinuxService on Linux. A unique transient systemd service contains the gated engine as its MainPID and its kernel/descendants. The supervisor stays outside. UID, executable, unit properties and cgroup membership must be verified before start is sent. A clean environment removes caller/manager credentials and package settings. KillMode=control-group, ExitType=main and finite RuntimeMaxSec constrain descendants even after main-engine death. This is owned lifecycle control for reviewed code, not hostile-code isolation.

The directly spawned sudo launcher, actual systemd-run client and service engine have separate recorded identities. A finite exec shim records client PID/starttime before replacing itself with systemd-run. Before gate release, privileged inspection verifies executable, exact unit argument, root UID and starttime; a pidfd observes client exit. The client-loss test revalidates identity and signals through a privileged pidfd rather than a numeric-PID search. Client loss closes the control writer and stops the owned service. Actual hosted verification remains required; Popen.pid is never assumed to identify the client.

The engine records control_eof separately from explicit user cancellation. Service runtime deadline, cell timeout, kernel failure and launcher loss remain distinct causes. Cgroup population reports zero/nonempty, not a precise process count. Success requires original/witness acceptance and kernel membership plus empty/removed previously verified cgroup; launcher exit alone is insufficient. A dead supervisor cannot publish a new final status, so the outside test harness records its own cleanup observation separately.

## Hosted tests and invocation

First recreate the isolated environment with the retained wheelhouse using the shared environment CLI and notebook-linux-py312 profile. No floating resolution or CUDA download is required. Run the candidate suite with that environment's Python:

    python windows/dev13-notebooks/test_linux_execution.py --suite --output ABS_NEW_DIRECTORY

The suite refuses non-Linux prerequisites rather than marking them skipped. Authored small-notebook fixtures exercise shared checkpointing, source preservation, rich output, source errors, cell timeout, kernel death, duplicate cancellation, engine SIGKILL, launcher loss, supervisor loss, service deadline and detached double-fork descendants with ignored SIGTERM. Each run uses a spaced Unicode output path and an unrelated responsive sentinel. Gate EOF and wrong-ownership refusal are separate tests. Retain all unit/cgroup/status/checkpoint/stdout/stderr evidence, including failures.

These are authored lifecycle fixtures, not original external framework notebooks. Original IBM019/020 and QB017 remain their separately pinned Windows contracts. The candidate also includes failed-engine startup, bounded concurrent-fork and repeated-run/GC fixtures. All require actual hosted results. Linux public original-framework acceptance remains separate and pending; the current small profile has no quantum framework contract. No current fixture pass may be relabeled a CUDA-Q/provider/hardware pass.

## Current validation and remaining work

On the initial shared implementation, all20existing Windows lifecycle tests passed and the stdlib early-pipe-close regression passed. Review found two reporting defects: missing engine results did not aggregate retained checkpoints, and teardown failures could prevent terminal reporting. Both are addressed in the candidate; three Windows fault-injection tests for stop timeout, ownership refusal and final-close failure passed. Final broader regression/review is pending. Python parsing and diff checks passed. No Linux lifecycle test has yet run on this candidate. Independent implementation review and actual coordinator-hosted execution are required; coordinator owns workflow, distribution registration and dispatch. No local WSL changes, provider credentials/jobs, releases or central checklist edits are included.
