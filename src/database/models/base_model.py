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
    
    def mark_modified(self):
        """Mark the database as modified"""
        logger.info(f"BASE_MODEL_DEBUG: mark_modified called for {self.db_path}")
        logger.info(f"BASE_MODEL_DEBUG: db_manager exists: {self.db_manager is not None}")
        if self.db_manager:
            logger.info(f"BASE_MODEL_DEBUG: Calling db_manager.mark_as_modified()")
            self.db_manager.mark_as_modified()
            logger.info(f"BASE_MODEL_DEBUG: Successfully called mark_as_modified for {self.db_path}")
        else:
            logger.warning(f"BASE_MODEL_DEBUG: No db_manager set for {self.db_path} - cannot mark as modified") 