@echo off
chcp 65001 >nul
title FluxCaption 查看日志
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0quick-client.ps1" -QuickAction logs
pause
