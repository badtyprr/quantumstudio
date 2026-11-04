"""Finite retained Linux original-notebook preparation and evidence audit; no engine replacement."""
import argparse
import ast
import base64
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import signal
import stat
import struct
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import zlib

PRODUCT = '244681403225583af607d6839ec39511d83fc2ab'
SOURCE_HASHES = {'run.py': '227ae70033fe2c36f0bf338631469a85c8e7243d6eb3e4d68df1e1eb201902c0', 'execution.py': '6ed98b8069931d6b2368d49346efc3a861cf46292333eb09ee8b7396713b513b', 'linux_lifecycle.py': '72277c1af6ad0e5615d55589fc852f22232a26b11efa5ee7b5dc9789cd496dc1', 'test_linux_execution.py': '45b3de764f508586ea86e098aa6c2f1508a63b027ccf5b2c5c7593b999c7819e', 'profiles/qiskit-aer-linux-py312.json': '7f429bd7fe023baa5263761e4cc6536eee68a08362d3f5feb72f2d9a6a73f1b7', 'ibm019-linux-requirements.lock': '39206d4cf230cd8b21d46698b72a3092fd4c0d2a5f4eccc7dd18ec2b1ad16769', 'contracts/ibm019.json': '74ece437462fc7408b2b944bc1d98a90bc6172604147e8b65f7f20a7659800a6', 'contracts/ibm020.json': '6366a32c3592d4974eba48f95669c239d49baabead4281e529337e0a64342862', 'witnesses/ibm019.py': 'ce9b6e3b5359582241ccb5ddc38d998171b853f785b66ff38f3792a1b99c9c70', 'witnesses/ibm020.py': '23c20f3c7eeb023170af030ebbe2fb35f7a05f661888ba36dd56eb7a5d451f5d'}
CONTRACTS = {'ibm019': {'version': 1, 'id': 'ibm019', 'route': 'notebook', 'source': {'url': 'https://quantum.cloud.ibm.com/endpoints-docs-learning/raw/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-algorithm.ipynb', 'sha256': 'c9d818b01277230bc0b7ecb64dc41fe54a53de8fcfc84c08818a5051d039567f', 'cells': [{'index': 0, 'type': 'markdown', 'sha256': 'a3155143e8613156279f9d03c7bba3b83bc1aaced25ff48bfc137a920f0cf5d9'}, {'index': 1, 'type': 'markdown', 'sha256': 'f7f66d07663b76f87d6965c90d285cc7cec1ce8bcc43de958352cf787ef30445'}, {'index': 2, 'type': 'code', 'sha256': '79d8fdd9629838715b0c5bbd8a406d66063bef9be6fcf7ed58e63b5c982bcb80'}, {'index': 3, 'type': 'code', 'sha256': '0f8cd08c48a98dd1d530a9045b0c726ac7361de4bd0d8acba93ae00e5518db61'}, {'index': 4, 'type': 'markdown', 'sha256': 'fa373c884d885872e8c8845ea465efa7bd1254bb074c9eb1768c3de7bf40cb39'}, {'index': 5, 'type': 'code', 'sha256': '890c5cf7a475ca211c14a959bfbb5e6accf78c7644c5f3fc68910c2bba9bb87e'}, {'index': 6, 'type': 'markdown', 'sha256': 'ce4b48ac27444e2cd6d5908323f4fed7586e22830e851b297daac555f90c916a'}, {'index': 7, 'type': 'code', 'sha256': 'b7072258896520d0823a1834e24bfe4f8d66486c55aa2b61c423a9938573ae99'}, {'index': 8, 'type': 'markdown', 'sha256': '4baa8eb611932f62c25062a3e704a3b694945b5b2c504f43f562c53b709eda69'}, {'index': 9, 'type': 'code', 'sha256': 'ae6a4337303cc4dcdef6b8c1a0a6ddb156c9260057c54694f97355e3def597b8'}, {'index': 10, 'type': 'markdown', 'sha256': 'd72806450d10501e4524900e5ebe8996a1a5642edd9a1fc1a2230b9e9a8818cb'}, {'index': 11, 'type': 'code', 'sha256': '5cf7801fff08ffc6da621b4ab00f565bf5c268bd13e2058caef62c715100ca96'}, {'index': 12, 'type': 'markdown', 'sha256': '96d9ba626e2b6b246339373dfcaa477d11b3ed08b24f9019445120eeb59ae6b0'}, {'index': 13, 'type': 'code', 'sha256': 'a12dd3741f410b738ec09a1b965ea0e67df188e034ac38a9ce7f536c0d6d6714'}, {'index': 14, 'type': 'markdown', 'sha256': '992056cf3eccf4c30c9e96ceb3b1ff26a8229955909d6d239765ecf39985c878'}, {'index': 15, 'type': 'code', 'sha256': 'e6c54a1d2d0a3aa92f5e029e71fbb3262dd67b9636b6b603b5a0f356c4d18c30'}, {'index': 16, 'type': 'markdown', 'sha256': 'd64da6446fdee316a7c86d823685fb93de9d35b4d326555839b2b18c4769ea65'}]}, 'code_cells': [2, 3, 5, 7, 9, 11, 13, 15], 'preamble': None, 'witness': {'path': 'witnesses/ibm019.py', 'sha256': 'ce9b6e3b5359582241ccb5ddc38d998171b853f785b66ff38f3792a1b99c9c70', 'hash_encoding': 'UTF-8 with LF; authored witness only'}, 'required_images': [7, 11], 'required_text': {'15': "'balanced'"}, 'capabilities': ['local-computation', 'rich-display'], 'external_requirements': ['Original markdown SVG/page rendering', 'Native mathematics and lesson interpretation'], 'source_preservation': 'Original cells retain text/type/order; authored cells have separate provenance', 'profiles': {'win32': 'qiskit-aer-win-py312', 'linux': 'qiskit-aer-linux-py312'}}, 'ibm020': {'version': 1, 'id': 'ibm020', 'route': 'notebook', 'source': {'url': 'https://quantum.cloud.ibm.com/endpoints-docs-learning/raw/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-jozsa-algorithm.ipynb', 'sha256': '513398ae77d7502e7e8c2f2d4bdc85d4a7b5474d25f88a00eb1a2e8a8777586f', 'cells': [{'index': 0, 'type': 'markdown', 'sha256': '92d8d40378e9055ccc93efb79eff921b7decc5326f36a7fd7c27d3b68abd0f83'}, {'index': 1, 'type': 'markdown', 'sha256': 'b1024fb4e8af74bb85f9aea26d7c4d0c83e13630ff0d5c3dd7b8a8357c8af213'}, {'index': 2, 'type': 'code', 'sha256': '55de482fb264ff236ec5f5ce7f6d562ddb37e3be098e1b42bccacf536469f4de'}, {'index': 3, 'type': 'markdown', 'sha256': 'e981f9c38a8c9daf3e5dabb1d831e89c4fcfaa28c879005cb37abe8a0724673f'}, {'index': 4, 'type': 'code', 'sha256': 'a80ceebf7cb87bb6b02a585280d44b650cfc2948df619628c7841e32b9f0fb38'}, {'index': 5, 'type': 'markdown', 'sha256': '9d3ea9cd4c6689c71c53dbaa1a61c0d2622417f0f953e3ecc1a1e301c90fd972'}, {'index': 6, 'type': 'code', 'sha256': '4f844a38e54c0a6aca7bd314a2d08a1b23e5780ae18795e9b634db49901b6ebb'}, {'index': 7, 'type': 'markdown', 'sha256': '7afeaa254c97ec7e7187a7deca9cb808cfaf00c4e94be59b1ecb0930c70216ee'}, {'index': 8, 'type': 'code', 'sha256': '435f56063750609363d4e3c6716e5d149d213b9619f4ea7829a5d623f0c779a6'}, {'index': 9, 'type': 'markdown', 'sha256': '6dbe6da8fba313ed60db825fb58a12db1470216f9da534967d7a28ccea2ba85f'}, {'index': 10, 'type': 'code', 'sha256': '0fbe03cfb90c1fff3bf6801aa44dfaf1729e1e638a1d631832026fecec6ebd4b'}, {'index': 11, 'type': 'markdown', 'sha256': '9bc306e53844be09b9fc25d5cda94e5b11796927fafa50a5765882cb2f5b279d'}, {'index': 12, 'type': 'code', 'sha256': '8d3392c23a52da52c143928dab952137507f4fe80bbf3ae0e881393a27671668'}, {'index': 13, 'type': 'markdown', 'sha256': '72ad18b0ff92b79d2177f61fe4141b37a9478e3b5ef69a658f579b7f4aa2ebbc'}, {'index': 14, 'type': 'markdown', 'sha256': '68cee3024ef13aa9d7671744c898710eeb16a65d7c5bd1d30ab6a3412da96f2c'}, {'index': 15, 'type': 'code', 'sha256': '7f1ed2e27d71d405e802e63a3b541c3b7d5f0928645709369abf177c1106e5c9'}, {'index': 16, 'type': 'markdown', 'sha256': '28cc9ff0824922790217becc96ae9c8ff925eab346b4eda18f68c697299db129'}, {'index': 17, 'type': 'code', 'sha256': '5c6a291e1ce98ed0f886533578880e59afa4b8b4ee3974f3927665f27a34dab8'}, {'index': 18, 'type': 'markdown', 'sha256': '6d1932efc7dfe5b53a6756397b3153605b9bf27b95bf14378e00af886b3fe5d5'}, {'index': 19, 'type': 'markdown', 'sha256': 'd64da6446fdee316a7c86d823685fb93de9d35b4d326555839b2b18c4769ea65'}]}, 'code_cells': [2, 4, 6, 8, 10, 12, 15, 17], 'preamble': 'import numpy as np; np.random.seed(0)', 'witness': {'path': 'witnesses/ibm020.py', 'sha256': '23c20f3c7eeb023170af030ebbe2fb35f7a05f661888ba36dd56eb7a5d451f5d', 'hash_encoding': 'UTF-8 with LF; authored witness only'}, 'required_images': [6, 12, 15], 'required_text': {'12': "'balanced'", '17': "'1011'"}, 'capabilities': ['local-computation', 'rich-display'], 'external_requirements': ['Original markdown SVG/page rendering', 'Native mathematics and lesson interpretation'], 'source_preservation': 'Original cells retain text/type/order; authored cells have separate provenance', 'profiles': {'win32': 'qiskit-aer-win-py312', 'linux': 'qiskit-aer-linux-py312'}}}
WINDOWS_REFERENCES = {'ibm019': {'sha256': '9b1eeb767de8e750c0b27070f360d27822967f6297feb49979c97b0d3d2367d6', 'results': {'checks': [{'case': 1, 'truth': [0, 0], 'state_residual': 1.1102230246251565e-16, 'probabilities': [0.9999999999999996, 1.0573994819069698e-33], 'counts': {'0': 256}, 'label': 'constant'}, {'case': 2, 'truth': [0, 1], 'state_residual': 1.1102230246251565e-16, 'probabilities': [1.0573994819069698e-33, 0.9999999999999996], 'counts': {'1': 256}, 'label': 'balanced'}, {'case': 3, 'truth': [1, 0], 'state_residual': 1.1102230246251565e-16, 'probabilities': [1.0573994819069698e-33, 0.9999999999999996], 'counts': {'1': 256}, 'label': 'balanced'}, {'case': 4, 'truth': [1, 1], 'state_residual': 1.1102230246251565e-16, 'probabilities': [0.9999999999999996, 1.0573994819069698e-33], 'counts': {'0': 256}, 'label': 'constant'}], 'expected_errors': [{'input': 0, 'type': 'ValueError', 'message': '`case` must be 1, 2, 3, or 4.'}, {'input': 5, 'type': 'ValueError', 'message': '`case` must be 1, 2, 3, or 4.'}], 'kernel_executable': 'F:\\src\\libqalculate\\.tools\\dev13-runtime-replay-20261104\\Scripts\\python.exe', 'kernel_version': '3.12.10 (tags/v3.12.10:0cc8128, Apr  8 2025, 12:21:36) [MSC v.1943 64 bit (AMD64)]'}}, 'ibm020': {'sha256': '043f5c936d4512391400f466ec23cc0f32813b2a1c587eaa2c6cbd2cc9d5d059', 'results': {'original_generated_truth': [1, 1, 0, 0, 1, 0, 1, 0], 'operator_residual': 1.1109166973105323e-15, 'state_residual': 3.889650809439966e-16, 'expected_probabilities': [0.0, 0.25, 0.25, 0.0, 0.0, 0.25, 0.25, 0.0], 'counts': {'001': 1042, '101': 985, '110': 1037, '010': 1032}, 'label': 'balanced', 'bv': [{'secret': '0000', 'operator_residual': 0.0, 'state_residual': 4.440892098500626e-16, 'counts': {'0000': 256}}, {'secret': '0001', 'operator_residual': 0.0, 'state_residual': 4.440892098500626e-16, 'counts': {'0001': 256}}, {'secret': '1000', 'operator_residual': 0.0, 'state_residual': 4.440892098500626e-16, 'counts': {'1000': 256}}, {'secret': '1011', 'operator_residual': 0.0, 'state_residual': 4.440892098500626e-16, 'counts': {'1011': 256}}, {'secret': '1111', 'operator_residual': 0.0, 'state_residual': 4.440892098500626e-16, 'counts': {'1111': 256}}]}}}
ARTIFACT_ID = 13350182532
ARTIFACT_BYTES = 117705532
ARTIFACT_SHA = '0ca0632ef9fc390126f52743dc7967c4e6107f9b8428ae5bc8e7d8859ee5d40b'
LOCK_SHA = '39206d4cf230cd8b21d46698b72a3092fd4c0d2a5f4eccc7dd18ec2b1ad16769'


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


def harness_files(root):
    harness = Path(__file__).resolve().parents[2]
    paths = {'helper': harness/'diagnostics/notebook-linux-originals/retained_execution.py',
             'workflow': harness/'.github/workflows/notebook-linux-originals.yml'}
    records = {}
    for role, path in paths.items():
        snapshot = root/'harness-source'/path.name
        require(path.is_file() and not path.is_symlink(), 'Missing current harness file: '+role)
        require(snapshot.is_file() and not snapshot.is_symlink(), 'Missing retained harness file: '+role)
        records[role] = dict(path=str(path), snapshot=str(snapshot), bytes=path.stat().st_size,
                             sha256=digest(path), snapshot_bytes=snapshot.stat().st_size,
                             snapshot_sha256=digest(snapshot))
    return records


def bind_harness(root):
    records = harness_files(root)
    for role, record in records.items():
        require(record['bytes']==record['snapshot_bytes'] and record['sha256']==record['snapshot_sha256'],
                'Initial retained harness mismatch: '+role)
    return records


def audit_harness(root):
    before = read(root/'identity.json')['harness_files']
    after = None
    errors = []
    try:
        after = harness_files(root)
        require(set(before)=={'helper','workflow'}, 'Initial harness inventory mismatch')
        for role in before:
            require(after[role]==before[role], 'Harness changed: '+role)
    except Exception as error:
        errors.append(dict(error_type=type(error).__name__, error=str(error)))
    write(root/'harness-after.json',dict(passed=not errors, before=before, after=after, errors=errors))
    require(not errors, 'Final harness identity failed; inspect harness-after.json')


def bind(product, root):
    def git(*args):return subprocess.check_output(['git','-C',str(product),*args],timeout=20,text=True).strip()
    require(git('rev-parse','HEAD')==PRODUCT and not git('status','--porcelain','--untracked-files=all'), 'Wrong/dirty product')
    source=product/'windows/dev13-notebooks'
    for name, expected in SOURCE_HASHES.items():require(digest(source/name)==expected,'Source hash mismatch: '+name)
    require(sys.platform=='linux' and platform.machine()=='x86_64' and platform.python_version()=='3.12.10'
            and platform.python_implementation()=='CPython', 'Requires CPython3.12.10 Linux x86_64')
    write(root/'identity.json',dict(product_revision=PRODUCT,product_tree=git('rev-parse','HEAD^{tree}'),source_hashes=SOURCE_HASHES,helper_sha256=digest(Path(__file__)),harness_files=bind_harness(root),
          harness_revision=os.environ['HARNESS_REVISION'],workflow_revision=os.environ['WORKFLOW_REVISION'],
          workflow_ref=os.environ['WORKFLOW_REF'],event_revision=os.environ['GITHUB_SHA'],run=os.environ['GITHUB_RUN_ID'],
          attempt=os.environ['GITHUB_RUN_ATTEMPT'],python=sys.version,platform=platform.platform(),scope='Two original finite notebook contracts plus disclosed authored witnesses'))


def acquire(root):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,req,fp,code,msg,headers,newurl):return None
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    endpoint='https://api.github.com/repos/badtyprr/quantumstudio/actions/artifacts/'+str(ARTIFACT_ID)
    headers={'Authorization':'Bearer '+os.environ['ARTIFACT_TOKEN'],'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
    def deadline(signum,frame):raise TimeoutError('Artifact acquisition deadline')
    previous=signal.signal(signal.SIGALRM,deadline);signal.alarm(240)
    try:
        with opener.open(urllib.request.Request(endpoint,headers=headers),timeout=30) as response:raw=response.read(1024*1024+1)
        require(len(raw)<=1024*1024,'Metadata too large');m=json.loads(raw)
        require(m['id']==ARTIFACT_ID and not m['expired'] and m['size_in_bytes']==ARTIFACT_BYTES and m['digest']=='sha256:'+ARTIFACT_SHA
                and m['name']=='notebook-linux-qiskit-41883503640-1' and m['workflow_run']['id']==41883503640 and m['workflow_run']['head_sha']=='890eb5b99fc4035fc3fb8144c744ff79bda4d387','Artifact identity mismatch')
        write(root/'artifact-api.json',raw)
        try:
            response=opener.open(urllib.request.Request(endpoint+'/zip',headers=headers),timeout=30)
        except urllib.error.HTTPError as error:
            require(error.code==302,'Artifact redirect required');location=error.headers.get('Location','');error.close()
            parsed=urllib.parse.urlsplit(location)
            require(parsed.scheme=='https' and parsed.hostname and not parsed.username and not parsed.password,'Invalid storage URL')
            response=opener.open(urllib.request.Request(location),timeout=60)
        with response, (root/'dependency-artifact.zip').open('xb') as out:
            total=0
            while chunk:=response.read(1024*1024):
                total+=len(chunk);require(total<=ARTIFACT_BYTES,'Oversized artifact');out.write(chunk)
    except Exception as error:
        # Do not log exception messages containing signed storage URLs or headers.
        raise RuntimeError('Retained artifact acquisition failed: '+type(error).__name__) from None
    finally:signal.alarm(0);signal.signal(signal.SIGALRM,previous)


def prepare(root, product):
    archive=root/'dependency-artifact.zip'
    require(archive.stat().st_size==ARTIFACT_BYTES and digest(archive)==ARTIFACT_SHA,'Artifact bytes mismatch')
    target=root/'retained';target.mkdir()
    with zipfile.ZipFile(archive) as z:
        entries=z.infolist();seen=set()
        require(len(entries)==160 and sum(x.file_size for x in entries)<512*1024*1024,'Unexpected artifact inventory')
        for entry in entries:
            safe_parts(entry.filename)
            require(entry.filename not in seen and not entry.is_dir() and not entry.flag_bits&1
                    and stat.S_IFMT(entry.external_attr>>16) in (0,stat.S_IFREG),'Unsafe ZIP entry')
            seen.add(entry.filename)
        for entry in entries:
            dest=target.joinpath(*safe_parts(entry.filename));dest.parent.mkdir(parents=True,exist_ok=True)
            with z.open(entry) as src,dest.open('xb') as out:shutil.copyfileobj(src,out)
    verify_manifest(target,159);a=target/'acquisition';verify_manifest(a,144)
    status=read(a/'status.json');require(status['state']=='succeeded' and status['wheels']==54 and status['public_wheels']==53
        and status['custom_wheels']==1 and status['exact_inventory'] and status['imports_verified'],'Acquisition prerequisite failed')
    lock=a/'requirements.lock';require(digest(lock)==LOCK_SHA and lock.read_bytes()==(product/'windows/dev13-notebooks/ibm019-linux-requirements.lock').read_bytes(),'Profile lock mismatch')
    wheels=read(a/'wheel-manifest.json');require(len(wheels)==54 and {x.name for x in (a/'wheels').iterdir()}=={x['filename'] for x in wheels},'Wheel inventory mismatch')
    for item in wheels:
        f=a/'wheels'/item['filename'];require(len(safe_parts(item['filename']))==1 and digest(f)==item['sha256'] and f.stat().st_size==item['bytes'],'Wheel mismatch')
    require(digest(a/'original-inputs.zip')=='9ae2fc258ad60ec4a1ee404febf3e2f738c09edc0a3e154f8442280211f90c72','Input ZIP mismatch')
    for name,c in CONTRACTS.items():require(digest(a/'inputs/sources'/str(name+'.ipynb'))==c['source']['sha256'],'Original source mismatch')
    write(root/'preparation.json',dict(passed=True,artifact=ARTIFACT_ID,sha256=ARTIFACT_SHA,wheels=54,lock_sha256=LOCK_SHA))


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


def audit(root, product, env):
    environment=read(env/'environment.json');require(environment['state']=='succeeded' and environment['offline_only'] and environment['profile']['id']=='qiskit-aer-linux-py312' and environment['profile']['lock_sha256']==LOCK_SHA and environment['identity']['python']=='3.12.10' and environment['identity']['platform']=='linux','Offline environment failed')
    lock=(product/'windows/dev13-notebooks/ibm019-linux-requirements.lock').read_text();expected=dict(line.split()[0].split('==') for line in lock.splitlines())
    normalize=lambda n:re.sub('[-_.]+','-',n).lower();expected={normalize(n):v for n,v in expected.items()}
    require(environment['identity']['packages']==expected and len(expected)==54,'Installed inventory mismatch')
    results=[];errors=[]
    for name in CONTRACTS:
        try:results.append(audit_run(root,name,environment))
        except Exception as error:errors.append(dict(contract=name,error_type=type(error).__name__,error=str(error)))
    require(not results or len(set(results))==len(results),'Reused owned unit')
    for name,h in SOURCE_HASHES.items():require(digest(product/'windows/dev13-notebooks'/name)==h,'Product changed')
    verify_manifest(root/'retained',159)
    audit_harness(root)
    write(root/'acceptance.json',dict(passed=not errors and len(results)==2,errors=errors,original_notebooks=2,original_code_cells=16,
          product_revision=PRODUCT,scope='Finite original code plus separately authored witnesses; external resources and interpretation outstanding'))
    require(not errors and len(results)==2,'Original notebook acceptance failed; inspect retained evidence')


def seal(root, env):
    for name in ('environment.json','install.log'):
        if (env/name).is_file():write(root/('offline-'+name),(env/name).read_bytes())
    records={}
    for path in sorted(root.rglob('*')):
        if path.is_file() and not path.is_symlink() and path.name!='evidence-manifest-final.json':records[path.relative_to(root).as_posix()]=dict(bytes=path.stat().st_size,sha256=digest(path))
    write(root/'evidence-manifest-final.json',records)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('mode',choices=['bind','prepare','audit','seal']);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--product',type=Path,required=True);ap.add_argument('--environment',type=Path,required=True);args=ap.parse_args()
    require(all(p.is_absolute() for p in (args.root,args.product,args.environment)),'Absolute paths required')
    args.root.mkdir(exist_ok=True)
    try:
        if args.mode=='bind':bind(args.product,args.root)
        elif args.mode=='prepare':acquire(args.root);prepare(args.root,args.product)
        elif args.mode=='audit':audit(args.root,args.product,args.environment)
        else:seal(args.root,args.environment)
    except Exception as error:
        write(args.root/(args.mode+'-failure.json'),dict(error_type=type(error).__name__,error=str(error)))
        print(args.mode+' failed; retained evidence available');return 1
    return 0


if __name__=='__main__':sys.exit(main())
