import logging
from pathlib import Path

from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import QIcon

from .mediafiles_tableview import MediaFilesTableView
from .models import ProcessingState, load_conversion_profiles
from .services import ExifToolService, FFmpegService, MediaInfoService
from .utils import config
from .workers import ProcessWorker

logger = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize services
        self.exiftool_service = ExifToolService(config.exiftool_path)
        self.ffmpeg_service = FFmpegService(config.ffmpeg_path)
        self.media_info_service = MediaInfoService()

        # Load conversion profiles
        try:
            self.conversion_profiles = load_conversion_profiles()
            logger.info(f"Loaded {len(self.conversion_profiles)} conversion profiles")
        except Exception as e:
            logger.error(f"Failed to load conversion profiles: {e}")
            self.conversion_profiles = []
            QtWidgets.QMessageBox.warning(
                self,
                "Configuration Error",
                f"Failed to load conversion profiles: {e}\n\nVideo conversion will not be available.",
            )

        # Widgets
        self.setWindowTitle("Python Media Sorter")
        icon_path = Path(__file__).parent.parent.parent / "ressources" / "appicon.png"
        self.setWindowIcon(QIcon(str(icon_path)))

        instructions = QtWidgets.QLabel(
            'Simply drag and drop one or more media files or one or more folders containing media files into the table below. Then press "Convert & Sort" to sort the files and convert them if necessary.'
        )

        self.media_file_table = MediaFilesTableView(
            exiftool_service=self.exiftool_service,
            media_info_service=self.media_info_service,
        )

        # Output folder selection
        output_layout = QtWidgets.QHBoxLayout()
        output_label = QtWidgets.QLabel("Output folder:")
        self.output_folder_edit = QtWidgets.QLineEdit()
        self.output_folder_edit.setText(str(config.temp_dir))
        self.output_folder_edit.setPlaceholderText("Select output folder...")
        browse_button = QtWidgets.QPushButton("Browse...")
        browse_button.clicked.connect(self.on_browse_output_folder)
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_folder_edit, 1)
        output_layout.addWidget(browse_button)

        self.convert_and_sort_button = QtWidgets.QPushButton("Convert && Sort")
        self.convert_and_sort_button.setDisabled(True)
        self.convert_and_sort_button.clicked.connect(self.on_convert_and_sort_clicked)

        # Progress widgets
        self.progress_label = QtWidgets.QLabel("Ready")
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)

        # Log view
        log_label = QtWidgets.QLabel("Processing Log:")
        self.log_view = QtWidgets.QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(150)
        self.log_view.setVisible(False)

        # Layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(instructions)
        layout.addWidget(self.media_file_table)
        layout.addLayout(output_layout)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.convert_and_sort_button)
        layout.addWidget(log_label)
        layout.addWidget(self.log_view)

        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(layout)

        self.setCentralWidget(central_widget)

        # Connect table signals
        self.media_file_table.model().enableSortButtonSignal.connect(
            lambda: self.convert_and_sort_button.setEnabled(True)
        )
        self.media_file_table.model().disableSortButtonSignal.connect(
            lambda: self.convert_and_sort_button.setEnabled(False)
        )
        self.media_file_table.model().importProgressSignal.connect(
            self.on_import_progress
        )

        # Worker reference
        self.process_worker = None

    def on_browse_output_folder(self):
        """Open folder selection dialog for output folder."""
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Output Folder", self.output_folder_edit.text()
        )
        if folder:
            self.output_folder_edit.setText(folder)

    def on_convert_and_sort_clicked(self):
        """Handle Convert & Sort button click."""
        # Get all pending media files
        media_files = [
            mf
            for mf in self.media_file_table.model()._data
            if mf.state == ProcessingState.Pending
        ]

        if not media_files:
            QtWidgets.QMessageBox.information(self, "No Files", "No files to process.")
            return

        # Validate output folder
        output_folder = Path(self.output_folder_edit.text().strip())
        if not output_folder.exists():
            try:
                output_folder.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self, "Invalid Output Folder", f"Cannot create output folder:\n{e}"
                )
                return

        # Disable button and show progress
        self.convert_and_sort_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_view.setVisible(True)
        self.log_view.clear()

        # Create and start worker
        self.process_worker = ProcessWorker(
            files=media_files,
            profiles=self.conversion_profiles,
            temp_folder=output_folder,
            exiftool_service=self.exiftool_service,
            ffmpeg_service=self.ffmpeg_service,
            mediainfo_service=self.media_info_service,
        )

        # Connect signals
        self.process_worker.signals.progress.connect(self.on_progress)
        self.process_worker.signals.log_message.connect(self.on_log)
        self.process_worker.signals.finished.connect(self.on_processing_finished)
        self.process_worker.signals.error.connect(self.on_processing_error)

        # Start worker
        QtCore.QThreadPool.globalInstance().start(self.process_worker)
        logger.info(f"Started processing {len(media_files)} files")

    def on_import_progress(self, current: int, total: int, message: str):
        """Update display during file import.

        Args:
            current: Current file index
            total: Total number of files
            message: Progress message
        """
        if total > 0:
            progress_percent = int((current / total) * 100)
            self.progress_bar.setValue(progress_percent)
            self.progress_bar.setVisible(True)
            self.progress_label.setText(f"Importing {current}/{total}: {message}")
        else:
            # Import complete or error
            self.progress_bar.setVisible(False)
            self.progress_label.setText(message)

    def on_progress(self, current: int, total: int, message: str):
        """Update progress display.

        Args:
            current: Current file index
            total: Total number of files
            message: Progress message
        """
        progress_percent = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(progress_percent)
        self.progress_label.setText(f"Processing {current}/{total}: {message}")
        logger.debug(f"Progress: {current}/{total} - {message}")

    def on_log(self, level: str, message: str):
        """Add message to log view.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR)
            message: Log message
        """
        self.log_view.append(f"[{level}] {message}")

    def on_processing_finished(self):
        """Handle processing completion."""
        self.progress_bar.setValue(100)
        self.convert_and_sort_button.setEnabled(True)

        # Refresh table to show updated states
        self.media_file_table.model().layoutChanged.emit()

        # Check if all files were processed successfully
        all_files = self.media_file_table.model()._data
        error_count = sum(1 for f in all_files if f.state == ProcessingState.Error)
        success_count = sum(1 for f in all_files if f.state == ProcessingState.Success)

        if error_count > 0:
            self.progress_label.setText("Processing completed with errors!")
            logger.warning(
                f"Processing completed with {error_count} error(s), {success_count} successful"
            )
            QtWidgets.QMessageBox.warning(
                self,
                "Processing Complete",
                f"Processing completed with {error_count} error(s).\n{success_count} file(s) processed successfully.\n\nCheck the log for details.",
            )
        else:
            self.progress_label.setText("Processing completed!")
            logger.info("Processing completed successfully")
            QtWidgets.QMessageBox.information(
                self,
                "Processing Complete",
                "All files have been processed successfully!",
            )

    def on_processing_error(self, error_tuple: tuple):
        """Handle processing error.

        Args:
            error_tuple: Tuple of (exception_type, error_message, traceback)
        """
        _, error_message, _ = error_tuple
        self.progress_label.setText("Processing failed!")
        self.convert_and_sort_button.setEnabled(True)
        logger.error(f"Processing error: {error_message}")

        QtWidgets.QMessageBox.critical(
            self,
            "Processing Error",
            f"An error occurred during processing:\n\n{error_message}",
        )
