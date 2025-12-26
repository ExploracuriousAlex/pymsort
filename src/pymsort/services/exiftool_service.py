"""
Service for interacting with ExifTool.
Handles metadata extraction, restoration, and file organization.

Uses pyexiftool library for efficient batch-mode communication with ExifTool.
"""

import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from exiftool import ExifToolHelper

logger = logging.getLogger(__name__)


class ExifToolService:
    """Service class for ExifTool operations.

    Uses pyexiftool to run ExifTool in batch mode for efficiency.
    The ExifTool process is started on initialization and should be
    terminated when no longer needed by calling terminate() or using
    the service as a context manager.
    """

    def __init__(self, exiftool_path: str = "exiftool"):
        """
        Initialize ExifTool service and start the ExifTool process.

        Args:
            exiftool_path: Path to exiftool executable (default: "exiftool" assumes it's in PATH or application directory)

        Raises:
            RuntimeError: If ExifTool cannot be started
        """
        self.exiftool_path = exiftool_path

        try:
            self._et = ExifToolHelper(common_args=["-G"], executable=exiftool_path)
            self._et.run()
            logger.info(f"ExifTool found, version: {self._et.version}")
        except FileNotFoundError:
            raise RuntimeError(
                f"ExifTool not found at '{exiftool_path}'. "
                "Please install ExifTool and place it in your system PATH or application directory."
            )
        except Exception as e:
            raise RuntimeError(f"Error starting ExifTool: {e}")

    def terminate(self) -> None:
        """Terminate the ExifTool process."""
        if hasattr(self, "_et") and self._et is not None and self._et.running:
            self._et.terminate()
            logger.debug("ExifTool process terminated")

    def __enter__(self) -> "ExifToolService":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - terminate ExifTool process."""
        self.terminate()

    def __del__(self) -> None:
        """Destructor - ensure ExifTool process is terminated."""
        self.terminate()

    @property
    def version(self) -> str:
        """Get ExifTool version."""
        return self._et.version

    def extract_metadata(self, file_paths: List[Path]) -> List[Dict[str, Any]]:
        """
        Extract metadata from files using ExifTool.

        Args:
            file_paths: List of file paths to extract metadata from

        Returns:
            List of dictionaries containing metadata for each file

        Raises:
            RuntimeError: If ExifTool execution fails
        """
        if not file_paths:
            return []

        logger.info(f"Extracting metadata from {len(file_paths)} files")

        try:
            metadata = self._et.get_metadata(
                file_paths,
                params=["-api", "largefilesupport=1"],
                # params=["-api", "largefilesupport=1", "-charset", "filename=utf8"]
            )
            logger.debug(f"Successfully extracted metadata from {len(metadata)} files")
            return metadata

        except Exception as e:
            logger.error(f"ExifTool error: {e}")
            raise RuntimeError(f"ExifTool failed: {e}")

    def restore_metadata(self, source_file: Path, destination_file: Path) -> bool:
        """
        Copy all metadata from source file to destination file.

        Args:
            source_file: Source file with original metadata
            destination_file: Destination file to copy metadata to

        Returns:
            True if successful, False otherwise
        """
        logger.debug(f"Restoring metadata from {source_file} to {destination_file}")

        try:
            self._et.execute(
                "-api",
                "largefilesupport=1",
                "-charset",
                "filename=utf8",
                "-q",  # Quiet mode
                "-tagsfromfile",
                str(source_file),
                str(destination_file),
            )

            # Clean up _original backup file created by ExifTool
            backup_file = destination_file.parent / f"{destination_file.name}_original"
            backup_file.unlink(missing_ok=True)

            logger.debug(f"Successfully restored metadata to {destination_file}")
            return True

        except Exception as e:
            logger.error(f"Error restoring metadata: {e}")
            return False

    def set_file_dates(self, file_path: Path) -> bool:
        """
        Set file dates based on EXIF metadata with priority order:
        1. CreationDate (QuickTime)
        2. DateTimeOriginal
        3. CreateDate
        4. FileModifyDate

        Args:
            file_path: File to set dates on

        Returns:
            True if successful, False otherwise
        """
        logger.debug(f"Setting file dates for {file_path}")

        try:
            result = self._et.execute(
                "-api",
                "largefilesupport=1",
                # FileModifyDate priority
                "-FileModifyDate<CreateDate",
                "-FileModifyDate<DateTimeOriginal",
                "-FileModifyDate<CreationDate",
                # FileAccessDate priority
                "-FileAccessDate<FileModifyDate",
                "-FileAccessDate<CreateDate",
                "-FileAccessDate<DateTimeOriginal",
                "-FileAccessDate<CreationDate",
                # FileCreateDate priority (Windows)
                "-FileCreateDate<FileModifyDate",
                "-FileCreateDate<CreateDate",
                "-FileCreateDate<DateTimeOriginal",
                "-FileCreateDate<CreationDate",
                str(file_path),
            )

            # ExifTool returns message about files failed condition check, which is acceptable
            if "files failed condition" not in result:
                # Clean up _original backup file
                backup_file = file_path.parent / f"{file_path.name}_original"
                backup_file.unlink(missing_ok=True)

            logger.debug(f"Successfully set file dates for {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error setting file dates: {e}")
            return False

    def organize_files(
        self, files: List[Path], temp_folder: Path, is_live_photo: bool = False
    ) -> Dict[Path, Optional[Path]]:
        """
        Organize files into folder structure based on metadata.

        Args:
            files: List of files to organize
            temp_folder: Base temporary folder for organization
            is_live_photo: Whether these are Live Photo videos

        Returns:
            Dictionary mapping source files to their destination paths (None if failed)
        """
        if not files:
            return {}

        logger.info(f"Organizing {len(files)} files (Live Photo: {is_live_photo})")

        # Create temporary argument file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            arg_file = Path(f.name)
            for file_path in files:
                f.write(f"{file_path}\n")

        try:
            # Build filename template based on file type
            if is_live_photo:
                # Live Photo videos go to LivePhotoVideo subfolder
                filename_template = (
                    f"-filename<{temp_folder}/unknown_camera_model/LivePhotoVideo/${{FileModifyDate}}/%-.37f%+2c.%e "
                    f"-filename<{temp_folder}/${{Model}}/LivePhotoVideo/${{FileModifyDate}}/%-.37f%+2c.%e "
                    f"-filename<{temp_folder}/unknown_camera_model/LivePhotoVideo/${{CreateDate}}/%-.37f%+2c.%e "
                    f"-filename<{temp_folder}/${{Model}}/LivePhotoVideo/${{CreateDate}}/%-.37f%+2c.%e "
                    f"-filename<{temp_folder}/unknown_camera_model/LivePhotoVideo/${{DateTimeOriginal}}/%-.37f%+2c.%e "
                    f"-filename<{temp_folder}/${{Model}}/LivePhotoVideo/${{DateTimeOriginal}}/%-.37f%+2c.%e "
                    f"-filename<{temp_folder}/unknown_camera_model/LivePhotoVideo/${{CreationDate}}/%-.37f%+2c.%e "
                    f"-filename<{temp_folder}/${{Model}}/LivePhotoVideo/${{CreationDate}}/%-.37f%+2c.%e"
                )
            else:
                # Regular files organized by camera model and extension
                filename_template = (
                    f"-filename<{temp_folder}/unknown_camera_model/%e/${{FileModifyDate}}/%-.37f%+2c.%e "
                    f"-filename<{temp_folder}/${{Is-montage}}/%e/${{FileModifyDate}}/%-.37f%+2c.%e "
                    f"-filename<{temp_folder}/${{Model}}/%e/${{FileModifyDate}}/%-.37f%+2c.%e "
                    f"-filename<{temp_folder}/unknown_camera_model/%e/${{CreateDate}}/%-.37f%+2c.%e "
                    f"-filename<{temp_folder}/${{Is-montage}}/%e/${{CreateDate}}/%-.37f%+2c.%e "
                    f"-filename<{temp_folder}/${{Model}}/%e/${{CreateDate}}/%-.37f%+2c.%e "
                    f"-filename<{temp_folder}/unknown_camera_model/%e/${{DateTimeOriginal}}/%-.37f%+2c.%e "
                    f"-filename<{temp_folder}/${{Is-montage}}/%e/${{DateTimeOriginal}}/%-.37f%+2c.%e "
                    f"-filename<{temp_folder}/${{Model}}/%e/${{DateTimeOriginal}}/%-.37f%+2c.%e "
                    f"-filename<{temp_folder}/unknown_camera_model/%e/${{CreationDate}}/%-.37f%+2c.%e "
                    f"-filename<{temp_folder}/${{Is-montage}}/%e/${{CreationDate}}/%-.37f%+2c.%e "
                    f"-filename<{temp_folder}/${{Model}}/%e/${{CreationDate}}/%-.37f%+2c.%e"
                )

            # Build command arguments
            args = (
                [
                    "-api",
                    "largefilesupport=1",
                    "-charset",
                    "filename=utf8",
                    "-L",
                    "-@",
                    str(arg_file),
                    "-d",
                    "%Y/%m-%B",  # Date format for folders: Year/Month-MonthName/
                ]
                + filename_template.split()
                + ["-v"]
            )  # Verbose for tracking moves

            # Execute command
            result = self._et.execute(*args)

            # Parse output to track source -> destination mapping
            file_mapping = {}
            for line in result.split("\n"):
                if " --> " in line:
                    parts = line.split(" --> ")
                    if len(parts) == 2:
                        source = Path(parts[0].strip().strip("'"))
                        destination = Path(parts[1].strip().strip("'"))

                        # Verify destination exists
                        if destination.exists():
                            file_mapping[source] = destination
                        else:
                            logger.error(f"Destination file not found: {destination}")
                            file_mapping[source] = None

            logger.info(f"Successfully organized {len(file_mapping)} files")
            return file_mapping

        except Exception as e:
            logger.error(f"Error organizing files: {e}")
            return {f: None for f in files}
        finally:
            arg_file.unlink(missing_ok=True)

    def get_capture_mode(self, file_path: Path) -> Optional[str]:
        """
        Get capture mode from video file.

        Args:
            file_path: Video file to check

        Returns:
            Capture mode string or None if not found
        """
        try:
            data = self._et.get_tags(
                file_path,
                tags=["CaptureMode", "ApplePhotosCaptureMode"],
                params=["-api", "largefilesupport=1"],
                # params=["-api", "largefilesupport=1", "-charset", "filename=utf8"]
            )

            if data:
                # Check for both possible tag names
                return data[0].get("CaptureMode") or data[0].get(
                    "ApplePhotosCaptureMode"
                )

            return None

        except Exception as e:
            logger.error(f"Error getting capture mode: {e}")
            return None
