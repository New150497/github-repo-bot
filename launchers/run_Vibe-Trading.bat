@echo off
chcp 65001 >nul
title GitHub Repo Agent - Vibe-Trading
cd /d "%~dp0\.."
echo =================================================================
echo 🤖 Launching Dedicated Agent Terminal for: Vibe-Trading
echo =================================================================
python repo_bot_fixed.py "Vibe-Trading"
pause
