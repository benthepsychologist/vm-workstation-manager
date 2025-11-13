#!/bin/bash
# Run this script on the test VM after SSH-ing in to set up your environment

set -e

echo "=========================================="
echo "VM Environment Setup"
echo "=========================================="
echo ""

# Update package list
echo "📦 Updating package list..."
sudo apt-get update -qq

# Install neovim
echo "📦 Installing neovim..."
sudo apt-get install -y neovim curl wget -qq

# Install Docker CE
echo "📦 Installing Docker CE..."
# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
    curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
fi

# Add the repository to Apt sources
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update -qq
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -qq

# Add current user to docker group
sudo usermod -aG docker $USER

echo "✅ Docker installed: $(docker --version)"

# Install code-server
echo "📦 Installing code-server..."
curl -fsSL https://code-server.dev/install.sh | sh

# Configure code-server
mkdir -p ~/.config/code-server
cat > ~/.config/code-server/config.yaml <<EOF
bind-addr: 127.0.0.1:8080
auth: none
cert: false
EOF

# Create systemd service for code-server
sudo tee /etc/systemd/system/code-server.service > /dev/null <<EOF
[Unit]
Description=code-server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/mnt/home/user
ExecStart=/usr/bin/code-server --config ~/.config/code-server/config.yaml /mnt/home/user
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Enable and start code-server
sudo systemctl daemon-reload
sudo systemctl enable code-server
sudo systemctl start code-server

echo "✅ code-server installed and running on port 8080"
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Installed:"
echo "  - neovim: $(nvim --version | head -1)"
echo "  - Docker: $(docker --version)"
echo "  - code-server: $(code-server --version)"
echo ""
echo "To access code-server:"
echo "  1. From your local machine, run: vmws tunnel"
echo "  2. Visit: http://localhost:8080"
echo "  3. No password required (secured by IAP tunnel)"
echo ""
echo "Note: You may need to log out and back in for Docker group membership to take effect."
