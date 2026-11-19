"""Pestaña DIOT: proveedores del mes con los datos que el XML no trae y exportación del TXT del SAT."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QComboBox, QTableWidget, QTableWidgetItem, QLabel,
                               QHeaderView, QMessageBox)

from app.core.settings import settings
from app.widgets.common import QButton
from app.widgets.confirm_box import QConfirmMessageBox
from app.widgets.period_selector import QPeriodSelector, show_message
from app.workers.database import database_worker
from base.tab import TabWidget
from execution import cfdi_store, diot

COLUMNS = ['Estado', 'RFC', 'Proveedor', 'Docs', 'Tercero', 'Operación', 'Frontera', 'Valor 16 %', 'Dev. 16 %',
           'Valor 8 %', 'Tasa 0 %', 'Exento', 'No objeto', 'IVA ret.', 'ID fiscal ext.', 'Nombre ext.', 'País',
           'Jurisdicción']
COL = {name: i for i, name in enumerate(COLUMNS)}
TEXT_FIELDS = {'ID fiscal ext.': 'tax_id', 'Nombre ext.': 'nombre_extranjero', 'País': 'pais',
               'Jurisdicción': 'jurisdiccion'}


class QDiot(TabWidget):
    layout_class = QVBoxLayout
    tooltip_label = 'DIOT (carga masiva)'
    page_title = 'DIOT'
    page_subtitle = 'Proveedores del mes y archivo de carga masiva para el SAT'

    @property
    def client_selector(self):
        return getattr(self.parent(), 'client_selector')

    def create_ui(self):
        self.providers: list[diot.DiotProvider] = []
        self._loading = False

        self.period = QPeriodSelector(self)
        self.unpaid = []

        self.table = QTableWidget(self)
        self.table.setColumnCount(len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemChanged.connect(self.on_item_changed)

        self.note = QLabel(self)
        self.note.setWordWrap(True)
        self.note.setProperty('class', 'secondary')

        self.save_btn = QButton('guardar ajustes', self, fn=self.save_settings)
        self.save_btn.setToolTip('Recuerda tipo de operación, frontera y datos de extranjeros por proveedor')
        self.export_btn = QButton('exportar txt', self, fn=self.export)
        self.export_btn.setProperty('class', 'primary')

        self.period.changed.connect(self.load_data)
        self.client_selector.on_change(self.load_data)

    @property
    def base(self):
        return settings.value('diot-base') or 'pagado'

    @property
    def efectos_fiscales(self):
        return settings.value('diot-efectos') or '01'

    def load_ui(self, layout):
        top = QHBoxLayout()
        top.addWidget(self.period, 1)
        top.addStretch(1)
        layout.addLayout(top)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.note)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        bottom.addWidget(self.save_btn)
        bottom.addWidget(self.export_btn)
        layout.addLayout(bottom)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_data()

    # ---- datos ----------------------------------------------------------------
    def load_data(self, *_):
        client = self.client_selector.get_current()
        self.providers, self.unpaid = [], []
        if client is not None:
            with database_worker.new_session() as session:
                if self.base == 'facturado':
                    records = cfdi_store.received_records(session, client, self.period.year, self.period.month)
                else:
                    records, self.unpaid = cfdi_store.cash_records(session, client, self.period.year,
                                                                   self.period.month)
                self.providers = diot.aggregate(records, cfdi_store.diot_settings(session, client))
        self.update_note()
        self.fill_table()

    def update_note(self):
        if self.base == 'facturado':
            text = 'Base facturado (se cambia en Configuración): todas las facturas recibidas por su fecha. La DIOT pide lo efectivamente pagado.'
        else:
            text = 'Base pagado (se cambia en Configuración): facturas PUE por su fecha y PPD por la fecha de su complemento de pago.'
            if self.unpaid:
                text += (f' {len(self.unpaid)} factura(s) PPD del mes sin pago registrado no se incluyen '
                         f'(entrarán en el mes en que llegue su complemento de pago).')
        self.note.setText(text)
        self.note.setToolTip('\n'.join(f'{r.emisor.rfc} {r.emisor.name} {r.total:,.2f} ({r.uuid})'
                                       for r in self.unpaid))

    def fill_table(self):
        self._loading = True
        self.table.setRowCount(0)
        operations = diot.OPERACIONES_2025 if self.period.year >= 2025 else diot.OPERACIONES_2024

        for row, p in enumerate(self.providers):
            self.table.insertRow(row)
            self.set_text(row, 'RFC', p.rfc)
            self.set_text(row, 'Proveedor', p.nombre)
            self.set_text(row, 'Docs', str(p.documentos), number=True)

            self.set_combo(row, 'Tercero', diot.TIPOS_TERCERO, p.tipo_tercero, 'tipo_tercero')
            allowed = sorted(set().union(*operations.values()))
            self.set_combo(row, 'Operación', {k: f'{k} {diot.TIPOS_OPERACION[k]}' for k in allowed},
                           p.tipo_operacion, 'tipo_operacion')
            self.set_combo(row, 'Frontera', {diot.FRONTERA_NORTE: 'Norte', diot.FRONTERA_SUR: 'Sur'},
                           p.frontera, 'frontera', enabled=p.base8 > 0)

            for column, value in (('Valor 16 %', p.base16), ('Dev. 16 %', p.dev16), ('Valor 8 %', p.base8),
                                  ('Tasa 0 %', p.tasa0), ('Exento', p.exento), ('No objeto', p.no_objeto),
                                  ('IVA ret.', p.iva_retenido)):
                self.set_text(row, column, f'{diot.sat_round(value):,}', number=True)

            for column, attr in TEXT_FIELDS.items():
                item = QTableWidgetItem(getattr(p, attr))
                editable = p.tipo_tercero == diot.EXTRANJERO
                flags = Qt.ItemFlag.ItemIsEnabled | (Qt.ItemFlag.ItemIsEditable if editable else Qt.ItemFlag.NoItemFlags)
                item.setFlags(flags)
                self.table.setItem(row, COL[column], item)

            self.update_status(row)
        for column, width in (('Tercero', 120), ('Operación', 250), ('Frontera', 90)):
            self.table.horizontalHeader().setSectionResizeMode(COL[column], QHeaderView.ResizeMode.Interactive)
            self.table.setColumnWidth(COL[column], width)
        self._loading = False

    def set_text(self, row, column, text, number=False):
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        if number: item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.table.setItem(row, COL[column], item)

    def set_combo(self, row, column, options: dict, current, attr, enabled=True):
        combo = QComboBox(self.table)
        for key, label in options.items():
            combo.addItem(label, key)
        combo.setCurrentIndex(max(0, combo.findData(current)))
        combo.setEnabled(enabled)
        combo.currentIndexChanged.connect(lambda _, r=row, c=combo, a=attr: self.on_combo(r, a, c.currentData()))
        self.table.setCellWidget(row, COL[column], combo)

    def on_combo(self, row, attr, value):
        provider = self.providers[row]
        setattr(provider, attr, value)
        if attr == 'tipo_tercero':
            self.fill_table()  # habilita o deshabilita los campos de extranjero
        else:
            self.update_status(row)

    def on_item_changed(self, item):
        if self._loading: return
        name = COLUMNS[item.column()]
        if name in TEXT_FIELDS:
            setattr(self.providers[item.row()], TEXT_FIELDS[name], item.text().strip())
            self.update_status(item.row())

    def update_status(self, row):
        provider = self.providers[row]
        errors = diot.validate(provider, self.period.year)
        warnings = provider.warnings
        was_loading, self._loading = self._loading, True
        item = QTableWidgetItem('Revisar' if errors else ('Aviso' if warnings else 'OK'))
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        item.setToolTip('\n'.join(errors + warnings) if errors or warnings else 'Sin errores')
        item.setForeground(Qt.GlobalColor.red if errors else
                           (Qt.GlobalColor.darkYellow if warnings else Qt.GlobalColor.darkGreen))
        self.table.setItem(row, COL['Estado'], item)
        self._loading = was_loading

    # ---- acciones -------------------------------------------------------------
    def save_settings(self, quiet=False):
        client = self.client_selector.get_current()
        if client is None or not self.providers: return
        with database_worker.new_session() as session:
            cfdi_store.save_diot_settings(session, client, self.providers)
        if not quiet:
            show_message(self, f'Se guardaron los ajustes de {len(self.providers)} proveedores.', title='Listo')

    def export(self):
        client = self.client_selector.get_current()
        if client is None:
            show_message(self, 'Seleccione un cliente', icon=QMessageBox.Icon.Warning, title='DIOT')
            return
        if not self.providers:
            show_message(self, 'No hay facturas recibidas guardadas para este periodo.\n'
                               'Genere primero el concentrado de egresos del mes.',
                         icon=QMessageBox.Icon.Warning, title='DIOT')
            return

        path = diot.default_filename(settings.get_workdir(), client.rfc, self.period.year, self.period.month)
        try:
            diot.export(path, self.providers, self.period.year, self.efectos_fiscales)
        except ValueError as error:
            text, _, detail = str(error).partition('\n')
            show_message(self, text, detail, icon=QMessageBox.Icon.Warning, title='DIOT con errores')
            return

        self.save_settings(quiet=True)
        layout = '2025 en adelante' if self.period.year >= 2025 else '2024 y anteriores'
        QConfirmMessageBox(self, f'Se generó la DIOT ({layout}, {len(self.providers)} proveedores):\n{path}\n'
                                 f'¿Desea abrir la carpeta?', lambda: os.startfile(path.parent), title='DIOT')
