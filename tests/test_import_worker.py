"""
Tests for ImportWorker.
"""

from unittest.mock import Mock

import pytest

from pymsort.models.mediafile import ProcessingState
from pymsort.workers.import_worker import ImportWorker, ImportWorkerSignals


class TestImportWorkerSignals:
    """Test cases for ImportWorkerSignals."""

    def test_signals_exist(self):
        """Test that all required signals exist."""
        signals = ImportWorkerSignals()
        assert hasattr(signals, "progress")
        assert hasattr(signals, "file_imported")
        assert hasattr(signals, "finished")
        assert hasattr(signals, "error")


class TestImportWorker:
    """Test cases for ImportWorker."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services."""
        mock_exiftool = Mock()
        mock_exiftool.extract_metadata.return_value = []

        mock_mediainfo = Mock()
        mock_mediainfo.analyze_file.return_value = None

        return {"exiftool": mock_exiftool, "mediainfo": mock_mediainfo}

    def test_init(self, mock_services):
        """Test ImportWorker initialization."""
        files = ["/path/to/file1.jpg", "/path/to/file2.mp4"]

        worker = ImportWorker(
            file_paths=files,
            exiftool_service=mock_services["exiftool"],
            mediainfo_service=mock_services["mediainfo"],
        )

        assert worker.file_paths == files
        assert worker.exiftool_service == mock_services["exiftool"]
        assert worker.mediainfo_service == mock_services["mediainfo"]
        assert hasattr(worker, "signals")

    def test_import_image_files(self, mock_services):
        """Test importing image files."""
        files = ["/path/to/image1.jpg", "/path/to/image2.png"]

        # Configure mocks
        mock_services["exiftool"].extract_metadata.return_value = [
            {"SourceFile": "/path/to/image1.jpg", "File:MIMEType": "image/jpeg"},
            {"SourceFile": "/path/to/image2.png", "File:MIMEType": "image/png"},
        ]

        worker = ImportWorker(
            file_paths=files,
            exiftool_service=mock_services["exiftool"],
            mediainfo_service=mock_services["mediainfo"],
        )

        # Track emitted files
        imported_files = []
        worker.signals.file_imported.connect(lambda mf: imported_files.append(mf))

        # Track progress
        progress_updates = []
        worker.signals.progress.connect(
            lambda c, t, m: progress_updates.append((c, t, m))
        )

        # Track completion
        finished = Mock()
        worker.signals.finished.connect(finished)

        # Run worker
        worker.run()

        # Verify
        assert len(imported_files) == 2
        assert imported_files[0].source_file == "/path/to/image1.jpg"
        assert imported_files[0].mime_type == "image/jpeg"
        assert imported_files[0].state == ProcessingState.Pending
        assert imported_files[1].source_file == "/path/to/image2.png"
        assert imported_files[1].mime_type == "image/png"
        assert len(progress_updates) > 0
        finished.assert_called_once()

    def test_import_video_files(self, mock_services):
        """Test importing video files with MediaInfo analysis."""
        files = ["/path/to/video.mp4"]

        # Configure mocks
        mock_services["exiftool"].extract_metadata.return_value = [
            {"SourceFile": "/path/to/video.mp4", "File:MIMEType": "video/mp4"}
        ]
        mock_services["mediainfo"].analyze_file.return_value = {
            "general": {"format": "MPEG-4", "is_live_photo": False},
            "video": {"stream_count": 1, "format": "AVC", "scan_type": "Progressive"},
            "audio": {"stream_count": 1, "format": "AAC"},
        }

        worker = ImportWorker(
            file_paths=files,
            exiftool_service=mock_services["exiftool"],
            mediainfo_service=mock_services["mediainfo"],
        )

        # Track emitted files
        imported_files = []
        worker.signals.file_imported.connect(lambda mf: imported_files.append(mf))

        finished = Mock()
        worker.signals.finished.connect(finished)

        # Run worker
        worker.run()

        # Verify
        assert len(imported_files) == 1
        mf = imported_files[0]
        assert mf.source_file == "/path/to/video.mp4"
        assert mf.mime_type == "video/mp4"
        assert mf.container_format == "MPEG-4"
        assert mf.video_format == "AVC"
        assert mf.video_scan_type == "Progressive"
        assert mf.audio_format == "AAC"
        assert mf.video_stream_count == 1
        assert mf.audio_stream_count == 1
        assert mf.is_live_photo_video is False
        assert mf.state == ProcessingState.Pending
        finished.assert_called_once()

    def test_skip_unsupported_files(self, mock_services):
        """Test that unsupported file types are skipped."""
        files = ["/path/to/document.pdf", "/path/to/image.jpg"]

        # Configure mocks - PDF is unsupported, JPG is supported
        mock_services["exiftool"].extract_metadata.return_value = [
            {"SourceFile": "/path/to/document.pdf", "File:MIMEType": "application/pdf"},
            {"SourceFile": "/path/to/image.jpg", "File:MIMEType": "image/jpeg"},
        ]

        worker = ImportWorker(
            file_paths=files,
            exiftool_service=mock_services["exiftool"],
            mediainfo_service=mock_services["mediainfo"],
        )

        # Track emitted files
        imported_files = []
        worker.signals.file_imported.connect(lambda mf: imported_files.append(mf))

        # Run worker
        worker.run()

        # Verify - only image should be imported
        assert len(imported_files) == 1
        assert imported_files[0].source_file == "/path/to/image.jpg"

    def test_handle_metadata_extraction_failure(self, mock_services):
        """Test handling when metadata extraction fails."""
        files = ["/path/to/file.jpg"]

        # Configure mock to return empty list (failure)
        mock_services["exiftool"].extract_metadata.return_value = []

        worker = ImportWorker(
            file_paths=files,
            exiftool_service=mock_services["exiftool"],
            mediainfo_service=mock_services["mediainfo"],
        )

        error_signal = Mock()
        worker.signals.error.connect(error_signal)

        # Run worker
        worker.run()

        # Verify error was emitted
        error_signal.assert_called_once()

    def test_progress_reporting(self, mock_services):
        """Test that progress is reported during import."""
        files = [f"/path/to/file{i}.jpg" for i in range(5)]

        # Configure mocks
        mock_services["exiftool"].extract_metadata.return_value = [
            {"SourceFile": f"/path/to/file{i}.jpg", "File:MIMEType": "image/jpeg"}
            for i in range(5)
        ]

        worker = ImportWorker(
            file_paths=files,
            exiftool_service=mock_services["exiftool"],
            mediainfo_service=mock_services["mediainfo"],
        )

        # Track progress
        progress_updates = []
        worker.signals.progress.connect(
            lambda c, t, m: progress_updates.append((c, t, m))
        )

        # Run worker
        worker.run()

        # Verify progress was reported
        assert len(progress_updates) > 0
        # First update should be about extracting metadata
        assert progress_updates[0][0] == 0
        assert progress_updates[0][1] == 5
        # Subsequent updates should show individual file progress
        assert any(
            str(i) in str(update[2]) for update in progress_updates for i in range(1, 6)
        )

    def test_video_without_mediainfo_data(self, mock_services):
        """Test video import when MediaInfo returns None."""
        files = ["/path/to/video.mp4"]

        # Configure mocks
        mock_services["exiftool"].extract_metadata.return_value = [
            {"SourceFile": "/path/to/video.mp4", "File:MIMEType": "video/mp4"}
        ]
        mock_services["mediainfo"].analyze_file.return_value = None

        worker = ImportWorker(
            file_paths=files,
            exiftool_service=mock_services["exiftool"],
            mediainfo_service=mock_services["mediainfo"],
        )

        # Track emitted files
        imported_files = []
        worker.signals.file_imported.connect(lambda mf: imported_files.append(mf))

        # Run worker
        worker.run()

        # Verify - file should still be imported with "Unknown" values
        assert len(imported_files) == 1
        mf = imported_files[0]
        assert mf.container_format == "Unknown"
        assert mf.video_format == "Unknown"
        assert mf.video_scan_type == "Unknown"
        assert mf.audio_format == "Unknown"
