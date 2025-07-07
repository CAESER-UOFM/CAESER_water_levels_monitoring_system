# Setup Instructions

## Initial Configuration

1. **Copy the settings template:**
   ```bash
   cp config/settings.template.json config/settings.json
   ```

2. **Configure Google Drive (if using cloud features):**
   - Set `google_drive_folder_id` to your main Google Drive folder ID
   - Set `google_drive_xle_folder_id` for XLE files
   - Set `google_drive_projects_folder_id` for cloud projects
   - Set `service_account_key_path` to your service account JSON file path

3. **Create required directories:**
   ```bash
   mkdir -p databases
   mkdir -p data
   mkdir -p temp
   ```

## Configuration Notes

- `local_db_directory`: Uses `./databases` (relative to installation folder)
- `service_account_key_path`: Set to your Google Drive service account key location
- All paths use relative directories to keep the installation portable
- User-specific configurations are kept in `config/settings.json` (not tracked by git)

## Directory Structure

```
project/
├── databases/          # Local database files
├── data/              # Data files (transducer, barometric, water level)
├── temp/              # Temporary cache files (auto-created)
├── config/
│   ├── settings.template.json  # Template for settings
│   └── settings.json          # Your personal settings (not tracked)
└── ...
```