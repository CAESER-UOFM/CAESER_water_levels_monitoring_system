import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox, QDialogButtonBox,
    QFormLayout, QGroupBox
)
from PyQt5.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

class EditUserDialog(QDialog):
    """Dialog for editing user credentials or adding a new user"""
    
    def __init__(self, username=None, parent=None):
        super().__init__(parent)
        
        # Store username (None for new user)
        self.username = username
        self.is_new_user = (username is None)
        
        # Set up UI
        self.setup_ui()
        
        # Load user data if editing an existing user
        if not self.is_new_user:
            self.load_user_data()
    
    def setup_ui(self):
        """Set up the dialog UI"""
        if self.is_new_user:
            self.setWindowTitle("Add New User")
        else:
            self.setWindowTitle(f"Edit User: {self.username}")
            
        self.setMinimumWidth(400)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Create form group
        form_group = QGroupBox("User Information")
        form_layout = QFormLayout(form_group)
        
        # Username field
        self.username_edit = QLineEdit()
        if not self.is_new_user:
            self.username_edit.setText(self.username)
            self.username_edit.setReadOnly(True)
        form_layout.addRow("Username:", self.username_edit)
        
        # Display name field
        self.display_name_edit = QLineEdit()
        form_layout.addRow("Display Name:", self.display_name_edit)
        
        # Password field
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Password:", self.password_edit)
        
        # Confirm password field
        self.confirm_password_edit = QLineEdit()
        self.confirm_password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Confirm Password:", self.confirm_password_edit)
        
        layout.addWidget(form_group)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_user)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_user_data(self):
        """Load user data from the users.json file"""
        try:
            config_dir = Path.cwd() / "config"
            users_file = config_dir / "users.json"
            
            if users_file.exists():
                with open(users_file, 'r') as f:
                    user_data = json.load(f)
                
                # Find the user with matching username
                for user in user_data.get('users', []):
                    if user.get('username') == self.username:
                        # Set display name in the form
                        self.display_name_edit.setText(user.get('display_name', ''))
                        return
            
            # If we get here, user wasn't found
            logger.warning(f"User '{self.username}' not found in users.json")
            QMessageBox.warning(self, "User Not Found", f"The user '{self.username}' was not found in the users file.")
            
        except Exception as e:
            logger.error(f"Error loading user data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load user data: {str(e)}")
    
    def save_user(self):
        """Save the user data to users.json"""
        # Validate inputs
        username = self.username_edit.text().strip()
        display_name = self.display_name_edit.text().strip()
        password = self.password_edit.text()
        confirm_password = self.confirm_password_edit.text()
        
        # Check required fields
        if not username:
            QMessageBox.warning(self, "Input Error", "Username is required.")
            return
        
        if not display_name:
            display_name = username  # Default to username if display name is empty
        
        # Check if new password is provided or we're creating a new user
        if self.is_new_user and not password:
            QMessageBox.warning(self, "Input Error", "Password is required for new users.")
            return
            
        # Check password confirmation if password is provided
        if password and password != confirm_password:
            QMessageBox.warning(self, "Input Error", "Passwords do not match.")
            return
        
        try:
            # Load existing users
            config_dir = Path.cwd() / "config"
            users_file = config_dir / "users.json"
            
            user_data = {"users": []}
            if users_file.exists():
                with open(users_file, 'r') as f:
                    user_data = json.load(f)
            
            # Find the user if editing, or check if username already exists for new user
            user_found = False
            for i, user in enumerate(user_data.get('users', [])):
                if user.get('username') == username:
                    user_found = True
                    
                    # Update existing user
                    user_data['users'][i]['display_name'] = display_name
                    
                    # Only update password if a new one is provided
                    if password:
                        user_data['users'][i]['password'] = password
                        
                    break
            
            # If not found and adding a new user
            if not user_found and self.is_new_user:
                # Check if the username is already taken (should not happen due to validation above)
                for user in user_data.get('users', []):
                    if user.get('username') == username:
                        QMessageBox.warning(self, "Username Taken", 
                                          f"The username '{username}' is already taken. Please choose a different username.")
                        return
                
                # Add new user
                user_data['users'].append({
                    'username': username,
                    'password': password,
                    'display_name': display_name
                })
            
            # Create config directory if it doesn't exist
            config_dir.mkdir(exist_ok=True)
            
            # Save the updated user data
            with open(users_file, 'w') as f:
                json.dump(user_data, f, indent=2)
            
            logger.info(f"User '{username}' {'added' if self.is_new_user else 'updated'} successfully")
            QMessageBox.information(self, "Success", 
                                  f"User '{username}' {'added' if self.is_new_user else 'updated'} successfully.")
            
            # Close the dialog
            self.accept()
            
        except Exception as e:
            logger.error(f"Error saving user data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save user data: {str(e)}")
