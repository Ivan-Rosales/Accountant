from matplotlib import dates
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from app.core.base_widget import BaseWidget
from core.models import Metrica


class QMetricsGraph(BaseWidget):
    margin = (5, 5, 5, 5)

    def create_ui(self):
        self.figure = Figure()
        self.figure.patch.set_alpha(0)

        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setStyleSheet("background: transparent;")
        Metrica.connect_func(self.load_metrics)

    def load_ui(self, layout):
        layout.addWidget(self.canvas)

    def load_metrics(self, instances):
        self.figure.clear()

        ax = self.figure.add_subplot(111)
        ax.set_facecolor("none")

        data = {i.fecha: i.registers for i in instances}

        ax.clear()
        ax.plot(data.keys(), data.values(), color='#0d6efd')
        ax.set_ylim(bottom=0)

        ax.xaxis.set_major_formatter(dates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(dates.AutoDateLocator())
        self.figure.autofmt_xdate()

        ax.tick_params(axis='x', colors='#51585e')
        ax.tick_params(axis='y', colors='#51585e')

        for spine in ax.spines.values():
            spine.set_color('#51585e')

        self.canvas.draw()
