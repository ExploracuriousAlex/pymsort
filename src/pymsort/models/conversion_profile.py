import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from dataclasses_json import dataclass_json

logger = logging.getLogger(__name__)


@dataclass_json
@dataclass
class ConversionProfile:
    UseCase: str
    Description: str
    OriginalFileExtension: str
    VideoFormat: str
    VideoScanType: str
    AudioFormat: str
    IsLivePhotoVideo: bool
    FfmpegExecutionString: str
    NewFileExtension: str

    @property
    def unique_key(self) -> Tuple[str, str, str, str, bool]:
        """Return the unique key tuple for profile matching."""
        return (
            self.OriginalFileExtension,
            self.VideoFormat,
            self.VideoScanType,
            self.AudioFormat,
            self.IsLivePhotoVideo,
        )


def load_conversion_profiles() -> List[ConversionProfile]:
    """Load conversion profiles from ConversionProfiles.json.

    Returns:
        List of ConversionProfile objects.

    Raises:
        ValueError: If duplicate profile keys are found.
        FileNotFoundError: If the profiles file doesn't exist.
    """
    profile_path = Path(__file__).parent.parent / "ConversionProfiles.json"

    logger.info(f"Loading conversion profiles from {profile_path}")

    with open(profile_path, encoding="utf-8") as f:
        profiles_json = json.load(f)

    conversion_profiles: List[ConversionProfile] = []
    seen_keys: set = set()

    for profile_data in profiles_json:
        profile = ConversionProfile.schema().load(profile_data)

        if profile.unique_key in seen_keys:
            error_msg = (
                f"Duplicate conversion profile found: "
                f"OriginalFileExtension='{profile.OriginalFileExtension}', "
                f"VideoFormat='{profile.VideoFormat}', "
                f"VideoScanType='{profile.VideoScanType}', "
                f"AudioFormat='{profile.AudioFormat}', "
                f"IsLivePhotoVideo='{profile.IsLivePhotoVideo}'"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        seen_keys.add(profile.unique_key)
        conversion_profiles.append(profile)

    logger.info("Loaded %d conversion profiles", len(conversion_profiles))
    return conversion_profiles
