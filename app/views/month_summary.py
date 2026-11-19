from exceptions import ValidationException
from PySide6.QtWidgets import QVBoxLayout, QCheckBox, QComboBox, QHBoxLayout, QLabel

from app.core.settings import settings
from app.mixin.async_execution import AsyncExecutionMixin
from app.widgets.common import spacer, QProgressButton
from app.widgets.confirm_box import QConfirmMessageBox
from app.widgets.file_selector import QFilesSelector
from app.widgets.metrics import QMetrics
from app.workers.month_summary import MonthSummaryWorker
from execution.month_summary import NOMINA_IMPORTES, NOMINA_NETO
from base.tab import TabWidget
from logger import logger


class QMonthSummary(AsyncExecutionMixin, TabWidget):
    layout_class = QVBoxLayout
    tooltip_label = 'concentrado mensual'

    worker_class = MonthSummaryWorker

    def create_ui(self):
        self.selector = QFilesSelector(self, filter="*.zip")
        self.prov_check = QCheckBox('Proveedores', self)

        # Importe con el que las nóminas que paga el cliente entran a sus egresos
        self.nomina_label = QLabel('Nóminas en egresos', self)
        self.nomina_combo = QComboBox(self)
        for key, label in NOMINA_IMPORTES.items():
            self.nomina_combo.addItem(label, key)
        self.nomina_combo.setToolTip('Neto pagado: total del recibo (como el programa anterior).\n'
                                     'Percepciones: sueldo bruto antes de ISR retenido, IMSS y otras deducciones.')

        self.metrics = QMetrics(self)
        self.execute_btn = QProgressButton('ejecutar', self, fn=self.start_worker)
        self.execute_btn.setProperty('class', 'primary')

        settings.register_setting(
            'check-providers',
            self.prov_check.isChecked,
            lambda x: self.prov_check.setChecked(x == 'true'),
            'false',
        )

        settings.register_setting(
            'nomina-importe',
            lambda: self.nomina_combo.currentData(),
            lambda x: self.nomina_combo.setCurrentIndex(max(0, self.nomina_combo.findData(x))),
            NOMINA_NETO,
        )

    def load_ui(self, layout):
        layout.addItem(spacer)
        layout.addWidget(self.selector)
        layout.addWidget(self.prov_check)

        nomina_layout = QHBoxLayout()
        nomina_layout.addWidget(self.nomina_label)
        nomina_layout.addWidget(self.nomina_combo, 1)
        layout.addLayout(nomina_layout)
        layout.addItem(spacer)

        layout.addWidget(self.metrics)
        layout.addWidget(self.execute_btn)

    def validate_data(self):
        client = getattr(self.parent(), 'client_selector').get_current()
        if client is None:
            raise ValidationException('Seleccione un cliente')
        paths = self.selector.get_files()
        if not paths:
            raise ValidationException('Seleccione al menos un archivo ZIP')

        params = {
            'create_providers': self.prov_check.isChecked(),
            'nomina_importe': self.nomina_combo.currentData(),
        }

        return paths, client, params

    def on_success(self, summary, n_files):
        logger.debug(f'{self.__class__.__name__} generation success {summary} {n_files}')

        self.execute_btn.setEnabled(True)
        self.execute_btn.resetProgress()
        self.metrics.add_registers_today(n_files)
        self.selector.clear()

        title = '¿Desea abrirlo?'
        message = f'Se generó correctamente.\n{summary.filename}\n{title}'
        QConfirmMessageBox(self, message, summary.startfile, title=title)
