import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

_, exe_url, exe_path, parent_pid = sys.argv


class Updater:
    def __init__(self):
        path = Path('updated.exe')
        self.download_exe(path, exe_url)
        self.update(path)

    @staticmethod
    def download_exe(path, url):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
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
                        bar_length = 40
                        filled = int(bar_length * percent)
                        bar = "█" * filled + "-" * (bar_length - filled)

                        sys.stdout.write(
                            f"\r[{bar}] {percent * 100:6.2f}% "
                            f"{downloaded}/{total} bytes"
                        )
                        sys.stdout.flush()

        print("\nDownload complete", path.absolute())
        return path

    @staticmethod
    def close_main():
        pid = int(parent_pid)

        subprocess.run(["taskkill", "/PID", str(pid), "/F"])

        for i in range(120):
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True
            )

            if str(pid) not in result.stdout:
                print("Proceso cerrado")
                break

            print("Esperando que cierre...")
            time.sleep(1)

    def update(self, path):
        self.close_main()

        for i in range(25):
            try:
                shutil.move(path, exe_path)
                print("\nReplace complete", str(path.absolute()), exe_path)
                break
            except:
                time.sleep(1)

        time.sleep(10)


Updater()
