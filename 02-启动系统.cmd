@echo off
chcp 65001 >nul
title FluxCaption 启动系统
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0quick-client.ps1" -QuickAction start
pause
