@echo off
title Instalador de Dependencias - Painel IAF 2026
echo ========================================================
echo   Instalando dependencias do projeto (Python / Pip)...
echo ========================================================
echo.

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo ========================================================
echo   Instalacao concluida com sucesso!
echo   Para abrir o sistema, execute: iniciar_painel.bat
echo ========================================================
echo.
pause
