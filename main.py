from PySide6.QtWidgets import QGridLayout, QVBoxLayout, QWidget

from app import settings as app_settings
from app.core.settings import settings
from app.views.client_admin import QClientAdmin
from app.views.month_summary import QMonthSummary
from app.views.year_summary import QYearSummary
from app.widgets.common import spacer, QButton
from app.widgets.debug_tools import QDebugTools
from app.widgets.selector_model import QSelectorModel
from base.window import BaseWindow
from functions import get_icon
from models import Cliente


class MainWindow(BaseWindow):
    layout_class = QGridLayout
    windows_size = (800, 400)
    margin = (0, 32, 0, 0)
    spacing = 0

    tabs = {
        'report-3': QMonthSummary,
        'report': QYearSummary,
        'user': QClientAdmin,
    }

    def __init__(self, *args, **kwargs):
        self._tabs = {}
        self.active_tab = None
        super().__init__(*args, **kwargs)

        default_tab = get_icon('report-3')
        settings.register_setting('main-tab', lambda: self.active_tab, self.change_current_tab, default_tab)

    def create_ui(self):
        self.client_selector = QSelectorModel(self, context={'model': Cliente})

        self.header_layout = QVBoxLayout()

        if app_settings.DEBUG:
            self.debug_tools = QDebugTools(self)
            self.header_layout.addWidget(self.debug_tools)

        self.header_layout.addWidget(self.client_selector)
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
            self.add_tab(get_icon(name), widget(self))

        self.buttons_layout.addItem(spacer)

    def add_tab(self, desc, widget):
        btn = QButton(desc, self, fn=lambda _, key=desc: self.change_current_tab(key))
        btn.setProperty('class', 'secondary')

        self.buttons_layout.addWidget(btn)
        self._tabs[desc] = (btn, widget)

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
