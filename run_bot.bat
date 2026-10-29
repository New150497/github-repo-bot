@echo off
chcp 65001 >nul
title GitHub Autonomous Agent
cd /d "%~dp0"
python repo_bot_fixed.py
pause

