"""Main entry point for pymsort application."""

import os
import sys

# Set LC_TIME environment variable before any imports
# This ensures ExifTool subprocess inherits it for German month names
os.environ["LC_TIME"] = "de_DE.UTF-8"

from src.pymsort.app import main

if __name__ == "__main__":
    sys.exit(main())
