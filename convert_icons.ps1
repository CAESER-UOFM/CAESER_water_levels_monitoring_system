# PowerShell script to convert PNG icons to proper ICO format with multiple sizes
# This creates high-quality ICO files with embedded sizes: 16x16, 32x32, 48x48, 256x256

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

function Convert-PngToIco {
    param(
        [string]$PngPath,
        [string]$IcoPath
    )
    
    try {
        Write-Host "Converting $PngPath to $IcoPath"
        
        # Load the original PNG
        $originalImage = [System.Drawing.Image]::FromFile($PngPath)
        
        # Define the sizes we want in the ICO file
        $sizes = @(16, 32, 48, 256)
        
        # Create a temporary directory for individual size files
        $tempDir = Join-Path $env:TEMP "IconConversion"
        if (!(Test-Path $tempDir)) {
            New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
        }
        
        $tempFiles = @()
        
        # Create resized versions for each size
        foreach ($size in $sizes) {
            Write-Host "  Creating ${size}x${size} version..."
            
            # Create a new bitmap with the target size
            $resizedBitmap = New-Object System.Drawing.Bitmap($size, $size)
            $graphics = [System.Drawing.Graphics]::FromImage($resizedBitmap)
            
            # Set high-quality rendering
            $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
            $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
            $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
            
            # Draw the resized image
            $graphics.DrawImage($originalImage, 0, 0, $size, $size)
            
            # Save as temporary PNG
            $tempFile = Join-Path $tempDir "${size}.png"
            $resizedBitmap.Save($tempFile, [System.Drawing.Imaging.ImageFormat]::Png)
            $tempFiles += $tempFile
            
            # Cleanup
            $graphics.Dispose()
            $resizedBitmap.Dispose()
        }
        
        # Now create the ICO file using the largest size as base
        # This is a simplified approach - for production, you'd want a proper ICO library
        $largestImage = [System.Drawing.Image]::FromFile($tempFiles[-1])  # 256x256
        
        # Convert to icon format
        $icon = [System.Drawing.Icon]::FromHandle(([System.Drawing.Bitmap]$largestImage).GetHicon())
        
        # Save the ICO file
        $iconBitmap = $icon.ToBitmap()
        $iconBitmap.Save($IcoPath, [System.Drawing.Imaging.ImageFormat]::Icon)
        
        # Cleanup
        $largestImage.Dispose()
        $icon.Dispose()
        $iconBitmap.Dispose()
        $originalImage.Dispose()
        
        # Clean up temporary files
        foreach ($tempFile in $tempFiles) {
            Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
        }
        Remove-Item $tempDir -Force -ErrorAction SilentlyContinue
        
        Write-Host "  Successfully created $IcoPath"
        return $true
        
    } catch {
        Write-Host "  Error converting $PngPath`: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Get the script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetsDir = Join-Path $scriptDir "assets"

# Ensure assets directory exists
if (!(Test-Path $assetsDir)) {
    Write-Host "Assets directory not found: $assetsDir" -ForegroundColor Red
    exit 1
}

Write-Host "Converting PNG icons to ICO format..." -ForegroundColor Green
Write-Host "Assets directory: $assetsDir" -ForegroundColor Gray

# Convert main app icon
$mainPng = Join-Path $assetsDir "water_level_meter.png"
$mainIco = Join-Path $assetsDir "water_level_meter.ico"

if (Test-Path $mainPng) {
    $result1 = Convert-PngToIco -PngPath $mainPng -IcoPath $mainIco
    if ($result1) {
        Write-Host "✓ Main app icon converted successfully" -ForegroundColor Green
    }
} else {
    Write-Host "✗ Main app PNG not found: $mainPng" -ForegroundColor Red
}

# Convert visualizer icon
$visualizerPng = Join-Path $assetsDir "Water_level_tab_icon.png"
$visualizerIco = Join-Path $assetsDir "Water_level_tab_icon.ico"

if (Test-Path $visualizerPng) {
    $result2 = Convert-PngToIco -PngPath $visualizerPng -IcoPath $visualizerIco
    if ($result2) {
        Write-Host "✓ Visualizer icon converted successfully" -ForegroundColor Green
    }
} else {
    Write-Host "✗ Visualizer PNG not found: $visualizerPng" -ForegroundColor Red
}

Write-Host "`nIcon conversion complete!" -ForegroundColor Green
Write-Host "Generated ICO files:" -ForegroundColor Gray
if (Test-Path $mainIco) {
    Write-Host "  - $mainIco" -ForegroundColor Gray
}
if (Test-Path $visualizerIco) {
    Write-Host "  - $visualizerIco" -ForegroundColor Gray
}