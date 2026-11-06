"""SDK-free injected launch tests. No WinDLL or process launch is permitted."""
import ctypes
import io
import subprocess
import threading
import unittest
from unittest.mock import Mock, patch

import windows_lifecycle as lifecycle


class FakeAPI:
    def __init__(self, fail=None):
        self.events, self.open, self.inheritable = [], set(), set()
        self.fail = fail
        self.terminal, self.code, self.suspend_count = False, 7, 1
        self.duplicate_count = 0

    def event(self, name, *args):
        self.events.append((name, *args))
        if self.fail == name or self.fail == (name, *args):
            raise OSError(name)

    def require_noninheritable(self, handle):
        self.event('require_noninheritable', handle)

    def pipe(self):
        self.event('pipe')
        self.open.update((1, 2))
        return 1, 2

    def inherit(self, handle, value):
        self.event('inherit', handle, value)
        if value:
            self.inheritable.add(handle)
        else:
            self.inheritable.discard(handle)

    def duplicate_file(self, stream):
        self.duplicate_count += 1
        self.event('duplicate_file', self.duplicate_count)
        handle = self.duplicate_count + 2
        self.open.add(handle)
        self.inheritable.add(handle)
        return handle

    def attributes(self, job, inherited):
        self.event('attributes', job, tuple(inherited))
        self.open.add('attributes')
        return 'attributes'

    def delete_attributes(self, attributes):
        self.event('delete_attributes', attributes)
        self.open.remove(attributes)

    def create(self, exe, command, cwd, environment, attributes, handles):
        self.event('create', exe, command, cwd, environment, attributes, tuple(handles))
        self.open.update((10, 11))
        return 10, 11, 42

    def identity(self, process, job, pid):
        self.event('identity', process, job, pid)
        return dict(launcher_pid=pid, specific_job_member=True, held_handle=True)

    def resume(self, thread):
        self.event('resume', thread)
        return self.suspend_count

    def close(self, handle):
        self.event('close', handle)
        self.open.remove(handle)
        self.inheritable.discard(handle)

    def wait(self, handle, milliseconds):
        self.event('wait', handle, milliseconds)
        return self.terminal

    def exit_code(self, handle):
        self.event('exit_code', handle)
        return self.code

    def terminate_process(self, handle):
        self.event('terminate_process', handle)
        self.terminal = True

    def terminate_job(self, handle):
        self.event('terminate_job', handle)
        self.terminal = True

    def write(self, handle, raw):
        self.event('write', handle, raw)
        return len(raw)


class LaunchTests(unittest.TestCase):
    def setUp(self):
        self.native_guard = patch.object(lifecycle, '_NativeAPI', side_effect=AssertionError('NATIVE_API_FORBIDDEN'))
        self.native_guard.start()
        self.addCleanup(self.native_guard.stop)
        self.addCleanup(setattr, lifecycle, '_TAINTED', False)

    def launch(self, api, **kwargs):
        return lifecycle.launch_owned(['C:/Space Ω/python.exe', '-I', 'hello "world"'],
                                      job_handle=99, stdout=io.StringIO(), stderr=io.StringIO(),
                                      _api=api, **kwargs)

    def test_creation_assignment_and_identity_precede_single_resume(self):
        api = FakeAPI()
        process = self.launch(api)
        names = [e[0] for e in api.events]
        self.assertLess(names.index('attributes'), names.index('create'))
        self.assertLess(names.index('identity'), names.index('resume'))
        self.assertEqual(names.count('resume'), 1)
        self.assertEqual(api.events[names.index('attributes')], ('attributes', 99, (1, 3, 4)))
        self.assertEqual(api.open, {2, 10})
        self.assertEqual(api.inheritable, set())
        self.assertFalse(any(e[0] == 'write' for e in api.events))
        self.assertEqual(process.process_handle, 10)
        self.assertEqual(process.pid, 42)
        process.kill()
        self.assertEqual(process.wait(), 7)
        process.close()
        self.assertEqual(api.open, set())
        self.assertFalse(any(e == ('close', 99) for e in api.events))

    def test_exact_environment_and_unicode_command(self):
        api = FakeAPI()
        process = self.launch(api, cwd='C:/資料 Folder', env={'z': 'Ω', 'A': 'two words'})
        event = next(e for e in api.events if e[0] == 'create')
        self.assertEqual(event[1], 'C:/Space Ω/python.exe')
        self.assertEqual(event[2], subprocess.list2cmdline(process.args))
        self.assertEqual(event[3:5], ('C:/資料 Folder', 'A=two words\0z=Ω\0\0'))
        process.close()

    def test_inherited_environment_is_none_and_empty_mapping_is_double_null(self):
        self.assertIsNone(lifecycle._launch_strings(['p'], None, None)[2])
        self.assertEqual(lifecycle._launch_strings(['p'], None, {})[2], '\0\0')

    def test_invalid_inputs_rejected_before_api(self):
        for argv, cwd, env in [([], None, None), (['a\0'], None, None),
                               (['p', 3], None, None), (['p'], 'x\0', None),
                               (['p'], None, {'PATH': '1', 'path': '2'}),
                               (['p'], None, {'a=b': '1'}), (['p'], None, {'x': '\0'}),
                               (['p', 'Ω' * 32768], None, None)]:
            with self.subTest(argv=str(argv)[:30], env=env), self.assertRaises(ValueError):
                lifecycle._launch_strings(argv, cwd, env)

    def test_precreation_failures_release_all_obtained_resources(self):
        for failure in ['require_noninheritable', 'pipe', ('inherit', 1, True),
                        ('duplicate_file', 1), ('duplicate_file', 2), 'attributes', 'create']:
            with self.subTest(failure=failure):
                api = FakeAPI(failure)
                with self.assertRaises(OSError):
                    self.launch(api)
                self.assertEqual(api.open, set())
                self.assertEqual(api.inheritable, set())
                self.assertFalse(any(e[0] in ('resume', 'terminate_process') for e in api.events))

    def test_identity_and_resume_failure_collect_exact_handles(self):
        for failure in ('identity', 'resume'):
            with self.subTest(failure=failure):
                api = FakeAPI(failure)
                with self.assertRaisesRegex(OSError, failure):
                    self.launch(api)
                self.assertIn(('terminate_process', 10), api.events)
                self.assertIn(('terminate_job', 99), api.events)
                self.assertIn(('wait', 10, 10000), api.events)
                self.assertEqual(api.open, set())

    def test_wrong_suspend_counts_are_rejected_and_collected(self):
        for count in (0, 2, 0xFFFFFFFF):
            api = FakeAPI()
            api.suspend_count = count
            with self.assertRaisesRegex(RuntimeError, 'SUSPEND_COUNT'):
                self.launch(api)
            self.assertEqual(api.open, set())

    def test_cleanup_attempts_independent_and_primary_retained(self):
        api = FakeAPI('identity')
        for method in ('terminate_process', 'terminate_job', 'wait', 'delete_attributes'):
            # Attribute deletion is already complete before identity; other stages fail.
            if method != 'delete_attributes':
                setattr(api, method, Mock(side_effect=OSError(method)))
        with self.assertRaisesRegex(OSError, 'identity') as caught:
            self.launch(api)
        self.assertEqual([x[0] for x in caught.exception.cleanup_errors],
                         ['terminate_created_process', 'terminate_owned_job', 'collect_created_process'])
        self.assertEqual(api.open, set())

    def test_inheritable_close_failure_clears_flag_and_fails_current_launch(self):
        api = FakeAPI(('close', 3))
        with self.assertRaisesRegex(RuntimeError, 'RESOURCE_CLEANUP'):
            self.launch(api)
        self.assertIn(('inherit', 3, False), api.events)
        self.assertFalse(lifecycle._TAINTED)
        self.assertEqual(api.inheritable, set())
        self.assertEqual(api.open, {3})  # Retained noninheritable leaked handle is a failure.
        self.assertNotIn(('resume', 11), api.events)

    def test_failed_close_and_deinherit_taint_all_future_cooperating_launches(self):
        api = FakeAPI(('close', 3))
        original = api.inherit
        def inherit(handle, value):
            if handle == 3 and not value:
                raise OSError('cannot disable')
            original(handle, value)
        api.inherit = inherit
        with self.assertRaises(RuntimeError):
            self.launch(api)
        self.assertTrue(lifecycle._TAINTED)
        other = FakeAPI()
        with self.assertRaisesRegex(RuntimeError, 'TAINTED'):
            self.launch(other)
        self.assertEqual(other.events, [])

    def test_primary_thread_close_failure_still_terminates_and_closes_process(self):
        api = FakeAPI(('close', 11))
        with self.assertRaises(OSError):
            self.launch(api)
        self.assertIn(('terminate_job', 99), api.events)
        self.assertEqual(api.open, {11})

    def test_attribute_deletion_failure_does_not_bypass_handle_cleanup(self):
        api = FakeAPI('delete_attributes')
        with self.assertRaises(OSError):
            self.launch(api)
        self.assertEqual(api.open, {'attributes'})
        self.assertIn(('terminate_job', 99), api.events)

    def test_text_start_cancel_and_eof(self):
        api = FakeAPI()
        process = self.launch(api)
        self.assertEqual(process.stdin.write('start\n'), 6)
        process.stdin.flush()
        process.stdin.write('cancel\n')
        process.stdin.close()
        process.stdin.close()
        self.assertTrue(process.stdin.closed)
        self.assertEqual([e[2] for e in api.events if e[0] == 'write'], [b'start\n', b'cancel\n'])
        with self.assertRaises(ValueError):
            process.stdin.write('start\n')
        process.close()

    def test_partial_and_failed_control_writes(self):
        api = FakeAPI()
        process = self.launch(api)
        api.write = Mock(side_effect=[2, 4])
        self.assertEqual(process.stdin.write('start\n'), 6)
        self.assertEqual(api.write.call_args_list[1].args, (2, b'art\n'))
        api.write = Mock(return_value=0)
        with self.assertRaises(OSError):
            process.stdin.write('x')
        api.write = Mock(side_effect=BrokenPipeError('closed'))
        with self.assertRaises(BrokenPipeError):
            process.stdin.write('x')
        process.close()

    def test_poll_wait_exit259_is_terminal_when_handle_signaled(self):
        api = FakeAPI()
        process = self.launch(api)
        self.assertIsNone(process.poll())
        with self.assertRaises(subprocess.TimeoutExpired):
            process.wait(.001)
        api.terminal, api.code = True, 259
        self.assertEqual(process.poll(), 259)
        process.close()
        self.assertEqual(process.wait(1), 259)
        self.assertEqual(process.poll(), 259)
        with self.assertRaises(ValueError):
            _ = process.process_handle
        process.close()

    def test_query_failure_is_not_terminal_exit(self):
        api = FakeAPI()
        process = self.launch(api)
        api.fail = 'wait'
        with self.assertRaises(OSError):
            process.poll()
        self.assertIsNone(process.returncode)
        api.fail, api.terminal = 'exit_code', True
        with self.assertRaises(OSError):
            process.wait(1)
        self.assertIsNone(process.returncode)
        process.close()

    def test_kill_only_exact_held_launcher_and_noop_after_terminal(self):
        api = FakeAPI()
        process = self.launch(api)
        process.kill()
        process.kill()
        self.assertEqual(api.events.count(('terminate_process', 10)), 1)
        self.assertFalse(any(e[0] == 'terminate_job' for e in api.events))
        process.close()

    def test_close_attempts_both_resources_and_can_retry(self):
        api = FakeAPI()
        process = self.launch(api)
        api.fail = ('close', 2)
        with self.assertRaises(RuntimeError):
            process.close()
        self.assertIn(('close', 10), api.events)
        self.assertEqual(api.open, {2})
        api.fail = None
        process.close()
        self.assertEqual(api.open, set())
        with self.assertRaises(ValueError):
            process.poll()

    def test_wait_requires_finite_bounded_timeout(self):
        for value in (None, True, -1, float('nan'), float('inf'), 4294968):
            with self.assertRaises(ValueError):
                lifecycle._milliseconds(value)
        self.assertEqual(lifecycle._milliseconds(.0001), 1)

    def test_noncanonical_module_rejected(self):
        with patch.object(lifecycle, '__name__', 'alternate_windows_lifecycle'):
            with self.assertRaisesRegex(RuntimeError, 'NONCANONICAL'):
                self.launch(FakeAPI())

    def test_failure_cleanup_keeps_lock_until_inheritable_handles_resolved(self):
        failed_create, release_cleanup, second_entered = threading.Event(), threading.Event(), threading.Event()
        first, second = FakeAPI('create'), FakeAPI()
        real_close, real_pipe = first.close, second.pipe
        def close(handle):
            if handle == 1:
                failed_create.set()
                if not release_cleanup.wait(2):
                    raise TimeoutError('test cleanup synchronization')
            real_close(handle)
        def pipe():
            second_entered.set()
            self.assertEqual(first.inheritable, set())
            return real_pipe()
        first.close, second.pipe = close, pipe
        errors, results = [], []
        def run(api):
            try:
                results.append(self.launch(api))
            except BaseException as error:
                errors.append(error)
        a, b = threading.Thread(target=run, args=(first,)), threading.Thread(target=run, args=(second,))
        a.start()
        self.assertTrue(failed_create.wait(2))
        b.start()
        self.assertFalse(second_entered.wait(.05))
        release_cleanup.set()
        a.join(2); b.join(2)
        self.assertFalse(a.is_alive() or b.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], OSError)
        self.assertTrue(second_entered.is_set())
        for process in results:
            process.close()

    def test_cooperating_launch_cannot_overlap_inheritable_lifetime(self):
        entered, release, second_entered = threading.Event(), threading.Event(), threading.Event()
        first, second = FakeAPI(), FakeAPI()
        original = first.create
        def create(*args):
            entered.set()
            if not release.wait(2):
                raise TimeoutError('test synchronization')
            return original(*args)
        first.create = create
        second.pipe = Mock(wraps=second.pipe, side_effect=lambda: (second_entered.set(), FakeAPI.pipe(second))[1])
        results, errors = [], []
        def run(api):
            try:
                results.append(self.launch(api))
            except BaseException as error:
                errors.append(error)
        a, b = threading.Thread(target=run, args=(first,)), threading.Thread(target=run, args=(second,))
        a.start()
        self.assertTrue(entered.wait(2))
        b.start()
        self.assertFalse(second_entered.wait(.05))
        release.set()
        a.join(2); b.join(2)
        self.assertFalse(a.is_alive() or b.is_alive())
        self.assertFalse(errors)
        self.assertTrue(second_entered.is_set())
        for process in results:
            process.close()


class NativeLayoutTests(unittest.TestCase):
    """Only ctypes data and injected function objects; never load a native DLL."""
    def test_windows_64_bit_structure_sizes_and_offsets(self):
        self.assertEqual(ctypes.sizeof(lifecycle._StartupInfo), 104)
        self.assertEqual(ctypes.sizeof(lifecycle._StartupInfoEx), 112)
        self.assertEqual(ctypes.sizeof(lifecycle._ProcessInformation), 24)
        self.assertEqual(lifecycle._StartupInfo.stdin.offset, 80)
        self.assertEqual(lifecycle._StartupInfoEx.attributes.offset, 104)

    def test_create_uses_real_extended_attributes_and_exact_flags(self):
        api = lifecycle._NativeAPI.__new__(lifecycle._NativeAPI)
        observed = {}
        def create(exe, command, pa, ta, inherit, flags, env, cwd, startup, process):
            observed.update(exe=exe, command=command.value, pa=pa, ta=ta, inherit=inherit,
                            flags=flags, env=env[:8], cwd=cwd)
            structure = startup._obj
            observed.update(cb=structure.startup.cb, attributes=structure.attributes,
                            handles=(structure.startup.stdin, structure.startup.stdout, structure.startup.stderr))
            process._obj.process, process._obj.thread, process._obj.pid = 10, 11, 42
            return True
        api.api = Mock(CreateProcessW=create)
        storage = ctypes.create_string_buffer(32)
        self.assertEqual(api.create('p.exe', 'p.exe "x y"', 'C:/Ω', 'a=b\0\0',
                                    (storage,), [1, 3, 4]), (10, 11, 42))
        self.assertEqual(observed['handles'], (1, 3, 4))
        self.assertEqual(observed['cb'], 112)
        self.assertEqual(observed['attributes'], ctypes.addressof(storage))
        self.assertEqual(observed['flags'], 0x8080404)
        self.assertIs(observed['inherit'], True)
        self.assertIsNone(observed['pa'])
        self.assertIsNone(observed['ta'])
        self.assertEqual(observed['command'], 'p.exe "x y"')

    def test_attribute_buffers_kept_alive_and_partial_failure_deleted(self):
        api = lifecycle._NativeAPI.__new__(lifecycle._NativeAPI)
        updates, deleted = [], []
        def initialize(storage, count, flags, size):
            self.assertEqual(count, 2)
            if storage is None:
                size._obj.value = 128
                return False
            return True
        def update(storage, flags, key, values, size, previous, returned):
            updates.append((key, tuple(values), size))
            return True
        api.api = Mock(InitializeProcThreadAttributeList=initialize, UpdateProcThreadAttribute=update,
                       DeleteProcThreadAttributeList=lambda storage: deleted.append(storage))
        with patch.object(ctypes, 'set_last_error'), patch.object(ctypes, 'get_last_error', return_value=122):
            attrs = api.attributes(99, [1, 3, 4])
        self.assertEqual(updates, [(0x2000D, (99,), 8), (0x20002, (1, 3, 4), 24)])
        api.delete_attributes(attrs)
        self.assertEqual(len(deleted), 1)
        api.api.UpdateProcThreadAttribute = Mock(side_effect=OSError('unsupported job list'))
        with patch.object(ctypes, 'set_last_error'), patch.object(ctypes, 'get_last_error', return_value=122):
            with self.assertRaises(OSError):
                api.attributes(99, [1, 3, 4])
        self.assertEqual(len(deleted), 2)

    def test_native_wait_and_resume_error_values_are_not_success(self):
        api = lifecycle._NativeAPI.__new__(lifecycle._NativeAPI)
        api.api = Mock()
        api.api.WaitForSingleObject.return_value = 0
        self.assertTrue(api.wait(10, 0))
        api.api.WaitForSingleObject.return_value = 258
        self.assertFalse(api.wait(10, 0))
        api.api.WaitForSingleObject.return_value = 17
        with self.assertRaisesRegex(OSError, 'UNEXPECTED_PROCESS_WAIT'):
            api.wait(10, 0)
        api.api.WaitForSingleObject.return_value = 0xFFFFFFFF
        api.api.ResumeThread.return_value = 0xFFFFFFFF
        with patch.object(ctypes, 'get_last_error', return_value=5), \
                patch.object(ctypes, 'WinError', return_value=OSError('injected error 5')):
            with self.assertRaisesRegex(OSError, 'error 5'):
                api.wait(10, 0)
            with self.assertRaisesRegex(OSError, 'error 5'):
                api.resume(11)

    def test_held_identity_uses_live_image_creation_and_specific_job(self):
        api = lifecycle._NativeAPI.__new__(lifecycle._NativeAPI)
        def times(handle, creation, exit_time, kernel, user):
            creation._obj.dwLowDateTime = 1234
            return True
        def image(handle, flags, buffer, size):
            buffer.value = 'C:/Profile Ω/python.exe'
            return True
        def member(process, job, result):
            self.assertEqual((process, job), (10, 99))
            result._obj.value = True
            return True
        api.api = Mock(GetProcessTimes=times, QueryFullProcessImageNameW=image, IsProcessInJob=member)
        api.api.WaitForSingleObject.return_value = 258
        api.api.GetProcessId.return_value = 42
        result = api.identity(10, 99, 42)
        self.assertEqual(result['creation_filetime'], 1234)
        self.assertEqual(result['image'], 'C:/Profile Ω/python.exe')
        self.assertTrue(result['specific_job_member'])
        self.assertEqual(api.api.WaitForSingleObject.call_count, 2)
        api.api.GetProcessId.return_value = 43
        with self.assertRaisesRegex(RuntimeError, 'ID_MISMATCH'):
            api.identity(10, 99, 42)
        api.api.GetProcessId.return_value = 42
        def absent(process, job, result):
            result._obj.value = False
            return True
        api.api.IsProcessInJob = absent
        with self.assertRaisesRegex(RuntimeError, 'UNCONFIRMED'):
            api.identity(10, 99, 42)
        api.api.WaitForSingleObject.return_value = 0
        with self.assertRaisesRegex(RuntimeError, 'ALREADY_EXITED'):
            api.identity(10, 99, 42)

    def test_native_bindings_are_pointer_sized_and_lazy(self):
        dll = Mock()
        with patch.object(ctypes, 'WinDLL', return_value=dll) as load:
            api = lifecycle._NativeAPI()
        load.assert_called_once_with('kernel32', use_last_error=True)
        self.assertIs(api.api, dll)
        self.assertEqual(dll.CreateProcessW.argtypes[-1], ctypes.POINTER(lifecycle._ProcessInformation))
        self.assertIs(dll.UpdateProcThreadAttribute.argtypes[2], ctypes.c_size_t)
        self.assertEqual(ctypes.sizeof(dll.GetCurrentProcess.restype), 8)
        for call in dll.method_calls:
            self.fail('Binding must not invoke native functions: ' + str(call))


if __name__ == '__main__':
    unittest.main(verbosity=2)
