# Quick Start Guide

## 🚀 Get Started in 5 Minutes

This guide will get you up and running with the CAESER Water Levels Monitoring System quickly and efficiently.

---

## Step 1: Installation (2 minutes)

### **Download and Install**
```bash
# Option A: Download Release (Recommended)
1. Go to GitHub Releases
2. Download latest version
3. Extract to desired location

# Option B: Clone Repository
git clone https://github.com/CAESER-UOFM/water-levels-monitoring.git
cd water-levels-monitoring
```

### **Run Installer**
```bash
# Windows Users
Double-click: setup.bat

# macOS/Linux Users
chmod +x setup.sh && ./setup.sh
```

**✅ That's it!** The installer handles everything automatically:
- Python environment setup
- Dependency installation
- Database initialization
- Launcher creation

---

## Step 2: First Launch (1 minute)

### **Start the Application**
```bash
# Windows
Double-click: water_levels_app.bat

# macOS/Linux  
Double-click: water_levels_app.command
```

### **Initial Setup**
1. **Create User Account**: Enter username and password
2. **Choose Database**: Select "Local Database" for solo use
3. **Welcome Tour**: Optional guided tour of interface

---

## Step 3: Import Your First Data (2 minutes)

### **Prepare Sample Data**
If you don't have data yet, download our sample files:
- [Sample XLE Files](link-to-sample-data)
- [Sample Manual Readings](link-to-sample-csv)

### **Import Barologger Data (Optional but Recommended)**
1. Go to **Barologger Tab**
2. Click **"Import Barologger Data"**
3. Select your atmospheric pressure XLE files
4. Click **"Import"** and wait for processing

### **Import Water Level Data**
1. Go to **Water Level Tab**
2. Click **"Import Water Level Data"**
3. Select your transducer XLE files
4. Map wells to locations (or use existing coordinates)
5. Apply barometric compensation if available
6. Click **"Process Data"**

---

## Step 4: Explore Your Data (1 minute)

### **View on Map**
1. Go to **Database Tab**
2. See your wells plotted on interactive map
3. Click wells for detailed information

### **Analyze Water Levels**
1. Go to **Water Level Tab**
2. Select a well from dropdown
3. View time series plots automatically
4. Use zoom and pan controls for detailed analysis

### **Calculate Recharge (Optional)**
1. Go to **Recharge Tab**
2. Select calculation method (RISE recommended for beginners)
3. Choose a well with good data coverage
4. Click **"Calculate Recharge"**
5. View results and export if desired

---

## 🎯 Common First Tasks

### **Task 1: Basic Data Analysis**
```
1. Import XLE files (Barologger + Water Level)
2. View data quality in plots
3. Export CSV for external analysis
4. Generate basic statistics report
```

### **Task 2: Multi-Well Comparison**
```
1. Import data from multiple wells
2. Use Database tab map to see spatial distribution
3. Compare water level trends between wells
4. Identify regional patterns
```

### **Task 3: Recharge Estimation**
```
1. Ensure high-quality, barometrically compensated data
2. Use RISE method for initial estimates
3. Validate results against known conditions
4. Export recharge calculations for reporting
```

---

## 🔧 Essential Features Overview

### **Five Main Tabs**
| Tab | Purpose | Key Features |
|-----|---------|--------------|
| 🗂️ **Database** | Well management & mapping | Interactive map, well locations, database switching |
| 🌡️ **Barologger** | Atmospheric pressure data | XLE import, master baro creation, pressure plots |
| 💧 **Water Level** | Core water level analysis | Data import, visualization, quality control |
| 📊 **Recharge** | Groundwater recharge calculations | RISE/MRC/ERC methods, parameter configuration |
| 🏃 **Runs** | Field monitoring campaigns | Run planning, progress tracking, team coordination |

### **Key Buttons to Know**
- **❓ Help**: Context-sensitive help system
- **📁 Import**: Data import wizards
- **📊 Plot**: Interactive data visualization
- **💾 Export**: Data and report export options
- **⚙️ Settings**: Configuration and preferences

---

## 🌟 Pro Tips for New Users

### **Data Quality First**
- ✅ Always import barologger data before water levels
- ✅ Review data plots for obvious errors
- ✅ Use quality control flags to mark questionable data
- ✅ Validate with manual readings when available

### **Organization Best Practices**
- 📁 Create clear folder structure for XLE files
- 📝 Use consistent well naming conventions
- 🗂️ Keep notes on data sources and collection methods
- 📅 Document any known issues or equipment changes

### **Analysis Workflow**
1. **Data Import** → Import all available data sources
2. **Quality Control** → Review and validate imported data  
3. **Visualization** → Create plots to understand patterns
4. **Analysis** → Calculate statistics and recharge rates
5. **Export** → Share results and create reports

---

## 🚨 Troubleshooting Quick Fixes

### **Common Issues**
| Problem | Quick Fix |
|---------|-----------|
| Import fails | Check file format - must be .xle, .lev, or .csv |
| No data in plots | Verify date ranges and quality flags |
| Slow performance | Close other applications, check available RAM |
| Can't find launchers | Check installation directory for .bat/.command files |

### **Getting Help**
- **Built-in Help**: Use ❓ button in any tab
- **Debug Mode**: Use debug launchers for detailed error info
- **Log Files**: Check application logs for specific errors
- **Community**: Post questions in GitHub Issues

---

## 🌐 Next Steps

### **Explore Advanced Features**
- **Google Drive Sync**: Set up cloud collaboration
- **Web Visualizer**: Access data from mobile devices
- **Batch Processing**: Handle large datasets efficiently
- **Custom Calculations**: Configure recharge parameters

### **Integration Options**
- **MONET Telemetry**: Connect real-time monitoring
- **GIS Systems**: Export data for mapping applications
- **Custom APIs**: Build automated workflows
- **External Databases**: Connect to larger monitoring networks

### **Learning Resources**
- **User Guide**: Comprehensive feature documentation
- **Video Tutorials**: Step-by-step video guides (coming soon)
- **Sample Projects**: Download example datasets and workflows
- **Best Practices**: Learn from experienced users

---

## 📞 Support and Community

### **Getting Help**
- **📖 Documentation**: Use built-in help system for detailed guidance
- **🐛 Bug Reports**: [GitHub Issues](../../issues) for problems and suggestions
- **💬 Discussions**: [GitHub Discussions](../../discussions) for questions and tips
- **📧 CAESER Members**: Contact maintainer for network-specific support

### **Contributing**
- **Feature Requests**: Suggest improvements via GitHub Issues
- **Documentation**: Help improve guides and tutorials
- **Testing**: Test new features and report feedback
- **Integration**: Share custom sensor integrations and workflows

---

## 🎉 You're Ready to Go!

**Congratulations!** You now have a powerful water level monitoring system ready to use. Start by importing your data and exploring the interactive features.

**Remember**: 
- Use the built-in ❓ Help system for detailed guidance
- Start simple and gradually explore advanced features
- The system is designed to grow with your needs

**Ready for more?** Continue to the [User Guide](docs/help/USER_GUIDE/getting_started.md) for comprehensive documentation.

---

*Professional groundwater monitoring made simple, powerful, and collaborative.*