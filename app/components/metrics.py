from datetime import datetime

from PySide6.QtWidgets import QLabel

from app.core.base_widget import BaseWidget
from app.mixin.database_mixin import DatabaseMixin
from db.models import Metrics


class QMetrics(DatabaseMixin, BaseWidget):
    def create_ui(self):
        self.counter = QLabel(self)
        self.update_metrics(0)

    def load_ui(self, layout):
        layout.addWidget(self.counter)

    def update_metrics(self, new_registers=1):
        self.execute_db(lambda: self.get_metrics(new_registers), {'success': self.on_update_metrics})

    async def get_metrics(self, new_registers):
        instances = await Metrics.all()

        today = datetime.today().date()
        instance, _ = await Metrics.get_or_create(fecha=today)
        instance.registers += new_registers
        await instance.save()

        return instances, instance

    def on_update_metrics(self, data):
        metrics, today_metrics = data
        self.counter.setText(f'{today_metrics.registers} registros')
