from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel

from app.core.settings import settings
from app.mixin.async_execution import AsyncExecutionMixin
from app.widgets.card import card
from app.widgets.common import QProgressButton
from app.widgets.confirm_box import QConfirmMessageBox
from app.widgets.file_selector import QFilesSelector
from app.widgets.loader import QLoadingOverlay
from app.widgets.metrics import QMetrics
from app.widgets.switch import QSwitchField
from app.workers.month_summary import MonthSummaryWorker
from base.tab import TabWidget
from exceptions import ValidationException
from execution.month_summary import NOMINA_IMPORTES, NOMINA_NETO
from logger import logger


class QMonthSummary(AsyncExecutionMixin, TabWidget):
    layout_class = QVBoxLayout
    tooltip_label = 'concentrado mensual'
    page_title = 'Concentrado mensual'
    page_subtitle = 'Genera el concentrado de ingresos o egresos a partir de los ZIP de facturas del SAT'

    worker_class = MonthSummaryWorker
    busy_message = 'Generando concentrado...'

    def create_ui(self):
        self.selector = QFilesSelector(self, filter="*.zip")
        self.selector.setProperty('class', 'dropzone')
        self.prov_check = QSwitchField(self, text='Generar también el reporte por proveedor')

        self.rules = QLabel(self)
        self.rules.setProperty('class', 'secondary')
        self.rules.setWordWrap(True)

        self.metrics = QMetrics(self)
        self.execute_btn = QProgressButton('generar concentrado', self, fn=self.start_worker)
        self.execute_btn.setProperty('class', 'primary')
        self.execute_btn.setMinimumHeight(40)

        settings.register_setting(
            'check-providers',
            self.prov_check.isChecked,
            lambda x: self.prov_check.setChecked(x == 'true'),
            'false',
        )

    def load_ui(self, layout):
        frame, frame_layout = card(self, 'Archivos', 'Uno o varios ZIP descargados del SAT; uno por mes y tipo')
        self.loader = QLoadingOverlay(frame)
        frame_layout.addWidget(self.selector)
        frame_layout.addWidget(self.prov_check)
        frame_layout.addWidget(self.rules)
        layout.addWidget(frame)
        layout.addStretch(1)

        footer = QHBoxLayout()
        footer.addWidget(self.metrics, 1)
        footer.addWidget(self.execute_btn, 2)
        layout.addLayout(footer)

    def showEvent(self, event):
        super().showEvent(event)
        importe = NOMINA_IMPORTES.get(settings.value('nomina-importe') or NOMINA_NETO)
        self.rules.setText(f'Nóminas en egresos: {importe.lower()}. Se cambia en Configuración.')

    def validate_data(self):
        client = getattr(self.parent(), 'client_selector').get_current()
        if client is None:
            raise ValidationException('Seleccione un cliente')
        paths = self.selector.get_files()
        if not paths:
            raise ValidationException('Seleccione al menos un archivo ZIP')

        params = {
            'create_providers': self.prov_check.isChecked(),
            'nomina_importe': settings.value('nomina-importe') or NOMINA_NETO,
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
