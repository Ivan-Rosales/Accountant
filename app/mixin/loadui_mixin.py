from PySide6.QtWidgets import QHBoxLayout, QBoxLayout

from app.logs.logger import logger


class LoadUiMixin:
    layout_class = QHBoxLayout

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.create_ui()

        layout = self.layout_class(self)
        self.load_ui(layout)

        if hasattr(self, 'titleBar'):
            self.titleBar.raise_()

        if hasattr(self, 'loaded_ui'):
            self.loaded_ui()

    def create_ui(self):
        logger.warn(f'create_ui is not implemented on {self.__class__.__name__}')

    def load_ui(self, layout: QBoxLayout):
        logger.warn(f'load_ui is not implemented on {self.__class__.__name__}')
