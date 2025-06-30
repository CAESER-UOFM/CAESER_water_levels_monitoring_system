# 🌊 CAESER Water Levels Monitoring System

Desktop app for processing water level data that doesn't suck. Built by groundwater nerds, for groundwater nerds.

## What it does (the important stuff)

**Turns your XLE files into actual insights** - Import Solinst data, apply barometric correction, calculate recharge rates, and get your plots looking publication-ready. Plus it syncs with Google Drive so your whole team can collaborate without the usual file-sharing chaos.

**Key features:**
- **Solinst support** - XLE and LEV files work out of the box
- **Barometric compensation** - Because atmospheric pressure is annoying but necessary
- **Recharge calculations** - RISE, MRC, and ERC methods (with the math actually working)
- **Team collaboration** - Google Drive sync that handles conflicts intelligently
- **Interactive maps** - See where your wells are and what they're doing
- **Export everything** - CSV, plots, whatever format you need

**Also handles:**
- Manual readings integration
- Batch processing (drag & drop multiple files)
- Quality control flagging
- Telemetry data from MONET
- Web visualizer for field access

## Installation (actually easy)

**Step 1:** Download the latest release  
**Step 2:** Run `setup.bat` (Windows) or `setup.sh` (Mac/Linux)  
**Step 3:** Launch using the shortcut it creates

That's it. No admin rights needed, installs to your user folder, doesn't mess with your system.

*University/corporate users:* If Windows shows a SmartScreen warning, just click "More info" → "Run anyway". This is normal for new software.

## Getting started

**First time using it?**
1. Launch the app and create a user account
2. Import some barologger data (atmospheric pressure - you'll thank us later)
3. Import your water level XLE files
4. Watch the magic happen as it automatically applies corrections
5. Calculate some recharge estimates and export your results

**The app has 5 main tabs:**
- **Database** - Map view of your wells and data management
- **Barologger** - Import atmospheric pressure data  
- **Water Level** - Main data processing and visualization
- **Recharge** - Calculate recharge rates using different methods
- **Runs** - Track field monitoring campaigns

## For different users

**CAESER team members:** Contact the maintainer for Google Drive credentials to enable full cloud sync and collaboration features.

**Independent researchers:** Everything works locally out of the box. You can set up your own Google Drive integration if you want cloud collaboration.

**Need other sensor support?** The app is modular - currently supports Solinst natively, but Campbell Scientific and In-Situ support is coming. Hit us up if you need something specific.

## 🖥️ **System Requirements**
- **OS**: Windows 10+ | macOS 10.14+ | Linux Ubuntu 18.04+
- **RAM**: 4GB+ (8GB+ recommended for large datasets)  
- **Storage**: 2GB+ free space
- **Internet**: Optional (required only for updates and cloud features)

## 🛠️ **Professional Features**

### **🔬 Scientific Analysis Tools**
- **Multiple Recharge Methods**: RISE, MRC, ERC with parameter customization
- **Statistical Analysis**: Well statistics, trend analysis, data quality metrics
- **Publication Graphics**: High-resolution plots with customizable styling
- **Data Export**: CSV, JSON, and database formats for further analysis

### **🌐 Web-Based Visualization**
- **Mobile Visualizer**: Responsive web interface for field access
- **Turso Integration**: Cloud database with real-time synchronization  
- **API Access**: RESTful endpoints for custom integrations
- **Offline Capability**: PWA support for field work without internet

### **🔧 Modular Sensor Support**
- **Current**: Full Solinst integration (XLE, LEV formats)
- **Expanding**: Campbell Scientific, In-Situ, OTT HydroMet compatibility
- **Legacy**: CSV import, manual readings, telemetry data integration
- **Custom**: Open architecture for proprietary sensor integration

### **🤖 AI & Database Integration**  
- **SQLite Foundation**: Optimized for LLM and AI analysis integration
- **Smart Queries**: Natural language database interaction (coming soon)
- **Pattern Recognition**: Automated anomaly detection and quality control
- **Predictive Analytics**: Machine learning integration for trend forecasting

## 🚀 **Future Development Roadmap**

### **Phase 1 (Current)**: Core Platform
✅ Multi-sensor integration and cloud collaboration  
✅ Advanced visualization and recharge calculations  
✅ Web-based tools and mobile interface

### **Phase 2 (Near-term)**: AI Integration  
🔄 Natural language database queries  
🔄 Automated report generation  
🔄 Predictive modeling integration  
🔄 Advanced pattern recognition

### **Phase 3 (Long-term)**: Ecosystem Expansion
🔄 Public web visualizer for county-wide data  
🔄 Real-time telemetry network integration  
🔄 Multi-agency collaboration platform  
🔄 Advanced research tools and publications support

## 📞 **Support & Community**

- **📖 Documentation**: Built-in help system with comprehensive guides
- **🐛 Issues**: [Report bugs and request features](../../issues)  
- **👥 CAESER Network**: Contact maintainer for research collaboration access
- **💬 Community**: Join discussions and share integration experiences

---

## 🎯 **Ready to Transform Your Water Level Monitoring?**

**[📥 Download Latest Release](../../releases/latest)** → **Run Installer** → **Start Analyzing**

*Professional groundwater monitoring made simple, powerful, and collaborative.*