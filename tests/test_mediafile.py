"""
Tests for MediaFile dataclass and ProcessingState enum.
"""

from pymsort.models.mediafile import MediaFile, ProcessingState


class TestProcessingState:
    """Test cases for ProcessingState enum."""

    def test_processing_state_values(self):
        """Test that all expected ProcessingState members exist."""
        expected_members = {
            "NoState",
            "Pending",
            "InProgress",
            "Success",
            "Warning",
            "Error",
        }
        actual_members = {member.name for member in ProcessingState}
        assert actual_members == expected_members

    def test_processing_state_str(self):
        """Test string representation returns the member name."""
        for state in ProcessingState:
            assert str(state) == state.name


class TestMediaFile:
    """Test cases for MediaFile dataclass."""

    def test_mediafile_creation_with_defaults(self):
        """Test creating a MediaFile with only required field uses correct defaults."""
        mf = MediaFile(source_file="/path/to/file.jpg")

        # Required field
        assert mf.source_file == "/path/to/file.jpg"

        # Default state
        assert mf.state == ProcessingState.NoState

        # All optional fields should be None
        assert mf.audio_format is None
        assert mf.audio_stream_count is None
        assert mf.container_format is None
        assert mf.create_date is None
        assert mf.creation_date is None
        assert mf.date_time_original is None
        assert mf.destination_file is None
        assert mf.file_modify_date is None
        assert mf.file_name is None
        assert mf.intermediate_file is None
        assert mf.mime_type is None
        assert mf.video_format is None
        assert mf.video_scan_type is None
        assert mf.video_stream_count is None
        assert mf.is_live_photo_video is None

    def test_mediafile_creation_with_all_fields(self):
        """Test creating a MediaFile with all fields set explicitly."""
        mf = MediaFile(
            source_file="/path/to/file.mov",
            audio_format="AAC",
            audio_stream_count=1,
            container_format="QuickTime",
            create_date="2024:01:01 12:00:00",
            creation_date="2024-01-01T12:00:00+01:00",
            date_time_original="2024:01:01 12:00:00",
            destination_file="/destination/file.mov",
            file_modify_date="2024:01:01 12:00:00",
            file_name="file.mov",
            intermediate_file="/temp/file.mov",
            mime_type="video/quicktime",
            state=ProcessingState.Pending,
            video_format="HEVC",
            video_scan_type="Progressive",
            video_stream_count=1,
            is_live_photo_video=True,
        )

        assert mf.source_file == "/path/to/file.mov"
        assert mf.audio_format == "AAC"
        assert mf.audio_stream_count == 1
        assert mf.container_format == "QuickTime"
        assert mf.create_date == "2024:01:01 12:00:00"
        assert mf.creation_date == "2024-01-01T12:00:00+01:00"
        assert mf.date_time_original == "2024:01:01 12:00:00"
        assert mf.destination_file == "/destination/file.mov"
        assert mf.file_modify_date == "2024:01:01 12:00:00"
        assert mf.file_name == "file.mov"
        assert mf.intermediate_file == "/temp/file.mov"
        assert mf.mime_type == "video/quicktime"
        assert mf.state == ProcessingState.Pending
        assert mf.video_format == "HEVC"
        assert mf.video_scan_type == "Progressive"
        assert mf.video_stream_count == 1
        assert mf.is_live_photo_video is True

    def test_mediafile_state_is_mutable(self):
        """Test that state can be changed (important for workflow)."""
        mf = MediaFile(source_file="/path/to/file.jpg")
        assert mf.state == ProcessingState.NoState

        mf.state = ProcessingState.Pending
        assert mf.state == ProcessingState.Pending

        mf.state = ProcessingState.InProgress
        assert mf.state == ProcessingState.InProgress

        mf.state = ProcessingState.Success
        assert mf.state == ProcessingState.Success

    def test_populate_from_mediainfo_with_valid_data(self):
        """Test populate_from_mediainfo with complete mediainfo data."""
        mf = MediaFile(source_file="/path/to/video.mov")

        mediainfo_data = {
            "general": {
                "format": "QuickTime",
                "is_live_photo": True,
            },
            "video": {
                "stream_count": 1,
                "format": "HEVC",
                "scan_type": "Progressive",
            },
            "audio": {
                "stream_count": 2,
                "format": "AAC",
            },
        }

        mf.populate_from_mediainfo(mediainfo_data)

        assert mf.container_format == "QuickTime"
        assert mf.video_stream_count == 1
        assert mf.video_format == "HEVC"
        assert mf.video_scan_type == "Progressive"
        assert mf.audio_stream_count == 2
        assert mf.audio_format == "AAC"
        assert mf.is_live_photo_video is True

    def test_populate_from_mediainfo_with_partial_data(self):
        """Test populate_from_mediainfo handles missing keys gracefully."""
        mf = MediaFile(source_file="/path/to/video.mov")

        # Minimal data - missing audio and some video fields
        mediainfo_data = {
            "general": {"format": "MPEG-4"},
            "video": {"format": "AVC"},
            "audio": {},
        }

        mf.populate_from_mediainfo(mediainfo_data)

        assert mf.container_format == "MPEG-4"
        assert mf.video_format == "AVC"
        assert mf.video_scan_type is None
        assert mf.video_stream_count == 0  # Default when missing
        assert mf.audio_stream_count == 0  # Default when missing
        assert mf.audio_format is None
        assert mf.is_live_photo_video is False  # Default when missing

    def test_populate_from_mediainfo_with_none(self):
        """Test populate_from_mediainfo sets defaults when info is None."""
        mf = MediaFile(source_file="/path/to/video.mov")

        mf.populate_from_mediainfo(None)

        assert mf.container_format == "Unknown"
        assert mf.video_format == "Unknown"
        assert mf.video_scan_type == "Unknown"
        assert mf.audio_format == "Unknown"

    def test_populate_from_mediainfo_with_empty_dict(self):
        """Test populate_from_mediainfo treats empty dict same as None."""
        mf = MediaFile(source_file="/path/to/video.mov")

        mf.populate_from_mediainfo({})

        # Empty dict is falsy, so same behavior as None
        assert mf.container_format == "Unknown"
        assert mf.video_format == "Unknown"
        assert mf.video_scan_type == "Unknown"
        assert mf.audio_format == "Unknown"
