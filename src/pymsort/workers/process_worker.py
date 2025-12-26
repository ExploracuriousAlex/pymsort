"""
Worker for processing media files.
Handles video conversion and file organization in background.
"""

import logging
import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from ..models import ConversionProfile, MediaFile, ProcessingState

logger = logging.getLogger(__name__)


class ProcessWorkerSignals(QObject):
    """Signals for ProcessWorker."""

    finished = Signal()
    error = Signal(tuple)
    progress = Signal(int, int, str)  # current, total, message
    file_state_changed = Signal(int, ProcessingState)  # row_index, new_state
    log_message = Signal(str, str)  # level, message


class ProcessWorker(QRunnable):
    """
    Worker for processing media files (conversion and organization).
    """

    def __init__(
        self,
        files: List[MediaFile],
        profiles: List[ConversionProfile],
        temp_folder: Path,
        exiftool_service,
        ffmpeg_service,
        mediainfo_service,
    ):
        """
        Initialize ProcessWorker.

        Args:
            files: List of MediaFile objects to process
            profiles: List of available ConversionProfile objects
            temp_folder: Temporary folder for intermediate files
            exiftool_service: ExifToolService instance
            ffmpeg_service: FFmpegService instance
            mediainfo_service: MediaInfoService instance
        """
        super().__init__()
        self.files = files
        self.profiles = profiles
        self.temp_folder = Path(temp_folder)
        self.exiftool_service = exiftool_service
        self.ffmpeg_service = ffmpeg_service
        self.mediainfo_service = mediainfo_service
        self.signals = ProcessWorkerSignals()

    @Slot()
    def run(self):
        """Execute the processing workflow."""
        try:
            self._log_info("Starting file processing...")

            # Ensure temp folder exists
            self.temp_folder.mkdir(parents=True, exist_ok=True)

            # Process video files
            self._process_video_files()

            # Process image files
            self._process_image_files()

            # Organize non-Live Photo files
            self._organize_regular_files()

            # Organize Live Photo videos
            self._organize_live_photo_videos()

            # Generate summary
            self._log_summary()

            self.signals.finished.emit()

        except Exception as e:
            logger.exception("Error in ProcessWorker")
            self.signals.error.emit((type(e), e, str(e)))

    def _process_video_files(self):
        """Process all pending video files."""
        video_files = [
            (i, f)
            for i, f in enumerate(self.files)
            if f.state == ProcessingState.Pending
            and f.mime_type
            and "video" in f.mime_type.lower()
        ]

        if not video_files:
            return

        self._log_info(f"Processing {len(video_files)} video files")

        for idx, (file_idx, video_file) in enumerate(video_files, 1):
            self.signals.progress.emit(
                idx,
                len(video_files),
                f"({idx} of {len(video_files)}) - Processing video {video_file.file_name}",
            )

            self._update_file_state(file_idx, ProcessingState.InProgress)

            # Validate video streams
            is_valid, error_msg = self.mediainfo_service.validate_video_streams(
                Path(video_file.source_file)
            )

            if not is_valid:
                self._log_error(
                    f"Invalid video file {video_file.source_file}: {error_msg}"
                )
                self._update_file_state(file_idx, ProcessingState.Error)
                continue

            # Validate audio for videos without it
            if video_file.audio_stream_count == 0:
                if not self._validate_audio_absence(video_file):
                    self._update_file_state(file_idx, ProcessingState.Error)
                    continue

            # Find matching conversion profile
            profile = self._find_matching_profile(video_file)
            if not profile:
                self._log_error(
                    f"No matching conversion profile for {video_file.source_file}"
                )
                self._update_file_state(file_idx, ProcessingState.Error)
                continue

            self._log_info(f"Using profile: {profile.Description}")

            # Determine extension: preserve original case if extensions match (case-insensitive)
            source_ext = Path(video_file.source_file).suffix
            if source_ext.lower() == profile.NewFileExtension.lower():
                target_ext = source_ext
            else:
                target_ext = profile.NewFileExtension

            # Create intermediate file
            intermediate_path = self._create_intermediate_path(video_file, target_ext)
            video_file.intermediate_file = str(intermediate_path)

            # Convert or copy video
            if profile.FfmpegExecutionString:
                # Conversion required
                success, error_msg = self.ffmpeg_service.convert_video(
                    Path(video_file.source_file),
                    intermediate_path,
                    profile.FfmpegExecutionString,
                )

                if not success:
                    self._log_error(f"Video conversion failed: {error_msg}")
                    self._update_file_state(file_idx, ProcessingState.Error)
                    continue

                # Restore metadata
                if not self.exiftool_service.restore_metadata(
                    Path(video_file.source_file), intermediate_path
                ):
                    self._log_warning("Failed to restore metadata (continuing anyway)")

                # Set proper dates
                self.exiftool_service.set_file_dates(intermediate_path)
            else:
                # Just copy
                try:
                    intermediate_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(Path(video_file.source_file), intermediate_path)
                except Exception as e:
                    error_msg = f"File copy failed: {e}"
                    self._log_error(error_msg)
                    self._update_file_state(file_idx, ProcessingState.Error)
                    continue

            self._log_info(f"Created intermediate file: {intermediate_path}")

    def _process_image_files(self):
        """Process all pending image files."""
        image_files = [
            (i, f)
            for i, f in enumerate(self.files)
            if f.state == ProcessingState.Pending
            and f.mime_type
            and "image" in f.mime_type.lower()
        ]

        if not image_files:
            return

        self._log_info(f"Processing {len(image_files)} image files")

        for idx, (file_idx, image_file) in enumerate(image_files, 1):
            self.signals.progress.emit(
                idx,
                len(image_files),
                f"({idx} of {len(image_files)}) - Copying image {image_file.file_name}",
            )

            self._update_file_state(file_idx, ProcessingState.InProgress)

            # Get file extension from source
            ext = Path(image_file.source_file).suffix

            # Create intermediate file
            intermediate_path = self._create_intermediate_path(image_file, ext)
            image_file.intermediate_file = str(intermediate_path)

            # Copy image
            try:
                intermediate_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(Path(image_file.source_file), intermediate_path)
            except Exception as e:
                error_msg = f"Image copy failed: {e}"
                self._log_error(error_msg)
                self._update_file_state(file_idx, ProcessingState.Error)
                continue

    def _organize_regular_files(self):
        """Organize non-Live Photo files into folder structure."""
        files_to_organize = [
            (i, f)
            for i, f in enumerate(self.files)
            if f.state == ProcessingState.InProgress
            and not f.is_live_photo_video
            and f.intermediate_file
        ]

        if not files_to_organize:
            return

        self._log_info(f"Organizing {len(files_to_organize)} regular files")
        self.signals.progress.emit(
            1, 2, "Organizing regular media files into folder structure"
        )

        # Organize files
        file_paths = [Path(f.intermediate_file) for _, f in files_to_organize]
        file_mapping = self.exiftool_service.organize_files(
            file_paths, self.temp_folder, is_live_photo=False
        )

        # Update file states based on results
        for file_idx, media_file in files_to_organize:
            intermediate = Path(media_file.intermediate_file)
            destination = file_mapping.get(intermediate)

            if destination:
                media_file.destination_file = str(destination)
                self._update_file_state(file_idx, ProcessingState.Success)
            else:
                self._log_error(f"Failed to organize file: {intermediate}")
                self._update_file_state(file_idx, ProcessingState.Error)

    def _organize_live_photo_videos(self):
        """Organize Live Photo videos into folder structure."""
        files_to_organize = [
            (i, f)
            for i, f in enumerate(self.files)
            if f.state == ProcessingState.InProgress
            and f.is_live_photo_video
            and f.intermediate_file
        ]

        if not files_to_organize:
            return

        self._log_info(f"Organizing {len(files_to_organize)} Live Photo videos")
        self.signals.progress.emit(
            1, 2, "Organizing Live Photo videos into folder structure"
        )

        # Organize files
        file_paths = [Path(f.intermediate_file) for _, f in files_to_organize]
        file_mapping = self.exiftool_service.organize_files(
            file_paths, self.temp_folder, is_live_photo=True
        )

        # Update file states based on results
        for file_idx, media_file in files_to_organize:
            intermediate = Path(media_file.intermediate_file)
            destination = file_mapping.get(intermediate)

            if destination:
                media_file.destination_file = str(destination)
                self._update_file_state(file_idx, ProcessingState.Success)
            else:
                self._log_error(f"Failed to organize Live Photo video: {intermediate}")
                self._update_file_state(file_idx, ProcessingState.Error)

    def _validate_audio_absence(self, video_file: MediaFile) -> bool:
        """Validate that absence of audio is acceptable for this video."""
        # Check if it's a Live Photo (audio not expected)
        if video_file.is_live_photo_video:
            self._log_warning(
                f"No audio stream in Live Photo video (acceptable): {video_file.source_file}"
            )
            return True

        # Check filename for time-lapse indicators
        filename_lower = video_file.file_name.lower() if video_file.file_name else ""
        timelapse_keywords = ["timelapse", "hyperlaps"]

        for keyword in timelapse_keywords:
            if keyword in filename_lower:
                self._log_warning(
                    f"No audio stream but filename contains '{keyword}' (acceptable)"
                )
                return True

        # Check EXIF capture mode
        capture_mode = self.exiftool_service.get_capture_mode(
            Path(video_file.source_file)
        )
        if capture_mode:
            acceptable_modes = ["Time-lapse"]
            if capture_mode in acceptable_modes:
                self._log_warning(
                    f"No audio stream but capture mode is '{capture_mode}' (acceptable)"
                )
                return True
            else:
                self._log_error(
                    f"No audio stream and capture mode '{capture_mode}' requires audio"
                )
                return False

        self._log_error("No audio stream found and no acceptable reason")
        return False

    def _find_matching_profile(
        self, video_file: MediaFile
    ) -> Optional[ConversionProfile]:
        """Find matching conversion profile for video file."""
        source_ext = Path(video_file.source_file).suffix

        # Create search key matching the ConversionProfile.unique_key format
        search_key = (
            source_ext.lower(),
            video_file.video_format or "",
            video_file.video_scan_type or "",
            video_file.audio_format or "",
            video_file.is_live_photo_video or False,
        )

        matching_profiles = [
            p
            for p in self.profiles
            if (
                p.OriginalFileExtension.lower(),
                p.VideoFormat,
                p.VideoScanType,
                p.AudioFormat,
                p.IsLivePhotoVideo,
            )
            == search_key
        ]

        if len(matching_profiles) == 1:
            return matching_profiles[0]
        elif len(matching_profiles) > 1:
            self._log_error(
                f"Found {len(matching_profiles)} matching profiles (ambiguous)"
            )
            return None
        else:
            return None

    def _create_intermediate_path(self, media_file: MediaFile, extension: str) -> Path:
        """Create intermediate file path with UUID."""
        if not extension.startswith("."):
            extension = f".{extension}"

        filename_base = Path(media_file.source_file).stem

        # Add UUID to filename
        unique_name = f"{filename_base}-{uuid.uuid4()}{extension}"

        return self.temp_folder / unique_name

    def _update_file_state(self, file_index: int, state: ProcessingState):
        """Update file state and emit signal."""
        self.files[file_index].state = state
        self.signals.file_state_changed.emit(file_index, state)

    def _log_info(self, message: str):
        """Log info message."""
        logger.info(message)
        self.signals.log_message.emit("INFO", message)

    def _log_warning(self, message: str):
        """Log warning message."""
        logger.warning(message)
        self.signals.log_message.emit("WARNING", message)

    def _log_error(self, message: str):
        """Log error message."""
        logger.error(message)
        self.signals.log_message.emit("ERROR", message)

    def _log_summary(self):
        """Log processing summary."""
        # Count files by type and state
        video_count = sum(
            1
            for f in self.files
            if f.mime_type
            and "video" in f.mime_type.lower()
            and not f.is_live_photo_video
        )
        image_count = sum(
            1 for f in self.files if f.mime_type and "image" in f.mime_type.lower()
        )
        live_photo_count = sum(1 for f in self.files if f.is_live_photo_video)

        success_count = sum(1 for f in self.files if f.state == ProcessingState.Success)
        error_count = sum(1 for f in self.files if f.state == ProcessingState.Error)

        self._log_info("=" * 50)
        self._log_info("Processing Summary:")
        self._log_info(f"  Videos processed: {video_count}")
        self._log_info(f"  Images processed: {image_count}")
        self._log_info(f"  Live Photo videos: {live_photo_count}")
        self._log_info(f"  Successfully completed: {success_count}")
        if error_count > 0:
            self._log_error(f"  Files with errors: {error_count}")
        self._log_info("=" * 50)
