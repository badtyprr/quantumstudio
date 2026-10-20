"""Explicit source context for the compiler CLI; stdin retains its old contract."""
from qasm_source_bundle import capture_source, MAX_BYTES


def import_request(arguments, stdin, convert):
    flags, values = set(), {}
    index = 0
    while index < len(arguments):
        arg = arguments[index]
        if arg in flags or arg in values:
            raise ValueError("Duplicate OpenQASM option: " + arg)
        if arg in ("--published-u", "--classical", "--module-headers"):
            flags.add(arg)
        elif arg in ("--source-file", "--source-root"):
            index += 1
            if index == len(arguments) or arguments[index].startswith("--"):
                raise ValueError("Missing value for " + arg)
            values[arg] = arguments[index]
        else:
            raise ValueError("Unknown OpenQASM option: " + arg)
        index += 1
    options = dict(published_u="--published-u" in flags, classical="--classical" in flags)
    if "--source-file" in values:
        bundle = capture_source(values["--source-file"], root=values.get("--source-root"),
                                module_headers="--module-headers" in flags)
        circuit = convert(bundle.expanded, **options)
        return {"Version": 1, "Circuit": circuit, "Source": bundle.snapshot()}
    if "--source-root" in values or "--module-headers" in flags:
        raise ValueError("Source root and module headers require --source-file.")
    source = stdin.read(MAX_BYTES + 1)
    if len(source) > MAX_BYTES:
        raise ValueError("OpenQASM input must be at most 256 KB.")
    return convert(source.decode("utf-8-sig"), **options)
