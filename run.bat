@echo off
echo ========================================
echo  Android Stream Receiver
echo ========================================
echo.
echo Choose receiver type:
echo   1. Simple (Console only, no OpenCV)
echo   2. Single Camera (OpenCV)
echo   3. Dual Camera (OpenCV)
echo.
set /p choice="Enter choice (1-3): "

if "%choice%"=="1" (
    python receiver_simple.py
) else if "%choice%"=="2" (
    set /p camera="Camera (back/front): "
    python receiver_opencv.py --camera %camera%
) else if "%choice%"=="3" (
    python receiver_dual.py
) else (
    echo Invalid choice
)

pause