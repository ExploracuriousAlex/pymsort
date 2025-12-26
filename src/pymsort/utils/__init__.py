"""
Utilities package for pymsort.
Contains helper functions and configuration management.
"""

from .config import Config, config
from .startup_checks import run_all_checks

__all__ = ["Config", "config", "run_all_checks"]
