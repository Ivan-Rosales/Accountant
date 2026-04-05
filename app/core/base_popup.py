from PySide6.QtWidgets import QMessageBox


class QDialogException(Exception):
    def __init__(self, *args, **kwargs):
        self.icon = kwargs.get('icon', QMessageBox.Icon.Warning)
        self.title = kwargs.get('title', 'Precaución')
        self.format = kwargs.get('format', True)

        args = list(args)
        self.parent = args.pop(0)
        super().__init__(*args)

    def get_text(self):
        return super().__str__()
