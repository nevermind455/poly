#!/bin/bash
# Run on VPS to pull new bot from GitHub and restart. No nano needed.
# Usage: cd ~/poly && bash update_and_restart.sh

set -e
cd "$(dirname "$0")"

echo "Pulling latest from GitHub..."
git pull origin master

echo "Stopping old bot..."
pkill -f "venv/bin/python3.*bot.py" 2>/dev/null || pkill -f "python3 bot.py" 2>/dev/null || true
sleep 2

echo "Starting bot..."
nohup venv/bin/python3 -u bot.py >> bot.log 2>&1 &

echo "Done. Bot restarted. View log: tail -f ~/poly/bot.log"
