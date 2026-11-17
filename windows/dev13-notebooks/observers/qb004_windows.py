"""Authored Windows command compatibility, separately labelled from source cells."""
import json as _qb004_json
from pathlib import Path as _qb004_Path
import subprocess as _qb004_subprocess
import sys as _qb004_sys


class _QB004Windows:
    def __init__(self, shell):
        self.shell = shell
        self.original_system = shell.system
        aliases = shell.alias_manager
        self.old_cat = aliases.retrieve_alias('cat') if aliases.is_alias('cat') else None
        self.commands = []
        self.restored = False
        shell.system = self.system
        aliases.define_alias('cat', 'type')

    def system(self, command):
        expected = f'"{_qb004_sys.executable}" -m pip install \'qbraid[visualization]\' qbraid-algorithms'
        translated = command == expected
        actual = _qb004_subprocess.list2cmdline([
            _qb004_sys.executable, '-m', 'pip', 'install',
            'qbraid[visualization]', 'qbraid-algorithms']) if translated else command
        try:
            self.original_system(actual)
        finally:
            self.commands.append(dict(original=command, actual=actual, translated=translated,
                                      exit_code=self.shell.user_ns.get('_exit_code')))
            self.save()

    def save(self):
        _qb004_Path('qb004-compatibility.json').write_text(_qb004_json.dumps(dict(
            commands=self.commands, cat_alias='type', restored=self.restored,
            scope='Authored Windows pip quoting and cat alias; SDK methods unchanged'), indent=2),
            encoding='utf-8')

    def restore(self):
        self.shell.system = self.original_system
        aliases = self.shell.alias_manager
        aliases.undefine_alias('cat')
        if self.old_cat is not None:
            aliases.define_alias('cat', self.old_cat)
        self.restored = self.shell.system is self.original_system and (
            aliases.retrieve_alias('cat') == self.old_cat if self.old_cat is not None
            else not aliases.is_alias('cat'))
        self.save()


_qb004_windows = _QB004Windows(get_ipython())
_qb004_windows.save()
