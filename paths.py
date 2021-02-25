"""Contains simple and base Path classes to be extended.

The Path class represents the common attributes and methods to represent a path in the browser,
whether it is an actual filesystem path or an abstract or virtual one. This can be a directory,
a file, or something else. Generally, subpaths/child paths will also be Paths or subclasses,
but this does not need to be the case, if the subclass handles such operations internally.

When implementing additional file handlers or backends, only import third party modules locally
when immediately needed, if possible. This allows the rest of the program to run properly despite
having missing dependencies. It is recommended to find a way to not crash (or at least exit
cleanly) if a dependency is missing, but it's not required.
"""
from __future__ import annotations

import os
import warnings
from collections.abc import MutableMapping, Sequence
from typing import Union, Optional, IO

from errors import IncorrectFileTypeWarning, NonexistentMappingError, UnexpectedSituationWarning

class Path:
    """Represents the common attributes and methods to represent a path in the browser.

    A path may not necessarily have children or data assigned to it, but it holds a reference to a
    parent object, which may be None.

    This class is meant to be extended by its subclasses, and should not be used on its own.
    """

    def __init__(self, name: str, parent: Optional[DirPath] = None, backend: str = 'fs',
                 path_type: str = 'text', context: Optional[list] = None) -> None:
        """Initializes a new Path object.

        :param name: the name of the new Path object. If a full path is specified, this will take the basename.
        :param parent: the parent of the new Path object, if any.
        :param backend: the backend implementing this Path, for example, the filesystem, or a
                        virtual file handler class.
        :param path_type: the type path the new object will represent.
        """
        self.name = os.path.basename(name)
        self.parent = parent
        self.backend = backend
        self.path_type = path_type
        self.path = None if self.name == name else os.path.abspath(name)
        self.path = self.get_path()
        self.context = context
        self.set_context(context)

    def set_name(self, name: str) -> None:
        self.name = name

    def set_parent(self, parent: DirPath):
        self.parent = parent

    def set_type(self, path_type: str) -> None:
        self.path_type = path_type

    def set_context(self, context: Optional[list] = None) -> None:
        if context is None and self.context is None:
            if self.parent is not None:
                self.context = self.parent.context
        elif self.context is None:
            self.context = context
        else:
            self.context[0] = context[0]

    def get_name(self) -> str:
        return self.name

    def get_parent(self) -> DirPath:
        return self.parent

    def get_backend(self) -> str:
        return self.backend

    def get_type(self) -> str:
        return self.path_type

    def get_context(self):
        if self.context is None:
            return self.context
        else:
            return self.context[0]

    def get_path(self) -> str:
        if self.path is not None:
            # If we have the value already, just return that
            return self.path
        elif self.parent is None and self.backend == 'fs':
            # This is the start node
            return os.path.abspath(self.name)
        elif self.parent is None:
            # This should theoretically never happen
            warnings.warn(UnexpectedSituationWarning(
                'get_path() was called on a non-filesystem backed Path with no parent'))
            return self.name
        else:
            # Generate path from parent's path
            return os.path.join(self.parent.get_path(), self.name)

    def absorb(self, other: Path) -> None:
        self.name = other.get_name()
        self.parent = other.get_parent()
        self.backend = other.get_path()
        self.path_type = other.get_type()

    def __eq__(self, other: Path) -> bool:
        return all([
            type(self) is type(other),
            self.get_name() == other.get_name(),
            self.get_parent() == other.get_parent(),
            self.get_backend() == other.get_backend(),
            self.get_type() == other.get_type()
        ])


class DirPath(Path, MutableMapping):
    """Represents the common attributes and methods to represent a directory in the browser.

    This class is meant to be extended by its subclasses, but can also be used by itself.
    """

    def __init__(self, name: str, parent: Optional[DirPath] = None, backend: str = 'fs', path_type: str = 'dir',
                 children: Union[list[Path], dict[str, Path], Path, None] = None, context=None) -> None:
        """Initializes a new DirPath object, optionally adding child Paths.

        :param name: inherited from Path
        :param parent: inherited from Path
        :param backend: inherited from Path
        :param path_type: inherited from Path
        :param children: a list or dict of Paths or a single Path object to be added to the new
                         object. This is used for initializing a new directory as a parent of an
                         existing one. In this case, the known existing path should always come
                         first.
        :param context: a context object, usually the active Terminal. This is usually only
                        provided to the starting node.
        """
        if children is None:
            self.children = {}
        elif type(children) is list:
            self.children = {}
            for item in children:
                self.children[item.get_name()] = item
        elif type(children) is dict:
            self.children = children
        else:
            self.children = {children.get_name(): children}
        super().__init__(name=name, parent=parent, backend=backend, path_type=path_type, context=context)
        if self.name == '..' and self.children:
            self.name = os.path.basename(self.get_path())

    def set_context(self, context: Optional[list] = None) -> None:
        if context is None and self.context is None:
            if self.parent is not None:
                self.context = self.parent.context
            elif self.children:
                self.context = list(self.values())[0].context
        elif self.context is None:
            self.context = context
        else:
            self.context[0] = context[0]

    def get_path(self) -> str:
        if self.path is not None:
            # If we have the value already, just return that
            return self.path
        elif self.parent is None and not self.children:
            # This is the start node
            return os.path.abspath(self.name)
        elif self.parent is not None:
            # Generate path from parent's path
            return os.path.join(self.parent.get_path(), self.name)
        else:
            # Generate path from first child Path
            return os.path.dirname(list(self.values())[0].get_path())

    def get_children(self) -> dict:
        return self.children

    def absorb(self, other: DirPath) -> None:
        super().absorb(other)
        self.children = other.get_children()

    def __eq__(self, other: DirPath) -> bool:
        return all([
            super().__eq__(other),
            self.children == other.get_children()
        ])

    def all(self) -> dict:
        """Returns a dict containing all references including child, self, and parent.

        :return: a dict containing all children, plus self and parent
        """
        to_return = self.children.copy()
        to_return.update({'.': self, '..': self.get_parent()})
        return to_return

    # ABC Mapping method implementations
    def __getitem__(self, key: str) -> Path:
        if key == '.':
            return self
        elif key == '..':
            return self.get_parent()
        else:
            return self.children[key]

    def __setitem__(self, key: str, value: Path) -> None:
        if key == '.':
            self.absorb(value)
        elif key == '..':
            self.set_parent(value)
        else:
            self.children[key] = value

    def __delitem__(self, key: str) -> None:
        del self.children[key]

    def __iter__(self) -> dict.keys:
        return iter(self.children)

    def __len__(self) -> int:
        return len(self.children)

    # Additional Mapping method overrides to prevent '.' and '..' from causing problems
    def __contains__(self, item: Path) -> bool:
        return item in self.children


class FilePath(Path):
    """Represents the common attributes and methods to represent a file in the browser.

    This class does not contain any implementations of a file-like object, as not all of this
    class' subclasses may be read that way. Instead, it simply holds an open() method which should
    be overridden by subclasses.

    This class should not be used by itself, instead, use TextFile or BinaryFile.
    """

    def open(self) -> None:
        """Opens the file this FilePath represents and prints its contents.

        This method will work fine on its own, but should be overridden.
        """
        with open(self.get_path()) as f:
            print(f.read())


class TextFile(FilePath):
    """Represents a generic text mode file in the browser.

    This class is essentially a wrapper for a base python file object in text mode. It provides a
    context manager, as well as the methods and attributes associated with its parent classes.
    To use the context manager, this class must have a filesystem ('fs') backend. In addition, the
    set_type() method does nothing, as this class and its subclasses should be of fixed type.

    This class can be extended by its subclasses, but should also function just fine on its own.
    """

    def __init__(self, name: str, parent: Optional[DirPath] = None, backend: str = 'fs',
                 path_type: str = 'text') -> None:
        """Initializes a new TextFile object.

        :param name: inherited from Path
        :param parent: inherited from Path
        :param backend: inherited from Path
        :param path_type: only included for continuity with other Path objects, this is ignored.
                          This type can only represent a text file.
        """
        super().__init__(name=name, parent=parent, backend=backend, path_type='text')

    def set_type(self, path_type: str) -> None:
        """Overrides Path.set_type(), does nothing. This type can only represent a text file."""
        pass

    def open(self) -> None:
        if self.backend == 'fs':
            with self.c_open() as f:
                print(f.read())
        else:
            print(self.get_parent().v_open(self.get_name(), temp=False, text=True).read())

    def c_open(self, mode: str = 'r') -> PathContextManager:
        if self.backend == 'fs':
            if 'b' in mode:
                warnings.warn(IncorrectFileTypeWarning(
                    'Binary mode access of a text mode file is not allowed. Correcting.'))
            mode = mode.replace('b', '')
            return PathContextManager(self.get_path(), mode)
        else:
            return PathContextManager(self.get_parent().v_open(self.get_name(), temp=False, text=True).read())


class BinaryFile(FilePath):
    """Represents a generic binary mode file in the browser.

    This class is essentially a wrapper for a base python file object in binary mode. It provides a
    context manager, as well as the methods and attributes associated with its parent classes.
    To use the context manager, this class must have a filesystem ('fs') backend. In addition, the
    set_type() method does nothing, as this class and its subclasses should be of fixed type.

    This class can be extended by its subclasses, but should also function just fine on its own.
    """

    def __init__(self, name: str, parent: Optional[DirPath] = None, backend: str = 'fs',
                 path_type: str = 'binary') -> None:
        """Initializes a new BinaryFile object.

        :param name: inherited from Path
        :param parent: inherited from Path
        :param backend: inherited from Path
        :param path_type: only included for continuity with other Path objects, this is ignored.
                          This type can only represent a binary file.
        """
        super().__init__(name=name, parent=parent, backend=backend, path_type='binary')

    def set_type(self, path_type: str) -> None:
        """Overrides Path.set_type(), does nothing. This type can only represent a binary file."""
        pass

    def open(self) -> None:
        if self.backend == 'fs':
            with self.c_open() as f:
                print(f.read())
        else:
            print(self.get_parent().v_open(self.get_name(), temp=False, text=False).read())

    def c_open(self, mode: str = 'r') -> PathContextManager:
        """Handles using this BinaryFile as a context manager.

        :param mode: the mode to open the file in. Forces binary mode.
        :return: a PathContextManager object representing the file.
        """
        if self.backend == 'fs':
            if 'b' not in mode:
                mode += 'b'
            return PathContextManager(self.get_path(), mode)
        else:
            return PathContextManager(self.get_parent().v_open(self.get_name(), temp=False, text=False))


class PathContextManager:
    """This is a context manager which should only be constructed and managed by FilePath objects."""
    def __init__(self, path, mode='r'):
        self.path = path
        self.mode = mode

    def __enter__(self):
        if type(self.path) is str:
            self.file = open(self.path, self.mode)
            return self.file
        else:
            return self.path

    def __exit__(self, exc_type, exc_val, exc_tb):
        if type(self.path) is str:
            if self.file:
                self.file.close()
        else:
            self.path.seek(0)


class VirtualDirPath(DirPath):
    """Tha base class for a virtual directory.

    Unlike its parent, this class does not support being initialized above a known one. All virtual
    paths should be navigated down to (or possibly adjacently to in a future implementation.
    Either way it doesn't matter, the children constructor argument is still not present.)

    For virtual paths, the backend is essentially responsible for anything that would normally be
    done through the filesystem. This can be either an implementation of the action, or raising an
    UnsupportedOperationWarning with an error message describing exactly what the action that can't
    be done is, and then finding a way to continue without crashing (for example, returning an
    empty or unmodified string when asked for a path, or providing an empty or blank file object
    when asked to open a file.)

    This class should not be used on its own, it should instead be subclassed.
    """
    def __init__(self, name: str, parent: DirPath, backend: str = 'virtual', path_type: str = 'virtual') -> None:
        """Initializes a new VirtualDirPath object.

        :param name: inherited from Path
        :param parent: inherited from Path, however, this is no longer optional, as a
                       VirtualDirPath object must always be the descendant of a DirPath with a
                       filesystem backend.
        :param backend: inherited from Path
        :param path_type: inherited from Path
        """
        self.children = {}
        Path.__init__(self, name=name, parent=parent, backend=backend, path_type=path_type)

    def find_children(self) -> None:
        """This method should fill in the children of the virtual directory when called.

        This method will be called on virtual directories in order to fill in the directory's
        children. This should return nothing, but find and register child Path objects in this
        object's self.children dict parameter.

        This method is a boilerplate and must be overridden by subclasses.
        """
        pass

    def v_open(self, path: str, temp: bool = False, text: bool = False) -> Union[str, IO]:
        """This method should open a child Path and return accessors.

        This method will be called by child FilePath objects in order to access the file they
        represent. If temp is True, this should return the path of the newly made tempfile.
        Otherwise, this should return an IO/Stream object containing the data of the requested
        path. The text parameter should determine the file mode: True for text, False for binary.
        The implementer is also responsible for queueing the tempfile for cleanup, if one is made.

        This method is a boilerplate and must be overridden by subclasses.
        :param path: the path to open.
        :param temp: True if the file should be opened as a tempfile, False for an IO/stream
                     object.
        :param text: True if the file should be opened in text mode, False for binary mode. If temp
                     is True, this should dictate how the data is read into the tempfile, if
                     possible. Otherwise, it should dictate what kind of IO/stream object is
                     returned.
        """
        pass
