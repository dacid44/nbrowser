from __future__ import annotations

import os
import random
import warnings
from typing import Callable

import paths
from errors import UnexpectedSituationWarning

class CommandClass:
    @classmethod
    def get_commands(cls) -> dict[str, Callable]:
        """Returns a dict of command functions and their names.

        This method should return a dict where the values are functions. Each function should take
        two arguments: a context argument, to which the current Terminal object will be passed, and
        a a list of strings, usually called args. All such functions should return None.

        When this class is passed to the Terminal object to initialize commands, it will call this
        method in order to access the class's functions.

        This method should be overridden, as it is a boilerplate and only returns an empty dict.
        """
        return {}

class BaseCommands(CommandClass):
    @classmethod
    def get_commands(cls) -> dict[str, Callable]:
        return {
            'ls': cls.ls,
            'cd': cls.cd,
            'pwd': cls.pwd,
            'open': cls.open,
            'ropen': cls.ropen,
            'type': cls.type,
            'echo': cls.echo,
            'recho': cls.recho,
        }

    @staticmethod
    def get_path_colors(path):
        import basic_file_paths
        import archive_paths
        to_return = ''
        if isinstance(path, archive_paths.ArchivePath) and path.get_is_anchor():
            to_return += '\x1b[31;1m'
        elif isinstance(path, paths.DirPath):
            to_return += '\x1b[34;1m'
        elif path.get_type() == 'image':
            to_return += '\x1b[35m'
        elif path.get_type() == 'pdf':
            to_return += '\x1b[33m'
        elif path.get_type() == 'video':
            to_return += '\x1b[35;1m'
        elif path.get_type() == 'generic':
            to_return += '\x1b[33;1m'
        return to_return

    @classmethod
    def ls(cls, context, args: list[str]) -> None:
        """Lists the contents of the current directory."""
        contents = list(context.current.keys())
        strs = []
        for item in contents:
            strs.append(f"'{item}'" if ' ' in item else item)
        if context.options['color']:
            for i in range(len(strs)):
                code = cls.get_path_colors(context.current[contents[i]])
                if code:
                    strs[i] = code + strs[i] + '\x1b[0m'
            from prompt_toolkit import print_formatted_text, ANSI
            print_formatted_text(ANSI(' '.join(strs)))
        else:
            print(' '.join(strs))

    @staticmethod
    def cd(context, args: list[str]) -> None:
        """Moves into the specified directory.

        If a directory is not specified, this will move into the directory where the browser
        program was started from.
        """
        name = ' '.join(args)
        if not name:
            context.current = context.start
        elif name in context.current:
            if isinstance(context.current[name], paths.DirPath):
                context.current = context.current[name]
                context.add_all_children()
            else:
                context.error('The given path is not a directory.')
        elif name == '.':
            pass
        elif name == '..':
            if context.current.get_path() != os.path.dirname(context.current.get_path()):
                if context.current.parent is None:
                    context.add_path(name='..', parent=True)
                    context.current = context.current.parent
                    context.add_all_children()
                else:
                    context.current = context.current.parent
            else:
                context.error('You are at the filesystem root.')
        else:
            context.error('The given path was not found.')

    @staticmethod
    def pwd(context, args):
        """Prints the path of the current directory."""
        print(context.current.get_path())

    @classmethod
    def open(cls, context, args):
        name = ' '.join(args)
        if name in context.current:
            if isinstance(context.current[name], paths.DirPath):
                cls.cd(context, args)
            elif isinstance(context.current[name], paths.FilePath):
                context.current[name].open()
            else:
                warnings.warn(UnexpectedSituationWarning(
                    'The open() command was called on a Path that was not a FilePath or a DirPath.'))
        else:
            context.error('The given path was not found.')

    @classmethod
    def ropen(cls, context, args):
        choice = random.choice(list(context.current))
        print(f'Opening {choice}...')
        cls.open(context, [choice])

    @staticmethod
    def type(context, args):
        name = ' '.join(args)
        if name in context.current.all():
            print(type(context.current[name]), context.current[name].get_type())
        else:
            context.error('The given path was not found.')

    @staticmethod
    def echo(context, args):
        print(' '.join(args))

    @classmethod
    def recho(cls, context, args):
        cls.echo(context, [repr(' '.join(args))])
