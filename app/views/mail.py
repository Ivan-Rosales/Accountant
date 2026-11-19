"""Pestaña Correos: facturas detectadas en la carpeta vigilada, envío y reenvíos desde el historial."""
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
                               QAbstractItemView, QListWidget, QListWidgetItem, QLineEdit, QTextEdit, QFrame,
                               QFileDialog, QMessageBox, QPushButton, QButtonGroup)

from app.core.settings import settings
from app.core.tasks import TaskRunner
from app.widgets.common import QButton
from app.widgets.loader import QLoadingOverlay
from app.widgets.message_dialog import KIND_INFO
from app.widgets.period_selector import show_message
from app.widgets.switch import QSwitchField
from app.widgets.toast import toast
from app.workers.database import database_worker
from app.workers.watch_dog import WatchdogWorker
from base.tab import TabWidget
from execution import mailer, contacts as contact_store
from logger import logger

RECENT_DAYS = 2  # al iniciar, se muestran los pares no enviados de los últimos días
PENDING, HISTORY = 'pending', 'history'


def is_invoice_file(path: str) -> bool:
    name = Path(path).name
    return Path(path).suffix.lower() in ('.xml', '.pdf') and not name.startswith(('~$', '.'))


class QMailPanel(QFrame):
    """Detalle de una factura: destinatarios sugeridos, todos los del cliente, nuevos, asunto y mensaje."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setProperty('class', 'card')
        self.mail: mailer.InvoiceMail | None = None

        self.title = QLabel('Seleccione una factura', self)
        self.title.setProperty('class', 'card-title')
        self.title.setWordWrap(True)
        self.info = QLabel(self)
        self.info.setProperty('class', 'secondary')
        self.info.setWordWrap(True)
        self.notice = QLabel(self)
        self.notice.setProperty('class', 'notice')
        self.notice.setWordWrap(True)
        self.notice.hide()

        self.recommended = QListWidget(self)
        self.others = QListWidget(self)
        for widget in (self.recommended, self.others):
            widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

        self.new_emails = QLineEdit(self)
        self.new_emails.setPlaceholderText('Otros destinatarios: correo@empresa.com; otro@empresa.com')
        self.save_contact = QSwitchField(self, text='Guardar los correos nuevos en el contacto')
        self.subject = QLineEdit(self)
        self.subject.setPlaceholderText('Asunto')
        self.body = QTextEdit(self)
        self.body.setAcceptRichText(False)
        self.body.setMinimumHeight(90)

        self.dismiss_btn = QButton('descartar', self)
        self.dismiss_btn.setToolTip('Quitar de pendientes sin enviar')
        self.send_btn = QButton('enviar', self)
        self.send_btn.setProperty('class', 'primary')

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(6)
        layout.addWidget(self.title)
        layout.addWidget(self.info)
        layout.addWidget(self.notice)
        for text, widget, stretch in (('Recomendados (contacto de la factura)', self.recommended, 1),
                                      ('Otros correos del cliente', self.others, 1)):
            label = QLabel(text, self)
            label.setProperty('class', 'field-label')
            layout.addWidget(label)
            layout.addWidget(widget, stretch)
        layout.addWidget(self.new_emails)
        layout.addWidget(self.save_contact)
        label = QLabel('Asunto y mensaje', self)
        label.setProperty('class', 'field-label')
        layout.addWidget(label)
        layout.addWidget(self.subject)
        layout.addWidget(self.body, 1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.dismiss_btn)
        buttons.addWidget(self.send_btn)
        layout.addLayout(buttons)
        self.set_mail(None)

    def set_mail(self, mail: mailer.InvoiceMail | None, preselected: list | None = None, allow_dismiss=True):
        self.mail = mail
        enabled = mail is not None
        for widget in (self.recommended, self.others, self.new_emails, self.subject, self.body, self.send_btn,
                       self.save_contact):
            widget.setEnabled(enabled)
        self.dismiss_btn.setVisible(allow_dismiss)
        self.dismiss_btn.setEnabled(enabled)
        self.recommended.clear()
        self.others.clear()
        self.new_emails.clear()
        self.notice.hide()
        if mail is None:
            self.title.setText('Seleccione una factura')
            self.info.setText('Las facturas aparecen aquí cuando se guarda un PDF y un XML con el mismo nombre '
                              'en la carpeta vigilada, o con "Enviar archivo...".')
            self.subject.clear()
            self.body.clear()
            return

        self.title.setText(f'{mail.label} · {mail.contacto_nombre or mail.contacto_rfc}')
        self.info.setText(f'{mail.fecha:%d/%m/%Y} · ${mail.total:,.2f} · {mail.contacto_rfc}\n'
                          f'{mail.xml_path.name} + {mail.pdf_path.name}')

        notices = []
        if mail.cliente_id is None:
            notices.append(f'El RFC {mail.emisor_rfc} no corresponde a un cliente registrado: '
                           'puede enviarlo, pero no se guardarán contactos.')
        if mail.sent_before:
            last = mail.sent_before[0]
            notices.append(f'Ya se envió el {last.fecha:%d/%m/%Y %H:%M} a {last.destinatarios}.')
        if notices:
            self.notice.setText('\n'.join(notices))
            self.notice.show()

        chosen = set(preselected) if preselected is not None else set(mail.recommended)
        for email in mail.recommended:
            self._add_item(self.recommended, email, email, email in chosen)
        if not mail.recommended:
            self._placeholder(self.recommended, 'El contacto no tiene correos: agréguelos abajo'
                              if mail.cliente_id else 'Sin cliente registrado')
        recommended = set(mail.recommended)
        others = [(e, name) for name, emails in mail.all_emails.items() for e in emails if e not in recommended]
        for email, name in others:
            self._add_item(self.others, f'{email}  —  {name}', email, email in chosen)
        if not others:
            self._placeholder(self.others, 'Sin otros correos')
        extra = [e for e in chosen if e not in recommended and e not in {o for o, _ in others}]
        self.new_emails.setText('; '.join(extra))

        self.save_contact.setEnabled(mail.cliente_id is not None)
        self.save_contact.setChecked(mail.cliente_id is not None)
        self.save_contact.label.setText(f'Guardar los correos nuevos en el contacto {mail.contacto_rfc}'
                                        + ('' if mail.contact_exists else ' (se creará)'))
        self.subject.setText(mailer.default_subject(mail))
        self.body.setPlainText(mailer.default_body(mail))

    @staticmethod
    def _add_item(widget, text, email, checked):
        item = QListWidgetItem(text, widget)
        item.setData(Qt.ItemDataRole.UserRole, email)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)

    @staticmethod
    def _placeholder(widget, text):
        item = QListWidgetItem(text, widget)
        item.setFlags(Qt.ItemFlag.NoItemFlags)

    def checked_emails(self) -> list[str]:
        emails = []
        for widget in (self.recommended, self.others):
            for row in range(widget.count()):
                item = widget.item(row)
                if item.checkState() == Qt.CheckState.Checked and item.data(Qt.ItemDataRole.UserRole):
                    emails.append(item.data(Qt.ItemDataRole.UserRole))
        return emails

    def recipients(self) -> tuple[list[str], list[str]]:
        """(todos los destinatarios, los que no estaban registrados)."""
        new = contact_store.split_emails(self.new_emails.text())
        chosen = self.checked_emails()
        return list(dict.fromkeys(chosen + new)), [e for e in new if e not in chosen]


class QMail(TabWidget):
    layout_class = QVBoxLayout
    tooltip_label = 'envío de facturas por correo'
    page_title = 'Correos'
    page_subtitle = 'Envíe al cliente de su cliente las facturas detectadas en la carpeta vigilada'

    def create_ui(self):
        self.tasks = TaskRunner(self)
        self.pending: dict[str, mailer.InvoiceMail] = {}
        self.dismissed: set[str] = set()
        self.history_rows = []
        self.mode = PENDING

        self.pending_btn = QPushButton('Pendientes', self)
        self.history_btn = QPushButton('Historial y reenvíos', self)
        self.mode_group = QButtonGroup(self)
        for button, mode in ((self.pending_btn, PENDING), (self.history_btn, HISTORY)):
            button.setCheckable(True)
            button.setProperty('class', 'segment')
            self.mode_group.addButton(button)
            button.clicked.connect(lambda _, m=mode: self.set_mode(m))
        self.pending_btn.setChecked(True)
        self.pending_btn.setProperty('position', 'first')
        self.history_btn.setProperty('position', 'last')

        self.open_btn = QButton('enviar archivo...', self, fn=self.open_file)
        self.open_btn.setToolTip('Elegir un XML (con su PDF del mismo nombre) para enviarlo o reenviarlo')
        self.status = QLabel(self)
        self.status.setProperty('class', 'secondary')

        self.table = QTableWidget(self)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.table.itemSelectionChanged.connect(self.on_select)
        self.loader = QLoadingOverlay(self.table)

        self.panel = QMailPanel(self)
        self.panel_loader = QLoadingOverlay(self.panel)
        self.panel.send_btn.clicked.connect(self.send)
        self.panel.dismiss_btn.clicked.connect(self.dismiss)

        # Vigilancia de la carpeta (los reenvíos no dependen de ella)
        self.watchdog = WatchdogWorker(None, relevant=is_invoice_file, recursive=False)
        self.watchdog.change.connect(self.on_file_event)
        self.changed_paths: set[str] = set()
        self.scan_timer = QTimer(self)
        self.scan_timer.setSingleShot(True)
        self.scan_timer.setInterval(900)  # esperar a que terminen de copiarse PDF y XML
        self.scan_timer.timeout.connect(self.scan_changes)
        self.destroyed.connect(self.watchdog.stop)
        QTimer.singleShot(0, self.apply_watch_settings)

    def load_ui(self, layout):
        top = QHBoxLayout()
        top.setSpacing(0)
        top.addWidget(self.pending_btn)
        top.addWidget(self.history_btn)
        top.addSpacing(12)
        top.addWidget(self.status, 1)
        top.addWidget(self.open_btn)
        layout.addLayout(top)

        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self.table, 1)
        body.addWidget(self.panel, 1)
        layout.addLayout(body, 1)

    # ---- vigilancia -------------------------------------------------------------
    @property
    def watch_dir(self):
        value = settings.value('mail-watchdir')
        return Path(str(value)) if value else None

    @property
    def watch_enabled(self):
        return str(settings.value('mail-watch') or 'true') != 'false'

    def apply_watch_settings(self, *_):
        folder = self.watch_dir
        if self.watch_enabled and folder is not None and folder.is_dir():
            self.watchdog.set_path(folder)
            self.status.setText(f'Vigilando {folder}')
            self.scan_recent()
        else:
            self.watchdog.set_path(None)
            reason = 'pausada' if not self.watch_enabled else 'sin carpeta válida'
            self.status.setText(f'Vigilancia {reason} (Configuración > Correo)')

    def on_file_event(self, path):
        self.changed_paths.add(path)
        self.scan_timer.start()

    def scan_recent(self):
        """Al iniciar: pares recientes de la carpeta que aún no se han enviado."""
        folder = self.watch_dir
        since = datetime.now() - timedelta(days=RECENT_DAYS)

        def work():
            with database_worker.new_session() as session:
                pairs = [p for p in mailer.find_pairs(folder)
                         if datetime.fromtimestamp(p[0].stat().st_mtime) >= since]
                mails = [m for xml, pdf in pairs if (m := mailer.analyze(session, xml, pdf))]
            return [m for m in mails if not m.sent_before]

        self.tasks.run('scan-recent', work, on_done=lambda mails: self.add_pending(mails, notify=False))

    def scan_changes(self):
        paths, self.changed_paths = self.changed_paths, set()

        def work():
            pairs = {pair[0]: pair for path in paths if (pair := mailer.pair_for(Path(path)))}
            with database_worker.new_session() as session:
                return [m for xml, pdf in pairs.values() if (m := mailer.analyze(session, xml, pdf))]

        self.tasks.run(f'scan-{id(paths)}', work, on_done=lambda mails: self.add_pending(mails, notify=True))

    def add_pending(self, mails, notify):
        new = [m for m in mails if m.key not in self.pending and m.key not in self.dismissed]
        for mail in mails:
            if mail.key not in self.dismissed:
                self.pending[mail.key] = mail  # actualiza si el archivo cambió
        if self.mode == PENDING:
            self.fill_pending()
        self.update_counts()
        if notify and new:
            mail = new[0]
            detail = f'{mail.contacto_nombre or mail.contacto_rfc}' + (f' y {len(new) - 1} más' if len(new) > 1 else '')
            toast(self, f'{mail.label} lista para enviar', detail=detail, kind=KIND_INFO,
                  action=('Ver', lambda key=mail.key: self.show_pending(key)), duration=8000)

    def show_pending(self, key):
        window = self.window()
        if hasattr(window, 'change_current_tab'):
            window.change_current_tab('mail')
        self.set_mode(PENDING)
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).data(Qt.ItemDataRole.UserRole) == key:
                self.table.selectRow(row)

    def update_counts(self):
        self.pending_btn.setText(f'Pendientes ({len(self.pending)})' if self.pending else 'Pendientes')

    # ---- listas -------------------------------------------------------------------
    def set_mode(self, mode):
        self.mode = mode
        (self.pending_btn if mode == PENDING else self.history_btn).setChecked(True)
        if mode == PENDING:
            self.fill_pending()
        else:
            self.load_history()

    def load_data(self, *_):
        self.set_mode(self.mode)

    def _setup_columns(self, labels, stretch):
        self.table.clear()
        self.table.setColumnCount(len(labels))
        self.table.setHorizontalHeaderLabels(labels)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(stretch, QHeaderView.ResizeMode.Stretch)

    def _row(self, values, key, tooltip=''):
        row = self.table.rowCount()
        self.table.insertRow(row)
        for column, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            item.setData(Qt.ItemDataRole.UserRole, key)
            if tooltip: item.setToolTip(tooltip)
            self.table.setItem(row, column, item)

    def fill_pending(self):
        self.table.blockSignals(True)
        self._setup_columns(['Fecha', 'Comprobante', 'Para', 'Total'], 2)
        self.table.setRowCount(0)
        for mail in sorted(self.pending.values(), key=lambda m: m.fecha, reverse=True):
            self._row([f'{mail.fecha:%d/%m/%Y}', mail.label, mail.contacto_nombre or mail.contacto_rfc,
                       f'${mail.total:,.2f}'], mail.key,
                      tooltip=f'Cliente: {mail.cliente_nombre or "no registrado"} ({mail.emisor_rfc})\n'
                              f'{mail.xml_path}')
        self.table.blockSignals(False)
        if self.table.rowCount():
            self.table.selectRow(0)
        else:
            self.panel.set_mail(None)

    def load_history(self):
        def work():
            with database_worker.new_session() as session:
                return mailer.history(session)

        self.tasks.run('history', work, on_done=self.fill_history, overlay=self.loader, message='Cargando historial...')

    def fill_history(self, rows):
        self.history_rows = rows
        self.table.blockSignals(True)
        self._setup_columns(['Fecha', 'Para', 'Destinatarios', 'Estado'], 2)
        self.table.setRowCount(0)
        for index, row in enumerate(rows):
            self._row([f'{row.fecha:%d/%m/%Y %H:%M}', row.contacto_nombre or row.contacto_rfc or '',
                       row.destinatarios, 'Enviado' if row.estado == 'enviado' else 'Error'], index)
            if row.estado != 'enviado':
                self.table.item(index, 3).setToolTip(row.error or '')
        self.table.blockSignals(False)
        self.panel.set_mail(None, allow_dismiss=False)

    def on_select(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        key = self.table.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        if self.mode == PENDING:
            self.panel.set_mail(self.pending.get(key))
        else:
            self.load_resend(self.history_rows[key])

    # ---- reenvíos (independientes de la vigilancia) -----------------------------------
    def load_resend(self, row):
        xml, pdf = Path(row.xml_path), Path(row.pdf_path)
        if not xml.is_file() or not pdf.is_file():
            self.panel.set_mail(None, allow_dismiss=False)
            self.panel.info.setText(f'Los archivos ya no existen:\n{xml}\n{pdf}')
            return
        previous = contact_store.split_emails(row.destinatarios)
        self.load_files(xml, pdf, preselected=previous, allow_dismiss=False)

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Seleccione el XML de la factura',
                                              str(self.watch_dir or ''), 'XML (*.xml)')
        if not path: return
        pair = mailer.pair_for(Path(path))
        if pair is None:
            show_message(self, 'No se encontró un PDF con el mismo nombre junto al XML.',
                         icon=QMessageBox.Icon.Warning, title='Correos')
            return
        self.load_files(*pair, allow_dismiss=False)

    def load_files(self, xml, pdf, preselected=None, allow_dismiss=False):
        def work():
            with database_worker.new_session() as session:
                return mailer.analyze(session, xml, pdf)

        def done(mail):
            if mail is None:
                show_message(self, 'El XML no es una factura (CFDI) o no se pudo leer.',
                             icon=QMessageBox.Icon.Warning, title='Correos')
                return
            self.panel.set_mail(mail, preselected=preselected, allow_dismiss=allow_dismiss)

        self.tasks.run('panel', work, on_done=done, overlay=self.panel_loader, message='Leyendo factura...')

    # ---- acciones -----------------------------------------------------------------
    def dismiss(self):
        mail = self.panel.mail
        if mail is None: return
        self.dismissed.add(mail.key)
        self.pending.pop(mail.key, None)
        self.fill_pending()
        self.update_counts()

    def send(self):
        mail = self.panel.mail
        if mail is None or self.tasks.is_running('send'): return
        recipients, new = self.panel.recipients()
        invalid = [e for e in recipients if not contact_store.is_valid_email(e)]
        if not recipients or invalid:
            show_message(self, 'Correos no válidos: ' + ', '.join(invalid) if invalid
                         else 'Seleccione o escriba al menos un destinatario.',
                         icon=QMessageBox.Icon.Warning, title='Correos')
            return

        smtp = mailer.SmtpSettings.from_settings(settings)
        subject, body = self.panel.subject.text().strip(), self.panel.body.toPlainText()
        save_new = self.panel.save_contact.isChecked() and mail.cliente_id is not None and new

        def work():
            password = mailer.get_password(smtp.user)
            with database_worker.new_session() as session:
                if save_new:
                    from models import Cliente
                    client = session.get(Cliente, mail.cliente_id)
                    contact_store.upsert_contact_with_emails(session, client, mail.contacto_rfc,
                                                             mail.contacto_nombre, new)
                mailer.send_invoice(session, smtp, password, mail, recipients, subject, body)

        def done(_):
            self.panel.send_btn.setEnabled(True)
            self.pending.pop(mail.key, None)
            self.update_counts()
            toast(self, 'Correo enviado', detail=f'{mail.label} a {", ".join(recipients)}')
            self.load_data()

        def failed(error):
            self.panel.send_btn.setEnabled(True)
            logger.error(f'Correo no enviado: {error}')
            show_message(self, 'No se pudo enviar el correo.', detail=str(error), icon=QMessageBox.Icon.Warning,
                         title='Correos')

        self.panel.send_btn.setEnabled(False)
        self.tasks.run('send', work, on_done=done, on_error=failed, overlay=self.panel_loader,
                       message='Enviando correo...')
