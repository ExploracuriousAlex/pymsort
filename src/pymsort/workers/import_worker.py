"""
Worker for importing media files in background with progress reporting.
"""

import logging
import os
from pathlib import Path
from typing import List

from PySide6.QtCore import QObject, QRunnable, Signal

from ..models.mediafile import MediaFile, ProcessingState
from ..services.exiftool_service import ExifToolService
from ..services.mediainfo_service import MediaInfoService

logger = logging.getLogger(__name__)


class ImportWorkerSignals(QObject):
    """Signals for ImportWorker."""

    progress = Signal(int, int, str)  # current, total, message
    file_imported = Signal(MediaFile)  # Single file was imported
    finished = Signal()
    error = Signal(str)


class ImportWorker(QRunnable):
    """
    Worker to import media files in background thread.

    Analyzes files using ExifTool and MediaInfo, then emits signals
    for progress updates and imported files.
    """

    def __init__(
        self,
        file_paths: List[str],
        exiftool_service: ExifToolService,
        mediainfo_service: MediaInfoService,
    ):
        """
        Initialize the import worker.

        Args:
            file_paths: List of file paths to import
            exiftool_service: Service for extracting metadata
            mediainfo_service: Service for analyzing media files
        """
        super().__init__()
        self.file_paths = file_paths
        self.exiftool_service = exiftool_service
        self.mediainfo_service = mediainfo_service
        self.signals = ImportWorkerSignals()

    def run(self):
        """Import files with progress reporting."""
        try:
            total = len(self.file_paths)
            logger.info(f"Starting import of {total} files")

            # Extract metadata for all files at once (more efficient)
            self.signals.progress.emit(0, total, "Extracting metadata...")

            path_objects = [Path(p) for p in self.file_paths]
            metadata_list = self.exiftool_service.extract_metadata(path_objects)

            if not metadata_list:
                logger.error("Failed to extract metadata")
                self.signals.error.emit("Failed to extract metadata from files")
                return

            # Process each file (SourceFile is included in metadata)
            for i, metadata in enumerate(metadata_list, 1):
                file_path = metadata.get("SourceFile", "")
                self._process_single_file(i, total, file_path, metadata)

            logger.info(f"Finished importing {total} files")
            self.signals.finished.emit()

        except Exception as e:
            logger.error(f"Error in import worker: {e}", exc_info=True)
            self.signals.error.emit(str(e))

    def _process_single_file(
        self, index: int, total: int, file_path: str, metadata: dict
    ) -> None:
        """Process a single file during import."""
        try:
            mime_type = metadata.get("File:MIMEType", "unknown")

            if not mime_type or mime_type == "unknown":
                logger.debug(f"Skipping {file_path} - no MIME type")
                return

            mime_lower = mime_type.lower()
            is_image = mime_lower.startswith("image")
            is_video = mime_lower.startswith("video")

            if not (is_image or is_video):
                logger.debug(
                    f"Skipping {file_path} - unsupported MIME type: {mime_type}"
                )
                return

            filename = os.path.basename(file_path)
            self.signals.progress.emit(index, total, f"Importing {filename}")

            mf = MediaFile(file_path, mime_type=mime_type)
            mf.state = ProcessingState.Pending

            if is_video:
                info = self.mediainfo_service.analyze_file(Path(file_path))
                mf.populate_from_mediainfo(info)

            logger.debug(
                f"Imported {'video' if is_video else 'image'} file: {filename}"
            )
            self.signals.file_imported.emit(mf)

        except Exception as e:
            logger.error(f"Error importing {file_path}: {e}")
