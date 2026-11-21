"""Run a Windows GUI replay on a separate window station and clipboard.

Pass the GUI runner executable followed by its normal arguments. The runner
writes its results to its output directory. Run one clipboard replay at a time.
"""
import argparse
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import sys


class StartupInfo(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD), ("reserved", wintypes.LPWSTR),
        ("desktop", wintypes.LPWSTR), ("title", wintypes.LPWSTR),
        *[(field, wintypes.DWORD) for field in
          ("x", "y", "width", "height", "xchars", "ychars", "fill", "flags")],
        ("show", wintypes.WORD), ("reserved_size", wintypes.WORD),
        ("reserved_data", wintypes.LPVOID), ("stdin", wintypes.HANDLE),
        ("stdout", wintypes.HANDLE), ("stderr", wintypes.HANDLE),
    ]


class ProcessInfo(ctypes.Structure):
    _fields_ = [("process", wintypes.HANDLE), ("thread", wintypes.HANDLE),
                ("process_id", wintypes.DWORD), ("thread_id", wintypes.DWORD)]


def checked(library, name, result, types, *args):
    fn = getattr(library, name)
    fn.restype, fn.argtypes = result, types
    value = fn(*args)
    if not value:
        raise ctypes.WinError(ctypes.get_last_error())
    return value


def station_name(user32, station):
    name = ctypes.create_unicode_buffer(256)
    size = wintypes.DWORD()
    checked(user32, "GetUserObjectInformationW", wintypes.BOOL,
            [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)],
            station, 2, name, ctypes.sizeof(name), ctypes.byref(size))
    return name.value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runner", type=Path)
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("A Windows desktop is required.")
    runner = str(args.runner.resolve(strict=True))
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    original = checked(user32, "GetProcessWindowStation", wintypes.HANDLE, [])
    maximum_allowed = 0x02000000
    # An unnamed request opens the station associated with this logon session.
    # Its generated name differs from the interactive WinSta0.
    station = checked(user32, "CreateWindowStationW", wintypes.HANDLE,
                      [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID],
                      None, 0, maximum_allowed, None)
    name = station_name(user32, station)
    if name.casefold() == station_name(user32, original).casefold() or name.casefold() == "winsta0":
        raise RuntimeError("A separate clipboard station is required.")
    desktop_name = f"QalculateReplay{os.getpid()}"
    checked(user32, "SetProcessWindowStation", wintypes.BOOL, [wintypes.HANDLE], station)
    try:
        checked(user32, "CreateDesktopW", wintypes.HANDLE,
                [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID],
                desktop_name, None, None, 0, maximum_allowed, None)
    finally:
        checked(user32, "SetProcessWindowStation", wintypes.BOOL, [wintypes.HANDLE], original)
    startup = StartupInfo()
    startup.cb = ctypes.sizeof(startup)
    startup.desktop = name + "\\" + desktop_name
    process = ProcessInfo()
    command = ctypes.create_unicode_buffer(subprocess.list2cmdline([runner, *args.arguments]))
    checked(kernel32, "CreateProcessW", wintypes.BOOL,
            [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.LPVOID, wintypes.LPVOID, wintypes.BOOL, wintypes.DWORD,
             wintypes.LPVOID, wintypes.LPCWSTR, ctypes.POINTER(StartupInfo), ctypes.POINTER(ProcessInfo)],
            runner, command, None, None, False, 0x08000000, None, None, ctypes.byref(startup), ctypes.byref(process))
    wait = kernel32.WaitForSingleObject
    wait.argtypes, wait.restype = [wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD
    if wait(process.process, 0xffffffff) != 0:
        raise ctypes.WinError(ctypes.get_last_error())
    code = wintypes.DWORD()
    checked(kernel32, "GetExitCodeProcess", wintypes.BOOL,
            [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)], process.process, ctypes.byref(code))
    # This standalone launcher owns the station, desktop and process handles
    # until the child exits. Windows closes them when the launcher terminates.
    return code.value


if __name__ == "__main__":
    sys.exit(main())
