@echo off
chcp 65001 >nul
title FluxCaption 停止系统
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0quick-client.ps1" -QuickAction stop
pause
