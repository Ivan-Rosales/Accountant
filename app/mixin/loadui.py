from PySide6.QtWidgets import QHBoxLayout, QBoxLayout

from logger import logger


class LoadUiMixin:
    layout_class = QHBoxLayout
    windows_size = (700, 300)
    margin = (0, 0, 0, 0)
    spacing = 4

    _layout = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.create_ui()

        self._layout = self.layout_class(self)
        self._layout.setContentsMargins(*self.margin)
        self._layout.setSpacing(self.spacing)
        self.load_ui(self._layout)

        if self.windows_size is not None:
            self.resize(*self.windows_size)

        if hasattr(self, 'titleBar'):
            self.titleBar.raise_()

        if hasattr(self, 'loaded_ui'):
            self.loaded_ui()

    def create_ui(self):
        logger.warn(f'create_ui is not implemented on {self.__class__.__name__}')

    def load_ui(self, layout: QBoxLayout):
        logger.warn(f'load_ui is not implemented on {self.__class__.__name__}')
