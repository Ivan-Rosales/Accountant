import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QFrame
from PySide6.QtWidgets import QSpacerItem, QSizePolicy
from qframelesswindow import FramelessWindow

_, exe_url, exe_path, last_version = sys.argv


class DownloadWorker(QObject):
    exc_download = Signal(Path, str)
    exc_replace = Signal(Path, object)

    progress = Signal(float)
    downloaded = Signal()
    updated = Signal()

    def download_app(self, path: Path, url):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as response:
                total = int(response.getheader("Content-Length", 0))
                chunk_size = 8192
                downloaded = 0

                with open(path.absolute(), "wb") as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break

                        f.write(chunk)
                        downloaded += len(chunk)

                        if total > 0:
                            percent = downloaded / total
                            self.progress.emit(float(percent * 100))
        finally:
            self.downloaded.emit()

    def replace_app(self, path: Path, func):
        for i in range(1, 120):
            func(f'Update attempt {i}')

            try:
                shutil.move(path, exe_path)
                break
            except:
                time.sleep(2)

        self.updated.emit()


class QLogger(QFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setObjectName("logs")

        self.setStyleSheet("#logs { border: 1px solid #444; border-radius: 8px; }")

        layout = QVBoxLayout(self)

        self.pre_label_2 = QLabel(self)
        self.pre_label_2.setStyleSheet('color: #333')
        layout.addWidget(self.pre_label_2)

        self.pre_label_1 = QLabel(self)
        self.pre_label_1.setStyleSheet('color: #555')
        layout.addWidget(self.pre_label_1)

        self.last_label = QLabel(self)
        layout.addWidget(self.last_label)

    def setText(self, text):
        self.pre_label_2.setText(self.pre_label_1.text())
        self.pre_label_1.setText(self.last_label.text())
        self.last_label.setText(text)


class UpdaterWindow(FramelessWindow):
    def __init__(self):
        super().__init__()
        self.version = last_version
        self.updated = False

        self.setFixedSize(501, 201)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 42, 10, 10)

        self.title = QLabel(self)
        layout.addWidget(self.title)

        spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout.addItem(spacer)
        self.label = QLogger(self)
        layout.addWidget(self.label)
        layout.addItem(spacer)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        self.thread = QThread()
        self.worker = DownloadWorker()
        self.worker.moveToThread(self.thread)
        self.worker.exc_download.connect(self.worker.download_app)
        self.worker.exc_replace.connect(self.worker.replace_app)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.downloaded.connect(self.on_downloaded)
        self.worker.updated.connect(self.on_updated)
        self.thread.start()

        title = f'Update available {self.version}'
        self.title.setText(title)
        self.label.setText(title)

        # launch downloading exe file
        self.path = Path('updated.exe')
        self.label.setText(f'Downloading... {self.version}')
        self.worker.exc_download.emit(self.path, exe_url)

    def on_error(self):
        self.thread.quit()

    def on_downloaded(self):
        if not self.path.is_file():
            self.thread.quit()
            return

        self.label.setText(f'Downloaded {self.path.absolute()}')

        # launch updating exe file
        self.label.setText(f'Updating... {self.version}')
        self.worker.exc_replace.emit(self.path, self.label.setText)

    def on_updated(self):
        self.label.setText(f'Updated {self.version} successfully')
        self.updated = True
        self.thread.quit()

    def closeEvent(self, event):
        super().closeEvent(event)
        if not self.updated: return
        subprocess.Popen([exe_path])


app = QtWidgets.QApplication([])

widget = UpdaterWindow()
widget.show()

sys.exit(app.exec())
