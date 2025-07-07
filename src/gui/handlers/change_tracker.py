import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class ChangeType(Enum):
    """Types of changes that can be tracked"""
    AUTOMATIC = "automatic"
    MANUAL = "manual"

class ChangeAction(Enum):
    """Actions that can be performed"""
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"

@dataclass
class ChangeRecord:
    """Represents a single change to the database"""
    id: str
    timestamp: str
    user: str
    change_type: ChangeType
    action: ChangeAction
    table_name: str
    record_id: Any
    field_name: Optional[str]
    old_value: Any
    new_value: Any
    description: str
    context: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['change_type'] = self.change_type.value
        result['action'] = self.action.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ChangeRecord':
        """Create from dictionary"""
        data['change_type'] = ChangeType(data['change_type'])
        data['action'] = ChangeAction(data['action'])
        return cls(**data)

class ChangeTracker:
    """Tracks changes to cloud databases for audit and version control"""
    
    def __init__(self, db_manager, user_auth_service):
        self.db_manager = db_manager
        self.user_auth_service = user_auth_service
        self.changes: List[ChangeRecord] = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def track_change(self, 
                    change_type: ChangeType,
                    action: ChangeAction,
                    table_name: str,
                    record_id: Any,
                    field_name: Optional[str] = None,
                    old_value: Any = None,
                    new_value: Any = None,
                    description: str = "",
                    context: Optional[Dict[str, Any]] = None) -> str:
        """
        Track a change to the database.
        
        Args:
            change_type: Whether this is an automatic or manual change
            action: The type of action (insert, update, delete)
            table_name: Name of the table being changed
            record_id: ID of the record being changed
            field_name: Name of the field being changed (for updates)
            old_value: Previous value
            new_value: New value
            description: Human-readable description of the change
            context: Additional context information
            
        Returns:
            Change ID for reference
        """
        if not self.db_manager.is_cloud_database:
            return ""
            
        change_id = f"{self.session_id}_{len(self.changes):04d}"
        current_user = self.user_auth_service.current_user or "Unknown"
        
        change = ChangeRecord(
            id=change_id,
            timestamp=datetime.now().isoformat(),
            user=current_user,
            change_type=change_type,
            action=action,
            table_name=table_name,
            record_id=record_id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            description=description,
            context=context or {}
        )
        
        self.changes.append(change)
        logger.debug(f"Tracked {change_type.value} change: {description}")
        return change_id
    
    def track_user_flag_change(self, well_number: str, old_status: str, new_status: str) -> str:
        """Track user flag changes specifically"""
        return self.track_change(
            change_type=ChangeType.MANUAL,
            action=ChangeAction.UPDATE,
            table_name="wells",
            record_id=well_number,
            field_name="user_flag",
            old_value=old_status,
            new_value=new_status,
            description=f"User flag changed from '{old_status}' to '{new_status}' for well {well_number}",
            context={
                "well_number": well_number,
                "ui_action": "flag_toggle"
            }
        )
    
    def track_water_level_insert(self, well_number: str, reading_data: Dict, change_type: ChangeType = ChangeType.AUTOMATIC) -> str:
        """Track water level data insertions"""
        return self.track_change(
            change_type=change_type,
            action=ChangeAction.INSERT,
            table_name="water_levels",
            record_id=reading_data.get('id', 'new'),
            field_name=None,
            old_value=None,
            new_value=reading_data,
            description=f"Water level reading added for well {well_number}",
            context={
                "well_number": well_number,
                "reading_date": reading_data.get('date_time'),
                "data_source": reading_data.get('source', 'unknown')
            }
        )
    
    def track_manual_reading_update(self, well_number: str, field_name: str, old_value: Any, new_value: Any) -> str:
        """Track manual updates to water level readings"""
        return self.track_change(
            change_type=ChangeType.MANUAL,
            action=ChangeAction.UPDATE,
            table_name="water_levels",
            record_id=well_number,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            description=f"Manual update to {field_name} for well {well_number}: {old_value} → {new_value}",
            context={
                "well_number": well_number,
                "ui_action": "manual_edit"
            }
        )
    
    def track_water_level_edit(self, well_number: str, records_modified: int, change_description: str, change_type: ChangeType = ChangeType.MANUAL) -> str:
        """Track water level data edits (flag changes, corrections, etc.)"""
        return self.track_change(
            change_type=change_type,
            action=ChangeAction.UPDATE,
            table_name="water_level_readings",
            record_id=well_number,
            field_name="flags_and_values",
            old_value=None,
            new_value=f"{records_modified} records modified",
            description=f"Water level edit for well {well_number}: {change_description}",
            context={
                "well_number": well_number,
                "records_modified": records_modified,
                "ui_action": "water_level_edit",
                "edit_type": change_description
            }
        )
    
    def track_bulk_water_level_delete(self, well_number: str, record_count: int) -> str:
        """Track bulk deletion of water level readings for a well"""
        return self.track_change(
            change_type=ChangeType.MANUAL,
            action=ChangeAction.DELETE,
            table_name="water_level_readings",
            record_id=well_number,
            field_name=None,
            old_value=f"{record_count} records",
            new_value=None,
            description=f"Deleted {record_count} water level readings for well {well_number}",
            context={
                "well_number": well_number,
                "ui_action": "bulk_delete",
                "record_count": record_count
            }
        )
    
    def track_bulk_baro_spike_correction(self, barologger_serials: List[str], record_count: int) -> str:
        """Track bulk spike correction of barologger pressure readings"""
        serials_str = ", ".join(barologger_serials)
        return self.track_change(
            change_type=ChangeType.MANUAL,
            action=ChangeAction.UPDATE,
            table_name="barometric_readings",
            record_id=serials_str,
            field_name="pressure",
            old_value=f"{record_count} spike-affected records",
            new_value=f"{record_count} corrected records",
            description=f"Applied spike correction to {record_count} pressure readings for barologger(s): {serials_str}",
            context={
                "barologger_serials": barologger_serials,
                "ui_action": "bulk_spike_correction",
                "record_count": record_count,
                "correction_type": "spike_detection_algorithm"
            }
        )
    
    def get_changes_summary(self) -> Dict[str, Any]:
        """Get a summary of all tracked changes"""
        if not self.changes:
            return {"total": 0, "automatic": 0, "manual": 0, "by_table": {}, "by_action": {}}
        
        summary = {
            "total": len(self.changes),
            "automatic": len([c for c in self.changes if c.change_type == ChangeType.AUTOMATIC]),
            "manual": len([c for c in self.changes if c.change_type == ChangeType.MANUAL]),
            "by_table": {},
            "by_action": {},
            "session_id": self.session_id,
            "start_time": self.changes[0].timestamp if self.changes else None,
            "end_time": self.changes[-1].timestamp if self.changes else None
        }
        
        for change in self.changes:
            # By table
            if change.table_name not in summary["by_table"]:
                summary["by_table"][change.table_name] = {"automatic": 0, "manual": 0}
            summary["by_table"][change.table_name][change.change_type.value] += 1
            
            # By action
            if change.action.value not in summary["by_action"]:
                summary["by_action"][change.action.value] = {"automatic": 0, "manual": 0}
            summary["by_action"][change.action.value][change.change_type.value] += 1
        
        return summary
    
    def get_changes_for_save(self) -> Dict[str, Any]:
        """Get changes in format suitable for saving to cloud"""
        return {
            "session_id": self.session_id,
            "summary": self.get_changes_summary(),
            "detailed_changes": [change.to_dict() for change in self.changes],
            "generated_at": datetime.now().isoformat()
        }
    
    def clear_changes(self):
        """Clear all tracked changes (call after successful save)"""
        self.changes.clear()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info("Change tracking cleared - new session started")
    
    def export_changes_to_file(self, file_path: str):
        """Export changes to a JSON file"""
        try:
            changes_data = self.get_changes_for_save()
            with open(file_path, 'w') as f:
                json.dump(changes_data, f, indent=2)
            logger.info(f"Changes exported to {file_path}")
        except Exception as e:
            logger.error(f"Error exporting changes: {e}")
    
    def get_manual_changes_description(self) -> str:
        """Generate a description of manual changes for the save dialog"""
        manual_changes = [c for c in self.changes if c.change_type == ChangeType.MANUAL]
        
        if not manual_changes:
            return "No manual changes made"
        
        descriptions = []
        for change in manual_changes:
            if change.action == ChangeAction.UPDATE and change.field_name == "user_flag":
                descriptions.append(f"Updated user flag for well {change.record_id}")
            else:
                descriptions.append(change.description)
        
        return "; ".join(descriptions[:5])  # Limit to first 5 changes
    
    def extract_proposal_data(self) -> Dict[str, Any]:
        """
        Extract proposal data for creating reduced database proposals.
        
        Returns:
            Dictionary containing organized change data for proposal creation
        """
        if not self.changes:
            return {"changes": {}, "statistics": {"total_records_affected": 0}}
        
        # Organize changes by table and action
        changes_by_table = {}
        affected_records = set()
        
        for change in self.changes:
            table = change.table_name
            if table not in changes_by_table:
                changes_by_table[table] = {
                    "added": [],
                    "modified": [],
                    "deleted": []
                }
            
            # Track affected records for statistics
            affected_records.add(f"{table}:{change.record_id}")
            
            change_data = {
                "id": change.id,
                "timestamp": change.timestamp,
                "user": change.user,
                "record_id": change.record_id,
                "field_name": change.field_name,
                "old_value": change.old_value,
                "new_value": change.new_value,
                "description": change.description,
                "context": change.context
            }
            
            if change.action == ChangeAction.INSERT:
                changes_by_table[table]["added"].append(change_data)
            elif change.action == ChangeAction.UPDATE:
                changes_by_table[table]["modified"].append(change_data)
            elif change.action == ChangeAction.DELETE:
                changes_by_table[table]["deleted"].append(change_data)
        
        # Generate statistics
        statistics = {
            "total_records_affected": len(affected_records),
            "total_changes": len(self.changes),
            "tables_modified": list(changes_by_table.keys()),
            "session_id": self.session_id,
            "change_types": {
                "automatic": len([c for c in self.changes if c.change_type == ChangeType.AUTOMATIC]),
                "manual": len([c for c in self.changes if c.change_type == ChangeType.MANUAL])
            },
            "actions": {
                "inserts": len([c for c in self.changes if c.action == ChangeAction.INSERT]),
                "updates": len([c for c in self.changes if c.action == ChangeAction.UPDATE]),
                "deletes": len([c for c in self.changes if c.action == ChangeAction.DELETE])
            }
        }
        
        return {
            "changes": changes_by_table,
            "statistics": statistics
        }
    
    def get_affected_record_ids(self, table_name: str) -> Dict[str, List]:
        """
        Get lists of affected record IDs for a specific table.
        Used for creating reduced databases that only contain changed records.
        
        Args:
            table_name: Name of the table to analyze
            
        Returns:
            Dictionary with lists of record IDs by action type
        """
        affected_ids = {
            "added": [],
            "modified": [],
            "deleted": []
        }
        
        for change in self.changes:
            if change.table_name == table_name:
                record_id = change.record_id
                
                if change.action == ChangeAction.INSERT and record_id not in affected_ids["added"]:
                    affected_ids["added"].append(record_id)
                elif change.action == ChangeAction.UPDATE and record_id not in affected_ids["modified"]:
                    affected_ids["modified"].append(record_id)
                elif change.action == ChangeAction.DELETE and record_id not in affected_ids["deleted"]:
                    affected_ids["deleted"].append(record_id)
        
        return affected_ids