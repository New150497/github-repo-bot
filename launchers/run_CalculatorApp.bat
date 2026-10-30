@echo off
chcp 65001 >nul
title GitHub Repo Agent - CalculatorApp
cd /d "%~dp0\.."
echo =================================================================
echo 🤖 Launching Dedicated Agent Terminal for: CalculatorApp
echo =================================================================
python repo_bot_fixed.py "CalculatorApp"
pause
