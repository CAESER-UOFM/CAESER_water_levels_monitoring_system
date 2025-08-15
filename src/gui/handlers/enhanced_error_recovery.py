#!/usr/bin/env python3
"""
Enhanced Error Recovery and Resilience System

Provides comprehensive error recovery, retry logic, and system resilience for
the enhanced field data processing pipeline. Handles various failure scenarios
including network issues, file corruption, permission problems, and system crashes.

Recovery strategies:
1. Exponential Backoff Retry Logic
2. Network Disconnection Handling  
3. File System Error Recovery
4. Partial Processing State Recovery
5. Graceful Degradation
6. Error Classification and Reporting

@author: Phase 8 implementation - Error Recovery System
"""

import os
import time
import json
import logging
import shutil
import platform
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import traceback

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"           # Non-critical, continue processing
    MEDIUM = "medium"     # Significant but recoverable  
    HIGH = "high"         # Critical, requires intervention
    FATAL = "fatal"       # Unrecoverable system failure

class ErrorCategory(Enum):
    """Error category types"""
    NETWORK = "network"                 # Network connectivity issues
    FILESYSTEM = "filesystem"           # File system access problems
    AUTHENTICATION = "authentication"   # Google Drive auth failures
    DATA_CORRUPTION = "data_corruption" # File corruption or invalid data
    PERMISSION = "permission"           # Access permission issues
    RESOURCE = "resource"               # Disk space, memory issues
    CONFIGURATION = "configuration"     # Invalid settings or config
    UNKNOWN = "unknown"                 # Unclassified errors

@dataclass
class ErrorRecord:
    """Record of an error occurrence"""
    timestamp: str
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    traceback: str
    context: Dict[str, Any]
    recovery_attempted: bool = False
    recovery_successful: bool = False
    retry_count: int = 0
    resolution: str = ""

@dataclass
class RecoveryState:
    """State of processing recovery"""
    last_successful_operation: str
    partial_processing_data: Dict[str, Any]
    failed_files: List[str] = None
    completed_files: List[str] = None
    recovery_checkpoint: str = ""
    
    def __post_init__(self):
        if self.failed_files is None:
            self.failed_files = []
        if self.completed_files is None:
            self.completed_files = []

class EnhancedErrorRecoverySystem:
    """
    Comprehensive error recovery and resilience system
    """
    
    def __init__(self, config_manager, recovery_dir: Optional[str] = None):
        """
        Initialize error recovery system
        
        Args:
            config_manager: Configuration manager instance
            recovery_dir: Directory for recovery state files
        """
        self.config_manager = config_manager
        self.recovery_dir = Path(recovery_dir or self._get_default_recovery_dir())
        self.recovery_dir.mkdir(parents=True, exist_ok=True)
        
        # Error tracking
        self.error_log: List[ErrorRecord] = []
        self.recovery_state: Optional[RecoveryState] = None
        self.error_log_file = self.recovery_dir / 'error_log.json'
        self.recovery_state_file = self.recovery_dir / 'recovery_state.json'
        
        # Load existing state
        self._load_error_log()
        self._load_recovery_state()
        
        logger.info(f"Error recovery system initialized: {self.recovery_dir}")
    
    def _get_default_recovery_dir(self) -> str:
        """Get default recovery directory"""
        if platform.system() == "Windows":
            return os.path.join(os.environ.get('APPDATA', ''), 'CAESER_Field_Data', 'recovery')
        else:
            return os.path.join(os.path.expanduser('~'), '.caeser_field_data', 'recovery')
    
    def with_retry(self, operation: Callable, max_retries: Optional[int] = None,
                   delay: Optional[float] = None, exponential_backoff: bool = True,
                   error_context: Dict[str, Any] = None) -> Tuple[Any, bool]:
        """
        Execute operation with retry logic and error recovery
        
        Args:
            operation: Function to execute
            max_retries: Maximum number of retries (uses config default if None)
            delay: Initial delay between retries (uses config default if None)
            exponential_backoff: Whether to use exponential backoff
            error_context: Additional context for error logging
            
        Returns:
            Tuple of (result, success)
        """
        config = self.config_manager.config.error_handling
        max_retries = max_retries if max_retries is not None else config.max_retries
        delay = delay if delay is not None else config.retry_delay_seconds
        exponential_backoff = exponential_backoff and config.exponential_backoff
        
        error_context = error_context or {}
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                result = operation()
                
                # If we had previous failures but this succeeded, log recovery
                if attempt > 0:
                    logger.info(f"Operation succeeded after {attempt} retries")
                    self._log_recovery_success(operation.__name__, attempt)
                
                return result, True
                
            except Exception as e:
                last_error = e
                error_category = self._classify_error(e)
                severity = self._determine_severity(e, error_category)
                
                # Log the error
                error_record = self._create_error_record(
                    e, error_category, severity, error_context, attempt
                )
                self._log_error(error_record)
                
                # Check if we should retry
                if attempt >= max_retries:
                    logger.error(f"Operation failed after {max_retries + 1} attempts: {e}")
                    break
                
                # Apply recovery strategy if available
                recovery_delay = self._apply_error_recovery_strategy(
                    error_category, severity, attempt
                )
                
                # Wait before retry
                retry_delay = delay
                if exponential_backoff:
                    retry_delay = delay * (2 ** attempt)
                
                total_delay = max(retry_delay, recovery_delay)
                
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {total_delay:.1f}s: {e}")
                time.sleep(total_delay)
        
        # All retries failed
        logger.error(f"All retry attempts exhausted for operation: {operation.__name__}")
        return None, False
    
    def _classify_error(self, error: Exception) -> ErrorCategory:
        """Classify error by type and characteristics"""
        error_message = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Network-related errors
        if any(keyword in error_message for keyword in [
            'connection', 'network', 'timeout', 'unreachable', 'dns', 'ssl', 'certificate'
        ]) or any(keyword in error_type for keyword in ['connection', 'timeout', 'ssl']):
            return ErrorCategory.NETWORK
        
        # Authentication errors
        if any(keyword in error_message for keyword in [
            'authentication', 'unauthorized', 'forbidden', 'credential', 'token', 'oauth'
        ]) or 'auth' in error_type:
            return ErrorCategory.AUTHENTICATION
        
        # File system errors
        if any(keyword in error_message for keyword in [
            'no such file', 'permission denied', 'access denied', 'file not found',
            'directory', 'disk full', 'no space'
        ]) or any(keyword in error_type for keyword in ['filenotfound', 'permission', 'oserror']):
            return ErrorCategory.FILESYSTEM if 'permission' not in error_message else ErrorCategory.PERMISSION
        
        # Data corruption
        if any(keyword in error_message for keyword in [
            'corrupt', 'invalid', 'malformed', 'parse', 'decode', 'xml', 'json'
        ]) or any(keyword in error_type for keyword in ['parse', 'decode', 'json', 'xml']):
            return ErrorCategory.DATA_CORRUPTION
        
        # Resource issues
        if any(keyword in error_message for keyword in [
            'memory', 'out of space', 'disk full', 'resource', 'quota'
        ]) or any(keyword in error_type for keyword in ['memory', 'resource']):
            return ErrorCategory.RESOURCE
        
        # Configuration issues
        if any(keyword in error_message for keyword in [
            'configuration', 'setting', 'config', 'parameter', 'invalid argument'
        ]):
            return ErrorCategory.CONFIGURATION
        
        return ErrorCategory.UNKNOWN
    
    def _determine_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Determine error severity"""
        error_message = str(error).lower()
        
        # Fatal errors that require immediate attention
        if any(keyword in error_message for keyword in [
            'system error', 'critical', 'fatal', 'corrupted system'
        ]):
            return ErrorSeverity.FATAL
        
        # High severity by category
        if category in [ErrorCategory.AUTHENTICATION, ErrorCategory.CONFIGURATION]:
            return ErrorSeverity.HIGH
        
        # High severity for certain file system errors
        if category == ErrorCategory.FILESYSTEM and any(keyword in error_message for keyword in [
            'disk full', 'no space', 'corrupted'
        ]):
            return ErrorSeverity.HIGH
        
        # Medium severity for network and permission issues
        if category in [ErrorCategory.NETWORK, ErrorCategory.PERMISSION, ErrorCategory.RESOURCE]:
            return ErrorSeverity.MEDIUM
        
        # Data corruption varies
        if category == ErrorCategory.DATA_CORRUPTION:
            if any(keyword in error_message for keyword in [
                'metadata', 'header', 'structure'
            ]):
                return ErrorSeverity.MEDIUM
            else:
                return ErrorSeverity.LOW
        
        return ErrorSeverity.LOW
    
    def _create_error_record(self, error: Exception, category: ErrorCategory,
                           severity: ErrorSeverity, context: Dict[str, Any],
                           retry_count: int) -> ErrorRecord:
        """Create error record"""
        return ErrorRecord(
            timestamp=datetime.now().isoformat(),
            error_id=f"{category.value}_{int(time.time())}_{retry_count}",
            category=category,
            severity=severity,
            message=str(error),
            traceback=traceback.format_exc(),
            context=context,
            retry_count=retry_count
        )
    
    def _log_error(self, error_record: ErrorRecord):
        """Log error record"""
        self.error_log.append(error_record)
        
        # Save to file if enabled
        if self.config_manager.config.error_handling.save_error_logs:
            self._save_error_log()
        
        # Log to system logger
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.FATAL: logging.CRITICAL
        }.get(error_record.severity, logging.ERROR)
        
        logger.log(log_level, f"[{error_record.category.value.upper()}] {error_record.message}")
    
    def _apply_error_recovery_strategy(self, category: ErrorCategory, 
                                     severity: ErrorSeverity, attempt: int) -> float:
        """
        Apply recovery strategy based on error type
        
        Returns:
            Additional delay required for recovery
        """
        recovery_delay = 0.0
        
        try:
            if category == ErrorCategory.NETWORK:
                # Network recovery: Progressive delays
                recovery_delay = min(30.0, 5.0 * (attempt + 1))
                if attempt > 2:
                    # Check network connectivity
                    self._check_network_connectivity()
            
            elif category == ErrorCategory.FILESYSTEM:
                # File system recovery: Check disk space, permissions
                recovery_delay = 2.0
                self._check_filesystem_health()
            
            elif category == ErrorCategory.AUTHENTICATION:
                # Auth recovery: Clear caches, re-authenticate
                recovery_delay = 10.0
                if attempt == 0:  # Only try once
                    self._attempt_authentication_recovery()
            
            elif category == ErrorCategory.RESOURCE:
                # Resource recovery: Cleanup, free resources
                recovery_delay = 5.0
                self._attempt_resource_cleanup()
            
            elif category == ErrorCategory.DATA_CORRUPTION:
                # Data corruption: Skip file, continue with others
                recovery_delay = 1.0
                logger.warning("Data corruption detected, will skip corrupted file")
            
        except Exception as e:
            logger.warning(f"Error during recovery strategy application: {e}")
        
        return recovery_delay
    
    def _check_network_connectivity(self):
        """Check basic network connectivity"""
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            logger.info("Network connectivity check passed")
        except Exception as e:
            logger.warning(f"Network connectivity check failed: {e}")
    
    def _check_filesystem_health(self):
        """Check file system health and available space"""
        try:
            # Check available disk space
            import shutil
            total, used, free = shutil.disk_usage(self.recovery_dir)
            free_gb = free / (1024**3)
            
            if free_gb < 1.0:  # Less than 1GB free
                logger.warning(f"Low disk space: {free_gb:.1f} GB available")
            else:
                logger.debug(f"Disk space check passed: {free_gb:.1f} GB available")
                
        except Exception as e:
            logger.warning(f"Filesystem health check failed: {e}")
    
    def _attempt_authentication_recovery(self):
        """Attempt to recover authentication"""
        try:
            # This would integrate with the Google service account handler
            logger.info("Attempting authentication recovery...")
            # Implementation would depend on the specific authentication system
            
        except Exception as e:
            logger.warning(f"Authentication recovery failed: {e}")
    
    def _attempt_resource_cleanup(self):
        """Attempt to free up resources"""
        try:
            # Clean up temporary files
            import gc
            gc.collect()
            
            # Clean up old error logs
            self._cleanup_old_error_logs()
            
            logger.info("Resource cleanup completed")
            
        except Exception as e:
            logger.warning(f"Resource cleanup failed: {e}")
    
    def _log_recovery_success(self, operation: str, attempts: int):
        """Log successful recovery"""
        logger.info(f"Operation '{operation}' recovered successfully after {attempts} attempts")
    
    def save_recovery_state(self, state: Dict[str, Any]):
        """Save recovery state for crash recovery"""
        try:
            self.recovery_state = RecoveryState(
                last_successful_operation=state.get('operation', ''),
                partial_processing_data=state.get('data', {}),
                failed_files=state.get('failed_files', []),
                completed_files=state.get('completed_files', []),
                recovery_checkpoint=datetime.now().isoformat()
            )
            
            with open(self.recovery_state_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.recovery_state), f, indent=2)
            
            logger.debug("Recovery state saved")
            
        except Exception as e:
            logger.error(f"Error saving recovery state: {e}")
    
    def load_recovery_state(self) -> Optional[RecoveryState]:
        """Load recovery state for crash recovery"""
        return self.recovery_state
    
    def clear_recovery_state(self):
        """Clear recovery state after successful completion"""
        try:
            if self.recovery_state_file.exists():
                self.recovery_state_file.unlink()
            
            self.recovery_state = None
            logger.debug("Recovery state cleared")
            
        except Exception as e:
            logger.warning(f"Error clearing recovery state: {e}")
    
    def _load_error_log(self):
        """Load error log from file"""
        try:
            if self.error_log_file.exists():
                with open(self.error_log_file, 'r', encoding='utf-8') as f:
                    error_data = json.load(f)
                
                # Reconstruct error records
                self.error_log = []
                for record_data in error_data:
                    record_data['category'] = ErrorCategory(record_data['category'])
                    record_data['severity'] = ErrorSeverity(record_data['severity'])
                    self.error_log.append(ErrorRecord(**record_data))
                
                logger.debug(f"Loaded {len(self.error_log)} error records")
                
        except Exception as e:
            logger.warning(f"Error loading error log: {e}")
            self.error_log = []
    
    def _load_recovery_state(self):
        """Load recovery state from file"""
        try:
            if self.recovery_state_file.exists():
                with open(self.recovery_state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                
                self.recovery_state = RecoveryState(**state_data)
                logger.debug("Recovery state loaded")
                
        except Exception as e:
            logger.warning(f"Error loading recovery state: {e}")
            self.recovery_state = None
    
    def _save_error_log(self):
        """Save error log to file"""
        try:
            # Convert to serializable format
            error_data = []
            for record in self.error_log:
                record_dict = asdict(record)
                record_dict['category'] = record.category.value
                record_dict['severity'] = record.severity.value
                error_data.append(record_dict)
            
            with open(self.error_log_file, 'w', encoding='utf-8') as f:
                json.dump(error_data, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.warning(f"Error saving error log: {e}")
    
    def _cleanup_old_error_logs(self):
        """Clean up old error log entries"""
        try:
            retention_days = self.config_manager.config.error_handling.error_log_retention_days
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            original_count = len(self.error_log)
            self.error_log = [
                record for record in self.error_log
                if datetime.fromisoformat(record.timestamp) > cutoff_date
            ]
            
            cleaned_count = original_count - len(self.error_log)
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old error log entries")
                self._save_error_log()
                
        except Exception as e:
            logger.warning(f"Error cleaning up old error logs: {e}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics"""
        try:
            stats = {
                'total_errors': len(self.error_log),
                'by_category': {},
                'by_severity': {},
                'recent_errors': 0,
                'recovery_success_rate': 0.0
            }
            
            # Count by category and severity
            for record in self.error_log:
                category = record.category.value
                severity = record.severity.value
                
                stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
                stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1
            
            # Count recent errors (last 24 hours)
            recent_cutoff = datetime.now() - timedelta(hours=24)
            stats['recent_errors'] = len([
                record for record in self.error_log
                if datetime.fromisoformat(record.timestamp) > recent_cutoff
            ])
            
            # Calculate recovery success rate
            recovery_attempts = [r for r in self.error_log if r.recovery_attempted]
            if recovery_attempts:
                successful = len([r for r in recovery_attempts if r.recovery_successful])
                stats['recovery_success_rate'] = successful / len(recovery_attempts) * 100
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting error statistics: {e}")
            return {'error': str(e)}
    
    def export_error_report(self, output_path: str) -> bool:
        """Export comprehensive error report"""
        try:
            report = {
                'export_timestamp': datetime.now().isoformat(),
                'system_info': {
                    'platform': platform.system(),
                    'python_version': platform.python_version(),
                    'recovery_dir': str(self.recovery_dir)
                },
                'statistics': self.get_error_statistics(),
                'recovery_state': asdict(self.recovery_state) if self.recovery_state else None,
                'error_log': []
            }
            
            # Add error records
            for record in self.error_log:
                record_dict = asdict(record)
                record_dict['category'] = record.category.value
                record_dict['severity'] = record.severity.value
                report['error_log'].append(record_dict)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Error report exported: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting error report: {e}")
            return False