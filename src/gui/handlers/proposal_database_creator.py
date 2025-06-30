import os
import json
import sqlite3
import logging
import tempfile
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class ProposalDatabaseCreator:
    """Creates reduced databases containing only changed records for proposals"""
    
    def __init__(self, db_manager, change_tracker):
        """
        Initialize the proposal database creator.
        
        Args:
            db_manager: DatabaseManager instance
            change_tracker: ChangeTracker instance
        """
        self.db_manager = db_manager
        self.change_tracker = change_tracker
        self._last_statistics = None  # Cache for statistics to avoid re-reading database
        
    def create_proposal_database(self, output_path: str, base_version_info: Dict = None) -> bool:
        """
        Create a reduced database containing only changed records.
        
        Args:
            output_path: Path where to save the proposal database
            base_version_info: Information about the base version being compared against
            
        Returns:
            bool: True if creation successful, False otherwise
        """
        try:
            # Get proposal data from change tracker
            proposal_data = self.change_tracker.extract_proposal_data()
            
            if not proposal_data["changes"]:
                logger.warning("No changes to create proposal from")
                return False
            
            # Create new SQLite database
            conn = sqlite3.connect(output_path)
            cursor = conn.cursor()
            
            try:
                # Create metadata table for proposal information
                self._create_metadata_table(cursor, proposal_data, base_version_info)
                
                # Process each table with changes
                for table_name, changes in proposal_data["changes"].items():
                    if table_name in ["wells", "water_levels", "water_level_readings", "barologgers", "transducers"]:
                        self._create_proposal_table(cursor, table_name, changes)
                
                # CRITICAL: Commit the transaction before returning
                conn.commit()
                logger.info(f"Created proposal database: {output_path}")
                logger.info("Proposal database transaction committed successfully")
                
                # Log statistics and return them directly
                stats = proposal_data["statistics"]
                logger.info(f"Proposal contains {stats['total_changes']} changes affecting {stats['total_records_affected']} records")
                
                # Return the statistics directly to avoid re-reading the database
                self._last_statistics = {
                    "metadata": proposal_data.get("metadata", {}),
                    "table_statistics": self._extract_table_stats_from_changes(proposal_data["changes"])
                }
                
                return True
                
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Error creating proposal database: {e}")
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass
            return False
    
    def _create_metadata_table(self, cursor: sqlite3.Cursor, proposal_data: Dict, base_version_info: Dict = None):
        """Create metadata table with proposal information"""
        cursor.execute("""
            CREATE TABLE proposal_metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        current_user = self.change_tracker.user_auth_service.current_user or "Unknown"
        project_name = getattr(self.db_manager, 'cloud_project_name', 'Unknown')
        
        metadata = {
            "proposal_version": "1.0",
            "created_at": datetime.now().isoformat(),
            "author": current_user,
            "project_name": project_name,
            "session_id": proposal_data["statistics"]["session_id"],
            "total_changes": str(proposal_data["statistics"]["total_changes"]),
            "total_records_affected": str(proposal_data["statistics"]["total_records_affected"]),
            "tables_modified": json.dumps(proposal_data["statistics"]["tables_modified"]),
            "base_version_time": base_version_info.get("modified_time", "") if base_version_info else "",
            "base_version_name": base_version_info.get("name", "") if base_version_info else ""
        }
        
        for key, value in metadata.items():
            cursor.execute("INSERT INTO proposal_metadata (key, value) VALUES (?, ?)", (key, value))
    
    def _create_proposal_table(self, cursor: sqlite3.Cursor, table_name: str, changes: Dict):
        """Create a table containing only the changed records"""
        try:
            # Get the schema from the source database
            # Use temp_db_path for cloud databases, current_db for local databases
            if hasattr(self.db_manager, 'temp_db_path') and self.db_manager.temp_db_path:
                source_db_path = self.db_manager.temp_db_path
            elif hasattr(self.db_manager, 'current_db') and self.db_manager.current_db:
                source_db_path = str(self.db_manager.current_db)
            else:
                raise ValueError("No database path available in DatabaseManager")
            
            source_conn = sqlite3.connect(source_db_path)
            source_cursor = source_conn.cursor()
            
            # Get table schema
            source_cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            schema_result = source_cursor.fetchone()
            
            if not schema_result:
                logger.warning(f"Table {table_name} not found in source database")
                source_conn.close()
                return
            
            # Create table with same schema but different name for proposal
            table_sql = schema_result[0]
            proposal_table_name = f"proposal_{table_name}"
            
            # Modify the CREATE TABLE statement to include proposal columns directly
            # This is more reliable than ALTER TABLE
            if ")" in table_sql:
                # Insert proposal columns before the closing parenthesis
                closing_paren_pos = table_sql.rfind(")")
                proposal_columns = ", proposal_action TEXT, proposal_change_id TEXT"
                modified_sql = table_sql[:closing_paren_pos] + proposal_columns + table_sql[closing_paren_pos:]
                proposal_sql = modified_sql.replace(f"CREATE TABLE {table_name}", f"CREATE TABLE {proposal_table_name}")
            else:
                # Fallback to original method
                proposal_sql = table_sql.replace(f"CREATE TABLE {table_name}", f"CREATE TABLE {proposal_table_name}")
            
            logger.info(f"Creating proposal table with SQL: {proposal_sql}")
            cursor.execute(proposal_sql)
            
            # Verify the columns were created
            cursor.execute(f"PRAGMA table_info({proposal_table_name})")
            table_info = cursor.fetchall()
            column_names = [row[1] for row in table_info]
            logger.info(f"Created table {proposal_table_name} with columns: {column_names}")
            
            if "proposal_action" not in column_names:
                logger.error(f"proposal_action column not found in {proposal_table_name}. Available columns: {column_names}")
                logger.info(f"Original table SQL was: {table_sql}")
                logger.info(f"Modified SQL was: {proposal_sql}")
                # Try ALTER TABLE as fallback
                try:
                    cursor.execute(f"ALTER TABLE {proposal_table_name} ADD COLUMN proposal_action TEXT")
                    cursor.execute(f"ALTER TABLE {proposal_table_name} ADD COLUMN proposal_change_id TEXT")
                    logger.info(f"Added proposal columns via ALTER TABLE for {proposal_table_name}")
                    # Verify again
                    cursor.execute(f"PRAGMA table_info({proposal_table_name})")
                    table_info = cursor.fetchall()
                    column_names = [row[1] for row in table_info]
                    logger.info(f"After ALTER TABLE, columns are: {column_names}")
                except Exception as alter_error:
                    logger.error(f"Failed to add proposal columns via ALTER TABLE: {alter_error}")
                    raise
            else:
                logger.info(f"Proposal columns successfully created in {proposal_table_name}")
            
            # Get column names for the original table
            source_cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in source_cursor.fetchall()]
            columns_str = ", ".join(columns)
            
            # Extract changed records and insert them
            record_ids_processed = set()
            
            # Process added records
            for change in changes.get("added", []):
                record_id = change["record_id"]
                if record_id not in record_ids_processed:
                    self._copy_record(source_cursor, cursor, table_name, proposal_table_name, 
                                    columns_str, record_id, "added", change["id"])
                    record_ids_processed.add(record_id)
            
            # Process modified records  
            for change in changes.get("modified", []):
                record_id = change["record_id"]
                if record_id not in record_ids_processed:
                    self._copy_record(source_cursor, cursor, table_name, proposal_table_name,
                                    columns_str, record_id, "modified", change["id"])
                    record_ids_processed.add(record_id)
            
            # Process deleted records (store the record data before deletion)
            for change in changes.get("deleted", []):
                record_id = change["record_id"]
                if record_id not in record_ids_processed:
                    self._copy_record(source_cursor, cursor, table_name, proposal_table_name,
                                    columns_str, record_id, "deleted", change["id"])
                    record_ids_processed.add(record_id)
            
            source_conn.close()
            logger.info(f"Created proposal table {proposal_table_name} with {len(record_ids_processed)} records")
            
        except Exception as e:
            logger.error(f"Error creating proposal table {table_name}: {e}")
    
    def _copy_record(self, source_cursor: sqlite3.Cursor, dest_cursor: sqlite3.Cursor, 
                    source_table: str, dest_table: str, columns_str: str, 
                    record_id: Any, action: str, change_id: str):
        """Copy a specific record from source to destination table"""
        try:
            # Find the record in the source table
            # For wells table, use well_number as the key
            if source_table == "wells":
                key_column = "well_number"
            elif source_table in ["water_levels", "water_level_readings"]:
                # For water_levels/water_level_readings tables, use well_number as key
                key_column = "well_number"
            else:
                # Default to id column
                key_column = "id"
            
            source_cursor.execute(f"SELECT {columns_str} FROM {source_table} WHERE {key_column} = ?", (record_id,))
            row = source_cursor.fetchone()
            
            if row:
                # Insert into proposal table with additional metadata
                placeholders = ", ".join(["?" for _ in row])
                insert_sql = f"INSERT INTO {dest_table} ({columns_str}, proposal_action, proposal_change_id) VALUES ({placeholders}, ?, ?)"
                dest_cursor.execute(insert_sql, list(row) + [action, change_id])
            else:
                logger.warning(f"Record {record_id} not found in {source_table}")
                
        except Exception as e:
            logger.error(f"Error copying record {record_id} from {source_table}: {e}")
    
    def _extract_table_stats_from_changes(self, changes: Dict) -> Dict[str, Dict[str, int]]:
        """Extract table statistics directly from changes data"""
        table_stats = {}
        
        for table_name, table_changes in changes.items():
            if table_name in ["wells", "water_levels", "water_level_readings", "barologgers", "transducers"]:
                stats = {}
                if table_changes.get("added"):
                    stats["added"] = len(table_changes["added"])
                if table_changes.get("modified"):
                    stats["modified"] = len(table_changes["modified"])
                if table_changes.get("deleted"):
                    stats["deleted"] = len(table_changes["deleted"])
                
                if stats:  # Only add if there are actual changes
                    table_stats[table_name] = stats
        
        return table_stats
    
    def get_proposal_statistics(self, proposal_db_path: str) -> Dict[str, Any]:
        """Get statistics from a proposal database"""
        # Use cached statistics if available (avoids database re-reading issues)
        if self._last_statistics:
            logger.info("Using cached proposal statistics (avoiding database re-read)")
            return self._last_statistics
        
        # Fallback to database reading if cache not available
        try:
            conn = sqlite3.connect(proposal_db_path)
            cursor = conn.cursor()
            
            # Get metadata
            cursor.execute("SELECT key, value FROM proposal_metadata")
            metadata = dict(cursor.fetchall())
            
            # Get table statistics
            table_stats = {}
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'proposal_%'")
            tables = cursor.fetchall()
            
            for (table_name,) in tables:
                cursor.execute(f"SELECT proposal_action, COUNT(*) FROM {table_name} GROUP BY proposal_action")
                action_counts = dict(cursor.fetchall())
                
                original_table = table_name.replace("proposal_", "")
                table_stats[original_table] = action_counts
            
            conn.close()
            
            return {
                "metadata": metadata,
                "table_statistics": table_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting proposal statistics: {e}")
            return {}
    
    def create_temporary_proposal(self, base_version_info: Dict = None) -> Optional[str]:
        """
        Create a temporary proposal database for preview/comparison.
        
        Args:
            base_version_info: Information about the base version being compared against
            
        Returns:
            Optional[str]: Path to temporary proposal database, or None if failed
        """
        try:
            # Create temporary file
            temp_fd, temp_path = tempfile.mkstemp(suffix=".db", prefix="proposal_")
            os.close(temp_fd)  # Close the file descriptor, we'll use the path
            
            if self.create_proposal_database(temp_path, base_version_info):
                return temp_path
            else:
                os.remove(temp_path)
                return None
                
        except Exception as e:
            logger.error(f"Error creating temporary proposal: {e}")
            return None