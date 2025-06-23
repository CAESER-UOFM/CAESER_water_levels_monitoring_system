from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QLineEdit, QMessageBox, QFormLayout,
                           QDialogButtonBox, QGroupBox, QTableWidget, QTableWidgetItem,
                           QComboBox, QHeaderView, QWidget)
from PyQt5.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

class UserManagementDialog(QDialog):
    """Dialog for managing users"""
    
    def __init__(self, user_auth_service, parent=None):
        super().__init__(parent)
        self.user_auth_service = user_auth_service
        self.setWindowTitle("User Management")
        self.resize(600, 400)
        self.setModal(True)
        self.setup_ui()
        self.load_users()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("User Management")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Users table
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(4)
        self.users_table.setHorizontalHeaderLabels(["Username", "Name", "Role", "Actions"])
        self.users_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.users_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.users_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.users_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.users_table.verticalHeader().setVisible(False)
        layout.addWidget(self.users_table)
        
        # Add user group
        add_user_group = QGroupBox("Add New User")
        add_user_layout = QFormLayout(add_user_group)
        
        self.new_username_edit = QLineEdit()
        self.new_username_edit.setPlaceholderText("Enter username")
        add_user_layout.addRow("Username:", self.new_username_edit)
        
        self.new_password_edit = QLineEdit()
        self.new_password_edit.setPlaceholderText("Enter password")
        self.new_password_edit.setEchoMode(QLineEdit.Password)
        add_user_layout.addRow("Password:", self.new_password_edit)
        
        self.new_name_edit = QLineEdit()
        self.new_name_edit.setPlaceholderText("Enter display name")
        add_user_layout.addRow("Name:", self.new_name_edit)
        
        self.new_role_combo = QComboBox()
        self.new_role_combo.addItems(["admin", "tech"])
        add_user_layout.addRow("Role:", self.new_role_combo)
        
        add_user_btn = QPushButton("Add User")
        add_user_btn.clicked.connect(self.add_user)
        add_user_layout.addRow("", add_user_btn)
        
        layout.addWidget(add_user_group)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_users(self):
        """Load users into the table"""
        users = self.user_auth_service.get_all_users()
        self.users_table.setRowCount(len(users))
        
        for row, user in enumerate(users):
            # Username
            username_item = QTableWidgetItem(user["username"])
            username_item.setFlags(username_item.flags() & ~Qt.ItemIsEditable)
            self.users_table.setItem(row, 0, username_item)
            
            # Name
            name_item = QTableWidgetItem(user["name"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.users_table.setItem(row, 1, name_item)
            
            # Role
            role_item = QTableWidgetItem(user["role"])
            role_item.setFlags(role_item.flags() & ~Qt.ItemIsEditable)
            self.users_table.setItem(row, 2, role_item)
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(2)
            
            edit_btn = QPushButton("Edit")
            edit_btn.setProperty("username", user["username"])
            edit_btn.clicked.connect(self.edit_user)
            
            delete_btn = QPushButton("Delete")
            delete_btn.setProperty("username", user["username"])
            delete_btn.clicked.connect(self.delete_user)
            
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            
            self.users_table.setCellWidget(row, 3, actions_widget)
        
        self.users_table.resizeColumnsToContents()
    
    def add_user(self):
        """Add a new user"""
        username = self.new_username_edit.text().strip()
        password = self.new_password_edit.text()
        name = self.new_name_edit.text().strip()
        role = self.new_role_combo.currentText()
        
        if not username or not password or not name:
            QMessageBox.warning(self, "Input Error", "All fields are required")
            return
        
        success, message = self.user_auth_service.add_user(username, password, name, role)
        
        if success:
            QMessageBox.information(self, "Success", message)
            self.new_username_edit.clear()
            self.new_password_edit.clear()
            self.new_name_edit.clear()
            self.load_users()
        else:
            QMessageBox.warning(self, "Error", message)
    
    def edit_user(self):
        """Edit an existing user"""
        sender = self.sender()
        username = sender.property("username")
        
        dialog = EditUserDialog(self.user_auth_service, username, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_users()
    
    def delete_user(self):
        """Delete a user"""
        sender = self.sender()
        username = sender.property("username")
        
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete user '{username}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, message = self.user_auth_service.delete_user(username)
            
            if success:
                QMessageBox.information(self, "Success", message)
                self.load_users()
            else:
                QMessageBox.warning(self, "Error", message)


class EditUserDialog(QDialog):
    """Dialog for editing a user"""
    
    def __init__(self, user_auth_service, username, parent=None):
        super().__init__(parent)
        self.user_auth_service = user_auth_service
        self.username = username
        self.setWindowTitle(f"Edit User: {username}")
        self.resize(400, 200)
        self.setModal(True)
        self.setup_ui()
        self.load_user()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Form
        form_layout = QFormLayout()
        
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Enter new password (leave empty to keep current)")
        self.password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Password:", self.password_edit)
        
        self.name_edit = QLineEdit()
        form_layout.addRow("Name:", self.name_edit)
        
        self.role_combo = QComboBox()
        self.role_combo.addItems(["admin", "tech"])
        form_layout.addRow("Role:", self.role_combo)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_user)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_user(self):
        """Load user data"""
        users = self.user_auth_service.get_all_users()
        user = next((u for u in users if u["username"] == self.username), None)
        
        if user:
            self.name_edit.setText(user["name"])
            self.role_combo.setCurrentText(user["role"])
    
    def save_user(self):
        """Save user changes"""
        password = self.password_edit.text() or None
        name = self.name_edit.text().strip()
        role = self.role_combo.currentText()
        
        if not name:
            QMessageBox.warning(self, "Input Error", "Name is required")
            return
        
        success, message = self.user_auth_service.update_user(
            self.username, password, name, role
        )
        
        if success:
            QMessageBox.information(self, "Success", message)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", message) 