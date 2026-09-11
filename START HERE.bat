@echo off
title Admission Guru - Server
color 1F
echo.
echo  =====================================================
echo    ADMISSION GURU - Starting Server
echo  =====================================================
echo.
echo  The server will start in a moment...
echo  Once you see "Running on http://127.0.0.1:5000"
echo  open your browser and go to:
echo.
echo       http://localhost:5000
echo.
echo  Press Ctrl+C to stop the server.
echo  =====================================================
echo.
python "%~dp0start_server.py"
pause
