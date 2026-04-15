from functools import cached_property
from pathlib import Path

from PySide6.QtWidgets import QLineEdit, QFileDialog

from app.mixin.property_update import PropertyMixin
from base.popup import QDialogException
from base.widget import BaseWidget


class QFilesSelector(PropertyMixin, BaseWidget):
    dialog_type = QFileDialog.getOpenFileNames
    placeholderText = 'archivos...'

    def __init__(self, *args, **kwargs):
        self.filter = kwargs.pop('filter', None)
        super().__init__(*args, **kwargs)
        self.files = None

    @cached_property
    def changeFiles(self):
        return self.input.textChanged

    def create_ui(self):
        self.input = QLineEdit(self, placeholderText=self.placeholderText)
        self.input.setReadOnly(True)
        self.input.mousePressEvent = self.on_click

    def load_ui(self, layout):
        layout.addWidget(self.input)

    def clear(self):
        self.input.clear()
        self.files = None

    def get_files(self) -> list[Path]:
        if self.files is None:
            raise QDialogException(self, 'seleccione al menos un archivo')

        return [Path(i) for i in self.files]

    def setPlaceholderText(self, text):
        self.input.setPlaceholderText(str(text))

    def on_click(self, _):
        self.on_click_files()

    def on_click_files(self):
        file_paths, _ = self.dialog_type(filter=self.filter)
        n_files = len(file_paths)

        if n_files == 0:
            return

        if n_files == 1:
            self.input.setText(file_paths[0])
            self.input.setToolTip('')
        else:
            self.input.setText(f"{n_files}'s files")
            self.input.setToolTip('\n'.join(file_paths))

        self.files = file_paths

    def setProperty(self, *args, **kwargs):
        self.setPropertyUpddate(self.input, *args, **kwargs)


class QDirSelector(QFilesSelector):
    dialog_type = QFileDialog.getExistingDirectory
    placeholderText = 'directorio...'

    @cached_property
    def changeDir(self):
        return self.input.textChanged

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filename = None
        self.path = None

    def with_file(self, filename):
        self.filename = filename

    def get_path(self) -> Path:
        if self.filename:
            self.path = Path(self.path)
            if self.path.name != self.filename:
                self.path = self.path / self.filename

        return Path(self.path)

    def setPath(self, path):
        self.path = Path(path)
        self.input.setText(str(path))

    def clear(self):
        self.input.clear()
        self.path = None

    def on_click(self, _):
        self.on_click_path()

    def on_click_path(self):
        self.path = self.dialog_type()
        path = self.get_path()
        self.input.setText(str(path))
        return path
