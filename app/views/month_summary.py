from PySide6.QtWidgets import QVBoxLayout, QCheckBox

from app.mixin.async_execution import AsyncExecutionMixin
from app.widgets.common import spacer, QProgressButton
from app.widgets.confirm_box import QConfirmMessageBox
from app.widgets.file_selector import QFilesSelector
from app.widgets.metrics import QMetrics
from app.workers.month_summary_worker import MonthSummaryWorker
from base.widget import BaseWidget


class QMonthSummary(AsyncExecutionMixin, BaseWidget):
    layout_class = QVBoxLayout
    margin = (5, 5, 5, 5)

    worker_class = MonthSummaryWorker

    def create_ui(self):
        self.selector = QFilesSelector(self, filter="*.zip")
        self.prov_check = QCheckBox('Proveedores', self)

        self.metrics = QMetrics(self)
        self.execute_btn = QProgressButton('ejecutar', self, fn=self.start_worker)
        self.execute_btn.setProperty('class', 'primary')

    def load_ui(self, layout):
        layout.addItem(spacer)
        layout.addWidget(self.selector)
        layout.addWidget(self.prov_check)
        layout.addItem(spacer)

        layout.addWidget(self.metrics)
        layout.addWidget(self.execute_btn)

    def validate_data(self):
        client = getattr(self.parent(), 'client_selector').get_current()
        get_paths = self.selector.get_files()

        params = {
            'create_providers': self.prov_check.isChecked(),
        }

        return get_paths, client, params

    def on_success(self, summary, n_files):
        self.execute_btn.setEnabled(True)
        self.execute_btn.resetProgress()
        self.metrics.add_registers_today(n_files)
        self.selector.clear()

        title = '¿Desea abrirlo?'
        message = f'Se generó correctamente.\n{summary.filename}\n{title}'
        QConfirmMessageBox(self, message, summary.startfile, title=title)
