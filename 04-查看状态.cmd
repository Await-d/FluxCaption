@echo off
chcp 65001 >nul
title FluxCaption 查看状态
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0quick-client.ps1" -QuickAction status
pause
