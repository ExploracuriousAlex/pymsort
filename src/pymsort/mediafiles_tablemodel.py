import logging
import os
from enum import IntEnum
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QThreadPool, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QApplication

from .models import MediaFile, ProcessingState
from .services import MediaInfoService
from .workers.import_worker import ImportWorker

logger = logging.getLogger(__name__)


class Column(IntEnum):
    """Table column indices."""

    SOURCE_FILE = 0
    MIME_TYPE = 1
    CONTAINER_FORMAT = 2
    VIDEO_FORMAT = 3
    VIDEO_SCAN_TYPE = 4
    AUDIO_FORMAT = 5
    LIVE_PHOTO = 6
    INTERMEDIATE_FILE = 7
    DESTINATION_FILE = 8
    STATE = 9


# Column headers corresponding to Column enum
COLUMN_HEADERS = {
    Column.SOURCE_FILE: "Source file",
    Column.MIME_TYPE: "MIME type",
    Column.CONTAINER_FORMAT: "Container format",
    Column.VIDEO_FORMAT: "Video format",
    Column.VIDEO_SCAN_TYPE: "Video scan type",
    Column.AUDIO_FORMAT: "Audio format",
    Column.LIVE_PHOTO: "Live Photo video",
    Column.INTERMEDIATE_FILE: "Intermediate file",
    Column.DESTINATION_FILE: "Destination file",
    Column.STATE: "Process state",
}


# Mapping of processing states to background colors
STATE_COLORS = {
    ProcessingState.InProgress: Qt.GlobalColor.blue,
    ProcessingState.Success: Qt.GlobalColor.green,
    ProcessingState.Warning: Qt.GlobalColor.yellow,
    ProcessingState.Error: Qt.GlobalColor.red,
}


class MediaFilesTableModel(QAbstractTableModel):
    enableSortButtonSignal = Signal()
    disableSortButtonSignal = Signal()
    importProgressSignal = Signal(int, int, str)  # current, total, message

    def __init__(
        self, exiftool_service, media_info_service: MediaInfoService, data=None
    ):
        super().__init__()
        self._data: List[MediaFile] = []
        self.exiftool_service = exiftool_service
        self.media_info_service = media_info_service

    def _get_display_value(self, media_file: MediaFile, column: int) -> Optional[str]:
        """Get display value for a cell."""
        column_mapping = {
            Column.SOURCE_FILE: media_file.source_file,
            Column.MIME_TYPE: media_file.mime_type,
            Column.CONTAINER_FORMAT: media_file.container_format,
            Column.VIDEO_FORMAT: media_file.video_format,
            Column.VIDEO_SCAN_TYPE: media_file.video_scan_type,
            Column.AUDIO_FORMAT: media_file.audio_format,
            Column.LIVE_PHOTO: media_file.is_live_photo_video,
            Column.INTERMEDIATE_FILE: media_file.intermediate_file,
            Column.DESTINATION_FILE: media_file.destination_file,
            Column.STATE: media_file.state.name,
        }
        return column_mapping.get(column)

    def data(self, index, role):
        if not index.isValid() or index.row() >= len(self._data):
            return None

        media_file = self._data[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            return self._get_display_value(media_file, index.column())

        if role == Qt.ItemDataRole.BackgroundRole:
            if index.column() == Column.STATE and media_file.state in STATE_COLORS:
                return QBrush(QColor(STATE_COLORS[media_file.state]))

        return None

    def rowCount(self, index=QModelIndex()):
        return len(self._data)

    def columnCount(self, index=QModelIndex()):
        return len(Column)

    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return COLUMN_HEADERS.get(section, "")
        return None

    def add_if_new(self, path):
        if any(mf.source_file == path for mf in self._data):
            logger.debug("File '%s' already in table. Skip.", path)
        else:
            self.add_file(path)

    def dropEvent(self, urls, **kwargs):
        """Handle file drop event using background worker."""
        logger.debug("Disable sort and convert button")
        self.disableSortButtonSignal.emit()

        # Collect all file paths
        file_paths = []
        for url in urls:
            path = url.toLocalFile()
            if os.path.isfile(path):
                file_paths.append(path)
            else:
                # Recursively add all files from directory
                for root, dirs, files in os.walk(path):
                    for file in files:
                        file_paths.append(os.path.join(root, file))

        # Filter out files already in the table
        existing_files = {mf.source_file for mf in self._data}
        new_files = [f for f in file_paths if f not in existing_files]

        if not new_files:
            logger.info("No new files to import")
            return

        logger.info(f"Starting import of {len(new_files)} files")

        # Set busy cursor
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        # Create and configure import worker
        worker = ImportWorker(
            file_paths=new_files,
            exiftool_service=self.exiftool_service,
            mediainfo_service=self.media_info_service,
        )

        # Connect signals
        worker.signals.progress.connect(self._on_import_progress)
        worker.signals.file_imported.connect(self._on_file_imported)
        worker.signals.finished.connect(self._on_import_finished)
        worker.signals.error.connect(self._on_import_error)

        # Start worker
        QThreadPool.globalInstance().start(worker)

    def add_file(self, path):
        """Add a single file to the table (synchronous, for testing/compatibility)."""
        # Use ExifTool to get MIME type (more reliable than MediaInfo)
        metadata_list = self.exiftool_service.extract_metadata([Path(path)])
        if not metadata_list or len(metadata_list) == 0:
            logger.error("Failed to extract metadata for '%s'", path)
            return

        # ExifTool returns a list with one dict per file
        file_metadata = metadata_list[0]
        mime_type = file_metadata.get("MIMEType", "unknown")

        if not mime_type or mime_type == "unknown":
            logger.error("Failed to get MIME type for '%s'", path)
            return

        mf = MediaFile(path, mime_type=mime_type)

        if mime_type.lower().startswith("image"):
            logger.debug("Add image file '%s'.", path)
        elif mime_type.lower().startswith("video"):
            logger.debug("Add video file '%s'.", path)
            # Get detailed media information and populate fields
            info = self.media_info_service.analyze_file(Path(path))
            mf.populate_from_mediainfo(info)
        else:
            logger.debug("MIME Type '%s' is not supported. Skip.", mime_type)
            return

        mf.state = ProcessingState.Pending
        self.beginInsertRows(
            QModelIndex(),
            self.rowCount(),
            self.rowCount(),
        )
        self._data.append(mf)
        self.endInsertRows()

    def _on_import_progress(self, current: int, total: int, message: str):
        """Handle import progress update."""
        self.importProgressSignal.emit(current, total, message)

    def _on_file_imported(self, media_file: MediaFile):
        """Handle imported file from worker."""
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        self._data.append(media_file)
        self.endInsertRows()

    def _on_import_finished(self):
        """Handle import completion."""
        logger.info("Import finished")
        QApplication.restoreOverrideCursor()

        # Enable button if there are pending files
        if any(mf.state == ProcessingState.Pending for mf in self._data):
            logger.debug("Enable sort and convert button since there are pending files")
            self.enableSortButtonSignal.emit()

        # Emit final progress
        self.importProgressSignal.emit(0, 0, "Import complete")

    def _on_import_error(self, error_message: str):
        """Handle import error."""
        logger.error(f"Import error: {error_message}")
        QApplication.restoreOverrideCursor()
        self.importProgressSignal.emit(0, 0, f"Import error: {error_message}")
