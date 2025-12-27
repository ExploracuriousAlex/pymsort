"""Startup checks for external tool availability."""

import logging
import subprocess
from typing import List, Tuple

from .config import config

logger = logging.getLogger(__name__)


def check_exiftool() -> Tuple[bool, str]:
    """Check if ExifTool is available.

    Returns:
        Tuple of (success, message)
    """
    if not config.exiftool_path:
        return (
            False,
            "ExifTool not found in PATH. Please install ExifTool and ensure it's in your system PATH.",
        )

    try:
        result = subprocess.run(
            [config.exiftool_path, "-ver"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            logger.info(f"ExifTool version {version} found at {config.exiftool_path}")
            return True, f"ExifTool {version}"
        else:
            return False, f"ExifTool found but returned error: {result.stderr}"
    except Exception as e:
        return False, f"Failed to run ExifTool: {e}"


def check_ffmpeg() -> Tuple[bool, str]:
    """Check if FFmpeg is available.

    Returns:
        Tuple of (success, message)
    """
    if not config.ffmpeg_path:
        return (
            False,
            "FFmpeg not found. Please install FFmpeg and place it in your system PATH or application directory.",
        )

    try:
        result = subprocess.run(
            [config.ffmpeg_path, "-version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            # Extract version from first line
            first_line = result.stdout.split("\n")[0]
            logger.info(f"FFmpeg found: {first_line}")
            return True, first_line
        else:
            return False, f"FFmpeg found but returned error: {result.stderr}"
    except Exception as e:
        return False, f"Failed to run FFmpeg: {e}"


def check_libfdk_aac() -> Tuple[bool, str]:
    """Check if FFmpeg has libfdk_aac encoder support.

    Returns:
        Tuple of (success, message)
    """
    if not config.ffmpeg_path:
        return False, "FFmpeg not available"

    try:
        result = subprocess.run(
            [config.ffmpeg_path, "-encoders"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            if "libfdk_aac" in result.stdout:
                logger.info("FFmpeg has libfdk_aac encoder support")
                return True, "libfdk_aac encoder available"
            else:
                return (
                    False,
                    "FFmpeg does not have libfdk_aac encoder. Some audio conversions may not be possible.",
                )
        else:
            return False, f"Failed to check FFmpeg encoders: {result.stderr}"
    except Exception as e:
        return False, f"Failed to check libfdk_aac: {e}"


def run_all_checks() -> Tuple[bool, List[str]]:
    """Run all startup checks.

    Returns:
        Tuple of (all_passed, messages)
    """
    messages = []
    all_passed = True

    # Auto-discover tools first
    config.auto_discover_tools()

    # Check ExifTool
    success, msg = check_exiftool()
    messages.append(f"{'✓' if success else '✗'} ExifTool: {msg}")
    if not success:
        all_passed = False

    # Check FFmpeg
    ffmpeg_success, msg = check_ffmpeg()
    messages.append(f"{'✓' if ffmpeg_success else '✗'} FFmpeg: {msg}")
    if not ffmpeg_success:
        all_passed = False

    # Check libfdk_aac only if FFmpeg is available (warning only, not critical)
    if ffmpeg_success:
        success, msg = check_libfdk_aac()
        messages.append(f"{'✓' if success else '⚠'} libfdk_aac: {msg}")
        # Don't fail if libfdk_aac is missing, it's optional

    # Ensure temp directory exists
    if config.ensure_temp_dir():
        messages.append(f"✓ Temporary directory: {config.temp_dir}")
    else:
        messages.append("✗ Failed to create temporary directory")
        all_passed = False

    return all_passed, messages
