"""Pinned finite Linux regression. No acquisition fallback or product mutation.

Original output/PNG/numerical checks copied unchanged from the provenance-bound
retained_execution.py named in expected.json. All orchestration is explicit here.
"""
import argparse
import ast
import base64
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import select
import shutil
import signal
import stat
import struct
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import uuid
import zlib

HERE = Path(__file__).resolve().parent
EXPECTED = json.loads((HERE / 'expected.json').read_bytes())
CONTRACTS = EXPECTED['contracts']
WINDOWS_REFERENCES = EXPECTED['windows_references']

def require(ok, message):
    if not ok:
        raise ValueError(message)

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def read(path):
    return json.loads(path.read_bytes())

def write(path, value):
    with path.open('xb') as stream:
        stream.write(value if isinstance(value, bytes) else (json.dumps(value, indent=2, ensure_ascii=False)+'\n').encode())

def safe_parts(name):
    parts = PurePosixPath(name).parts
    require(bool(parts) and not PurePosixPath(name).is_absolute() and '/'.join(parts)==name
            and all(p not in ('.','..') for p in parts) and '\\' not in name and ':' not in name, 'Unsafe retained path')
    return parts

def verify_manifest(root, count, complete=True):
    manifest=read(root/'evidence-manifest.json')
    require(len(manifest)==count, 'Unexpected manifest count')
    for name, item in manifest.items():
        path=root.joinpath(*safe_parts(name))
        require(path.is_file() and not path.is_symlink(), 'Missing manifest file')
        expected=item if isinstance(item,str) else item['sha256']
        require(digest(path)==expected, 'Manifest digest mismatch: '+name)
        if isinstance(item,dict):require(path.stat().st_size==item['bytes'], 'Manifest size mismatch')
    if complete:
        actual={f.relative_to(root).as_posix() for f in root.rglob('*') if f.is_file()}
        require(actual==set(manifest)|{'evidence-manifest.json'}, 'Manifest inventory mismatch')
    return manifest

def png(raw):
    require(raw.startswith(b'\x89PNG\r\n\x1a\n'),'Invalid PNG signature')
    require(len(raw)<=32*1024*1024,'Oversized PNG')
    pos=8;dims=None;ended=False;compressed=[]
    while pos<len(raw):
        require(pos+12<=len(raw),'Truncated PNG');n=struct.unpack('>I',raw[pos:pos+4])[0];kind=raw[pos+4:pos+8]
        require(pos+12+n<=len(raw),'Truncated PNG chunk');data=raw[pos+8:pos+8+n]
        require(zlib.crc32(kind+data)&0xffffffff==struct.unpack('>I',raw[pos+8+n:pos+12+n])[0],'PNG CRC mismatch')
        if kind==b'IHDR':require(n==13 and dims is None,'Invalid IHDR');dims=struct.unpack('>II',data[:8]);require(all(dims),'Empty PNG')
        if kind==b'IDAT':compressed.append(data)
        pos+=12+n
        if kind==b'IEND':ended=True;break
    require(ended and pos==len(raw) and dims is not None and compressed,'Incomplete PNG')
    decoder=zlib.decompressobj();pixels=decoder.decompress(b''.join(compressed),64*1024*1024)
    require(bool(pixels) and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,'Invalid/oversized PNG image data')
    return dims

def finite(value, limit=1e-12):
    require(type(value) in (int,float) and math.isfinite(value) and 0<=value<=limit,'Residual out of contract')

def witness(name,w):
    if name=='ibm019':
        require(len(w['checks'])==4 and [r['case'] for r in w['checks']]==[1,2,3,4],'Deutsch cases mismatch')
        for r,truth in zip(w['checks'],[[0,0],[0,1],[1,0],[1,1]]):
            bit=truth[0]^truth[1];require(r['truth']==truth and r['counts']=={str(bit):256} and r['label']==('balanced' if bit else 'constant'),'Deutsch result mismatch');finite(r['state_residual'])
            require(len(r['probabilities'])==2,'Deutsch probability shape')
            for v,e in zip(r['probabilities'],[1-bit,bit]):finite(abs(v-e))
        require([r['input'] for r in w['expected_errors']]==[0,5] and all(r['type']=='ValueError' for r in w['expected_errors']),'Expected errors missing')
    else:
        truth=w['original_generated_truth'];require(len(truth)==8 and all(type(v)==int and v in (0,1) for v in truth),'DJ truth shape')
        finite(w['operator_residual']);finite(w['state_residual']);require(w['label']=='balanced' and sum(truth)==4,'DJ classification mismatch')
        probs=[(sum((-1)**(truth[x]+((x&y).bit_count()%2)) for x in range(8))/8)**2 for y in range(8)]
        require(len(w['expected_probabilities'])==8,'DJ probabilities shape')
        for a,b in zip(probs,w['expected_probabilities']):finite(abs(a-b))
        counts=w['counts'];require(all(re.fullmatch('[01]{3}',k) and type(v)==int and v>=0 for k,v in counts.items()) and sum(counts.values())==4096,'DJ counts mismatch')
        for i,prob in enumerate(probs):finite(abs(counts.get(format(i,'03b'),0)/4096-prob),.05)
        require([r['secret'] for r in w['bv']]==['0000','0001','1000','1011','1111'],'BV witnesses mismatch')
        for r in w['bv']:finite(r['state_residual']);finite(r['operator_residual']);require(r['counts']=={r['secret']:256},'BV counts mismatch')

def audit_run(root, name, environment):
    c=CONTRACTS[name];d=root/name;status=read(d/'status.json');engine=read(d/'engine-result.json')
    require((root/(name+'-exit.txt')).read_text().strip()=='0','Notebook command failed')
    require(status['state']==status['original_execution']==status['authored_verification']=='succeeded','Notebook failed')
    require(engine['state']=='succeeded' and status['source_cells_preserved'] and engine['source_cells_preserved'],'Source preservation not established')
    require(status['external_resources']=='outstanding' and status['interpretation']=='outstanding','External obligations collapsed')
    require(digest(d/'source-original.ipynb')==c['source']['sha256'],'Run source mismatch')
    require(status['identity']==environment['identity'] and status['profile']['id']=='qiskit-aer-linux-py312' and status['contract']==name,'Run environment/contract mismatch')
    records=read(d/'cells.json');nb=read(d/'executed.ipynb');require(len(records)==len(nb['cells']) and [r['index'] for r in records]==list(range(len(records))),'Cell record mismatch')
    original=[r for r in records if r['original_index'] is not None]
    require([r['original_index'] for r in original]==list(range(len(c['source']['cells']))),'Original cell order mismatch')
    for r,expected in zip(original,c['source']['cells']):
        cell=nb['cells'][r['index']];raw=''.join(cell['source']).encode()
        require(r['type']==cell['cell_type']==expected['type'] and hashlib.sha256(raw).hexdigest()==r['source_sha256']==expected['sha256'],'Original cell changed')
        require(r['state']==('succeeded' if expected['type']=='code' else 'not_executable'),'Original cell not complete')
    authored=[r for r in records if r['original_index'] is None]
    roles=(['preamble'] if c['preamble'] else [])+['independent-witness'];require([r['authored_role'] for r in authored]==roles,'Authored roles mismatch')
    for r in authored:
        cell=nb['cells'][r['index']];h=hashlib.sha256(''.join(cell['source']).encode()).hexdigest()
        expected=c['witness']['sha256'] if r['authored_role']=='independent-witness' else hashlib.sha256(c['preamble'].encode()).hexdigest()
        require(r['state']=='succeeded' and h==r['source_sha256']==expected and 'authored-'+r['authored_role'] in cell['metadata']['tags'],'Authored cell mismatch')
    image_dir=root/'rich-images'/name;image_dir.mkdir(parents=True)
    images=[]
    for index in c['required_images']:
        cell=nb['cells'][original[index]['index']];found=0
        for o in cell.get('outputs',[]):
            if 'image/png' in o.get('data',{}):
                raw=base64.b64decode(''.join(o['data']['image/png']),validate=True);dims=png(raw);path=image_dir/(str(index)+'-'+str(found)+'.png');write(path,raw);images.append(dict(cell=index,path=str(path.relative_to(root)),sha256=digest(path),dimensions=dims));found+=1
        require(found>0,'Required drawing missing')
    for index,text in c['required_text'].items():require(any(''.join(o.get('data',{}).get('text/plain',''))==text for o in nb['cells'][original[int(index)]['index']].get('outputs',[])),'Required display text missing')
    w=engine['independent_results'];require(w==status['independent_results'],'Witness status disagreement');witness(name,w)
    reference=WINDOWS_REFERENCES[name]
    write(root/(name+'-windows-comparison.json'),dict(reference_sha256=reference['sha256'],windows=reference['results'],linux=w,identical=w==reference['results'],scope='Observed cross-platform values; existing witness tolerances unchanged, no output-equality requirement'))
    service=read(d/'service.json');gate=service['at_gate']['properties'];client=read(d/'client-identity.json');kernel=read(d/'kernel.json');unit=service['unit']
    require(service['gate_held'] and gate['Id']==unit and gate['Description']==service['description'] and gate['User']=='runner' and int(gate['MainPID'])==service['engine_pid']==status['engine_pid'],'Owned engine identity mismatch')
    require(service['engine_cgroup'].strip()=='0::'+gate['ControlGroup'] and gate['ControlGroup'].endswith('/'+unit),'Engine cgroup mismatch')
    require(service['client']['pid']==client['pid']==status['client_pid'] and service['client']['starttime']==client['starttime'] and service['client']['unit']==unit and service['client']['executable']=='/usr/bin/systemd-run','Client identity mismatch')
    require(kernel['pid']>0 and Path(kernel['executable'])==Path(environment['identity']['executable']),'Kernel identity mismatch')
    require(status['cleanup']['active_processes']==0 and status['cleanup']['kernel_job_membership'] and status['cleanup']['containment']=='systemd_service' and service['population']['empty'],'Owned cleanup incomplete')
    write(root/(name+'-audit.json'),dict(passed=True,original_code_cells=8,original_cells=len(original),authored_roles=roles,images=images,unit=unit,independent_results=w,external_resources='outstanding',interpretation='outstanding'))
    return unit


def error_record(error):
    return dict(type=type(error).__name__, message=str(error))


def cleanup_all(operations, persist):
    """Run every cleanup even when observation or diagnostic persistence fails.

    Return raw failures in memory too: a broken filesystem cannot certify cleanup.
    Persistence is deliberately last and never guards resource operations.
    """
    records = []
    for label, operation in operations:
        try:
            records.append(dict(step=label, result=operation()))
        except BaseException as error:
            records.append(dict(step=label, error=error_record(error)))
    try:
        persist(records)
    except BaseException as error:
        records.append(dict(step='persist_cleanup', error=error_record(error)))
        # Last-resort console evidence has no effect on ownership operations.
        try:
            print(json.dumps(records), file=sys.stderr)
        except BaseException:
            pass
    return records


def clean_report(records):
    require(not any('error' in r for r in records), 'Cleanup or evidence persistence unconfirmed')


def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(), 'Unexpected symlink in source/evidence')
        if path.is_file():
            result[path.relative_to(root).as_posix()] = dict(bytes=path.stat().st_size, sha256=digest(path))
    return result


def verify_sources(root, fixtures=False):
    found = inventory(root)
    found = {k: v for k, v in found.items() if '__pycache__' not in PurePosixPath(k).parts}
    product = {k: v for k, v in found.items() if not k.startswith('regression-fixtures/')}
    require(product == EXPECTED['source_files'], 'Runtime source bytes/inventory changed')
    if not fixtures:
        require(found == product, 'Unexpected authored files')
    return found


def copy_runtime(source, target):
    verify_sources(source)
    require(not target.exists(), 'Fresh runtime required')
    shutil.copytree(source, target)
    verify_sources(target)
    return target


def lock_inventory(raw):
    rows = {}
    for line in raw.splitlines():
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([^\s]+) --hash=sha256:([0-9a-f]{64})', line)
        require(match is not None, 'Malformed lock row')
        name = re.sub('[-_.]+', '-', match[1]).lower()
        require(name not in rows, 'Duplicate normalized lock name')
        rows[name] = match[2]
    require(bool(rows), 'Empty lock')
    return rows


def method_set(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'LinuxLifecycleTests')
    return [n.name for n in cls.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], timeout=20, text=True).strip()


def owned_cleanup(runtime, evidence, require_empty_before=False):
    """Recover only recorded unique units; preserve every raw secondary failure."""
    sys.path.insert(0, str(runtime))
    import linux_lifecycle as lifecycle
    import pwd
    all_rows = []
    for path in sorted(evidence.rglob('service.json')):
        raw = dict(path=str(path))
        def recover():
            saved = read(path)
            raw['saved'] = saved
            unit = saved['unit']
            require(re.fullmatch(r'qalculate-notebook-[0-9a-f]{32}\.service', unit), 'Invalid owned unit')
            require(saved['description'] == 'Qalculate owned engine '+unit
                    and saved['before']['properties']['LoadState'] == 'not-found', 'No unique owned identity')
            current = lifecycle._unit_snapshot(unit)
            raw['current'] = current
            props = current['properties']
            group = None
            if saved.get('gate_held'):
                gate = saved['at_gate']['properties']
                require(gate['Id'] == unit and gate['Description'] == saved['description'], 'Saved gate mismatch')
                relative = Path(gate['ControlGroup'])
                require(relative.is_absolute() and '..' not in relative.parts and relative.name == unit, 'Invalid saved cgroup')
                group = (Path('/sys/fs/cgroup')/str(relative).lstrip('/')).resolve()
                require(group.is_relative_to(Path('/sys/fs/cgroup').resolve()), 'Cgroup escape')
            if props.get('LoadState') != 'not-found':
                require(props.get('Description') == saved['description'] and props.get('User') == pwd.getpwuid(os.geteuid()).pw_name,
                        'Refuse foreign service')
                # An observational failure never prevents stopping a verified unit.
                actions = []
                if group is not None:
                    actions.append(('before_population', lambda: lifecycle._empty_group(group)))
                actions.append(('stop_verified_unit', lambda: lifecycle._command(['sudo', '-n', 'systemctl', 'stop', unit], timeout=15)))
                actions.append(('reset_verified_unit', lambda: lifecycle._command(['sudo', '-n', 'systemctl', 'reset-failed', unit])))
                raw['operations'] = cleanup_all(actions, lambda rows: None)
                clean_report(raw['operations'])
                stop = next(r['result'] for r in raw['operations'] if r['step'] == 'stop_verified_unit')
                require(stop['exit_code'] == 0, 'Owned stop failed')
            if group is not None:
                raw['after_population'] = lifecycle._empty_group(group)
                require(raw['after_population']['empty'], 'Owned cgroup still populated')
                if require_empty_before and 'operations' in raw:
                    before = next(r for r in raw['operations'] if r['step'] == 'before_population')
                    require(before.get('result', {}).get('empty') is True, 'Outer cleanup rescued a live service; not acceptance')
            else:
                # Existing failed-engine-start fixture has no assignment gate.
                # Record unavailable membership rather than fabricate active0.
                after = lifecycle._unit_snapshot(unit)
                raw['unassigned_after'] = after
                require(after['properties'].get('MainPID', '0') == '0', 'Unassigned engine still live')
                raw['population'] = 'unconfirmed: no assignment gate; not a successful kernel run'
            return raw
        rows = cleanup_all([('recover_recorded_unit', recover)], lambda rows:
                write(path.parent/('outer-cleanup-'+uuid.uuid4().hex+'.json'), dict(raw=raw, operations=rows)))
        all_rows.extend(rows)
    clean_report(all_rows)
    return all_rows


def command(argv, cap, log, runtime=None, evidence=None):
    """Finite owned launcher, raw receipt before assertions, cleanup despite writes."""
    process = None
    primary = None
    result = None
    rows = []
    try:
        with log.open('xb') as stream:
            process = subprocess.Popen([str(a) for a in argv], stdout=stream, stderr=subprocess.STDOUT,
                                       env={k: v for k, v in os.environ.items() if k != 'ARTIFACT_TOKEN'})
            result = process.wait(timeout=cap)
    except BaseException as error:
        primary = error
    finally:
        operations = []
        if process is not None:
            def collect():
                if process.poll() is None:
                    process.kill()
                return process.wait(timeout=10)
            operations.append(('collect_owned_launcher', collect))
        if runtime is not None and evidence is not None:
            operations.append(('owned_services', lambda: owned_cleanup(runtime, evidence, require_empty_before=primary is None and result == 0)))
        rows = cleanup_all(operations, lambda data: write(log.with_suffix('.receipt.json'),
                    dict(argv=[str(a) for a in argv], cap_seconds=cap, exit=result,
                         primary=error_record(primary) if primary else None, cleanup=data)))
    if primary is not None:
        raise primary
    clean_report(rows)
    require(result == 0, 'Command failed: '+log.name)


def install_argv(config):
    require(set(config) == {'profile', 'python', 'wheelhouse', 'destination', 'source_root'}, 'Installer fields changed')
    require(config['profile'] in {a['profile'] for a in EXPECTED['artifacts']}, 'Unreviewed installer profile')
    for name in ('python', 'wheelhouse', 'destination', 'source_root'):
        require(Path(config[name]).is_absolute(), 'Installer paths must be absolute')
    return [config['python'], '-B', '-E', '-s', str(Path(config['source_root'])/'run.py'),
            'environment', '--profile', config['profile'], '--python', config['python'],
            '--wheelhouse', config['wheelhouse'], '--destination', config['destination']]


def install_worker(root, control=None, launch=None):
    # Private process entry behind LinuxService.assign, never a shell command.
    # EOF/wrong input prevents venv/pip or even reading the installation request.
    control = sys.stdin if control is None else control
    require(control.readline() == 'start\n', 'Installer gate not released')
    config = read(root/'install-request.json')
    require(Path(config['python']).resolve(strict=True) == Path(sys.executable).resolve(strict=True), 'Installer interpreter mismatch')
    verify_sources(Path(config['source_root']))
    require(not Path(config['destination']).exists(), 'Fresh environment required')
    argv = install_argv(config)
    write(root/'worker-start.json', dict(argv=argv, gate='start', pid=os.getpid()))
    if launch is None:
        launch = lambda args: subprocess.run(args, timeout=300).returncode
    code = launch(argv)
    write(root/'worker-exit.json', dict(exit=code))
    require(type(code) is int and code == 0, 'Public environment command failed')


def contained_install(source, root, config, service_factory=None, popen=None, clock=None):
    """An exact gated LinuxService owns venv/pip descendants, not a broad PGID.

    RuntimeMaxSec300 and the outer300-second wait budget are independent.
    Existing10-second startup,5-second stop and bounded collection/query operations
    may extend cleanup; static I/O has no hard total. Unknown population stays None.
    """
    root.mkdir()
    argv = install_argv(config)
    write(root/'install-request.json', config)
    if service_factory is None:
        sys.path.insert(0, str(source))
        from linux_lifecycle import LinuxService
        service_factory = LinuxService
    popen = subprocess.Popen if popen is None else popen
    clock = time.monotonic if clock is None else clock
    started = clock()
    service = None
    process = None
    primary = None
    code = None
    population = None
    rows = []
    try:
        service = service_factory(root, 300)
        with (root/'launcher.stdout').open('xb') as stdout, (root/'launcher.stderr').open('xb') as stderr:
            command_ = service.command([config['python'], '-I', '-B', str(HERE/'run_regression.py'),
                                        'install-worker', '--root', str(root)])
            process = popen(command_, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, text=True,
                            close_fds=True, env={k: v for k, v in os.environ.items() if k != 'ARTIFACT_TOKEN'})
            service.assign(process)  # Verifies exact main PID/executable/user/unit/cgroup.
            remaining = 300 - (clock() - started)
            require(remaining > 0, 'Installer outer budget expired before gate')
            process.stdin.write('start\n')
            process.stdin.flush()
            code = process.wait(timeout=remaining)
            # Raw terminal code is recorded before the acceptance assertion.
            write(root/'launcher-exit.json', dict(exit=code, elapsed_seconds=clock()-started))
            require(type(code) is int and code == 0, 'Contained installer launcher failed')
            population = service.active()
            require(population == 0, 'Installer returned with live descendants')
    except BaseException as error:
        primary = error
    finally:
        def close_control():
            if process is not None and process.stdin is not None and not process.stdin.closed:
                process.stdin.close()
        operations = [('close_control', close_control)]
        if service is not None:
            # Each method preserves existing exact-unit/pidfd ownership checks.
            operations.append(('terminate_owned_service', service.terminate))
            # LinuxService diagnostics can fail before its stop; independent recovery
            # still checks the recorded unique identity/current description/user.
            operations.append(('recover_recorded_service', lambda: owned_cleanup(source, root, require_empty_before=primary is None)))
            operations.append(('collect_verified_client', service.stop_client))
        if process is not None:
            # Never broad-kill a PGID or user process; this is our Popen handle.
            def collect_launcher():
                if process.poll() is None:
                    process.kill()
                return process.wait(timeout=10)
            operations.append(('collect_owned_launcher', collect_launcher))
        if service is not None:
            operations.append(('observe_owned_population', service.active))
            operations.append(('close_owned_service', service.close))
        rows = cleanup_all(operations, lambda records: write(root/'install-cleanup.json',
                dict(primary=error_record(primary) if primary else None, exit=code,
                     population_before_cleanup=population, operations=records,
                     runtime_seconds=300, outer_budget_seconds=300,
                     scope='Exact transient installer service; no host-wide or session ownership')))
    if primary is not None:
        raise primary
    clean_report(rows)
    observed = [r for r in rows if r['step'] == 'observe_owned_population']
    require(len(observed) == 1 and observed[0].get('result') == 0, 'Installer cleanup population unconfirmed')
    write(root/'install-acceptance.json', dict(passed=True, exit=code, active_processes=0,
          argv=argv, containment='unchanged LinuxService specific cgroup'))


def acquire(root, artifact):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    def deadline(signum, frame):
        raise TimeoutError('Acquisition deadline')
    previous = signal.signal(signal.SIGALRM, deadline)
    signal.alarm(EXPECTED['bounds']['acquisition'])
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        api = 'https://api.github.com/repos/badtyprr/quantumstudio/actions/artifacts/'+str(artifact['id'])
        headers = {'Authorization': 'Bearer '+os.environ['ARTIFACT_TOKEN'],
                   'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
        with opener.open(urllib.request.Request(api, headers=headers), timeout=30) as response:
            raw = response.read(1024*1024+1)
            metadata_status = getattr(response, 'status', None)
        require(len(raw) <= 1024*1024, 'Oversize API response')
        # Public API body only: retain bounded mismatch evidence before parse.
        # Never retain request headers or signed artifact storage redirect URLs.
        write(root/'artifact-api.json', raw)
        write(root/'artifact-api-context.json', dict(endpoint=api, status=metadata_status, bytes=len(raw)))
        metadata = json.loads(raw)
        require(metadata['id'] == artifact['id'] and metadata['expired'] is False
                and metadata['name'] == artifact['name'] and metadata['size_in_bytes'] == artifact['bytes']
                and metadata['digest'] == 'sha256:'+artifact['sha256']
                and metadata['workflow_run']['id'] == artifact['run']
                and metadata['workflow_run']['head_sha'] == artifact['head'], 'Artifact identity mismatch')
        try:
            response = opener.open(urllib.request.Request(api+'/zip', headers=headers), timeout=30)
        except urllib.error.HTTPError as redirect:
            require(redirect.code == 302, 'Expected storage redirect')
            location = redirect.headers.get('Location', '')
            redirect.close()
            parsed = urllib.parse.urlsplit(location)
            require(parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password,
                    'Invalid storage redirect')
            # Fresh request contains no token; this opener refuses further redirects.
            response = opener.open(urllib.request.Request(location), timeout=60)
        with response, (root/'dependency.zip').open('xb') as stream:
            size = 0
            while chunk := response.read(1024*1024):
                size += len(chunk)
                require(size <= artifact['bytes'], 'Oversize dependency')
                stream.write(chunk)
        unpack(root, artifact)
    except Exception as error:
        raise RuntimeError('Dependency unavailable or invalid: '+type(error).__name__) from None
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def unpack(root, artifact):
    archive = root/'dependency.zip'
    require(archive.stat().st_size == artifact['bytes'] and digest(archive) == artifact['sha256'], 'Archive bytes mismatch')
    target = root/'retained'
    target.mkdir()
    with zipfile.ZipFile(archive) as package:
        entries = package.infolist()
        require(len(entries) == artifact['entries'] and sum(e.file_size for e in entries) < 512*1024*1024,
                'Archive inventory/size mismatch')
        seen = set()
        for entry in entries:
            safe_parts(entry.filename)
            require(entry.filename not in seen and not entry.is_dir() and not entry.flag_bits & 1
                    and stat.S_IFMT(entry.external_attr >> 16) in (0, stat.S_IFREG), 'Unsafe archive entry')
            seen.add(entry.filename)
        for entry in entries:
            path = target.joinpath(*safe_parts(entry.filename))
            path.parent.mkdir(parents=True, exist_ok=True)
            with package.open(entry) as src, path.open('xb') as dest:
                shutil.copyfileobj(src, dest)
    verify_manifest(target, artifact['entries']-1)
    base = target/artifact['subdir']
    require(digest(base/'requirements.lock') == EXPECTED['source_files'][artifact['lock']]['sha256'], 'Retained lock mismatch')
    lock_inventory((base/'requirements.lock').read_text())
    wheels = read(base/'wheel-manifest.json')
    require(len(wheels) == artifact['wheels'] and {p.name for p in (base/'wheels').iterdir()} == {r['filename'] for r in wheels},
            'Wheel inventory mismatch')
    for row in wheels:
        require(len(safe_parts(row['filename'])) == 1, 'Invalid wheel name')
        path = base/'wheels'/row['filename']
        require(path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], 'Wheel mismatch')
    if artifact['wheels'] == 54:
        verify_manifest(base, 144)
        status = read(base/'status.json')
        require(status['state'] == 'succeeded' and status['wheels'] == 54 and status['public_wheels'] == 53
                and status['custom_wheels'] == 1 and status['exact_inventory'] and status['imports_verified'],
                'Retained acquisition prerequisite failed')
        for name, contract in CONTRACTS.items():
            require(digest(base/'inputs/sources'/str(name+'.ipynb')) == contract['source']['sha256'], 'Original source mismatch')
        wheel = next(p for p in (base/'wheels').iterdir() if p.name == 'nbclient-0.11.0-py3-none-any.whl')
        with zipfile.ZipFile(wheel) as package:
            client_source = package.read(EXPECTED['deadline']['member'])
            require(hashlib.sha256(client_source).hexdigest() == EXPECTED['deadline']['sha256'],
                    'Deadline implementation changed')
            write(root/'pinned-nbclient-client.py', client_source)


def environment_snapshot(environment):
    # Hash installed bytes, including METADATA/RECORD, native modules and resolved
    # interpreter. Venv symlinks are expected; record their target as well as bytes.
    records = {}
    for path in sorted(environment.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            records[path.relative_to(environment).as_posix()] = dict(bytes=path.stat().st_size, sha256=digest(path),
                symlink=os.readlink(path) if path.is_symlink() else None)
    return records


def load_fixture_module():
    spec = importlib.util.spec_from_file_location('linux_regression_fixtures', HERE/'fixtures.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def worker(args):
    sys.path.insert(0, str(args.runtime))
    verify_sources(args.runtime, fixtures=True)
    if args.kind == 'observer':
        load_fixture_module().run(args.case, args.runtime, args.root, EXPECTED)
        return
    import test_linux_execution
    require(method_set(args.runtime/'test_linux_execution.py') == EXPECTED['lifecycle_methods'], 'Lifecycle methods changed')
    if args.kind == 'lifecycle':
        require(args.case in EXPECTED['lifecycle_methods'], 'Unreviewed lifecycle method')
        args.root.mkdir()
        test_linux_execution.LinuxLifecycleTests.evidence_root = args.root
        suite = unittest.TestSuite([test_linux_execution.LinuxLifecycleTests(args.case)])
    else:
        import test_execution
        suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(getattr(test_execution, name))
                                   for name in EXPECTED['synthetic_classes'])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    require(result.wasSuccessful() and not result.skipped and result.testsRun > 0, 'Finite suite did not pass every test')
    write(args.root.parent/(args.root.name+'-tests.json'), dict(passed=True, tests=result.testsRun, skipped=0))


def bind(args):
    require(sys.platform == 'linux' and platform.machine() == 'x86_64' and platform.python_version() == '3.12.10',
            'Requires Linux x86_64 CPython3.12.10')
    harness = HERE.parents[1]
    require(git(args.product, 'rev-parse', 'HEAD') == EXPECTED['product_revision']
            and git(args.product, 'rev-parse', 'HEAD^{tree}') == EXPECTED['product_tree'], 'Product revision mismatch')
    for checkout in (args.product, harness):
        require(not git(checkout, 'status', '--porcelain', '--untracked-files=all'), 'Dirty checkout')
    require(git(harness, 'rev-parse', 'HEAD') == os.environ['HARNESS_REVISION'] == os.environ['GITHUB_SHA']
            == os.environ['WORKFLOW_REVISION'], 'Harness/workflow/event mismatch')
    require(os.environ['WORKFLOW_REF'].startswith('badtyprr/quantumstudio/.github/workflows/notebook-linux-shared-regression.yml@'),
            'Wrong workflow ref')
    verify_sources(args.product/'windows/dev13-notebooks')
    args.root.mkdir()
    retained = args.root/'harness-source'
    retained.mkdir()
    paths = [HERE/name for name in ('run_regression.py', 'fixtures.py', 'test_regression.py', 'expected.json')]
    paths.append(harness/'.github/workflows/notebook-linux-shared-regression.yml')
    for path in paths:
        shutil.copyfile(path, retained/path.name)
    identity = dict(product_revision=EXPECTED['product_revision'], product_tree=EXPECTED['product_tree'],
                    harness_revision=os.environ['HARNESS_REVISION'], workflow_revision=os.environ['WORKFLOW_REVISION'],
                    workflow_ref=os.environ['WORKFLOW_REF'], run=os.environ['GITHUB_RUN_ID'], attempt=os.environ['GITHUB_RUN_ATTEMPT'],
                    image_os=os.environ.get('ImageOS'), image_version=os.environ.get('ImageVersion'),
                    python=sys.version, executable=sys.executable, executable_sha256=digest(Path(sys.executable)),
                    kernel=platform.platform(), systemd=subprocess.check_output(['systemctl','--version'], text=True, timeout=10),
                    source_files=EXPECTED['source_files'], harness_files=inventory(retained))
    write(args.root/'identity.json', identity)


def run_all(args):
    bind(args)
    root = args.root
    source = args.product/'windows/dev13-notebooks'
    runtime = copy_runtime(source, root/'preflight-runtime')
    command([sys.executable, '-B', '-E', '-s', runtime/'test_linux_execution.py', '--preflight', '--output', root/'preflight'],
            120, root/'preflight.log', runtime, root/'preflight')
    environments = {}
    snapshots = {}
    for artifact in EXPECTED['artifacts']:
        key = str(artifact['wheels'])
        dependency = root/('dependency-'+key)
        dependency.mkdir()
        acquire(dependency, artifact)
        environment = root.parent/(root.name+'-environment-'+key)
        require(not environment.exists(), 'Fresh environment required')
        contained_install(source, root/('install-'+key),
                          dict(profile=artifact['profile'], python=sys.executable,
                               wheelhouse=str(dependency/'retained'/artifact['subdir']/'wheels'),
                               destination=str(environment), source_root=str(source)))
        report = read(environment/'environment.json')
        require(report['state'] == 'succeeded' and report['offline_only'] is True
                and report['identity']['packages'] == lock_inventory((source/artifact['lock']).read_text())
                and len(report['identity']['packages']) == artifact['wheels'], 'Environment inventory mismatch')
        environments[key] = environment
        snapshots[key] = environment_snapshot(environment)
        write(root/('environment-'+key+'-before.json'), snapshots[key])
        shutil.copyfile(environment/'environment.json', root/('environment-'+key+'.json'))
        shutil.copyfile(environment/'install.log', root/('environment-'+key+'-install.log'))
    runtime = copy_runtime(source, root/'synthetic-runtime')
    command([environments['54']/'bin/python', '-B', '-E', '-s', HERE/'run_regression.py', 'worker', '--kind', 'synthetic',
             '--runtime', runtime, '--root', root/'synthetic'], 120, root/'synthetic.log', runtime, root/'synthetic')
    units = []
    for name in CONTRACTS:
        runtime = copy_runtime(source, root/(name+'-runtime'))
        command([sys.executable, '-B', '-E', '-s', runtime/'run.py', 'run', '--contract', name, '--source',
                 root/'dependency-54/retained/acquisition/inputs/sources'/str(name+'.ipynb'), '--environment', environments['54'],
                 '--output', root/name], 720, root/(name+'.log'), runtime, root/name)
        write(root/(name+'-exit.txt'), b'0\n')
        units.append(audit_run(root, name, read(environments['54']/'environment.json')))
    for method in EXPECTED['lifecycle_methods']:
        runtime = copy_runtime(source, root/(method+'-runtime'))
        command([environments['46']/'bin/python', '-B', '-E', '-s', HERE/'run_regression.py', 'worker', '--kind', 'lifecycle',
                 '--case', method, '--runtime', runtime, '--root', root/method], 120, root/(method+'.log'), runtime, root/method)
    for case in EXPECTED['cases']:
        runtime = copy_runtime(source, root/(case+'-runtime'))
        command([environments['54']/'bin/python', '-B', '-E', '-s', HERE/'run_regression.py', 'worker', '--kind', 'observer',
                 '--case', case, '--runtime', runtime, '--root', root/case], 120, root/(case+'.log'), runtime, root/case)
    for key, environment in environments.items():
        after = environment_snapshot(environment)
        write(root/('environment-'+key+'-after.json'), after)
        require(after == snapshots[key], 'Installed environment changed')
    verify_sources(source)
    for runtime in root.glob('*-runtime'):
        verify_sources(runtime, fixtures=True)
        if (runtime/'regression-fixtures').exists():
            require(inventory(runtime/'regression-fixtures') == read(root/(runtime.name[:-8]+'-fixtures.json')), 'Fixture changed')
    retained = root/'harness-source'
    require(inventory(retained) == read(root/'identity.json')['harness_files'], 'Retained harness changed')
    for path in retained.iterdir():
        current = HERE/path.name if path.suffix != '.yml' else HERE.parents[1]/'.github/workflows'/path.name
        require(digest(current) == digest(path), 'Active harness changed')
    all_units = [read(p)['unit'] for p in root.rglob('service.json')]
    require(len(all_units) == len(set(all_units)), 'Reused service unit')
    write(root/'acceptance.json', dict(passed=True, product=EXPECTED['product_revision'], originals=2, original_code_cells=16,
          lifecycle_cases=14, observer_cases=7, visual_review='outstanding', scope=EXPECTED['scope']))


def seal(args):
    args.root.mkdir(exist_ok=True)
    # Include partial install reports on failure without uploading environments.
    for key in ('46', '54'):
        environment = args.root.parent/(args.root.name+'-environment-'+key)
        for name in ('environment.json', 'install.log'):
            source = environment/name
            target = args.root/('partial-'+key+'-'+name)
            if source.is_file() and not target.exists():
                shutil.copyfile(source, target)
    records = inventory(args.root)
    write(args.root/'evidence-manifest-final.json', records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['run', 'worker', 'install-worker', 'seal'])
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--product', type=Path)
    parser.add_argument('--runtime', type=Path)
    parser.add_argument('--kind', choices=['synthetic', 'lifecycle', 'observer'])
    parser.add_argument('--case')
    args = parser.parse_args()
    require(args.root.is_absolute(), 'Absolute evidence path required')
    try:
        if args.mode == 'run':
            run_all(args)
        elif args.mode == 'worker':
            worker(args)
        elif args.mode == 'install-worker':
            install_worker(args.root)
        else:
            seal(args)
    except BaseException as error:
        try:
            args.root.mkdir(exist_ok=True)
            write(args.root/(args.mode+'-failure.json'), error_record(error))
        except BaseException as secondary:
            print(json.dumps(dict(primary=error_record(error), persistence=error_record(secondary))), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
