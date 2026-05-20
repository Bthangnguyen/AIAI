# clean_c_drive.ps1
# Requires Administrator privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Please run this script as an Administrator!"
    Exit
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "   BAT DAU DONG DEP O C (C-DRIVE CLEANUP SCRIPT)  " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Check Initial Space
$driveC = Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DeviceID='C:'"
$initialFreeBytes = $driveC.FreeSpace
$initialFreeGB = [Math]::Round($initialFreeBytes / 1GB, 2)
Write-Host "Dung luong trong ban dau cua o C: $initialFreeGB GB`n" -ForegroundColor Yellow

# Helper to Safely Delete files in a directory
function Clean-Directory {
    param (
        [string]$Path,
        [string]$Description
    )
    if (Test-Path $Path) {
        Write-Host "Dang don dep: $Description ($Path)..." -ForegroundColor Gray
        try {
            # Delete files and subfolders, ignoring errors for locked files
            Get-ChildItem -Path $Path -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "-> Da don dep xong $Description." -ForegroundColor Green
        } catch {
            Write-Host "-> Co mot so file dang mo, khong the xoa toan bo." -ForegroundColor DarkYellow
        }
    } else {
        Write-Host "-> Khong tim thay duong dan: $Path (Bo qua)" -ForegroundColor DarkGray
    }
}

# 1. System Temp Cleanup
Clean-Directory -Path "$env:SystemRoot\Temp\*" -Description "Windows System Temp"
Clean-Directory -Path "$env:TEMP\*" -Description "User Temp"
Clean-Directory -Path "$env:SystemRoot\Prefetch\*" -Description "Windows Prefetch"

# 2. Windows Update Download Cache
# Stop Windows Update Service first to release lock
Write-Host "Dang dung dich vu Windows Update de don update cache..." -ForegroundColor Gray
Stop-Service -Name "wuauserv" -Force -ErrorAction SilentlyContinue
Clean-Directory -Path "$env:SystemRoot\SoftwareDistribution\Download\*" -Description "Windows Update Cache"
Start-Service -Name "wuauserv" -ErrorAction SilentlyContinue

# 3. Developer Cache Cleanup
# NPM
if (Get-Command npm -ErrorAction SilentlyContinue) {
    Write-Host "Dang xoa NPM Cache..." -ForegroundColor Gray
    try {
        npm cache clean --force
        Write-Host "-> Da don dep NPM cache qua CLI." -ForegroundColor Green
    } catch {}
}
Clean-Directory -Path "$env:APPDATA\npm-cache\*" -Description "NPM AppData Cache"

# PIP
if (Get-Command pip -ErrorAction SilentlyContinue) {
    Write-Host "Dang xoa PIP Cache..." -ForegroundColor Gray
    try {
        pip cache purge
        Write-Host "-> Da don dep PIP cache qua CLI." -ForegroundColor Green
    } catch {}
}
Clean-Directory -Path "$env:LOCALAPPDATA\pip\Cache\*" -Description "PIP Cache Folder"

# NuGet
if (Get-Command dotnet -ErrorAction SilentlyContinue) {
    Write-Host "Dang xoa NuGet Cache..." -ForegroundColor Gray
    try {
        dotnet nuget locals all --clear
        Write-Host "-> Da don dep NuGet cache qua dotnet CLI." -ForegroundColor Green
    } catch {}
}
Clean-Directory -Path "$env:USERPROFILE\.nuget\packages\*" -Description "NuGet Local Package Folder"

# 4. Check Final Space
$driveC = Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DeviceID='C:'"
$finalFreeBytes = $driveC.FreeSpace
$finalFreeGB = [Math]::Round($finalFreeBytes / 1GB, 2)
$savedBytes = $finalFreeBytes - $initialFreeBytes
$savedGB = [Math]::Round($savedBytes / 1GB, 2)

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "Dung luong trong ban dau: $initialFreeGB GB" -ForegroundColor Yellow
Write-Host "Dung luong trong hien tai: $finalFreeGB GB" -ForegroundColor Green
if ($savedGB -gt 0) {
    Write-Host "-> DA GIAI PHONG DUOC: $savedGB GB!" -ForegroundColor Green -BackgroundColor Black
} else {
    Write-Host "-> O C hien tai da sach se hoac khong co them file gi de giai phong." -ForegroundColor Green
}
Write-Host "==================================================" -ForegroundColor Cyan
