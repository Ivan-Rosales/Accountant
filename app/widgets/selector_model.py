from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox

from app.core.settings import QSettings
from app.mixin.model import ModelMixin
from base.widget import BaseWidget


class QSelectorModel(ModelMixin, BaseWidget):
    start_signal = Signal()

    def create_ui(self):
        self.list = QComboBox(self)
        self.list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.list.view()

        self.model.on_change(self.load_instances)
        self.lazy_current = None

        parent = self.parent()
        parent_name = parent.__class__.__name__
        getter = lambda: getattr(self.get_current(), 'id', None)
        setting_key = f'{parent_name}.selector_{self.model.__name__}'.lower()

        app_settings = QSettings()
        app_settings.register_setting(setting_key, getter, self.set_lazy_current, 0)

    def on_change(self, func):
        def wrapper(index):
            return func(self.list.itemData(index))

        self.list.currentIndexChanged.connect(wrapper)

    def load_ui(self, layout):
        layout.addWidget(self.list)

    def get_current(self):
        return self.list.currentData()

    def set_lazy_current(self, pk):
        self.lazy_current = int(pk)

    def load_instances(self, instances):
        self.list.clear()

        for instance in instances:
            self.list.addItem(str(instance), instance)

            if instance.id == self.lazy_current:
                index = self.list.findData(instance)
                self.list.setCurrentIndex(index)
