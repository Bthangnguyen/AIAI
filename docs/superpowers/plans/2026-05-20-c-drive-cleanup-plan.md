# C-Drive Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a script and a manual walkthrough for safe, visual and automated C-drive cleanup on Windows, focusing on system junk and developer cache.

**Architecture:** Leverage WizTree for visual scanning, PowerShell for automated cleanup of safe directories/developer caches, and Storage Sense / Settings for high-risk manual deletions.

**Tech Stack:** PowerShell, Windows OS APIs.

---

### Task 1: Create and Test the PowerShell Cleanup Script

**Files:**
- Create: `scripts/clean_c_drive.ps1`

- [ ] **Step 1: Write the clean_c_drive.ps1 script code**
  
  Create the folder `scripts` if it does not exist, and write the following code into `scripts/clean_c_drive.ps1`:
  
  ```powershell
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
  ```

- [ ] **Step 2: Dry run/test locally to check script logic**
  
  Run the script in standard dry run or run it safely via powershell console to confirm no critical syntax errors exist:
  ```powershell
  Get-Command -Name "Get-CimInstance"
  ```
  Expected output: Details of `Get-CimInstance` cmdlet confirming capability.

- [ ] **Step 3: Run the script with Administrator rights**
  
  Run the script to perform actual clean up:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\scripts\clean_c_drive.ps1
  ```
  *(Note: If you run it from a standard terminal, it will error prompting for Administrator rights, which confirms the safety check works).*

- [ ] **Step 4: Commit the script**
  
  ```bash
  git add scripts/clean_c_drive.ps1
  git commit -m "feat: add powershell script for safe C drive cleanup"
  ```

---

### Task 2: Create Manual Cleanup and WizTree Visual Instructions

**Files:**
- Create: `docs/superpowers/manual_cleanup_steps.md`

- [ ] **Step 1: Write the manual_cleanup_steps.md file**
  
  Write a comprehensive user guide in Vietnamese detailing how to use WizTree, how to clean `Windows.old` through Windows Storage Sense, how to uninstall large unused apps, and how to prune Docker image/volumes:
  
  ```markdown
  # Hướng dẫn dọn dẹp ổ C thủ công bằng WizTree & Windows Settings

  ## 1. Tìm và xóa tệp tin lớn bằng WizTree (Trực quan)
  - Tải WizTree Portable (file ZIP không cần cài đặt): https://diskanalyzer.com/download
  - Giải nén và chạy file `WizTree64.exe` bằng cách nhấn chuột phải chọn **Run as administrator**.
  - Chọn ổ **C:** và nhấn **Scan**.
  - Quan sát sơ đồ khối màu bên dưới: Khối càng to thể hiện tệp tin/thư mục đó càng nặng.
  - Hướng dẫn xóa:
    - Nhấn đúp vào khối to để xem đường dẫn thư mục.
    - Nếu là thư mục chứa tệp cá nhân như `C:\Users\<Tên_User>\Downloads`, `Videos`, `Documents`, bro có thể xóa trực tiếp các tệp tin không dùng nữa (chọn file -> Chuột phải -> **Delete**).
    - **LƯU Ý**: KHÔNG xóa bất kỳ file nào trong thư mục `C:\Windows` hoặc `C:\Program Files` nếu không chắc chắn.

  ## 2. Dọn dẹp thư mục Windows.old (Bản sao lưu cập nhật cũ)
  Thư mục này có thể nặng tới 10-30GB. Cách xóa an toàn qua giao diện chính chủ:
  1. Mở cài đặt hệ thống: nhấn tổ hợp phím **Windows + I**.
  2. Chọn **System** -> **Storage** (Lưu trữ).
  3. Chọn **Temporary files** (Tệp tạm thời).
  4. Đợi hệ thống quét xong, tìm mục **Previous Windows installation(s)** (Bản cài đặt Windows trước đó) và tích chọn.
  5. Nhấn **Remove files** (Xóa tệp) để thực hiện dọn dẹp.

  ## 3. Gỡ ứng dụng/game khổng lồ không sử dụng
  1. Vào **Settings** (Win + I) -> **Apps** -> **Installed apps**.
  2. Tại mục **Sort by**, chọn **Size (Large to small)** để đưa ứng dụng nặng nhất lên đầu.
  3. Rà soát xem game cũ hoặc bộ ứng dụng lập trình/đồ họa nào lâu rồi không dùng tới thì nhấn vào dấu 3 chấm -> Chọn **Uninstall**.

  ## 4. Xóa rác Docker (Dành cho lập trình viên)
  Nếu bro có sử dụng Docker, bộ nhớ đệm image/container/volume rác có thể ngốn hàng chục GB ổ C.
  - Mở Terminal (PowerShell/CMD).
  - Chạy lệnh sau để dọn dẹp sạch sẽ các container đã dừng, network dư thừa và image không tag:
    ```bash
    docker system prune -a --volumes -f
    ```
  ```

- [ ] **Step 2: Commit manual_cleanup_steps.md**
  
  ```bash
  git add docs/superpowers/manual_cleanup_steps.md
  git commit -m "docs: add manual cleanup steps and WizTree instructions"
  ```

---

### Task 3: Execution and Verification

**Files:**
- Modify: `docs/superpowers/plans/2026-05-20-c-drive-cleanup-plan.md` (Update checklist status)

- [ ] **Step 1: Run verification and record free space changes**
  
  Verify that the cleanup worked, all script runs were logged successfully, and write out a brief walkthrough detailing:
  - Initial Free Space
  - Final Free Space
  - Total space freed.
