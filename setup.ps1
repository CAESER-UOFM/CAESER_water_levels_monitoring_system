# CAESER Water Levels Monitoring Application - PowerShell Installer
# This version may have fewer SmartScreen restrictions

Write-Host "CAESER Water Levels Monitoring Application - PowerShell Installer" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as admin (optional for this installer)
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if ($isAdmin) {
    Write-Host "Running with administrator privileges." -ForegroundColor Green
} else {
    Write-Host "Running without administrator privileges (this is fine!)." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "This installer will:"
Write-Host "  • Install to your user profile (no admin required)"
Write-Host "  • Create desktop shortcuts"
Write-Host "  • Set up Python environment and dependencies"
Write-Host ""

$continue = Read-Host "Continue with installation? (Y/n)"
if ($continue -eq "n" -or $continue -eq "N") {
    Write-Host "Installation cancelled." -ForegroundColor Red
    exit
}

Write-Host ""
Write-Host "Starting batch installer..." -ForegroundColor Green
Write-Host ""

# Get the directory where this script is located
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Run the batch file from PowerShell
& "$scriptDir\setup.bat"

Write-Host ""
Write-Host "PowerShell launcher complete." -ForegroundColor Green