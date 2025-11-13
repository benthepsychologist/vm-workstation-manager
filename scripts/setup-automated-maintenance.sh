#!/bin/bash
# Setup automated maintenance tasks on the VM
# - Weekly backups
# - Daily security updates
# - Weekly auto-reboot if kernel updated

set -e

echo "=========================================="
echo "Setting up automated maintenance"
echo "=========================================="
echo ""

# Get VM name and zone from metadata
VM_NAME=$(curl -s "http://metadata.google.internal/computeMetadata/v1/instance/name" -H "Metadata-Flavor: Google")
ZONE=$(curl -s "http://metadata.google.internal/computeMetadata/v1/instance/zone" -H "Metadata-Flavor: Google" | cut -d'/' -f4)

echo "VM: $VM_NAME"
echo "Zone: $ZONE"
echo ""

# 1. Setup weekly backups (Sunday 2 AM)
echo "📦 Setting up weekly backups..."
sudo tee /usr/local/bin/vm-weekly-backup.sh > /dev/null <<'EOF'
#!/bin/bash
# Weekly backup script - snapshots the data disk

VM_NAME=$(curl -s "http://metadata.google.internal/computeMetadata/v1/instance/name" -H "Metadata-Flavor: Google")
ZONE=$(curl -s "http://metadata.google.internal/computeMetadata/v1/instance/zone" -H "Metadata-Flavor: Google" | cut -d'/' -f4)
DISK_NAME="${VM_NAME}-disk"
SNAPSHOT_NAME="${VM_NAME}-auto-backup-$(date +%Y%m%d-%H%M%S)"

echo "[$(date)] Starting weekly backup: $SNAPSHOT_NAME"

gcloud compute disks snapshot "$DISK_NAME" \
  --snapshot-names="$SNAPSHOT_NAME" \
  --zone="$ZONE" \
  --storage-location="$(echo $ZONE | sed 's/-[a-z]$//')"

if [ $? -eq 0 ]; then
    echo "[$(date)] Backup successful: $SNAPSHOT_NAME"

    # Keep only last 4 weekly backups (1 month)
    SNAPSHOTS=$(gcloud compute snapshots list --filter="name~${VM_NAME}-auto-backup" --format="value(name)" --sort-by="~creationTimestamp" | tail -n +5)
    if [ ! -z "$SNAPSHOTS" ]; then
        echo "[$(date)] Cleaning up old backups..."
        echo "$SNAPSHOTS" | while read snapshot; do
            echo "[$(date)] Deleting old snapshot: $snapshot"
            gcloud compute snapshots delete "$snapshot" --quiet
        done
    fi
else
    echo "[$(date)] Backup failed!"
    exit 1
fi
EOF

sudo chmod +x /usr/local/bin/vm-weekly-backup.sh

# Create cron job for weekly backups (Sunday 2 AM)
echo "0 2 * * 0 /usr/local/bin/vm-weekly-backup.sh >> /var/log/vm-backup.log 2>&1" | sudo tee /etc/cron.d/vm-weekly-backup > /dev/null

echo "✅ Weekly backups configured (Sundays 2 AM)"
echo "   - Keeps last 4 backups (1 month)"
echo "   - Logs: /var/log/vm-backup.log"
echo ""

# 2. Setup automatic security updates
echo "📦 Setting up automatic security updates..."

sudo apt-get install -y unattended-upgrades apt-listchanges

# Configure unattended-upgrades
sudo tee /etc/apt/apt.conf.d/50unattended-upgrades > /dev/null <<'EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}";
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
    "${distro_id}ESM:${distro_codename}-infra-security";
};

Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::InstallOnShutdown "false";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Automatic-Reboot-WithUsers "false";
EOF

# Enable automatic updates
sudo tee /etc/apt/apt.conf.d/20auto-upgrades > /dev/null <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
APT::Periodic::Unattended-Upgrade "1";
EOF

echo "✅ Automatic security updates enabled"
echo "   - Runs daily"
echo "   - Security patches only"
echo "   - No automatic reboots"
echo ""

# 3. Setup weekly reboot if kernel updated (Sunday 3 AM)
echo "📦 Setting up weekly reboot check..."
sudo tee /usr/local/bin/vm-check-reboot.sh > /dev/null <<'EOF'
#!/bin/bash
# Check if reboot is needed (e.g., kernel update) and reboot

if [ -f /var/run/reboot-required ]; then
    echo "[$(date)] Reboot required. Rebooting now..."
    sudo reboot
else
    echo "[$(date)] No reboot required."
fi
EOF

sudo chmod +x /usr/local/bin/vm-check-reboot.sh

# Create cron job for weekly reboot check (Sunday 3 AM)
echo "0 3 * * 0 /usr/local/bin/vm-check-reboot.sh >> /var/log/vm-reboot-check.log 2>&1" | sudo tee /etc/cron.d/vm-reboot-check > /dev/null

echo "✅ Weekly reboot check configured (Sundays 3 AM)"
echo "   - Only reboots if kernel/system update requires it"
echo "   - Logs: /var/log/vm-reboot-check.log"
echo ""

# 4. Create log rotation config
echo "📦 Setting up log rotation..."
sudo tee /etc/logrotate.d/vm-maintenance > /dev/null <<'EOF'
/var/log/vm-backup.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
}

/var/log/vm-reboot-check.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
}
EOF

echo "✅ Log rotation configured"
echo ""

echo "=========================================="
echo "Automated Maintenance Setup Complete!"
echo "=========================================="
echo ""
echo "Configured:"
echo "  ✅ Weekly backups (Sundays 2 AM)"
echo "     - Keeps last 4 backups"
echo "     - View logs: sudo tail -f /var/log/vm-backup.log"
echo ""
echo "  ✅ Daily security updates"
echo "     - Automatic security patches"
echo "     - No automatic reboots"
echo ""
echo "  ✅ Weekly reboot check (Sundays 3 AM)"
echo "     - Only if kernel/system update requires it"
echo "     - View logs: sudo tail -f /var/log/vm-reboot-check.log"
echo ""
echo "To test backup manually:"
echo "  sudo /usr/local/bin/vm-weekly-backup.sh"
echo ""
echo "To check for updates now:"
echo "  sudo unattended-upgrade --dry-run"
echo ""
