"""
Version Checker for Water Level Monitoring Application
Checks GitHub for new releases and manages version information.
"""

import requests
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
try:
    from packaging import version
except ImportError:
    # Fallback for simple version comparison
    class version:
        @staticmethod
        def parse(v):
            return tuple(map(int, v.split('.')))

logger = logging.getLogger(__name__)

class VersionChecker:
    """Handles version checking and comparison"""
    
    def __init__(self, current_version: str, github_repo: str = "benjaled/water_levels_monitoring"):
        """
        Initialize version checker
        
        Args:
            current_version: Current application version (e.g., "1.0.0")
            github_repo: GitHub repository in format "owner/repo"
        """
        self.current_version = current_version
        self.github_repo = github_repo
        self.github_api_url = f"https://api.github.com/repos/{github_repo}/releases"
        
    def get_current_version(self) -> str:
        """Get current application version"""
        return self.current_version
        
    def get_latest_release(self) -> Optional[Dict]:
        """
        Get latest release information from GitHub
        
        Returns:
            Dict with release information or None if error
        """
        try:
            response = requests.get(f"{self.github_api_url}/latest", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch latest release: {e}")
            return None
            
    def is_update_available(self) -> Tuple[bool, Optional[str]]:
        """
        Check if update is available
        
        Returns:
            Tuple of (is_available, latest_version)
        """
        latest_release = self.get_latest_release()
        if not latest_release:
            return False, None
            
        latest_version = latest_release.get('tag_name', '').lstrip('v')
        
        try:
            if version.parse(latest_version) > version.parse(self.current_version):
                return True, latest_version
        except Exception as e:
            logger.error(f"Version comparison failed: {e}")
            
        return False, latest_version
        
    def get_update_info(self) -> Optional[Dict]:
        """
        Get detailed update information
        
        Returns:
            Dict with update details or None
        """
        is_available, latest_version = self.is_update_available()
        
        if not is_available:
            return None
            
        latest_release = self.get_latest_release()
        if not latest_release:
            return None
            
        # Find download URL for source code
        download_url = None
        for asset in latest_release.get('assets', []):
            if asset['name'].endswith('.zip') and 'source' in asset['name'].lower():
                download_url = asset['browser_download_url']
                break
                
        # If no specific source asset, use the tarball
        if not download_url:
            download_url = latest_release.get('tarball_url')
            
        return {
            'version': latest_version,
            'current_version': self.current_version,
            'release_notes': latest_release.get('body', ''),
            'download_url': download_url,
            'release_date': latest_release.get('published_at'),
            'prerelease': latest_release.get('prerelease', False),
            'size': self._get_download_size(download_url) if download_url else None
        }
        
    def _get_download_size(self, url: str) -> Optional[int]:
        """Get download size without downloading"""
        try:
            response = requests.head(url, timeout=10)
            return int(response.headers.get('content-length', 0))
        except:
            return None