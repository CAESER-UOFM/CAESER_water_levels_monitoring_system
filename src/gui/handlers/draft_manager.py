"""
Draft Manager for Cloud Databases

Handles local draft persistence for cloud databases, allowing users to:
1. Work on local changes without uploading immediately
2. Resume work on drafts after app restart
3. Get notified when cloud version changes while working on drafts
4. Clean up drafts after successful cloud uploads
"""

import os
import json
import shutil
import logging
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class DraftManager:
    """Manages local drafts of cloud databases"""
    
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        self.drafts_dir = os.path.join(cache_dir, 'drafts')
        self.drafts_metadata_file = os.path.join(self.drafts_dir, 'drafts_metadata.json')
        
        # Ensure drafts directory exists
        os.makedirs(self.drafts_dir, exist_ok=True)
        
    def save_draft(self, project_name: str, temp_db_path: str, 
                   original_download_time: str, changes_description: str = None) -> bool:
        """
        Save current database state as a local draft.
        
        Args:
            project_name: Name of the cloud project
            temp_db_path: Path to the current temporary database
            original_download_time: When the original version was downloaded
            changes_description: Optional description of changes
            
        Returns:
            True if draft saved successfully
        """
        try:
            # Create draft filename
            draft_filename = f"{project_name}_draft.db"
            draft_path = os.path.join(self.drafts_dir, draft_filename)
            
            # Copy current database to draft location
            shutil.copy2(temp_db_path, draft_path)
            
            # Save draft metadata
            draft_metadata = {
                'project_name': project_name,
                'draft_filename': draft_filename,
                'original_download_time': original_download_time,
                'draft_created_at': datetime.now().isoformat(),
                'draft_updated_at': datetime.now().isoformat(),
                'changes_description': changes_description or "Local changes",
                'has_unsaved_changes': True
            }
            
            # Load existing drafts metadata
            drafts_data = self._load_drafts_metadata()
            
            # Update or add this draft
            drafts_data[project_name] = draft_metadata
            
            # Save updated metadata
            self._save_drafts_metadata(drafts_data)
            
            logger.info(f"Draft saved for project: {project_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving draft for {project_name}: {e}")
            return False
    
    def has_draft(self, project_name: str) -> bool:
        """Check if a draft exists for the given project."""
        try:
            drafts_data = self._load_drafts_metadata()
            return project_name in drafts_data and drafts_data[project_name].get('has_unsaved_changes', False)
        except Exception as e:
            logger.error(f"Error checking for draft: {e}")
            return False
    
    def get_draft_info(self, project_name: str) -> Optional[Dict]:
        """Get information about a draft."""
        try:
            drafts_data = self._load_drafts_metadata()
            return drafts_data.get(project_name)
        except Exception as e:
            logger.error(f"Error getting draft info: {e}")
            return None
    
    def load_draft(self, project_name: str, temp_dir: str) -> Optional[str]:
        """
        Load a draft database to a temporary location.
        
        Args:
            project_name: Name of the project
            temp_dir: Directory to copy the draft to
            
        Returns:
            Path to the loaded draft, or None if failed
        """
        try:
            draft_info = self.get_draft_info(project_name)
            if not draft_info:
                return None
                
            draft_path = os.path.join(self.drafts_dir, draft_info['draft_filename'])
            if not os.path.exists(draft_path):
                logger.warning(f"Draft file not found: {draft_path}")
                return None
            
            # Create new temp filename
            import uuid
            temp_filename = f"wlm_{project_name}_{uuid.uuid4().hex[:8]}.db"
            temp_path = os.path.join(temp_dir, temp_filename)
            
            # Copy draft to temp location
            shutil.copy2(draft_path, temp_path)
            
            logger.info(f"Draft loaded for project: {project_name}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Error loading draft for {project_name}: {e}")
            return None
    
    def clear_draft(self, project_name: str) -> bool:
        """
        Clear a draft after successful cloud upload.
        
        Args:
            project_name: Name of the project
            
        Returns:
            True if cleared successfully
        """
        try:
            # Load existing drafts
            drafts_data = self._load_drafts_metadata()
            
            if project_name in drafts_data:
                # Remove draft file
                draft_info = drafts_data[project_name]
                draft_path = os.path.join(self.drafts_dir, draft_info['draft_filename'])
                if os.path.exists(draft_path):
                    os.remove(draft_path)
                
                # Remove from metadata
                del drafts_data[project_name]
                self._save_drafts_metadata(drafts_data)
                
                logger.info(f"Draft cleared for project: {project_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing draft for {project_name}: {e}")
            return False
    
    def update_draft(self, project_name: str, temp_db_path: str, 
                     changes_description: str = None) -> bool:
        """Update an existing draft with current changes."""
        try:
            draft_info = self.get_draft_info(project_name)
            if not draft_info:
                logger.warning(f"No existing draft to update for: {project_name}")
                return False
            
            # Update the draft file
            draft_path = os.path.join(self.drafts_dir, draft_info['draft_filename'])
            shutil.copy2(temp_db_path, draft_path)
            
            # Update metadata
            drafts_data = self._load_drafts_metadata()
            drafts_data[project_name]['draft_updated_at'] = datetime.now().isoformat()
            if changes_description:
                drafts_data[project_name]['changes_description'] = changes_description
            
            self._save_drafts_metadata(drafts_data)
            
            logger.info(f"Draft updated for project: {project_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating draft for {project_name}: {e}")
            return False
    
    def list_drafts(self) -> List[Dict]:
        """List all available drafts."""
        try:
            drafts_data = self._load_drafts_metadata()
            return [
                info for info in drafts_data.values() 
                if info.get('has_unsaved_changes', False)
            ]
        except Exception as e:
            logger.error(f"Error listing drafts: {e}")
            return []
    
    def check_version_changes(self, project_name: str, current_cloud_time: str) -> Dict:
        """
        Check if cloud version changed since draft was created.
        
        Returns:
            Dict with 'changed': bool and 'info': draft_info
        """
        try:
            draft_info = self.get_draft_info(project_name)
            if not draft_info:
                return {'changed': False, 'info': None}
            
            original_time = draft_info.get('original_download_time')
            changed = original_time != current_cloud_time
            
            return {
                'changed': changed,
                'info': draft_info,
                'original_time': original_time,
                'current_cloud_time': current_cloud_time
            }
            
        except Exception as e:
            logger.error(f"Error checking version changes: {e}")
            return {'changed': False, 'info': None}
    
    def _load_drafts_metadata(self) -> Dict:
        """Load drafts metadata from file."""
        try:
            if os.path.exists(self.drafts_metadata_file):
                with open(self.drafts_metadata_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading drafts metadata: {e}")
            return {}
    
    def _save_drafts_metadata(self, drafts_data: Dict) -> bool:
        """Save drafts metadata to file."""
        try:
            with open(self.drafts_metadata_file, 'w') as f:
                json.dump(drafts_data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving drafts metadata: {e}")
            return False