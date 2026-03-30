from PySide6.QtWidgets import QPushButton


class QButton(QPushButton):
    def __init__(self, *args, **kwargs):
        fn = kwargs.pop('fn', None)
        super().__init__(*args, **kwargs)
        if callable(fn): self.clicked.connect(fn)
