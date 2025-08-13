# -*- coding: utf-8 -*-
"""
Base model class for database models.

This module provides a base class for all database models to inherit from.
It includes common functionality like marking the database as modified.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class BaseModel:
    """Base class for all database models"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_manager = None
    
    def set_db_manager(self, db_manager):
        """Set the database manager reference for marking modifications"""
        self.db_manager = db_manager
        logger.info(f"DB_MANAGER_DEBUG: set_db_manager called for {self.db_path}")
        logger.info(f"DB_MANAGER_DEBUG: db_manager is_cloud_database={getattr(db_manager, 'is_cloud_database', 'MISSING')}")
        logger.info(f"DB_MANAGER_DEBUG: db_manager is_loaded_from_draft={getattr(db_manager, 'is_loaded_from_draft', 'MISSING')}")
    
    def mark_modified(self):
        """Mark the database as modified"""
        if self.db_manager:
            self.db_manager.mark_as_modified()
            logger.debug(f"Marked database {self.db_path} as modified")
        else:
            logger.warning(f"No db_manager set for {self.db_path} - cannot mark as modified") 