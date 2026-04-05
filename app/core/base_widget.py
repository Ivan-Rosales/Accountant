from PySide6.QtWidgets import QWidget

from app.mixin.loadui_mixin import LoadUiMixin


class BaseWidget(LoadUiMixin, QWidget):
    def __init__(self, *args, **kwargs):
        self.context = kwargs.pop('context', {})
        super().__init__(*args, **kwargs)

        self._dialog = {}

    def get_context(self):
        context = self.context

        parent = self.parent()
        while parent:
            if hasattr(parent, 'context'):
                context.update(parent.context)
            parent = parent.parent()

        return self.context
