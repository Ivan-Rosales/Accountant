import os

from PySide6.QtWidgets import QGridLayout, QVBoxLayout, QWidget

from app import settings as app_settings
from app.core.settings import settings
from app.views.client_admin import QClientAdmin
from app.views.configuration import QConfiguration
from app.views.month_summary import QMonthSummary
from app.views.year_summary import QYearSummary
from app.widgets.common import spacer, QButton
from app.widgets.debug_tools import QDebugTools
from app.widgets.selector_model import QSelectorModel
from app.workers.database import database_worker
from base.window import BaseWindow
from functions import get_icon
from models import Cliente


class MainWindow(BaseWindow):
    layout_class = QGridLayout
    windows_size = (801, 401)
    margin = (0, 32, 0, 0)
    spacing = 0

    tabs = {
        'text-file': QMonthSummary,
        'bar-char': QYearSummary,
        'user': QClientAdmin,
        'gear': QConfiguration,
    }

    _load_qs = False

    def __init__(self, *args, **kwargs):
        self._tabs = {}
        self.active_tab = None
        super().__init__(*args, **kwargs)

        settings.register_setting('main-tab', lambda: self.active_tab, self.change_current_tab, 'gear')

    def create_ui(self):
        self.client_selector = QSelectorModel(self, context={'model': Cliente})

        self.header_layout = QGridLayout()
        self.header_layout.setColumnStretch(0, 1)

        if app_settings.DEBUG:
            self.debug_tools = QDebugTools(self)
            self.header_layout.addWidget(self.debug_tools, 0, 0, 1, 2)

        self.header_layout.addWidget(self.client_selector, 1, 0)

        self.folder_btn = QButton(get_icon('folder'), self, fn=self.open_path)
        self.folder_btn.setToolTip('abrir carpeta del cliente'.capitalize())
        self.header_layout.addWidget(self.folder_btn, 1, 1)

        self.header_layout.setContentsMargins(5, 5, 5, 5)

        self.header = QWidget()
        self.header.setObjectName("MainHeader")
        self.header.setLayout(self.header_layout)

        self.buttons_layout = QVBoxLayout()
        self.buttons_layout.setContentsMargins(0, 5, 5, 5)
        self.buttons_layout.setSpacing(5)
        self.buttons = QWidget()
        self.buttons.setObjectName("MainButtons")
        self.buttons.setLayout(self.buttons_layout)

    def load_ui(self, layout: QGridLayout):
        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 1)
        layout.setRowStretch(0, 0)
        layout.setRowStretch(1, 1)

        layout.addWidget(self.header, 0, 0, 1, 2)

        layout.addWidget(self.buttons, 1, 0)

        for name, widget in self.tabs.items():
            if name == 'gear':
                self.buttons_layout.addItem(spacer)

            self.add_tab(name, widget(self))

        conf = self.get_widget_tab('gear')
        conf.register_change('dbdir', database_worker.reset)
        conf.register_change('theme', self.load_qss)
        self.load_qss(conf.get_conf_value('theme'))
        self.header.setFocus()

    def get_widget_tab(self, name):
        _, widget = self._tabs[name]
        return widget

    def add_tab(self, name, widget):
        icon = get_icon(name)
        btn = QButton(icon, self, fn=lambda _, key=name: self.change_current_tab(key))

        if tooltip_label := getattr(widget, 'tooltip_label', None):
            btn.setToolTip(tooltip_label.capitalize())

        self.buttons_layout.addWidget(btn)
        self._tabs[name] = (btn, widget)

        self._layout.addWidget(widget, 1, 1)
        widget.hide()

    def change_current_tab(self, active):
        to_active_btn = None
        to_show_widget = None

        for key, (btn, widget) in self._tabs.items():
            if key == active:
                to_active_btn = btn
                to_show_widget = widget
                self.active_tab = active
            else:
                self.setPropertyUpddate(btn, 'state', '')
                widget.hide()

        if to_active_btn and to_show_widget:
            self.setPropertyUpddate(to_active_btn, 'state', 'active')
            to_show_widget.show()

    def open_path(self):
        client = self.client_selector.get_current()
        if client is None: return
        path = settings.get_workdir() / client.rfc
        path.mkdir(parents=True, exist_ok=True)
        if path.is_dir():
            os.startfile(path)
