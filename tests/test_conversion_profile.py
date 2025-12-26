"""
Tests for ConversionProfile dataclass and profile loading.
"""

import json

from pymsort.models.conversion_profile import (
    ConversionProfile,
    load_conversion_profiles,
)


class TestConversionProfile:
    """Test cases for ConversionProfile dataclass."""

    def test_conversion_profile_creation(self):
        """Test creating a ConversionProfile with all fields."""
        profile = ConversionProfile(
            UseCase="Sony DSC-RX100",
            Description="Test profile",
            OriginalFileExtension=".mts",
            VideoFormat="AVC",
            VideoScanType="Progressive",
            AudioFormat="AC-3",
            IsLivePhotoVideo=False,
            FfmpegExecutionString="ffmpeg -i %s %s",
            NewFileExtension=".mp4",
        )

        assert profile.UseCase == "Sony DSC-RX100"
        assert profile.Description == "Test profile"
        assert profile.OriginalFileExtension == ".mts"
        assert profile.VideoFormat == "AVC"
        assert profile.VideoScanType == "Progressive"
        assert profile.AudioFormat == "AC-3"
        assert profile.IsLivePhotoVideo is False
        assert profile.FfmpegExecutionString == "ffmpeg -i %s %s"
        assert profile.NewFileExtension == ".mp4"

    def test_conversion_profile_is_dataclass(self):
        """Test that ConversionProfile is a dataclass."""
        assert hasattr(ConversionProfile, "__dataclass_fields__")
        # Check that all required fields exist
        required_fields = [
            "UseCase",
            "Description",
            "OriginalFileExtension",
            "VideoFormat",
            "VideoScanType",
            "AudioFormat",
            "IsLivePhotoVideo",
            "FfmpegExecutionString",
            "NewFileExtension",
        ]
        for field in required_fields:
            assert field in ConversionProfile.__dataclass_fields__


class TestLoadConversionProfilesIsolated:
    """Test cases for loading conversion profiles with isolated temp files."""

    def test_load_valid_profiles(self, tmp_path, monkeypatch):
        """Test loading valid conversion profiles with mocked path."""
        import pymsort.models.conversion_profile as cp_module

        # Create a temporary JSON file with valid profiles
        profiles_data = [
            {
                "UseCase": "Test Case 1",
                "Description": "Test profile 1",
                "OriginalFileExtension": ".mts",
                "VideoFormat": "AVC",
                "VideoScanType": "Progressive",
                "AudioFormat": "AC-3",
                "IsLivePhotoVideo": False,
                "FfmpegExecutionString": "ffmpeg -i %s %s",
                "NewFileExtension": ".mp4",
            },
            {
                "UseCase": "Test Case 2",
                "Description": "Test profile 2",
                "OriginalFileExtension": ".mov",
                "VideoFormat": "HEVC",
                "VideoScanType": "",
                "AudioFormat": "AAC",
                "IsLivePhotoVideo": True,
                "FfmpegExecutionString": "",
                "NewFileExtension": ".mov",
            },
        ]

        # Create pymsort subdirectory structure to match the path resolution
        pymsort_dir = tmp_path / "pymsort"
        pymsort_dir.mkdir()
        profiles_file = tmp_path / "ConversionProfiles.json"
        with open(profiles_file, "w") as f:
            json.dump(profiles_data, f)

        # Mock the __file__ path to point to our temp directory
        original_file = cp_module.__file__
        monkeypatch.setattr(
            cp_module, "__file__", str(pymsort_dir / "conversion_profile.py")
        )

        try:
            # Load profiles
            profiles = load_conversion_profiles()

            # Verify
            assert len(profiles) == 2
            assert profiles[0].UseCase == "Test Case 1"
            assert profiles[0].VideoFormat == "AVC"
            assert profiles[1].UseCase == "Test Case 2"
            assert profiles[1].VideoFormat == "HEVC"
            assert profiles[1].IsLivePhotoVideo is True
        finally:
            # Restore original
            monkeypatch.setattr(cp_module, "__file__", original_file)


class TestLoadConversionProfiles:
    """Test cases for loading conversion profiles from JSON."""

    def test_load_valid_profiles(self):
        """Test loading actual conversion profiles."""
        profiles = load_conversion_profiles()

        # Verify we got profiles
        assert len(profiles) == 17  # Known number from actual file

        # Verify structure
        assert all(hasattr(p, "UseCase") for p in profiles)
        assert all(hasattr(p, "VideoFormat") for p in profiles)

    def test_load_profiles_unique_combinations(self):
        """Test that all profile combinations are unique."""
        profiles = load_conversion_profiles()

        # Check all combinations are unique
        combinations = set()
        for profile in profiles:
            combo = (
                profile.OriginalFileExtension,
                profile.VideoFormat,
                profile.VideoScanType,
                profile.AudioFormat,
                profile.IsLivePhotoVideo,
            )
            assert combo not in combinations, f"Duplicate profile combination: {combo}"
            combinations.add(combo)

    def test_load_profiles_different_combinations_succeed(self):
        """Test that different combinations are allowed."""
        profiles = load_conversion_profiles()
        assert len(profiles) > 1

        # Verify different combinations exist
        combinations = [(p.OriginalFileExtension, p.VideoFormat) for p in profiles]
        assert len(set(combinations)) > 1

    def test_load_profiles_empty_audio_format(self):
        """Test profiles with empty audio format."""
        profiles = load_conversion_profiles()

        # Find profiles with no audio
        no_audio = [p for p in profiles if p.AudioFormat == ""]
        assert len(no_audio) > 0

        # Verify all filtered profiles have empty AudioFormat
        for profile in no_audio:
            assert profile.AudioFormat == ""

    def test_profile_with_live_photo_flag(self):
        """Test Live Photo profiles."""
        profiles = load_conversion_profiles()

        live_photos = [p for p in profiles if p.IsLivePhotoVideo]
        assert len(live_photos) > 0
        assert all(p.NewFileExtension == ".mov" for p in live_photos)
