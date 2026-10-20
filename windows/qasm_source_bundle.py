"""Immutable local OpenQASM sources; expansion never consults the working directory.

This component supplies source context, not compilation or editor persistence.
The selected root is a deliberate import boundary, including for symlink targets.
"""
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PureWindowsPath

from antlr4 import InputStream, Token
from antlr4.error.ErrorListener import ErrorListener
from openqasm3.parser import qasm3Lexer

MAX_BYTES = 262144
MAX_FILES = 64
MAX_DEPTH = 16
STANDARD_INCLUDES = frozenset(("stdgates.inc", "qelib1.inc"))


class SourceError(ValueError):
    pass


class _LexerErrors(ErrorListener):
    def __init__(self, name):
        self.name = name

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, error):
        raise SourceError(f"{self.name}:{line}:{column + 1}: {msg}")


def _includes(text, name):
    # Reuse the pinned grammar: comments, pragmas and calibration text must not
    # accidentally become filesystem requests.
    lexer = qasm3Lexer(InputStream(text))
    lexer.removeErrorListeners()
    lexer.addErrorListener(_LexerErrors(name))
    tokens = [t for t in lexer.getAllTokens() if t.channel == Token.DEFAULT_CHANNEL]
    for index, token in enumerate(tokens):
        if token.type != qasm3Lexer.INCLUDE:
            continue
        following = tokens[index + 1:index + 3]
        if (len(following) != 2 or following[0].type != qasm3Lexer.StringLiteral
                or following[1].type != qasm3Lexer.SEMICOLON):
            raise SourceError(f"{name}:{token.line}: Expected a quoted include filename and semicolon.")
        yield token.start, following[1].stop + 1, token.line, following[0].text[1:-1]


@dataclass(frozen=True)
class SourceFile:
    name: str
    sha256: str
    text: str


@dataclass(frozen=True)
class SourcePiece:
    """A contiguous expansion fragment and its original source location."""
    name: str
    line: int
    text: str


@dataclass(frozen=True)
class SourceBundle:
    root: Path
    entry: str
    files: tuple[SourceFile, ...]
    pieces: tuple[SourcePiece, ...]
    bindings: tuple[tuple[str, str], ...]

    @property
    def expanded(self):
        return "".join(piece.text for piece in self.pieces)

    def changed_files(self):
        """Compare captured bytes with disk; never change the captured program."""
        changed = []
        for source in self.files:
            try:
                path = _inside(self.root / source.name, self.root)
                digest = hashlib.sha256(_read(path)).hexdigest()
            except (OSError, SourceError):
                digest = None
            if digest != source.sha256 and source.name not in changed:
                changed.append(source.name)
        for name, target in self.bindings:
            try:
                current = _inside(self.root / name, self.root).relative_to(self.root).as_posix()
            except (OSError, SourceError):
                current = None
            if current != target and target not in changed and name not in changed:
                changed.append(name)
        return tuple(changed)


def _inside(path, root):
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise SourceError("Include target is outside the selected source root.")
    if not resolved.is_file():
        raise SourceError("Source is not a regular file.")
    return resolved


def _read(path):
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise SourceError(f"Source exceeds {MAX_BYTES} bytes.")
    return data


def capture_source(entry, *, root=None):
    """Capture a selected file and its relative includes, with bounded expansion.

    A caller may explicitly select a wider root; absolute include paths remain
    disallowed. Repeated includes expand repeatedly (no implicit include-once),
    leaving duplicate-definition diagnostics to the compiler.
    """
    entry = Path(entry).absolute()
    entry = entry.parent.resolve(strict=True) / entry.name
    root = Path(root).resolve(strict=True) if root is not None else entry.parent.resolve(strict=True)
    files, pieces, bindings = {}, [], {}
    total_bytes = expanded_bytes = 0

    def append(name, line, text):
        nonlocal expanded_bytes
        expanded_bytes += len(text.encode("utf-8"))
        if expanded_bytes > MAX_BYTES:
            raise SourceError(f"{name}:{line}: Expanded source exceeds {MAX_BYTES} bytes.")
        if text:
            pieces.append(SourcePiece(name, line, text))

    def visit(path, active):
        nonlocal total_bytes
        requested_path = Path(os.path.normpath(path))
        if not requested_path.is_relative_to(root):
            raise SourceError("Include path is outside the selected source root.")
        # Keep the original path for later identity checks: lexically collapsing
        # link/../file can select a different file than filesystem resolution.
        requested = path.relative_to(root).as_posix()
        path = _inside(path, root)
        name = path.relative_to(root).as_posix()
        bindings[requested] = name
        if len(bindings) > MAX_FILES:
            raise SourceError(f"{name}: Source bundle exceeds {MAX_FILES} dependency paths.")
        if name in active:
            raise SourceError("Include cycle: " + " -> ".join((*active, name)))
        if len(active) >= MAX_DEPTH:
            raise SourceError(f"{name}: Include nesting exceeds {MAX_DEPTH} files.")
        if name not in files:
            if len(files) >= MAX_FILES:
                raise SourceError(f"{name}: Source bundle exceeds {MAX_FILES} files.")
            data = _read(path)
            total_bytes += len(data)
            if total_bytes > MAX_BYTES:
                raise SourceError(f"{name}: Source bundle exceeds {MAX_BYTES} bytes.")
            try:
                text = data.decode("utf-8-sig")
            except UnicodeDecodeError as error:
                raise SourceError(f"{name}: Source must be valid UTF-8.") from error
            files[name] = SourceFile(name, hashlib.sha256(data).hexdigest(), text)
        text = files[name].text
        cursor = 0
        for start, end, line, filename in _includes(text, name):
            if filename in STANDARD_INCLUDES:
                continue
            append(name, text.count("\n", 0, cursor) + 1, text[cursor:start])
            # Interpret portable relative filenames only. Windows drive-relative
            # paths, UNC paths and alternate data streams are never implicit roots.
            if (not filename or filename.startswith("/") or "\\" in filename or ":" in filename
                    or Path(filename).is_absolute() or PureWindowsPath(filename).drive):
                raise SourceError(f"{name}:{line}: Include requires a relative filename using '/' separators.")
            append(name, line, "\n")
            try:
                visit(path.parent / filename, (*active, name))
            except (OSError, SourceError) as error:
                raise SourceError(f'{name}:{line}: include "{filename}": {error}') from error
            append(name, line, "\n")
            cursor = end
        append(name, text.count("\n", 0, cursor) + 1, text[cursor:])

    visit(entry, ())
    return SourceBundle(root, entry.relative_to(root).as_posix(), tuple(files.values()), tuple(pieces), tuple(bindings.items()))
