# 🖥️ Windows Setup Guide - Unblocking Files

## ⚠️ **Important: Windows Security Notice**

When you download files from the internet, Windows automatically "blocks" them for security. This is normal and happens with ALL downloaded software. You need to "unblock" the setup file before you can run it.

---

## 📋 **Quick Visual Steps**

### **Step 1: Find your downloaded setup.bat file**
```
📁 Downloads folder → setup.bat (or inside extracted ZIP folder)
```

### **Step 2: Right-click on setup.bat**

<div align="center">

**Visual Guide:**

```
📁 Your Downloads Folder
├── 📄 setup.bat  ← Right-click this file
└── 📁 other files...

🖱️ Right-click menu appears:
┌─────────────────┐
│ 🔄 Open        │
│ ✏️  Edit        │
│ 📋 Copy        │
│ ✂️  Cut         │
│ 🗑️ Delete      │
│ 📋 Properties  │ ← Click this!
└─────────────────┘
```

</div>

### **Step 3: The Properties Window Opens**

<div align="center">

**Look for the "Security" section at the bottom:**

```
┌──────────────────────────────────────┐
│        📄 setup.bat Properties       │
├──────────────────────────────────────┤
│ 📂 General                           │
│                                      │
│ Name: setup.bat                      │
│ Type: Batch File (.bat)             │
│ Size: 2.1 KB                        │
│ Location: C:\Users\...\Downloads     │
│                                      │
│ ⚠️  Security:                        │
│ ┌──────────────────────────────────┐ │
│ │ This file came from another      │ │
│ │ computer and might be blocked    │ │ 
│ │ to help protect this computer.   │ │
│ │                                  │ │
│ │ ☐ Unblock  ← CHECK THIS BOX!    │ │
│ └──────────────────────────────────┘ │
│                                      │
│    [ OK ]  [ Cancel ]  [ Apply ]     │
└──────────────────────────────────────┘
```

**Steps:**
1. **✅ Check** the "Unblock" checkbox
2. **Click "OK"**
3. **Done!** Now you can double-click setup.bat

</div>

### **Step 4: Check the "Unblock" checkbox ✅**
- Look for the "Security" section at the bottom
- Check the box next to **"Unblock"**
- Click **"OK"**

### **Step 5: Now double-click setup.bat to install**
```
🖱️ Double-click setup.bat → Installation starts! 🎉
```

---

## 🤔 **Troubleshooting**

### **Don't see the "Unblock" option?**
- The file might already be unblocked
- Try double-clicking setup.bat anyway
- If it still doesn't work, see the "Alternative Method" below

### **Still getting security warnings?**
**SmartScreen Warning:**
```
┌─────────────────────────────────┐
│ 🛡️ Windows protected your PC    │
├─────────────────────────────────┤
│ Windows Defender SmartScreen   │
│ prevented an unrecognized app   │
│ from starting.                  │
│                                 │
│ [Don't run] [More info]         │
└─────────────────────────────────┘
```

**Solution:**
1. Click **"More info"** 
2. Click **"Run anyway"**

This is normal for new software! The warning appears because the app doesn't have a Microsoft code signing certificate (which costs thousands of dollars).

---

## 🔧 **Alternative Method (If right-click doesn't work)**

### **Method 1: Using File Explorer Properties**
1. Open **File Explorer**
2. Navigate to your `setup.bat` file
3. **Single-click** to select it (don't double-click)
4. Press **Alt + Enter** (this opens Properties)
5. Follow steps 3-5 above

### **Method 2: PowerShell Method (Advanced)**
1. Hold **Shift** and **right-click** in the folder containing setup.bat
2. Select **"Open PowerShell window here"**
3. Type: `Unblock-File -Path .\setup.bat`
4. Press **Enter**
5. Now double-click setup.bat

---

## 💡 **Why This Happens**

**This is completely normal!** Windows does this for ALL downloaded software to protect users from malicious files. Popular apps like:
- Chrome browser downloads
- Discord installers  
- Steam games
- Any software from GitHub

All require this same "unblock" process when downloaded.

---

## ✅ **Success Indicators**

**You'll know it worked when:**
- Double-clicking setup.bat opens a black command window
- You see text like "Installing Water Levels Monitoring System..."
- The installation proceeds without security warnings

**Installation should take 1-2 minutes and you'll see:**
```
✅ Python environment created
✅ Dependencies installed  
✅ Application files copied
✅ Shortcuts created
🎉 Installation complete!
```

---

## 🆘 **Still Need Help?**

If you're still having trouble:

1. **Take a screenshot** of any error messages
2. **Open an issue** on GitHub with your screenshot
3. **Include** your Windows version (Windows 10/11)
4. **Mention** what step you're stuck on

**Quick Windows version check:**
- Press **Windows key + R**
- Type `winver` and press Enter
- Note the version number in the window that opens

---

**Remember:** This is a one-time setup step. Once installed, you won't need to do this again! 🚀