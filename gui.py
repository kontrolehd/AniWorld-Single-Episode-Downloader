import sys
import threading
import subprocess
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QProgressBar,
)
from PyQt6.QtCore import pyqtSignal, QObject
import re
import os


class WorkerSignals(QObject):
    output = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)
    finished = pyqtSignal()


class DownloadWorker(threading.Thread):
    def __init__(self, episode_url: str, output_dir: str, signals: WorkerSignals):
        super().__init__()
        self.episode_url = episode_url
        self.output_dir = output_dir
        self.signals = signals
        self.open_video = False
        self.open_folder = False

    def run(self):
        try:
            script_path = os.path.abspath(os.path.join(os.getcwd(), "AIProjekte/aniworld_single_downloader/downloader.py"))
            cmd = [
                sys.executable,
                script_path,
                self.episode_url,
            ]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.output_dir,
            )
            progress_pattern = re.compile(r"\[download\]\s+(\d{1,3}\.\d)%")
            output_lines = []
            for line in process.stdout:
                self.signals.output.emit(line)
                output_lines.append(line)
                match = progress_pattern.search(line)
                if match:
                    progress_value = int(float(match.group(1)))
                    self.signals.progress.emit(progress_value)
            for line in process.stderr:
                self.signals.error.emit(line)
            process.wait()
            if process.returncode == 0:
                self.signals.output.emit("Download completed successfully.\n")
                self.signals.progress.emit(100)
                if self.open_video or self.open_folder:
                    filename = None
                    for out_line in reversed(output_lines):
                        if "Downloading to " in out_line:
                            filename = out_line.strip().split("Downloading to ")[-1]
                            break
                    if filename:
                        if self.open_video:
                            try:
                                os.startfile(filename)
                            except Exception as e:
                                self.signals.error.emit(f"Failed to open video file: {e}\n")
                        elif self.open_folder:
                            folder_path = os.path.dirname(filename)
                            try:
                                os.startfile(folder_path)
                            except Exception as e:
                                self.signals.error.emit(f"Failed to open folder: {e}\n")
            else:
                self.signals.error.emit(f"Download failed with exit code {process.returncode}\n")
        except Exception as e:
            self.signals.error.emit(f"Error running downloader: {e}\n")
        finally:
            self.signals.finished.emit()


class AniWorldDownloaderGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AniWorld Single Episode Downloader")
        self.setMinimumSize(600, 500)
        self.init_ui()
        self.worker = None

    def init_ui(self):
        layout = QVBoxLayout()

        label = QLabel("Episode URL:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter the aniworld.to episode URL here")

        output_label = QLabel("Output Directory:")
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setPlaceholderText("Select output directory")
        self.output_dir_input.setReadOnly(True)
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_output_dir)

        self.download_button = QPushButton("Start Download")
        self.download_button.clicked.connect(self.start_download)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        layout.addWidget(label)
        layout.addWidget(self.url_input)
        layout.addWidget(output_label)
        layout.addWidget(self.output_dir_input)
        layout.addWidget(browse_button)
        layout.addWidget(self.download_button)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log_output)

        self.setLayout(layout)

    def browse_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.output_dir_input.setText(directory)

    def append_log(self, text: str):
        self.log_output.append(text)
        self.log_output.ensureCursorVisible()

    def update_progress(self, value: int):
        self.progress_bar.setValue(value)

    def start_download(self):
        episode_url = self.url_input.text().strip()
        output_dir = self.output_dir_input.text().strip()

        if not episode_url:
            QMessageBox.warning(self, "Input Error", "Please enter an episode URL.")
            return
        if not output_dir:
            QMessageBox.warning(self, "Input Error", "Please select an output directory.")
            return

        self.download_button.setEnabled(False)
        self.log_output.clear()
        self.progress_bar.setValue(0)

        self.signals = WorkerSignals()
        self.signals.output.connect(self.append_log)
        self.signals.error.connect(self.append_log)
        self.signals.progress.connect(self.update_progress)
        self.signals.finished.connect(self.download_finished)

        self.worker = DownloadWorker(episode_url, output_dir, self.signals)
        self.worker.start()

    def download_finished(self):
        self.download_button.setEnabled(True)
        self.append_log("Download process finished.")
