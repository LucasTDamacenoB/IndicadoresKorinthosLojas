@echo off
title Instalador de Dependencias - Painel IAF 2026
echo ========================================================
echo   Instalando dependencias do projeto (Python / Pip)...
echo ========================================================
echo.

set "PY_CMD="

REM 1. Tenta python direto
python --version >nul 2>&1
if %errorlevel% == 0 (
    set "PY_CMD=python"
    goto :RUN
)

REM 2. Tenta py launcher
py --version >nul 2>&1
if %errorlevel% == 0 (
    set "PY_CMD=py"
    goto :RUN
)

REM 3. Caminhos conhecidos do Python neste computador
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
    goto :RUN
)
if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Python\bin\python.exe"
    goto :RUN
)

:RUN
if "%PY_CMD%"=="" (
    echo [ERRO] Python nao foi encontrado no sistema!
    pause
    exit /b 1
)

echo Usando Python: %PY_CMD%
echo.
"%PY_CMD%" -m pip install --upgrade pip
"%PY_CMD%" -m pip install -r requirements.txt

echo.
echo ========================================================
echo   Instalacao concluida com sucesso!
echo   Para abrir o sistema, execute: iniciar_painel.bat
echo ========================================================
echo.
pause
