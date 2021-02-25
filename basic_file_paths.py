import os
import subprocess
import warnings
from typing import Optional

import paths
from errors import NonexistentMappingError, UnsupportedOperationWarning

class ImageFile(paths.FilePath):
    def __init__(self, name: str, parent: Optional[paths.DirPath] = None, backend: str = 'fs',
                 path_type: str = 'image') -> None:
        """Initializes a new ImageFile object.

        :param name: inherited from paths.Path
        :param parent: inherited from paths.Path
        :param backend: inherited from paths.Path
        :param path_type: only included for continuity with other Path objects, this is ignored.
                          This type can only represent an image file.
        """
        super().__init__(name=name, parent=parent, backend=backend, path_type='image')
        self.image = None

    def set_type(self, path_type: str) -> None:
        """Overrides Path.set_type(), does nothing. This type can only represent an image file."""
        pass

    def open(self) -> None:
        self.load()
        self.image.show()

    def c_open(self) -> 'ImageContextManager':
        self.load()
        return ImageContextManager(self.image)

    def load(self) -> None:
        if self.image is not None:
            return
        from PIL import Image
        if self.backend == 'fs':
            self.image = Image.open(self.get_path())
        else:
            self.image = Image.open(self.get_parent().v_open(self.get_path()))


class ImageContextManager:
    """This is a context manager which should only be constructed and managed by ImagePath objects."""

    def __init__(self, image):
        self.image = image

    def __enter__(self):
        return self.image

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class GenericFile(paths.FilePath):
    def __init__(self, name: str, parent: Optional[paths.DirPath] = None, backend: str = 'fs',
                 path_type: str = 'pdf') -> None:
        """Initializes a new GenericFile object.

        :param name: inherited from paths.Path
        :param parent: inherited from paths.Path
        :param backend: inherited from paths.Path
        :param path_type: inherited from paths.Path
        """
        super().__init__(name=name, parent=parent, backend=backend, path_type=path_type)
        self.programs = { # If the viewer is None, open with the OS default program (this may only work on Windows)
            'pdf': r'C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe',
            'video': r'C:\Program Files\VideoLAN\VLC\vlc.exe',
            'generic': None,
        }

    def open(self):
        if self.get_type() in self.programs:
            if self.get_backend() == 'fs':
                file = self.get_path()
            else:
                file = self.get_parent().v_open(self.get_name(), temp=True, text=False)
            args = [self.programs[self.get_type()]] if self.programs[self.get_type()] else []
            args.append(file)
            subprocess.run(args)
        else:
            warnings.warn(UnsupportedOperationWarning(f'Opening {self.get_type()} files is not currently supported.'))


class TermuxGenericFile(paths.FilePath):
    def __init__(self, name: str, parent: Optional[paths.DirPath] = None, backend: str = 'fs',
                 path_type: str = 'pdf') -> None:
        """Initializes a new GenericFile object.

        :param name: inherited from paths.Path
        :param parent: inherited from paths.Path
        :param backend: inherited from paths.Path
        :param path_type: inherited from paths.Path
        """
        super().__init__(name=name, parent=parent, backend=backend, path_type=path_type)

    def open(self):
        if self.get_backend() == 'fs':
            file = self.get_path()
        else:
            file = self.get_parent().v_open(self.get_name(), temp=True, text=False)
        subprocess.run(['termux-open', file])
