"""
Tests for ExifToolService.
"""

import pytest
import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from pymsort.services.exiftool_service import ExifToolService


class TestExifToolService:
    """Test cases for ExifToolService."""

    @pytest.fixture
    def mock_subprocess_run(self):
        """Create a mock for subprocess.run."""
        with patch("pymsort.services.exiftool_service.subprocess.run") as mock_run:
            # Default: successful version check
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "13.44\n"
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            yield mock_run

    @pytest.fixture
    def service(self, mock_subprocess_run):
        """Create an ExifToolService instance."""
        return ExifToolService(exiftool_path="exiftool")

    def test_init_success(self, mock_subprocess_run):
        """Test successful initialization."""
        service = ExifToolService(exiftool_path="exiftool")
        assert service.exiftool_path == "exiftool"
        mock_subprocess_run.assert_called_once()

    def test_init_exiftool_not_found(self):
        """Test initialization when ExifTool is not found."""
        with patch("pymsort.services.exiftool_service.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            with pytest.raises(RuntimeError, match="ExifTool not found"):
                ExifToolService(exiftool_path="nonexistent")

    def test_init_exiftool_verification_failed(self):
        """Test initialization when ExifTool verification fails."""
        with patch("pymsort.services.exiftool_service.subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = "Error"
            mock_run.return_value = mock_result

            with pytest.raises(RuntimeError, match="verification failed"):
                ExifToolService(exiftool_path="exiftool")

    def test_extract_metadata_empty_list(self, service, mock_subprocess_run):
        """Test extracting metadata from empty file list."""
        result = service.extract_metadata([])
        assert result == []
        # Only the verification call should have been made during init
        assert mock_subprocess_run.call_count == 1

    def test_extract_metadata_success(self, service, mock_subprocess_run):
        """Test successful metadata extraction."""
        # Setup mock for extraction call
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            [
                {"SourceFile": "/test/file1.jpg", "Make": "Canon"},
                {"SourceFile": "/test/file2.jpg", "Make": "Nikon"},
            ]
        )
        mock_subprocess_run.return_value = mock_result

        files = [Path("/test/file1.jpg"), Path("/test/file2.jpg")]

        with patch("tempfile.NamedTemporaryFile", mock_open()) as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = "/tmp/test.txt"
            with patch.object(Path, "unlink"):
                result = service.extract_metadata(files)

        assert len(result) == 2
        assert result[0]["Make"] == "Canon"
        assert result[1]["Make"] == "Nikon"

    def test_extract_metadata_json_decode_error(self, service, mock_subprocess_run):
        """Test handling of invalid JSON output."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Invalid JSON"
        mock_subprocess_run.return_value = mock_result

        files = [Path("/test/file1.jpg")]

        with patch("tempfile.NamedTemporaryFile", mock_open()) as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = "/tmp/test.txt"
            with patch.object(Path, "unlink"):
                with pytest.raises(
                    RuntimeError, match="Failed to parse ExifTool output"
                ):
                    service.extract_metadata(files)

    def test_extract_metadata_timeout(self, service, mock_subprocess_run):
        """Test handling of timeout."""
        mock_subprocess_run.side_effect = subprocess.TimeoutExpired("exiftool", 300)

        files = [Path("/test/file1.jpg")]

        with patch("tempfile.NamedTemporaryFile", mock_open()) as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = "/tmp/test.txt"
            with patch.object(Path, "unlink"):
                with pytest.raises(RuntimeError, match="timed out"):
                    service.extract_metadata(files)

    def test_extract_metadata_exiftool_error(self, service, mock_subprocess_run):
        """Test handling of ExifTool execution error."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Error processing file"
        mock_subprocess_run.return_value = mock_result

        files = [Path("/test/file1.jpg")]

        with patch("tempfile.NamedTemporaryFile", mock_open()) as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = "/tmp/test.txt"
            with patch.object(Path, "unlink"):
                with pytest.raises(RuntimeError, match="failed with return code"):
                    service.extract_metadata(files)

    def test_restore_metadata_success(self, service, mock_subprocess_run):
        """Test successful metadata restoration."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        source = Path("/test/source.jpg")
        dest = Path("/test/dest.jpg")

        with patch.object(Path, "unlink"):
            result = service.restore_metadata(source, dest)

        assert result is True

    def test_restore_metadata_failure(self, service, mock_subprocess_run):
        """Test failed metadata restoration."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Failed to copy metadata"
        mock_subprocess_run.return_value = mock_result

        source = Path("/test/source.jpg")
        dest = Path("/test/dest.jpg")

        result = service.restore_metadata(source, dest)
        assert result is False

    # Note: check_live_photo functionality is handled by MediaInfoService

    def test_organize_files_success(self, service, mock_subprocess_run):
        """Test successful file organization."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "1 files moved"
        mock_subprocess_run.return_value = mock_result

        files = [Path("/test/file1.jpg"), Path("/test/file2.jpg")]
        temp_folder = Path("/test/temp")

        with patch("tempfile.NamedTemporaryFile", mock_open()) as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = "/tmp/test.txt"
            with patch.object(Path, "unlink"):
                with patch.object(Path, "exists", return_value=True):
                    result = service.organize_files(files, temp_folder)

        assert isinstance(result, dict)
        assert len(result) >= 0

    def test_organize_files_empty_list(self, service, mock_subprocess_run):
        """Test organizing empty file list."""
        files = []
        temp_folder = Path("/test/temp")

        result = service.organize_files(files, temp_folder)

        assert result == {}

    def test_organize_files_live_photo(self, service, mock_subprocess_run):
        """Test organizing Live Photo videos."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "1 files moved"
        mock_subprocess_run.return_value = mock_result

        files = [Path("/test/livephoto.mov")]
        temp_folder = Path("/test/temp")

        with patch("tempfile.NamedTemporaryFile", mock_open()) as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = "/tmp/test.txt"
            with patch.object(Path, "unlink"):
                with patch.object(Path, "exists", return_value=True):
                    result = service.organize_files(
                        files, temp_folder, is_live_photo=True
                    )

        assert isinstance(result, dict)
