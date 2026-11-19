"""Pestaña Comprobantes: revisar los CFDI guardados de un mes, marcar cancelados y regenerar."""
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QComboBox, QTableWidget, QTableWidgetItem, QLabel,
                               QAbstractItemView, QHeaderView, QMessageBox, QWidget)

from app.core.settings import settings
from app.core.tasks import TaskRunner
from app.widgets.common import QButton
from app.widgets.loader import QLoadingOverlay
from app.widgets.toast import toast
from app.widgets.period_selector import QPeriodSelector, show_message
from app.widgets.switch import QSwitch, QClickComboBox, QSwitchField
from app.workers.database import database_worker
from base.tab import TabWidget
from execution import cfdi_store
from execution.month_summary import MonthSummary, GENERIC_RFCS, PUBLICO_EN_GENERAL
from execution.month_summary_providers import MonthSummaryProviders
from logger import logger

TIPOS = {'I': 'Factura', 'E': 'Nota de crédito', 'P': 'Pago', 'N': 'Nómina', 'T': 'Traslado'}
COLUMNS = ['Cancelado', 'Fecha', 'Tipo', 'RFC', 'Nombre', 'Total', 'IVA', 'Moneda', 'Origen']


def money(value) -> str:
    return f'{Decimal(value or 0):,.2f}'


class QCfdiAdmin(TabWidget):
    layout_class = QVBoxLayout
    tooltip_label = 'comprobantes guardados'
    page_title = 'Comprobantes'
    page_subtitle = 'Facturas guardadas por mes: marque las canceladas y regenere el concentrado'

    @property
    def client_selector(self):
        return getattr(self.parent(), 'client_selector')

    def create_ui(self):
        self.period = QPeriodSelector(self)
        self.kind = QClickComboBox(self)
        self.kind.addItem('Egresos', False)
        self.kind.addItem('Ingresos', True)

        self.table = QTableWidget(self)
        self.table.setColumnCount(len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        self.summary = QLabel(self)
        self.summary.setProperty('class', 'secondary')

        self.regenerate_btn = QButton('regenerar concentrado', self, fn=self.regenerate)
        self.regenerate_btn.setProperty('class', 'primary')
        self.regenerate_btn.setToolTip('Vuelve a generar la hoja del mes con los comprobantes no cancelados')

        self.prov_check = QSwitchField(self, text='Incluir reporte por proveedor')
        self.prov_check.setToolTip('Al regenerar, también actualiza el concentrado por proveedor del mes')
        settings.register_setting(
            'cfdi-check-providers',
            self.prov_check.isChecked,
            lambda x: self.prov_check.setChecked(x == 'true'),
            'false',
        )

        self.tasks = TaskRunner(self)
        self.loader = QLoadingOverlay(self.table)

        self.period.changed.connect(self.request_load)
        self.kind.currentIndexChanged.connect(self.request_load)
        self.client_selector.on_change(self.request_load)
        self._loading = False
        self.dirty = False

    def load_ui(self, layout):
        top = QHBoxLayout()
        top.addWidget(self.period, 2)
        top.addWidget(self.kind, 1)
        layout.addLayout(top)
        layout.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        bottom.addWidget(self.summary, 1)
        bottom.addWidget(self.prov_check)
        bottom.addWidget(self.regenerate_btn)
        layout.addLayout(bottom)

    def load_data(self, *_):
        client = self.client_selector.get_current()
        if client is None:
            self.table.setRowCount(0)
            self.summary.setText('Seleccione un cliente')
            return

        ingreso, year, month = self.kind.currentData(), self.period.year, self.period.month
        self.summary.setText('Cargando comprobantes...')

        def query():
            with database_worker.new_session() as session:
                return cfdi_store.month_records(session, client, year, month, ingreso, include_cancelled=True)

        self.tasks.run('load', query, on_done=lambda records: self.show_records(records, ingreso),
                       on_error=self.on_load_error, overlay=self.loader, message='Cargando comprobantes...')

    def on_load_error(self, error):
        self.summary.setText(f'No se pudieron cargar los comprobantes: {error}')

    def show_records(self, records, ingreso):
        self._loading = True
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(0)
            for record in records:
                self.add_row(record, ingreso)
        finally:
            self.table.setUpdatesEnabled(True)
            self._loading = False
            self.set_dirty(False)

        active = [r for r in records if not r.cancelado]
        cancelled = len(records) - len(active)
        if not records:
            self.summary.setText('No hay comprobantes guardados de este periodo. '
                                 'Se guardan al generar el concentrado mensual.')
        else:
            total = (sum((r.total for r in active if r.tipo == 'I'), Decimal(0))
                     - sum((r.total for r in active if r.tipo == 'E'), Decimal(0)))
            self.summary.setText(f'{len(records)} comprobantes · {cancelled} cancelados · total {money(total)}')

    def add_row(self, record, ingreso):
        row = self.table.rowCount()
        self.table.insertRow(row)

        cell = QWidget(self.table)
        cell.setStyleSheet("background: transparent;")
        cell_layout = QHBoxLayout(cell)
        cell_layout.setContentsMargins(0, 0, 0, 0)
        cell_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        switch = QSwitch(cell, checked=bool(record.cancelado))
        switch.setToolTip('Marcar como cancelado (se excluye del concentrado y de la DIOT)')
        switch.toggled.connect(lambda checked, uuid=record.uuid: self.on_cancel_toggled(uuid, checked))
        cell_layout.addWidget(switch)
        self.table.setCellWidget(row, 0, cell)

        counterpart = record.receptor if (ingreso or record.tipo == 'N') else record.emisor
        name = PUBLICO_EN_GENERAL if counterpart.rfc in GENERIC_RFCS else counterpart.name
        values = [record.fecha.strftime('%d/%m/%Y'), TIPOS.get(record.tipo, record.tipo), counterpart.rfc, name,
                  money(record.total), money(record.iva), record.moneda or '', record.origen or '']
        for column, value in enumerate(values, 1):
            item = QTableWidgetItem(str(value))
            item.setToolTip(f'UUID {record.uuid}')
            if column in (5, 6):
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, column, item)

    def on_cancel_toggled(self, uuid, cancelled):
        if self._loading: return
        client = self.client_selector.get_current()
        self.set_dirty(True)  # la interfaz responde de inmediato; el guardado corre en segundo plano

        def save():
            with database_worker.new_session() as session:
                cfdi_store.set_cancelled(session, client, uuid, cancelled)
            logger.info(f'CFDI {uuid} cancelado={cancelled}')

        self.tasks.run(f'cancel-{uuid}', save, on_error=lambda e: show_message(
            self, f'No se pudo guardar el cambio: {e}', icon=QMessageBox.Icon.Warning, title='Comprobantes'))

    def set_dirty(self, dirty):
        self.dirty = dirty
        self.regenerate_btn.setText('Regenerar concentrado' + (' *' if dirty else ''))

    def regenerate(self):
        client = self.client_selector.get_current()
        if client is None or self.tasks.is_running('regenerate'): return
        ingreso, year, month = self.kind.currentData(), self.period.year, self.period.month
        nomina_importe = settings.value('nomina-importe')
        summary = MonthSummary(client, nomina_importe=nomina_importe)
        providers = MonthSummaryProviders(client, nomina_importe=nomina_importe) if self.prov_check.isChecked() else None

        def work():
            with database_worker.new_session() as session:
                records = cfdi_store.month_records(session, client, year, month, ingreso)
            if not records: return None
            summary.add_records(records)
            summary.save()
            if providers is not None:
                providers.add_records(records)
                providers.save()
            return summary

        def done(result):
            self.regenerate_btn.setEnabled(True)
            if result is None:
                show_message(self, 'No hay comprobantes vigentes para este periodo.',
                             icon=QMessageBox.Icon.Warning, title='Sin comprobantes')
                return
            self.set_dirty(False)
            files = result.filename.name + (f' y {providers.filename.name}' if providers is not None else '')
            toast(self, 'Concentrado regenerado', detail=files, action=('Abrir', result.startfile))

        def failed(error):
            self.regenerate_btn.setEnabled(True)
            show_message(self, str(error), icon=QMessageBox.Icon.Warning, title='No se pudo regenerar')

        self.regenerate_btn.setEnabled(False)
        self.tasks.run('regenerate', work, on_done=done, on_error=failed, overlay=self.loader,
                       message='Regenerando concentrado...')
