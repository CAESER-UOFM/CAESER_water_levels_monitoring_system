# Tools Directory

This directory contains various tools and applications for the Water Level Monitoring system.

## Applications

### 🖥️ **Visualizer** (Desktop Application)
**Location:** `tools/Visualizer/`  
**Type:** Python Desktop Application  
**Purpose:** Full-featured desktop visualizer with advanced analysis capabilities

- **Technology:** Python, tkinter/Qt GUI
- **Features:** Complete data analysis, recharge calculations, advanced plotting
- **Entry Point:** `main.py`
- **Usage:** Desktop workstation analysis

### 📱 **MobileVisualizer** (Web Application)
**Location:** `tools/MobileVisualizer/`  
**Type:** Mobile Web Application  
**Purpose:** Simplified mobile interface for field data viewing

- **Technology:** Next.js, React, TypeScript
- **Features:** Mobile-optimized data viewing, basic plotting, data export
- **Entry Point:** `npm run dev` or deploy to web
- **Usage:** Field work, mobile data access

## Utility Scripts

The main `tools/` directory also contains various utility scripts:

- `csv_to_xle_converter.py` - Convert CSV files to XLE format
- `solinst_file_organizer.py` - Organize Solinst data files  
- `xle_metadata_editor.py` - Edit XLE file metadata
- `well_toc_calculator.py` - Calculate well top of casing
- And many more...

## Getting Started

### Desktop Visualizer
```bash
cd tools/Visualizer
python main.py
```

### Mobile Web App
```bash
cd tools/MobileVisualizer
npm install
npm run dev
```

## Architecture

```
tools/
├── Visualizer/           # Desktop Python application
│   ├── main.py          # Desktop app entry point
│   ├── gui/             # GUI components
│   ├── db/              # Database modules
│   └── ...
├── MobileVisualizer/     # Mobile web application  
│   ├── package.json     # Web app dependencies
│   ├── src/             # React/TypeScript source
│   ├── public/          # Static assets
│   └── ...
└── *.py                 # Utility scripts
```

## Documentation

- **Desktop App:** See documentation in `tools/Visualizer/`
- **Mobile App:** See `tools/MobileVisualizer/README.md`
- **Deployment:** See `tools/MobileVisualizer/DEPLOYMENT.md`

Both applications work with the same SQLite database format and are designed to complement each other for different use cases.