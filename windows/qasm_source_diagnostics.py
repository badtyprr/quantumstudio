"""Original-file diagnostics for the pinned, single-request compiler process."""
import logging
import re

from antlr4.error.Errors import RecognitionException
from openqasm3.parser import QASM3ParsingError

from qasm_source_bundle import SourceError


_AST_LOCATION = re.compile(r"^L(\d+):C(\d+): (.*)", re.DOTALL)
_COMPILER_LOCATION = re.compile(r"^Error at line (\d+), column (\d+) in QASM file")


class LocatedError(ValueError):
    """An adapter failure with optional parser coordinates, separate from prose."""
    def __init__(self, message, span):
        super().__init__(message)
        self.line = getattr(span, "start_line", None)
        self.column = getattr(span, "start_column", None)


def error_at(node, message):
    # Keep str(error) unchanged for stdin-only clients.
    return LocatedError(message, getattr(node, "span", None))


def _parser_location(error):
    """Use typed parser failures; never guess coordinates from user messages."""
    pending, seen = [error], set()
    while pending and len(seen) < 64:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, LocatedError) and type(current.line) is int and type(current.column) is int:
            return current.line, current.column, str(current)
        if isinstance(current, RecognitionException):
            token = current.offendingToken
            if token is not None:
                return token.line, token.column, "Unexpected token " + repr(token.text)
        if isinstance(current, QASM3ParsingError):
            match = _AST_LOCATION.match(str(current))
            if match:
                return int(match[1]), int(match[2]), match[3]
        pending.extend(value for value in (current.__cause__, current.__context__, *current.args)
                       if isinstance(value, BaseException))
    return None


def _label(bundle, line, column):
    try:
        location = bundle.location(line, column)
    except ValueError:
        return None
    suffix = " (expanded include boundary)" if location.synthetic else ""
    return f"{location.name}:{location.line}:{location.column + 1}{suffix}"


class _CompilerLocations(logging.Filter):
    """Adapt the pinned compiler's span-bearing log record before rendering it."""
    def __init__(self, bundle):
        super().__init__()
        self.bundle = bundle
        self.last_label = None

    def filter(self, record):
        message = record.getMessage()
        match = _COMPILER_LOCATION.match(message)
        if match:
            label = _label(self.bundle, int(match[1]), int(match[2]))
            if label:
                self.last_label = label
                record.msg = label + message[match.end():]
                record.args = ()
        return True


def compile_source(bundle, convert, **options):
    """Preserve compiler behavior, adding only evidenced original locations.

    PyQASM 1.0.4 exposes semantic spans through its logger, while grammar
    failures retain ANTLR tokens in the exception chain. This adapter handles
    both contracts. Location-free failures name the entry file without
    inventing a line. The temporary filter is always removed.
    """
    logger = logging.getLogger("pyqasm")
    locations = _CompilerLocations(bundle)
    logger.addFilter(locations)
    try:
        result = convert(bundle.expanded, **options)
        def locations_in(value):
            if isinstance(value, dict):
                context = value.get('WireSource')
                match = re.fullmatch(r'OpenQASM:(\d+):(\d+)', context or '')
                if match:
                    label = _label(bundle, int(match[1]), int(match[2])-1)
                    if label is not None:
                        if len(label.encode('utf-8')) > 512:
                            raise SourceError('Runtime wire source location exceeds 512 UTF-8 bytes.')
                        value['WireSource'] = label
                for item in value.values(): locations_in(item)
            elif isinstance(value, list):
                for item in value: locations_in(item)
        locations_in(result)
        return result
    except Exception as error:
        parser = _parser_location(error)
        label = locations.last_label
        message = str(error)
        if parser:
            line, column, detail = parser
            label = _label(bundle, line, column)
            message = detail
        raise SourceError(f"{label or bundle.entry}: {message or 'OpenQASM compilation failed.'}") from error
    finally:
        logger.removeFilter(locations)
