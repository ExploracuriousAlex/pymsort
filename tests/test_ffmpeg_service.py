"""
Tests for FFmpegService.
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from pymsort.services.ffmpeg_service import FFmpegService


class TestFFmpegService:
    """Test cases for FFmpegService."""

    @pytest.fixture
    def mock_subprocess_run(self):
        """Create a mock for subprocess.run."""
        with patch("pymsort.services.ffmpeg_service.subprocess.run") as mock_run:
            # Default: successful version check
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "ffmpeg version n8.0.1\nconfiguration: ...\n"
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            yield mock_run

    @pytest.fixture
    def service(self, mock_subprocess_run):
        """Create an FFmpegService instance."""
        return FFmpegService(ffmpeg_path="ffmpeg")

    def test_init_success(self, mock_subprocess_run):
        """Test successful initialization."""
        service = FFmpegService(ffmpeg_path="ffmpeg")
        assert service.ffmpeg_path == "ffmpeg"
        mock_subprocess_run.assert_called_once()

    def test_init_ffmpeg_not_found(self):
        """Test initialization when FFmpeg is not found."""
        with patch("pymsort.services.ffmpeg_service.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            with pytest.raises(RuntimeError, match="FFmpeg not found"):
                FFmpegService(ffmpeg_path="nonexistent")

    def test_init_ffmpeg_verification_failed(self):
        """Test initialization when FFmpeg verification fails."""
        with patch("pymsort.services.ffmpeg_service.subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = "Error"
            mock_run.return_value = mock_result

            with pytest.raises(RuntimeError, match="verification failed"):
                FFmpegService(ffmpeg_path="ffmpeg")

    def test_check_libfdk_aac_support_available(self, service, mock_subprocess_run):
        """Test detection of libfdk_aac support."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Encoder libfdk_aac [Fraunhofer FDK AAC]\n"
        mock_subprocess_run.return_value = mock_result

        result = service.check_libfdk_aac_support()
        assert result is True

    def test_check_libfdk_aac_support_not_available(self, service, mock_subprocess_run):
        """Test when libfdk_aac is not supported."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Unknown encoder libfdk_aac\n"
        mock_subprocess_run.return_value = mock_result

        result = service.check_libfdk_aac_support()
        assert result is False

    def test_check_libfdk_aac_support_exception(self, service, mock_subprocess_run):
        """Test handling of exception during libfdk_aac check."""
        mock_subprocess_run.side_effect = Exception("Test error")

        result = service.check_libfdk_aac_support()
        assert result is False

    def test_convert_video_success(self, service, mock_subprocess_run):
        """Test successful video conversion."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        source = Path("/test/source.mp4")
        dest = Path("/test/dest.mp4")
        command_template = "ffmpeg -i %s %s"

        # Mock file operations
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "stat") as mock_stat:
                mock_stat.return_value.st_size = 1000
                success, message = service.convert_video(source, dest, command_template)

        assert success is True
        assert message == ""

    def test_convert_video_ffmpeg_error(self, service, mock_subprocess_run):
        """Test video conversion with FFmpeg error."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Invalid codec"
        mock_subprocess_run.return_value = mock_result

        source = Path("/test/source.mp4")
        dest = Path("/test/dest.mp4")
        command_template = "ffmpeg -i %s %s"

        success, message = service.convert_video(source, dest, command_template)

        assert success is False
        assert "FFmpeg failed" in message
        assert "Invalid codec" in message

    def test_convert_video_destination_not_created(self, service, mock_subprocess_run):
        """Test when destination file is not created."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        source = Path("/test/source.mp4")
        dest = Path("/test/dest.mp4")
        command_template = "ffmpeg -i %s %s"

        # Mock destination file doesn't exist
        with patch.object(Path, "exists", return_value=False):
            success, message = service.convert_video(source, dest, command_template)

        assert success is False
        assert "not created" in message

    def test_convert_video_destination_empty(self, service, mock_subprocess_run):
        """Test when destination file is empty."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        source = Path("/test/source.mp4")
        dest = Path("/test/dest.mp4")
        command_template = "ffmpeg -i %s %s"

        # Mock destination file exists but is empty
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "stat") as mock_stat:
                mock_stat.return_value.st_size = 0
                success, message = service.convert_video(source, dest, command_template)

        assert success is False
        assert "empty" in message

    def test_convert_video_timeout(self, service, mock_subprocess_run):
        """Test video conversion timeout."""
        mock_subprocess_run.side_effect = subprocess.TimeoutExpired("ffmpeg", 3600)

        source = Path("/test/source.mp4")
        dest = Path("/test/dest.mp4")
        command_template = "ffmpeg -i %s %s"

        success, message = service.convert_video(source, dest, command_template)

        assert success is False
        assert "timed out" in message.lower()

    def test_convert_video_exception(self, service, mock_subprocess_run):
        """Test handling of unexpected exception during conversion."""
        mock_subprocess_run.side_effect = Exception("Unexpected error")

        source = Path("/test/source.mp4")
        dest = Path("/test/dest.mp4")
        command_template = "ffmpeg -i %s %s"

        success, message = service.convert_video(source, dest, command_template)

        assert success is False
        assert "Error during video conversion" in message

    def test_convert_video_command_formatting(self, service, mock_subprocess_run):
        """Test that command template is correctly formatted with file paths."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        source = Path("/test/source.mp4")
        dest = Path("/test/dest.mp4")
        command_template = "ffmpeg -i '%s' -c:v libx264 '%s'"

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "stat") as mock_stat:
                mock_stat.return_value.st_size = 1000
                service.convert_video(source, dest, command_template)

        # Verify subprocess was called with shell=True
        assert mock_subprocess_run.called
        call_args = mock_subprocess_run.call_args
        assert call_args[1]["shell"] is True
