#!/bin/bash
# VPS Setup Script for Nigeria Logistics Scraper
# Run on fresh Ubuntu 22.04 (ARM or x86)

set -euo pipefail

echo "=== Setting up Nigeria Logistics Scraper on VPS ==="

# Update system
apt-get update && apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker ubuntu

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install Python and deps
apt-get install -y python3 python3-pip python3-venv git curl jq cron htop

# Create scraper user
useradd -m -s /bin/bash scraper 2>/dev/null || true
usermod -aG docker scraper

# Setup directories
mkdir -p /opt/scraper/{data,logs,scripts,output,queries}
chown -R scraper:scraper /opt/scraper

# Copy application files (assumes you've cloned the repo)
cd /opt/scraper
# git clone your-repo-url .  # or copy from local

# Create Python venv
sudo -u scraper python3 -m venv /opt/scraper/venv
sudo -u scraper /opt/scraper/venv/bin/pip install pandas requests python-dotenv

# Install systemd service
cp /opt/scraper/deploy/vps/systemd/scraper.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable scraper

# Setup cron for daily runs (optional)
cat > /etc/cron.d/scraper << 'CRONEOF'
# Run daily at 2 AM
0 2 * * * scraper /opt/scraper/venv/bin/python /opt/scraper/scripts/scraper.py >> /opt/scraper/logs/cron.log 2>&1
CRONEOF

# Pull Docker image
docker pull gosom/google-maps-scraper

# Setup logrotate
cat > /etc/logrotate.d/scraper << 'LOGEOF'
/opt/scraper/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 scraper scraper
}
LOGEOF

echo "=== VPS Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Copy your scripts to /opt/scraper/scripts/"
echo "2. Copy your master data to /opt/scraper/data/"
echo "3. Start service: systemctl start scraper"
echo "4. Check logs: journalctl -u scraper -f"
echo "5. Or run manually: sudo -u scraper /opt/scraper/venv/bin/python /opt/scraper/scripts/scraper.py"
