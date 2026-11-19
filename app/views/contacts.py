"""Pestaña Contactos: clientes de mi cliente y sus correos."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
                               QListWidget, QLabel, QAbstractItemView, QMessageBox, QFrame)

from app.core.tasks import TaskRunner
from app.widgets.common import QButton
from app.widgets.confirm_box import confirm_delete
from app.widgets.loader import QLoadingOverlay
from app.widgets.period_selector import show_message
from app.widgets.toast import toast
from app.workers.database import database_worker
from base.dialog import BaseDialog
from base.tab import TabWidget
from base.widget import BaseWidget
from execution import contacts as store


class QContactForm(BaseWidget):
    """Formulario del modal de alta/edición de contacto."""
    layout_class = QVBoxLayout
    windows_size = None
    spacing = 6
    saved = Signal()

    def create_ui(self):
        self.contact_id = None
        self.client = None
        self.rfc = QLineEdit(self)
        self.rfc.setPlaceholderText('RFC')
        self.rfc.setMaxLength(13)
        self.rfc.textEdited.connect(lambda text: self.rfc.setText(text.upper()))
        self.nombre = QLineEdit(self)
        self.nombre.setPlaceholderText('Nombre o razón social')
        self.emails = QLineEdit(self)
        self.emails.setPlaceholderText('correo@empresa.com; otro@empresa.com')
        self.error = QLabel(self)
        self.error.setProperty('class', 'invalid')
        self.error.setWordWrap(True)
        self.error.hide()
        self.cancel_btn = QButton('cancelar', self, fn=lambda: self.parent().hide())
        self.save_btn = QButton('guardar', self, fn=self.on_save)
        self.save_btn.setProperty('class', 'primary')
        for field in (self.rfc, self.nombre, self.emails):
            field.returnPressed.connect(self.on_save)

    def load_ui(self, layout):
        for text, widget in (('RFC', self.rfc), ('Nombre', self.nombre), ('Correos (opcional)', self.emails)):
            label = QLabel(text, self)
            label.setProperty('class', 'field-label')
            layout.addWidget(label)
            layout.addWidget(widget)
        layout.addWidget(self.error)
        layout.addSpacing(10)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.cancel_btn)
        buttons.addWidget(self.save_btn)
        layout.addLayout(buttons)

    def set_contact(self, client, contact=None):
        self.client = client
        if contact is not None:
            self.contact_id = contact.id
            self.rfc.setText(contact.rfc)
            self.nombre.setText(contact.nombre)
            self.emails.hide()

    def on_save(self):
        try:
            with database_worker.new_session() as session:
                contact = store.save_contact(session, self.client, self.rfc.text(), self.nombre.text(), self.contact_id)
                invalid = store.add_emails(session, contact.id, store.split_emails(self.emails.text())) \
                    if self.emails.isVisible() else []
        except ValueError as error:
            self.error.setText(str(error))
            self.error.show()
            return
        if invalid:
            show_message(self, 'Se guardó el contacto, pero estos correos no son válidos:\n' + '\n'.join(invalid),
                         icon=QMessageBox.Icon.Warning, title='Correos no válidos')
        self.saved.emit()
        self.parent().hide()


class QContacts(TabWidget):
    layout_class = QHBoxLayout
    tooltip_label = 'contactos de cada cliente'
    page_title = 'Contactos'
    page_subtitle = 'Clientes de su cliente y los correos a los que se les envían sus facturas'

    @property
    def client_selector(self):
        return getattr(self.parent(), 'client_selector')

    def create_ui(self):
        self.contacts: list[store.ContactView] = []
        self.tasks = TaskRunner(self)

        # Contactos
        self.search = QLineEdit(self)
        self.search.setPlaceholderText('Buscar por RFC o nombre...')
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.filter_rows)
        self.new_btn = QButton('nuevo contacto', self, fn=self.create_contact)
        self.new_btn.setProperty('class', 'primary')
        self.edit_btn = QButton('editar', self, fn=self.edit_contact)
        self.delete_btn = QButton('eliminar', self, fn=self.delete_contacts)

        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['RFC', 'Nombre', 'Correos'])
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self.on_select)
        self.table.doubleClicked.connect(lambda *_: self.edit_contact())
        self.loader = QLoadingOverlay(self.table)

        # Correos del contacto seleccionado
        self.emails_title = QLabel('Correos', self)
        self.emails_title.setProperty('class', 'card-title')
        self.emails_hint = QLabel('Seleccione un contacto', self)
        self.emails_hint.setProperty('class', 'secondary')
        self.email_list = QListWidget(self)
        self.email_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.email_list.itemSelectionChanged.connect(self.on_email_select)
        self.email_input = QLineEdit(self)
        self.email_input.setPlaceholderText('nuevo@correo.com; otro@correo.com')
        self.email_input.returnPressed.connect(self.add_emails)
        self.add_email_btn = QButton('agregar', self, fn=self.add_emails)
        self.add_email_btn.setProperty('class', 'primary')
        self.remove_email_btn = QButton('quitar seleccionados', self, fn=self.remove_emails)

        self.client_selector.on_change(self.request_load)
        self.on_select()

    def load_ui(self, layout):
        left = QVBoxLayout()
        top = QHBoxLayout()
        top.addWidget(self.search, 1)
        top.addWidget(self.edit_btn)
        top.addWidget(self.delete_btn)
        top.addWidget(self.new_btn)
        left.addLayout(top)
        left.addWidget(self.table, 1)
        layout.addLayout(left, 3)

        panel = QFrame(self)
        panel.setProperty('class', 'card')
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 14, 16, 16)
        panel_layout.addWidget(self.emails_title)
        panel_layout.addWidget(self.emails_hint)
        panel_layout.addWidget(self.email_list, 1)
        row = QHBoxLayout()
        row.addWidget(self.email_input, 1)
        row.addWidget(self.add_email_btn)
        panel_layout.addLayout(row)
        panel_layout.addWidget(self.remove_email_btn)
        layout.addWidget(panel, 2)

    # ---- datos ------------------------------------------------------------------
    def load_data(self, *_):
        client = self.client_selector.get_current()
        if client is None:
            self.contacts = []
            self.fill_table()
            return

        def query():
            with database_worker.new_session() as session:
                return store.list_contacts(session, client)

        self.tasks.run('load', query, on_done=self.show_contacts, overlay=self.loader, message='Cargando contactos...')

    def show_contacts(self, contacts, keep_id=None):
        keep_id = keep_id or (self.current_contact().id if self.current_contact() else None)
        self.contacts = contacts
        self.fill_table(keep_id)

    def fill_table(self, keep_id=None):
        self.table.setRowCount(0)
        for row, contact in enumerate(self.contacts):
            self.table.insertRow(row)
            for column, value in enumerate((contact.rfc, contact.nombre, str(len(contact.emails)))):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, contact.id)
                self.table.setItem(row, column, item)
            if contact.id == keep_id:
                self.table.selectRow(row)
        self.filter_rows(self.search.text())
        self.on_select()

    def filter_rows(self, text):
        text = (text or '').lower()
        for row, contact in enumerate(self.contacts):
            haystack = f'{contact.rfc} {contact.nombre} {" ".join(contact.emails)}'.lower()
            self.table.setRowHidden(row, bool(text) and text not in haystack)

    def selected_contacts(self) -> list[store.ContactView]:
        rows = sorted({i.row() for i in self.table.selectionModel().selectedRows()})
        return [self.contacts[r] for r in rows if r < len(self.contacts)]

    def current_contact(self):
        selected = self.selected_contacts()
        return selected[0] if len(selected) == 1 else None

    def on_select(self):
        selected = self.selected_contacts()
        self.edit_btn.setEnabled(len(selected) == 1)
        self.delete_btn.setEnabled(bool(selected))
        contact = self.current_contact()
        enabled = contact is not None
        for widget in (self.email_input, self.add_email_btn, self.email_list):
            widget.setEnabled(enabled)
        self.email_list.clear()
        if contact is None:
            self.emails_title.setText('Correos')
            self.emails_hint.setText('Seleccione un contacto' if not selected else 'Seleccione solo un contacto')
        else:
            self.emails_title.setText(f'Correos de {contact.nombre or contact.rfc}')
            self.emails_hint.setText(contact.rfc)
            self.email_list.addItems(contact.emails)
        self.on_email_select()

    def on_email_select(self):
        self.remove_email_btn.setEnabled(bool(self.email_list.selectedItems()))

    # ---- acciones ---------------------------------------------------------------
    def open_form(self, contact=None):
        client = self.client_selector.get_current()
        if client is None:
            show_message(self, 'Seleccione un cliente', icon=QMessageBox.Icon.Warning, title='Contactos')
            return
        title = 'Editar contacto' if contact else 'Nuevo contacto'
        dialog = BaseDialog(self, widget=QContactForm, title=title, uuid=f'contact-{contact.id if contact else "new"}')
        dialog.widget.set_contact(client, contact)
        dialog.widget.saved.connect(self.load_data)
        dialog.show()

    def create_contact(self):
        self.open_form()

    def edit_contact(self):
        if contact := self.current_contact():
            self.open_form(contact)

    def delete_contacts(self):
        selected = self.selected_contacts()
        if not selected: return
        if not confirm_delete(self, [str(c) for c in selected], what='contacto',
                              detail='También se eliminan sus correos.'):
            return

        def work():
            with database_worker.new_session() as session:
                store.delete_contacts(session, [c.id for c in selected])

        self.tasks.run('delete', work, on_done=lambda _: (self.load_data(), toast(
            self, 'Contactos eliminados', detail=f'{len(selected)} contacto(s)')), overlay=self.loader,
            message='Eliminando...')

    def add_emails(self):
        contact = self.current_contact()
        emails = store.split_emails(self.email_input.text())
        if contact is None or not emails: return
        invalid = [e for e in emails if not store.is_valid_email(e)]
        if invalid:
            show_message(self, 'Estos correos no son válidos:\n' + '\n'.join(invalid),
                         icon=QMessageBox.Icon.Warning, title='Correos no válidos')
            return

        def work():
            with database_worker.new_session() as session:
                store.add_emails(session, contact.id, emails)

        self.email_input.clear()
        contact.emails = sorted(set(contact.emails) | set(emails))  # respuesta inmediata
        self.on_select()
        self.tasks.run('emails', work, on_done=lambda _: self.load_data())

    def remove_emails(self):
        contact = self.current_contact()
        emails = [i.text() for i in self.email_list.selectedItems()]
        if contact is None or not emails: return
        if not confirm_delete(self, emails, what='correo'): return

        def work():
            with database_worker.new_session() as session:
                store.remove_emails(session, contact.id, emails)

        contact.emails = [e for e in contact.emails if e not in emails]
        self.on_select()
        self.tasks.run('emails', work, on_done=lambda _: self.load_data())
