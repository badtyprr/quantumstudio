"""Finite Linux dependency acquisition proof; not kernel/lifecycle acceptance."""
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.output.is_absolute() or not args.requirements.is_absolute():
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
        if identity["python"] != "3.12.10" or identity["platform"] != "linux" or identity["machine"] != "x86_64":
            raise ValueError("Requires CPython 3.12.10 Linux x86_64")
        if platform.python_implementation() != "CPython":
            raise ValueError("CPython required")
        raw = args.requirements.read_bytes()
        write(output / "direct-requirements.txt", raw)
        direct = pins(raw)
        if set(direct) != {"pip", "ipython", "ipykernel", "jupyter-client", "nbclient", "nbformat", "matplotlib"}:
            raise ValueError("Only the seven reviewed notebook bootstrap direct packages are in scope")
        write(output / "requirements-identity.json", dict(path=str(args.requirements.resolve()), sha256=sha(raw), pins=direct))
        wheels = output / "wheels"; wheels.mkdir()
        metadata = output / "pypi"; metadata.mkdir()
        home = output / "private-home"; home.mkdir()
        environment = clean_environment(home)
        pip = [sys.executable, "-I", "-m", "pip", "--isolated", "--disable-pip-version-check", "--no-input"]
        status["stage"] = "acquisition"
        command(pip + ["download", "--index-url", "https://pypi.org/simple", "--only-binary=:all:",
                "--no-cache-dir", "--keyring-provider", "disabled", "--timeout", "30", "--retries", "2",
                "--dest", str(wheels), "-r", str(output / "direct-requirements.txt")], output, "download", environment, 900)
        status["stage"] = "wheel-verification"
        inventory = {}; records = []; locks = []
        for path in sorted(wheels.iterdir()):
            name, version = wheel_metadata(path)
            if name in inventory:
                raise ValueError("Duplicate normalized wheel distribution")
            inventory[name] = version
            digest, size = sha(path.read_bytes()), path.stat().st_size
            url, response = fetch_version(name, version)
            write(metadata / (name + ".json"), response)
            match_published(json.loads(response), path.name, digest, size, name, version)
            records.append(dict(name=name, version=version, filename=path.name, bytes=size, sha256=digest,
                                metadata_url=url, metadata_sha256=sha(response)))
            locks.append(name + "==" + version + " --hash=sha256:" + digest)
        if not inventory or any(inventory.get(n) != v for n, v in direct.items()):
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
