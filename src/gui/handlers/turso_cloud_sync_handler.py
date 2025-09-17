# -*- coding: utf-8 -*-
"""
Turso Cloud Sync Handler - Syncs data from Turso tables to local cloud database tables

This handler pulls data from Turso (wells, loggers) and updates the corresponding
local cloud database tables (wells, transducers, transducers_locations, barologgers, barologgers_locations)
"""

import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QProgressDialog

logger = logging.getLogger(__name__)


class TursoCloudSyncWorker(QThread):
    """Worker thread for syncing Turso data to local cloud database"""

    progress_updated = pyqtSignal(str)  # Status message
    sync_completed = pyqtSignal(bool, str, dict)  # Success, message, stats

    def __init__(self, db_manager, settings_handler, project_name, sync_types):
        super().__init__()
        self.db_manager = db_manager
        self.settings_handler = settings_handler
        self.project_name = project_name
        self.sync_types = sync_types  # ['wells', 'loggers'] or subset
        self.stats = {
            'wells_synced': 0,
            'transducers_synced': 0,
            'transducer_locations_synced': 0,
            'barologgers_synced': 0,
            'barologger_locations_synced': 0,
            'errors': []
        }

    def run(self):
        """Main sync process"""
        try:
            self.progress_updated.emit("Initializing Turso connection...")

            # Get Turso credentials
            turso_url = self.settings_handler.get_setting("turso_loggers_url", "")
            turso_token = self.settings_handler.get_setting("turso_loggers_token", "")

            if not turso_url or not turso_token:
                self.sync_completed.emit(False, "Turso credentials not configured in settings", self.stats)
                return

            # Convert libsql URL to HTTP API URL
            api_url = turso_url.replace('libsql://', 'https://').replace('.turso.io', '.turso.io/v2/pipeline')

            # Sync wells if requested
            if 'wells' in self.sync_types:
                self.progress_updated.emit("Syncing wells from Turso...")
                success = self._sync_wells_data(api_url, turso_token)
                if not success:
                    self.sync_completed.emit(False, "Failed to sync wells data", self.stats)
                    return

            # Sync loggers if requested
            if 'loggers' in self.sync_types:
                self.progress_updated.emit("Syncing loggers from Turso...")
                success = self._sync_loggers_data(api_url, turso_token)
                if not success:
                    self.sync_completed.emit(False, "Failed to sync loggers data", self.stats)
                    return

            self.progress_updated.emit("Sync completed successfully!")
            self.sync_completed.emit(True, "Successfully synced data from Turso", self.stats)

        except Exception as e:
            error_msg = f"Error during Turso sync: {str(e)}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            self.sync_completed.emit(False, error_msg, self.stats)

    def _sync_wells_data(self, api_url: str, token: str) -> bool:
        """Sync wells data from Turso to local database"""
        try:
            # Query wells from Turso filtered by current project
            # Using actual field names from schema analysis
            query = f"""
                SELECT well_number, well_name, project_name, latitude, longitude, elevation,
                       well_depth, installation_date, well_type, well_status, location_notes
                FROM wells
                WHERE project_name = '{self.project_name}'
            """

            turso_wells = self._execute_turso_query(api_url, token, query)
            if turso_wells is None:
                return False

            # Clear existing wells for this project and insert new data
            with self.db_manager.get_db_connection() as conn:
                cursor = conn.cursor()

                # Delete existing wells for this project (filter by project in well_number pattern)
                cursor.execute("DELETE FROM wells WHERE well_number IN (SELECT well_number FROM wells WHERE well_number LIKE ?)", (f"%{self.project_name}%",))

                # Insert wells from Turso using actual local database schema
                for well in turso_wells:
                    cursor.execute("""
                        INSERT INTO wells (well_number, latitude, longitude, top_of_casing,
                                         parking_instructions, access_requirements, safety_notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        well.get('well_number'),
                        well.get('latitude'),
                        well.get('longitude'),
                        well.get('elevation'),  # Map elevation to top_of_casing
                        f"Project: {well.get('project_name', '')}",  # Store project in parking_instructions
                        well.get('well_name', ''),  # Store well_name in access_requirements
                        well.get('location_notes', '')  # Store notes in safety_notes
                    ))

                conn.commit()
                self.stats['wells_synced'] = len(turso_wells)
                logger.info(f"Synced {len(turso_wells)} wells from Turso for project {self.project_name}")

            return True

        except Exception as e:
            error_msg = f"Error syncing wells data: {str(e)}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            return False

    def _sync_loggers_data(self, api_url: str, token: str) -> bool:
        """Sync loggers data from Turso to local transducers and barologgers tables"""
        try:
            # Query loggers from Turso filtered by current project
            # Using actual field names from schema analysis
            query = f"""
                SELECT serial_number, instrument_type, model, project, location,
                       start_time, end_time, latitude, longitude, elevation,
                       deployment_depth, deployed_by, deployment_notes, retrieval_notes,
                       equipment_status, calibration_date, last_maintenance, active
                FROM loggers
                WHERE project = '{self.project_name}' AND active = 1
            """

            turso_loggers = self._execute_turso_query(api_url, token, query)
            if turso_loggers is None:
                return False

            # Separate loggers by type using correct field name
            transducers = [l for l in turso_loggers if l.get('instrument_type') == 'transducer']
            barologgers = [l for l in turso_loggers if l.get('instrument_type') == 'barologger']

            with self.db_manager.get_db_connection() as conn:
                cursor = conn.cursor()

                # Sync transducers
                if transducers:
                    success = self._sync_transducers(cursor, transducers)
                    if not success:
                        return False

                # Sync barologgers
                if barologgers:
                    success = self._sync_barologgers(cursor, barologgers)
                    if not success:
                        return False

                conn.commit()

            return True

        except Exception as e:
            error_msg = f"Error syncing loggers data: {str(e)}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            return False

    def _sync_transducers(self, cursor, transducers: List[Dict]) -> bool:
        """Sync transducers and transducer_locations tables"""
        try:
            # Clear existing transducers for this project (filter by project pattern in locations)
            cursor.execute("""
                DELETE FROM transducers
                WHERE serial_number IN (
                    SELECT DISTINCT transducer_serial
                    FROM transducer_locations
                    WHERE well_number IN (
                        SELECT well_number FROM wells WHERE project_name = ?
                    )
                )
            """, (self.project_name,))

            cursor.execute("""
                DELETE FROM transducer_locations
                WHERE well_number IN (
                    SELECT well_number FROM wells WHERE project_name = ?
                )
            """, (self.project_name,))

            for transducer in transducers:
                serial_number = transducer.get('serial_number')

                # Insert into transducers table (handle NULL model)
                model = transducer.get('model') or 'Unknown'

                cursor.execute("""
                    INSERT OR REPLACE INTO transducers (serial_number, model, calibration_date, last_maintenance)
                    VALUES (?, ?, ?, ?)
                """, (
                    serial_number,
                    model,
                    transducer.get('calibration_date'),
                    transducer.get('last_maintenance')
                ))

                # Insert into transducer_locations table using correct field names
                cursor.execute("""
                    INSERT INTO transducer_locations (
                        transducer_serial, well_number, start_date, end_date,
                        latitude, longitude, elevation, deployment_depth,
                        deployed_by, deployment_notes, retrieval_notes, equipment_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    serial_number,
                    transducer.get('location'),  # Using 'location' field from Turso
                    transducer.get('start_time'),  # Using 'start_time' not 'deployment_date'
                    transducer.get('end_time'),    # Using 'end_time' not 'retrieval_date'
                    transducer.get('latitude'),
                    transducer.get('longitude'),
                    transducer.get('elevation'),
                    transducer.get('deployment_depth'),
                    transducer.get('deployed_by'),
                    transducer.get('deployment_notes'),
                    transducer.get('retrieval_notes'),
                    transducer.get('equipment_status', 'working')
                ))

            self.stats['transducers_synced'] = len(transducers)
            self.stats['transducer_locations_synced'] = len(transducers)
            logger.info(f"Synced {len(transducers)} transducers from Turso for project {self.project_name}")

            return True

        except Exception as e:
            error_msg = f"Error syncing transducers: {str(e)}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            return False

    def _sync_barologgers(self, cursor, barologgers: List[Dict]) -> bool:
        """Sync barologgers and barologger_locations tables"""
        try:
            # Clear existing barologgers for this project
            cursor.execute("""
                DELETE FROM barologgers
                WHERE serial_number IN (
                    SELECT DISTINCT barologger_serial
                    FROM barologger_locations
                    WHERE location_name LIKE ?
                )
            """, (f"%{self.project_name}%",))

            cursor.execute("""
                DELETE FROM barologger_locations
                WHERE location_name LIKE ?
            """, (f"%{self.project_name}%",))

            for barologger in barologgers:
                serial_number = barologger.get('serial_number')

                # Insert into barologgers table (handle NULL model)
                model = barologger.get('model') or 'Unknown'

                cursor.execute("""
                    INSERT OR REPLACE INTO barologgers (serial_number, model, calibration_date, last_maintenance)
                    VALUES (?, ?, ?, ?)
                """, (
                    serial_number,
                    model,
                    barologger.get('calibration_date'),
                    barologger.get('last_maintenance')
                ))

                # Insert into barologger_locations table using correct field names
                cursor.execute("""
                    INSERT INTO barologger_locations (
                        barologger_serial, location_name, start_date, end_date,
                        latitude, longitude, elevation, deployed_by,
                        deployment_notes, retrieval_notes, equipment_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    serial_number,
                    barologger.get('location'),     # Using 'location' field from Turso
                    barologger.get('start_time'),   # Using 'start_time' not 'deployment_date'
                    barologger.get('end_time'),     # Using 'end_time' not 'retrieval_date'
                    barologger.get('latitude'),
                    barologger.get('longitude'),
                    barologger.get('elevation'),
                    barologger.get('deployed_by'),
                    barologger.get('deployment_notes'),
                    barologger.get('retrieval_notes'),
                    barologger.get('equipment_status', 'working')
                ))

            self.stats['barologgers_synced'] = len(barologgers)
            self.stats['barologger_locations_synced'] = len(barologgers)
            logger.info(f"Synced {len(barologgers)} barologgers from Turso for project {self.project_name}")

            return True

        except Exception as e:
            error_msg = f"Error syncing barologgers: {str(e)}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            return False

    def _execute_turso_query(self, api_url: str, token: str, query: str) -> Optional[List[Dict]]:
        """Execute a query against Turso and return results"""
        try:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }

            payload = {
                "requests": [
                    {
                        "type": "execute",
                        "stmt": {
                            "sql": query
                        }
                    }
                ]
            }

            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()

            if 'results' not in result or not result['results']:
                logger.warning("No results returned from Turso query")
                return []

            first_result = result['results'][0]
            if first_result.get('type') != 'ok':
                error_msg = first_result.get('error', 'Unknown error')
                logger.error(f"Turso query error: {error_msg}")
                return None

            # Extract rows and columns from new API format
            response_data = first_result.get('response', {})
            result_data = response_data.get('result', {})
            columns = [col.get('name', '') for col in result_data.get('cols', [])]
            rows = result_data.get('rows', [])

            # Convert to list of dictionaries handling new cell format
            records = []
            for row in rows:
                record = {}
                for i, cell in enumerate(row):
                    if i < len(columns):
                        # Handle new Turso API format where cells have type and value
                        if isinstance(cell, dict):
                            if cell.get('type') == 'null':
                                value = None
                            else:
                                value = cell.get('value')
                        else:
                            value = cell
                        record[columns[i]] = value
                records.append(record)

            logger.info(f"Successfully retrieved {len(records)} records from Turso")
            return records

        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error querying Turso: {e}")
            return None
        except Exception as e:
            logger.error(f"Error querying Turso: {e}")
            return None


class TursoCloudSyncHandler:
    """Main handler for Turso cloud sync operations"""

    def __init__(self, db_manager, settings_handler):
        self.db_manager = db_manager
        self.settings_handler = settings_handler
        self.worker = None

    def sync_project_data(self, project_name: str, sync_types: List[str], parent_widget=None) -> bool:
        """
        Sync data from Turso for a specific project

        Args:
            project_name: Name of the project to sync
            sync_types: List of data types to sync ['wells', 'loggers']
            parent_widget: Parent widget for progress dialog

        Returns:
            True if sync was successful, False otherwise
        """
        try:
            # Validate inputs
            if not project_name:
                QMessageBox.warning(parent_widget, "Error", "Project name is required for sync")
                return False

            if not sync_types:
                QMessageBox.warning(parent_widget, "Error", "Please select data types to sync")
                return False

            # Check if database is available
            if not self.db_manager.current_db:
                QMessageBox.warning(parent_widget, "Error", "No database is currently open")
                return False

            # Check Turso configuration
            turso_url = self.settings_handler.get_setting("turso_loggers_url", "")
            turso_token = self.settings_handler.get_setting("turso_loggers_token", "")

            if not turso_url or not turso_token:
                QMessageBox.warning(
                    parent_widget,
                    "Configuration Error",
                    "Turso credentials not configured.\n\n"
                    "Please configure 'turso_loggers_url' and 'turso_loggers_token' in settings."
                )
                return False

            # Show progress dialog
            progress_dialog = QProgressDialog("Initializing Turso sync...", "Cancel", 0, 0, parent_widget)
            progress_dialog.setWindowTitle("Syncing from Turso")
            progress_dialog.setModal(True)
            progress_dialog.show()

            # Create and start worker thread
            self.worker = TursoCloudSyncWorker(self.db_manager, self.settings_handler, project_name, sync_types)
            self.worker.progress_updated.connect(progress_dialog.setLabelText)
            self.worker.sync_completed.connect(lambda success, msg, stats: self._on_sync_completed(success, msg, stats, progress_dialog, parent_widget))

            # Handle cancel button
            progress_dialog.canceled.connect(self._cancel_sync)

            self.worker.start()

            return True

        except Exception as e:
            error_msg = f"Error starting Turso sync: {str(e)}"
            logger.error(error_msg)
            QMessageBox.critical(parent_widget, "Sync Error", error_msg)
            return False

    def _on_sync_completed(self, success: bool, message: str, stats: Dict, progress_dialog, parent_widget):
        """Handle sync completion"""
        try:
            progress_dialog.close()

            if success:
                # Show success message with stats
                stats_text = []
                if stats.get('wells_synced', 0) > 0:
                    stats_text.append(f"Wells: {stats['wells_synced']}")
                if stats.get('transducers_synced', 0) > 0:
                    stats_text.append(f"Transducers: {stats['transducers_synced']}")
                if stats.get('barologgers_synced', 0) > 0:
                    stats_text.append(f"Barologgers: {stats['barologgers_synced']}")

                stats_summary = ", ".join(stats_text) if stats_text else "No data"

                QMessageBox.information(
                    parent_widget,
                    "Sync Successful",
                    f"✅ Turso sync completed successfully!\n\n"
                    f"Synced data: {stats_summary}\n\n"
                    f"Tables will refresh automatically."
                )
            else:
                error_details = ""
                if stats.get('errors'):
                    error_details = f"\n\nDetails:\n" + "\n".join(stats['errors'][:3])  # Show first 3 errors

                QMessageBox.critical(
                    parent_widget,
                    "Sync Failed",
                    f"❌ {message}{error_details}"
                )

            # Clean up worker
            if self.worker:
                self.worker.deleteLater()
                self.worker = None

        except Exception as e:
            logger.error(f"Error handling sync completion: {e}")

    def _cancel_sync(self):
        """Cancel the sync operation"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            logger.info("Turso sync cancelled by user")

    def is_configured(self) -> bool:
        """Check if Turso is properly configured"""
        turso_url = self.settings_handler.get_setting("turso_loggers_url", "")
        turso_token = self.settings_handler.get_setting("turso_loggers_token", "")
        return bool(turso_url and turso_token)