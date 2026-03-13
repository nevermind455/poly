#!/bin/bash
# Run this ON the VPS to pull latest code from GitHub
# Usage: bash pull.sh   (or chmod +x pull.sh && ./pull.sh)

set -e
cd "$(dirname "$0")"

echo "Pulling latest from GitHub..."
git pull origin master

echo "Done. Restart the bot if it's running (e.g. systemctl restart polybot or kill and run again)."
