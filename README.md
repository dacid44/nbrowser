# nbrowser
A OOP-based command line file browser.

## Files:

#### nbrowser.py

​	Contains the driver methods and implements the shell/CLI interface.

#### errors.py

​	Contains exceptions and errors used by the program.

#### commands.py

​	Contains the commands for the program implemented as functions. `nbrowser.py` will import these to use in the shell environment.

#### paths.py

​	Contains the base classes that are extended or used by other parts of the program, including `Path`, the root class for all path classes, `DirPath` and `FilePath`, the root classes for directories and files, two base implementations of file classes, `TextFile` and `BinaryFile`, and `VirtualDirPath`, the base class for virtual directories.

#### basic_file_paths.py

​	Contains classes implementing some basic file types like images (which are handled using Pillow) and a generic file type, used for situations where the file can be opened simply by calling it as the argument of another program. Also contains a generic type for Termux using Termux:API.

#### archive_paths.py

​	Contains a base class, `ArchivePath`, for implementing archive files as virtual directories, and `Py7zrArchivePath`, an implementation of `ArchivePath` for `.7z` files.

## Description:

​	This is an archive browser program, made using Python. It utilizes classes to represent files and directories, making it easy to implement virtual directories simply by implementing class methods. (Example: implementing virtual directories for archive files like `.7z` and `.zip` to allow browsing through them like any other folder.) This also makes it easy to implement automatic handling of different file types. Both of these things can be done simply by extending a base class (implementation details are written as docstrings in the various classes' code).

​	In addition, it is easy to implement new commands, as commands are simple functions which take two arguments: `context` (a reference to the current `Terminal` object) and `args` (a list of string arguments passed from the shell.)

​	The `prompt_toolkit` module is used for the included command-line interface, however, it should be relatively easy to write a different interface if desired (the same methods would need to be implemented, however this is less well documented I may change this more regularly than the implementation details of other parts of the program.)

​	After adding new functionality through additional `Path` subclasses or new commands, pass them to the `Terminal` constructor/`__init__` method, along with the file types they should be used for (for path classes.) There is a default list but these will be overridden by types that are passed in.
