@echo off
cd /d "%~dp0"
echo Building Mate Helper for Windows...
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Create the executable
pyinstaller ^
    --name "MateHelper" ^
    --onefile ^
    --windowed ^
REM --icon desktop_pet\models\default_models\pt\kasane_teto\sprites\icon.ico ^
    --add-data "desktop_pet\models;desktop_pet\models" ^
    --hidden-import "gi" ^
    --hidden-import "gi.repository.Gtk" ^
    --hidden-import "gi.repository.Gdk" ^
    --hidden-import "gi.repository.GdkPixbuf" ^
    --hidden-import "gi.repository.GLib" ^
    --hidden-import "gi.repository.Pango" ^
    --hidden-import "gi.repository.PangoCairo" ^
    --hidden-import "cairo" ^
    --hidden-import "webrtcvad" ^
    --hidden-import "sounddevice" ^
    --hidden-import "numpy" ^
    --hidden-import "PIL._tkinter_finder" ^
    desktop_pet\main.py

echo.
echo Build complete! Check the dist\ folder for MateHelper.exe
pause
