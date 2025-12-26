"""Configuration management for pymsort."""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class Config:
    """Application configuration."""

    def __init__(self):
        """Initialize configuration with default values."""
        self.exiftool_path: Optional[str] = None
        self.ffmpeg_path: Optional[str] = None
        self.temp_dir: Path = Path.home() / ".pymsort" / "temp"

    def ensure_temp_dir(self) -> bool:
        """Create temporary directory if it doesn't exist.

        Returns:
            bool: True if directory exists or was created successfully, False otherwise.
        """
        try:
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Temporary directory ready: {self.temp_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to create temporary directory: {e}")
            return False

    def find_tool(self, tool_name: str) -> Optional[str]:
        """Find tool in local directory or PATH.

        Args:
            tool_name: Name of the tool executable (e.g., 'exiftool', 'ffmpeg')

        Returns:
            Full path to the tool if found, None otherwise.
        """
        # On Windows, try both with and without .exe extension
        tool_variants = [tool_name]
        if os.name == "nt" and not tool_name.endswith(".exe"):
            tool_variants.append(f"{tool_name}.exe")

        # First, search in local directory (project root)
        local_dir = Path(
            __file__
        ).parent.parent.parent.parent  # Navigate up to project root
        for variant in tool_variants:
            local_tool_path = local_dir / variant
            if local_tool_path.is_file() and os.access(local_tool_path, os.X_OK):
                logger.info(f"Found {tool_name} in local directory: {local_tool_path}")
                return str(local_tool_path)

        # Then search in PATH
        for variant in tool_variants:
            for path_dir in os.environ.get("PATH", "").split(os.pathsep):
                tool_path = Path(path_dir) / variant
                if tool_path.is_file() and os.access(tool_path, os.X_OK):
                    logger.debug(f"Found {tool_name} in PATH: {tool_path}")
                    return str(tool_path)

        logger.warning(f"Tool not found in local directory or PATH: {tool_name}")
        return None

    def auto_discover_tools(self) -> None:
        """Automatically discover external tools in PATH."""
        self.exiftool_path = self.find_tool("exiftool")
        self.ffmpeg_path = self.find_tool("ffmpeg")


# Global configuration instance
config = Config()
