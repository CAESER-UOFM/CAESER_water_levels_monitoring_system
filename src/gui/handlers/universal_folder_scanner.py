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

# Handle imports that work both in package context and standalone
try:
    # Try relative imports first (when used as part of the package)
    from ...config.smoo_paths import get_smoo_path, is_smoo_available
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
                status TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def record_folder_scan(self, folder_path: str, files_found: int, unique_added: int, metadata: Dict):
        """Record a completed folder scan"""
        conn = sqlite3.connect(self.db_path)
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
        conn.close()
    
    def record_processed_file(self, file_sig: str, file_path: str, filename: str, 
                            serial: str, size: int, final_location: str, status: str):
        """Record a processed file"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO processed_files 
            (file_signature, original_path, filename, serial_number, file_size, 
             processing_date, final_location, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            file_sig, str(file_path), filename, serial, size,
            datetime.now().isoformat(), final_location, status
        ))
        
        conn.commit()
        conn.close()
    
    def get_processed_signatures(self) -> Set[str]:
        """Get all processed file signatures"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT file_signature FROM processed_files')
        signatures = {row[0] for row in cursor.fetchall()}
        
        conn.close()
        return signatures
    
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
        self.db = FolderScanDatabase()
        
        # Load databases dynamically from SMOO Projects structure
        self.databases = self._discover_project_databases()
        
        # Combined data from all databases
        self.all_wells_data = {}
        self.all_transducer_locations = []
        
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
            
            return {
                'serial_number': serial,
                'location': location,
                'instrument_type': instrument,
                'file_size': file_path.stat().st_size,
                'file_path': str(file_path)
            }
        except Exception as e:
            return {
                'serial_number': None,
                'location': '',
                'instrument_type': '',
                'file_size': file_path.stat().st_size if file_path.exists() else 0,
                'file_path': str(file_path),
                'error': str(e)
            }
    
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
                            'start_date': start_date,
                            'end_date': end_date,
                            'cae_number': cae_number,
                            'database': db_name
                        })
                        locations_count += 1
                
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
                
                # Extract metadata
                metadata = self.extract_xle_metadata(file_path)
                
                if not metadata['serial_number']:
                    errors.append({
                        'file_path': str(file_path),
                        'reason': 'no_serial_number',
                        'error': metadata.get('error', 'Unknown error')
                    })
                    continue
                
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
            'unique_files_list': unique_files,
            'duplicates_list': duplicates,
            'errors_list': errors
        }
        
        print(f"   ✅ Scan complete:")
        print(f"      🆕 Unique files: {len(unique_files)}")
        print(f"      🔄 Duplicates: {len(duplicates)}")
        print(f"      ❌ Errors: {len(errors)}")
        
        # Record scan in database
        self.db.record_folder_scan(
            str(folder_path),
            len(xle_files),
            len(unique_files),
            {
                'duplicates': len(duplicates),
                'errors': len(errors),
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
        
        # Load databases for matching
        self.load_databases()
        
        corrected_count = 0
        unmatched_count = 0
        
        # Create temporary processing directory
        temp_dir = Path("temp_processing")
        if apply_changes:
            temp_dir.mkdir(exist_ok=True)
        
        try:
            for file_info in scan_results['unique_files_list']:
                file_path = Path(file_info['file_path'])
                metadata = file_info['metadata']
                signature = file_info['signature']
                
                print(f"   📄 Processing: {file_path.name}")
                
                # Try to match with databases (simplified matching for now)
                serial_number = metadata['serial_number']
                matched = False
                
                for location_record in self.all_transducer_locations:
                    if location_record['serial_number'] == serial_number:
                        # Found a match - this would go to corrected
                        if apply_changes:
                            # Copy to corrected folder with proper naming
                            new_name = f"{serial_number}_{location_record['cae_number']}_{file_path.stem}.xle"
                            dest_path = self.corrected_dir / new_name
                            shutil.copy2(file_path, dest_path)
                            
                            # Record in database
                            self.db.record_processed_file(
                                signature, str(file_path), file_path.name,
                                serial_number, metadata['file_size'],
                                str(dest_path), 'corrected'
                            )
                            
                        corrected_count += 1
                        matched = True
                        break
                
                if not matched:
                    # No match found - goes to unmatched
                    if apply_changes:
                        dest_path = self.unmatched_dir / file_path.name
                        shutil.copy2(file_path, dest_path)
                        
                        # Record in database
                        self.db.record_processed_file(
                            signature, str(file_path), file_path.name,
                            serial_number, metadata['file_size'],
                            str(dest_path), 'unmatched'
                        )
                    
                    unmatched_count += 1
            
            results = {
                'processed': len(scan_results['unique_files_list']),
                'corrected': corrected_count,
                'unmatched': unmatched_count,
                'dry_run': not apply_changes
            }
            
            action = "Would process" if not apply_changes else "Processed"
            print(f"   ✅ {action} {results['processed']} files:")
            print(f"      📁 Corrected: {results['corrected']}")
            print(f"      📁 Unmatched: {results['unmatched']}")
            
            return results
            
        finally:
            # Clean up temp directory
            if apply_changes and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
    
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
                'corrected': len(list(self.corrected_dir.glob("*.xle"))) if self.corrected_dir.exists() else 0,
                'unmatched': len(list(self.unmatched_dir.glob("*.xle"))) if self.unmatched_dir.exists() else 0
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