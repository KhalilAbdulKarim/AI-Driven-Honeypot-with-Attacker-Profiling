#!/bin/bash
# Honeypot deployment script for Ubuntu 22.04/24.04
# Usage: bash deploy/install.sh

set -e

PROJECT_DIR="/home/ubuntu/AI-Driven-Honeypot-with-Attacker-Profiling"
VENV_DIR="$PROJECT_DIR/honeypot/.venv"
SUPERVISOR_CONF="/etc/supervisor/conf.d/honeypot.conf"

echo "[1/6] Installing system dependencies..."
sudo apt update -qq
sudo apt install -y python3 python3-pip python3-venv supervisor

echo "[2/6] Installing Python packages..."
cd $PROJECT_DIR
source $VENV_DIR/bin/activate
pip install -q paramiko requests anthropic python-dotenv flask flask-cors

echo "[3/6] Creating required directories..."
mkdir -p data logs keys

echo "[4/6] Installing supervisor config..."
sudo cp deploy/supervisor.conf $SUPERVISOR_CONF
sudo supervisorctl reread
sudo supervisorctl update

echo "[5/6] Starting services..."
sudo supervisorctl start all

echo "[6/6] Done!"
sudo supervisorctl status
echo ""
echo "Honeypot running on port 2222"
echo "Dashboard running on port 5002"