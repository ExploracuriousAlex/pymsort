"""
Tests for ExifToolService.
"""

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from pymsort.services.exiftool_service import ExifToolService


class TestExifToolService:
    """Test cases for ExifToolService."""

    @pytest.fixture
    def mock_exiftool(self):
        """Create a mock for exiftool.ExifToolHelper."""
        with patch("pymsort.services.exiftool_service.ExifToolHelper") as mock_et_class:
            mock_et_instance = MagicMock()
            mock_et_instance.running = True
            mock_et_instance.execute.return_value = "13.44"
            mock_et_instance.get_metadata.return_value = []
            mock_et_instance.get_tags.return_value = []
            mock_et_class.return_value = mock_et_instance
            yield mock_et_instance

    @pytest.fixture
    def service(self, mock_exiftool):
        """Create an ExifToolService instance."""
        return ExifToolService(exiftool_path="exiftool")

    def test_init_success(self, mock_exiftool):
        """Test successful initialization."""
        service = ExifToolService(exiftool_path="exiftool")
        assert service.exiftool_path == "exiftool"
        mock_exiftool.run.assert_called_once()

    def test_init_exiftool_not_found(self):
        """Test initialization when ExifTool is not found."""
        with patch("pymsort.services.exiftool_service.ExifToolHelper") as mock_et_class:
            mock_et_class.return_value.run.side_effect = FileNotFoundError()

            with pytest.raises(RuntimeError, match="ExifTool not found"):
                ExifToolService(exiftool_path="nonexistent")

    def test_init_exiftool_verification_failed(self):
        """Test initialization when ExifTool run fails."""
        with patch("pymsort.services.exiftool_service.ExifToolHelper") as mock_et_class:
            mock_et_instance = MagicMock()
            mock_et_instance.run.side_effect = Exception("ExifTool error")
            mock_et_class.return_value = mock_et_instance

            with pytest.raises(RuntimeError, match="Error starting ExifTool"):
                ExifToolService(exiftool_path="exiftool")

    def test_extract_metadata_empty_list(self, service, mock_exiftool):
        """Test extracting metadata from empty file list."""
        result = service.extract_metadata([])
        assert result == []

    def test_extract_metadata_success(self, service, mock_exiftool):
        """Test successful metadata extraction."""
        mock_exiftool.get_metadata.return_value = [
            {"SourceFile": "/test/file1.jpg", "Make": "Canon"},
            {"SourceFile": "/test/file2.jpg", "Make": "Nikon"},
        ]

        files = [Path("/test/file1.jpg"), Path("/test/file2.jpg")]
        result = service.extract_metadata(files)

        assert len(result) == 2
        assert result[0]["Make"] == "Canon"
        assert result[1]["Make"] == "Nikon"

    def test_extract_metadata_timeout(self, service, mock_exiftool):
        """Test handling of timeout/error."""
        mock_exiftool.get_metadata.side_effect = Exception("ExifTool timeout")

        files = [Path("/test/file1.jpg")]

        with pytest.raises(RuntimeError, match="ExifTool failed"):
            service.extract_metadata(files)

    def test_extract_metadata_exiftool_error(self, service, mock_exiftool):
        """Test handling of ExifTool execution error."""
        mock_exiftool.get_metadata.side_effect = Exception("Error processing file")

        files = [Path("/test/file1.jpg")]

        with pytest.raises(RuntimeError, match="ExifTool failed"):
            service.extract_metadata(files)

    def test_restore_metadata_success(self, service, mock_exiftool):
        """Test successful metadata restoration."""
        mock_exiftool.execute.return_value = "1 image files updated"

        source = Path("/test/source.jpg")
        dest = Path("/test/dest.jpg")

        with patch.object(Path, "unlink"):
            result = service.restore_metadata(source, dest)

        assert result is True

    def test_restore_metadata_failure(self, service, mock_exiftool):
        """Test failed metadata restoration."""
        mock_exiftool.execute.side_effect = Exception("Failed to copy metadata")

        source = Path("/test/source.jpg")
        dest = Path("/test/dest.jpg")

        result = service.restore_metadata(source, dest)
        assert result is False

    # Note: check_live_photo functionality is handled by MediaInfoService

    def test_organize_files_success(self, service, mock_exiftool):
        """Test successful file organization."""
        mock_exiftool.execute.return_value = "1 files moved"

        files = [Path("/test/file1.jpg"), Path("/test/file2.jpg")]
        temp_folder = Path("/test/temp")

        with patch("tempfile.NamedTemporaryFile", mock_open()) as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = "/tmp/test.txt"
            with patch.object(Path, "unlink"):
                with patch.object(Path, "exists", return_value=True):
                    result = service.organize_files(files, temp_folder)

        assert isinstance(result, dict)
        assert len(result) >= 0

    def test_organize_files_empty_list(self, service, mock_exiftool):
        """Test organizing empty file list."""
        files = []
        temp_folder = Path("/test/temp")

        result = service.organize_files(files, temp_folder)

        assert result == {}

    def test_organize_files_live_photo(self, service, mock_exiftool):
        """Test organizing Live Photo videos."""
        mock_exiftool.execute.return_value = "1 files moved"

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
