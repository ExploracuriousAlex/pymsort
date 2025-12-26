"""
Service for interacting with FFmpeg.
Handles video conversion operations.
"""

import logging
import subprocess
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)


class FFmpegService:
    """Service class for FFmpeg operations."""

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        """
        Initialize FFmpeg service.

        Args:
            ffmpeg_path: Path to ffmpeg executable (default: "ffmpeg" assumes it's in PATH or application directory)
        """
        self.ffmpeg_path = ffmpeg_path
        self._verify_ffmpeg()

    def _verify_ffmpeg(self) -> None:
        """Verify that FFmpeg is available and working."""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                # Extract version from first line
                version_line = result.stdout.split("\n")[0]
                logger.info(f"FFmpeg found: {version_line}")
            else:
                raise RuntimeError(f"FFmpeg verification failed: {result.stderr}")
        except FileNotFoundError:
            raise RuntimeError(
                f"FFmpeg not found at '{self.ffmpeg_path}'. "
                "Please install FFmpeg and place it in your system PATH or application directory."
            )
        except Exception as e:
            raise RuntimeError(f"Error verifying FFmpeg: {e}")

    def check_libfdk_aac_support(self) -> bool:
        """
        Check if FFmpeg was compiled with libfdk_aac encoder support.

        Returns:
            True if libfdk_aac is supported, False otherwise
        """
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-loglevel", "error", "-h", "encoder=libfdk_aac"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            has_support = "Encoder libfdk_aac [Fraunhofer FDK AAC]" in result.stdout

            if has_support:
                logger.info("FFmpeg supports libfdk_aac encoder")
            else:
                logger.warning("FFmpeg does NOT support libfdk_aac encoder")

            return has_support

        except Exception as e:
            logger.error(f"Error checking libfdk_aac support: {e}")
            return False

    def convert_video(
        self, source_file: Path, destination_file: Path, ffmpeg_command_template: str
    ) -> Tuple[bool, str]:
        """
        Convert video file using FFmpeg.

        Args:
            source_file: Source video file
            destination_file: Destination video file
            ffmpeg_command_template: FFmpeg command template with %s placeholders
                                    (first %s = source, second %s = destination)

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        # Format the command with actual file paths
        command = ffmpeg_command_template % (str(source_file), str(destination_file))

        logger.info(f"Converting video: {source_file} -> {destination_file}")
        logger.debug(f"FFmpeg command: {command}")

        try:
            # Run FFmpeg command
            # Note: The command template includes the full command, so we execute via shell
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout for conversion
            )

            if result.returncode != 0:
                error_msg = f"FFmpeg failed with return code {result.returncode}: {result.stderr}"
                logger.error(error_msg)
                return False, error_msg

            # Verify destination file exists and has content
            if not destination_file.exists():
                error_msg = "Destination file was not created"
                logger.error(error_msg)
                return False, error_msg

            if destination_file.stat().st_size == 0:
                error_msg = "Destination file is empty"
                logger.error(error_msg)
                return False, error_msg

            logger.info(f"Successfully converted video to {destination_file}")
            return True, ""

        except subprocess.TimeoutExpired:
            error_msg = "FFmpeg conversion timed out (exceeded 1 hour)"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error during video conversion: {e}"
            logger.error(error_msg)
            return False, error_msg
