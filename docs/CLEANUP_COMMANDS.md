# Repository Cleanup Commands

Run these commands in your repository root to implement Option 4 (Hybrid approach):

## 🧹 Step 1: Remove Sensitive Files

```bash
# Remove the sensitive credential files from git
git rm config/water-levels-monitoring-451921-bfb891f4bf7c.json
git rm config/client_secret_728293570565-45o222f786nahq6hc1o6vvi2kur6frvf.apps.googleusercontent.com.json
git rm config/token.pickle

# Commit the removal
git commit -m "🔒 Remove sensitive Google API credentials for security"
```

## 📋 Step 2: Add .gitignore Protection

```bash
# Copy the .gitignore template
cp docs/gitignore_template .gitignore

# Add and commit .gitignore
git add .gitignore
git commit -m "🛡️ Add comprehensive .gitignore for credential security"
```

## 📄 Step 3: Update README

```bash
# Copy the GitHub-ready README
cp docs/README_FOR_GITHUB.md README.md

# Add and commit new README
git add README.md
git commit -m "📚 Add comprehensive README for public distribution"
```

## 🔄 Step 4: Push Changes

```bash
# Push all changes to GitHub
git push origin main
```

## 🏗️ Step 5: Create Private Credentials Repository

1. **Go to GitHub** and create a new **PRIVATE** repository
2. **Name it**: `water_levels_monitoring_credentials`
3. **Make it private**: ✅ Private
4. **Initialize**: With README

## 📁 Step 6: Set Up Private Repository

```bash
# Create a temporary directory for credentials repo
mkdir ../water_levels_monitoring_credentials
cd ../water_levels_monitoring_credentials

# Initialize git and connect to private repo
git init
git remote add origin https://github.com/benjaled/water_levels_monitoring_credentials.git

# Create credentials directory
mkdir config

# Copy your REAL credential files to this repo
# (You'll need to do this manually with your actual files)
cp /path/to/your/real/water-levels-monitoring-451921-bfb891f4bf7c.json config/
cp /path/to/your/real/client_secret_*.json config/

# Create README for private repo
cat > README.md << 'EOF'
# Water Level Monitoring - Private Credentials

This private repository contains Google API credentials for the Water Level Monitoring System.

## Files
- `config/water-levels-monitoring-*.json` - Service Account credentials
- `config/client_secret_*.json` - OAuth Client credentials

## Usage
These files should be copied to the `config/` directory of the main application.

## Security
- This repository is private
- Only authorized users have access
- Never make this repository public
- Never commit these files to the main public repository

## Access
Contact the repository owner for access to these credentials.
EOF

# Add files and commit
git add .
git commit -m "Add Google API credentials for authorized users"
git push -u origin main
```

## 🎯 Step 7: Create First Release

1. **Go to your main repository**: https://github.com/benjaled/water_levels_monitoring_-for_external_edits-
2. **Click "Releases"** → **"Create a new release"**
3. **Fill in**:
   - **Tag**: `v1.0.0`
   - **Title**: `Water Level Monitoring System v1.0.0 - Initial Release`
   - **Description**: Copy from `docs/RELEASE_SETUP_GUIDE.md`
4. **Click "Publish release"**

## ✅ Verification Checklist

After running all commands:

- [ ] Sensitive files removed from public repo
- [ ] .gitignore prevents future credential commits
- [ ] README updated with installation instructions
- [ ] Private credentials repository created
- [ ] Real credentials stored in private repo only
- [ ] First release published
- [ ] Can download source code from release
- [ ] Setup dialog works when credentials missing

## 🚀 Result

Your setup will be:

### Public Repository (`water_levels_monitoring_-for_external_edits-`)
- ✅ Professional README with installation instructions
- ✅ Complete application code (without credentials)
- ✅ Enhanced installers
- ✅ Auto-update system
- ✅ Credential setup dialog
- ✅ Safe for public viewing

### Private Repository (`water_levels_monitoring_credentials`)
- ✅ Real Google API credentials
- ✅ Only accessible to invited users
- ✅ Secure credential distribution

### User Experience
1. **Download** main app from public repository
2. **Run installer** 
3. **Get credentials** from private repository (if authorized)
4. **Use setup dialog** to configure credentials
5. **Enjoy full functionality** with Google Drive features

Now you can safely show your public repository to friends! 🎉