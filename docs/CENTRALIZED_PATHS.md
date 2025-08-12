# Centralized Path Configuration

## Problem Solved
Previously, shared drive paths were hardcoded in 7+ different files, making path changes require manual updates across the entire codebase. This was error-prone and violated the DRY (Don't Repeat Yourself) principle.

## Solution: Single Source of Truth

### 1. Central Configuration
**File**: `src/config/paths.py`
- Contains `DefaultPaths` class with all shared drive paths
- Single location to change base path structure
- Provides functions for getting path configurations

### 2. Settings Integration
**File**: `src/gui/handlers/settings_handler.py`
- Imports default paths from centralized location
- No hardcoded fallback paths in settings defaults
- Uses `get_default_shared_drive_paths()` function

### 3. Code Updates
All modules now:
- Import from `src/config/paths.py` instead of hardcoding
- Remove fallback defaults or use centralized ones
- Fail gracefully if config is missing instead of using stale defaults

## How to Change Paths Now

### To change the base shared drive location:

1. **Option A: Update config file** (Recommended)
   ```json
   // config/settings.json
   {
     "shared_drive_root": "T:/New_Location/Water_levels_monitoring_system/",
     "shared_drive_projects": "T:/New_Location/Water_levels_monitoring_system/Projects/",
     // etc...
   }
   ```

2. **Option B: Update central constants** (For permanent changes)
   ```python
   # src/config/paths.py
   class DefaultPaths:
       SHARED_DRIVE_BASE = "T:/New_Location/Water_levels_monitoring_system"
   ```

### Result:
- **ONE change** updates the entire application
- **No hunting** for hardcoded paths in multiple files
- **Consistent behavior** across all modules

## Files Modified

### Updated to use centralized paths:
1. `src/config/paths.py` - **NEW**: Central path definitions
2. `src/gui/handlers/settings_handler.py` - Uses centralized defaults
3. `src/gui/handlers/shared_drive_db_handler.py` - Removed hardcoded fallback
4. `src/gui/handlers/shared_drive_updater.py` - Uses `DefaultPaths`
5. `src/gui/dialogs/shared_drive_settings_dialog.py` - Dynamic placeholder
6. `docs/help/TEAM_INSTRUCTIONS/installation_and_setup.md` - Added note about centralized config

### Files that already had correct paths:
- `windows_installer.bat` - Already used correct path
- `config/settings.json` - Already had correct paths

## Benefits

1. **Maintainability**: Change paths in one place
2. **Consistency**: All modules use same configuration source
3. **Error Prevention**: No risk of missing updates in some files
4. **Clarity**: Clear hierarchy of configuration (config file > defaults > error)
5. **Documentation**: Central location documents path structure

## Migration Notes

- **Backward Compatible**: Existing config files continue to work
- **Graceful Degradation**: Missing config values cause helpful error messages
- **No Breaking Changes**: All existing functionality preserved
- **Future Proof**: Easy to add new path configurations

## Usage Examples

```python
# Good: Use centralized configuration
from src.config.paths import DefaultPaths, get_default_shared_drive_paths

# Get default base path
base_path = DefaultPaths.SHARED_DRIVE_BASE

# Get all default paths as dict
paths = get_default_shared_drive_paths()

# Bad: Don't hardcode paths anymore
# hardcoded_path = "S:/Water_Projects/CAESER/Water_Data_Series/Water_levels_monitoring_system/"
```

This refactoring ensures that path management follows software engineering best practices and makes the system much more maintainable.