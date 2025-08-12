"""
Central path configuration for CAESER Water Levels Monitoring System.

This module provides the single source of truth for all system paths.
All other modules should import from here instead of hardcoding paths.
"""

import os
from pathlib import Path

# Application root directory
APP_ROOT = Path(__file__).parent.parent.parent

# Default shared drive paths - centralized configuration
class DefaultPaths:
    """Default path constants - single source of truth"""
    
    # Base shared drive structure
    SHARED_DRIVE_BASE = "S:/Water_Projects/CAESER/Water_Data_Series/Water_levels_monitoring_system"
    
    # Derived paths
    SHARED_DRIVE_ROOT = f"{SHARED_DRIVE_BASE}/"
    SHARED_DRIVE_PROJECTS = f"{SHARED_DRIVE_BASE}/Projects/"
    SHARED_DRIVE_FIELD_DATA = f"{SHARED_DRIVE_BASE}/FIELD_DATA_CONSOLIDATED/"
    SHARED_DRIVE_FEEDBACK = f"{SHARED_DRIVE_BASE}/App_Feedback/"
    
    # Local paths
    LOCAL_INSTALLATION_DIR = "CAESER_Water_levels_monitoring_system"

def get_default_shared_drive_paths():
    """
    Get default shared drive paths as a dictionary.
    
    Returns:
        dict: Default path configuration
    """
    return {
        "shared_drive_root": DefaultPaths.SHARED_DRIVE_ROOT,
        "shared_drive_projects": DefaultPaths.SHARED_DRIVE_PROJECTS,
        "shared_drive_field_data": DefaultPaths.SHARED_DRIVE_FIELD_DATA,
        "shared_drive_feedback": DefaultPaths.SHARED_DRIVE_FEEDBACK
    }

def get_user_installation_dir():
    """
    Get the default user installation directory.
    
    Returns:
        str: User installation directory path
    """
    return os.path.join(os.path.expanduser("~"), DefaultPaths.LOCAL_INSTALLATION_DIR)

# Legacy support - these will be removed in future versions
LEGACY_SHARED_DRIVE_ROOT = "S:/Water_Projects/CAESER/Water_Data_Series/Water_levels_monitoring/"
LEGACY_WARNING_SHOWN = False

def show_legacy_path_warning():
    """Show warning about legacy path usage (for debugging)"""
    global LEGACY_WARNING_SHOWN
    if not LEGACY_WARNING_SHOWN:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("Using legacy hardcoded path - should be migrated to config-based approach")
        LEGACY_WARNING_SHOWN = True