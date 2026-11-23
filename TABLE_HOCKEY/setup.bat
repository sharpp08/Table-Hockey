@echo off
REM Installs everything Table Hockey needs into the active Python environment.
REM Run this from the project folder (D:\Yorme\Table Hockey) with the venv activated.

python -m ensurepip --upgrade
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Done. Checking pygame...
python -c "import pygame; print('pygame-ce', pygame.version.ver, 'is ready')"
pause
