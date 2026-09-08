@echo off
title Enviar Projeto para o GitHub - Painel IAF 2026
cd /d "%~dp0"
echo ========================================================
echo   Enviando arquivos para o GitHub...
echo   Repositorio: LucasTDamacenoB/IndicadoresKorinthosLojas
echo ========================================================
echo.

git branch -M main
git remote remove origin 2>nul
git remote add origin https://github.com/LucasTDamacenoB/IndicadoresKorinthosLojas.git
git add .
git commit -m "Deploy Painel Indicadores Lojas - IAF 2026" 2>nul
git push -u origin main --force

echo.
echo ========================================================
if %errorlevel% equ 0 (
    echo   [SUCESSO] Arquivos enviados com sucesso para o GitHub!
    echo   Agora va ao Streamlit Cloud para criar/reiniciar o app.
) else (
    echo   [AVISO] Verifique a mensagem acima para concluir o login.
)
echo ========================================================
echo.
pause
