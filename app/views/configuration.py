from pathlib import Path

from PySide6.QtWidgets import QVBoxLayout, QLabel

from app.core.settings import DATABASE_DIR, WORKDIR, settings
from app.widgets.common import spacer, QButton
from app.widgets.file_selector import QDirSelector
from base.widget import BaseWidget
from logger import logger


class QConfiguration(BaseWidget):
    layout_class = QVBoxLayout
    margin = (5, 5, 5, 5)

    fields = [
        {
            'field': 'workdir', 'label': 'Ruta de trabajo',
            'component': QDirSelector, 'default': str(WORKDIR)
        },
        {
            'field': 'database_dir', 'label': 'Ruta de base de datos',
            'component': QDirSelector, 'default': str(DATABASE_DIR)
        },
    ]

    def create_ui(self):
        self._widgets = {}
        for definition in self.fields:
            field = definition.get('field')
            label = definition.get('label', field)
            component_class = definition.get('component')
            default = definition.get('default')

            label = QLabel(label, self)
            component = component_class(self)

            if hasattr(component_class, 'setPath'):
                component.setPath(default)

            if hasattr(component_class, 'setPlaceholderText'):
                component.setPlaceholderText(str(label))

            self._widgets[f'{field}_label'] = label
            self._widgets[field] = component

        self.save_btn = QButton('guardar', self, fn=self.on_save)
        self.save_btn.setProperty('class', 'primary')

    def load_ui(self, layout):
        layout.addItem(spacer)
        for widget in self._widgets.values():
            layout.addWidget(widget)
        layout.addItem(spacer)

        layout.addWidget(self.save_btn)

    def get_value(self, widget):
        if isinstance(widget, QDirSelector):
            return Path(widget.get_path())

        return None

    def on_save(self):
        widgets = {label: widget for label, widget in self._widgets.items() if not isinstance(widget, QLabel)}
        values = {label: self.get_value(widget) for label, widget in widgets.items()}

        for key, value in values.items():
            settings.setValue(key, str(value))
            logger.info(f'{key.capitalize()} {value} saved')


"""
    def validate_dbdir(self):
        print('validate_dbdir')
        raw_path = self.dbdir_edit.get_path()
        if raw_path is None: return
        path = str(raw_path)
        if not path.endswith(f'db.sqlite3'):
            path += '/db.sqlite3'
            self.dbdir_edit.setPath(path)

    def save(self):
        path = str(self.dbdir_edit.get_path())
        settings.setValue('database_dir', str(Path(path)))
        logger.info(f'Database directory {path} saved')

        path = self.workdir_edit.get_path()
        settings.setValue('workdir', str(Path(path)))
        logger.info(f'Working directory {path} saved')
"""
