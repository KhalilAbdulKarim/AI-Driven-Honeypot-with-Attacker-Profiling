#!/bin/bash
# Run after git pull to update and restart services
# Usage: bash deploy/update.sh

set -e

PROJECT_DIR="/home/ubuntu/AI-Driven-Honeypot-with-Attacker-Profiling"
SUPERVISOR_CONF="/etc/supervisor/conf.d/honeypot.conf"

echo "[1/3] Updating supervisor config..."
sudo cp deploy/supervisor.conf $SUPERVISOR_CONF
sudo supervisorctl reread
sudo supervisorctl update

echo "[2/3] Restarting services..."
sudo supervisorctl restart all

echo "[3/3] Status:"
sudo supervisorctl status