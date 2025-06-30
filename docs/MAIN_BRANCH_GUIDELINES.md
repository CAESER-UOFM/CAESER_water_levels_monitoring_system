# Main Branch Guidelines

## 🎯 Purpose
This document defines what belongs in the **main branch** vs **development branches** to maintain a clean, production-ready codebase.

## ✅ MAIN BRANCH: Production-Ready Code Only

### What BELONGS in Main:
- **Core application code** (`src/` directory)
- **Production documentation** (user guides, installation instructions)
- **Essential configuration templates** (settings templates, not actual config files)
- **Production build scripts** (`setup.sh`, `setup.bat`, `setup.ps1`)
- **Core assets** (icons, images used by the application)
- **Requirements and dependencies** (`Requirements.txt`, `package.json`)

### Production Documentation (KEEP):
- `README.md` - Main project documentation
- `SETUP.md` - Installation and setup instructions
- `docs/QUICK_START.md` - User getting started guide
- `docs/INSTALLATION_GUIDE.md` - Detailed installation
- `docs/USER_GUIDE/` - End user documentation
- `docs/TECHNICAL/` - Production technical docs

## ❌ MAIN BRANCH: What Should NEVER Be Here

### Testing and Development Files (FORBIDDEN):
- `claude_testing/` - Testing framework directory
- `*test*.py` - Any test files
- `*test*.json` - Test results and configurations
- `*debug*.py` - Debug and development scripts
- `PATH_MANAGEMENT_WARNING.md` - Development warnings

### Development Tools (FORBIDDEN):
- `test_installer.bat` - Development installer scripts
- `setup_debug.bat`, `setup_simple.bat` - Development setup variants
- `debug_*.py` - Debugging utilities
- `example_*.py` - Example and demonstration code
- IDE configuration folders (`.spyproject/`, `.spyder-py3/`)

### Large Data Files (FORBIDDEN):
- `imported_xle_files/` - Test sensor data (millions of lines)
- `last_run/` - Runtime data and temporary outputs
- Large sample datasets for testing

### Development Documentation (FORBIDDEN):
- `docs/PHASE*.md` - Development phase documentation
- `docs/FINAL_TODO_LIST.md` - Development task lists
- `docs/google_drive_analysis.md` - Technical analysis documents
- `docs/dual_database_*.md` - Implementation planning docs
- Testing reports and summaries

## 🔧 DEVELOPMENT BRANCHES: Where Everything Else Goes

### Use Development Branches For:
- **Feature development** - New functionality and improvements
- **Testing infrastructure** - Test files, test data, testing frameworks
- **Debugging tools** - Debug scripts, development utilities
- **Experimental code** - Proof of concepts, experimental features
- **Development documentation** - Implementation notes, TODO lists, analysis
- **IDE configurations** - Personal development environment settings

### Recommended Branch Names:
- `feature/telemetry-validation` - Specific feature development
- `testing/integration-framework` - Testing infrastructure
- `bugfix/database-connection` - Bug fixes
- `docs/api-documentation` - Documentation improvements

## 🚫 .gitignore Protection

The `.gitignore` file has been updated with a **MAIN BRANCH PROTECTION** section that prevents common development files from being accidentally committed:

```gitignore
# =============================================================================
# MAIN BRANCH PROTECTION: PREVENT TESTING AND DEVELOPMENT FILES
# =============================================================================
claude_testing/
*test*.py
debug_*.py
setup_debug.bat
imported_xle_files/
.spyproject/
```

## 🔀 Proper Merge Strategy

### ✅ Correct Approach:
1. **Cherry-pick specific commits** from development branches
2. **Review each commit** before merging to main
3. **Only merge production-ready code**
4. **Test thoroughly** before merging

### ❌ Avoid:
- Merging entire development branches
- Bulk merges without review
- Including testing infrastructure in merges
- Merging experimental or debugging code

## 🛡️ Enforcement

This guideline is enforced through:
1. **Comprehensive .gitignore** - Prevents accidental commits
2. **Code review process** - Manual review before merges
3. **Branch protection** - Only allow reviewed merges to main
4. **Regular cleanup** - Periodic review and cleanup of main branch

## 📞 Questions?

If you're unsure whether something belongs in main:
- **Ask yourself**: "Would an end user need this file?"
- **When in doubt**: Put it in a development branch first
- **Production rule**: If it's not essential for the application to run, it belongs in a branch

---

**Remember**: Main branch = Production ready. Everything else = Development branches.