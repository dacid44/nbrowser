from __future__ import annotations

import os
import argparse
import glob
from getpass import getpass
import warnings
from typing import Union, Callable, Optional, Any

from prompt_toolkit import PromptSession, ANSI
from prompt_toolkit.completion import WordCompleter

import paths
import basic_file_paths
import archive_paths
from commands import *
from errors import UnsupportedOperationWarning


class Terminal:
    def __init__(self, start_path: str,
                 commands: Union[type[CommandClass],
                                 list[Union[type[CommandClass], Callable[[Terminal, list[str]], None]]], None] = None,
                 file_map: Optional[dict] = None, dir_map: Optional[dict] = None,
                 options: Optional[dict] = None) -> None:
        self.options = {
            'color': True,
        }
        if options is not None:
            self.options.update(options)
        self.start = paths.DirPath(name=os.path.abspath(start_path), context=[self])
        self.current = self.start
        self.file_map = {
            'text': [paths.TextFile, ['.txt']],
            'binary': [paths.BinaryFile, ['.bin']],
        }
        if file_map is not None:
            self.file_map.update(file_map)
        self.dir_map = {
            'dir': [paths.DirPath, ['']],
        }
        if dir_map is not None:
            self.dir_map.update(dir_map)
        self.add_all_children()
        self.commands = {}
        self.initialize_command_class(BaseCommands)
        if isinstance(commands, type):
            self.initialize_command_class(commands)
        elif commands is not None:
            for item in commands:
                if isinstance(item, type):
                    self.initialize_command_class(item)
                else:
                    self.commands[item.__name__] = item
        self.running = None
        self.session = None
        self.tempfiles = []

    def set_current(self, path: str) -> None:
        self.current = path

    def get_current(self) -> paths.DirPath:
        return self.current

    def get_start(self) -> paths.DirPath:
        return self.start

    def initialize_command_class(self, command_class: type[CommandClass]) -> None:
        self.commands.update(command_class.get_commands())

    def initialize_commands(self, commands) -> None:
        # I'm not f**king writing that type hinting again. It takes a list or a dict of command functions.
        for name in commands:
            self.commands[name] = commands[name]

    def execute_command(self, command_str: str) -> None:
        args = command_str.split()
        if len(args) == 0:
            pass
        elif args[0] not in self.commands.keys():
            self.error('Invalid command.')
        else:
            self.commands[args[0]](self, args[1:])

    def error(self, message: Any) -> None:
        print(message)

    def get_path_type(self, path: str, is_dir: bool = True, default_type: str = 'text',
                      default_dir_type: str = 'dir') -> str:
        path_type = default_dir_type if is_dir else default_type
        mapping = self.dir_map if is_dir else self.file_map
        ext = os.path.splitext(path)[1]
        for cand_type in mapping:
            if ext in mapping[cand_type][1]:
                path_type = cand_type
        return path_type

    def add_path(self, name: str, is_dir: bool = True, path_type: Optional[str] = None, default_type: str = 'text',
                 default_dir_type: str = 'dir', parent: bool = False, backend: str = 'fs',
                 dest: Optional[paths.DirPath] = None, init_kwargs: Optional[dict] = None) -> None:
        """Adds the specified path to the tree as a new Path object.

        :param name: the name of the new Path.
        :param is_dir: whether the new Path is a directory or not.
        :param path_type: if specified, override the automatic type detection.
        :param default_type: the type to default to if the given path is a file and there are no
                             matching extensions defined.
        :param default_dir_type: the type to default to if the given path is a directory and there
                                 are no matching extensions defined.
        :param parent: True if the new Path should be added as a parent of self.current, false otherwise
        :param backend: the backend type for the new Path object.
        :param dest: if specified, add the path to the given path instead of self.current.
        :param init_kwargs: if specified, pass these kwargs to the new Path's constructor.
        """
        if dest is None:
            dest = self.current
        if path_type is None:
            path_type = self.get_path_type(name, is_dir, default_type, default_dir_type)
        if init_kwargs is None:
            init_kwargs = {}
        mapping = self.dir_map if is_dir else self.file_map
        if parent and backend == 'fs':
            dest['..'] = mapping[path_type][0](name=name, backend=backend, children=dest, path_type=path_type,
                                               **init_kwargs)
        elif parent:
            warnings.warn(UnsupportedOperationWarning(
                'Adding parent paths outside of the filesystem is unsupported at this time.'))
        elif backend == 'fs':
            dest[os.path.basename(name)] = mapping[path_type][0](name=name, parent=dest, backend=backend,
                                                                 path_type=path_type, **init_kwargs)
        else:
            dest[os.path.basename(name)] = mapping[path_type][0](name=os.path.basename(name), parent=dest,
                                                                 backend=backend, path_type=path_type, **init_kwargs)

    def add_all_children(self) -> None:
        if self.current.get_backend() == 'fs':
            for path in glob.glob(os.path.join(self.current.get_path(), '*')):
                if os.path.basename(path) not in self.current:
                    self.add_path(name=path, is_dir=os.path.isdir(path))
        else:
            self.current.find_children()

    def password(self, prompt: str) -> str:
        if self.running == 'nb_shell':
            return self.session.prompt(prompt, completer=None, is_password=True)
        else:
            return getpass(prompt)

    def cleanup(self) -> None:
        for file in self.tempfiles:
            os.remove(file)

    def add_tempfile(self, name: str) -> None:
        self.tempfiles.append(name)

    def nb_shell(self) -> None:
        self.session = PromptSession()
        self.running = 'nb_shell'
        while self.running == 'nb_shell':
            try:
                line = self.session.prompt(self.nb_prompt(), completer=self.nb_completer(), is_password=False)
            except KeyboardInterrupt:
                line = '\x1a'
            if line in ['exit', '\x1a']:
                break
            self.execute_command(line)
        self.running = None
        self.cleanup()
        print('Exiting...')

    def nb_prompt(self) -> Union[str, ANSI]:
        prompt = f'<{{}}{self.current.get_type()}{{}}> {self.current.get_name()}$ '
        if self.options['color']:
            if isinstance(self.current, archive_paths.ArchivePath):
                prompt = ANSI(prompt.format('\x1b[31;1m', '\x1b[0m'))
            elif isinstance(self.current, paths.VirtualDirPath):
                prompt = ANSI(prompt.format('\x1b[36;1m', '\x1b[0m'))
            else:
                prompt = ANSI(prompt.format('\x1b[34;1m', '\x1b[0m'))
        else:
            prompt = prompt.format('', '')
        return prompt

    def nb_completer(self):
        options = list(self.commands.keys()) + ['exit'] + list(self.current.keys())
        return WordCompleter(options)


if __name__ == '__main__':
    extra_file_types = {
        'image': [basic_file_paths.ImageFile, ['.jpg', '.png', '.bmp', '.webp']],
        'pdf': [basic_file_paths.GenericFile, ['.pdf']],
        'video': [basic_file_paths.GenericFile, ['.mp4', '.mkv', '.webm', '.gif']],
        'generic': [basic_file_paths.GenericFile, []],
        '7z': [archive_paths.Py7zrArchivePath, ['.7z']],
    }
    extra_dir_types = {
        '7z': [archive_paths.Py7zrArchivePath, ['.7z']]
    }
    term = Terminal('.', file_map=extra_file_types, dir_map=extra_dir_types)
    term.nb_shell()
