import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel, QLineEdit, \
    QProgressBar, QGroupBox, QHBoxLayout, QComboBox, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl
import pytube
import os


class DownloaderThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, url, path, format):
        super().__init__()
        self.url = url
        self.path = path
        self.format = format
        self.paused = False
        self.stopped = False
        self.mutex = QMutex()
        self.wait_condition = QWaitCondition()

    def run(self):
        try:
            yt = pytube.YouTube(self.url)
            duration = yt.length  # Duration of the video in seconds

            if duration > 120:  # Check if the video is longer than 2 minutes
                self.error.emit("Video is longer than 2 minutes.")
                return

            if self.format == "MP4":
                stream = yt.streams.get_highest_resolution()
            else:  # MP3
                stream = yt.streams.filter(only_audio=True).first()

            total_size = stream.filesize
            downloaded_size = 0

            temp_file = os.path.join(self.path, "temp_download")
            if os.path.exists(temp_file):
                downloaded_size = os.path.getsize(temp_file)

            def on_progress(chunk, file_handle, bytes_remaining):
                nonlocal downloaded_size
                downloaded_size = total_size - bytes_remaining
                progress_percent = int((downloaded_size / total_size) * 100)
                self.progress.emit(progress_percent)

                self.mutex.lock()
                if self.paused:
                    self.wait_condition.wait(self.mutex)
                if self.stopped:
                    self.mutex.unlock()
                    return
                self.mutex.unlock()

            yt.register_on_progress_callback(on_progress)
            stream.download(output_path=self.path, filename="temp_download", skip_existing=True)

            if not self.stopped:
                final_filename = stream.default_filename
                if self.format == "MP3":
                    base, ext = os.path.splitext(final_filename)
                    final_filename = base + ".mp3"
                os.rename(temp_file, os.path.join(self.path, final_filename))
                self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))

    def pause(self):
        self.mutex.lock()
        self.paused = True
        self.mutex.unlock()

    def resume(self):
        self.mutex.lock()
        self.paused = False
        self.wait_condition.wakeAll()
        self.mutex.unlock()

    def stop(self):
        self.mutex.lock()
        self.stopped = True
        self.paused = False
        self.wait_condition.wakeAll()
        self.mutex.unlock()


class MyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Youtube Video Downloader')
        self.setGeometry(500, 500, 700, 350)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        vbox = QVBoxLayout()

        self.input_field1 = QLineEdit(self)
        self.input_field1.setPlaceholderText('Enter Url:')
        vbox.addWidget(self.input_field1)

        self.input_field2 = QLineEdit(self)
        self.input_field2.setPlaceholderText('Enter Path:')
        vbox.addWidget(self.input_field2)

        self.format_group_box = QGroupBox('Format Selection')
        format_layout = QVBoxLayout()

        self.format_combo = QComboBox(self)
        self.format_combo.addItem("MP4")
        self.format_combo.addItem("MP3")
        format_layout.addWidget(self.format_combo)

        self.format_group_box.setLayout(format_layout)
        vbox.addWidget(self.format_group_box)

        self.btn_download = QPushButton('Download', self)
        self.btn_download.clicked.connect(self.buttonClicked)
        vbox.addWidget(self.btn_download)

        # Create a group box for the progress bar and pause/resume buttons
        progress_group_box = QGroupBox('Progress Bar')
        progress_layout = QVBoxLayout()

        self.progress_bar = QProgressBar(self)
        progress_layout.addWidget(self.progress_bar)

        # Create a horizontal layout for pause and resume buttons
        hbox = QHBoxLayout()
        self.btn_pause = QPushButton('Pause', self)
        self.btn_pause.clicked.connect(self.pauseDownload)
        self.btn_pause.setEnabled(False)
        hbox.addWidget(self.btn_pause)

        self.btn_resume = QPushButton('Resume', self)
        self.btn_resume.clicked.connect(self.resumeDownload)
        self.btn_resume.setEnabled(False)
        hbox.addWidget(self.btn_resume)

        progress_layout.addLayout(hbox)
        progress_group_box.setLayout(progress_layout)
        vbox.addWidget(progress_group_box)

        self.output_label = QLabel('by Nilüş ❤️', self)
        vbox.addWidget(self.output_label)

        central_widget.setLayout(vbox)

    def buttonClicked(self):
        url = self.input_field1.text()
        path = self.input_field2.text()
        format = self.format_combo.currentText()

        if not url or not path:
            self.output_label.setText("Please provide both URL and Path.")
            return

        self.downloader_thread = DownloaderThread(url, path, format)
        self.downloader_thread.progress.connect(self.updateProgressBar)
        self.downloader_thread.finished.connect(self.downloadFinished)
        self.downloader_thread.error.connect(self.downloadError)
        self.downloader_thread.start()

        self.btn_pause.setEnabled(True)
        self.btn_resume.setEnabled(False)

    def updateProgressBar(self, value):
        self.progress_bar.setValue(value)

    def downloadFinished(self):
        self.output_label.setText("Download finished!")
        self.btn_pause.setEnabled(False)
        self.btn_resume.setEnabled(False)

    def downloadError(self, error_message):
        if error_message == "Video is longer than 2 minutes.":
            self.showUpgradeMessage()
        else:
            self.output_label.setText(f"Error: {error_message}")
        self.btn_pause.setEnabled(False)
        self.btn_resume.setEnabled(False)

    def showUpgradeMessage(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Upgrade Required")
        msg.setText("Please get the full version of the program.\n\n For information, visit the website :)")

        link = QLabel('<a href="http://www.nilus3568.com">www.nilus3568.com</a>', self)
        link.setOpenExternalLinks(True)
        msg.layout().addWidget(link)
        msg.exec_()

    def pauseDownload(self):
        if self.downloader_thread and self.downloader_thread.isRunning():
            self.downloader_thread.pause()
            self.btn_pause.setEnabled(False)
            self.btn_resume.setEnabled(True)

    def resumeDownload(self):
        if self.downloader_thread and self.downloader_thread.isRunning():
            self.downloader_thread.resume()
            self.btn_pause.setEnabled(True)
            self.btn_resume.setEnabled(False)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    ex.show()
    sys.exit(app.exec_())
