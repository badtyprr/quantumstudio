"""Seven finite authored fixtures; source ROOT stays the copied immutable runtime.

No SDK import occurs at module load. Runtime entry imports only the selected
installed notebook environment and the unmodified engine after binding it.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import time
import uuid


def require(ok, message):
    if not ok:
        raise ValueError(message)


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def read(path):
    return json.loads(path.read_bytes())


def proc_identity(pid):
    root = Path('/proc')/str(pid)
    return dict(pid=pid, starttime=(root/'stat').read_text().rpartition(')')[2].split()[19],
                cgroup=(root/'cgroup').read_text(), executable=str((root/'exe').resolve(strict=True)))


def validate_ready(ready, identity, nonce, service, live):
    gate = service['at_gate']['properties']
    unit = service['unit']
    relative = gate['ControlGroup']
    require(service['gate_held'] and gate['Id'] == unit and gate['Description'] == service['description'], 'No service ownership')
    require(relative.startswith('/') and '..' not in Path(relative).parts and Path(relative).name == unit, 'Wrong specific cgroup')
    require(ready['nonce'] == nonce and ready['child'] == identity and live
            and identity['cgroup'].strip() == '0::'+relative, 'Child readiness identity mismatch')
    require(ready['popen_pid'] == identity['pid'] and ready['popen_live'] is True, 'No live owned Popen child')


def classify_deadline(record, output, primary, expectation, context):
    lifecycle = context['contract']['observer_lifecycle']
    require(lifecycle['cleanup_timeout_seconds'] == expectation['allowance_seconds'] == 1
            and lifecycle['cleanup']['sha256'] == expectation['cleanup_source_sha256']
            and context['profile']['default_cell_timeout_seconds'] == 10, 'Deadline scheduling context changed')
    error = record.get('error', {})
    require(primary['type'] == 'CellExecutionError' and 'OBSERVATION_PRIMARY' in primary['message'], 'Primary error replaced')
    require(record['state'] == 'failed' and error.get('type') == expectation['error_type']
            and error.get('message') == expectation['message'], 'Unexpected deadline diagnostic')
    require('CLEANUP_STARTED\n' in output and expectation['elapsed_min'] <= record['elapsed_seconds'] < expectation['elapsed_max'],
            'Deadline cause not established by finite observation')
    return dict(classification='pinned_cleanup_deadline_compatible', restoration='unconfirmed',
                diagnostic=error, elapsed_seconds=record['elapsed_seconds'], source_binding=expectation, scheduling_context=context)


CHILD = '''import json,os,pathlib,sys,time
root=pathlib.Path('/proc')
def identity(pid):
 p=root/str(pid)
 return dict(pid=pid,starttime=(p/'stat').read_text().rpartition(')')[2].split()[19],cgroup=(p/'cgroup').read_text(),executable=str((p/'exe').resolve(strict=True)))
parent=identity(os.getppid())
ready=dict(nonce=sys.argv[2],child=identity(os.getpid()))
p=pathlib.Path(sys.argv[1]);t=p.with_suffix('.tmp');t.write_text(json.dumps(ready));t.replace(p)
deadline=time.monotonic()+75
while time.monotonic()<deadline:
 try:
  if identity(parent['pid'])['starttime']!=parent['starttime']: break
 except (FileNotFoundError,ProcessLookupError): break
 time.sleep(.05)
'''


def authored(case, runtime, output, nonce):
    namespace = runtime/'regression-fixtures'
    namespace.mkdir()  # Collisions, including a prior authored namespace, fail.
    def source(name, code):
        path = namespace/name
        with path.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(code)
        return dict(path=path.relative_to(runtime).as_posix(), sha256=hashlib.sha256(code.encode()).hexdigest())
    source('child.py', CHILD)
    bootstrap = source('bootstrap.py', "marker = 'changed'\nprint('BOOTSTRAP_READY')\n")
    cleanup_code = "print('CLEANUP_STARTED', flush=True)\nmarker = 'restored'\nprint('RESTORED')\n"
    if case in ('source_primary_cleanup_error', 'observer_primary_cleanup_error'):
        cleanup_code = "print('CLEANUP_STARTED', flush=True)\nraise RuntimeError('CLEANUP_SECONDARY')\n"
    if case == 'cleanup_deadline':
        cleanup_code = "print('CLEANUP_STARTED', flush=True)\nimport time\ntime.sleep(30)\n"
    cleanup = source('cleanup.py', cleanup_code)
    observer_code = "assert marker == 'changed'\nprint('OBSERVED_FIRST')\n"
    if case == 'observer_failure':
        observer_code += "raise RuntimeError('OBSERVATION_FAILED')\n"
    if case in ('observer_primary_cleanup_error', 'cleanup_deadline'):
        observer_code += "raise RuntimeError('OBSERVATION_PRIMARY')\n"
    if case.startswith('observer_cancel_'):
        # Kernel owns Popen. Ready receipt records that exact handle's PID/poll,
        # and the harness holds a pidfd for that identity through cancellation.
        observer_code += f'''import subprocess,sys,time,json,pathlib
child = subprocess.Popen([sys.executable, '-I', {str(namespace/'child.py')!r}, {str(output/'child-ready.json')!r}, {nonce!r}], close_fds=True)
ready_path=pathlib.Path({str(output/'child-ready.json')!r})
deadline=time.monotonic()+25
while not ready_path.exists():
 if child.poll() is not None: raise RuntimeError('CHILD_EXITED')
 if time.monotonic()>deadline: raise RuntimeError('CHILD_NOT_READY')
 time.sleep(.05)
ready=json.loads(ready_path.read_bytes())
ready.update(popen_pid=child.pid,popen_live=child.poll() is None)
target=pathlib.Path({str(output/'observer-ready.json')!r});temporary=target.with_suffix('.tmp')
temporary.write_text(json.dumps(ready));temporary.replace(target)
print('OBSERVER_CHILD_READY',flush=True)
time.sleep(70)
'''
    observer = source('observer.py', observer_code)
    second = source('observer-second.py', "assert marker == 'changed'\nprint('OBSERVED_SECOND')\n")
    codes = ["print('SOURCE_FIRST', flush=True)", "print('SOURCE_SECOND', flush=True)"]
    if case == 'source_primary_cleanup_error':
        codes[0] += "\nraise RuntimeError('SOURCE_PRIMARY')"
    descriptors = [dict(after_original_index=0, role='postcell-observer', **observer),
                   dict(after_original_index=1, role='postcell-observer', **second)]
    lifecycle = dict(bootstrap=bootstrap, cleanup=cleanup, cleanup_timeout_seconds=1 if case == 'cleanup_deadline' else 5)
    return codes, descriptors, lifecycle


def wait_ready(output, process, timeout=30):
    deadline = time.monotonic()+timeout
    while time.monotonic() < deadline:
        path = output/'observer-ready.json'
        if path.exists():
            return read(path)
        require(process.poll() is None, 'Supervisor exited before readiness')
        time.sleep(.05)
    raise TimeoutError('Child readiness deadline')


def stream_text(cell):
    return ''.join(''.join(o.get('text', '')) for o in cell.get('outputs', []) if o['output_type'] == 'stream')


def supervisor_exit(case, code, persist):
    expected = 0 if case == 'observer_success' else 1
    persist(dict(actual=code, expected=expected, case=case))
    require(type(code) is int and code == expected, 'Unexpected supervisor exit')


def audit(case, output, expected):
    status = read(output/'status.json')
    cells = read(output/'cells.json')
    notebook = read(output/'executed.ipynb')
    engine = read(output/'engine-result.json') if (output/'engine-result.json').exists() else None
    # Raw snapshots have already been written by the product. Preserve a single
    # coherent input receipt before any semantic assertion can fail.
    write(output/'raw-audit-input.json', dict(status=status, cells=cells, notebook=notebook, engine=engine))
    require(len(cells) == 7 and len(notebook['cells']) == 7, 'Fixture cell inventory mismatch')
    require([c['authored_role'] for c in cells] == ['observer-bootstrap', None, 'postcell-observer', None,
            'postcell-observer', 'observer-cleanup', 'independent-witness'], 'Authored ordering mismatch')
    require(cells[0]['state'] == 'succeeded' and 'BOOTSTRAP_READY' in stream_text(notebook['cells'][0]), 'Bootstrap not observed')
    require('SOURCE_FIRST' in stream_text(notebook['cells'][1]), 'First source output lost')
    require(status['cleanup']['active_processes'] == 0 and status['cleanup']['kernel_job_membership'] is True
            and status['cleanup']['containment'] == 'systemd_service', 'Cleanup not confirmed')
    source = read(output/'source-original.ipynb')
    for original, position in enumerate((1, 3)):
        require(cells[position]['original_index'] == original
                and ''.join(notebook['cells'][position]['source']) == ''.join(source['cells'][original]['source'])
                and notebook['cells'][position]['cell_type'] == source['cells'][original]['cell_type'], 'Source changed')
    if case == 'observer_success':
        require(all(c['state'] == 'succeeded' for c in cells), 'Success fixture incomplete')
        require(status['state'] == status['original_execution'] == status['authored_observation']
                == status['authored_verification'] == 'succeeded', 'Success outcome mismatch')
        require(status['independent_results'] == {'restored': True}, 'Restoration witness failed')
    else:
        require(cells[3]['state'] == cells[4]['state'] == cells[6]['state'] == 'not_run', 'Later cells executed')
        require(status['original_execution'] == 'incomplete' and status['authored_verification'] == 'not_run', 'Scopes collapsed')
        if case.startswith('observer_cancel_'):
            force = case.endswith('force0')
            require(status['state'] == 'cancelled' and status['cancellation_requested'] is True
                    and cells[2]['state'] == 'interrupted' and cells[5]['state'] == 'not_run'
                    and status['authored_observation'] == 'interrupted', 'Cancellation outcome mismatch')
            require(status['cleanup']['method'] == ('forced' if force else 'graceful'), 'Cancellation method mismatch')
            require((output/'cancel.request').exists(), 'Cancel receipt missing')
            if engine is not None:
                require(engine['control_event'] == 'cancel_requested', 'Control event missing')
                require(cells[5].get('skip_reason') == 'kernel_interrupted_or_unavailable', 'Cleanup skip reason missing')
            else:
                require(force, 'Graceful cancellation missing report')
            write(output/'cancellation-audit.json', dict(engine_report_present=engine is not None,
                  checkpoint_recovery=engine is None, restoration='unconfirmed', method=status['cleanup']['method']))
        else:
            require(status['state'] == 'failed' and engine is not None, 'Failure outcome mismatch')
            primary = 'SOURCE_PRIMARY' if case == 'source_primary_cleanup_error' else (
                      'OBSERVATION_FAILED' if case == 'observer_failure' else 'OBSERVATION_PRIMARY')
            require(status['error']['type'] == 'CellExecutionError' and primary in status['error']['message'], 'Primary error replaced')
            require(cells[1]['state'] == ('failed' if primary == 'SOURCE_PRIMARY' else 'succeeded'), 'Source state mismatch')
            require(status['authored_observation'] == ('not_run' if primary == 'SOURCE_PRIMARY' else 'failed'), 'Observation state mismatch')
            if case == 'observer_failure':
                require(cells[5]['state'] == 'succeeded' and 'RESTORED' in stream_text(notebook['cells'][5]), 'Cleanup not completed')
            elif case == 'cleanup_deadline':
                classification = classify_deadline(cells[5], stream_text(notebook['cells'][5]), status['error'], expected['deadline'], read(output/'engine-request.json'))
                write(output/'deadline-classification.json', classification)
            else:
                require(cells[5]['state'] == 'failed' and cells[5]['error']['type'] == 'CellExecutionError'
                        and 'CLEANUP_SECONDARY' in cells[5]['error']['message'], 'Secondary error missing')
    return dict(passed=True, case=case, scope='Authored Linux observer fixture only')


def run(case, runtime, output, expected):
    require(case in expected['cases'], 'Unknown fixture')
    import execution
    import linux_lifecycle
    import nbformat
    # Import local harness utilities explicitly; never modify execution.ROOT.
    spec = importlib.util.spec_from_file_location('linux_regression_tools', Path(__file__).with_name('run_regression.py'))
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    require(execution.ROOT == runtime, 'Engine ROOT mismatch')
    output.mkdir()
    nonce = uuid.uuid4().hex
    codes, observers, lifecycle = authored(case, runtime, output, nonce)
    write(output.parent/(case+'-fixtures.json'), helper.inventory(runtime/'regression-fixtures'))
    raw = nbformat.writes(nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(c) for c in codes])).encode()
    (output/'source-original.ipynb').write_bytes(raw)
    profile = execution.profile_for('qiskit-aer-linux-py312')
    identity = execution.inspect_environment(Path(sys.executable), profile)
    config = dict(python=sys.executable, identity=identity, contract_sha256='authored-linux-observer-fixture',
          profile=dict(profile, default_cell_timeout_seconds=60 if case.startswith('observer_cancel_') else 10,
                       cancel_grace_seconds=0 if case.endswith('force0') else 5, service_runtime_seconds=90),
          witness="import json; print(json.dumps({'restored': marker == 'restored'}))",
          contract=dict(id=case, source={'sha256': hashlib.sha256(raw).hexdigest()}, code_cells=[0, 1],
                        preamble=None, required_images=[], required_text={}, post_cell_observers=observers,
                        observer_lifecycle=lifecycle))
    write(output/'engine-request.json', config)
    sentinel = None
    process = None
    pidfd = None
    primary = None
    cleanup = []
    try:
        sentinel = subprocess.Popen([sys.executable, '-I', '-u', '-c',
                    'import sys\nfor line in sys.stdin: print(line.strip(),flush=True)'],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, close_fds=True)
        sentinel_before = proc_identity(sentinel.pid)
        with (output/'supervisor.stdout').open('x') as stdout, (output/'supervisor.stderr').open('x') as stderr:
            process = subprocess.Popen([sys.executable, '-B', '-E', '-s', runtime/'test_linux_execution.py',
                                        '--supervise', '--output', output], stdout=stdout, stderr=stderr)
            if case.startswith('observer_cancel_'):
                ready = wait_ready(output, process)
                pidfd = os.pidfd_open(ready['child']['pid'])
                identity = proc_identity(ready['child']['pid'])
                service = read(output/'service.json')
                live = not select.select([pidfd], [], [], 0)[0]
                write(output/'raw-readiness.json', dict(ready=ready, identity=identity, service=service, live=live, nonce=nonce))
                validate_ready(ready, identity, nonce, service, live)
                # Recheck held identity immediately before the only cancel call.
                validate_ready(ready, proc_identity(identity['pid']), nonce, service,
                               not select.select([pidfd], [], [], 0)[0])
                receipt = execution.cancel(output)
                write(output/'cancel-call.json', receipt)
            exit_code = process.wait(timeout=70)
            supervisor_exit(case, exit_code, lambda receipt: write(output/'supervisor-exit.json', receipt))
        semantic = audit(case, output, expected)
    except BaseException as error:
        primary = error
    finally:
        def collect_supervisor():
            if process is not None:
                if process.poll() is None:
                    process.kill()
                return process.wait(timeout=10)
        def observe_sentinel():
            require(sentinel is not None and sentinel.poll() is None, 'Outside-service sentinel lost')
            require(proc_identity(sentinel.pid) == sentinel_before, 'Outside-service sentinel identity changed')
            sentinel.stdin.write('still alive\n')
            sentinel.stdin.flush()
            require(select.select([sentinel.stdout], [], [], 3)[0] and sentinel.stdout.readline() == 'still alive\n',
                    'Sentinel did not respond')
            return dict(boundary='Outside inner notebook service, inside hosted job', identity=sentinel_before, alive=True)
        def collect_sentinel():
            if sentinel is not None:
                try:
                    sentinel.stdin.close()
                finally:
                    if sentinel.poll() is None:
                        sentinel.kill()
                    code = sentinel.wait(timeout=5)
                    sentinel.stdout.close()
                return code
        operations = [('collect_supervisor', collect_supervisor),
                      ('observe_owned_cgroup', lambda: helper.owned_cleanup(runtime, output, require_empty_before=primary is None)),
                      ('sentinel_still_alive', observe_sentinel), ('collect_sentinel_handle', collect_sentinel)]
        if pidfd is not None:
            operations.append(('close_child_pidfd', lambda: os.close(pidfd)))
        cleanup = helper.cleanup_all(operations, lambda rows: write(output/'fixture-cleanup.json',
                          dict(primary=helper.error_record(primary) if primary else None, operations=rows)))
    if primary is not None:
        raise primary
    helper.clean_report(cleanup)
    write(output/'fixture-acceptance.json', semantic)
