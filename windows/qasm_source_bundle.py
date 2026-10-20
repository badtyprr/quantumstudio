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
    bom: bool = False


@dataclass(frozen=True)
class SourcePiece:
    """A contiguous expansion fragment and its original source location."""
    name: str
    line: int
    text: str
    column: int = 0
    synthetic: bool = False


@dataclass(frozen=True)
class SourceLocation:
    """Original character coordinates: one-based line, zero-based column."""
    name: str
    line: int
    column: int
    synthetic: bool = False


@dataclass(frozen=True)
class SourceBundle:
    root: Path
    entry: str
    files: tuple[SourceFile, ...]
    pieces: tuple[SourcePiece, ...]
    bindings: tuple[tuple[str, str], ...]
    module_headers: bool = False

    @property
    def expanded(self):
        return "".join(piece.text for piece in self.pieces)

    def location(self, line, column):
        """Map parser coordinates without consulting source files on disk.

        Columns count Unicode characters, matching the pinned ANTLR parser.
        An inserted separator points to its include directive and is marked
        synthetic, so a caller cannot mistake it for original source text.
        Invalid coordinates reject rather than inventing a nearby location.
        """
        if type(line) is not int or type(column) is not int or line < 1 or column < 0:
            raise ValueError("Expected a positive source line and nonnegative column.")
        text = self.expanded
        start = 0
        for _ in range(line - 1):
            newline = text.find("\n", start)
            if newline < 0:
                raise ValueError("Expanded source line is out of range.")
            start = newline + 1
        end = text.find("\n", start)
        if end < 0:
            end = len(text)
        if column > end - start:
            raise ValueError("Expanded source column is out of range.")
        offset = start + column
        if not self.pieces:
            return SourceLocation(self.entry, 1, 0)
        position = 0
        for index, piece in enumerate(self.pieces):
            stop = position + len(piece.text)
            if offset < stop or index == len(self.pieces) - 1:
                if piece.synthetic:
                    return SourceLocation(piece.name, piece.line, piece.column, True)
                prefix = piece.text[:offset - position]
                newlines = prefix.count("\n")
                original_column = len(prefix) - prefix.rfind("\n") - 1 if newlines else piece.column + len(prefix)
                return SourceLocation(piece.name, piece.line + newlines, original_column)
            position = stop

    def snapshot(self):
        """JSON-compatible provenance; text and BOM reconstruct the hashed bytes."""
        return {"Version": 1, "Root": str(self.root), "Entry": self.entry,
                "ModuleHeaders": self.module_headers,
                "Files": [{"Name": f.name, "Sha256": f.sha256, "Text": f.text, "Bom": f.bom}
                          for f in self.files],
                "Bindings": [{"Path": name, "Target": target} for name, target in self.bindings]}

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


def check_snapshot(snapshot, *, root):
    """Check saved provenance only beneath a root explicitly selected now.

    Root in the saved JSON is descriptive metadata, never filesystem authority.
    Validate every name and hash before touching disk, and leave the snapshot
    unchanged even when a dependency is missing or its link has been retargeted.
    """
    def fields(value, names):
        if not isinstance(value, dict) or set(value) != set(names.split()):
            raise SourceError("Invalid source snapshot fields.")
        return value

    def relative(value, canonical):
        if (not isinstance(value, str) or not value or len(value) > 32768
                or value.startswith("/") or any(c in value for c in "\\:\0")):
            raise SourceError("Source paths must be relative and use '/' separators.")
        depth = 0
        for part in value.split("/"):
            if part in ("", "."):
                raise SourceError("Empty or dot source path component.")
            if part == "..":
                depth -= 1
                if canonical or depth < 0:
                    raise SourceError("Source path escapes its root.")
            else:
                depth += 1
        if not depth:
            raise SourceError("Source path must identify a file.")
        return value

    fields(snapshot, "Version Root Entry ModuleHeaders Files Bindings")
    if type(snapshot["Version"]) is not int or snapshot["Version"] != 1:
        raise SourceError("Expected source snapshot version 1.")
    if (not isinstance(snapshot["Root"], str) or not snapshot["Root"]
            or len(snapshot["Root"]) > 32768 or "\0" in snapshot["Root"]
            or type(snapshot["ModuleHeaders"]) is not bool):
        raise SourceError("Invalid source snapshot metadata.")
    entry = relative(snapshot["Entry"], True)
    for name in ("Files", "Bindings"):
        if not isinstance(snapshot[name], list) or not 1 <= len(snapshot[name]) <= MAX_FILES:
            raise SourceError("Source snapshots require 1 to 64 files and dependency paths.")
    files, bindings, total = {}, {}, 0
    for item in snapshot["Files"]:
        fields(item, "Name Sha256 Text Bom")
        name = relative(item["Name"], True)
        if name in files or not isinstance(item["Text"], str) or type(item["Bom"]) is not bool:
            raise SourceError("Invalid or duplicate source file.")
        try:
            data = (b"\xef\xbb\xbf" if item["Bom"] else b"") + item["Text"].encode("utf-8")
        except UnicodeEncodeError as error:
            raise SourceError("Source snapshot contains invalid Unicode.") from error
        total += len(data)
        if total > MAX_BYTES:
            raise SourceError("Source snapshot exceeds 262144 bytes.")
        digest = item["Sha256"]
        if not isinstance(digest, str) or hashlib.sha256(data).hexdigest() != digest.lower():
            raise SourceError("Source hash mismatch: " + name)
        files[name] = digest.lower()
    for item in snapshot["Bindings"]:
        fields(item, "Path Target")
        name, target = relative(item["Path"], False), relative(item["Target"], True)
        if name in bindings or target not in files:
            raise SourceError("Duplicate or unresolved source dependency binding.")
        bindings[name] = target
    if entry not in bindings or set(bindings.values()) != set(files):
        raise SourceError("Source entry or dependency identity is missing.")

    if root is None or not os.fspath(root).strip():
        raise SourceError("Select a source root directory.")
    selected = Path(root).resolve(strict=True)
    if not selected.is_dir():
        raise SourceError("Select a source root directory.")
    results = []
    for name, expected_target in bindings.items():
        row = {"Path": name, "Target": expected_target}
        try:
            path = _inside(selected / name, selected)
            actual_target = path.relative_to(selected).as_posix()
            if actual_target != expected_target:
                row.update(Status="retargeted", CurrentTarget=actual_target)
            else:
                digest = hashlib.sha256(_read(path)).hexdigest()
                row["Status"] = "unchanged" if digest == files[expected_target] else "changed"
        except FileNotFoundError:
            row["Status"] = "missing"
        except (OSError, SourceError):
            # Includes escaped links, directories, inaccessible and oversized
            # files. Do not read escaped targets or expose their contents.
            row["Status"] = "unavailable"
        results.append(row)
    return {"Version": 1, "Root": str(selected), "Files": results,
            "Unchanged": all(row["Status"] == "unchanged" for row in results)}


def capture_source(entry, *, root=None, module_headers=False):
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
    root_version = None
    standard_includes = set()

    def header(text, name):
        lexer = qasm3Lexer(InputStream(text))
        lexer.removeErrorListeners()
        lexer.addErrorListener(_LexerErrors(name))
        tokens = [t for t in lexer.getAllTokens() if t.channel == Token.DEFAULT_CHANNEL]
        versions = [i for i, token in enumerate(tokens) if token.type == qasm3Lexer.OPENQASM]
        if not versions:
            return None
        if versions != [0] or len(tokens) < 3 or tokens[2].type != qasm3Lexer.SEMICOLON:
            raise SourceError(f"{name}: A version header must occur once, at the start.")
        parts = tokens[1].text.split(".")
        if not 1 <= len(parts) <= 2 or not all(part.isascii() and part.isdigit() for part in parts):
            raise SourceError(f"{name}: Invalid OpenQASM version header.")
        version = (int(parts[0]), int(parts[1]) if len(parts) == 2 else 0)
        return version, tokens[0].start, tokens[2].stop + 1

    def append(name, line, text, column=0, synthetic=False):
        nonlocal expanded_bytes
        expanded_bytes += len(text.encode("utf-8"))
        if expanded_bytes > MAX_BYTES:
            raise SourceError(f"{name}:{line}: Expanded source exceeds {MAX_BYTES} bytes.")
        if text:
            pieces.append(SourcePiece(name, line, text, column, synthetic))

    def visit(path, active):
        nonlocal total_bytes, root_version
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
            files[name] = SourceFile(name, hashlib.sha256(data).hexdigest(), text, data.startswith(b"\xef\xbb\xbf"))
        text = files[name].text
        if module_headers:
            declaration = header(text, name)
            if not active:
                root_version = declaration[0] if declaration else None
            elif declaration:
                if root_version is None or declaration[0] != root_version:
                    raise SourceError(f"{name}: Included module version must match the entry file's explicit version.")
                # An explicit adapter extension for generated standalone modules.
                # Preserve original source and line offsets in the snapshot.
                _, start, end = declaration
                text = text[:start] + "".join(c if c in "\r\n" else " " for c in text[start:end]) + text[end:]
        cursor = 0
        def fragment(start, end):
            append(name, text.count("\n", 0, start) + 1, text[start:end],
                   start - text.rfind("\n", 0, start) - 1)
        for start, end, line, filename in _includes(text, name):
            if filename in STANDARD_INCLUDES:
                if module_headers and filename in standard_includes:
                    fragment(cursor, start)
                    append(name, line, "".join(c if c in "\r\n" else " " for c in text[start:end]),
                           start - text.rfind("\n", 0, start) - 1)
                    cursor = end
                standard_includes.add(filename)
                continue
            fragment(cursor, start)
            # Interpret portable relative filenames only. Windows drive-relative
            # paths, UNC paths and alternate data streams are never implicit roots.
            if (not filename or filename.startswith("/") or "\\" in filename or ":" in filename
                    or Path(filename).is_absolute() or PureWindowsPath(filename).drive):
                raise SourceError(f"{name}:{line}: Include requires a relative filename using '/' separators.")
            include_column = start - text.rfind("\n", 0, start) - 1
            append(name, line, "\n", include_column, True)
            try:
                visit(path.parent / filename, (*active, name))
            except (OSError, SourceError) as error:
                raise SourceError(f'{name}:{line}: include "{filename}": {error}') from error
            append(name, line, "\n", include_column, True)
            cursor = end
        fragment(cursor, len(text))

    visit(entry, ())
    return SourceBundle(root, entry.relative_to(root).as_posix(), tuple(files.values()), tuple(pieces), tuple(bindings.items()), module_headers)
