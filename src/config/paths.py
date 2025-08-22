"""
Central path configuration for CAESER Water Levels Monitoring System.

This module provides the single source of truth for all system paths.
All other modules should import from here instead of hardcoding paths.

UPDATED: Now includes cross-platform SMOO support with automatic Mac/Windows detection.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

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
    
    Now includes cross-platform SMOO detection with automatic Mac/Windows switching.
    
    Returns:
        dict: Default path configuration (SMOO paths if available, fallback to Windows paths)
    """
    # Try to use cross-platform SMOO manager
    try:
        from .smoo_paths import smoo_manager
        
        if smoo_manager.is_smoo_available():
            # Use SMOO paths (auto-detected for current platform)
            smoo_paths = smoo_manager.get_all_smoo_paths()
            logger.info("Using SMOO paths for shared drive configuration")
            return {
                "shared_drive_root": smoo_paths["base"] + "/",
                "shared_drive_projects": smoo_paths["projects"] + "/",
                "shared_drive_field_data": smoo_paths["field_data"] + "/",
                "shared_drive_feedback": smoo_paths["feedback"] + "/"
            }
        else:
            logger.warning("SMOO not available, falling back to default Windows paths")
    except ImportError:
        logger.warning("SMOO manager not available, using legacy paths")
    except Exception as e:
        logger.error(f"Error accessing SMOO manager: {e}, falling back to legacy paths")
    
    # Fallback to legacy Windows paths
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
        logger.warning("Using legacy hardcoded path - should be migrated to config-based approach")
        LEGACY_WARNING_SHOWN = True


def get_smoo_aware_path(path_type: str, fallback_to_local: bool = True):
    """
    Get cross-platform SMOO-aware path with intelligent fallbacks.
    
    Args:
        path_type: Type of path (base, projects, field_data, feedback, config, credentials)
        fallback_to_local: If True, fallback to local app paths when SMOO unavailable
        
    Returns:
        str: Resolved path (SMOO preferred, with fallbacks)
    """
    try:
        from .smoo_paths import get_smoo_path
        
        # Try SMOO path first
        smoo_path = get_smoo_path(path_type, APP_ROOT if fallback_to_local else None)
        if smoo_path:
            return smoo_path
            
    except ImportError:
        logger.debug("SMOO manager not available")
    except Exception as e:
        logger.error(f"Error getting SMOO path for {path_type}: {e}")
    
    # Fallback to legacy configuration
    legacy_paths = {
        "base": DefaultPaths.SHARED_DRIVE_BASE,
        "projects": DefaultPaths.SHARED_DRIVE_PROJECTS.rstrip('/'),
        "field_data": DefaultPaths.SHARED_DRIVE_FIELD_DATA.rstrip('/'),
        "feedback": DefaultPaths.SHARED_DRIVE_FEEDBACK.rstrip('/'),
        "config": str(APP_ROOT / "config"),
        "credentials": str(APP_ROOT / "credentials")
    }
    
    return legacy_paths.get(path_type, str(APP_ROOT))


def is_smoo_environment():
    """
    Check if we're running in a SMOO-enabled environment.
    
    Returns:
        bool: True if SMOO is available and accessible
    """
    try:
        from .smoo_paths import is_smoo_available
        return is_smoo_available()
    except ImportError:
        return False
    except Exception:
        return False


def get_platform_appropriate_paths():
    """
    Get paths appropriate for the current platform and environment.
    
    Returns:
        dict: Platform-appropriate path configuration
    """
    if is_smoo_environment():
        try:
            from .smoo_paths import smoo_manager
            paths = smoo_manager.get_all_smoo_paths()
            logger.info("Using SMOO paths for platform-appropriate configuration")
            return {
                "shared_drive_base": paths["base"],
                "shared_drive_projects": paths["projects"],
                "shared_drive_field_data": paths["field_data"],
                "shared_drive_feedback": paths["feedback"],
                "config_dir": paths["config"],
                "credentials_dir": paths.get("credentials", str(APP_ROOT / "credentials"))
            }
        except Exception as e:
            logger.error(f"Error getting SMOO paths: {e}")
    
    # Fallback to Windows/legacy paths
    logger.info("Using legacy Windows paths for configuration")
    return {
        "shared_drive_base": DefaultPaths.SHARED_DRIVE_BASE,
        "shared_drive_projects": DefaultPaths.SHARED_DRIVE_PROJECTS.rstrip('/'),
        "shared_drive_field_data": DefaultPaths.SHARED_DRIVE_FIELD_DATA.rstrip('/'),
        "shared_drive_feedback": DefaultPaths.SHARED_DRIVE_FEEDBACK.rstrip('/'),
        "config_dir": str(APP_ROOT / "config"),
        "credentials_dir": str(APP_ROOT / "credentials")
    }