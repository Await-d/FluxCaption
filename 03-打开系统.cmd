@echo off
chcp 65001 >nul
title FluxCaption 打开系统
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0quick-client.ps1" -QuickAction open
