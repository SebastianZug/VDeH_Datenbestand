"""
Notebook Utilities for VDEh Project
====================================

Common setup functions for Jupyter notebooks to reduce code duplication.
This module provides standardized project initialization and configuration loading.

Usage in notebooks:
    from utils.notebook_utils import setup_notebook

    project_root, config = setup_notebook()
"""

import sys
import logging
from pathlib import Path
from typing import Tuple, Optional

# Logger for this module
logger = logging.getLogger(__name__)


def find_project_root(start_path: Optional[Path] = None, marker_file: str = 'config.yaml') -> Path:
    """
    Find project root by searching for a marker file in parent directories.

    Args:
        start_path: Starting directory (defaults to current working directory)
        marker_file: File to search for that indicates project root

    Returns:
        Path to project root

    Raises:
        FileNotFoundError: If marker file is not found in any parent directory

    Example:
        >>> project_root = find_project_root()
        >>> print(f"Project root: {project_root}")
    """
    if start_path is None:
        start_path = Path.cwd()

    # Search in current directory and all parent directories
    for parent in [start_path] + list(start_path.parents):
        marker_path = parent / marker_file
        if marker_path.exists():
            logger.debug(f"Found project root at {parent}")
            return parent

    # Marker file not found
    searched_paths = [str(p) for p in ([start_path] + list(start_path.parents))]
    raise FileNotFoundError(
        f"{marker_file} not found in any parent directory. "
        f"Searched paths: {searched_paths}"
    )


def add_src_to_path(project_root: Path) -> None:
    """
    Add project's src directory to Python path if not already present.

    This allows importing project modules without installing the package.

    Args:
        project_root: Path to project root directory

    Example:
        >>> project_root = Path('/path/to/project')
        >>> add_src_to_path(project_root)
        >>> import parsers  # Now works!
    """
    src_path = project_root / 'src'
    src_path_str = str(src_path)

    if src_path_str not in sys.path:
        sys.path.insert(0, src_path_str)
        logger.debug(f"Added {src_path} to Python path")
    else:
        logger.debug(f"{src_path} already in Python path")


def configure_logging(level: int = logging.INFO, format_string: Optional[str] = None) -> None:
    """
    Configure logging for notebook environment.

    Args:
        level: Logging level (default: INFO)
        format_string: Custom format string (optional)

    Example:
        >>> configure_logging(level=logging.DEBUG)
        >>> logger.info("This is an info message")
    """
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    logging.basicConfig(
        level=level,
        format=format_string,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger.debug(f"Logging configured at level {logging.getLevelName(level)}")


def setup_notebook(
    marker_file: str = 'config.yaml',
    add_src: bool = True,
    configure_logs: bool = True,
    log_level: int = logging.INFO
) -> Tuple[Path, object]:
    """
    Complete notebook setup: find project root, add src to path, load config, setup logging.

    This is the main function to use at the start of notebooks.

    Args:
        marker_file: File indicating project root (default: 'config.yaml')
        add_src: Whether to add src/ to Python path (default: True)
        configure_logs: Whether to configure logging (default: True)
        log_level: Logging level if configure_logs is True

    Returns:
        Tuple of (project_root, config) where:
            - project_root is a Path object
            - config is a VDEHConfig object

    Raises:
        FileNotFoundError: If project root cannot be found
        RuntimeError: If configuration cannot be loaded

    Example:
        >>> from utils.notebook_utils import setup_notebook
        >>> project_root, config = setup_notebook()
        >>> print(f"Project: {config.get('project.name')}")
        >>> print(f"Root: {project_root}")
    """
    # Configure logging first if requested
    if configure_logs:
        configure_logging(level=log_level)

    # Find project root
    logger.info("Searching for project root...")
    project_root = find_project_root(marker_file=marker_file)
    logger.info(f"Project root found: {project_root}")

    # Add src to path if requested
    if add_src:
        add_src_to_path(project_root)

    # Load configuration
    try:
        from config_loader import load_config
        logger.info("Loading configuration...")
        config_path = project_root / marker_file
        config = load_config(str(config_path))
        logger.info(f"Configuration loaded successfully: {config.get('project.name')}")
        return project_root, config
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise RuntimeError(f"Configuration loading failed: {e}") from e


def display_notebook_info(project_root: Path, config: object) -> None:
    """
    Display notebook environment information.

    Useful for debugging and documentation in notebooks.

    Args:
        project_root: Path to project root
        config: VDEHConfig object

    Example:
        >>> project_root, config = setup_notebook()
        >>> display_notebook_info(project_root, config)
    """
    import pandas as pd
    import numpy as np

    info = {
        'Project Root': str(project_root),
        'Project Name': config.get('project.name'),
        'Project Version': config.get('project.version'),
        'Config Path': str(config.config_path),
        'Python Path (src)': str(project_root / 'src'),
        'Pandas Version': pd.__version__,
        'NumPy Version': np.__version__,
    }

    print("=" * 60)
    print("NOTEBOOK ENVIRONMENT INFO")
    print("=" * 60)
    for key, value in info.items():
        print(f"{key:20s}: {value}")
    print("=" * 60)


# Convenience imports for notebooks
__all__ = [
    'setup_notebook',
    'find_project_root',
    'add_src_to_path',
    'configure_logging',
    'display_notebook_info'
]
