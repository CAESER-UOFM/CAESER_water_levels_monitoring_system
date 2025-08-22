"""
Cross-Platform SMOO Path Manager for CAESER Water Levels Monitoring System

This module handles automatic detection and switching between Windows and Mac
SMOO paths, allowing seamless development on Mac while maintaining Windows
compatibility for production deployment.

Key Features:
- Automatic platform detection
- SMOO path validation and accessibility testing
- Fallback to local paths when SMOO unavailable
- Windows/Mac path translation
- Thread-safe path resolution
"""

import sys
import platform
import logging
from pathlib import Path
from typing import Optional, Dict, Union
from threading import Lock

logger = logging.getLogger(__name__)

class CrossPlatformSMOOManager:
    """
    Manages SMOO paths across Windows and Mac platforms with automatic detection
    """
    
    # Thread safety for singleton instance
    _instance = None
    _lock = Lock()
    
    # Platform-specific SMOO base paths
    PLATFORM_PATHS = {
        "Windows": [
            "S:/Water_Projects/CAESER/Water_Data_Series/Water_levels_monitoring_system",
            "S:\\Water_Projects\\CAESER\\Water_Data_Series\\Water_levels_monitoring_system"
        ],
        "Darwin": [  # Mac
            "/Volumes/caeserdata/sharedworkspace/Water_Projects/CAESER/Water_Data_Series/Water_levels_monitoring_system",
            "/Volumes/CAESERDATA/sharedworkspace/Water_Projects/CAESER/Water_Data_Series/Water_levels_monitoring_system"
        ]
    }
    
    def __new__(cls):
        """Singleton pattern to ensure one instance per process"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CrossPlatformSMOOManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the SMOO manager"""
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self.current_platform = platform.system()
        self._detected_smoo_path = None
        self._smoo_accessible = None
        self._path_cache = {}
        
        logger.info(f"Initializing SMOO Manager for platform: {self.current_platform}")
        
        # Perform initial detection
        self._detect_smoo_path()
    
    def _detect_smoo_path(self) -> Optional[str]:
        """
        Auto-detect accessible SMOO path for current platform
        
        Returns:
            str: Detected SMOO path or None if not accessible
        """
        platform_paths = self.PLATFORM_PATHS.get(self.current_platform, [])
        
        if not platform_paths:
            logger.warning(f"No SMOO paths configured for platform: {self.current_platform}")
            return None
        
        for path in platform_paths:
            if self._test_path_accessibility(path):
                logger.info(f"SMOO path detected and accessible: {path}")
                self._detected_smoo_path = path
                self._smoo_accessible = True
                return path
        
        logger.warning("No accessible SMOO paths found")
        self._smoo_accessible = False
        return None
    
    def _test_path_accessibility(self, path: str) -> bool:
        """
        Test if a path exists and is accessible
        
        Args:
            path: Path to test
            
        Returns:
            bool: True if accessible, False otherwise
        """
        try:
            path_obj = Path(path)
            
            if not path_obj.exists():
                return False
            
            if not path_obj.is_dir():
                return False
            
            # Test read access by listing contents
            list(path_obj.iterdir())
            return True
            
        except (PermissionError, OSError, FileNotFoundError):
            return False
        except Exception as e:
            logger.debug(f"Unexpected error testing path {path}: {e}")
            return False
    
    def is_smoo_available(self) -> bool:
        """
        Check if SMOO is currently accessible
        
        Returns:
            bool: True if SMOO accessible, False otherwise
        """
        if self._smoo_accessible is None:
            self._detect_smoo_path()
        
        return self._smoo_accessible or False
    
    def get_smoo_base_path(self) -> Optional[str]:
        """
        Get the detected SMOO base path
        
        Returns:
            str: SMOO base path or None if not available
        """
        if self._detected_smoo_path is None:
            self._detect_smoo_path()
        
        return self._detected_smoo_path
    
    def get_smoo_path(self, subfolder: str = "") -> Optional[str]:
        """
        Get SMOO path with optional subfolder
        
        Args:
            subfolder: Optional subfolder path (e.g., "Projects", "FIELD_DATA_CONSOLIDATED")
            
        Returns:
            str: Full SMOO path or None if not available
        """
        base_path = self.get_smoo_base_path()
        if base_path is None:
            return None
        
        if not subfolder:
            return base_path
        
        # Normalize subfolder path
        subfolder = subfolder.strip('/\\')
        if self.current_platform == "Windows":
            full_path = f"{base_path}\\{subfolder}"
        else:
            full_path = f"{base_path}/{subfolder}"
        
        return full_path
    
    def get_all_smoo_paths(self) -> Dict[str, Optional[str]]:
        """
        Get all standard SMOO paths
        
        Returns:
            dict: Dictionary of path names to full paths
        """
        if not self.is_smoo_available():
            return {
                "base": None,
                "projects": None,
                "field_data": None,
                "feedback": None,
                "config": None,
                "credentials": None,
                "user_feedback": None
            }
        
        base = self.get_smoo_base_path()
        return {
            "base": base,
            "projects": self.get_smoo_path("Projects"),
            "field_data": self.get_smoo_path("FIELD_DATA_CONSOLIDATED"),
            "feedback": self.get_smoo_path("App_Feedback"),
            "config": self.get_smoo_path("config"),
            "credentials": self.get_smoo_path("credentials"),
            "user_feedback": self.get_smoo_path("User_Feedback")
        }
    
    def get_fallback_paths(self, app_root: Union[str, Path]) -> Dict[str, str]:
        """
        Get fallback local paths when SMOO is not available
        
        Args:
            app_root: Application root directory
            
        Returns:
            dict: Dictionary of fallback paths
        """
        app_root = Path(app_root)
        
        return {
            "base": str(app_root),
            "projects": str(app_root / "local_projects"),
            "field_data": str(app_root / "local_field_data"),
            "feedback": str(app_root / "local_feedback"),
            "config": str(app_root / "config"),
            "credentials": str(app_root / "credentials"),
            "user_feedback": str(app_root / "local_user_feedback")
        }
    
    def resolve_path(self, path_type: str, app_root: Union[str, Path] = None) -> str:
        """
        Resolve a path with SMOO priority and local fallback
        
        Args:
            path_type: Type of path (base, projects, field_data, feedback, config, credentials)
            app_root: Application root for fallback paths
            
        Returns:
            str: Resolved path (SMOO if available, otherwise local fallback)
        """
        # Try SMOO first
        smoo_paths = self.get_all_smoo_paths()
        if smoo_paths.get(path_type) is not None:
            resolved_path = smoo_paths[path_type]
            logger.debug(f"Resolved {path_type} to SMOO: {resolved_path}")
            return resolved_path
        
        # Fallback to local paths
        if app_root is None:
            # Try to determine app root automatically
            app_root = Path(__file__).parent.parent.parent
        
        fallback_paths = self.get_fallback_paths(app_root)
        resolved_path = fallback_paths.get(path_type, str(app_root))
        
        logger.debug(f"Resolved {path_type} to fallback: {resolved_path}")
        return resolved_path
    
    def refresh_detection(self) -> bool:
        """
        Force refresh of SMOO path detection
        
        Returns:
            bool: True if SMOO is now accessible, False otherwise
        """
        logger.info("Forcing SMOO path detection refresh")
        self._detected_smoo_path = None
        self._smoo_accessible = None
        self._path_cache.clear()
        
        return self._detect_smoo_path() is not None
    
    def get_platform_info(self) -> Dict[str, str]:
        """
        Get platform and path information for debugging
        
        Returns:
            dict: Platform information
        """
        smoo_path = self.get_smoo_base_path()
        
        return {
            "platform": self.current_platform,
            "platform_machine": platform.machine(),
            "python_version": sys.version,
            "smoo_available": str(self.is_smoo_available()),
            "smoo_path": smoo_path or "Not available",
            "possible_paths": str(self.PLATFORM_PATHS.get(self.current_platform, []))
        }


# Global instance - use this throughout the application
smoo_manager = CrossPlatformSMOOManager()


def get_smoo_path(path_type: str = "base", app_root: Union[str, Path] = None) -> str:
    """
    Convenience function to get SMOO paths with fallback
    
    Args:
        path_type: Type of path to retrieve
        app_root: Application root for fallbacks
        
    Returns:
        str: Resolved path
    """
    return smoo_manager.resolve_path(path_type, app_root)


def is_smoo_available() -> bool:
    """
    Convenience function to check SMOO availability
    
    Returns:
        bool: True if SMOO is accessible
    """
    return smoo_manager.is_smoo_available()


def get_platform_info() -> Dict[str, str]:
    """
    Convenience function to get platform information
    
    Returns:
        dict: Platform information
    """
    return smoo_manager.get_platform_info()


def refresh_smoo_detection() -> bool:
    """
    Convenience function to refresh SMOO detection
    
    Returns:
        bool: True if SMOO is accessible after refresh
    """
    return smoo_manager.refresh_detection()