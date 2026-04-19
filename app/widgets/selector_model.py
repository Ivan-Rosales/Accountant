from pathlib import Path

from PySide6.QtCore import Qt, Signal, QStringListModel, QTimer
from PySide6.QtWidgets import QComboBox, QCompleter

from app.core.settings import settings
from app.mixin.model import ModelMixin
from app.settings import QSS_PATH
from base.widget import BaseWidget


class QSelectorModel(ModelMixin, BaseWidget):
    start_signal = Signal()

    def create_ui(self):
        self.searching = False
        self.lazy_current = None
        self.list = QComboBox(self)
        self.list.setEditable(True)
        self.list.lineEdit().editingFinished.connect(self.reset_text)
        self.list.focusInEvent = self.on_focus_in
        self.list.focusOutEvent = self.on_focus_out

        self.completer = QCompleter(self)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.list.setCompleter(self.completer)
        self.completer.complete()
        raw_style_sheet = Path(QSS_PATH).with_name('combo_box.qss').read_text()
        style_sheet = raw_style_sheet.replace('QComboBox ', '')
        style_sheet = style_sheet[style_sheet.index('}') + 1:]
        self.completer.popup().setStyleSheet(style_sheet)
        self.completer.popup().hide()

        parent = self.parent()
        parent_name = parent.__class__.__name__
        getter = lambda: getattr(self.get_current(), 'id', None)
        setting_key = f'{parent_name}.selector_{self.model.__name__}'.lower()
        settings.register_setting(setting_key, getter, self.set_lazy_current, 0)
        self.model.on_change(self.load_instances)

    def load_ui(self, layout):
        layout.addWidget(self.list)

    def on_focus_in(self, event):
        QComboBox.focusInEvent(self.list, event)

        if self.searching: return
        self.searching = True
        QTimer.singleShot(0, self.list.lineEdit().selectAll)

    def on_focus_out(self, event):
        QComboBox.focusOutEvent(self.list, event)
        self.searching = False

    def reset_text(self):
        self.searching = False
        if current_data := self.list.currentData():
            self.list.lineEdit().setText(str(current_data))

    def on_change(self, func):
        def wrapper(index):
            return func(self.list.itemData(index))

        self.list.currentIndexChanged.connect(wrapper)

    def get_current(self):
        return self.list.currentData()

    def set_lazy_current(self, pk):
        self.lazy_current = int(pk)

    def load_instances(self, instances):
        self.list.clear()
        labels = []

        for instance in instances:
            self.list.addItem(str(instance), instance)
            labels.append(str(instance))

            if instance.id == self.lazy_current:
                index = self.list.findData(instance)
                self.list.setCurrentIndex(index)

        self.completer.setModel(QStringListModel(labels, self.completer))
