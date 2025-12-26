"""
Tests for MediaInfoService.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pymsort.services.mediainfo_service import MediaInfoService


class TestMediaInfoService:
    """Test cases for MediaInfoService."""

    @pytest.fixture
    def mock_mediainfo(self):
        """Create a mock MediaInfo object."""
        with patch("pymsort.services.mediainfo_service.MediaInfo") as mock:
            yield mock

    def test_analyze_file_success_video(self, mock_mediainfo):
        """Test successful analysis of a video file."""
        # Create mock MediaInfo with video and audio tracks
        mock_info = MagicMock()

        mock_general = MagicMock()
        mock_general.format = "MPEG-4"
        mock_general.internet_media_type = "video/mp4"
        mock_general.file_size = 1000000
        mock_general.duration = 30000
        mock_general.comapplequicktimecontentidentifier = ""

        mock_video = MagicMock()
        mock_video.format = "AVC"
        mock_video.scan_type = "Progressive"
        mock_video.width = 1920
        mock_video.height = 1080
        mock_video.frame_rate = 30.0
        mock_video.codec_id = "avc1"

        mock_audio = MagicMock()
        mock_audio.format = "AAC"
        mock_audio.channel_s = 2
        mock_audio.sampling_rate = 48000
        mock_audio.codec_id = "mp4a"

        mock_info.general_tracks = [mock_general]
        mock_info.video_tracks = [mock_video]
        mock_info.audio_tracks = [mock_audio]

        mock_mediainfo.parse.return_value = mock_info

        result = MediaInfoService.analyze_file(Path("/test/video.mp4"))

        assert result is not None
        assert result["general"]["format"] == "MPEG-4"
        assert result["general"]["mime_type"] == "video/mp4"
        assert result["general"]["is_live_photo"] is False
        assert result["video"]["format"] == "AVC"
        assert result["video"]["scan_type"] == "Progressive"
        assert result["video"]["stream_count"] == 1
        assert result["audio"]["format"] == "AAC"
        assert result["audio"]["stream_count"] == 1

    def test_analyze_file_success_image(self, mock_mediainfo):
        """Test successful analysis of an image file."""
        mock_info = MagicMock()

        mock_general = MagicMock()
        mock_general.format = "JPEG"
        mock_general.internet_media_type = "image/jpeg"
        mock_general.file_size = 500000
        mock_general.duration = None
        mock_general.comapplequicktimecontentidentifier = None

        mock_info.general_tracks = [mock_general]
        mock_info.video_tracks = []
        mock_info.audio_tracks = []

        mock_mediainfo.parse.return_value = mock_info

        result = MediaInfoService.analyze_file(Path("/test/image.jpg"))

        assert result is not None
        assert result["general"]["format"] == "JPEG"
        assert result["general"]["mime_type"] == "image/jpeg"
        assert result["video"]["stream_count"] == 0
        assert result["audio"]["stream_count"] == 0

    def test_analyze_file_live_photo(self, mock_mediainfo):
        """Test detection of Live Photo video."""
        mock_info = MagicMock()

        mock_general = MagicMock()
        mock_general.format = "MPEG-4"
        mock_general.internet_media_type = "video/quicktime"
        mock_general.file_size = 1000000
        mock_general.duration = 3000
        mock_general.comapplequicktimecontentidentifier = "ABC123"

        mock_video = MagicMock()
        mock_video.format = "AVC"
        mock_video.scan_type = "Progressive"
        mock_video.width = 1920
        mock_video.height = 1080
        mock_video.frame_rate = 30.0
        mock_video.codec_id = "avc1"

        mock_info.general_tracks = [mock_general]
        mock_info.video_tracks = [mock_video]
        mock_info.audio_tracks = []

        mock_mediainfo.parse.return_value = mock_info

        result = MediaInfoService.analyze_file(Path("/test/livephoto.mov"))

        assert result is not None
        assert result["general"]["is_live_photo"] is True

    def test_analyze_file_parsing_failed(self, mock_mediainfo):
        """Test when MediaInfo returns a string (parsing error)."""
        mock_mediainfo.parse.return_value = "Error parsing file"

        result = MediaInfoService.analyze_file(Path("/test/bad.mp4"))

        assert result is None

    def test_analyze_file_exception(self, mock_mediainfo):
        """Test handling of exception during analysis."""
        mock_mediainfo.parse.side_effect = Exception("Test error")

        result = MediaInfoService.analyze_file(Path("/test/error.mp4"))

        assert result is None

    def test_analyze_file_missing_format(self, mock_mediainfo):
        """Test handling of None format values."""
        mock_info = MagicMock()

        mock_general = MagicMock()
        mock_general.format = None
        mock_general.internet_media_type = None
        mock_general.file_size = 1000000
        mock_general.duration = 30000
        mock_general.comapplequicktimecontentidentifier = None

        mock_video = MagicMock()
        mock_video.format = None
        mock_video.scan_type = None
        mock_video.width = 1920
        mock_video.height = 1080
        mock_video.frame_rate = 30.0
        mock_video.codec_id = None

        mock_info.general_tracks = [mock_general]
        mock_info.video_tracks = [mock_video]
        mock_info.audio_tracks = []

        mock_mediainfo.parse.return_value = mock_info

        result = MediaInfoService.analyze_file(Path("/test/unknown.mp4"))

        assert result is not None
        assert result["general"]["format"] == "Unknown"
        assert result["general"]["mime_type"] == "Unknown"
        assert result["video"]["format"] == "Unknown"

    def test_get_mime_type_success(self, mock_mediainfo):
        """Test successful MIME type retrieval."""
        mock_info = MagicMock()
        mock_general = MagicMock()
        mock_general.internet_media_type = "video/mp4"
        mock_info.general_tracks = [mock_general]

        mock_mediainfo.parse.return_value = mock_info

        result = MediaInfoService.get_mime_type(Path("/test/video.mp4"))

        assert result == "video/mp4"

    def test_get_mime_type_no_general_track(self, mock_mediainfo):
        """Test MIME type when no general track exists."""
        mock_info = MagicMock()
        mock_info.general_tracks = []

        mock_mediainfo.parse.return_value = mock_info

        result = MediaInfoService.get_mime_type(Path("/test/video.mp4"))

        assert result == "unknown"

    def test_get_mime_type_none_value(self, mock_mediainfo):
        """Test MIME type when value is None."""
        mock_info = MagicMock()
        mock_general = MagicMock()
        mock_general.internet_media_type = None
        mock_info.general_tracks = [mock_general]

        mock_mediainfo.parse.return_value = mock_info

        result = MediaInfoService.get_mime_type(Path("/test/video.mp4"))

        assert result == "unknown"

    def test_get_mime_type_parsing_failed(self, mock_mediainfo):
        """Test MIME type when parsing fails."""
        mock_mediainfo.parse.return_value = "Error parsing"

        result = MediaInfoService.get_mime_type(Path("/test/bad.mp4"))

        assert result == "unknown"

    def test_get_mime_type_exception(self, mock_mediainfo):
        """Test MIME type when exception occurs."""
        mock_mediainfo.parse.side_effect = Exception("Test error")

        result = MediaInfoService.get_mime_type(Path("/test/error.mp4"))

        assert result == "unknown"

    def test_is_video_file_true(self, mock_mediainfo):
        """Test video file detection."""
        mock_info = MagicMock()
        mock_general = MagicMock()
        mock_general.internet_media_type = "video/mp4"
        mock_info.general_tracks = [mock_general]
        mock_mediainfo.parse.return_value = mock_info

        result = MediaInfoService.is_video_file(Path("/test/video.mp4"))

        assert result is True

    def test_is_video_file_false(self, mock_mediainfo):
        """Test non-video file detection."""
        mock_info = MagicMock()
        mock_general = MagicMock()
        mock_general.internet_media_type = "image/jpeg"
        mock_info.general_tracks = [mock_general]
        mock_mediainfo.parse.return_value = mock_info

        result = MediaInfoService.is_video_file(Path("/test/image.jpg"))

        assert result is False

    def test_is_image_file_true(self, mock_mediainfo):
        """Test image file detection."""
        mock_info = MagicMock()
        mock_general = MagicMock()
        mock_general.internet_media_type = "image/jpeg"
        mock_info.general_tracks = [mock_general]
        mock_mediainfo.parse.return_value = mock_info

        result = MediaInfoService.is_image_file(Path("/test/image.jpg"))

        assert result is True

    def test_is_image_file_false(self, mock_mediainfo):
        """Test non-image file detection."""
        mock_info = MagicMock()
        mock_general = MagicMock()
        mock_general.internet_media_type = "video/mp4"
        mock_info.general_tracks = [mock_general]
        mock_mediainfo.parse.return_value = mock_info

        result = MediaInfoService.is_image_file(Path("/test/video.mp4"))

        assert result is False

    def test_is_image_file_excludes_vnd_fpx(self, mock_mediainfo):
        """Test that vnd.fpx files (like Thumbs.db) are excluded."""
        mock_info = MagicMock()
        mock_general = MagicMock()
        mock_general.internet_media_type = "image/vnd.fpx"
        mock_info.general_tracks = [mock_general]
        mock_mediainfo.parse.return_value = mock_info

        result = MediaInfoService.is_image_file(Path("/test/Thumbs.db"))

        assert result is False

    def test_is_live_photo_video_true(self, mock_mediainfo):
        """Test Live Photo video detection."""
        mock_info = MagicMock()
        mock_general = MagicMock()
        mock_general.comapplequicktimecontentidentifier = "ABC123"
        mock_info.general_tracks = [mock_general]
        mock_mediainfo.parse.return_value = mock_info

        result = MediaInfoService.is_live_photo_video(Path("/test/livephoto.mov"))

        assert result is True

    def test_is_live_photo_video_false(self, mock_mediainfo):
        """Test non-Live Photo video detection."""
        mock_info = MagicMock()
        mock_general = MagicMock()
        mock_general.comapplequicktimecontentidentifier = ""
        mock_info.general_tracks = [mock_general]
        mock_mediainfo.parse.return_value = mock_info

        result = MediaInfoService.is_live_photo_video(Path("/test/regular.mov"))

        assert result is False

    def test_is_live_photo_video_no_identifier(self, mock_mediainfo):
        """Test Live Photo detection with None identifier."""
        mock_info = MagicMock()
        mock_general = MagicMock()
        mock_general.comapplequicktimecontentidentifier = None
        mock_info.general_tracks = [mock_general]
        mock_mediainfo.parse.return_value = mock_info

        result = MediaInfoService.is_live_photo_video(Path("/test/regular.mov"))

        assert result is False

    def test_is_live_photo_video_parsing_failed(self, mock_mediainfo):
        """Test Live Photo detection when parsing fails."""
        mock_mediainfo.parse.return_value = "Error parsing"

        result = MediaInfoService.is_live_photo_video(Path("/test/bad.mov"))

        assert result is False

    def test_is_live_photo_video_exception(self, mock_mediainfo):
        """Test Live Photo detection when exception occurs."""
        mock_mediainfo.parse.side_effect = Exception("Test error")

        result = MediaInfoService.is_live_photo_video(Path("/test/error.mov"))

        assert result is False

    def test_validate_video_streams_success(self, mock_mediainfo):
        """Test successful video stream validation."""
        with patch.object(MediaInfoService, "analyze_file") as mock_analyze:
            mock_analyze.return_value = {
                "video": {"stream_count": 1},
                "audio": {"stream_count": 1},
            }

            is_valid, message = MediaInfoService.validate_video_streams(
                Path("/test/video.mp4")
            )

            assert is_valid is True
            assert message == ""

    def test_validate_video_streams_two_streams(self, mock_mediainfo):
        """Test validation with two video streams (depth map)."""
        with patch.object(MediaInfoService, "analyze_file") as mock_analyze:
            mock_analyze.return_value = {
                "video": {"stream_count": 2},
                "audio": {"stream_count": 1},
            }

            is_valid, message = MediaInfoService.validate_video_streams(
                Path("/test/video.mp4")
            )

            assert is_valid is True
            assert message == ""

    def test_validate_video_streams_no_video(self, mock_mediainfo):
        """Test validation failure with no video stream."""
        with patch.object(MediaInfoService, "analyze_file") as mock_analyze:
            mock_analyze.return_value = {
                "video": {"stream_count": 0},
                "audio": {"stream_count": 1},
            }

            is_valid, message = MediaInfoService.validate_video_streams(
                Path("/test/audio.mp4")
            )

            assert is_valid is False
            assert "No video stream" in message

    def test_validate_video_streams_too_many(self, mock_mediainfo):
        """Test validation failure with too many video streams."""
        with patch.object(MediaInfoService, "analyze_file") as mock_analyze:
            mock_analyze.return_value = {
                "video": {"stream_count": 3},
                "audio": {"stream_count": 1},
            }

            is_valid, message = MediaInfoService.validate_video_streams(
                Path("/test/video.mp4")
            )

            assert is_valid is False
            assert "Too many video streams" in message

    def test_validate_video_streams_analysis_failed(self, mock_mediainfo):
        """Test validation when analysis fails."""
        with patch.object(MediaInfoService, "analyze_file") as mock_analyze:
            mock_analyze.return_value = None

            is_valid, message = MediaInfoService.validate_video_streams(
                Path("/test/bad.mp4")
            )

            assert is_valid is False
            assert "Could not analyze" in message

    def test_validate_video_streams_exception(self, mock_mediainfo):
        """Test validation when exception occurs."""
        with patch.object(MediaInfoService, "analyze_file") as mock_analyze:
            mock_analyze.side_effect = Exception("Test error")

            is_valid, message = MediaInfoService.validate_video_streams(
                Path("/test/error.mp4")
            )

            assert is_valid is False
            assert "Test error" in message
