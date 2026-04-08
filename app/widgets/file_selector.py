from pathlib import Path

from PySide6.QtWidgets import QLineEdit, QFileDialog

from base.popup import QDialogException
from base.widget import BaseWidget


class QFileSelector(BaseWidget):
    def __init__(self, *args, **kwargs):
        self.filter = kwargs.pop('filter', None)
        super().__init__(*args, **kwargs)
        self.files = None

    def create_ui(self):
        self.input = QLineEdit(self, placeholderText='files...')
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

    def on_click(self, _):
        file_paths, _ = QFileDialog.getOpenFileNames(filter=self.filter)
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
