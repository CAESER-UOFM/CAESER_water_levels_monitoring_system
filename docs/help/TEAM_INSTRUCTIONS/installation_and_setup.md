# 🚀 CAESER Water Levels - Installation & Setup Guide

## 💻 Installation Steps

### 📁 Step 1: Get the Installation Files

#### 🏢 **Option A: Smoo Shared Drive** (Recommended)
```
📂 Go to: S:\Water_Projects\CAESER\Water_Data_Series\Water_levels_monitoring_system
```

#### 🌐 **Option B: GitHub Download** (No Smoo Access)
```
🔗 Download from: https://github.com/CAESER-UOFM/CAESER_water_levels_monitoring_system
📥 Click "Code" → "Download ZIP"
📂 Extract to your preferred location
```

### 🖱️ Step 2: Run Windows Installer
1. 🖱️ **Double-click** `windows_installer`
2. 💻 **Terminal will open** - just press `Enter`
3. ⏳ **Python and environment** will install automatically
4. 📂 **Installation location**: `C:\Users\[your-user]\CAESER_Water_levels_monitoring_system`

### 🚀 Step 3: Launch the App
- 🖱️ **Normal launch**: Click `"CAESER Water Levels Monitoring"` shortcut
- 🐛 **Debug mode**: Open `"water_levels_monitoring_system_debug"` from launchers folder

---

## 🔐 First Launch Setup

### 👤 Initial Login
```
🔑 Username: admin
🔑 Password: admin
```

### 👥 Create Your User Account
1. 📋 Go to **Menu Bar** → **User** → **Manage Users**
2. ➕ **Add new user** for yourself
3. 🎯 **Purpose**: Helps us track feedback system usage

---

## ☁️ Google Drive Credentials Setup

### 🔧 Method 1: During First Launch
- 📁 **Load file**: `google_drive_credentials.json`
- 📂 **Location**: `S:\Water_Projects\CAESER\Water_Data_Series\Water_levels_monitoring_system\config`

### ⚙️ Method 2: Through Settings
1. 🚀 Go to **Settings** if you missed it during first launch
2. 📁 **Add credentials** in the credentials section
3. 🔗 **No Smoo access?** Use the link provided in credentials section (special permission needed)

---

## 🌐 MONET Integration

### 🔑 Add MONET Credentials
- 📍 **Location**: Settings section
- 👤 **Required**: Authorized MONET user credentials
- 🎯 **Purpose**: Enables MONET connectivity

---

## 🗄️ Database System Overview

### 📊 Database Types

#### ☁️ **Cloud Databases**
- 🔄 **Working mode**: Local with tracking system
- 📂 **Storage location**: `databases/temp` folder
- 🔄 **Sync behavior**: Manual upload to cloud
- 📈 **Tracking**: Changes tracked in Drive

#### 💻 **Local Databases**
- 📂 **Storage location**: `databases` folder (direct)
- 🔧 **Creation**: New databases created here
- 🏠 **Usage**: Purely local, no cloud sync

### 🔄 Cloud Database Workflow

#### 📥 **Download & Modify**
1. 📱 **Download** cloud database
2. ✏️ **Modify locally** (won't sync automatically)
3. 📤 **Upload manually** to sync changes

#### 🛡️ **Backup System**
- 💾 **Auto-backup**: Last 2 modified databases
- 🔄 **Change tracking**: All changes tracked in Drive
- 📋 **Recovery**: Available if information is lost

#### 💾 **Draft System**
- 🚨 **Scenario**: Close app without uploading changes
- 🔄 **Auto-save**: System creates draft automatically
- 🧪 **Testing**: Please try this system out!

---

## 💬 Feedback Systems Overview

### 1. 📢 **General Feedback** (Main Window)
- 🎯 **Purpose**: Report bugs and app improvements
- 💾 **Storage**: Saved in Drive
- 📋 **Requirement**: Drive credentials must be set

### 2. 🚩 **User Flag Comments** (Water Levels Tab)
- 📍 **Access**: Water Levels Tab → User Flag Management
- 🎯 **Purpose**: Track problems with well data
- 💾 **Storage**: Saved in database

### 3. 📋 **Protocol Changes** (Edit Water Levels Dialog)
- 📍 **Access**: Water Levels Tab → Edit Water Levels Dialog
- 🎯 **Purpose**: Suggest water level data processing improvements
- 💾 **Storage**: Saved in Drive
- 📝 **Use case**: Share processing insights with team

### 4. 📝 **Well Notes** (Edit Water Levels Dialog)
- 📍 **Access**: Water Levels Tab → Edit Water Levels Dialog
- 🎯 **Purpose**: Track water level behaviors (jumps, patterns, etc.)
- 💾 **Storage**: Saved in database
- 📊 **Focus**: Data behavior, not protocols or errors

---

## 📊 Recharge Tab Features

### 🔬 **Available Methods**
- 🌊 **RISE Method**: Water table fluctuation approach
- 📈 **MRC Method**: Master recession curve analysis

### 🧪 **Testing Encouraged**
- 🎮 **Play around** with both methods
- 💡 **Suggestions welcome** for improvements
- 🔬 **Test everything** - don't worry about mistakes!

---

## 🧪 Testing & Experimentation

### 🎯 **Safe Testing Approach**
1. 📥 **Download** a cloud database
2. 🔬 **Play and modify** without uploading
3. 🧪 **Test all features** - experiment freely!
4. 🚫 **Don't upload** test changes

### 🛡️ **Mistake Recovery**
- 😅 **Uploaded by mistake?** Don't worry!
- 🔄 **Backup system** will help recover
- 💾 **2 database backups** always available
- 🔍 **Change tracking** in Drive for recovery

---

## 🎉 You're All Set!

### 🔄 **Next Steps**
1. 🔧 **Complete setup** following this guide
2. 👤 **Create your user account**
3. ☁️ **Set up Drive credentials**
4. 🧪 **Download a test database**
5. 🎮 **Experiment with features**
6. 💬 **Use feedback systems** to share insights
7. 📊 **Try recharge calculations**

### 💡 **Remember**
- 🧪 **Test freely** - backups protect you
- 💬 **Share feedback** - help improve the system
- 🤝 **Ask questions** - team support is available
- 🔄 **Experiment** - learn by doing!

---

## 📚 Need More Help?

### 🔍 **Built-in Help System**
The app includes a comprehensive help system with detailed information:

#### 🚀 **How to Access Help**
1. 🖱️ **Click Help button** in any tab
2. 🔍 **Search for topics** using the search box
3. 📖 **Browse sections**:
   - 🚀 **Quick Start** - Getting started tutorials
   - ⚙️ **How It Works** - Technical details
   - 📊 **Application Tabs** - Feature guides
   - 🔧 **System Features** - Feedback systems, Master Baro concept
   - 🔬 **Advanced Topics** - Recharge calculations, cloud collaboration
   - 🔧 **Troubleshooting** - Common issues and solutions

#### 🎯 **Featured Help Topics**
- 💬 **System Feedback & Documentation** - Complete guide to all feedback mechanisms
- 🌡️ **Master Baro Concept** - Understanding atmospheric pressure compensation
- 🚩 **User Flag Comments** - Quality control workflow
- 📋 **Protocol & Well Notes** - Documentation best practices

#### 💡 **Pro Tips**
- 🎯 **Context-sensitive help** available in most dialogs
- 📖 **Hover tooltips** on buttons and fields
- 🔍 **Search function** finds topics quickly
- 📚 **Step-by-step guides** for complex workflows

---

**🚀 Ready to start monitoring groundwater? Have fun exploring the system!** 🌊📊

*💡 **Pro Tip**: Start with downloading a cloud database and testing features before working with real data. Use the built-in help system for detailed guidance on any feature!*