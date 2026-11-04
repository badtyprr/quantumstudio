"""Acquire exact Linux Qiskit dependencies; no notebook execution or profile enablement."""
import base64
import csv
import configparser
import io
import stat
import tarfile
from pathlib import PurePosixPath
import argparse
import email
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import zipfile


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def pins(raw):
    """Deliberately excludes options, URLs, markers, ranges and continuations."""
    result = {}
    pattern = re.compile(r"([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)(?:\[([A-Za-z0-9._-]+(?:,[A-Za-z0-9._-]+)*)\])?==([0-9]+(?:\.[0-9]+)*(?:(?:a|b|rc)[0-9]+)?(?:\.post[0-9]+)?(?:\.dev[0-9]+)?)")
    for line in raw.decode("utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = pattern.fullmatch(line)
        if not match:
            raise ValueError("Only simple exact public version pins, with optional extras, are accepted")
        name, extras, version = match.groups()
        key = normalize(name)
        if key in result:
            raise ValueError("Duplicate normalized direct requirement")
        if extras and len(set(map(normalize, extras.split(',')))) != len(extras.split(',')):
            raise ValueError("Duplicate normalized extras")
        # CUDA binary stacks and package SDKs require a separate reviewed contract.
        if key.startswith(("nvidia-", "cuda", "cupy", "cudf", "cuml", "tensorrt")):
            raise ValueError("CUDA dependency excluded from this bootstrap contract")
        result[key] = version
    if not result or "pip" not in result:
        raise ValueError("Reviewed requirements must explicitly pin pip for exact environment inventory")
    return result


def clean_environment(home):
    # Allowlist rather than recording inherited secrets or permitting pip configuration.
    result = {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL") if key in os.environ}
    result.update(HOME=str(home), XDG_CONFIG_HOME=str(home), TMPDIR=str(home), PIP_CONFIG_FILE=os.devnull, PYTHONNOUSERSITE="1", PIP_NO_INPUT="1",
                  PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_KEYRING_PROVIDER="disabled")
    return result


def wheel_metadata(path):
    if path.suffix != ".whl" or not path.is_file() or path.is_symlink():
        raise ValueError("Expected regular wheel file")
    with zipfile.ZipFile(path) as archive:
        matches = [x for x in archive.infolist() if x.filename.endswith(".dist-info/METADATA")]
        if len(matches) != 1 or matches[0].file_size > 4 * 1024 * 1024:
            raise ValueError("Wheel must contain one bounded METADATA record")
        metadata = email.message_from_bytes(archive.read(matches[0]))
    names, versions = metadata.get_all("Name", []), metadata.get_all("Version", [])
    if len(names) != 1 or len(versions) != 1:
        raise ValueError("Ambiguous wheel identity")
    name, version = names[0], versions[0]
    # Apply the same finite version/name grammar without loosening it for transitives.
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?", name) or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)*(?:(?:a|b|rc)[0-9]+)?(?:\.post[0-9]+)?(?:\.dev[0-9]+)?", version):
        raise ValueError("Invalid or unsupported wheel identity")
    if normalize(name).startswith(("nvidia-", "cuda", "cupy", "cudf", "cuml", "tensorrt")) or normalize(name).endswith("-sdk"):
        raise ValueError("CUDA/SDK dependency excluded")
    return normalize(name), version


def match_published(document, filename, digest, size, name, version):
    if normalize(document["info"]["name"]) != name or document["info"]["version"] != version:
        raise ValueError("Versioned PyPI response identity mismatch")
    matches = [x for x in document["urls"] if x["filename"] == filename]
    if len(matches) != 1:
        raise ValueError("Wheel filename not unique in versioned PyPI record")
    item = matches[0]
    if item["packagetype"] != "bdist_wheel" or item.get("yanked") or item["digests"]["sha256"] != digest or item["size"] != size:
        raise ValueError("Published wheel digest/size/type/yank mismatch")


def write(path, value):
    with path.open("xb") as stream:
        stream.write(value if isinstance(value, bytes) else (json.dumps(value, indent=2) + "\n").encode())


def command(argv, output, name, environment, timeout):
    write(output / (name + "-command.json"), dict(argv=argv, timeout_seconds=timeout))
    started = time.monotonic()
    with (output / (name + ".log")).open("xb") as log:
        process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, env=environment,
                                   cwd=output, stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=10)
            write(output / (name + "-exit.json"), dict(exit_code=process.returncode, interrupted=True,
                  elapsed_seconds=time.monotonic()-started))
            raise
    write(output / (name + "-exit.json"), dict(exit_code=code, elapsed_seconds=time.monotonic()-started))
    if code:
        raise RuntimeError(name + " failed; retained command log contains details")


def fetch_version(name, version):
    url = "https://pypi.org/pypi/" + urllib.parse.quote(name, safe="") + "/" + urllib.parse.quote(version, safe="") + "/json"
    # No inherited proxy/auth settings; no redirect to an unreviewed source.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise ValueError("Unexpected PyPI metadata redirect")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    def deadline(signum, frame):
        raise TimeoutError("PyPI metadata total deadline exceeded")
    previous = signal.signal(signal.SIGALRM, deadline)
    signal.alarm(45)
    try:
        with opener.open(urllib.request.Request(url, headers={"Accept": "application/json"}), timeout=30) as response:
            raw = response.read(16 * 1024 * 1024 + 1)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
    if len(raw) > 16 * 1024 * 1024:
        raise ValueError("Oversized PyPI response")
    return url, raw



INPUT_SHA = "9ae2fc258ad60ec4a1ee404febf3e2f738c09edc0a3e154f8442280211f90c72"
REQUIREMENTS_SHA = '2e79d9f979e06329f3c07cca4baca637d2c0622de29174eb842109397136d8d6'
EXPECTED_PINS = {'asttokens': '3.0.2', 'attrs': '26.1.0', 'colorama': '0.4.6', 'comm': '0.2.3', 'contourpy': '1.4.0', 'cycler': '0.12.1', 'debugpy': '1.8.22', 'dill': '0.4.1', 'executing': '2.3.0', 'fastjsonschema': '2.22.3', 'fonttools': '4.68.0', 'ipykernel': '7.4.0', 'ipython': '9.18.1', 'ipython-pygments-lexers': '1.1.1', 'jedi': '0.20.1', 'jsonschema': '4.26.0', 'jsonschema-specifications': '2025.9.1', 'jupyter-client': '8.10.0', 'jupyter-core': '5.9.1', 'kiwisolver': '1.5.1', 'matplotlib': '3.11.2', 'matplotlib-inline': '0.2.2', 'nbclient': '0.11.0', 'nbformat': '5.11.1', 'nest-asyncio2': '1.7.4', 'numpy': '2.5.4', 'packaging': '26.3', 'parso': '0.8.7', 'pillow': '13.0.0', 'platformdirs': '4.14.4', 'prompt-toolkit': '3.0.53', 'psutil': '7.2.2', 'pure-eval': '0.2.4', 'pygments': '2.21.0', 'pylatexenc': '2.10', 'pyparsing': '3.3.3', 'python-dateutil': '4.0.0', 'pyzmq': '27.3.0', 'qiskit': '2.2.3', 'qiskit-aer': '0.18.2', 'referencing': '0.37.0', 'rpds-py': '2026.9.1', 'rustworkx': '0.18.1', 'scipy': '1.18.1', 'stack-data': '0.6.3', 'stevedore': '5.9.1', 'tornado': '6.6', 'traitlets': '5.16.1', 'typing-extensions': '4.16.0', 'tzdata': '2026.6', 'wcwidth': '0.9.4', 'pip': '25.3', 'pexpect': '4.9.0', 'ptyprocess': '0.7.0'}
REVIEWED_PUBLIC = {'asttokens-3.0.2-py3-none-any.whl': {'sha256': '9da13157f5b28becde0bd374fc677dcd3c290614264eff096f167c469cd9f933', 'bytes': 28702}, 'attrs-26.1.0-py3-none-any.whl': {'sha256': 'c647aa4a12dfbad9333ca4e71fe62ddc36f4e63b2d260a37a8b83d2f043ac309', 'bytes': 67548}, 'colorama-0.4.6-py2.py3-none-any.whl': {'sha256': '4f1d9991f5acc0ca119f9d443620b77f9d6b33703e51011c16baf57afb285fc6', 'bytes': 25335}, 'comm-0.2.3-py3-none-any.whl': {'sha256': 'c615d91d75f7f04f095b30d1c1711babd43bdc6419c1be9886a85f2f4e489417', 'bytes': 7294}, 'contourpy-1.4.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl': {'sha256': '875f42444c9cf48d56f724f2637e60d0f73b3b12c9041e1484580a233edf9591', 'bytes': 383243}, 'cycler-0.12.1-py3-none-any.whl': {'sha256': '85cef7cff222d8644161529808465972e51340599459b8ac3ccbac5a854e0d30', 'bytes': 8321}, 'debugpy-1.8.22-cp312-cp312-manylinux_2_34_x86_64.whl': {'sha256': '8a697acec45dbc70d17fb5d9f4f61989fc294d273c69de487fd10cb35fdd75eb', 'bytes': 4000941}, 'debugpy-1.8.22-py2.py3-none-any.whl': {'sha256': 'a9e9d3550e15ca479c59333e90845029190531f0cacfedab3b815a57bd913947', 'bytes': 5374857}, 'dill-0.4.1-py3-none-any.whl': {'sha256': '1e1ce33e978ae97fcfcff5638477032b801c46c7c65cf717f95fbc2248f79a9d', 'bytes': 120019}, 'executing-2.3.0-py3-none-any.whl': {'sha256': '736e859c9f8701f11fcf516856f26f562e04776387824b43a35a1dfe21c84122', 'bytes': 29393}, 'fastjsonschema-2.22.3-py3-none-any.whl': {'sha256': 'f670b443830b75aca3f00b75949efa20f4b2a80302ec7a21505c28dd54cffd43', 'bytes': 28442}, 'fonttools-4.68.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl': {'sha256': '3edce69ecdefa73ab1041901ca22eefed6ebb93a77bc77e889d940479f25bf7d', 'bytes': 5443448}, 'fonttools-4.68.0-py3-none-any.whl': {'sha256': 'd76f8fdcb6936f5e1045a0c9dd721a4bf11112e60d1e243bfa1d39f06a8b3104', 'bytes': 1248357}, 'ipykernel-7.4.0-py3-none-any.whl': {'sha256': 'a6757f790ddc5a6006b813d82da1a9dbb65b3a00f2b6607df776418c6566ec1c', 'bytes': 123184}, 'ipython-9.18.1-py3-none-any.whl': {'sha256': '997ce9140d374531a61069c70c0f9ef299d6dd3559ea0f94b8af589726e3c1d5', 'bytes': 649819}, 'ipython_pygments_lexers-1.1.1-py3-none-any.whl': {'sha256': 'a9462224a505ade19a605f71f8fa63c2048833ce50abc86768a0d81d876dc81c', 'bytes': 8074}, 'jedi-0.20.1-py2.py3-none-any.whl': {'sha256': '0fb16d86c4a4c73c37ba518c77419975e30fcc620658a8d14fbb5720cdd34142', 'bytes': 4885980}, 'jsonschema-4.26.0-py3-none-any.whl': {'sha256': 'd489f15263b8d200f8387e64b4c3a75f06629559fb73deb8fdfb525f2dab50ce', 'bytes': 90630}, 'jsonschema_specifications-2025.9.1-py3-none-any.whl': {'sha256': '98802fee3a11ee76ecaca44429fda8a41bff98b00a0f2838151b113f210cc6fe', 'bytes': 18437}, 'jupyter_client-8.10.0-py3-none-any.whl': {'sha256': '5f73f24f22fa25192cfff6b23c051932a2473a797b05734aff495b392103e14e', 'bytes': 110184}, 'jupyter_core-5.9.1-py3-none-any.whl': {'sha256': 'ebf87fdc6073d142e114c72c9e29a9d7ca03fad818c5d300ce2adc1fb0743407', 'bytes': 29032}, 'kiwisolver-1.5.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl': {'sha256': '34633ecf50d16187ab8e5528b7a2530f2feb4e23f300db4672538b51cfc5cd38', 'bytes': 1477929}, 'matplotlib-3.11.2-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl': {'sha256': 'df4f7784aca81a94f254c0a2767d592ee25f407e488f5fa7203e51093fb6ca27', 'bytes': 9860353}, 'matplotlib_inline-0.2.2-py3-none-any.whl': {'sha256': '3c821cf1c209f59fb2d2d64abbf5b23b67bcb2210d663f9918dd851c6da1fcf6', 'bytes': 9534}, 'nbclient-0.11.0-py3-none-any.whl': {'sha256': 'ef7fa0d59d6e1d41103933d8a445a18d5de860ca6b613b87b8574accdb3c2895', 'bytes': 25288}, 'nbformat-5.11.1-py3-none-any.whl': {'sha256': 'cc6698fa75f4fab8755ead786317815f13a6fee3b53311c0abb1a8b51d52f7ec', 'bytes': 79849}, 'nest_asyncio2-1.7.4-py3-none-any.whl': {'sha256': '86e77b52c3d1496b294af3c944b44213b9b82a12a5ee590c0acc4ca4692ef6c7', 'bytes': 8543}, 'numpy-2.5.4-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl': {'sha256': 'fbde6962867ee75b48b0ee29b2b9372ec5d617799dbaf38e82dc0596f2f7738a', 'bytes': 16727283}, 'packaging-26.3-py3-none-any.whl': {'sha256': 'd7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c', 'bytes': 129956}, 'parso-0.8.7-py2.py3-none-any.whl': {'sha256': 'a8926eb2a1b915486941fdbd31e86a4baf88fe8c210f25f2f35ecec5b574ca1c', 'bytes': 107025}, 'pillow-13.0.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl': {'sha256': '42d63be3af4f9b951b199b0a9d23365d37ab14687e6d77b74940432c8515c4ca', 'bytes': 7144542}, 'platformdirs-4.14.4-py3-none-any.whl': {'sha256': '89c1bfa30434b2dcc08655bcfb1789e1a6f97602c11ff990615d09a4b823d6be', 'bytes': 35357}, 'prompt_toolkit-3.0.53-py3-none-any.whl': {'sha256': '01c0891d7f9237d5e339f7d3e42cdae80b7534abb1c7c0e3352efba6231492f2', 'bytes': 392288}, 'psutil-7.2.2-cp36-abi3-manylinux2010_x86_64.manylinux_2_12_x86_64.manylinux_2_28_x86_64.whl': {'sha256': '076a2d2f923fd4821644f5ba89f059523da90dc9014e85f8e45a5774ca5bc6f9', 'bytes': 155560}, 'pure_eval-0.2.4-py3-none-any.whl': {'sha256': '96cae060a313cfaad51bb761278bfb0e62dc0248d9315a81173752dc546cd37a', 'bytes': 11893}, 'pygments-2.21.0-py3-none-any.whl': {'sha256': '2363c69b61c4a97c838da3b130dcd6468f4848992b21a82f2a63ec34377137d9', 'bytes': 1250147}, 'pyparsing-3.3.3-py3-none-any.whl': {'sha256': 'ece8c00a69cf01b45d0b1dedabb469c90d8caf996d4fda40f147627a122849a4', 'bytes': 126420}, 'python_dateutil-4.0.0-py3-none-any.whl': {'sha256': 'a5e246f79eb80475e691bf93862cead98decd8a498cf53ba0516fcdc0f50dc1c', 'bytes': 92853}, 'pyzmq-27.3.0-cp312-abi3-manylinux_2_26_x86_64.manylinux_2_28_x86_64.whl': {'sha256': '858fe25231e0fd8612da142efde019faa5ef63fa150a821a27870e791b38c798', 'bytes': 855178}, 'qiskit-2.2.3-cp39-abi3-manylinux2014_x86_64.manylinux_2_17_x86_64.whl': {'sha256': '75acf702866a68be36870400d845d0775e7baa5397bf880bc56864ee105cbe93', 'bytes': 8007661}, 'qiskit_aer-0.18.2-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl': {'sha256': '0c010f3829b925e6cb77a1856d099b742b2dbfea517f9b0422eef9247f884b49', 'bytes': 14220648}, 'referencing-0.37.0-py3-none-any.whl': {'sha256': '381329a9f99628c9069361716891d34ad94af76e461dcb0335825aecc7692231', 'bytes': 26766}, 'rpds_py-2026.9.1-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl': {'sha256': 'addeda51556dac7c1a2f14cda62db8b621cd12afba3091d03a96c72932387eab', 'bytes': 371261}, 'rustworkx-0.18.1-cp310-abi3-manylinux2014_x86_64.manylinux_2_17_x86_64.whl': {'sha256': '1ebd2441a51c68a784df8c62dc2e6f1a9f58c0eb1c2e21fd59776e08f55c0c0b', 'bytes': 2366881}, 'scipy-1.18.1-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl': {'sha256': 'f55fa87b6c612ecd6b058f167c53231b1d14e412efe361d3d6e38b3631c73218', 'bytes': 35344199}, 'stack_data-0.6.3-py3-none-any.whl': {'sha256': 'd5558e0c25a4cb0853cddad3d77da9891a08cb85dd9f9f91b9f8cd66e511e695', 'bytes': 24521}, 'stevedore-5.9.1-py3-none-any.whl': {'sha256': '5c8ff3a9f336cc1a06ac0f597bc79d11a2f950bfd32e290ca56b5a301fafafbf', 'bytes': 54931}, 'tornado-6.6-cp311-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl': {'sha256': '11bb97c00981eb8254e55bd6a5ad960c983ae343fef8ae3ae5584cd1fb70236a', 'bytes': 529544}, 'traitlets-5.16.1-py3-none-any.whl': {'sha256': 'f775618166caa0396c8e337099240f2bd3e5e917d203b2e6fbe21a58d3cb1f6b', 'bytes': 86211}, 'typing_extensions-4.16.0-py3-none-any.whl': {'sha256': '481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8', 'bytes': 45571}, 'tzdata-2026.6-py2.py3-none-any.whl': {'sha256': '0a10eec6e13ef16b627fabed9a5f2ba61a62b1c67f327305f4e7e412a70b4aec', 'bytes': 348210}, 'wcwidth-0.9.4-cp310-abi3-manylinux2014_x86_64.manylinux_2_17_x86_64.whl': {'sha256': 'b185c8b927b23af2721be1783499d1cfa5c028b098b0858951b4ae224477f1c2', 'bytes': 785946}, 'wcwidth-0.9.4-py3-none-any.whl': {'sha256': '901eace6d2dd25ebb917d0ce5db18e5c537e1504c905cf32f0d006c12098b05d', 'bytes': 301806}, 'pexpect-4.9.0-py2.py3-none-any.whl': {'sha256': '7236d1e080e4936be2dc3e326cec0af72acf9212a7e1d060210e70a47e253523', 'bytes': 63772}, 'ptyprocess-0.7.0-py2.py3-none-any.whl': {'sha256': '4b41f3967fce3af57cc7e94b888626c18bf37a083e3651ca8feeb66d492fef35', 'bytes': 13993}, 'pip-25.3-py3-none-any.whl': {'sha256': '9655943313a94722b7774661c21049070f6bbb0a1516bf02f7c8d5d9201514cd', 'bytes': 1778622}}

# Retained source audit copied from reviewed verifier SHA256
# 1040799b3f0c898da4caaf178586d7d0542ce49991674c721a607009dac35f1f.
def audit(wheel, source):
    if sys.flags.optimize:
        raise RuntimeError('OPTIMIZED_PYTHON_NOT_ALLOWED_FOR_INTEGRITY_AUDIT')
    wheel_raw, source_raw = wheel.read_bytes(), source.read_bytes()
    assert hashlib.sha256(wheel_raw).hexdigest() == '7211b83dc685ec8e5e25d09c5538d867279a4bb41058c00ab12fa8a8250bfcd2'
    assert hashlib.sha256(source_raw).hexdigest() == '3dd8fd84eb46dc30bee1e23eaab8d8fb5a7f507347b23e5f38ad9675c84f40d3'
    with zipfile.ZipFile(io.BytesIO(wheel_raw)) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names))
        assert all(not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts for name in names)
        files = {name: archive.read(name) for name in names}
    record_name = 'pylatexenc-2.10.dist-info/RECORD'
    rows = list(csv.reader(io.StringIO(files[record_name].decode())))
    assert len(rows) == len(files) and {row[0] for row in rows} == set(files)
    for name, digest, size in rows:
        if name == record_name:
            assert digest == size == ''
            continue
        expected = 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(files[name]).digest()).decode().rstrip('=')
        assert digest == expected and int(size) == len(files[name]), name
    metadata = email.message_from_bytes(files['pylatexenc-2.10.dist-info/METADATA'])
    wheel_metadata = email.message_from_bytes(files['pylatexenc-2.10.dist-info/WHEEL'])
    assert metadata['Name'] == 'pylatexenc' and metadata['Version'] == '2.10'
    assert wheel_metadata['Root-Is-Purelib'] == 'true' and wheel_metadata.get_all('Tag') == ['py3-none-any']
    with tarfile.open(fileobj=io.BytesIO(source_raw), mode='r:gz') as archive:
        members = archive.getmembers()
        assert len({member.name for member in members}) == len(members)
        source_files = {member.name: archive.extractfile(member).read() for member in members if member.isfile()}
    code = sorted(name for name in files if name.startswith('pylatexenc/'))
    assert all(name.endswith('.py') for name in code)
    source_code = {name.removeprefix('pylatexenc-2.10/') for name in source_files
                   if name.startswith('pylatexenc-2.10/pylatexenc/') and name.endswith('.py')}
    assert set(code) == source_code
    for name in code:
        assert files[name] == source_files['pylatexenc-2.10/' + name], name
    assert files['pylatexenc-2.10.dist-info/licenses/LICENSE.txt'] == source_files['pylatexenc-2.10/LICENSE.txt']
    wheel_entries, source_entries = configparser.ConfigParser(), configparser.ConfigParser()
    wheel_entries.read_string(files['pylatexenc-2.10.dist-info/entry_points.txt'].decode())
    source_entries.read_string(source_files['pylatexenc-2.10/pylatexenc.egg-info/entry_points.txt'].decode())
    assert {name: dict(wheel_entries[name]) for name in wheel_entries.sections()} == {
        name: dict(source_entries[name]) for name in source_entries.sections()}
    assert files['pylatexenc-2.10.dist-info/top_level.txt'] == source_files['pylatexenc-2.10/pylatexenc.egg-info/top_level.txt']
    source_metadata = email.message_from_bytes(source_files['pylatexenc-2.10/pylatexenc.egg-info/PKG-INFO'])
    for field in ('Name', 'Version', 'Requires-Python', 'Requires-Dist'):
        assert sorted(metadata.get_all(field, [])) == sorted(source_metadata.get_all(field, [])), field
    return dict(wheel_sha256=hashlib.sha256(wheel_raw).hexdigest(), source_sha256=hashlib.sha256(source_raw).hexdigest(),
                wheel_members=len(files), record_digests_verified=len(rows)-1, exact_source_modules=code,
                license_matches_source=True, entry_points_match_source=True, distribution_requirements_match_source=True,
                generator=wheel_metadata['Generator'], pure_tag='py3-none-any',
                scope='Retained artifact integrity and exact packaged-source correspondence only',
                linux_import_verified=False, reproducible_rebuild_verified=False)



def extract_inputs(path, output):
    raw = path.read_bytes()
    if len(raw) != 311293 or sha(raw) != INPUT_SHA:
        raise ValueError('Pinned input ZIP digest/size mismatch')
    write(output / 'original-inputs.zip', raw)
    target = output / 'inputs'
    target.mkdir()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        if len(names) != 7 or len(set(names)) != 7:
            raise ValueError('Expected seven unique input entries')
        for entry in archive.infolist():
            parts = PurePosixPath(entry.filename).parts
            if (not parts or PurePosixPath(entry.filename).is_absolute() or
                '/'.join(parts) != entry.filename or any(p in ('.', '..') for p in parts) or
                '\\' in entry.filename or ':' in entry.filename or
                stat.S_IFMT(entry.external_attr >> 16) not in (0, stat.S_IFREG) or
                entry.flag_bits & 1 or entry.file_size > 2*1024*1024):
                raise ValueError('Unsafe input ZIP member')
        manifest = json.loads(archive.read('manifest.json'))
        if set(names) != set(manifest['files']) | {'manifest.json'}:
            raise ValueError('Input manifest inventory mismatch')
        for name in names:
            data = archive.read(name)
            if name != 'manifest.json':
                record = manifest['files'][name]
                if len(data) != record['bytes'] or sha(data) != record['sha256']:
                    raise ValueError('Input member digest/size mismatch')
            dest = target.joinpath(*PurePosixPath(name).parts)
            dest.parent.mkdir(parents=True, exist_ok=True)
            write(dest, data)
    result = audit(target / 'custom-wheel/pylatexenc-2.10-py3-none-any.whl',
                   target / 'provenance/pylatexenc-2.10.tar.gz')
    write(output / 'custom-wheel-source-audit.json', result)
    return target

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--requirements", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not all(p.is_absolute() for p in (args.inputs, args.output, args.requirements)):
        raise ValueError("Absolute requirements and output paths required")
    output = args.output.absolute()
    # Refuse any existing output, including a symlink; never delete/reuse a run.
    if output.exists() or output.is_symlink():
        raise FileExistsError("Fresh output directory required")
    output.mkdir(parents=False, exist_ok=False)
    output = output.resolve(strict=True)
    status = dict(state="failed", stage="preflight", scope="dependency acquisition/installation only",
                  lifecycle_acceptance=False, notebook_acceptance=False)
    try:
        identity = dict(python=platform.python_version(), platform=sys.platform, machine=platform.machine(),
                        executable=sys.executable, helper_sha256=sha(Path(__file__).read_bytes()))
        write(output / "source-platform.json", identity)
        if sys.flags.optimize:
            raise ValueError("Optimized Python is not allowed for retained source audit")
        if identity["python"] != "3.12.10" or identity["platform"] != "linux" or identity["machine"] != "x86_64":
            raise ValueError("Requires CPython 3.12.10 Linux x86_64")
        if platform.python_implementation() != "CPython":
            raise ValueError("CPython required")
        status["stage"] = "input-verification"
        inputs = extract_inputs(args.inputs, output)
        raw = args.requirements.read_bytes()
        if sha(raw) != REQUIREMENTS_SHA:
            raise ValueError("Reviewed requirements bytes mismatch")
        write(output / "exact-requirements.txt", raw)
        direct = pins(raw)
        if direct != EXPECTED_PINS:
            raise ValueError("Exact reviewed version-parity package roots required")
        write(output / "requirements-identity.json", dict(path=str(args.requirements.resolve()), sha256=sha(raw), pins=direct))
        wheels = output / "wheels"; wheels.mkdir()
        metadata = output / "pypi"; metadata.mkdir()
        home = output / "private-home"; home.mkdir()
        environment = clean_environment(home)
        pip = [sys.executable, "-I", "-m", "pip", "--isolated", "--disable-pip-version-check", "--no-input"]
        command(pip + ["--version"], output, "resolver-version", environment, 30)
        write(output / "resolver-source.json", dict(base="0f9586221dae9604cdef72dd0d3a3015767246af", roots="51 Windows-version roots plus pexpect, ptyprocess and pip; not minimal closure", public_metadata_proposal_sha256="504a5a6a764f40a90a6daa9d4ca82d88640e4a55a9eab3d6e456b5cef5c0e5b1"))
        status["stage"] = "acquisition"
        command(pip + ["download", "--index-url", "https://pypi.org/simple", "--only-binary=:all:",
                "--no-cache-dir", "--keyring-provider", "disabled", "--timeout", "30", "--retries", "2",
                "--find-links", str(inputs / "custom-wheel"), "--dest", str(wheels), "-r", str(output / "exact-requirements.txt")], output, "download", environment, 900)
        status["stage"] = "wheel-verification"
        inventory = {}; records = []; locks = []
        for path in sorted(wheels.iterdir()):
            name, version = wheel_metadata(path)
            if name in inventory:
                raise ValueError("Duplicate normalized wheel distribution")
            inventory[name] = version
            digest, size = sha(path.read_bytes()), path.stat().st_size
            if inventory[name] != EXPECTED_PINS.get(name):
                raise ValueError("Unexpected resolved package/version; no upgrades permitted")
            if name == 'pylatexenc':
                if digest != '7211b83dc685ec8e5e25d09c5538d867279a4bb41058c00ab12fa8a8250bfcd2':
                    raise ValueError('Custom wheel was substituted')
                records.append(dict(name=name, version=version, filename=path.name, bytes=size, sha256=digest,
                                    provenance='retained custom build; not public wheel or reproducible rebuild'))
            else:
                frozen = REVIEWED_PUBLIC.get(path.name)
                if frozen != dict(sha256=digest, bytes=size):
                    raise ValueError('Wheel differs from reviewed versioned metadata candidates')
                url, response = fetch_version(name, version)
                write(metadata / (name + '.json'), response)
                match_published(json.loads(response), path.name, digest, size, name, version)
                records.append(dict(name=name, version=version, filename=path.name, bytes=size, sha256=digest,
                                    metadata_url=url, metadata_sha256=sha(response)))
            locks.append(name + "==" + version + " --hash=sha256:" + digest)
        if inventory != direct:
            raise ValueError("Resolved wheels do not match direct pins")
        write(output / "wheel-manifest.json", records)
        lock = ("\n".join(locks) + "\n").encode(); write(output / "requirements.lock", lock)
        status["stage"] = "offline-install"
        target = output / "environment"
        command([sys.executable, "-I", "-m", "venv", str(target)], output, "venv", environment, 120)
        python = str(target / "bin/python")
        command([python, "-I", "-m", "pip", "--isolated", "--disable-pip-version-check", "--no-input",
                "install", "--no-index", "--no-cache-dir", "--only-binary=:all:", "--require-hashes",
                "--find-links", str(wheels), "-r", str(output / "requirements.lock")], output, "install", environment, 600)
        status["stage"] = "installed-validation"
        command([python, "-I", "-m", "pip", "--isolated", "check"], output, "pip-check", environment, 60)
        code = "import importlib.metadata as m,json,re; print(json.dumps([{'name':re.sub('[-_.]+','-',d.metadata['Name']).lower(),'version':d.version} for d in m.distributions()]))"
        command([python, "-I", "-c", code], output, "installed-inventory", environment, 30)
        installed = json.loads((output / "installed-inventory.log").read_bytes())
        actual = {x["name"]: x["version"] for x in installed}
        if len(actual) != len(installed) or actual != inventory:
            raise ValueError("Installed distribution inventory differs from verified lock")
        status["stage"] = "import-validation"
        command([python, '-I', '-c', "import qiskit,qiskit_aer,pylatexenc,nbclient,json; print(json.dumps({m.__name__:m.__file__ for m in (qiskit,qiskit_aer,pylatexenc,nbclient)}))"], output, 'imports', environment, 120)
        imports = json.loads((output / 'imports.log').read_bytes())
        if set(imports) != {'qiskit', 'qiskit_aer', 'pylatexenc', 'nbclient'} or any(
                not Path(value).resolve().is_relative_to(target.resolve()) for value in imports.values()):
            raise ValueError('Imported module escaped the fresh environment')
        original_manifest = json.loads((inputs / 'manifest.json').read_bytes())
        for name, record in original_manifest['files'].items():
            if sha((inputs / name).read_bytes()) != record['sha256']:
                raise ValueError('Retained input changed during acquisition')
        for path in wheels.iterdir():
            if sha(path.read_bytes()) != next(r['sha256'] for r in records if r['filename']==path.name):
                raise ValueError('Wheel changed during installation')
        status.update(public_wheels=53, custom_wheels=1, imports_verified=True)
        status.update(state="succeeded", stage="complete", wheels=len(records), lock_sha256=sha(lock), exact_inventory=True)
    except BaseException as error:
        status.update(error_type=type(error).__name__, error=str(error))
    finally:
        write(output / "status.json", status)
        write(output / "evidence-manifest.json", {str(p.relative_to(output)):sha(p.read_bytes())
              for p in output.rglob('*') if p.is_file() and not p.is_symlink() and "environment" not in p.relative_to(output).parts})
    print(json.dumps(status))
    return 0 if status["state"] == "succeeded" else 1


if __name__ == "__main__":
    sys.exit(main())
