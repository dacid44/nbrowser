from __future__ import annotations

import os
import pathlib
import tempfile
import shutil
from io import FileIO, BytesIO, StringIO
from collections.abc import Sequence
from typing import Optional, Union, IO, Any

import paths


# TODO: Implement unzip or lzma based virtual paths, and one based on the 7z archive (much faster
#  and compatible with basically every archive format)
class ArchivePath(paths.VirtualDirPath):
    def __init__(self, name: str, parent: paths.DirPath, backend: str = 'py7zr', path_type: str = 'archive',
                 is_anchor: bool = True) -> None:
        super().__init__(name=name, parent=parent, backend='py7zr', path_type=path_type)
        self.is_anchor = is_anchor
        self.anchor = self.get_path() if self.is_anchor else None
        self.anchor = self.get_anchor()
        self.child_data = {}

    def set_is_anchor(self, is_anchor: bool) -> None:
        self.is_anchor = is_anchor

    def set_anchor(self, anchor: str) -> None:
        self.anchor = anchor

    def get_is_anchor(self) -> bool:
        return self.is_anchor

    def get_anchor(self) -> str:
        if self.anchor is not None:
            return self.anchor
        elif self.get_is_anchor():
            return self.get_path()
        else:
            return self.get_parent().get_anchor()


class Py7zrArchivePath(ArchivePath):
    def __init__(self, name: str, parent: paths.DirPath, backend: str = 'py7zr', path_type: str = '7z',
                 is_anchor: bool = True) -> None:
        super().__init__(name=name, parent=parent, backend='py7zr', path_type=path_type, is_anchor=is_anchor)
        self.archive_file = None

    def get_archive_file(self) -> 'py7zr.SevenZipFile':
        if self.archive_file is not None:
            return self.archive_file
        elif not self.get_is_anchor():
            return self.parent.get_archive_file()
        else:
            import py7zr
            if self.get_parent().get_backend() == 'fs':
                file = self.get_path()
            else:
                file = self.get_parent().v_open(self.get_name(), temp=False, text=False)
            try:
                try:
                    return py7zr.SevenZipFile(file, 'r')
                except py7zr.exceptions.PasswordRequired:
                    import lzma
                    for i in range(3):
                        try:
                            password = self.get_context().password(f'{self.get_name()} requires a password: ')
                            return py7zr.SevenZipFile(file, mode='r', password=password)
                        except lzma.LZMAError:
                            self.get_context().error('Incorrect password.')
            except py7zr.exceptions.ArchiveError as e:
                self.get_context().error(f'Decompression error: {str(e)}')

    def filter_children(self, files: list[dict]) -> dict[str, dict]:
        to_return = {}
        for file in files:
            # print(file['filename'], os.path.dirname(os.path.join(self.get_anchor(), file['filename'])))
            if os.path.normpath(self.get_path()) == \
                    os.path.normpath(os.path.dirname(os.path.join(self.get_anchor(), file['filename']))) and \
                    os.path.basename(file['filename']) not in self.children:
                # print('adding')
                to_return[os.path.basename(file['filename'])] = file
        return to_return

    def find_children(self) -> None:
        if self.archive_file is None:
            self.archive_file = self.get_archive_file()
        if self.archive_file is not None:
            child_info = self.filter_children(self.archive_file.header.files_info.files)
            for item in child_info:
                if child_info[item]['folder'] is None:
                    self.get_context().add_path(name=item, is_dir=True, path_type='7z', backend='py7zr',
                                                dest=self, init_kwargs={'is_anchor': False})
                else:
                    self.get_context().add_path(name=item, is_dir=False, backend='py7zr', dest=self)

    def v_open(self, path: str, temp: bool = False, text: bool = False) -> Union[str, IO]:
        if path not in self.child_data:
            extract_path = pathlib.Path(
                os.path.relpath(os.path.join(self.get_path(), path), self.get_anchor())).as_posix()
            self.child_data[path] = self.archive_file.read([extract_path])[extract_path].read()
            self.archive_file.reset()
        if temp:
            file = tempfile.mkstemp(suffix=os.path.splitext(path)[1], text=False)
            self.get_context().add_tempfile(file[1])
            with FileIO(file[0], 'wb') as f:
                data = BytesIO(self.child_data[path])
                shutil.copyfileobj(data, f)
            return file[1]
        else:
            if text:
                return StringIO(str(self.child_data[path], encoding='utf-8'))
            else:
                return BytesIO(self.child_data[path])
