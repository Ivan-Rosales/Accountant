from functools import cached_property

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QWidget, QScrollArea, QFrame, QMessageBox

from app.core.settings import settings
from app.settings import DEFAULT_THEME, DEFAULT_WORK_DIR, DEFAULT_DATABASE_DIR, DEFAULT_MAIL_DIR
from app.widgets.card import card
from app.widgets.color_picker import QThemePicker
from app.widgets.common import QButton
from app.widgets.file_selector import QDirSelector
from app.widgets.import_files import QImportWidget
from app.widgets.option_selector import QOptionSelector, QTextField
from app.widgets.switch import QSwitchField
from base.tab import TabWidget
from execution import mailer
from execution.mailer import SECURITIES, SECURITY_SSL
from app.core.tasks import TaskRunner
from app.widgets.period_selector import show_message
from app.widgets.toast import toast
from execution.month_summary import NOMINA_IMPORTES, NOMINA_NETO
from functions import get_icon
from logger import logger

DIOT_BASES = {'pagado': 'Pagado (flujo de efectivo)', 'facturado': 'Facturado (fecha de factura)'}
DIOT_EFECTOS = {'01': 'Sí', '02': 'No'}


class QConfiguration(TabWidget):
    change_configuration = Signal(str, object)
    layout_class = QVBoxLayout

    tooltip_label = 'configuración'
    page_title = 'Configuración'
    page_subtitle = 'Apariencia, rutas y reglas de cálculo'

    sections = {
        'apariencia': ('Apariencia', ''),
        'rutas': ('Rutas', 'Dónde se guardan los concentrados y la base de datos'),
        'calculo': ('Reglas de cálculo', 'Afectan a los concentrados y la DIOT que se generen a partir de ahora'),
        'correo': ('Correo', 'Envío de facturas: carpeta vigilada y cuenta SMTP. '
                             'La contraseña se guarda en el Administrador de credenciales de Windows.'),
    }

    fields = {
        'theme': {
            'section': 'apariencia',
            'label': 'Color del tema',
            'widget': QThemePicker,
            'default': DEFAULT_THEME,
        },
        'workdir': {
            'section': 'rutas',
            'label': 'Carpeta de concentrados',
            'widget': QDirSelector,
            'default': DEFAULT_WORK_DIR,
        },
        'dbdir': {
            'section': 'rutas',
            'label': 'Base de datos',
            'widget': QDirSelector,
            'default': DEFAULT_DATABASE_DIR,
        },
        'nomina-importe': {
            'section': 'calculo',
            'label': 'Nóminas en egresos',
            'widget': QOptionSelector,
            'options': NOMINA_IMPORTES,
            'default': NOMINA_NETO,
            'help': 'Neto pagado: total del recibo (como el programa anterior). '
                    'Percepciones: sueldo bruto antes de ISR retenido, IMSS y otras deducciones.',
        },
        'diot-base': {
            'section': 'calculo',
            'label': 'Base de la DIOT',
            'widget': QOptionSelector,
            'options': DIOT_BASES,
            'default': 'pagado',
            'help': 'Pagado: facturas PUE por su fecha y PPD por la fecha de su complemento de pago. '
                    'Facturado: todas las facturas por su fecha.',
        },
        'diot-efectos': {
            'section': 'calculo',
            'label': 'DIOT (campo 54)',
            'widget': QSwitchField,
            'text': 'Se dio efectos fiscales a los comprobantes',
            'values': ('01', '02'),
            'default': '01',
        },
        'mail-watch': {
            'section': 'correo',
            'label': 'Vigilancia',
            'widget': QSwitchField,
            'text': 'Detectar facturas nuevas en la carpeta (PDF + XML con el mismo nombre)',
            'values': ('true', 'false'),
            'default': 'true',
        },
        'mail-watchdir': {
            'section': 'correo',
            'label': 'Carpeta a vigilar',
            'widget': QDirSelector,
            'default': DEFAULT_MAIL_DIR,
        },
        'mail-host': {
            'section': 'correo',
            'label': 'Servidor SMTP',
            'widget': QTextField,
            'placeholder': 'smtp.gmail.com, smtp.office365.com...',
            'default': '',
        },
        'mail-security': {
            'section': 'correo',
            'label': 'Seguridad',
            'widget': QOptionSelector,
            'options': SECURITIES,
            'default': SECURITY_SSL,
        },
        'mail-port': {
            'section': 'correo',
            'label': 'Puerto',
            'widget': QTextField,
            'placeholder': '465 (SSL) o 587 (STARTTLS)',
            'default': '465',
        },
        'mail-user': {
            'section': 'correo',
            'label': 'Usuario (correo remitente)',
            'widget': QTextField,
            'placeholder': 'facturas@despacho.com',
            'default': '',
        },
        'mail-from-name': {
            'section': 'correo',
            'label': 'Nombre del remitente',
            'widget': QTextField,
            'placeholder': 'Despacho contable',
            'default': '',
        },
        'mail-password': {
            'section': 'correo',
            'label': 'Contraseña',
            'widget': QTextField,
            'secret': True,
            'placeholder': 'Contraseña de aplicación',
            'default': '',
            'help': 'Con Gmail u Outlook use una contraseña de aplicación. No se guarda en el archivo de configuración.',
        },
    }

    @cached_property
    def widgets(self):
        return {label: desc['widget'] for label, desc in self.fields.items() if desc.get('widget')}

    def create_ui(self):
        self.touched = {}
        self.tasks = TaskRunner(self)

        self.import_widget = QImportWidget(self)

        for label, description in self.fields.items():
            widget_class = description['widget']
            if isinstance(widget_class, QWidget):  # ya instanciado por otra ventana
                widget_class = type(widget_class)
            kwargs = {}
            if widget_class is QOptionSelector: kwargs = {'options': description['options']}
            if widget_class is QSwitchField: kwargs = {'text': description['text'], 'values': description['values']}
            if widget_class is QTextField:
                kwargs = {'secret': description.get('secret', False), 'placeholder': description.get('placeholder', '')}
            widget = widget_class(self, **kwargs)
            self.fields[label]['widget'] = widget
            try:
                self.set_value(widget, self.stored_value(label))
            except Exception:  # valor guardado inválido: se usa el default en silencio
                try:
                    self.set_value(widget, description.get('default'))
                except Exception:
                    pass
            self.set_on_change(label, widget)

        self.widgets['dbdir'].with_file('db.sqlite3')
        self.refresh_password_hint()

        self.label_version = QLabel(f'Versión {settings.version}', self)
        self.label_version.setProperty('class', 'secondary')

        self.label = QLabel('Hay cambios sin guardar', self)
        self.label.setProperty('class', 'invalid')
        self.label.hide()

        self.save_btn = QButton('guardar', self, fn=self.save_configuration)
        self.save_btn.setProperty('class', 'primary')

        self.discard_btn = QButton('descartar cambios', self, fn=self.discard_changes)
        self.discard_btn.setToolTip('Regresar a la configuración guardada')
        self.discard_btn.setEnabled(False)

        self.reset_btn = QButton(get_icon('recurring'), self, fn=self.reset_configuration, icon_opacity=0.5)
        self.reset_btn.setToolTip('Regresar a la configuración por defecto')
        self.reset_btn.setProperty('type', 'flat')

    def load_ui(self, layout: QVBoxLayout):
        content = QWidget(self)
        content.setObjectName('ScrollContent')
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 8, 0)
        content_layout.setSpacing(12)

        for key, (title, subtitle) in self.sections.items():
            frame, frame_layout = card(content, title, subtitle)
            for label, description in self.fields.items():
                if description['section'] != key: continue
                caption = QLabel(description['label'], frame)
                caption.setProperty('class', 'field-label')
                frame_layout.addWidget(caption)
                widget = description['widget']
                if help_text := description.get('help'):
                    widget.setToolTip(help_text)
                frame_layout.addWidget(widget)
                if help_text:
                    hint = QLabel(help_text, frame)
                    hint.setProperty('class', 'secondary')
                    hint.setWordWrap(True)
                    frame_layout.addWidget(hint)
            content_layout.addWidget(frame)

            if key == 'correo':
                self.test_mail_btn = QButton('probar conexión', frame, fn=self.test_mail)
                frame_layout.addWidget(self.test_mail_btn)

        frame, frame_layout = card(content, 'Importar', 'Trae los concentrados en Excel del programa anterior')
        frame_layout.addWidget(self.import_widget)
        content_layout.addWidget(frame)
        content_layout.addStretch(1)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        footer = QHBoxLayout()
        footer.addWidget(self.label_version)
        footer.addWidget(self.label)
        footer.addStretch(1)
        footer.addWidget(self.reset_btn)
        footer.addWidget(self.discard_btn)
        footer.addWidget(self.save_btn)
        layout.addLayout(footer)

    def on_change(self, label, value):
        if getattr(self, '_reverting', False): return
        self.touched[label] = value
        self.discard_btn.setEnabled(True)

        widget = self.widgets[label]
        widget.setProperty('class', 'invalid')
        self.label.show()

        if label == 'theme' and value:
            self.preview_theme(value)
            self.label.setText('Vista previa del tema: guarde para conservarlo')
        else:
            self.label.setText('Hay cambios sin guardar')

    def preview_theme(self, theme):
        """Aplica el tema a la ventana sin guardarlo (Guardar lo conserva, Descartar lo revierte)."""
        window = self.window()
        if hasattr(window, 'apply_theme'):
            window.apply_theme(theme)
        elif hasattr(window, 'load_qss'):
            window.load_qss(theme)

    def get_value(self, widget):
        if isinstance(widget, QDirSelector):
            return str(widget.get_path())
        if isinstance(widget, (QThemePicker, QOptionSelector, QSwitchField, QTextField)):
            return widget.get_value()

        logger.warning(f'{self.__class__.__name__} is not defined get_value for {widget.__class__.__name__}')
        return None

    def set_value(self, widget, value):
        if isinstance(widget, QDirSelector):
            widget.setPlaceholderText(value)
            widget.setPath(value)
        elif isinstance(widget, (QThemePicker, QOptionSelector, QSwitchField, QTextField)):
            widget.set_value(value)
        else:
            logger.warning(f'{self.__class__.__name__} is not defined set_value for {widget.__class__.__name__}')

    def set_on_change(self, label, widget):
        def changed(*_, l=label, w=widget):
            self.on_change(l, self.get_value(w))

        if isinstance(widget, QDirSelector):
            widget.changeDir.connect(changed)
        elif isinstance(widget, QThemePicker):
            widget.changeTheme.connect(changed)
        elif isinstance(widget, (QOptionSelector, QSwitchField, QTextField)):
            widget.changeOption.connect(changed)
        else:
            logger.warning(f'{self.__class__.__name__} is not defined set_on_change for {widget.__class__.__name__}')

    def reset_configuration(self):
        for label, description in self.fields.items():
            self.set_value(description.get('widget'), description.get('default'))

        logger.info(f'{self.__class__.__name__} reset configuration to default')

    def stored_value(self, label):
        description = self.fields[label]
        if description.get('secret'):
            return ''  # las contraseñas nunca se leen de vuelta al campo
        return settings.value(label) or description.get('default')

    def refresh_password_hint(self):
        widget = self.widgets.get('mail-password')
        if widget is None: return
        try:
            stored = bool(mailer.get_password(self.get_value(self.widgets['mail-user'])))
        except Exception:
            stored = False
        widget.setPlaceholderText('Guardada (escriba para reemplazarla)' if stored else 'Contraseña de aplicación')

    def save_configuration(self):
        for label, value in self.touched.items():
            if self.fields[label].get('secret'):
                if value:
                    try:
                        mailer.set_password(self.get_value(self.widgets['mail-user']), value)
                    except Exception as error:
                        show_message(self, f'No se pudo guardar la contraseña en Windows: {error}',
                                     icon=QMessageBox.Icon.Warning, title='Configuración')
                self.widgets[label].set_value('')
            else:
                settings.setValue(label, value)
                logger.debug(f'Change configuration {label} to {value}')
            self.change_configuration.emit(label, value)
            self.widgets[label].setProperty('class', None)

        self.refresh_password_hint()
        self.touched.clear()
        self.label.hide()
        self.discard_btn.setEnabled(False)
        logger.debug('Configuration saved')

    def discard_changes(self):
        """Vuelve a los valores guardados sin aplicar nada."""
        if 'theme' in self.touched:
            self.preview_theme(settings.value('theme') or self.fields['theme'].get('default'))
        self._reverting = True
        try:
            for label in list(self.touched):
                description = self.fields[label]
                self.set_value(description['widget'], self.stored_value(label))
                self.widgets[label].setProperty('class', None)
        finally:
            self._reverting = False
        self.touched.clear()
        self.label.hide()
        self.discard_btn.setEnabled(False)
        logger.info(f'{self.__class__.__name__} discarded changes')

    def get_conf_value(self, label):
        return self.get_value(self.widgets[label])

    def register_change(self, register, function):
        def wrapper(label, *args, **kwargs):
            if register == label: return function(*args, **kwargs)
            return None

        self.change_configuration.connect(wrapper)

    def test_mail(self):
        """Prueba la conexión con lo capturado (aunque no esté guardado)."""
        values = {key: self.get_value(self.widgets[key]) for key in
                  ('mail-host', 'mail-port', 'mail-security', 'mail-user', 'mail-from-name')}
        try:
            smtp = mailer.SmtpSettings(host=values['mail-host'], port=int(values['mail-port'] or 0),
                                       security=values['mail-security'], user=values['mail-user'],
                                       from_name=values['mail-from-name'])
            password = self.get_value(self.widgets['mail-password']) or mailer.get_password(smtp.user)
        except Exception as error:
            show_message(self, f'Revise los datos: {error}', icon=QMessageBox.Icon.Warning, title='Correo')
            return
        if not password:
            show_message(self, 'Capture la contraseña para probar la conexión.', icon=QMessageBox.Icon.Warning,
                         title='Correo')
            return

        self.test_mail_btn.setEnabled(False)
        self.test_mail_btn.setText('Probando...')

        def finish():
            self.test_mail_btn.setEnabled(True)
            self.test_mail_btn.setText('Probar conexión')

        def done(_):
            finish()
            toast(self, 'Conexión correcta', detail=f'{smtp.user} en {smtp.host}:{smtp.port}')

        def failed(error):
            finish()
            show_message(self, 'No se pudo conectar al servidor de correo.', detail=str(error),
                         icon=QMessageBox.Icon.Warning, title='Correo')

        self.tasks.run('test-mail', lambda: mailer.test_connection(smtp, password), on_done=done, on_error=failed)
