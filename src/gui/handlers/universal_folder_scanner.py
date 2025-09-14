#!/usr/bin/env python3
"""
Universal XLE Folder Scanner and Integrator

A comprehensive system for scanning any folder for XLE files and integrating
unique files into the organized collection. Designed for integration with
SMOO cloud storage system.
"""

import os
import sys
import json
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import re
from collections import defaultdict
import hashlib

# Import vented transducer utilities
try:
    from src.utils.vented_transducer_utils import is_vented_transducer, should_apply_compensation
except ImportError:
    try:
        # Fallback for relative import
        from ...utils.vented_transducer_utils import is_vented_transducer, should_apply_compensation
    except ImportError:
        # Final fallback - define dummy functions
        def is_vented_transducer(serial_number):
            return False
        def should_apply_compensation(serial_number):
            return True

# Handle imports that work both in package context and standalone
try:
    # Try relative imports first (when used as part of the package)
    from config.smoo_paths import get_smoo_path, is_smoo_available
    from .solinst_reader import SolinstReader
except ImportError:
    # Fall back to direct file imports (when used standalone or from different contexts)
    import sys
    from pathlib import Path
    import importlib.util
    
    # Get the current file's directory
    current_dir = Path(__file__).resolve().parent
    src_dir = current_dir.parent.parent  # Go up from handlers -> gui -> src
    
    # Import smoo_paths directly
    smoo_paths_file = src_dir / "config" / "smoo_paths.py"
    spec = importlib.util.spec_from_file_location("smoo_paths", smoo_paths_file)
    smoo_module = importlib.util.module_from_spec(spec)
    sys.modules["smoo_paths"] = smoo_module
    spec.loader.exec_module(smoo_module)
    get_smoo_path = smoo_module.get_smoo_path
    is_smoo_available = smoo_module.is_smoo_available
    
    # Import SolinstReader directly  
    solinst_file = current_dir / "solinst_reader.py"
    spec = importlib.util.spec_from_file_location("solinst_reader", solinst_file)
    solinst_module = importlib.util.module_from_spec(spec)
    sys.modules["solinst_reader"] = solinst_module
    spec.loader.exec_module(solinst_module)
    SolinstReader = solinst_module.SolinstReader


class FolderScanDatabase:
    """Database to track scanned folders and processed files"""
    
    def __init__(self, db_path: str = "folder_scan_tracking.db"):
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """Initialize the tracking database"""
        # Ensure parent directory exists before creating database
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table to track scanned folders
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scanned_folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_path TEXT UNIQUE,
                last_scan_date TEXT,
                files_found INTEGER,
                unique_files_added INTEGER,
                scan_metadata TEXT
            )
        ''')
        
        # Table to track processed files with their signatures
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_signature TEXT UNIQUE,
                original_path TEXT,
                filename TEXT,
                serial_number TEXT,
                file_size INTEGER,
                processing_date TEXT,
                final_location TEXT,
                status TEXT,
                cae_number TEXT,
                project_name TEXT,
                instrument_type TEXT
            )
        ''')
        
        # Add new columns to existing databases (migration)
        try:
            cursor.execute('ALTER TABLE processed_files ADD COLUMN cae_number TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
            
        try:
            cursor.execute('ALTER TABLE processed_files ADD COLUMN project_name TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
            
        try:
            cursor.execute('ALTER TABLE processed_files ADD COLUMN instrument_type TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        conn.commit()
        conn.close()
    
    def record_folder_scan(self, folder_path: str, files_found: int, unique_added: int, metadata: Dict):
        """Record a completed folder scan with retry logic"""
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            conn = None
            try:
                conn = sqlite3.connect(self.db_path, timeout=10.0)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO scanned_folders 
                    (folder_path, last_scan_date, files_found, unique_files_added, scan_metadata)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    str(folder_path),
                    datetime.now().isoformat(),
                    files_found,
                    unique_added,
                    json.dumps(metadata, default=str)
                ))
                
                conn.commit()
                return  # Success
                
            except sqlite3.OperationalError as e:
                if "readonly" in str(e).lower() or "locked" in str(e).lower():
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        print(f"   ❌ Failed to record scan after {max_retries} attempts: {e}")
                        raise
                else:
                    raise
            except Exception as e:
                print(f"   ❌ Error recording scan: {e}")
                raise
            finally:
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
    
    def record_processed_file(self, file_sig: str, file_path: str, filename: str, 
                            serial: str, size: int, final_location: str, status: str,
                            cae_number: str = None, project_name: str = None, 
                            instrument_type: str = None):
        """Record a processed file with optional enhanced metadata"""
        max_retries = 3
        retry_delay = 0.1  # 100ms delay between retries
        
        for attempt in range(max_retries):
            conn = None
            try:
                conn = sqlite3.connect(self.db_path, timeout=10.0)  # 10 second timeout
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR IGNORE INTO processed_files 
                    (file_signature, original_path, filename, serial_number, file_size, 
                     processing_date, final_location, status, cae_number, project_name, instrument_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    file_sig, str(file_path), filename, serial, size,
                    datetime.now().isoformat(), final_location, status,
                    cae_number, project_name, instrument_type
                ))
                
                conn.commit()
                return  # Success - exit retry loop
                
            except sqlite3.OperationalError as e:
                if "readonly" in str(e).lower() or "locked" in str(e).lower():
                    print(f"   ⚠️  Database locked on attempt {attempt + 1}/{max_retries}, retrying...")
                    if attempt < max_retries - 1:  # Don't sleep on last attempt
                        import time
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        print(f"   ❌ Database operation failed after {max_retries} attempts: {e}")
                        raise
                else:
                    print(f"   ❌ Database error: {e}")
                    raise
            except Exception as e:
                print(f"   ❌ Unexpected database error: {e}")
                raise
            finally:
                if conn:
                    try:
                        conn.close()
                    except:
                        pass  # Ignore errors when closing
    
    def get_processed_signatures(self) -> Set[str]:
        """Get all processed file signatures"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT file_signature FROM processed_files')
        signatures = {row[0] for row in cursor.fetchall()}
        
        conn.close()
        return signatures
    
    def get_unmatched_files(self) -> List[Dict]:
        """Get all files currently marked as unmatched for potential upgrading"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT file_signature, original_path, filename, serial_number, 
                   final_location, processing_date, cae_number, project_name
            FROM processed_files 
            WHERE status = 'unmatched'
            ORDER BY processing_date DESC
        ''')
        
        unmatched_files = []
        for row in cursor.fetchall():
            unmatched_files.append({
                'file_signature': row[0],
                'original_path': row[1], 
                'filename': row[2],
                'serial_number': row[3],
                'final_location': row[4],
                'processing_date': row[5],
                'cae_number': row[6],
                'project_name': row[7]
            })
        
        conn.close()
        return unmatched_files
    
    def upgrade_file_status(self, file_signature: str, new_status: str, 
                           new_location: str, cae_number: str = None, project_name: str = None):
        """Upgrade a file's status (e.g., unmatched -> corrected) and update location"""
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            conn = None
            try:
                conn = sqlite3.connect(self.db_path, timeout=10.0)
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE processed_files 
                    SET status = ?, final_location = ?, cae_number = ?, project_name = ?,
                        processing_date = ?
                    WHERE file_signature = ?
                ''', (new_status, new_location, cae_number, project_name, 
                      datetime.now().isoformat(), file_signature))
                
                conn.commit()
                return cursor.rowcount > 0  # Return True if row was updated
                
            except sqlite3.OperationalError as e:
                if "readonly" in str(e).lower() or "locked" in str(e).lower():
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        print(f"   ❌ Failed to upgrade file status after {max_retries} attempts: {e}")
                        raise
                else:
                    raise
            finally:
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
        
        return False
    
    def get_scan_history(self) -> List[Dict]:
        """Get folder scan history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT folder_path, last_scan_date, files_found, unique_files_added
            FROM scanned_folders 
            ORDER BY last_scan_date DESC
        ''')
        
        history = [
            {
                'folder_path': row[0],
                'last_scan_date': row[1], 
                'files_found': row[2],
                'unique_files_added': row[3]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return history


class UniversalXLEScanner:
    """Universal XLE file scanner and processor for any folder"""
    
    def __init__(self, corrected_dir: str, unmatched_dir: str, databases_dir: str):
        self.corrected_dir = Path(corrected_dir)
        self.unmatched_dir = Path(unmatched_dir) 
        self.databases_dir = Path(databases_dir)
        self.reader = SolinstReader()
        
        # Ensure directories exist during initialization
        self.corrected_dir.parent.mkdir(parents=True, exist_ok=True)  # Create universal_xle_files
        self.corrected_dir.mkdir(parents=True, exist_ok=True)         # Create corrected
        self.unmatched_dir.mkdir(parents=True, exist_ok=True)         # Create unmatched
        
        # Create tracking database in the same directory as corrected files
        db_path = Path(corrected_dir).parent / "folder_scan_tracking.db"
        self.db = FolderScanDatabase(str(db_path))
        
        # Load databases dynamically from SMOO Projects structure
        self.databases = self._discover_project_databases()
        
        # Combined data from all databases
        self.all_wells_data = {}
        self.all_transducer_locations = []
        
        # Track failed operations for reporting
        self.failed_operations = []
        
        # Processing state
        self.new_files = []
        self.duplicate_files = []
        self.processed_files = []
        self.stats = defaultdict(int)
        
        print(f"🔍 Universal XLE Scanner initialized")
        print(f"📁 Corrected: {self.corrected_dir}")
        print(f"📁 Unmatched: {self.unmatched_dir}")
        print(f"🗄️ Database tracking: {self.db.db_path}")
        print(f"🗃️ Found {len(self.databases)} project databases: {list(self.databases.keys())}")
    
    def _discover_project_databases(self) -> Dict[str, Path]:
        """Discover project databases using SMOO Projects structure (same as main window)"""
        databases = {}
        
        try:
            if is_smoo_available():
                # Use SMOO paths
                smoo_base = get_smoo_path("base")
                projects_path = Path(smoo_base) / "Projects"
            else:
                # Use local fallback - look relative to databases_dir for Projects folder
                projects_path = self.databases_dir.parent / "Projects"
            
            if not projects_path.exists():
                print(f"   ⚠️  Projects folder not found: {projects_path}")
                return databases
            
            # List all directories in projects folder (same logic as SharedDriveDbHandler.list_projects)
            for item in projects_path.iterdir():
                if not item.is_dir():
                    continue
                    
                # Check if project has a DATABASES folder
                databases_folder = item / "DATABASES"
                if not databases_folder.exists():
                    continue
                    
                # Look for database file named {project_name}.db
                db_file_path = databases_folder / f"{item.name}.db"
                if db_file_path.exists():
                    databases[item.name] = db_file_path
                    print(f"   ✅ Found: {item.name} -> {db_file_path}")
                    
        except Exception as e:
            print(f"   ❌ Error discovering databases: {e}")
            # Fallback to empty dict - scanner will still work for duplicate detection
            
        return databases
    
    def create_file_signature(self, file_path: Path) -> str:
        """Create unique file signature using path + size + partial content hash"""
        try:
            size = file_path.stat().st_size
            name = file_path.stem.lower()
            
            # Add partial content hash for more uniqueness
            with open(file_path, 'rb') as f:
                # Read first 1KB and last 1KB for hash
                content_start = f.read(1024)
                f.seek(max(0, size - 1024))
                content_end = f.read(1024)
                
            content_hash = hashlib.md5(content_start + content_end).hexdigest()[:8]
            return f"{name}_{size}_{content_hash}"
        except:
            return f"{file_path.name}_{file_path.stat().st_size if file_path.exists() else 0}_error"
    
    def format_folder_name(self, name: str) -> str:
        """Format a name to be safe for use as a folder name"""
        if not name or name.lower() in ['unknown', 'n/a', 'none']:
            return 'UNKNOWN'
        
        # Clean the name for filesystem safety
        cleaned = str(name).strip()
        # Replace problematic characters
        replacements = {
            ':': '-', '/': '_', '\\': '_', '|': '_', 
            '?': '_', '*': '_', '<': '_', '>': '_', 
            '"': '_', "'": '_', ' ': '_', '.': '_',
            '#': ''  # Remove hash symbols completely
        }
        
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        
        # Remove multiple underscores and trailing/leading underscores
        while '__' in cleaned:
            cleaned = cleaned.replace('__', '_')
        cleaned = cleaned.strip('_')
        
        # Ensure it's not empty after cleaning
        return cleaned if cleaned else 'UNKNOWN'
    
    def retry_operation(self, operation, *args, max_retries=3, delay=1.0, operation_name="Operation", **kwargs):
        """
        Retry an operation with exponential backoff for network/permission errors
        
        Args:
            operation: Function to retry
            *args: Arguments for the operation
            max_retries: Maximum number of retry attempts
            delay: Initial delay between retries (seconds)
            operation_name: Name for logging
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Result of operation or None if all retries failed
        """
        import time
        
        for attempt in range(max_retries + 1):
            try:
                result = operation(*args, **kwargs)
                if attempt > 0:
                    print(f"      ✅ {operation_name} succeeded on retry {attempt}")
                return result
                
            except (OSError, IOError, PermissionError) as e:
                if attempt == max_retries:
                    print(f"      ❌ {operation_name} failed after {max_retries} retries: {str(e)[:100]}")
                    self.failed_operations.append({
                        'operation': operation_name,
                        'args': str(args)[:100],
                        'error': str(e)[:200],
                        'final_attempt': True
                    })
                    return None
                else:
                    wait_time = delay * (2 ** attempt)  # Exponential backoff
                    print(f"      ⚠️  {operation_name} failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)[:100]}")
                    print(f"      ⏳ Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                    
            except Exception as e:
                # For non-network errors, don't retry
                print(f"      ❌ {operation_name} failed with non-retryable error: {str(e)[:100]}")
                self.failed_operations.append({
                    'operation': operation_name,
                    'args': str(args)[:100], 
                    'error': str(e)[:200],
                    'final_attempt': True,
                    'non_retryable': True
                })
                return None
        
        return None
    
    def generate_failure_report(self) -> str:
        """Generate a summary report of failed operations"""
        if not self.failed_operations:
            return "✅ No failed operations"
        
        report = f"\n⚠️  OPERATION FAILURES SUMMARY ({len(self.failed_operations)} total)\n"
        report += "=" * 60 + "\n"
        
        # Group by operation type
        operation_groups = {}
        for failure in self.failed_operations:
            op_type = failure['operation']
            if op_type not in operation_groups:
                operation_groups[op_type] = []
            operation_groups[op_type].append(failure)
        
        for op_type, failures in operation_groups.items():
            report += f"\n📋 {op_type}: {len(failures)} failures\n"
            for i, failure in enumerate(failures[:3], 1):  # Show first 3 of each type
                report += f"   {i}. {failure['error'][:100]}\n"
                if failure.get('non_retryable'):
                    report += f"      💀 Non-retryable error\n"
                else:
                    report += f"      🔄 Retried but failed\n"
            
            if len(failures) > 3:
                report += f"   ... and {len(failures) - 3} more similar failures\n"
        
        report += f"\n💡 Suggestion: Check network connectivity and file permissions\n"
        report += f"   Failed operations have been logged and processing continued\n"
        
        return report
    
    def validate_date_range(self, file_first_timestamp, deployment_start, deployment_end):
        """
        Validate if file's first timestamp falls within transducer deployment date range
        
        Args:
            file_first_timestamp: First timestamp from XLE data (datetime or string)
            deployment_start: Start date from database (string, should not be None)
            deployment_end: End date from database (string or None - if None, assume current deployment)
            
        Returns:
            bool: True if file timestamp is within deployment range
        """
        from datetime import datetime, date
        
        try:
            # Convert file timestamp to date
            if isinstance(file_first_timestamp, str):
                # Handle various date string formats
                try:
                    file_date = datetime.fromisoformat(file_first_timestamp).date()
                except:
                    try:
                        file_date = datetime.strptime(file_first_timestamp, '%Y-%m-%d %H:%M:%S').date()
                    except:
                        file_date = datetime.strptime(file_first_timestamp, '%Y-%m-%d').date()
            elif hasattr(file_first_timestamp, 'date'):
                file_date = file_first_timestamp.date()
            else:
                print(f"      ⚠️  Invalid file timestamp format: {file_first_timestamp}")
                return False
            
            # Parse deployment start date (should not be None)
            if not deployment_start:
                print(f"      ⚠️  Missing deployment start date - cannot validate")
                return False
            
            # Handle both date and datetime formats from database
            try:
                # Try datetime format first (2025-01-01T18:30:00 or 2025-01-01 18:30:00)
                if 'T' in deployment_start:
                    start_date = datetime.fromisoformat(deployment_start).date()
                elif ' ' in deployment_start and ':' in deployment_start:
                    start_date = datetime.strptime(deployment_start, '%Y-%m-%d %H:%M:%S').date()
                else:
                    # Just date format (2025-01-01)
                    start_date = datetime.strptime(deployment_start, '%Y-%m-%d').date()
            except Exception as e:
                print(f"      ⚠️  Could not parse start date '{deployment_start}': {e}")
                return True  # Safer to allow processing if we can't parse
            
            # Parse deployment end date (None means current deployment)
            if deployment_end:
                try:
                    # Handle both date and datetime formats from database
                    if 'T' in deployment_end:
                        end_date = datetime.fromisoformat(deployment_end).date()
                    elif ' ' in deployment_end and ':' in deployment_end:
                        end_date = datetime.strptime(deployment_end, '%Y-%m-%d %H:%M:%S').date()
                    else:
                        # Just date format (2025-01-01)
                        end_date = datetime.strptime(deployment_end, '%Y-%m-%d').date()
                except Exception as e:
                    print(f"      ⚠️  Could not parse end date '{deployment_end}': {e}")
                    end_date = date.today()  # Safer fallback
            else:
                # No end date = current deployment, use today
                end_date = date.today()
            
            # Check if file date is within deployment range
            is_valid = start_date <= file_date <= end_date
            
            if not is_valid:
                print(f"      📅 Date mismatch: File={file_date}, Deployment={start_date} to {end_date}")
            
            return is_valid
            
        except Exception as e:
            print(f"      ⚠️  Date validation error: {e}")
            # If we can't validate dates, assume it's valid (safer for processing)
            return True
    
    def find_matching_deployments(self, serial_number, file_first_timestamp):
        """
        Find all deployment records that match serial number and date range
        
        Returns:
            list: All matching deployment records (could be 0, 1, or multiple)
        """
        matches = []
        
        for location_record in self.all_transducer_locations:
            if location_record['serial_number'] == serial_number:
                # Check date range validation
                if self.validate_date_range(
                    file_first_timestamp, 
                    location_record['start_date'], 
                    location_record['end_date']
                ):
                    matches.append(location_record)
        
        return matches
    
    def get_file_first_timestamp(self, file_path: Path):
        """
        Extract the first data timestamp from XLE file (not file creation date)
        
        Returns:
            datetime or None: First timestamp from XLE data
        """
        try:
            # Use SolinstReader to get actual data timestamps
            df, metadata = self.reader.read_xle(file_path)
            
            if not df.empty and 'timestamp' in df.columns:
                first_timestamp = df['timestamp'].min()
                print(f"      📅 File first reading: {first_timestamp}")
                return first_timestamp
            else:
                print(f"      ⚠️  No timestamp data found in {file_path.name}")
                return None
                
        except Exception as e:
            print(f"      ⚠️  Could not read timestamps from {file_path.name}: {e}")
            return None
    
    def extract_xle_metadata(self, file_path: Path) -> Dict:
        """Extract metadata from XLE file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(2048)
            
            # Extract serial number
            serial_match = re.search(r'<Serial_number>(\d+)</Serial_number>', content, re.IGNORECASE)
            serial = serial_match.group(1) if serial_match else None
            
            # Extract location
            location_match = re.search(r'<Location>(.*?)</Location>', content, re.IGNORECASE)
            location = location_match.group(1).strip() if location_match else ''
            
            # Extract instrument type
            instrument_match = re.search(r'<Instrument_type>(.*?)</Instrument_type>', content, re.IGNORECASE)
            instrument = instrument_match.group(1).strip() if instrument_match else ''
            
            # Check if this is a vented transducer
            is_vented = is_vented_transducer(instrument_type=instrument)
            
            return {
                'serial_number': serial,
                'location': location,
                'instrument_type': instrument,
                'is_vented': is_vented,
                'compensation_required': not is_vented,
                'file_size': file_path.stat().st_size,
                'file_path': str(file_path)
            }
        except Exception as e:
            return {
                'serial_number': None,
                'location': '',
                'instrument_type': '',
                'is_vented': False,
                'compensation_required': True,  # Default to requiring compensation if unknown
                'file_size': file_path.stat().st_size if file_path.exists() else 0,
                'file_path': str(file_path),
                'error': str(e)
            }
    
    def is_file_compensated(self, file_path: Path) -> bool:
        """
        Check if XLE file is already compensated by looking for <Compensation_info> section
        
        Compensated files have barometric compensation already applied by Solinst software
        and should NOT be imported to avoid double compensation.
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Look for <Compensation_info> section which indicates already compensated file
                if '<Compensation_info>' in content:
                    return True
                    
                return False
                
        except Exception as e:
            print(f"   ⚠️  Could not check compensation status for {file_path.name}: {e}")
            # If we can't determine, assume it's not compensated (safer for import)
            return False
    
    def load_databases(self):
        """Load all database information for matching"""
        print(f"\\n📊 Loading database information...")
        
        if not self.databases:
            print(f"   ⚠️  No databases found - files will be moved to unmatched folder")
            return
        
        for db_name, db_path in self.databases.items():
            if not db_path.exists():
                print(f"   ⚠️  Database not found: {db_name} at {db_path}")
                continue
            
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Load wells data
                cursor.execute("SELECT well_number, cae_number FROM wells")
                wells_rows = cursor.fetchall()
                wells_count = 0
                
                for well_number, cae_number in wells_rows:
                    if cae_number:
                        self.all_wells_data[well_number] = (cae_number, db_name)
                        wells_count += 1
                
                # Load transducer locations
                cursor.execute("""
                    SELECT serial_number, well_number, start_date, end_date 
                    FROM transducer_locations 
                    ORDER BY serial_number, start_date
                """)
                locations_rows = cursor.fetchall()
                
                locations_count = 0
                for serial_number, well_number, start_date, end_date in locations_rows:
                    if well_number in self.all_wells_data:
                        cae_number, _ = self.all_wells_data[well_number]
                        self.all_transducer_locations.append({
                            'serial_number': str(serial_number),
                            'well_number': well_number,
                            'start_date': start_date or '',  # Convert None to empty string
                            'end_date': end_date or '',      # Convert None to empty string
                            'cae_number': cae_number,
                            'database': db_name,
                            'device_type': 'transducer'
                        })
                        locations_count += 1
                
                # Load barologger locations (separate table for barometric sensors)
                try:
                    cursor.execute("""
                        SELECT bl.serial_number, bl.location_description, bl.start_date, bl.end_date 
                        FROM barologger_locations bl
                        JOIN barologgers b ON bl.serial_number = b.serial_number
                        ORDER BY bl.serial_number, bl.start_date
                    """)
                    baro_rows = cursor.fetchall()
                    
                    baro_count = 0
                    for serial_number, location_desc, start_date, end_date in baro_rows:
                        self.all_transducer_locations.append({
                            'serial_number': str(serial_number),
                            'well_number': None,  # Barologgers don't have well numbers
                            'start_date': start_date or '',
                            'end_date': end_date or '',
                            'cae_number': location_desc,  # Use location description as CAE number
                            'database': db_name,
                            'device_type': 'barologger'
                        })
                        baro_count += 1
                        locations_count += 1
                    
                    if baro_count > 0:
                        print(f"      📊 Added {baro_count} barologger locations")
                        
                except Exception as baro_error:
                    print(f"      ⚠️  Could not load barologgers from {db_name}: {baro_error}")
                    # Continue without barologgers if table doesn't exist
                
                conn.close()
                print(f"   ✅ {db_name}: {wells_count} wells, {locations_count} locations")
                
            except Exception as e:
                print(f"   ❌ Error loading {db_name}: {e}")
                continue
        
        print(f"   🎯 Total: {len(self.all_wells_data)} wells, {len(self.all_transducer_locations)} location records")
    
    def scan_folder(self, folder_path: str) -> Dict:
        """Scan a folder for XLE files and identify unique ones"""
        folder_path = Path(folder_path)
        
        if not folder_path.exists():
            raise ValueError(f"Folder does not exist: {folder_path}")
        
        print(f"\\n🔍 Scanning folder: {folder_path}")
        
        # Get previously processed file signatures
        processed_signatures = self.db.get_processed_signatures()
        
        # Find all XLE files
        xle_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.xle'):
                    xle_files.append(Path(root) / file)
        
        print(f"   📊 Found {len(xle_files)} XLE files")
        
        # Process files
        unique_files = []
        duplicates = []
        errors = []
        compensated_files = []  # Track compensated files separately
        vented_files = []  # Track vented transducers separately
        
        for file_path in xle_files:
            try:
                # Create file signature
                signature = self.create_file_signature(file_path)
                
                # Check if already processed
                if signature in processed_signatures:
                    duplicates.append({
                        'file_path': str(file_path),
                        'signature': signature,
                        'reason': 'already_processed'
                    })
                    continue
                
                # Check if file is already compensated (CRITICAL: avoid double compensation!)
                if self.is_file_compensated(file_path):
                    compensated_files.append({
                        'file_path': str(file_path),
                        'signature': signature,
                        'reason': 'already_compensated'
                    })
                    continue
                
                # Extract metadata
                metadata = self.extract_xle_metadata(file_path)
                
                if not metadata['serial_number']:
                    errors.append({
                        'file_path': str(file_path),
                        'reason': 'no_serial_number',
                        'error': metadata.get('error', 'Unknown error')
                    })
                    continue
                
                # Check if this is a vented transducer (for tracking/reporting)
                if metadata.get('is_vented', False):
                    vented_files.append({
                        'file_path': str(file_path),
                        'signature': signature,
                        'metadata': metadata,
                        'reason': 'vented_transducer'
                    })
                
                # This is a new unique file
                unique_files.append({
                    'file_path': str(file_path),
                    'signature': signature,
                    'metadata': metadata
                })
                
            except Exception as e:
                errors.append({
                    'file_path': str(file_path),
                    'reason': 'processing_error',
                    'error': str(e)
                })
        
        results = {
            'folder_path': str(folder_path),
            'scan_date': datetime.now().isoformat(),
            'total_files': len(xle_files),
            'unique_files': len(unique_files),
            'duplicates': len(duplicates),
            'errors': len(errors),
            'compensated_files': len(compensated_files),
            'vented_files': len(vented_files),
            'unique_files_list': unique_files,
            'duplicates_list': duplicates,
            'errors_list': errors,
            'compensated_files_list': compensated_files,
            'vented_files_list': vented_files
        }
        
        print(f"   ✅ Scan complete:")
        print(f"      🆕 Unique files: {len(unique_files)}")
        print(f"      🔄 Duplicates: {len(duplicates)}")
        print(f"      🚫 Compensated (skipped): {len(compensated_files)}")
        print(f"      🌬️ Vented transducers: {len(vented_files)}")
        print(f"      ❌ Errors: {len(errors)}")
        
        # Record scan in database
        self.db.record_folder_scan(
            str(folder_path),
            len(xle_files),
            len(unique_files),
            {
                'duplicates': len(duplicates),
                'errors': len(errors),
                'compensated_files': len(compensated_files),
                'vented_files': len(vented_files),
                'scan_method': 'universal_scanner'
            }
        )
        
        return results
    
    def process_unique_files(self, scan_results: Dict, apply_changes: bool = False) -> Dict:
        """Process unique files through CAE correction and organization"""
        
        if not scan_results['unique_files_list']:
            return {'processed': 0, 'corrected': 0, 'unmatched': 0}
        
        print(f"\\n🔧 Processing {len(scan_results['unique_files_list'])} unique files...")
        
        if not apply_changes:
            print("   📝 DRY RUN MODE - No files will be moved")
        else:
            # Ensure destination directories exist before copying files
            print("   📁 Creating destination directories...")
            self.corrected_dir.mkdir(parents=True, exist_ok=True)
            self.unmatched_dir.mkdir(parents=True, exist_ok=True)
            print(f"   ✅ Corrected dir: {self.corrected_dir}")
            print(f"   ✅ Unmatched dir: {self.unmatched_dir}")
        
        # Load databases for matching
        self.load_databases()
        
        # Check for previously unmatched files that can now be matched (smart upgrade)
        if apply_changes:
            self.check_and_upgrade_unmatched_files()
        
        corrected_count = 0
        unmatched_count = 0
        
        # Add matching info to results for dialog display
        for file_info in scan_results['unique_files_list']:
            file_info['match_info'] = {'project': 'Unmatched', 'cae_number': 'N/A'}
        
        # Clear any previous failure tracking
        self.failed_operations = []
        
        # Create temporary processing directory
        temp_dir = Path("temp_processing")
        if apply_changes:
            temp_dir.mkdir(exist_ok=True)
        
        try:
            for i, file_info in enumerate(scan_results['unique_files_list']):
                file_path = Path(file_info['file_path'])
                metadata = file_info['metadata']
                signature = file_info['signature']
                
                print(f"   📄 Processing: {file_path.name}")
                
                # Enhanced matching with date range validation
                serial_number = metadata['serial_number']
                matched = False
                multiple_matches = []
                
                print(f"      🔍 Checking matches for serial: {serial_number}")
                
                # Get first timestamp from file data for date validation
                file_first_timestamp = self.get_file_first_timestamp(file_path)
                
                if file_first_timestamp:
                    # Find all deployments that match serial number AND date range
                    matching_deployments = self.find_matching_deployments(serial_number, file_first_timestamp)
                    
                    if len(matching_deployments) == 1:
                        # Perfect match - single deployment
                        location_record = matching_deployments[0]
                        cae_number = location_record.get('cae_number', 'Unknown')
                        project_name = location_record.get('database', 'Unknown')
                        print(f"      ✅ MATCHED to well: {cae_number} in project: {project_name}")
                        print(f"         📅 Date validated: {file_first_timestamp.date()} within deployment range")
                        
                        # Store matching info for dialog display
                        scan_results['unique_files_list'][i]['match_info'] = {
                            'project': project_name,
                            'cae_number': cae_number,
                            'match_type': 'single_match'
                        }
                        matched = True
                        
                    elif len(matching_deployments) > 1:
                        # Multiple matches - this needs special handling
                        print(f"      ⚠️  MULTIPLE MATCHES found for serial {serial_number}:")
                        for match in matching_deployments:
                            print(f"         📍 {match['cae_number']} ({match['database']}) - {match['start_date']} to {match['end_date'] or 'current'}")
                        
                        # For now, use first match but mark as conflicted
                        location_record = matching_deployments[0]
                        cae_number = location_record.get('cae_number', 'Unknown')
                        project_name = location_record.get('database', 'Unknown')
                        
                        # Store matching info with conflict flag
                        scan_results['unique_files_list'][i]['match_info'] = {
                            'project': project_name,
                            'cae_number': cae_number,
                            'match_type': 'multiple_matches',
                            'all_matches': matching_deployments
                        }
                        matched = True
                        multiple_matches = matching_deployments
                        
                    else:
                        # No date-validated matches found
                        print(f"      ❌ No deployment found for serial {serial_number} matching file date {file_first_timestamp.date()}")
                        print(f"         Available deployments for this serial:")
                        for location_record in self.all_transducer_locations:
                            if location_record['serial_number'] == serial_number:
                                print(f"         📅 {location_record['cae_number']} ({location_record['database']}) - {location_record['start_date']} to {location_record['end_date'] or 'current'}")
                else:
                    print(f"      ⚠️  Could not extract timestamp - falling back to serial-only matching")
                    # Fallback to old logic if we can't get timestamps
                    for location_record in self.all_transducer_locations:
                        if location_record['serial_number'] == serial_number:
                            cae_number = location_record.get('cae_number', 'Unknown')
                            project_name = location_record.get('database', 'Unknown')
                            print(f"      ✅ FALLBACK MATCH to well: {cae_number} in project: {project_name} (Serial: {serial_number})")
                            
                            scan_results['unique_files_list'][i]['match_info'] = {
                                'project': project_name,
                                'cae_number': cae_number,
                                'match_type': 'fallback_serial_only'
                            }
                            matched = True
                            break
                
                if matched and apply_changes:
                    # Generate proper filename using database CAE number for consistency
                    # Format: SerialNumber_CAE_YYYY_MM_DD_To_YYYY_MM_DD.xle
                    # Use CAE number from database (not original XLE location) to match folder structure
                    # Keep CAE format simple for filename (allow dashes, just clean filesystem-unsafe chars)
                    cae_clean = str(cae_number).replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_').strip()
                    
                    # Extract actual first and last dates from data points (same as SMOO consolidator)
                    try:
                        # Read XLE file to get actual data (not just metadata)
                        df, _ = self.reader.read_xle(Path(file_path))
                        
                        # Get actual first and last dates from data
                        if not df.empty and 'timestamp' in df.columns:
                            first_date = df['timestamp'].min()
                            last_date = df['timestamp'].max()
                            start_date = first_date.strftime('%Y_%m_%d')
                            end_date = last_date.strftime('%Y_%m_%d')
                        else:
                            # Fallback if no data available
                            start_date = 'UNKNOWN'
                            end_date = 'UNKNOWN'
                    except Exception as e:
                        print(f"   ⚠️  Could not extract actual dates from {file_path.name}: {e}")
                        start_date = 'UNKNOWN'
                        end_date = 'UNKNOWN'
                    
                    # Determine device type and organize by project + device type + case/location
                    device_type = location_record.get('device_type', 'water_levels')
                    device_folder = 'barologgers' if device_type == 'barologger' else 'water_levels'
                    
                    # Add case/location subfolder for better organization
                    if device_type == 'barologger':
                        # For barologgers: use location name (already in cae_number field for baros)
                        subfolder_name = self.format_folder_name(cae_number)
                    else:
                        # For water level transducers: use CAE number
                        subfolder_name = self.format_folder_name(cae_number)
                    
                    # Create organized folder structure: corrected/PROJECT/device_type/CAE_or_LOCATION/
                    project_dir = self.corrected_dir / project_name / device_folder / subfolder_name
                    project_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Use CORRECT format: Serial_CAE_StartDate_To_EndDate.xle (matches folder structure)
                    new_name = f"{serial_number}_{cae_clean}_{start_date}_To_{end_date}.xle"
                    dest_path = project_dir / new_name
                    
                    # Attempt file copy with retry logic
                    copy_result = self.retry_operation(
                        shutil.copy2, file_path, dest_path,
                        operation_name=f"Copy {file_path.name} to corrected"
                    )
                    
                    if copy_result is not None:
                        print(f"      📁 Organized: {project_name}/{device_folder}/{subfolder_name}/")
                        print(f"      📄 Created: {new_name}")
                        print(f"      ✅ Using database CAE '{cae_number}' for consistent naming")
                        
                        # Record in database with enhanced metadata
                        try:
                            self.db.record_processed_file(
                                signature, str(file_path), file_path.name,
                                serial_number, metadata['file_size'],
                                str(dest_path), 'corrected',
                                cae_number, project_name, metadata.get('instrument_type')
                            )
                            corrected_count += 1
                        except Exception as db_error:
                            print(f"      ⚠️  Database recording failed: {str(db_error)[:100]}")
                            # Continue processing even if database fails
                    else:
                        print(f"      ❌ Skipped {file_path.name} - all copy attempts failed")
                        # Continue to next file instead of stopping entire process
                
                if not matched:
                    # No match found - goes to unmatched with organized structure  
                    print(f"      ❌ UNMATCHED: Serial {serial_number} not found in any database")
                    print(f"         Available serials: {[loc.get('serial_number', 'N/A') for loc in self.all_transducer_locations[:5]]}...")
                    if apply_changes:
                        # Organize unmatched files by device type too (guess from filename patterns)
                        device_folder = 'barologgers' if any(baro_pattern in file_path.name.lower() for baro_pattern in ['baro', 'barometric']) else 'water_levels'
                        unmatched_device_dir = self.unmatched_dir / device_folder
                        unmatched_device_dir.mkdir(parents=True, exist_ok=True)
                        
                        dest_path = unmatched_device_dir / file_path.name
                        
                        # Attempt file copy with retry logic
                        copy_result = self.retry_operation(
                            shutil.copy2, file_path, dest_path,
                            operation_name=f"Copy {file_path.name} to unmatched"
                        )
                        
                        if copy_result is not None:
                            # Record in database with enhanced metadata
                            try:
                                self.db.record_processed_file(
                                    signature, str(file_path), file_path.name,
                                    serial_number, metadata['file_size'],
                                    str(dest_path), 'unmatched',
                                    None, None, metadata.get('instrument_type')  # No CAE/project for unmatched
                                )
                                unmatched_count += 1
                            except Exception as db_error:
                                print(f"      ⚠️  Database recording failed: {str(db_error)[:100]}")
                                # Continue processing even if database fails
                        else:
                            print(f"      ❌ Skipped {file_path.name} - all copy attempts failed")
            
            # Generate failure report
            failure_report = self.generate_failure_report()
            if self.failed_operations:
                print(failure_report)
            
            results = {
                'processed': len(scan_results['unique_files_list']),
                'corrected': corrected_count,
                'unmatched': unmatched_count,
                'failures': len(self.failed_operations),
                'failure_report': failure_report,
                'dry_run': not apply_changes
            }
            
            action = "Would process" if not apply_changes else "Processed"
            print(f"   ✅ {action} {results['processed']} files:")
            print(f"      📁 Corrected: {results['corrected']}")
            print(f"      📁 Unmatched: {results['unmatched']}")
            if results['failures'] > 0:
                print(f"      ⚠️  Failures: {results['failures']} (processing continued)")
            
            return results
            
        finally:
            # Clean up temp directory
            if apply_changes and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def check_and_upgrade_unmatched_files(self):
        """Check previously unmatched files that can now be matched and upgrade them"""
        print("\\n🔄 Checking for unmatched files that can now be matched...")
        
        unmatched_files = self.db.get_unmatched_files()
        if not unmatched_files:
            print("   ℹ️  No unmatched files to check")
            return
        
        upgraded_count = 0
        
        for unmatched_file in unmatched_files:
            serial_number = unmatched_file['serial_number']
            original_location = Path(unmatched_file['final_location'])
            
            # Check if this serial number can now be matched
            matched_location = None
            matched_project = None
            matched_cae = None
            
            for location_record in self.all_transducer_locations:
                if location_record['serial_number'] == serial_number:
                    matched_location = location_record
                    matched_project = location_record.get('database', 'Unknown')
                    matched_cae = location_record.get('cae_number', 'Unknown')
                    break
            
            if matched_location:
                # We found a match! Move file from unmatched to corrected
                try:
                    if original_location.exists():
                        # Generate proper corrected filename
                        df, metadata = self.reader.read_xle(original_location)
                        
                        if not df.empty and 'timestamp' in df.columns:
                            first_date = df['timestamp'].min()
                            last_date = df['timestamp'].max()
                            start_date = first_date.strftime('%Y_%m_%d')
                            end_date = last_date.strftime('%Y_%m_%d')
                            
                            # Use database CAE number for consistency with folder structure
                            # Keep CAE format simple for filename (allow dashes, just clean filesystem-unsafe chars)
                            cae_clean = str(matched_cae).replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_').strip()
                            
                            # Determine device type and organize by project + device type + case/location
                            device_type = matched_location.get('device_type', 'water_levels')
                            device_folder = 'barologgers' if device_type == 'barologger' else 'water_levels'
                            
                            # Add case/location subfolder for better organization
                            if device_type == 'barologger':
                                # For barologgers: use location name (already in cae_number field for baros)
                                subfolder_name = self.format_folder_name(matched_cae)
                            else:
                                # For water level transducers: use CAE number
                                subfolder_name = self.format_folder_name(matched_cae)
                            
                            # Create organized folder structure for upgraded file: corrected/PROJECT/device_type/CAE_or_LOCATION/
                            project_dir = self.corrected_dir / matched_project / device_folder / subfolder_name
                            project_dir.mkdir(parents=True, exist_ok=True)
                            
                            # Generate corrected filename using database CAE number
                            corrected_name = f"{serial_number}_{cae_clean}_{start_date}_To_{end_date}.xle"
                            corrected_path = project_dir / corrected_name
                            
                            # Move file from unmatched to organized corrected folder with retry
                            move_result = self.retry_operation(
                                shutil.move, str(original_location), str(corrected_path),
                                operation_name=f"Move {original_location.name} to corrected"
                            )
                            
                            if move_result is not None:
                                print(f"      📁 Organized: {matched_project}/{device_folder}/{subfolder_name}/")
                                print(f"      📄 Upgraded: {corrected_name}")
                                print(f"      ✅ Using database CAE '{matched_cae}' for consistent naming")
                                
                                # Update database record
                                try:
                                    success = self.db.upgrade_file_status(
                                        unmatched_file['file_signature'],
                                        'corrected', 
                                        str(corrected_path),
                                        matched_cae,
                                        matched_project
                                    )
                                    
                                    if success:
                                        print(f"   ✅ UPGRADED: {original_location.name} → {corrected_name}")
                                        print(f"      📍 Now matched to well: {matched_cae} in project: {matched_project}")
                                        upgraded_count += 1
                                    else:
                                        print(f"   ⚠️  File moved but database update failed for {corrected_name}")
                                except Exception as db_error:
                                    print(f"   ⚠️  Database update failed: {str(db_error)[:100]}")
                                    # File was moved successfully, continue
                            else:
                                print(f"   ❌ Failed to move {original_location.name} - all move attempts failed")
                                # Continue to next file instead of stopping
                        else:
                            print(f"   ⚠️  Could not read data from {original_location.name} for upgrade")
                    else:
                        print(f"   ⚠️  Unmatched file no longer exists: {original_location}")
                        
                except Exception as e:
                    print(f"   ❌ Error upgrading {unmatched_file['filename']}: {e}")
        
        if upgraded_count > 0:
            print(f"   🎉 Successfully upgraded {upgraded_count} files from unmatched to corrected!")
        else:
            print("   ℹ️  No files could be upgraded at this time")
    
    def get_scan_summary(self) -> Dict:
        """Get summary of all scanning activity"""
        history = self.db.get_scan_history()
        
        total_scans = len(history)
        total_files_found = sum(scan['files_found'] for scan in history)
        total_unique_added = sum(scan['unique_files_added'] for scan in history)
        
        return {
            'total_scans': total_scans,
            'total_files_found': total_files_found,
            'total_unique_added': total_unique_added,
            'recent_scans': history[:10],  # Last 10 scans
            'current_collection_size': {
                'corrected': len(list(self.corrected_dir.glob("**/*.xle"))) if self.corrected_dir.exists() else 0,
                'unmatched': len(list(self.unmatched_dir.glob("**/*.xle"))) if self.unmatched_dir.exists() else 0
            }
        }


def main():
    """Main function for testing the universal scanner"""
    print("🔍 Universal XLE Folder Scanner")
    print("=" * 50)
    
    # Initialize scanner
    script_dir = Path(__file__).parent
    corrected_dir = script_dir / "corrected_xle_files" / "corrected"
    unmatched_dir = script_dir / "corrected_xle_files" / "unmatched"
    databases_dir = script_dir.parent / "databases"
    
    scanner = UniversalXLEScanner(corrected_dir, unmatched_dir, databases_dir)
    
    # Example usage - scan a test folder
    if len(sys.argv) > 1:
        folder_to_scan = sys.argv[1]
        
        try:
            # Scan folder
            results = scanner.scan_folder(folder_to_scan)
            
            # Process unique files (dry run)
            if results['unique_files'] > 0:
                process_results = scanner.process_unique_files(results, apply_changes=False)
                
                print(f"\\n💡 To apply changes, run with --apply flag")
            else:
                print(f"\\n✅ No unique files found to process")
            
            # Show summary
            summary = scanner.get_scan_summary()
            print(f"\\n📊 Scanner Summary:")
            print(f"   Total scans performed: {summary['total_scans']}")
            print(f"   Total files found: {summary['total_files_found']}")
            print(f"   Total unique files added: {summary['total_unique_added']}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return 1
    
    else:
        print("Usage: python3 universal_folder_scanner.py <folder_path>")
        print("       python3 universal_folder_scanner.py <folder_path> --apply")
        
        # Show current summary
        summary = scanner.get_scan_summary()
        print(f"\\n📊 Current Collection:")
        print(f"   Corrected files: {summary['current_collection_size']['corrected']}")
        print(f"   Unmatched files: {summary['current_collection_size']['unmatched']}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())