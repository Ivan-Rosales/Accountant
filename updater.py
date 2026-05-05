import shutil
import sys
import time
import urllib.request
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QLabel, QHBoxLayout, QProgressBar
from qframelesswindow import FramelessWindow

try:
    _, exe_url, exe_path, parent_pid, last_version = sys.argv
except Exception as e:
    exe_url = exe_path = parent_pid = last_version = None


class DownloadWorker(QObject):
    start = Signal()
    progress = Signal(float)
    end = Signal(object)

    def download_app(self):
        try:
            path = Path('updated.exe')

            req = urllib.request.Request(exe_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as response:
                total = int(response.getheader("Content-Length", 0))
                downloaded = 0
                chunk_size = 8192

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

            self.end.emit(path)
        except:
            self.end.emit(None)


class UpdaterWindow(FramelessWindow):
    def __init__(self):
        super().__init__()

        layout = QHBoxLayout(self)

        self.label = QLabel(f'Update available {last_version}', self)
        layout.addWidget(self.label)

        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)

        self.download_app()

    def download_app(self):
        self.thread = QThread()
        self.worker = DownloadWorker()
        self.worker.moveToThread(self.thread)
        self.worker.start.connect(self.worker.download_app)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.end.connect(self.on_end)
        self.thread.start()

        self.worker.start.emit()

    def on_end(self, path):
        self.thread.quit()

        if path is None:
            self.label.setText('Update failed')
            return

        self.label.setText('Download complete')

        self.label.setText('Updating...')

        for i in range(25):
            try:
                shutil.move(path, exe_path)
                self.label.setText('Updated')
                break
            except:
                time.sleep(1)


app = QtWidgets.QApplication([])

widget = UpdaterWindow()
widget.show()

sys.exit(app.exec())
