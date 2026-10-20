"""Explicit source context for the compiler CLI; stdin retains its old contract."""
import json
from qasm_source_bundle import capture_source, check_snapshot, MAX_BYTES
from qasm_source_diagnostics import compile_source


def import_request(arguments, stdin, convert):
    flags, values = set(), {}
    index = 0
    while index < len(arguments):
        arg = arguments[index]
        if arg in flags or arg in values:
            raise ValueError("Duplicate OpenQASM option: " + arg)
        if arg in ("--published-u", "--classical", "--module-headers", "--check-source"):
            flags.add(arg)
        elif arg in ("--source-file", "--source-root"):
            index += 1
            if index == len(arguments) or arguments[index].startswith("--"):
                raise ValueError("Missing value for " + arg)
            values[arg] = arguments[index]
        else:
            raise ValueError("Unknown OpenQASM option: " + arg)
        index += 1
    if "--check-source" in flags:
        if flags != {"--check-source"} or set(values) != {"--source-root"}:
            raise ValueError("Source checking requires only --check-source and an explicit --source-root.")
        source = stdin.read(4194305)
        if len(source) > 4194304:
            raise ValueError("Source snapshot must be at most 4 MB.")
        return check_snapshot(json.loads(source.decode("utf-8-sig")), root=values["--source-root"])
    options = dict(published_u="--published-u" in flags, classical="--classical" in flags)
    if "--source-file" in values:
        bundle = capture_source(values["--source-file"], root=values.get("--source-root"),
                                module_headers="--module-headers" in flags)
        circuit = compile_source(bundle, convert, **options)
        return {"Version": 1, "Circuit": circuit, "Source": bundle.snapshot()}
    if "--source-root" in values or "--module-headers" in flags:
        raise ValueError("Source root and module headers require --source-file.")
    source = stdin.read(MAX_BYTES + 1)
    if len(source) > MAX_BYTES:
        raise ValueError("OpenQASM input must be at most 256 KB.")
    return convert(source.decode("utf-8-sig"), **options)
