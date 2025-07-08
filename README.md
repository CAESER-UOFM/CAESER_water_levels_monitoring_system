<div align="center">

# CAESER Water Levels Monitoring System

<img src="src/gui/icons/app_icon.webp" alt="CAESER Mascot" width="200">

**Professional water level data processing and analysis**

[![Download Latest](https://img.shields.io/badge/Download-Latest%20Version-success?style=for-the-badge&logo=download)](../../archive/refs/heads/main.zip)

<!-- Navigation Menu -->
<a id="navigation-menu"></a>
<table width="100%">
<tr>
<td align="center"><a href="#-quick-install"><b>🚀 Quick Install</b></a></td>
<td align="center"><a href="#-features"><b>📊 Features</b></a></td>
<td align="center"><a href="#-getting-started"><b>🎯 Getting Started</b></a></td>
<td align="center"><a href="#-integration"><b>🌐 Integration</b></a></td>
<td align="center"><a href="#-support"><b>💬 Support</b></a></td>
</tr>
<tr>
<td align="center"><small>2-minute setup</small></td>
<td align="center"><small>What it does</small></td>
<td align="center"><small>First steps</small></td>
<td align="center"><small>Connect systems</small></td>
<td align="center"><small>Get help</small></td>
</tr>
</table>

<!-- Quick Action Buttons -->
<div align="center">

**🎯 Most Common Actions:**

[![📥 Download](https://img.shields.io/badge/📥-Download_Now-success?style=flat-square)](../../archive/refs/heads/main.zip) 
[![❓ Help](https://img.shields.io/badge/❓-Get_Help-red?style=flat-square)](#-support)

---

<details>
<summary><b>📋 Table of Contents - Quick Jump Menu</b></summary>

### 🚀 Installation & Setup
- [📥 Quick Install](#-quick-install)
  - [Download Options](#step-1-download)
  - [🖥️ Windows Unblock Instructions](#-windows-users---critical-first-step)
  - [Installation Steps](#step-2-install)
  - [Launch Application](#step-3-launch)

### 📖 Using the Application  
- [📊 Features Overview](#-features)
- [🎯 Getting Started](#-getting-started)
  - [🆕 First Time Users](#-first-time-users---5-minute-tutorial)
  - [🎓 Different User Types](#-for-different-user-types)

### 🔌 Advanced Topics
- [🌐 Integration](#-integration)
- [💬 Support & Help](#-support)

### 📄 Additional Resources
- All installation and setup instructions are included in this README
- Scroll down for complete Windows, macOS, and Linux instructions
- Use the navigation menu above for quick access to any section

</details>

</div>

</div>

---

Desktop application for processing water level data from Solinst loggers with automated barometric compensation, recharge calculations, and team collaboration.

<details>
<summary><h2>🚀 Quick Install</h2></summary>

*🏠 [Home](#navigation-menu) > 🚀 Installation*

### Step 1: Download
<div align="center">

**🎯 Easiest Way: Direct Download**

[![Download ZIP](https://img.shields.io/badge/📁_Download_ZIP-Latest_Version-success?style=for-the-badge&logo=download)](../../archive/refs/heads/main.zip)

*Click the badge above → ZIP file downloads automatically*

> **🖥️ Windows Users:** You'll need to "unblock" the windows_installer.bat file before running it. 
> [See detailed instructions below](#step-2-install) for complete step-by-step guidance.

</div>

**Alternative: Clone Repository**
```bash
git clone https://github.com/CAESER-UOFM/water-levels-monitoring.git
```

### Step 2: Install

#### **🖥️ Windows Users - Critical First Step!**

> **⚠️ WINDOWS SECURITY REQUIREMENT**
> 
> **Before running setup.bat, you MUST unblock it first:**
> 
> 1. **Right-click** `setup.bat` → **Properties**
> 2. Check **"Unblock"** ✅ → Click **"OK"**  
> 3. **Then** double-click `setup.bat`
>
> **🎯 Need help?** → Follow the detailed steps below
>
> ```
> Right-click setup.bat → Properties → ✅ Unblock → OK → Double-click
> ```

**Why this happens:** Windows blocks ALL downloaded files for security. This is normal and required for any software downloaded from the internet.

```bash
# After unblocking:
Double-click: setup.bat

# macOS/Linux Users  
chmod +x setup.sh && ./setup.sh
```

### Step 3: Launch
```bash
# Look for these files in your installation directory:
# Windows: water_levels_app.bat
# macOS/Linux: water_levels_app.command
```

**✅ No admin rights needed • ✅ Portable installation • ✅ Works on restricted networks**

> **🖥️ Windows Users:** All setup instructions are included above with detailed steps

</details>

---

<details>
<summary><h2>📊 Features</h2></summary>

*🏠 [Home](#navigation-menu) > 📊 Features* | <div align="right"><a href="#navigation-menu">⬆️ Back to Top</a></div>

<table>
<tr>
<td width="50%">

### 🔧 **Data Processing**
- **Solinst Integration** - Native XLE/LEV support
- **Barometric Compensation** - Automatic atmospheric correction
- **Quality Control** - Smart data validation and flagging
- **Batch Processing** - Drag & drop multiple files

</td>
<td width="50%">

### 📈 **Analysis & Visualization**
- **Recharge Calculations** - RISE, MRC, and ERC methods
- **Interactive Maps** - Well locations with live data
- **Custom Exports** - Publication-ready plots and data
- **Web Visualizer** - Mobile-friendly field access

</td>
</tr>
<tr>
<td width="50%">

### ☁️ **Collaboration**
- **Google Drive Sync** - Seamless team collaboration
- **Conflict Resolution** - Smart handling of concurrent edits
- **Multi-user Access** - Role-based permissions
- **Real-time Updates** - Live data synchronization

</td>
<td width="50%">

### 🔌 **Integration**
- **MONET Telemetry** - Real-time monitoring data
- **Manual Readings** - Field measurement integration
- **External APIs** - Connect with other monitoring systems
- **Custom Sensors** - Modular architecture for expansion

</td>
</tr>
</table>

</details>

<details>
<summary><h2>🎯 Getting Started</h2></summary>

<div align="right"><a href="#navigation-menu">⬆️ Back to Top</a></div>

<details>
<summary><b>🆕 First Time Users - 5 Minute Tutorial</b></summary>

### Quick Workflow
1. **🚀 Launch** the app and create a user account
2. **📊 Import barologger data** (atmospheric pressure - trust us on this)
3. **💧 Import your water level XLE files**
4. **✨ Watch automatic barometric compensation** happen
5. **📈 Calculate recharge estimates** and export results

### Application Structure
| Tab | What It Does | When To Use |
|-----|--------------|-------------|
| **🗄️ Database** | Map view and data management | Overview of your monitoring network |
| **🌡️ Barologger** | Atmospheric pressure import | Before processing water levels |
| **💧 Water Level** | Main data processing | Your primary workspace |
| **📊 Recharge** | Calculate recharge rates | Analysis and reporting |
| **🏃 Runs** | Field campaign tracking | Managing field work |

</details>

<details>
<summary><b>🎓 For Different User Types</b></summary>

### **CAESER Team Members**
- **Full cloud sync** with shared research databases
- **Multi-site collaboration** across monitoring locations
- **MONET integration** for telemetry data
- *Contact maintainer for Google Drive credentials*

### **Independent Researchers**
- **Complete local functionality** - no cloud required
- **Custom Google Drive setup** for your own team collaboration
- **Modular sensor support** - easy to adapt for different equipment

### **Universities & Institutions**
- **No admin rights required** - perfect for restricted networks
- **Portable installation** - runs from user directories
- **Batch processing** - handle large datasets efficiently

</details>

---

</details>

<details>
<summary><h2>🌐 Integration</h2></summary>

<div align="right"><a href="#navigation-menu">⬆️ Back to Top</a></div>

<div align="center">

### Supported Data Sources

| **Sensors** | **Telemetry** | **Manual Data** | **Cloud Storage** |
|-------------|---------------|-----------------|-------------------|
| Solinst XLE/LEV | MONET | CSV Import | Google Drive |
| Campbell Scientific* | MonitorMyWatershed | Field readings | Custom APIs |
| In-Situ* | Custom APIs | Quality validation | Real-time sync |

*Coming soon*

</div>

**Integration Examples:**
- **Research Networks:** Connect with CAESER's larger well database
- **Regulatory Reporting:** Export to agency-required formats  
- **GIS Systems:** Compatible with ArcGIS and QGIS workflows
- **Web Visualization:** Mobile-friendly data access for field teams

---

</details>

<details>
<summary><h2>💬 Support</h2></summary>

<div align="right"><a href="#navigation-menu">⬆️ Back to Top</a></div>

<div align="center">

### **Get Help When You Need It**

| **Type** | **Resource** | **Best For** |
|----------|--------------|--------------|
| 📖 **Built-in Help** | Help button in app | Step-by-step guidance |
| 🐛 **Issues** | [GitHub Issues](../../issues) | Bug reports & feature requests |
| 💬 **Discussions** | [GitHub Discussions](../../discussions) | Questions & tips |
| 👥 **CAESER Network** | Contact maintainer | Research collaboration |

</div>

<details>
<summary><b>📋 System Requirements</b></summary>

### **Operating System**
- **Windows:** 10 or later
- **macOS:** 10.14 (Mojave) or later  
- **Linux:** Ubuntu 18.04+ or equivalent

### **Hardware**
- **RAM:** 4GB minimum, 8GB+ recommended for large datasets
- **Storage:** 2GB free space for installation
- **Internet:** Optional (only needed for updates and cloud features)

### **Institutional Requirements**
✅ **No administrator rights required**  
✅ **Runs on restricted networks**  
✅ **Portable installation**  
✅ **No system registry modifications**

</details>

---

</details>

<div align="center">

## 🚀 **Ready to Start?**

**Transform your water level monitoring workflow today**

[![Download Now](https://img.shields.io/badge/📥_Download_Now-Get_Started-success?style=for-the-badge&logo=download)](../../archive/refs/heads/main.zip)

### **What happens next?**
1. **Download** takes 30 seconds
2. **Installation** takes 2 minutes  
3. **First analysis** in under 5 minutes

*Professional groundwater monitoring. No complexity.*

---

**Built by the [CAESER Research Group](https://caeser.memphis.edu) at the University of Memphis**

---

<!-- Quick Navigation Footer -->
<details>
<summary><b>🔗 Quick Links & Navigation</b></summary>

<table width="100%">
<tr>
<th colspan="4">📱 Quick Actions</th>
</tr>
<tr>
<td align="center">
<a href="../../archive/refs/heads/main.zip"><b>📥 Download</b></a><br>
<small>Get latest version</small>
</td>
<td align="center">
<a href="#-quick-install"><b>🚀 Setup Guide</b></a><br>
<small>Installation steps</small>
</td>
<td align="center">
<a href="#-getting-started"><b>🎯 Getting Started</b></a><br>
<small>First steps</small>
</td>
<td align="center">
<a href="../../issues"><b>❓ Get Help</b></a><br>
<small>Report issues</small>
</td>
</tr>
</table>

<table width="100%">
<tr>
<th colspan="5">🧭 Page Navigation</th>
</tr>
<tr>
<td align="center"><a href="#-quick-install">🚀 Install</a></td>
<td align="center"><a href="#-features">📊 Features</a></td>
<td align="center"><a href="#-getting-started">🎯 Getting Started</a></td>
<td align="center"><a href="#-integration">🌐 Integration</a></td>
<td align="center"><a href="#-support">💬 Support</a></td>
</tr>
</table>

</details>

</div>