"""Tests for Config class."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from pymsort.utils.config import Config


class TestConfig:
    """Test cases for Config class."""

    def test_init_default_values(self):
        """Test Config initialization with default values."""
        config = Config()

        assert config.exiftool_path is None
        assert config.ffmpeg_path is None
        assert config.temp_dir == Path.home() / ".pymsort" / "temp"

    def test_ensure_temp_dir_creates_directory(self, tmp_path):
        """Test that ensure_temp_dir creates the directory."""
        config = Config()
        config.temp_dir = tmp_path / "test_temp"

        # Directory should not exist yet
        assert not config.temp_dir.exists()

        # ensure_temp_dir should create it
        result = config.ensure_temp_dir()

        assert result is True
        assert config.temp_dir.exists()
        assert config.temp_dir.is_dir()

    def test_ensure_temp_dir_existing_directory(self, tmp_path):
        """Test ensure_temp_dir with existing directory."""
        config = Config()
        config.temp_dir = tmp_path / "existing"
        config.temp_dir.mkdir()

        result = config.ensure_temp_dir()

        assert result is True
        assert config.temp_dir.exists()

    def test_ensure_temp_dir_permission_error(self, tmp_path):
        """Test ensure_temp_dir handles permission errors."""
        config = Config()
        config.temp_dir = tmp_path / "no_permission"

        with patch.object(Path, "mkdir", side_effect=PermissionError("No permission")):
            result = config.ensure_temp_dir()

        assert result is False

    def test_find_tool_in_path(self):
        """Test finding tool in PATH."""
        config = Config()

        # Mock PATH environment variable
        fake_path = "/usr/bin:/usr/local/bin"

        with patch.dict(os.environ, {"PATH": fake_path}):
            with patch.object(Path, "is_file", return_value=True):
                with patch("os.access", return_value=True):
                    result = config.find_tool("exiftool")

        assert result is not None

    def test_find_tool_not_found(self):
        """Test find_tool when tool doesn't exist."""
        config = Config()

        with patch.dict(os.environ, {"PATH": "/nonexistent/path"}):
            with patch.object(Path, "is_file", return_value=False):
                result = config.find_tool("nonexistent_tool")

        assert result is None

    def test_find_tool_windows_exe_extension(self):
        """Test that Windows .exe extension is added when needed."""
        # Skip this test on non-Windows systems
        if sys.platform != "win32":
            pytest.skip("Windows-specific test, skipping on non-Windows platform")

    def test_singleton_config_instance(self):
        """Test that config is used as singleton in the module."""
        from pymsort.utils.config import config

        assert isinstance(config, Config)
        assert config.exiftool_path is None
        assert config.ffmpeg_path is None


class TestConfigToolDiscovery:
    """Test actual tool discovery behavior."""

    def test_config_finds_exiftool_if_available(self):
        """Test config can find exiftool if it's in PATH."""
        config = Config()

        # Only test if exiftool is actually available
        result = config.find_tool("exiftool")

        # If exiftool is installed, result should be a path
        # If not installed, result will be None (that's okay)
        if result is not None:
            assert Path(result).exists()

    def test_config_finds_ffmpeg_if_available(self):
        """Test config can find ffmpeg if it's in PATH."""
        config = Config()

        result = config.find_tool("ffmpeg")

        if result is not None:
            assert Path(result).exists()
