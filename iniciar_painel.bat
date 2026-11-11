@echo off
title Painel IAF 2026 - O Boticario (CP Korinthos)
echo ========================================================
echo   Iniciando Painel de Indicadores IAF 2026...
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
    echo Verifique a instalacao do Python.
    pause
    exit /b 1
)

echo Usando Python: %PY_CMD%
echo.
"%PY_CMD%" -m streamlit run app.py

pause
