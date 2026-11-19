import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

CHUNK_SIZE = 64 * 1024
REPLACE_ATTEMPTS = 120
REPLACE_WAIT = 2


class DownloadError(Exception):
    pass


def download_verified(url: str, path: Path, expected_sha256: str, progress=None, timeout=30) -> Path:
    """Descarga `url` en `path` y verifica tamaño y SHA-256. Si algo falla borra el archivo y lanza DownloadError."""
    if not url.startswith('https://'):
        raise DownloadError(f'URL no segura: {url}')

    partial = path.with_name(path.name + '.part')
    digest = hashlib.sha256()
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Accountant-Updater'})
        with urllib.request.urlopen(request, timeout=timeout) as response, open(partial, 'wb') as file:
            total = int(response.getheader('Content-Length') or 0)
            downloaded = 0
            while chunk := response.read(CHUNK_SIZE):
                file.write(chunk)
                digest.update(chunk)
                downloaded += len(chunk)
                if progress and total > 0:
                    progress(downloaded / total * 100)

        if total and downloaded != total:
            raise DownloadError(f'Descarga incompleta: {downloaded} de {total} bytes')
        if digest.hexdigest() != expected_sha256.lower():
            raise DownloadError('La firma SHA-256 del archivo descargado no coincide')

        os.replace(partial, path)
        return path
    except DownloadError:
        partial.unlink(missing_ok=True)
        raise
    except Exception as error:
        partial.unlink(missing_ok=True)
        raise DownloadError(f'Error al descargar: {error}') from error


def replace_executable(new_file: Path, target: Path, log=None, attempts=REPLACE_ATTEMPTS, wait=REPLACE_WAIT):
    """Reemplaza el ejecutable esperando a que la app anterior lo libere. Conserva un respaldo hasta el final."""
    backup = target.with_name(target.name + '.old')
    for attempt in range(1, attempts + 1):
        if log: log(f'Intento de actualización {attempt}')
        try:
            if target.exists():
                os.replace(target, backup)
            try:
                shutil.move(new_file, target)
            except OSError:
                if backup.exists(): os.replace(backup, target)  # restaurar la versión anterior
                raise
            backup.unlink(missing_ok=True)
            return
        except OSError:
            time.sleep(wait)
    raise DownloadError('No se pudo reemplazar el ejecutable: sigue en uso')


def main():
    from PySide6 import QtWidgets
    from PySide6.QtCore import QObject, QThread, Signal
    from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QFrame, QSpacerItem, QSizePolicy
    from qframelesswindow import FramelessWindow

    _, exe_url, exe_path, last_version, expected_sha256 = sys.argv
    exe_path = Path(exe_path)

    class UpdateWorker(QObject):
        run = Signal()
        progress = Signal(float)
        message = Signal(str)
        failed = Signal(str)
        updated = Signal()

        def on_run(self):
            path = Path(tempfile.gettempdir()) / f'Contabilidad-{last_version}.exe'
            try:
                self.message.emit(f'Descargando {last_version}...')
                download_verified(exe_url, path, expected_sha256, progress=self.progress.emit)
                self.message.emit('Descarga verificada')
                replace_executable(path, exe_path, log=self.message.emit)
                self.updated.emit()
            except DownloadError as error:
                path.unlink(missing_ok=True)
                self.failed.emit(str(error))

    class QLogger(QFrame):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.setObjectName('logs')
            self.setStyleSheet('#logs { border: 1px solid #444; border-radius: 8px; }')
            layout = QVBoxLayout(self)
            self.labels = [QLabel(self) for _ in range(3)]
            self.labels[0].setStyleSheet('color: #333')
            self.labels[1].setStyleSheet('color: #555')
            for label in self.labels:
                layout.addWidget(label)

        def setText(self, text):
            for upper, lower in zip(self.labels, self.labels[1:]):
                upper.setText(lower.text())
            self.labels[-1].setText(text)

    class UpdaterWindow(FramelessWindow):
        def __init__(self):
            super().__init__()
            self.finished = False

            self.setFixedSize(501, 201)
            layout = QVBoxLayout(self)
            layout.setContentsMargins(10, 42, 10, 10)

            self.title = QLabel(f'Actualización disponible {last_version}', self)
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
            self.worker = UpdateWorker()
            self.worker.moveToThread(self.thread)
            self.worker.run.connect(self.worker.on_run)
            self.worker.progress.connect(lambda v: self.progress_bar.setValue(int(v)))
            self.worker.message.connect(self.label.setText)
            self.worker.failed.connect(self.on_failed)
            self.worker.updated.connect(self.on_updated)
            self.thread.start()
            self.worker.run.emit()

        def on_failed(self, error):
            self.label.setText(f'No se actualizó: {error}')
            self.label.setText('Cierre esta ventana para abrir la versión actual')
            self.finished = True
            self.thread.quit()

        def on_updated(self):
            self.label.setText(f'Actualizado a {last_version} correctamente')
            self.finished = True
            self.thread.quit()

        def closeEvent(self, event):
            if not self.finished:
                event.ignore()  # no cerrar a media actualización
                return
            super().closeEvent(event)
            self.thread.wait()
            if exe_path.exists():
                subprocess.Popen([str(exe_path)])

    app = QtWidgets.QApplication([])
    widget = UpdaterWindow()
    widget.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
