@echo off
:: This PORTABLE script copies files relative to its location to a fixed destination.

:: Set the fixed destination folder
set "tmp=%~dp0\tmp242"
set "destination=C:\Users\rosie\Downloads\op_rando_window\current"

:: Create the destination directory if it doesn't exist
if not exist "%destination%" mkdir "%destination%"
if not exist "%tmp%" mkdir "%tmp%"

echo Copying files from the script's directory...
echo.

:: %~dp0 refers to the Drive and Path of the batch file.
:: This copies files from the same folder the .bat file is in.
copy "%~dp0build.rs" "%tmp%"
copy "%~dp0Cargo.toml" "%tmp%"
copy "%~dp0build_rename.bat" "%destination%"

:: Copy the CONTENTS of the src directory, also relative to the script's location.
xcopy "%~dp0src\*" "%tmp%\" /S /E /I /Y

:: rename files to add gui_testing to front of their names
for %%f in ("%tmp%\*") do ren "%%f" "op_rando_%%~nxf"


:: Now move the renamed files to the destination
xcopy "%~dp0tmp242\*" "%destination%\" /S /E /I /Y
:: Clean up the temporary folder
rd /S /Q "%tmp%"

echo.
echo All files copied successfully!