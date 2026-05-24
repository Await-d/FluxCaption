@echo off
chcp 65001 >nul
title FluxCaption 首次配置
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0quick-client.ps1" -QuickAction setup
pause
