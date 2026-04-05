from pathlib import Path

from PySide6.QtWidgets import QVBoxLayout

from app.core.base_popup import QDialogException
from app.core.base_widget import BaseWidget
from app.messages_box.confirm_box import QConfirmMessageBox
from app.widgets.common import spacer, QButton
from app.widgets.file_selector import QFileSelector
from app.widgets.metrics import QMetrics
from core.exceptions import ValidationException
from core.month_summary import MonthSummary
from core.zip_file import ZipFile


class QMonthSummary(BaseWidget):
    layout_class = QVBoxLayout
    margin = (5, 5, 5, 5)

    def create_ui(self):
        self.selector = QFileSelector(self, filter="*.zip")

        self.metrics = QMetrics(self)
        self.execute_btn = QButton('ejecutar', self, fn=self.execute)
        self.execute_btn.setProperty('class', 'primary')

    def load_ui(self, layout):
        layout.addItem(spacer)
        layout.addWidget(self.selector)
        layout.addItem(spacer)

        layout.addWidget(self.metrics)
        layout.addWidget(self.execute_btn)

    def execute(self):
        self.execute_btn.setDisabled(True)

        try:
            raw_paths = self.selector.get_files()
            paths = [Path(i) for i in raw_paths]
            client = self.parent().client_selector.get_current()

            n_files = len(paths)
            for path in paths:
                zipfile = ZipFile(path)
                data_path = zipfile.extract()

                summary = MonthSummary(client)
                summary.add_files_in_folder(data_path)
                summary.save()

                if n_files == 1:
                    message = f'Se generó correctamente.\n{summary.path}\n¿Desea abrirlo?'
                    QConfirmMessageBox(self, message, summary.startfile)

            self.metrics.add_registers_today(n_files)
        except ValidationException as error:
            raise QDialogException(self, str(error), format=False)
        finally:
            self.execute_btn.setEnabled(True)
