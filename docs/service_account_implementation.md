# Service Account Authentication Implementation Guide

## Overview
Service Account authentication allows your application to authenticate with Google Drive without requiring user login. The application uses its own credentials to access Google Drive resources.

## Service Account vs OAuth2 User Authentication

### Current OAuth2 Flow
- Requires user to log in with Google account
- Opens browser for authentication
- User must have access to the Drive folders
- Token stored locally per user
- Requires user interaction

### Service Account Flow
- No user login required
- Uses private key file for authentication
- Application authenticates as itself
- No browser interaction needed
- Credentials embedded in application

## Pros and Cons

### Advantages of Service Account
1. **No User Interaction**: Completely automated authentication
2. **Consistent Access**: Same credentials for all users
3. **Simplified Deployment**: No OAuth consent screens
4. **Better for Automation**: Ideal for background services
5. **No Token Management**: No refresh tokens to handle

### Disadvantages of Service Account
1. **Security Risk**: Private key must be protected
2. **Shared Access**: All users access same Drive account
3. **No User Attribution**: Can't track individual user actions
4. **Folder Sharing Required**: Must share folders with service account
5. **Quota Limits**: All requests count against single account

## Implementation Steps

### 1. Create Service Account in Google Cloud Console
```
1. Go to Google Cloud Console
2. Create new project or select existing
3. Enable Google Drive API
4. Create Service Account:
   - Go to "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Fill in service account details
   - Grant "Editor" role
   - Create and download JSON key file
```

### 2. Share Google Drive Folders
```
1. Get service account email from JSON file
2. Share each Drive folder with service account email
3. Grant "Editor" permissions
```

### 3. Update Authentication Code

Replace current OAuth2 authentication with service account:

```python
from google.oauth2 import service_account
from googleapiclient.discovery import build

class GoogleDriveService:
    """Service Account based Google Drive authentication"""
    
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    def __init__(self, settings_handler):
        self.settings_handler = settings_handler
        self.service = None
        self.authenticated = False
        
    def authenticate(self, force=False):
        """Authenticate using service account credentials"""
        try:
            # Get service account key file path
            key_file_path = self.settings_handler.get_setting(
                "service_account_key_path", 
                "config/service-account-key.json"
            )
            
            if not os.path.exists(key_file_path):
                logger.error(f"Service account key file not found: {key_file_path}")
                return False
            
            # Create credentials from service account key
            credentials = service_account.Credentials.from_service_account_file(
                key_file_path,
                scopes=self.SCOPES
            )
            
            # Build the Drive service
            self.service = build('drive', 'v3', credentials=credentials)
            self.authenticated = True
            logger.info("Successfully authenticated with service account")
            return True
            
        except Exception as e:
            logger.error(f"Service account authentication error: {e}")
            self.authenticated = False
            return False
    
    def get_service(self):
        """Get the authenticated Google Drive service"""
        if not self.authenticated:
            if not self.authenticate():
                return None
        return self.service
```

### 4. Update Settings Dialog

Remove OAuth-specific UI elements and add service account configuration:

```python
class GoogleDriveSettingsDialog(QDialog):
    def setup_ui(self):
        # Service Account Configuration
        sa_group = QGroupBox("Service Account Configuration")
        sa_layout = QVBoxLayout(sa_group)
        
        # Service account key file
        key_layout = QHBoxLayout()
        key_label = QLabel("Service Account Key:")
        self.key_path = QLineEdit()
        self.key_path.setPlaceholderText("Path to service-account-key.json")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_service_account_key)
        
        key_layout.addWidget(key_label)
        key_layout.addWidget(self.key_path, 1)
        key_layout.addWidget(browse_btn)
        
        # Display service account email
        self.sa_email_label = QLabel("Service Account Email: Not loaded")
        sa_layout.addLayout(key_layout)
        sa_layout.addWidget(self.sa_email_label)
```

### 5. Security Considerations

**Protecting the Service Account Key:**

```python
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class SecureKeyStorage:
    """Encrypt service account key for storage"""
    
    @staticmethod
    def encrypt_key(key_data: dict, password: str) -> bytes:
        """Encrypt service account key with password"""
        # Derive key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'water_levels_salt',  # Should be random in production
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        f = Fernet(key)
        
        # Encrypt the JSON data
        encrypted = f.encrypt(json.dumps(key_data).encode())
        return encrypted
    
    @staticmethod
    def decrypt_key(encrypted_data: bytes, password: str) -> dict:
        """Decrypt service account key with password"""
        # Derive key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'water_levels_salt',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        f = Fernet(key)
        
        # Decrypt the data
        decrypted = f.decrypt(encrypted_data)
        return json.loads(decrypted.decode())
```

## Migration Path

### Phase 1: Dual Authentication Support
1. Add service account authentication alongside OAuth2
2. Add setting to choose authentication method
3. Test with select users

### Phase 2: Service Account Default
1. Make service account the default method
2. Keep OAuth2 as fallback option
3. Document migration for users

### Phase 3: Remove OAuth2
1. Remove OAuth2 code completely
2. Simplify authentication flow
3. Update all documentation

## Alternative Solutions

### 1. API Key Authentication
- Simpler but less secure
- Limited to public data only
- Not suitable for private Drive files

### 2. Domain-Wide Delegation
- Service account impersonates users
- Requires Google Workspace admin setup
- Maintains user attribution

### 3. Hybrid Approach
- Service account for system operations
- OAuth2 for user-specific operations
- More complex but flexible

## Recommended Approach

For your use case, I recommend:

1. **Pure Service Account** if:
   - All users need same access
   - No user attribution needed
   - Simplified deployment is priority

2. **Domain-Wide Delegation** if:
   - Using Google Workspace
   - Need user attribution
   - Want to maintain permissions

3. **Hybrid Approach** if:
   - Some operations are system-wide
   - Some operations are user-specific
   - Need maximum flexibility

## Example Implementation

Here's a complete example of the updated GoogleDriveService:

```python
import os
import json
import logging
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

class GoogleDriveService:
    """Service Account based Google Drive authentication"""
    
    SCOPES = ['https://www.googleapis.com/auth/drive']
    _instance = None
    
    @classmethod
    def get_instance(cls, settings_handler=None):
        if cls._instance is None and settings_handler is not None:
            cls._instance = cls(settings_handler)
        return cls._instance
    
    def __init__(self, settings_handler):
        if GoogleDriveService._instance is not None:
            raise Exception("This class is a singleton. Use get_instance() instead.")
            
        self.settings_handler = settings_handler
        self.service = None
        self.authenticated = False
        self.service_account_email = None
        
    def authenticate(self, force=False):
        """Authenticate using service account credentials"""
        if self.authenticated and not force:
            return True
            
        try:
            # Get service account key file path
            key_file_path = self.settings_handler.get_setting(
                "service_account_key_path", 
                ""
            )
            
            # Try default location if not set
            if not key_file_path or not os.path.exists(key_file_path):
                default_path = Path.cwd() / "config" / "service-account-key.json"
                if default_path.exists():
                    key_file_path = str(default_path)
                    self.settings_handler.set_setting(
                        "service_account_key_path", 
                        key_file_path
                    )
            
            if not key_file_path or not os.path.exists(key_file_path):
                logger.error("Service account key file not found")
                return False
            
            # Load and parse key file to get email
            with open(key_file_path, 'r') as f:
                key_data = json.load(f)
                self.service_account_email = key_data.get('client_email')
            
            # Create credentials from service account key
            credentials = service_account.Credentials.from_service_account_file(
                key_file_path,
                scopes=self.SCOPES
            )
            
            # Build the Drive service
            self.service = build('drive', 'v3', credentials=credentials)
            self.authenticated = True
            logger.info(f"Authenticated as service account: {self.service_account_email}")
            return True
            
        except Exception as e:
            logger.error(f"Service account authentication error: {e}")
            self.authenticated = False
            return False
    
    def get_service(self):
        """Get the authenticated Google Drive service"""
        if not self.authenticated:
            if not self.authenticate():
                return None
        return self.service
    
    def get_service_account_email(self):
        """Get the service account email address"""
        return self.service_account_email
```

## Next Steps

1. Create service account in Google Cloud Console
2. Download service account key JSON file
3. Share all Drive folders with service account email
4. Update authentication code
5. Test thoroughly before removing OAuth2
6. Update documentation for users