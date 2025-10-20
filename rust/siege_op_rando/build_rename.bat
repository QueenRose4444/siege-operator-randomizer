@echo off
REM Change the current directory to the script's directory.
REM This ensures that cargo can find Cargo.toml, regardless of where the script is called from.
pushd %~dp0

echo Building the release version...
cargo build --release

REM Check if the build was successful
if %errorlevel% neq 0 (
    echo Build failed. >&2
    popd
    exit /b %errorlevel%
)

echo Build successful.

REM --- ROBUST VERSION PARSING ---
REM Get version from Cargo.toml by splitting the line at the '=' sign to avoid ambiguity.
for /f "tokens=2 delims==" %%v in ('findstr "^version" Cargo.toml') do (
    set "VERSION=%%v"
)
REM Clean up the version string (remove leading spaces and quotes).
set VERSION=%VERSION: =%
set VERSION=%VERSION:"=%

REM --- SETUP FILE PATHS ---
set EXE_NAME=r6_op_rando
set ORIGINAL_EXE_PATH=target\release\%EXE_NAME%.exe
set BUILDS_DIR=builds
set NEW_EXE_NAME=%EXE_NAME%_v%VERSION%.exe
set NEW_EXE_PATH=%BUILDS_DIR%\%NEW_EXE_NAME%

REM Create the builds directory if it doesn't exist
echo.
echo Checking for builds directory...
if not exist "%BUILDS_DIR%" (
    echo Creating builds directory.
    mkdir "%BUILDS_DIR%"
)

REM Move and rename the executable
echo Moving executable to %NEW_EXE_PATH%...
move /Y "%ORIGINAL_EXE_PATH%" "%NEW_EXE_PATH%"

if %errorlevel% neq 0 (
    echo Failed to move the executable. Make sure it's not running. >&2
    popd
    exit /b %errorlevel%
)

echo.
echo Done! Your file is ready at: %NEW_EXE_PATH%

REM Restore the original directory
popd

