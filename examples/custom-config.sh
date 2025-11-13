#!/bin/bash
# Example: Customize your VM configuration

# This shows how to modify the VM creation to your needs

# 1. Change machine type (for more power)
# Edit: scripts/create-test-vm.sh
# Change: MACHINE_TYPE="e2-standard-2"
# To: MACHINE_TYPE="e2-standard-4"  # 4 vCPU, 16GB RAM

# 2. Change zone
# vmws config --zone=us-west1-a

# 3. Add custom software
# Edit: scripts/setup-vm-environment.sh
# Add before the final echo:
#
# echo "📦 Installing additional tools..."
# sudo apt-get install -y \
#   postgresql-client \
#   redis-tools \
#   jq

# 4. Customize code-server extensions
# After VM is created, SSH in and:
# code-server --install-extension ms-python.python
# code-server --install-extension golang.go

# 5. Change auto-shutdown timeout
# SSH into VM:
# sudo vim /usr/local/bin/vm-auto-shutdown.sh
# Change: IDLE_TIMEOUT_MINUTES=120
# To: IDLE_TIMEOUT_MINUTES=240  # 4 hours
# Then: sudo systemctl restart vm-auto-shutdown

# 6. Use a different disk size
# Edit: scripts/create-test-vm.sh
# Change: DISK_SIZE="200GB"
# To: DISK_SIZE="500GB"

echo "See this file for customization examples"
echo "Edit the scripts directly, then run: vmws create"
