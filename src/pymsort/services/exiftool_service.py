"""
Service for interacting with ExifTool.
Handles metadata extraction, restoration, and file organization.

"""

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ExifToolService:
    """Service class for ExifTool operations."""

    def __init__(self, exiftool_path: str = "exiftool"):
        """
        Initialize ExifTool service.

        Args:
            exiftool_path: Path to exiftool executable (default: "exiftool" assumes it's in PATH or application directory)

        """
        self.exiftool_path = exiftool_path
        self._verify_exiftool()

    def _verify_exiftool(self) -> None:
        """Verify that ExifTool is available and working."""
        try:
            result = subprocess.run(
                [self.exiftool_path, "-ver"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                logger.info(f"ExifTool found, version: {version}")
            else:
                raise RuntimeError(f"ExifTool verification failed: {result.stderr}")
        except FileNotFoundError:
            raise RuntimeError(
                f"ExifTool not found at '{self.exiftool_path}'. "
                "Please install ExifTool and ensure it's in your PATH."
            )
        except Exception as e:
            raise RuntimeError(f"Error verifying ExifTool: {e}")

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

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            arg_file = Path(f.name)
            for file_path in file_paths:
                f.write(f"{file_path}\n")
        try:
            # Execute ExifTool with argument file
            cmd = [
                self.exiftool_path,
                "-api",
                "largefilesupport=1",
                "-charset",
                "filename=utf8",
                "-@",
                str(arg_file),
                "-json",
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=300,  # 5 minute timeout
            )
            if result.returncode != 0:
                logger.error(f"ExifTool error: {result.stderr}")
                raise RuntimeError(
                    f"ExifTool failed with return code {result.returncode}"
                )
            metadata = json.loads(result.stdout)
            logger.debug(f"Successfully extracted metadata from {len(metadata)} files")
            return metadata

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ExifTool JSON output: {e}")
            raise RuntimeError(f"Failed to parse ExifTool output: {e}")
        except subprocess.TimeoutExpired:
            logger.error("ExifTool timed out")
            raise RuntimeError("ExifTool execution timed out")
        finally:
            arg_file.unlink(missing_ok=True)

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
            cmd = [
                self.exiftool_path,
                "-api",
                "largefilesupport=1",
                "-charset",
                "filename=utf8",
                "-q",  # Quiet mode
                "-tagsfromfile",
                str(source_file),
                str(destination_file),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                logger.error(f"Failed to restore metadata: {result.stderr}")
                return False

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
            cmd = [
                self.exiftool_path,
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
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            # ExifTool returns message about files failed condition check, which is acceptable
            if result.returncode != 0 and "files failed condition" not in result.stdout:
                logger.warning(
                    f"Setting file dates returned code {result.returncode}: {result.stderr}"
                )
                return False
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

            # ExifTool evaluates the command-line arguments left to right, and latter assignments to the same tag override earlier ones, so the Directory for each image is ultimately set by the rightmost copy argument that is valid for that image.
            # means the date is taken from tags with the following priority:
            # 1. CreationDate - QuickTime tag which is used in videos; in addition to CreateDate it also contains the time zone
            # 2. DateTimeOriginal - Date and time of original data generation
            # 3. CreateDate - (called DateTimeDigitized by the EXIF spec) Date and time of digital data generation
            # 4. FileModifyDate - Date and time of the last change to the file itself; more reliable than the FileCreateDate since FileCreateDate is changed e.g. on copy operation
            # %-.37f   ignores the last 36 characters of the file name since this is just an UID for internal use
            # %+2c     will add a copy number which is automatically incremented if the file already exists in the format _01, _02 ...

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
            cmd = (
                [
                    self.exiftool_path,
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

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=300,
            )

            # Parse output to track source -> destination mapping
            file_mapping = {}
            for line in result.stdout.split("\n"):
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
            cmd = [
                self.exiftool_path,
                "-api",
                "largefilesupport=1",
                "-charset",
                "filename=utf8",
                "-json",
                "-CaptureMode",
                "-ApplePhotosCaptureMode",
                str(file_path),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data:
                    # Check for both possible tag names
                    return data[0].get("CaptureMode") or data[0].get(
                        "ApplePhotosCaptureMode"
                    )

            return None

        except Exception as e:
            logger.error(f"Error getting capture mode: {e}")
            return None
