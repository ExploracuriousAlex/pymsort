from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, Optional


class ProcessingState(Enum):
    NoState = auto()
    Pending = auto()
    InProgress = auto()
    Success = auto()
    Warning = auto()
    Error = auto()

    def __str__(self):
        return self.name


@dataclass
class MediaFile:
    source_file: str
    audio_format: Optional[str] = None
    audio_stream_count: Optional[int] = None
    container_format: Optional[str] = None
    create_date: Optional[str] = None
    creation_date: Optional[str] = None
    date_time_original: Optional[str] = None
    destination_file: Optional[str] = None
    file_modify_date: Optional[str] = None
    file_name: Optional[str] = None
    intermediate_file: Optional[str] = None
    mime_type: Optional[str] = None
    state: ProcessingState = ProcessingState.NoState
    video_format: Optional[str] = None
    video_scan_type: Optional[str] = None
    video_stream_count: Optional[int] = None
    is_live_photo_video: Optional[bool] = None

    def populate_from_mediainfo(self, info: Optional[Dict[str, Any]]) -> None:
        """
        Populate video-related fields from MediaInfo analysis result.

        Args:
            info: Dictionary from MediaInfoService.analyze_file() or None
        """
        if info:
            self.container_format = info.get("general", {}).get("format")
            self.video_stream_count = info.get("video", {}).get("stream_count", 0)
            self.audio_stream_count = info.get("audio", {}).get("stream_count", 0)
            self.video_format = info.get("video", {}).get("format")
            self.video_scan_type = info.get("video", {}).get("scan_type")
            self.audio_format = info.get("audio", {}).get("format")
            self.is_live_photo_video = info.get("general", {}).get(
                "is_live_photo", False
            )
        else:
            self.container_format = "Unknown"
            self.video_format = "Unknown"
            self.video_scan_type = "Unknown"
            self.audio_format = "Unknown"
