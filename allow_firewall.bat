@echo off
:: Batch script to allow BioLens Backend Port 10000 through Windows Firewall
title BioLens - Allow Firewall Port 10000

echo ========================================================
echo   BioLens Backend - Windows Firewall Port 10000 Setup
echo ========================================================
echo.

:: Check for administrative permissions
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script requires Administrator privileges!
    echo Please right-click on this file and select "Run as administrator".
    echo.
    pause
    exit /b 1
)

echo Adding Inbound Rule for Port 10000 (TCP)...
netsh advfirewall firewall add rule name="BioLens Backend Port 10000" dir=in action=allow protocol=TCP localport=10000

echo.
echo ========================================================
echo [SUCCESS] Windows Firewall is now configured!
echo Your phone on the same Wi-Fi can now connect to:
echo http://192.168.10.230:10000
echo ========================================================
echo.
pause
