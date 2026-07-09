@echo off
title Shiro AI Desktop
cd /d "%~dp0"

echo.
echo  ============================================
echo    SHIRO AI - Desktop Companion
echo  ============================================
echo.

if exist "venv\Scripts\python.exe" (
    set "PY=venv\Scripts\python.exe"
    set "PYW=venv\Scripts\pythonw.exe"
) else (
    set "PY=py"
    set "PYW=pyw"
)

echo  [OK] Preflight: model offline, GGUF, dependensi...
"%PY%" scripts\preflight_desktop.py
if errorlevel 1 (
    echo.
    echo  [ERROR] Preflight gagal. Periksa Python dan Ollama.
    pause
    exit /b 1
)

for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5000" ^| findstr "LISTENING"') do (
    echo  [OK] Server sudah jalan di port 5000
    goto :launch
)

echo  [OK] Memulai desktop companion...
echo  [OK] Icon tray ada di taskbar (kanan bawah)
echo  [OK] Klik kanan tray: autostart Windows, show/hide, keluar
echo.

:launch
if exist "venv\Scripts\pythonw.exe" (
    venv\Scripts\pip.exe install pywebview pystray pillow -q 2>nul
    venv\Scripts\pythonw.exe desktop_launcher.py
) else (
    py -m pip install pywebview pystray pillow -q 2>nul
    pyw desktop_launcher.py 2>nul || py desktop_launcher.py
)

if errorlevel 1 (
    echo.
    echo  Gagal. Pastikan pywebview terpasang:
    echo    pip install pywebview pystray pillow
    echo.
    pause
    exit /b 1
)
