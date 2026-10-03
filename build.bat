@echo off
echo ======================================================================
echo BUILDING OBSESSION MATRIX STANDALONE EXECUTABLE
echo ======================================================================
echo.

echo [1/3] Running Unit Tests...
python run_tests.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Unit tests failed! Aborting build.
    exit /b %ERRORLEVEL%
)

echo.
echo [2/3] Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo [3/3] Executing PyInstaller...
pyinstaller --noconfirm ObsessionMatrix.spec

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ======================================================================
    echo BUILD SUCCESSFUL!
    echo Final Executable: dist\ObsessionMatrix\ObsessionMatrix.exe
    echo ======================================================================
) else (
    echo.
    echo [ERROR] Build failed! Check PyInstaller output above.
)
