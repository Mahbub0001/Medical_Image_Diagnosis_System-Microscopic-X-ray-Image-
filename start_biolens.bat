@echo off
title BioLens - Start Server for Mobile App
color 0A

echo ======================================================================
echo             BIOLENS MEDICAL AI - SERVER LAUNCHER
echo ======================================================================
echo.

:: Detect current Local Wi-Fi IP
set LOCAL_IP=127.0.0.1
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set LOCAL_IP=%%a
)
set LOCAL_IP=%LOCAL_IP: =%

echo [1] Local PC IP Address detected : %LOCAL_IP%
echo.

:: Start FastAPI Backend Server in a new window
echo [2] Launching BioLens AI Backend (Port 10000)...
start "BioLens AI Backend" cmd /k "cd /d e:\capstone\updated\cap_software_2.0\backend && D:\anaconda\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 10000"

:: Start ngrok Tunnel in a new window
echo [3] Launching ngrok Tunnel...
start "BioLens ngrok Tunnel" cmd /k "ngrok http 10000"

echo.
echo ======================================================================
echo                     ALL SERVERS LAUNCHED!
echo ======================================================================
echo.
echo  HOW TO RUN FROM YOUR PHONE:
echo.
echo  METHOD 1 (Same Wi-Fi - Recommended):
echo    1. Connect phone to the same Wi-Fi as your PC.
echo    2. In BioLens App -> Sidebar -> "Server API"
echo    3. Enter URL: http://%LOCAL_IP%:10000
echo    4. Tap "Save & Apply".
echo.
echo  METHOD 2 (Anywhere / Mobile Data via ngrok):
echo    1. Look at the "BioLens ngrok Tunnel" window.
echo    2. Copy the "Forwarding" https URL (e.g. https://xxxx.ngrok-free.app)
echo    3. In BioLens App -> Sidebar -> "Server API" -> Paste it.
echo    4. Tap "Save & Apply".
echo.
echo ======================================================================
echo Press any key to close this launcher window (Servers will stay running).
pause >nul
