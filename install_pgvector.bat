@echo off
REM Install pgvector for PostgreSQL 12 on Windows
REM Run this script as Administrator from "x64 Native Tools Command Prompt for VS 2019"

echo ============================================
echo pgvector Installation for PostgreSQL 12
echo ============================================

REM Set PostgreSQL path
set "PGROOT=D:\PostgreSQL\12"

REM Check if PGROOT exists
if not exist "%PGROOT%\bin\pg_config.exe" (
    echo ERROR: PostgreSQL not found at %PGROOT%
    echo Please update PGROOT variable in this script
    pause
    exit /b 1
)

echo PostgreSQL path: %PGROOT%

REM Go to temp directory
cd %TEMP%

REM Clone pgvector if not exists
if not exist "pgvector" (
    echo Cloning pgvector v0.7.4...
    git clone --branch v0.7.4 https://github.com/pgvector/pgvector.git
)

cd pgvector

echo.
echo Building pgvector...
nmake /F Makefile.win

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    echo Make sure you are running from "x64 Native Tools Command Prompt for VS 2019"
    pause
    exit /b 1
)

echo.
echo Installing pgvector...
nmake /F Makefile.win install

if errorlevel 1 (
    echo.
    echo ERROR: Installation failed!
    echo Try running as Administrator
    pause
    exit /b 1
)

echo.
echo ============================================
echo pgvector installed successfully!
echo ============================================
echo.
echo Now run in PostgreSQL:
echo   CREATE EXTENSION vector;
echo.
pause
