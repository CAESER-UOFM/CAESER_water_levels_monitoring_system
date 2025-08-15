#!/usr/bin/env python3
"""
Enhanced Field Data Processing Configuration System

Provides comprehensive configuration management and validation for the enhanced
field data processing pipeline. Includes settings validation, default values,
environment overrides, and configuration recovery.

Configuration categories:
1. Google Drive Integration Settings
2. File Processing Options
3. Duplicate Detection Configuration  
4. Temp Folder Management
5. Error Handling & Recovery
6. Logging & Monitoring

@author: Phase 8 implementation - Configuration & Error Handling
"""

import os
import json
import logging
import platform
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class GoogleDriveConfig:
    """Google Drive integration configuration"""
    service_account_file: str = ""
    solinst_folder_id: str = ""
    max_download_retries: int = 3
    download_timeout_seconds: int = 300
    batch_size: int = 10
    rate_limit_delay: float = 0.5
    enable_date_filtering: bool = True

@dataclass
class ProcessingConfig:
    """File processing configuration"""
    max_filename_length: int = 80
    preserve_original_timestamps: bool = True
    validate_metadata_completeness: bool = True
    skip_files_with_errors: bool = False
    enable_intelligent_naming: bool = True
    hierarchical_organization: bool = True
    date_format: str = "%Y-%m-%d"
    
@dataclass
class DuplicateDetectionConfig:
    """Duplicate detection configuration"""
    enable_duplicate_detection: bool = True
    use_content_hash: bool = True
    allow_time_range_overlap: bool = False
    overlap_tolerance_hours: int = 1
    cleanup_invalid_records: bool = True
    backup_registry_on_cleanup: bool = True

@dataclass
class TempFolderConfig:
    """Temporary folder management configuration"""
    base_temp_dir: str = ""  # Empty means use system default
    session_timeout_hours: int = 24
    auto_cleanup_on_exit: bool = True
    emergency_cleanup_on_start: bool = False
    max_temp_disk_usage_gb: float = 5.0

@dataclass
class ErrorHandlingConfig:
    """Error handling and recovery configuration"""
    max_retries: int = 3
    retry_delay_seconds: float = 2.0
    exponential_backoff: bool = True
    continue_on_file_errors: bool = True
    enable_error_recovery: bool = True
    save_error_logs: bool = True
    error_log_retention_days: int = 30

@dataclass
class LoggingConfig:
    """Logging and monitoring configuration"""
    log_level: str = "INFO"
    enable_file_logging: bool = True
    log_file_rotation: bool = True
    max_log_file_size_mb: int = 10
    log_retention_days: int = 30
    enable_performance_monitoring: bool = False

@dataclass
class EnhancedFieldDataConfig:
    """Complete enhanced field data processing configuration"""
    
    # Configuration sections
    google_drive: GoogleDriveConfig = field(default_factory=GoogleDriveConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    duplicate_detection: DuplicateDetectionConfig = field(default_factory=DuplicateDetectionConfig)
    temp_folder: TempFolderConfig = field(default_factory=TempFolderConfig)
    error_handling: ErrorHandlingConfig = field(default_factory=ErrorHandlingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # System configuration
    version: str = "1.0.0"
    platform: str = platform.system()
    config_created: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

class ConfigurationManager:
    """
    Enhanced field data processing configuration manager
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager
        
        Args:
            config_file: Optional path to configuration file
        """
        self.config_file = config_file or self._get_default_config_path()
        self.config: EnhancedFieldDataConfig = EnhancedFieldDataConfig()
        self.validation_errors: List[str] = []
        
        # Load configuration
        self.load_configuration()
        
        logger.info(f"Configuration manager initialized: {self.config_file}")
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path"""
        if platform.system() == "Windows":
            config_dir = os.path.join(os.environ.get('APPDATA', ''), 'CAESER_Field_Data')
        else:
            config_dir = os.path.join(os.path.expanduser('~'), '.caeser_field_data')
        
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, 'enhanced_field_data_config.json')
    
    def load_configuration(self) -> bool:
        """
        Load configuration from file with validation
        
        Returns:
            True if loaded successfully
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # Reconstruct config object from loaded data
                self.config = self._dict_to_config(config_data)
                
                # Apply environment overrides
                self._apply_environment_overrides()
                
                # Validate configuration
                if not self.validate_configuration():
                    logger.warning("Configuration validation failed, using defaults for invalid values")
                
                # Update last loaded timestamp
                self.config.last_updated = datetime.now().isoformat()
                
                logger.info("Configuration loaded successfully")
                return True
            else:
                logger.info("No configuration file found, using defaults")
                self._create_default_configuration()
                # Apply environment overrides even for default configuration
                self._apply_environment_overrides()
                return True
                
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self._create_default_configuration()
            self._apply_environment_overrides()
            return False
    
    def save_configuration(self) -> bool:
        """
        Save configuration to file
        
        Returns:
            True if saved successfully
        """
        try:
            # Update timestamp
            self.config.last_updated = datetime.now().isoformat()
            
            # Create backup if file exists
            if os.path.exists(self.config_file):
                backup_path = f"{self.config_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                import shutil
                shutil.copy2(self.config_file, backup_path)
                logger.debug(f"Created configuration backup: {backup_path}")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # Save atomically
            temp_file = f"{self.config_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.config), f, indent=2, ensure_ascii=False)
            
            os.replace(temp_file, self.config_file)
            
            logger.info(f"Configuration saved: {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False
    
    def validate_configuration(self) -> bool:
        """
        Validate current configuration
        
        Returns:
            True if configuration is valid
        """
        self.validation_errors = []
        
        try:
            # Validate Google Drive settings
            if not self.config.google_drive.service_account_file:
                self.validation_errors.append("Google Drive service account file not specified")
            elif not os.path.exists(self.config.google_drive.service_account_file):
                self.validation_errors.append(f"Service account file not found: {self.config.google_drive.service_account_file}")
            
            # Validate processing settings
            if self.config.processing.max_filename_length < 20:
                self.validation_errors.append("Maximum filename length too short (minimum 20 characters)")
                self.config.processing.max_filename_length = 80
            
            # Validate temp folder settings
            if self.config.temp_folder.max_temp_disk_usage_gb < 0.1:
                self.validation_errors.append("Maximum temp disk usage too small (minimum 0.1 GB)")
                self.config.temp_folder.max_temp_disk_usage_gb = 1.0
            
            # Validate error handling settings
            if self.config.error_handling.max_retries < 0:
                self.validation_errors.append("Maximum retries cannot be negative")
                self.config.error_handling.max_retries = 3
            
            # Validate logging settings
            valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if self.config.logging.log_level not in valid_log_levels:
                self.validation_errors.append(f"Invalid log level: {self.config.logging.log_level}")
                self.config.logging.log_level = 'INFO'
            
            if self.validation_errors:
                logger.warning(f"Configuration validation issues: {len(self.validation_errors)}")
                for error in self.validation_errors:
                    logger.warning(f"  - {error}")
                return False
            
            logger.debug("Configuration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Error during configuration validation: {e}")
            return False
    
    def _apply_environment_overrides(self):
        """Apply environment variable overrides"""
        try:
            # Google Drive overrides
            if os.getenv('CAESER_SERVICE_ACCOUNT_FILE'):
                self.config.google_drive.service_account_file = os.getenv('CAESER_SERVICE_ACCOUNT_FILE')
            
            if os.getenv('CAESER_SOLINST_FOLDER_ID'):
                self.config.google_drive.solinst_folder_id = os.getenv('CAESER_SOLINST_FOLDER_ID')
            
            # Processing overrides
            if os.getenv('CAESER_MAX_FILENAME_LENGTH'):
                try:
                    self.config.processing.max_filename_length = int(os.getenv('CAESER_MAX_FILENAME_LENGTH'))
                except ValueError:
                    logger.warning("Invalid CAESER_MAX_FILENAME_LENGTH environment variable")
            
            # Logging overrides
            if os.getenv('CAESER_LOG_LEVEL'):
                self.config.logging.log_level = os.getenv('CAESER_LOG_LEVEL').upper()
            
            # Temp folder overrides
            if os.getenv('CAESER_TEMP_DIR'):
                self.config.temp_folder.base_temp_dir = os.getenv('CAESER_TEMP_DIR')
            
            logger.debug("Applied environment variable overrides")
            
        except Exception as e:
            logger.warning(f"Error applying environment overrides: {e}")
    
    def _create_default_configuration(self):
        """Create default configuration"""
        self.config = EnhancedFieldDataConfig()
        
        # Set platform-specific defaults
        if platform.system() == "Windows":
            # Windows-specific defaults
            pass
        elif platform.system() == "Darwin":
            # macOS-specific defaults  
            pass
        else:
            # Linux-specific defaults
            pass
        
        logger.info("Created default configuration")
    
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> EnhancedFieldDataConfig:
        """Convert dictionary to configuration object"""
        try:
            return EnhancedFieldDataConfig(
                google_drive=GoogleDriveConfig(**config_dict.get('google_drive', {})),
                processing=ProcessingConfig(**config_dict.get('processing', {})),
                duplicate_detection=DuplicateDetectionConfig(**config_dict.get('duplicate_detection', {})),
                temp_folder=TempFolderConfig(**config_dict.get('temp_folder', {})),
                error_handling=ErrorHandlingConfig(**config_dict.get('error_handling', {})),
                logging=LoggingConfig(**config_dict.get('logging', {})),
                version=config_dict.get('version', '1.0.0'),
                platform=config_dict.get('platform', platform.system()),
                config_created=config_dict.get('config_created', datetime.now().isoformat()),
                last_updated=config_dict.get('last_updated', datetime.now().isoformat())
            )
        except Exception as e:
            logger.warning(f"Error reconstructing configuration from dict: {e}")
            return EnhancedFieldDataConfig()
    
    def get_setting(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a specific configuration setting
        
        Args:
            section: Configuration section name
            key: Setting key
            default: Default value if not found
            
        Returns:
            Setting value or default
        """
        try:
            section_obj = getattr(self.config, section, None)
            if section_obj is None:
                return default
            
            return getattr(section_obj, key, default)
            
        except Exception as e:
            logger.warning(f"Error getting setting {section}.{key}: {e}")
            return default
    
    def set_setting(self, section: str, key: str, value: Any) -> bool:
        """
        Set a specific configuration setting
        
        Args:
            section: Configuration section name
            key: Setting key
            value: Setting value
            
        Returns:
            True if set successfully
        """
        try:
            section_obj = getattr(self.config, section, None)
            if section_obj is None:
                logger.warning(f"Unknown configuration section: {section}")
                return False
            
            setattr(section_obj, key, value)
            logger.debug(f"Set configuration: {section}.{key} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting {section}.{key}: {e}")
            return False
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get summary of current configuration"""
        try:
            return {
                'version': self.config.version,
                'platform': self.config.platform,
                'config_file': self.config_file,
                'config_created': self.config.config_created,
                'last_updated': self.config.last_updated,
                'validation_errors': len(self.validation_errors),
                'sections': {
                    'google_drive': {
                        'service_account_configured': bool(self.config.google_drive.service_account_file),
                        'folder_id_configured': bool(self.config.google_drive.solinst_folder_id),
                        'date_filtering_enabled': self.config.google_drive.enable_date_filtering
                    },
                    'processing': {
                        'intelligent_naming': self.config.processing.enable_intelligent_naming,
                        'hierarchical_organization': self.config.processing.hierarchical_organization,
                        'max_filename_length': self.config.processing.max_filename_length
                    },
                    'duplicate_detection': {
                        'enabled': self.config.duplicate_detection.enable_duplicate_detection,
                        'content_hash': self.config.duplicate_detection.use_content_hash
                    },
                    'error_handling': {
                        'max_retries': self.config.error_handling.max_retries,
                        'continue_on_errors': self.config.error_handling.continue_on_file_errors
                    },
                    'logging': {
                        'level': self.config.logging.log_level,
                        'file_logging': self.config.logging.enable_file_logging
                    }
                }
            }
        except Exception as e:
            logger.error(f"Error getting configuration summary: {e}")
            return {'error': str(e)}
    
    def reset_to_defaults(self, backup: bool = True) -> bool:
        """
        Reset configuration to defaults
        
        Args:
            backup: Whether to backup current configuration
            
        Returns:
            True if reset successful
        """
        try:
            if backup and os.path.exists(self.config_file):
                backup_path = f"{self.config_file}.reset_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                import shutil
                shutil.copy2(self.config_file, backup_path)
                logger.info(f"Created configuration backup: {backup_path}")
            
            self._create_default_configuration()
            self.save_configuration()
            
            logger.info("Configuration reset to defaults")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting configuration: {e}")
            return False
    
    def export_configuration(self, output_path: str) -> bool:
        """
        Export current configuration to file
        
        Args:
            output_path: Output file path
            
        Returns:
            True if exported successfully
        """
        try:
            config_export = {
                'export_timestamp': datetime.now().isoformat(),
                'config_summary': self.get_configuration_summary(),
                'full_configuration': asdict(self.config),
                'validation_errors': self.validation_errors
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(config_export, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Configuration exported: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting configuration: {e}")
            return False