@echo off
chcp 65001 >nul
title GitHub Autonomous Agent - Telegram Remote Server
cd /d "%~dp0"

echo ===================================================================
echo 🤖 GitHub Autonomous Agent - Telegram Remote Server
echo ===================================================================
echo.

python telegram_remote.py

echo.
echo ===================================================================
echo সার্ভার বন্ধ হয়েছে। আবার চালু করতে এই উইন্ডো রিস্টার্ট করুন।
echo ===================================================================
pause
