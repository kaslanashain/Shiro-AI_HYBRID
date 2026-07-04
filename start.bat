@echo off
title Shiro AI Server
cd /d "%~dp0"

echo.
echo  ============================================
echo    SHIRO AI - Start (tanpa error port)
echo  ============================================
echo.

REM Matikan server lama di port 5000 (jika ada)
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5000" ^| findstr "LISTENING"') do (
    echo  [OK] Menutup server lama ^(PID %%a^)...
    taskkill /PID %%a /F >nul 2>&1
)

timeout /t 1 /nobreak >nul

if exist "venv\Scripts\python.exe" (
    set "PY=venv\Scripts\python.exe"
) else (
    set "PY=py"
)

echo  [OK] Memulai server...
echo  [OK] Buka: http://127.0.0.1:5000
echo  [OK] Stop: tekan Ctrl+C di jendela ini
echo.

start "" cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:5000"

"%PY%" main.py

echo.
echo  Server berhenti. Tekan tombol apapun untuk keluar...
pause >nul
