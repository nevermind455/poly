@echo off
title Polymarket BTC Bot - 24/7
color 0A

echo ============================================
echo   POLYMARKET BOT - 24/7 AUTO-RESTART
echo   Press Ctrl+C twice to fully stop
echo ============================================
echo.

:loop
echo [%date% %time%] Starting bot...
python real_bot.py
echo.
echo [%date% %time%] Bot stopped. Restarting in 10 seconds...
echo Press Ctrl+C now if you want to stop permanently.
timeout /t 10
goto loop
