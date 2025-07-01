# 🚨 CRITICAL: Instructions for Merging to Main Branch

## ⚠️ MAIN BRANCH PROTECTION RULES

The main branch has been **completely cleaned** and now contains **ONLY production-ready code**. 

### ❌ DO NOT MERGE TO MAIN:
- **Testing files**: `test_*.py`, `*_test.py`, `test_database_setup_dialog.py`
- **Sample data**: Sample CSV files, test databases, debug files
- **Development artifacts**: Any files with `debug`, `test`, `sample` in the name
- **This instruction file**: `MERGE_TO_MAIN_INSTRUCTIONS.md`

### ✅ SAFE TO MERGE TO MAIN:
- **Production code changes**: Modified files in `src/` directory
- **Essential documentation**: User-facing documentation only
- **Core functionality**: Database dialog improvements, CSV import features

## 🎯 FOR CSV IMPORT FEATURE MERGE:

### ✅ Files to Cherry-Pick/Merge:
```
src/gui/dialogs/database_*.py          # Database dialog improvements
src/gui/handlers/*_handler.py          # Modified handlers for CSV import
src/database/initializer.py           # Database setup improvements (if modified)
docs/INSTALLATION_GUIDE.md            # If updated for new features
docs/QUICK_START.md                    # If updated for new workflow
```

### ❌ Files to EXCLUDE from Merge:
```
test_database_setup_dialog.py         # Testing file
sample_*.csv                          # Sample data files  
*_test_*.csv                          # Test CSV files
debug_*.py                            # Debug scripts
**/test_*                             # Any test directories
MERGE_TO_MAIN_INSTRUCTIONS.md         # This instruction file
```

## 🔧 Recommended Merge Process:

### Option 1: Cherry-Pick Specific Commits (SAFEST)
```bash
git checkout main
git cherry-pick <commit-hash-1>  # Only production code commits
git cherry-pick <commit-hash-2>  # Exclude test file commits
```

### Option 2: Selective File Merge
```bash
git checkout main
git checkout benja-improvements -- src/gui/dialogs/database_setup_dialog.py
git checkout benja-improvements -- src/gui/handlers/csv_import_handler.py
# Only merge specific production files
```

### Option 3: Manual Copy (MOST CONTROLLED)
1. Identify the exact production code changes
2. Manually copy only the production code modifications
3. Test thoroughly before committing

## 🧪 Before Merging - MANDATORY CHECKS:

### Pre-Merge Validation:
- [ ] **List all files being merged** - verify none are test/debug files
- [ ] **Check file contents** - ensure no hardcoded paths or test data
- [ ] **Review git diff** - confirm only production changes included
- [ ] **Test installation** - verify app still installs cleanly

### Post-Merge Validation:
- [ ] **Run application** - ensure CSV import feature works
- [ ] **Check main branch** - verify no test files were added
- [ ] **Test clean install** - download and install on fresh machine

## 📝 CSV Import Feature Summary:

**What to Include in Main:**
- Enhanced database creation dialog with CSV import option
- Background CSV processing worker
- Automatic format detection for exported vs expected formats
- Error handling and validation for CSV imports
- User-friendly progress reporting

**What to Exclude from Main:**
- Test files and sample CSV data
- Debug scripts and development artifacts  
- Development documentation and implementation notes

## 🚀 Target Result:

After merge, main branch should have:
✅ **Enhanced database setup** with CSV import capability
✅ **Production-ready CSV import workflow** 
✅ **Clean codebase** with no testing artifacts
✅ **User documentation** reflecting new features

---
**🤖 This file should NOT be merged to main - it's for development guidance only**
**🔒 Main branch protection is critical - when in doubt, ask for review**