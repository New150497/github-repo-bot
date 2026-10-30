@echo off
chcp 65001 >nul
title GitHub Repo Agent - Hello-World
cd /d "%~dp0\.."
echo =================================================================
echo 🤖 Launching Dedicated Agent Terminal for: Hello-World
echo =================================================================
python repo_bot_fixed.py "Hello-World"
pause
