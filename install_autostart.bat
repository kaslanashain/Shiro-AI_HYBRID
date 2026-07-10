@echo off
title Shiro AI - Pasang Autostart Windows
cd /d "%~dp0"

echo.
echo  ============================================
echo    SHIRO AI - Autostart Desktop
echo  ============================================
echo.
echo  Shiro AI akan jalan otomatis saat:
echo    - Windows login / nyalakan laptop
echo    - Buka laptop setelah sleep (unlock)
echo.

if exist "venv\Scripts\python.exe" (
    set "PY=venv\Scripts\python.exe"
) else (
    set "PY=py"
)

"%PY%" scripts\desktop_autostart.py install
if errorlevel 1 (
    echo  [ERROR] Gagal memasang autostart.
    pause
    exit /b 1
)

echo.
echo  [OK] Autostart terpasang!
echo  [OK] Shortcut Startup: %%APPDATA%%\...\Startup\Shiro_AI_Desktop.bat
echo  [OK] Registry Run: HKCU\Software\...\Run\Shiro AI Desktop
echo.
echo  Restart laptop atau logout/login untuk uji coba.
echo.
pause
