@echo off
title Mió Baixador do Youtube - Instalação
echo Instalando dependências (yt-dlp, customtkinter, ffmpeg)...
pip install yt-dlp customtkinter imageio-ffmpeg -q
echo.
echo Abrindo o app...
python app.py
pause
