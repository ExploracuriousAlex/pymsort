"""Tests for startup checks."""

from unittest.mock import MagicMock, patch

from pymsort.utils.startup_checks import (
    check_exiftool,
    check_ffmpeg,
    check_libfdk_aac,
    run_all_checks,
)


class TestCheckExifTool:
    """Test cases for check_exiftool function."""

    @patch("pymsort.services.exiftool_service.ExifToolHelper")
    def test_exiftool_available(self, mock_helper_class):
        """Test successful ExifTool check."""
        # Setup mock
        mock_helper = MagicMock()
        mock_helper.version = "12.50"
        mock_helper.running = True
        mock_helper_class.return_value = mock_helper

        success, message = check_exiftool()

        assert success is True
        assert "12.50" in message

    @patch("pymsort.services.exiftool_service.ExifToolHelper")
    def test_exiftool_not_found(self, mock_helper_class):
        """Test ExifTool not found."""
        # Simulate FileNotFoundError when tool not found
        mock_helper_class.side_effect = FileNotFoundError("ExifTool not found")

        success, message = check_exiftool()

        assert success is False
        assert "not found" in message.lower() or "ExifTool" in message

    @patch("pymsort.services.exiftool_service.ExifToolHelper")
    def test_exiftool_unexpected_error(self, mock_helper_class):
        """Test unexpected error during ExifTool check."""
        mock_helper_class.side_effect = Exception("Unexpected error")

        success, message = check_exiftool()

        assert success is False
        assert "Error starting ExifTool" in message or "Unexpected error" in message


class TestCheckFFmpeg:
    """Test cases for check_ffmpeg function."""

    @patch("pymsort.utils.startup_checks.config")
    @patch("pymsort.utils.startup_checks.subprocess.run")
    def test_ffmpeg_available(self, mock_run, mock_config):
        """Test successful FFmpeg check."""
        mock_config.ffmpeg_path = "/usr/local/bin/ffmpeg"
        mock_run.return_value = MagicMock(
            returncode=0, stdout="ffmpeg version 6.0\n", stderr=""
        )

        success, message = check_ffmpeg()

        assert success is True
        assert "ffmpeg version" in message.lower()
        mock_run.assert_called_once()

    @patch("pymsort.utils.startup_checks.config")
    def test_ffmpeg_not_configured(self, mock_config):
        """Test FFmpeg not configured in config."""
        mock_config.ffmpeg_path = None

        success, message = check_ffmpeg()

        assert success is False
        assert "not found" in message.lower()

    @patch("pymsort.utils.startup_checks.config")
    @patch("pymsort.utils.startup_checks.subprocess.run")
    def test_ffmpeg_error_code(self, mock_run, mock_config):
        """Test FFmpeg returns error code."""
        mock_config.ffmpeg_path = "/usr/local/bin/ffmpeg"
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Error message"
        )

        success, message = check_ffmpeg()

        assert success is False
        assert "error" in message.lower()

    @patch("pymsort.utils.startup_checks.config")
    @patch("pymsort.utils.startup_checks.subprocess.run")
    def test_ffmpeg_timeout(self, mock_run, mock_config):
        """Test FFmpeg subprocess timeout."""
        mock_config.ffmpeg_path = "/usr/local/bin/ffmpeg"
        mock_run.side_effect = TimeoutError("Command timed out")

        success, message = check_ffmpeg()

        assert success is False
        assert "Failed to run FFmpeg" in message


class TestCheckLibFdkAac:
    """Test cases for check_libfdk_aac function."""

    @patch("pymsort.utils.startup_checks.config")
    @patch("pymsort.utils.startup_checks.subprocess.run")
    def test_libfdk_aac_available(self, mock_run, mock_config):
        """Test libfdk_aac encoder is available."""
        mock_config.ffmpeg_path = "/usr/local/bin/ffmpeg"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Encoders:\n A..... libfdk_aac           Fraunhofer FDK AAC\n",
            stderr="",
        )

        success, message = check_libfdk_aac()

        assert success is True
        assert "libfdk_aac" in message

    @patch("pymsort.utils.startup_checks.config")
    @patch("pymsort.utils.startup_checks.subprocess.run")
    def test_libfdk_aac_not_available(self, mock_run, mock_config):
        """Test libfdk_aac encoder is not available."""
        mock_config.ffmpeg_path = "/usr/local/bin/ffmpeg"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Encoders:\n A..... aac    Native AAC encoder\n",
            stderr="",
        )

        success, message = check_libfdk_aac()

        assert success is False
        assert "does not have libfdk_aac" in message

    @patch("pymsort.utils.startup_checks.config")
    def test_libfdk_aac_ffmpeg_not_available(self, mock_config):
        """Test check when FFmpeg is not available."""
        mock_config.ffmpeg_path = None

        success, message = check_libfdk_aac()

        assert success is False
        assert "not available" in message.lower()


class TestRunAllChecks:
    """Test cases for run_all_checks function."""

    @patch("pymsort.utils.startup_checks.check_libfdk_aac")
    @patch("pymsort.utils.startup_checks.check_ffmpeg")
    @patch("pymsort.utils.startup_checks.check_exiftool")
    @patch("pymsort.utils.startup_checks.config")
    def test_all_checks_pass(
        self, mock_config, mock_exiftool, mock_ffmpeg, mock_libfdk
    ):
        """Test when all checks pass."""
        mock_config.auto_discover_tools = MagicMock()
        mock_config.ensure_temp_dir = MagicMock(return_value=True)
        mock_config.temp_dir = "/tmp/test"
        mock_exiftool.return_value = (True, "ExifTool 12.50")
        mock_ffmpeg.return_value = (True, "ffmpeg version 6.0")
        mock_libfdk.return_value = (True, "libfdk_aac available")

        all_passed, messages = run_all_checks()

        assert all_passed is True
        assert len(messages) == 4  # exiftool, ffmpeg, libfdk, temp_dir
        assert all("✓" in msg or "✓" in msg for msg in messages[:3])
        mock_config.auto_discover_tools.assert_called_once()

    @patch("pymsort.utils.startup_checks.check_libfdk_aac")
    @patch("pymsort.utils.startup_checks.check_ffmpeg")
    @patch("pymsort.utils.startup_checks.check_exiftool")
    @patch("pymsort.utils.startup_checks.config")
    def test_exiftool_fails(self, mock_config, mock_exiftool, mock_ffmpeg, mock_libfdk):
        """Test when ExifTool check fails."""
        mock_config.auto_discover_tools = MagicMock()
        mock_exiftool.return_value = (False, "ExifTool not found")
        mock_ffmpeg.return_value = (True, "ffmpeg version 6.0")
        mock_libfdk.return_value = (True, "libfdk_aac available")

        all_passed, messages = run_all_checks()

        assert all_passed is False
        assert "✗" in messages[0]
        assert "✓" in messages[1]

    @patch("pymsort.utils.startup_checks.check_libfdk_aac")
    @patch("pymsort.utils.startup_checks.check_ffmpeg")
    @patch("pymsort.utils.startup_checks.check_exiftool")
    @patch("pymsort.utils.startup_checks.config")
    def test_ffmpeg_fails(self, mock_config, mock_exiftool, mock_ffmpeg, mock_libfdk):
        """Test when FFmpeg check fails."""
        mock_config.auto_discover_tools = MagicMock()
        mock_exiftool.return_value = (True, "ExifTool 12.50")
        mock_ffmpeg.return_value = (False, "FFmpeg not found")
        mock_libfdk.return_value = (False, "FFmpeg not available")

        all_passed, messages = run_all_checks()

        assert all_passed is False
        assert "✓" in messages[0]
        assert "✗" in messages[1]

    @patch("pymsort.utils.startup_checks.check_libfdk_aac")
    @patch("pymsort.utils.startup_checks.check_ffmpeg")
    @patch("pymsort.utils.startup_checks.check_exiftool")
    @patch("pymsort.utils.startup_checks.config")
    def test_all_checks_fail(
        self, mock_config, mock_exiftool, mock_ffmpeg, mock_libfdk
    ):
        """Test when all checks fail."""
        mock_config.auto_discover_tools = MagicMock()
        mock_config.ensure_temp_dir = MagicMock(return_value=False)
        mock_exiftool.return_value = (False, "ExifTool not found")
        mock_ffmpeg.return_value = (False, "FFmpeg not found")
        mock_libfdk.return_value = (False, "FFmpeg not available")

        all_passed, messages = run_all_checks()

        assert all_passed is False
        # Check that first 3 messages have ✗
        assert "✗" in messages[0]
        assert "✗" in messages[1]
        assert "✗" in messages[2]  # temp_dir failed
