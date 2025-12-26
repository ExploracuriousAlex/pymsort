"""
Tests for ProcessWorker.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from pymsort.models import MediaFile, ProcessingState
from pymsort.workers.process_worker import ProcessWorker, ProcessWorkerSignals


class TestProcessWorkerSignals:
    """Test cases for ProcessWorkerSignals."""

    def test_signals_exist(self):
        """Test that all signals are defined."""
        signals = ProcessWorkerSignals()
        assert hasattr(signals, "finished")
        assert hasattr(signals, "error")
        assert hasattr(signals, "progress")
        assert hasattr(signals, "file_state_changed")
        assert hasattr(signals, "log_message")


class TestProcessWorker:
    """Test cases for ProcessWorker."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services."""
        mock_file = Mock()

        return {
            "exiftool": Mock(),
            "ffmpeg": Mock(),
            "file": mock_file,
            "mediainfo": Mock(),
        }

    @pytest.fixture
    def sample_profiles(self):
        """Load actual conversion profiles from file."""
        from pymsort.models.conversion_profile import load_conversion_profiles

        return load_conversion_profiles()

    @pytest.fixture
    def sample_video_file(self):
        """Create a sample video MediaFile."""
        return MediaFile(
            source_file="/test/video.mov",
            file_name="video.mov",
            mime_type="video/quicktime",
            container_format="QuickTime",
            video_format="AVC",
            video_scan_type="Progressive",
            audio_format="AAC",
            is_live_photo_video=False,
            intermediate_file="",
            destination_file="",
            state=ProcessingState.Pending,
            video_stream_count=1,
            audio_stream_count=1,
        )

    @pytest.fixture
    def sample_image_file(self):
        """Create a sample image MediaFile."""
        return MediaFile(
            source_file="/test/image.jpg",
            file_name="image.jpg",
            mime_type="image/jpeg",
            container_format="",
            video_format="",
            video_scan_type="",
            audio_format="",
            is_live_photo_video=False,
            intermediate_file="",
            destination_file="",
            state=ProcessingState.Pending,
            video_stream_count=0,
            audio_stream_count=0,
        )

    def test_init(self, mock_services, sample_profiles):
        """Test ProcessWorker initialization."""
        files = []
        temp_folder = Path("/tmp/test")

        worker = ProcessWorker(
            files=files,
            profiles=sample_profiles,
            temp_folder=temp_folder,
            exiftool_service=mock_services["exiftool"],
            ffmpeg_service=mock_services["ffmpeg"],
            mediainfo_service=mock_services["mediainfo"],
        )

        assert worker.files == files
        assert worker.profiles == sample_profiles
        assert worker.temp_folder == temp_folder
        assert hasattr(worker, "signals")

    def test_log_methods(self, mock_services, sample_profiles):
        """Test that log methods emit signals."""
        worker = ProcessWorker(
            files=[],
            profiles=sample_profiles,
            temp_folder=Path("/tmp/test"),
            exiftool_service=mock_services["exiftool"],
            ffmpeg_service=mock_services["ffmpeg"],
            mediainfo_service=mock_services["mediainfo"],
        )

        log_signal = Mock()
        worker.signals.log_message.connect(log_signal)

        worker._log_info("Test info")
        log_signal.assert_called_with("INFO", "Test info")

        worker._log_warning("Test warning")
        log_signal.assert_called_with("WARNING", "Test warning")

        worker._log_error("Test error")
        log_signal.assert_called_with("ERROR", "Test error")

    def test_update_file_state(self, mock_services, sample_profiles, sample_video_file):
        """Test updating file state."""
        files = [sample_video_file]
        worker = ProcessWorker(
            files=files,
            profiles=sample_profiles,
            temp_folder=Path("/tmp/test"),
            exiftool_service=mock_services["exiftool"],
            ffmpeg_service=mock_services["ffmpeg"],
            mediainfo_service=mock_services["mediainfo"],
        )

        state_signal = Mock()
        worker.signals.file_state_changed.connect(state_signal)

        worker._update_file_state(0, ProcessingState.InProgress)

        assert files[0].state == ProcessingState.InProgress
        state_signal.assert_called_once_with(0, ProcessingState.InProgress)

    def test_create_intermediate_path(
        self, mock_services, sample_profiles, sample_video_file
    ):
        """Test creating intermediate file path."""
        worker = ProcessWorker(
            files=[sample_video_file],
            profiles=sample_profiles,
            temp_folder=Path("/tmp/test"),
            exiftool_service=mock_services["exiftool"],
            ffmpeg_service=mock_services["ffmpeg"],
            mediainfo_service=mock_services["mediainfo"],
        )

        path = worker._create_intermediate_path(sample_video_file, ".mp4")

        assert path.parent == Path("/tmp/test")
        assert path.suffix == ".mp4"
        assert len(path.stem) > 0  # Should have UUID in name

    def test_find_matching_profile_exact_match(
        self, mock_services, sample_profiles, sample_video_file
    ):
        """Test finding matching conversion profile."""
        worker = ProcessWorker(
            files=[sample_video_file],
            profiles=sample_profiles,
            temp_folder=Path("/tmp/test"),
            exiftool_service=mock_services["exiftool"],
            ffmpeg_service=mock_services["ffmpeg"],
            mediainfo_service=mock_services["mediainfo"],
        )

        profile = worker._find_matching_profile(sample_video_file)

        # sample_video_file is .mov, AVC, Progressive, AAC, not live photo
        # This matches the "iPhone/iPad Legacy (AVC)" profile from actual file
        assert profile is not None
        assert profile.VideoFormat == "AVC"
        assert profile.AudioFormat == "AAC"
        assert profile.OriginalFileExtension == ".mov"

    def test_find_matching_profile_no_match(
        self, mock_services, sample_profiles, sample_video_file
    ):
        """Test when no matching profile exists."""
        # Change to format combination that doesn't exist in profiles
        sample_video_file.video_format = "VP9"  # Not in any profile

        worker = ProcessWorker(
            files=[sample_video_file],
            profiles=sample_profiles,
            temp_folder=Path("/tmp/test"),
            exiftool_service=mock_services["exiftool"],
            ffmpeg_service=mock_services["ffmpeg"],
            mediainfo_service=mock_services["mediainfo"],
        )

        profile = worker._find_matching_profile(sample_video_file)

        assert profile is None

    def test_validate_audio_absence_live_photo(
        self, mock_services, sample_profiles, sample_video_file
    ):
        """Test audio validation for Live Photo videos."""
        sample_video_file.is_live_photo_video = True
        sample_video_file.audio_stream_count = 0

        worker = ProcessWorker(
            files=[sample_video_file],
            profiles=sample_profiles,
            temp_folder=Path("/tmp/test"),
            exiftool_service=mock_services["exiftool"],
            ffmpeg_service=mock_services["ffmpeg"],
            mediainfo_service=mock_services["mediainfo"],
        )

        result = worker._validate_audio_absence(sample_video_file)

        assert result is True  # Live Photos don't need audio

    def test_process_video_conversion_success(
        self, mock_services, sample_profiles, sample_video_file
    ):
        """Test successful video conversion."""
        # Change video file to match a profile that requires conversion (.mts with AC-3 audio)
        sample_video_file.source_file = "/test/video.mts"
        sample_video_file.file_name = "video.mts"
        sample_video_file.audio_format = "AC-3"
        sample_video_file.video_format = "AVC"
        sample_video_file.video_scan_type = "Progressive"

        mock_services["mediainfo"].validate_video_streams.return_value = (True, "")
        mock_services["ffmpeg"].convert_video.return_value = (True, "")
        mock_services["exiftool"].restore_metadata.return_value = True
        mock_services["exiftool"].set_file_dates.return_value = None

        # Mock organize_files to return a dict with any intermediate file mapping to a destination
        def organize_files_mock(file_paths, temp_folder, is_live_photo):
            return {path: Path(f"/dest/{path.name}") for path in file_paths}

        mock_services["exiftool"].organize_files.side_effect = organize_files_mock

        files = [sample_video_file]
        worker = ProcessWorker(
            files=files,
            profiles=sample_profiles,
            temp_folder=Path("/tmp/test"),
            exiftool_service=mock_services["exiftool"],
            ffmpeg_service=mock_services["ffmpeg"],
            mediainfo_service=mock_services["mediainfo"],
        )

        finished_signal = Mock()
        worker.signals.finished.connect(finished_signal)

        worker.run()

        # Verify conversion was called
        assert mock_services["ffmpeg"].convert_video.called
        finished_signal.assert_called_once()

    def test_process_video_validation_failed(
        self, mock_services, sample_profiles, sample_video_file
    ):
        """Test handling of invalid video file."""
        mock_services["file"].ensure_directory.return_value = (True, "")
        mock_services["mediainfo"].validate_video_streams.return_value = (
            False,
            "Invalid format",
        )

        files = [sample_video_file]
        worker = ProcessWorker(
            files=files,
            profiles=sample_profiles,
            temp_folder=Path("/tmp/test"),
            exiftool_service=mock_services["exiftool"],
            ffmpeg_service=mock_services["ffmpeg"],
            mediainfo_service=mock_services["mediainfo"],
        )

        state_signal = Mock()
        worker.signals.file_state_changed.connect(state_signal)

        worker.run()

        # Verify file was marked as error
        assert files[0].state == ProcessingState.Error

    def test_process_image_copy(
        self, mock_services, sample_profiles, sample_image_file
    ):
        """Test image file copying."""

        # Mock organize_files to return proper dict
        def organize_files_mock(file_paths, temp_folder, is_live_photo):
            return {path: Path(f"/dest/{path.name}") for path in file_paths}

        mock_services["exiftool"].organize_files.side_effect = organize_files_mock

        files = [sample_image_file]
        worker = ProcessWorker(
            files=files,
            profiles=sample_profiles,
            temp_folder=Path("/tmp/test"),
            exiftool_service=mock_services["exiftool"],
            ffmpeg_service=mock_services["ffmpeg"],
            mediainfo_service=mock_services["mediainfo"],
        )

        finished_signal = Mock()
        worker.signals.finished.connect(finished_signal)

        worker.run()

        # Verify finished signal was called
        finished_signal.assert_called_once()

    def test_process_error_handling(self, mock_services, sample_profiles):
        """Test error handling in run method."""
        worker = ProcessWorker(
            files=[],
            profiles=sample_profiles,
            temp_folder=Path("/tmp/test"),
            exiftool_service=mock_services["exiftool"],
            ffmpeg_service=mock_services["ffmpeg"],
            mediainfo_service=mock_services["mediainfo"],
        )

        error_signal = Mock()
        worker.signals.error.connect(error_signal)

        # Mock mkdir to raise an error
        with patch.object(Path, "mkdir", side_effect=Exception("Test error")):
            worker.run()

        # Verify error signal was emitted
        assert error_signal.called

    def test_organize_files_success(
        self, mock_services, sample_profiles, sample_video_file
    ):
        """Test successful file organization."""
        mock_services["mediainfo"].validate_video_streams.return_value = (True, "")

        # Mock organize_files to return proper dict
        def organize_files_mock(file_paths, temp_folder, is_live_photo):
            return {path: Path(f"/dest/{path.name}") for path in file_paths}

        mock_services["exiftool"].organize_files.side_effect = organize_files_mock

        files = [sample_video_file]
        # Set video to copy mode (no conversion)
        sample_video_file.video_format = "AVC"

        # Mock shutil.copy2 to avoid file system operations
        with patch("shutil.copy2"):
            worker = ProcessWorker(
                files=files,
                profiles=sample_profiles,
                temp_folder=Path("/tmp/test"),
                exiftool_service=mock_services["exiftool"],
                ffmpeg_service=mock_services["ffmpeg"],
                mediainfo_service=mock_services["mediainfo"],
            )

            worker.run()

        # Verify organize was called
        assert mock_services["exiftool"].organize_files.called

    def test_organize_files_failure(
        self, mock_services, sample_profiles, sample_video_file
    ):
        """Test handling of organization failure."""
        mock_services["mediainfo"].validate_video_streams.return_value = (True, "")
        # Empty dict means no files were organized
        mock_services["exiftool"].organize_files.return_value = {}

        files = [sample_video_file]
        sample_video_file.video_format = "AVC"

        # Mock shutil.copy2 to avoid file system operations
        with patch("shutil.copy2"):
            worker = ProcessWorker(
                files=files,
                profiles=sample_profiles,
                temp_folder=Path("/tmp/test"),
                exiftool_service=mock_services["exiftool"],
                ffmpeg_service=mock_services["ffmpeg"],
                mediainfo_service=mock_services["mediainfo"],
            )

            log_signal = Mock()
            worker.signals.log_message.connect(log_signal)

            worker.run()

        # With empty dict, file should show as pending since destination is None
        # Check that organize was called
        assert mock_services["exiftool"].organize_files.called
