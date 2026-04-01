@echo off
title P2P Calc — Build Tool
color 0A
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   USDT-INR P2P Calc  —  Windows Builder  ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install from https://python.org
    pause & exit /b 1
)

echo  [1/4]  Installing dependencies...
pip install customtkinter requests pyinstaller --quiet --upgrade
if errorlevel 1 (
    echo  [ERROR] pip install failed.
    pause & exit /b 1
)

echo  [2/4]  Cleaning old build...
if exist build  rmdir /s /q build
if exist dist   rmdir /s /q dist

echo  [3/4]  Building EXE with PyInstaller...
pyinstaller p2pcalc.spec --noconfirm
if errorlevel 1 (
    echo  [ERROR] PyInstaller failed. See above for details.
    pause & exit /b 1
)

echo  [4/4]  Done!
echo.
echo  ✓  Your EXE is at:  dist\P2PCalc.exe
echo.
echo  Double-click dist\P2PCalc.exe to run the app.
echo  Share that single file — no install needed.
echo.
pause
