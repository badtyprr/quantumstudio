"""Creation-owned Windows launch for dedicated notebook supervisors.

Windows 10+, 64-bit only. No Popen fallback. Import canonically once per process.
All supervisor launches must cooperate with launch_lock; uncoordinated native
broad-inheritance launches in this process are outside this finite contract.
Native API binding is lazy, so tests can inject an API without calling Windows.
"""
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import math
import os
import subprocess
import sys
import threading


_LOCK = threading.Lock()
_TAINTED = False


@contextmanager
def launch_lock():
    """Serialize the entire temporary inheritable-handle lifetime."""
    if __name__ != 'windows_lifecycle':
        raise RuntimeError('NONCANONICAL_LAUNCH_MODULE')
    with _LOCK:
        if _TAINTED:
            raise RuntimeError('LAUNCH_STATE_TAINTED')
        yield


def _attempt(errors, label, operation):
    try:
        return operation()
    except BaseException as error:
        errors.append((label, error))


def _attach(primary, errors):
    primary.cleanup_errors = [(label, str(error)) for label, error in errors]
    for label, error in errors:
        primary.add_note(label + ': ' + repr(error))


def _raise_cleanup(errors):
    if errors:
        error = RuntimeError('WINDOWS_RESOURCE_CLEANUP_FAILED')
        _attach(error, errors)
        raise error


def _milliseconds(timeout):
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise ValueError('FINITE_TIMEOUT_REQUIRED')
    if not math.isfinite(timeout) or timeout < 0 or timeout > 4294967:
        raise ValueError('FINITE_TIMEOUT_REQUIRED')
    return math.ceil(timeout * 1000)


def _launch_strings(argv, cwd, env):
    if (not isinstance(argv, (list, tuple)) or not argv
            or any(type(arg) is not str or '\0' in arg for arg in argv) or not argv[0]):
        raise ValueError('INVALID_LAUNCH_ARGUMENTS')
    command = subprocess.list2cmdline(argv)
    if len(command.encode('utf-16-le')) // 2 >= 32767:
        raise ValueError('COMMAND_LINE_TOO_LONG')
    if cwd is not None:
        cwd = os.fspath(cwd)
        if type(cwd) is not str or '\0' in cwd:
            raise ValueError('INVALID_WORKING_DIRECTORY')
    environment = None
    if env is not None:
        rows, seen = [], set()
        for key, value in env.items():
            if (type(key) is not str or type(value) is not str or not key
                    or '\0' in key or '\0' in value or '=' in key):
                raise ValueError('INVALID_ENVIRONMENT')
            folded = key.upper()
            if folded in seen:
                raise ValueError('DUPLICATE_ENVIRONMENT_KEY')
            seen.add(folded)
            rows.append((key, value))
        # Reject duplicate case-insensitive keys, rather than silently replace.
        environment = '\0'.join(key + '=' + value for key, value in
                                sorted(rows, key=lambda row: row[0].upper())) + '\0\0'
    return command, cwd, environment


class _TextPipe:
    """Unbuffered UTF-8/LF control writer; flush never waits for child reads."""
    def __init__(self, api, handle):
        self.api, self.handle = api, handle

    @property
    def closed(self):
        return self.handle is None

    def flush(self):
        if self.closed:
            raise ValueError('CONTROL_PIPE_CLOSED')

    def write(self, value):
        self.flush()
        if type(value) is not str:
            raise TypeError('CONTROL_PIPE_REQUIRES_TEXT')
        raw = value.encode('utf-8')
        while raw:
            size = self.api.write(self.handle, raw)
            if not 0 < size <= len(raw):
                raise OSError('INVALID_PIPE_WRITE_SIZE')
            raw = raw[size:]
        return len(value)

    def close(self):
        if self.handle is not None:
            self.api.close(self.handle)
            self.handle = None


class OwnedProcess:
    """Held-handle Popen subset; Job termination/drain belongs to the caller."""
    def __init__(self, api, argv, process, pid, stdin, identity):
        self._api, self.args = api, list(argv)
        self._handle, self.pid, self.stdin = process, pid, stdin
        self.identity, self.returncode = identity, None

    @property
    def process_handle(self):
        if self._handle is None:
            raise ValueError('PROCESS_HANDLE_CLOSED')
        return self._handle

    def poll(self):
        if self.returncode is not None:
            return self.returncode
        if self._api.wait(self.process_handle, 0):
            self.returncode = self._api.exit_code(self.process_handle)
        return self.returncode

    def wait(self, timeout=10):
        milliseconds = _milliseconds(timeout)
        if self.returncode is not None:
            return self.returncode
        if not self._api.wait(self.process_handle, milliseconds):
            raise subprocess.TimeoutExpired(self.args, timeout)
        self.returncode = self._api.exit_code(self.process_handle)
        return self.returncode

    def kill(self):
        if self.poll() is None:
            self._api.terminate_process(self.process_handle)

    terminate = kill

    def close(self):
        errors = []
        _attempt(errors, 'close_control_pipe', self.stdin.close)
        if self._handle is not None:
            handle = self._handle
            before = len(errors)
            _attempt(errors, 'close_process_handle', lambda: self._api.close(handle))
            if len(errors) == before:
                self._handle = None
        _raise_cleanup(errors)


def launch_owned(argv, *, job_handle, stdout, stderr, cwd=None, env=None, _api=None):
    """Create in the supplied Job, verify while suspended, then resume once.

The caller exclusively owns the noninheritable kill-on-close Job and must drain
and close it even if this constructor fails. No successful process escapes the
failure cleanup path. _api is a private deterministic test seam.
"""
    global _TAINTED
    command, cwd, environment = _launch_strings(argv, cwd, env)
    api = _api if _api is not None else _NativeAPI()
    inherited, ordinary = [], []
    attributes = None
    process = thread = parent_pipe = None
    errors = []

    def release_inherited():
        global _TAINTED
        for handle in inherited[:]:
            try:
                api.close(handle)
                inherited.remove(handle)
            except BaseException as error:
                errors.append(('close_inherited_handle', error))
                try:
                    api.inherit(handle, False)
                    inherited.remove(handle)
                    ordinary.append(handle)
                except BaseException as fallback:
                    errors.append(('disable_handle_inheritance', fallback))
                    _TAINTED = True

    with launch_lock():
        try:
            api.require_noninheritable(job_handle)
            child_pipe, parent_pipe = api.pipe()
            ordinary.extend((child_pipe, parent_pipe))
            # Track before enabling inheritance so a failed call still cleans it.
            inherited.append(child_pipe)
            ordinary.remove(child_pipe)
            api.inherit(child_pipe, True)
            for stream in (stdout, stderr):
                handle = api.duplicate_file(stream)
                inherited.append(handle)
            attributes = api.attributes(job_handle, inherited)
            process, thread, pid = api.create(argv[0], command, cwd, environment,
                                              attributes, inherited)
            release_inherited()
            _raise_cleanup(errors)
            api.delete_attributes(attributes)
            attributes = None
            identity = api.identity(process, job_handle, pid)
            if api.resume(thread) != 1:
                raise RuntimeError('UNEXPECTED_PRIMARY_THREAD_SUSPEND_COUNT')
            api.close(thread)
            thread = None
            writer = _TextPipe(api, parent_pipe)
            result = OwnedProcess(api, argv, process, pid, writer, identity)
            ordinary.remove(parent_pipe)
            process = parent_pipe = None
            return result
        except BaseException as primary:
            # All independent attempts run even when diagnostics/termination fail.
            if process is not None:
                _attempt(errors, 'terminate_created_process', lambda: api.terminate_process(process))
                _attempt(errors, 'terminate_owned_job', lambda: api.terminate_job(job_handle))
                def collect():
                    if not api.wait(process, 10000):
                        raise TimeoutError('CREATED_PROCESS_COLLECTION_TIMEOUT')
                _attempt(errors, 'collect_created_process', collect)
            release_inherited()
            if attributes is not None:
                _attempt(errors, 'delete_attributes', lambda: api.delete_attributes(attributes))
            if thread is not None:
                _attempt(errors, 'close_primary_thread', lambda: api.close(thread))
            if process is not None:
                _attempt(errors, 'close_created_process', lambda: api.close(process))
            for handle in ordinary:
                _attempt(errors, 'close_pipe_or_duplicate', lambda handle=handle: api.close(handle))
            _attach(primary, errors)
            raise


class _StartupInfo(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('reserved', wintypes.LPWSTR),
                ('desktop', wintypes.LPWSTR), ('title', wintypes.LPWSTR)] + [
        (name, wintypes.DWORD) for name in ('x', 'y', 'width', 'height', 'chars_x',
                                          'chars_y', 'fill', 'flags')] + [
        ('show', wintypes.WORD), ('reserved_size', wintypes.WORD),
        ('reserved_bytes', ctypes.c_void_p), ('stdin', wintypes.HANDLE),
        ('stdout', wintypes.HANDLE), ('stderr', wintypes.HANDLE)]


class _StartupInfoEx(ctypes.Structure):
    _fields_ = [('startup', _StartupInfo), ('attributes', ctypes.c_void_p)]


class _ProcessInformation(ctypes.Structure):
    _fields_ = [('process', wintypes.HANDLE), ('thread', wintypes.HANDLE),
                ('pid', wintypes.DWORD), ('tid', wintypes.DWORD)]


class _NativeAPI:
    """Deferred Win32 calls; no API is loaded by importing this module."""
    def __init__(self):
        if sys.platform != 'win32' or ctypes.sizeof(ctypes.c_void_p) != 8:
            raise RuntimeError('WINDOWS_64_BIT_REQUIRED')
        if (ctypes.sizeof(_StartupInfo), ctypes.sizeof(_StartupInfoEx),
                ctypes.sizeof(_ProcessInformation)) != (104, 112, 24):
            raise RuntimeError('UNSUPPORTED_LAUNCH_ABI')
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        H, D, B, P = wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL, ctypes.c_void_p
        signatures = {
            'CreatePipe': ([ctypes.POINTER(H), ctypes.POINTER(H), P, D], B),
            'GetHandleInformation': ([H, ctypes.POINTER(D)], B),
            'SetHandleInformation': ([H, D, D], B),
            'DuplicateHandle': ([H, H, H, ctypes.POINTER(H), D, B, D], B),
            'GetCurrentProcess': ([], H),
            'InitializeProcThreadAttributeList': ([P, D, D, ctypes.POINTER(ctypes.c_size_t)], B),
            'UpdateProcThreadAttribute': ([P, D, ctypes.c_size_t, P, ctypes.c_size_t, P, P], B),
            'DeleteProcThreadAttributeList': ([P], None),
            'CreateProcessW': ([wintypes.LPCWSTR, wintypes.LPWSTR, P, P, B, D, P,
                                wintypes.LPCWSTR, P, ctypes.POINTER(_ProcessInformation)], B),
            'GetProcessId': ([H], D),
            'GetProcessTimes': ([H] + [ctypes.POINTER(wintypes.FILETIME)] * 4, B),
            'QueryFullProcessImageNameW': ([H, D, wintypes.LPWSTR, ctypes.POINTER(D)], B),
            'IsProcessInJob': ([H, H, ctypes.POINTER(B)], B),
            'ResumeThread': ([H], D),
            'WaitForSingleObject': ([H, D], D),
            'GetExitCodeProcess': ([H, ctypes.POINTER(D)], B),
            'TerminateProcess': ([H, wintypes.UINT], B),
            'TerminateJobObject': ([H, wintypes.UINT], B),
            'CloseHandle': ([H], B),
            'WriteFile': ([H, P, D, ctypes.POINTER(D), P], B),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.api, name)
            function.argtypes, function.restype = args, result

    @staticmethod
    def check(value):
        if not value:
            raise ctypes.WinError(ctypes.get_last_error())
        return value

    def require_noninheritable(self, handle):
        flags = wintypes.DWORD()
        self.check(self.api.GetHandleInformation(handle, ctypes.byref(flags)))
        if flags.value & 1:
            raise ValueError('JOB_HANDLE_MUST_NOT_BE_INHERITABLE')

    def pipe(self):
        read, write = wintypes.HANDLE(), wintypes.HANDLE()
        self.check(self.api.CreatePipe(ctypes.byref(read), ctypes.byref(write), None, 0))
        return read.value, write.value

    def inherit(self, handle, value):
        self.check(self.api.SetHandleInformation(handle, 1, int(value)))

    def duplicate_file(self, stream):
        import msvcrt
        handle = msvcrt.get_osfhandle(stream.fileno())
        duplicate = wintypes.HANDLE()
        current = self.api.GetCurrentProcess()
        self.check(self.api.DuplicateHandle(current, handle, current,
                   ctypes.byref(duplicate), 0, True, 2))  # DUPLICATE_SAME_ACCESS
        return duplicate.value

    def attributes(self, job, handles):
        size = ctypes.c_size_t()
        ctypes.set_last_error(0)
        result = self.api.InitializeProcThreadAttributeList(None, 2, 0, ctypes.byref(size))
        if result or ctypes.get_last_error() != 122 or not size.value:
            raise OSError('ATTRIBUTE_LIST_SIZE_QUERY_FAILED')
        storage = ctypes.create_string_buffer(size.value)
        jobs = (wintypes.HANDLE * 1)(job)
        inherited = (wintypes.HANDLE * len(handles))(*handles)
        self.check(self.api.InitializeProcThreadAttributeList(storage, 2, 0, ctypes.byref(size)))
        try:
            self.check(self.api.UpdateProcThreadAttribute(storage, 0, 0x2000D, jobs,
                                                         ctypes.sizeof(jobs), None, None))
            self.check(self.api.UpdateProcThreadAttribute(storage, 0, 0x20002, inherited,
                                                         ctypes.sizeof(inherited), None, None))
        except BaseException:
            self.api.DeleteProcThreadAttributeList(storage)
            raise
        return storage, jobs, inherited  # Keep value buffers alive until deletion.

    def delete_attributes(self, attributes):
        self.api.DeleteProcThreadAttributeList(attributes[0])

    def create(self, executable, command, cwd, environment, attributes, handles):
        startup = _StartupInfoEx()
        startup.startup.cb = ctypes.sizeof(startup)
        startup.startup.flags = 0x100  # STARTF_USESTDHANDLES
        startup.startup.stdin, startup.startup.stdout, startup.startup.stderr = handles
        startup.attributes = ctypes.cast(attributes[0], ctypes.c_void_p)
        info = _ProcessInformation()
        command_buffer = ctypes.create_unicode_buffer(command)
        env_buffer = None if environment is None else ctypes.create_unicode_buffer(environment)
        # SUSPENDED | UNICODE_ENVIRONMENT | EXTENDED_STARTUPINFO_PRESENT | NO_WINDOW
        flags = 0x4 | 0x400 | 0x80000 | 0x8000000
        self.check(self.api.CreateProcessW(executable, command_buffer, None, None, True,
                   flags, env_buffer, cwd, ctypes.byref(startup), ctypes.byref(info)))
        return info.process, info.thread, info.pid

    def identity(self, process, job, pid):
        if self.wait(process, 0):
            raise RuntimeError('CREATED_PROCESS_ALREADY_EXITED')
        actual_pid = self.check(self.api.GetProcessId(process))
        if actual_pid != pid:
            raise RuntimeError('CREATED_PROCESS_ID_MISMATCH')
        times = [wintypes.FILETIME() for _ in range(4)]
        self.check(self.api.GetProcessTimes(process, *(ctypes.byref(t) for t in times)))
        creation = times[0].dwHighDateTime << 32 | times[0].dwLowDateTime
        image = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(image))
        self.check(self.api.QueryFullProcessImageNameW(process, 0, image, ctypes.byref(size)))
        member = wintypes.BOOL()
        self.check(self.api.IsProcessInJob(process, job, ctypes.byref(member)))
        if not member.value or not creation or not image.value or self.wait(process, 0):
            raise RuntimeError('CREATED_PROCESS_IDENTITY_OR_JOB_UNCONFIRMED')
        return dict(launcher_pid=pid, creation_filetime=creation, image=image.value,
                    specific_job_member=True, held_handle=True)

    def resume(self, thread):
        value = self.api.ResumeThread(thread)
        if value == 0xFFFFFFFF:
            raise ctypes.WinError(ctypes.get_last_error())
        return value

    def wait(self, process, milliseconds):
        value = self.api.WaitForSingleObject(process, milliseconds)
        if value == 0:
            return True
        if value == 258:
            return False
        if value == 0xFFFFFFFF:
            raise ctypes.WinError(ctypes.get_last_error())
        raise OSError('UNEXPECTED_PROCESS_WAIT_RESULT: ' + str(value))

    def exit_code(self, process):
        code = wintypes.DWORD()
        self.check(self.api.GetExitCodeProcess(process, ctypes.byref(code)))
        return code.value

    def terminate_process(self, process):
        self.check(self.api.TerminateProcess(process, 1))

    def terminate_job(self, job):
        self.check(self.api.TerminateJobObject(job, 1))

    def close(self, handle):
        self.check(self.api.CloseHandle(handle))

    def write(self, handle, raw):
        written = wintypes.DWORD()
        self.check(self.api.WriteFile(handle, raw, len(raw), ctypes.byref(written), None))
        return written.value
