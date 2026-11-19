from base.widget import BaseWidget


class TabWidget(BaseWidget):
    margin = (20, 4, 20, 16)
    spacing = 12

    tooltip_label = None
    page_title = ''
    page_subtitle = ''

    _stale = True

    def request_load(self, *_):
        """Carga ahora si la pestaña está visible; si no, al mostrarse (no se trabaja en pestañas ocultas)."""
        if self.isVisible():
            self._stale = False
            self.load_data()
        else:
            self._stale = True

    def showEvent(self, event):
        super().showEvent(event)
        if self._stale and hasattr(self, 'load_data'):
            self._stale = False
            self.load_data()
