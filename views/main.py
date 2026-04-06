from PySide6.QtCore import QThread
from PySide6.QtWidgets import QGridLayout, QVBoxLayout, QWidget

import settings
from app.core.base_view import BaseView
from app.widgets.common import spacer, QButton
from app.widgets.debug_tools import QDebugTools
from app.widgets.selector_model import QSelectorModel
from core.database import database_worker
from core.functions import get_icon
from core.models import Cliente
from views.client_admin import QClientAdmin
from views.month_summary_widget import QMonthSummary


class MainView(BaseView):
    layout_class = QGridLayout
    windows_size = (800, 400)
    margin = (0, 32, 0, 0)
    spacing = 0

    def __init__(self, *args, **kwargs):
        self.db_thread = QThread()
        self.db_worker = database_worker
        self.db_worker.moveToThread(self.db_thread)
        self.db_thread.start()

        self.tabs = {}
        self.active_tab = None
        super().__init__(*args, **kwargs)

    def create_ui(self):
        self.debug_tools = QDebugTools(self)
        self.client_selector = QSelectorModel(self, context={'model': Cliente})

        self.header_layout = QVBoxLayout()
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

        if settings.DEBUG:
            layout.addWidget(self.header, 0, 0, 1, 2)

        layout.addWidget(self.buttons, 1, 0)

        self.add_tab(get_icon('month'), QMonthSummary())
        self.add_tab(get_icon('user'), QClientAdmin())
        self.buttons_layout.addItem(spacer)
        self.set_current_tab(0)

    def add_tab(self, desc, widget):
        btn = QButton(desc, self, fn=lambda _, key=desc: self.change_current_tab(key))
        btn.setProperty('class', 'secondary')

        self.buttons_layout.addWidget(btn)
        self.tabs[desc] = (btn, widget)

        self._layout.addWidget(widget, 1, 1)
        widget.hide()

    def set_current_tab(self, index):
        key = None
        if isinstance(index, int):
            key = list(self.tabs.keys())[index]
        if isinstance(index, str):
            key = index

        if key is None: return
        self.change_current_tab(key)

    def setPropertyUpddate(self, widget, key, value):
        widget.setProperty(key, value)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    def change_current_tab(self, active):
        to_active_btn = None
        to_show_widget = None

        for key, (btn, widget) in self.tabs.items():
            if key == active:
                to_active_btn = btn
                to_show_widget = widget
            else:
                self.setPropertyUpddate(btn, 'state', '')
                widget.hide()

        if to_active_btn and to_show_widget:
            self.setPropertyUpddate(to_active_btn, 'state', 'active')
            to_show_widget.show()
