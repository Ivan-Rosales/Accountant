from datetime import datetime

from PySide6.QtWidgets import QLabel

from app.core.base_widget import BaseWidget
from core.models import Metrica


class QMetrics(BaseWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.today_metrics: Metrica | None = None

    def create_ui(self):
        self.counter = QLabel(self)
        self.counter.setProperty('class', 'secondary')
        Metrica.get_or_create(fecha=datetime.now().date())
        Metrica.connect_func(self.load_instances)

    def load_ui(self, layout):
        layout.addWidget(self.counter)

    def load_instances(self, instances):
        today = datetime.now().date()
        today_metrics = next(iter([i for i in instances if i.fecha == today]), None)
        if not today_metrics: return

        self.today_metrics = today_metrics
        self.counter.setText(f'{self.today_metrics.registers} registros')

    def add_registers_today(self, count):
        self.today_metrics.registers += count
        self.today_metrics.save()
