"""Prepare the hash-locked Windows wheelhouse for a reviewed transpiler notebook."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
from urllib.request import urlopen
import venv

ROOT = Path(__file__).resolve().parent
PROFILES = {"qb011": "transpiler-pyquil-win-py312", "qb012": "transpiler-win-py312"}
SOURCE_HASH = "4361e759782f58dd0b8aa3a6d901e3ea5709f91c6a060bd444081fbb007b05a9"
BACKEND_HASH = "ca140b45d5325a9478f880e351484f62fef15f336462e449ca0c03c873d589c2"
WHEEL_HASH = "8eda564220237edd729da76e3eb081ce43eae8a1adf0c0e591a8fe6c366fc3c9"


def download_verified(project, version, filename, expected, directory):
    with urlopen(f"https://pypi.org/pypi/{project}/{version}/json", timeout=45) as response:
        files = json.load(response)["urls"]
    entry = next(f for f in files if f["filename"] == filename and f["digests"]["sha256"] == expected)
    target = directory / filename
    with urlopen(entry["url"], timeout=90) as response, target.open("xb") as output:
        shutil.copyfileobj(response, output)
    if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
        raise ValueError(f"Unexpected digest for {filename}")
    return target


def prepare(contract, destination):
    if sys.platform != "win32" or sys.version_info[:3] != (3, 12, 10) or struct.calcsize("P") != 8:
        raise ValueError("Use Windows 64-bit CPython 3.12.10 for these wheels")
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    profile = json.loads((ROOT / "profiles" / (PROFILES[contract] + ".json")).read_bytes())
    lock = ROOT / profile["lock"]
    if hashlib.sha256(lock.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != profile["lock_sha256"]:
        raise ValueError("Dependency lock digest differs from the profile")

    with tempfile.TemporaryDirectory(dir=destination.parent) as temp:
        work = Path(temp)
        source = download_verified("rpcq", "3.11.0", "rpcq-3.11.0.tar.gz", SOURCE_HASH, work)
        backend = download_verified("setuptools", "84.2.1", "setuptools-84.2.1-py3-none-any.whl",
                                    BACKEND_HASH, work)
        venv.EnvBuilder(with_pip=True).create(work / "builder")
        pip = [str(work / "builder/Scripts/python.exe"), "-B", "-m", "pip", "--isolated",
               "--disable-pip-version-check"]
        subprocess.run(pip + ["install", "--no-index", "--no-deps", str(backend)], check=True)
        built = work / "built"
        subprocess.run(pip + ["wheel", "--no-index", "--no-deps", "--no-cache-dir", "--use-pep517",
                              "--no-build-isolation", "-w", str(built), str(source)], check=True,
                       env=dict(os.environ, SOURCE_DATE_EPOCH="315532800", PYTHONHASHSEED="0"))
        wheel = built / "rpcq-3.11.0-py3-none-any.whl"
        if hashlib.sha256(wheel.read_bytes()).hexdigest() != WHEEL_HASH:
            raise ValueError("Rebuilt rpcq wheel differs from the reviewed wheel")
        wheels = work / "wheels"
        subprocess.run(pip + ["download", "--index-url", "https://pypi.org/simple", "--only-binary=:all:",
                              "--require-hashes", "--no-deps", "--find-links", str(built), "-r", str(lock),
                              "--dest", str(wheels)], check=True)
        wheels.rename(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", choices=PROFILES)
    parser.add_argument("destination", type=Path, help="new wheelhouse directory")
    args = parser.parse_args()
    prepare(args.contract, args.destination)
