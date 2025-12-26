"""
Tests for MediaFilesTableModel.
"""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import Qt

from pymsort.mediafiles_tablemodel import MediaFilesTableModel
from pymsort.models import MediaFile, ProcessingState
from pymsort.services import MediaInfoService


class TestMediaFilesTableModel:
    """Test cases for MediaFilesTableModel."""

    @pytest.fixture
    def mock_exiftool_service(self):
        """Create a mock ExifToolService."""
        return Mock()

    @pytest.fixture
    def mock_media_info_service(self):
        """Create a mock MediaInfoService."""
        service = Mock(spec=MediaInfoService)
        service.get_mime_type.return_value = "video/mp4"
        return service

    @pytest.fixture
    def model(self, mock_exiftool_service, mock_media_info_service):
        """Create a fresh MediaFilesTableModel for each test."""
        return MediaFilesTableModel(mock_exiftool_service, mock_media_info_service)

    def test_initial_state(self, model):
        """Test that model starts empty."""
        assert model.rowCount() == 0
        assert model.columnCount() == 10

    def test_column_count(self, model):
        """Test that model has correct number of columns."""
        assert model.columnCount() == 10

    def test_column_headers(self, model):
        """Test that column headers are correct."""
        expected_headers = [
            "Source file",
            "MIME type",
            "Container format",
            "Video format",
            "Video scan type",
            "Audio format",
            "Live Photo video",
            "Intermediate file",
            "Destination file",
            "Process state",
        ]

        for i, header in enumerate(expected_headers):
            assert (
                model.headerData(
                    i, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole
                )
                == header
            )

    def test_add_file_image(self, mock_exiftool_service, mock_media_info_service):
        """Test adding an image file."""
        # Configure mocks
        mock_exiftool_service.extract_metadata.return_value = [
            {"MIMEType": "image/jpeg"}
        ]

        model = MediaFilesTableModel(mock_exiftool_service, mock_media_info_service)
        model.add_file("/path/to/image.jpg")

        assert model.rowCount() == 1
        assert model._data[0].source_file == "/path/to/image.jpg"
        assert model._data[0].mime_type == "image/jpeg"
        assert model._data[0].state == ProcessingState.Pending

    def test_add_file_video(self, mock_exiftool_service, mock_media_info_service):
        """Test adding a video file."""
        # Configure mocks
        mock_exiftool_service.extract_metadata.return_value = [
            {"MIMEType": "video/mp4"}
        ]
        mock_media_info_service.analyze_file.return_value = {
            "general": {"format": "MPEG-4"},
            "video": {"stream_count": 1, "format": "AVC", "scan_type": "Progressive"},
            "audio": {"stream_count": 1, "format": "AAC"},
        }

        model = MediaFilesTableModel(mock_exiftool_service, mock_media_info_service)
        model.add_file("/path/to/video.mp4")

        assert model.rowCount() == 1
        assert model._data[0].source_file == "/path/to/video.mp4"
        assert model._data[0].mime_type == "video/mp4"
        assert model._data[0].container_format == "MPEG-4"
        assert model._data[0].video_format == "AVC"
        assert model._data[0].video_scan_type == "Progressive"
        assert model._data[0].audio_format == "AAC"
        assert model._data[0].video_stream_count == 1
        assert model._data[0].audio_stream_count == 1
        assert model._data[0].is_live_photo_video is False
        assert model._data[0].state == ProcessingState.Pending

    def test_add_file_live_photo_video(
        self, mock_exiftool_service, mock_media_info_service
    ):
        """Test adding a Live Photo video."""
        # Configure mocks
        mock_exiftool_service.extract_metadata.return_value = [
            {"MIMEType": "video/quicktime"}
        ]
        mock_media_info_service.analyze_file.return_value = {
            "general": {"format": "QuickTime", "is_live_photo": True},
            "video": {"stream_count": 1, "format": "HEVC", "scan_type": ""},
            "audio": {"stream_count": 0},
        }

        model = MediaFilesTableModel(mock_exiftool_service, mock_media_info_service)
        model.add_file("/path/to/livephoto.mov")

        assert model.rowCount() == 1
        assert model._data[0].is_live_photo_video is True

    def test_add_file_duplicate_skipped(
        self, mock_exiftool_service, mock_media_info_service
    ):
        """Test that duplicate files are skipped."""
        # Configure mocks
        mock_exiftool_service.extract_metadata.return_value = [
            {"MIMEType": "image/jpeg"}
        ]

        model = MediaFilesTableModel(mock_exiftool_service, mock_media_info_service)

        # Add file first time
        model.add_if_new("/path/to/image.jpg")
        assert model.rowCount() == 1

        # Try to add same file again
        model.add_if_new("/path/to/image.jpg")
        assert model.rowCount() == 1  # Should still be 1

    def test_add_file_unsupported_mimetype_skipped(
        self, mock_exiftool_service, mock_media_info_service
    ):
        """Test that unsupported file types are skipped."""
        # Configure mocks - return None to simulate unsupported file
        mock_exiftool_service.extract_metadata.return_value = []

        model = MediaFilesTableModel(mock_exiftool_service, mock_media_info_service)
        model.add_file("/path/to/document.pdf")

        assert model.rowCount() == 0  # Should not be added

    def test_data_display_role(self, model):
        """Test data retrieval with DisplayRole."""
        # Add a test file manually
        test_file = MediaFile(
            source_file="/path/to/test.jpg",
            mime_type="image/jpeg",
            container_format="JPEG",
            video_format="",
            video_scan_type="",
            audio_format="",
            is_live_photo_video=False,
            intermediate_file="/temp/test.jpg",
            destination_file="/dest/test.jpg",
            state=ProcessingState.Success,
        )
        model._data.append(test_file)

        # Test each column
        index = model.index(0, 0)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "/path/to/test.jpg"

        index = model.index(0, 1)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "image/jpeg"

        index = model.index(0, 9)
        assert model.data(index, Qt.ItemDataRole.DisplayRole) == "Success"

    def test_data_background_role_states(self, model):
        """Test background colors for different states."""
        # Add files with different states
        states_to_test = [
            (ProcessingState.InProgress, Qt.GlobalColor.blue),
            (ProcessingState.Success, Qt.GlobalColor.green),
            (ProcessingState.Warning, Qt.GlobalColor.yellow),
            (ProcessingState.Error, Qt.GlobalColor.red),
        ]

        for state, expected_color in states_to_test:
            test_file = MediaFile(
                source_file=f"/path/to/file_{state.name}.jpg", state=state
            )
            model._data.append(test_file)

        # Check background colors (column 9 is state column)
        for i, (state, expected_color) in enumerate(states_to_test):
            index = model.index(i, 9)
            background = model.data(index, Qt.ItemDataRole.BackgroundRole)
            assert background.color() == expected_color

    def test_signals_exist(self, model):
        """Test that required signals exist."""
        assert hasattr(model, "enableSortButtonSignal")
        assert hasattr(model, "disableSortButtonSignal")

    def test_drop_event_emits_disable_signal(self, model, qtbot):
        """Test that dropEvent emits disable signal."""
        with qtbot.waitSignal(model.disableSortButtonSignal):
            model.dropEvent([])

    def test_drop_event_enables_button_with_pending_files(
        self, mock_exiftool_service, mock_media_info_service, qtbot
    ):
        """Test that button is enabled when pending files exist."""
        model = MediaFilesTableModel(mock_exiftool_service, mock_media_info_service)

        # Add a pending file first
        test_file = MediaFile(
            source_file="/path/to/test.jpg", state=ProcessingState.Pending
        )
        model._data.append(test_file)

        # Configure mocks
        mock_exiftool_service.extract_metadata.return_value = [
            {"MIMEType": "image/jpeg"}
        ]

        with patch("os.path.isfile", return_value=True):
            with patch("os.walk", return_value=[]):
                # Create mock URL
                mock_url = Mock()
                mock_url.toLocalFile.return_value = "/path/to/new.jpg"

                with qtbot.waitSignal(model.enableSortButtonSignal):
                    model.dropEvent([mock_url])

    def test_video_without_audio_track(
        self, mock_exiftool_service, mock_media_info_service
    ):
        """Test handling video without audio track."""
        # Configure mocks
        mock_exiftool_service.extract_metadata.return_value = [
            {"MIMEType": "video/quicktime"}
        ]
        mock_media_info_service.analyze_file.return_value = {
            "general": {"format": "QuickTime", "is_live_photo": False},
            "video": {"stream_count": 1, "format": "HEVC", "scan_type": ""},
            "audio": {
                "stream_count": 0  # No audio
            },
        }

        model = MediaFilesTableModel(mock_exiftool_service, mock_media_info_service)
        model.add_file("/path/to/timelapse.mov")

        assert model.rowCount() == 1
        assert model._data[0].audio_stream_count == 0
        assert (
            model._data[0].audio_format is None
        )  # No audio format when no audio streams

    def test_multiple_files_added(self, mock_exiftool_service, mock_media_info_service):
        """Test adding multiple files."""
        # Configure mocks
        mock_exiftool_service.extract_metadata.return_value = [
            {"MIMEType": "image/jpeg"}
        ]

        model = MediaFilesTableModel(mock_exiftool_service, mock_media_info_service)

        files = ["/path/to/file1.jpg", "/path/to/file2.jpg", "/path/to/file3.jpg"]
        for file in files:
            model.add_file(file)

        assert model.rowCount() == 3
        for i, file in enumerate(files):
            assert model._data[i].source_file == file
