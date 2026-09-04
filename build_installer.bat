@echo off
title Build - Mió Baixador do Youtube
echo Buildando o app com PyInstaller...
python -m PyInstaller app.spec --noconfirm
echo.
echo Criando instalador com Inno Setup...
"C:\Users\cfcfa\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer.iss
echo.
echo ============================================
echo  Instalador gerado: Output\Setup_MioBaixador.exe
echo ============================================
pause
