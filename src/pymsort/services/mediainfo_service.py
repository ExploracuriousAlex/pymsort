"""
Service for interacting with MediaInfo.
Handles media file analysis.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from pymediainfo import MediaInfo

logger = logging.getLogger(__name__)


class MediaInfoService:
    """Service class for MediaInfo operations."""

    @staticmethod
    def analyze_file(file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Analyze a media file using MediaInfo.

        Args:
            file_path: Path to media file

        Returns:
            Dictionary with media file information or None if analysis failed
        """
        try:
            media_info = MediaInfo.parse(str(file_path))

            # Check if parsing failed
            if isinstance(media_info, str):
                logger.error(f"MediaInfo parsing failed for {file_path}: {media_info}")
                return None

            # Extract information
            result = {
                "file_path": str(file_path),
                "general": {},
                "video": {},
                "audio": {},
            }

            # General track information
            if media_info.general_tracks:
                general = media_info.general_tracks[0]
                result["general"] = {
                    "format": general.format or "Unknown",
                    "mime_type": general.internet_media_type or "Unknown",
                    "file_size": general.file_size,
                    "duration": general.duration,
                }

                # Check for Live Photo identifier
                live_photo_id = general.comapplequicktimecontentidentifier
                result["general"]["is_live_photo"] = bool(
                    live_photo_id and live_photo_id != ""
                )

            # Video track information
            result["video"]["stream_count"] = len(media_info.video_tracks)
            if media_info.video_tracks:
                video = media_info.video_tracks[0]
                result["video"]["format"] = video.format or "Unknown"
                result["video"]["scan_type"] = video.scan_type or ""
                result["video"]["width"] = video.width
                result["video"]["height"] = video.height
                result["video"]["frame_rate"] = video.frame_rate
                result["video"]["codec"] = video.codec_id or video.format

            # Audio track information
            result["audio"]["stream_count"] = len(media_info.audio_tracks)
            if media_info.audio_tracks:
                audio = media_info.audio_tracks[0]
                result["audio"]["format"] = audio.format or "Unknown"
                result["audio"]["channels"] = audio.channel_s
                result["audio"]["sampling_rate"] = audio.sampling_rate
                result["audio"]["codec"] = audio.codec_id or audio.format

            return result

        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return None

    @staticmethod
    def get_mime_type(file_path: Path) -> str:
        """
        Get MIME type of a file.

        Args:
            file_path: Path to file

        Returns:
            MIME type string or 'unknown' if cannot be determined
        """
        try:
            media_info = MediaInfo.parse(str(file_path))

            if isinstance(media_info, str):
                return "unknown"

            if media_info.general_tracks:
                mime = media_info.general_tracks[0].internet_media_type
                return mime if mime else "unknown"

            return "unknown"

        except Exception as e:
            logger.error(f"Error getting MIME type for {file_path}: {e}")
            return "unknown"

    @staticmethod
    def is_video_file(file_path: Path) -> bool:
        """
        Check if file is a video file.

        Args:
            file_path: Path to file

        Returns:
            True if file is a video, False otherwise
        """
        mime_type = MediaInfoService.get_mime_type(file_path)
        return mime_type.lower().startswith("video")

    @staticmethod
    def is_image_file(file_path: Path) -> bool:
        """
        Check if file is an image file.

        Args:
            file_path: Path to file

        Returns:
            True if file is an image, False otherwise
        """
        mime_type = MediaInfoService.get_mime_type(file_path)
        # Exclude vnd.fpx (used for Thumbs.db)
        return (
            mime_type.lower().startswith("image") and "vnd.fpx" not in mime_type.lower()
        )

    @staticmethod
    def is_live_photo_video(file_path: Path) -> bool:
        """
        Check if video file is an Apple Live Photo video.

        Args:
            file_path: Path to video file

        Returns:
            True if it's a Live Photo video, False otherwise
        """
        try:
            media_info = MediaInfo.parse(str(file_path))

            if isinstance(media_info, str):
                return False

            if media_info.general_tracks:
                general = media_info.general_tracks[0]
                live_photo_id = general.comapplequicktimecontentidentifier
                return bool(live_photo_id and live_photo_id != "")

            return False

        except Exception as e:
            logger.error(f"Error checking Live Photo status for {file_path}: {e}")
            return False

    @staticmethod
    def validate_video_streams(file_path: Path) -> tuple[bool, str]:
        """
        Validate video stream configuration.

        Args:
            file_path: Path to video file

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        try:
            info = MediaInfoService.analyze_file(file_path)
            if not info:
                return False, "Could not analyze video file"

            video_count = info["video"]["stream_count"]
            # Note: audio_count could be used for future validation
            # audio_count = info['audio']['stream_count']

            # Check video streams
            if video_count == 0:
                return False, "No video stream found"
            elif video_count > 2:
                return False, f"Too many video streams ({video_count})"

            # Video count of 1 or 2 is acceptable
            # (2 streams can be depth map or similar)

            return True, ""

        except Exception as e:
            logger.error(f"Error validating video streams: {e}")
            return False, str(e)
