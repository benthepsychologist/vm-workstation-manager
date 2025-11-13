# VM Workstation Manager

> Replace Google Cloud Workstations with self-managed VMs and save $91-124/month

A simple CLI tool to manage self-hosted development VMs as drop-in replacements for Google Cloud Workstations.

## Features

✅ **Same functionality as Cloud Workstations**
- Web-based VS Code (code-server)
- Docker, neovim, full dev environment
- IAP authentication & secure access
- Auto-shutdown after 2hr idle

✅ **Massive cost savings**
- Cloud Workstation: **$150/month**
- Self-managed VM: **$26-59/month**
- **Save $91-124/month (61-83%)**

✅ **Simple CLI interface**
```bash
vmws create   # Create VM from workstation
vmws start    # Start VM
vmws tunnel   # Connect to code-server
vmws stop     # Stop VM
```

## Quick Start

### 1. Install (on your local machine)

```bash
# Clone the repo
git clone https://github.com/yourusername/vm-workstation-manager.git
cd vm-workstation-manager

# Install CLI
./bin/vmws install

# Or manually
cp bin/vmws /usr/local/bin/vmws
chmod +x /usr/local/bin/vmws
```

### 2. Create VM (from Cloud Workstation)

```bash
# SSH into your Cloud Workstation
# Clone this repo there too

cd vm-workstation-manager
./bin/vmws create
```

This will:
- Snapshot your workstation disk
- Create a new VM with your data
- Install Docker, code-server, neovim
- Set up auto-shutdown (2hr idle)
- Generate detailed report

**Time:** ~6 minutes

### 3. Use from your local machine

```bash
# Start VM
vmws start

# Connect to code-server (web VS Code)
vmws tunnel
# Visit http://localhost:8080

# Or SSH directly
vmws ssh

# Stop VM when done
vmws stop
```

## Commands

| Command | Description |
|---------|-------------|
| `vmws create` | Create VM from workstation (run from workstation) |
| `vmws start` | Start stopped VM |
| `vmws stop` | Stop VM to save money |
| `vmws status` | Show VM status |
| `vmws connect` / `vmws ssh` | SSH into VM |
| `vmws tunnel` | Start IAP tunnel to code-server |
| `vmws logs` | View auto-shutdown logs |
| `vmws config` | Configure VM name/zone/project |
| `vmws delete` | Delete VM and all resources |
| `vmws install` | Install CLI on local machine |

## Configuration

```bash
# Interactive
vmws config

# Or specify directly
vmws config --vm-name my-dev-vm --zone us-central1-a --project my-project

# Config stored at: ~/.vmws/config
```

## Cost Breakdown

### Cloud Workstation
- **$150/month**
  - $6/month: e2-standard-2 VM
  - $144/month: Control plane (workstation cluster)

### Self-Managed VM (24/7)
- **$59/month**
  - $49/month: e2-standard-2 VM compute
  - $8/month: 200GB data disk
  - $2/month: 50GB boot disk
- **Savings: $91/month (61%)**

### Self-Managed VM (8hrs/day with auto-stop)
- **$26/month**
  - $16/month: Compute (8hrs × $0.067/hr × 30 days)
  - $10/month: Disks (always charged)
- **Savings: $124/month (83%)**

## Auto-Shutdown

Your VM automatically shuts down after **2 hours of idle time** (same as Cloud Workstations).

Tracks:
- SSH connections
- code-server connections

**Adjust timeout:**
```bash
vmws ssh
sudo vim /usr/local/bin/vm-auto-shutdown.sh
# Change IDLE_TIMEOUT_MINUTES=120
sudo systemctl restart vm-auto-shutdown
```

## What's Included

### Development Environment
- ✅ Docker CE (latest)
- ✅ code-server 4.105.1 (web-based VS Code)
- ✅ neovim 0.7.2
- ✅ git, gcloud, python3
- ✅ All your workstation data at `/mnt/home/user/`

### Automation
- ✅ Auto-shutdown after 2hr idle
- ✅ One-command start/stop
- ✅ IAP tunnel management
- ✅ Status monitoring

## Architecture

```
┌─────────────────────────┐
│   Local Machine (Mac)   │
│                         │
│   $ vmws start          │
│   $ vmws tunnel         │
└───────────┬─────────────┘
            │
            │ IAP Tunnel
            │
┌───────────▼─────────────┐
│   Google Cloud          │
│                         │
│   ┌─────────────────┐   │
│   │  Self-Managed   │   │
│   │     VM          │   │
│   │                 │   │
│   │  - code-server  │   │
│   │  - Docker       │   │
│   │  - Your data    │   │
│   │  - Auto-shutdown│   │
│   └─────────────────┘   │
│                         │
│   ┌─────────────────┐   │
│   │  Cloud          │   │
│   │  Workstation    │   │
│   │  (Optional)     │   │
│   └─────────────────┘   │
└─────────────────────────┘
```

## Comparison

| Feature | Cloud Workstation | Self-Managed VM |
|---------|------------------|----------------|
| **Cost** | $150/mo | $26-59/mo ⭐ |
| **Auto-shutdown** | ✅ 2hr idle | ✅ 2hr idle |
| **Web IDE** | ✅ Code OSS | ✅ code-server |
| **Docker** | ✅ | ✅ |
| **IAP Auth** | ✅ | ✅ |
| **Start method** | Click in console | `vmws start` |
| **Connect** | Click "Open" | `vmws tunnel` |
| **Updates** | Google manages | You manage |
| **Setup time** | Instant | 6 min (one-time) |

## Example Workflow

```bash
# Morning: Start your dev environment
vmws start

# Open web IDE
vmws tunnel &
open http://localhost:8080

# Work on your code
# VM auto-shuts down after 2hrs if idle

# Or stop manually when done
vmws stop
```

## Files Structure

```
vm-workstation-manager/
├── bin/
│   └── vmws                        # Main CLI tool
├── scripts/
│   ├── run-vm-test-workflow.sh     # Create VM workflow
│   ├── create-test-vm.sh           # Create VM only
│   ├── cleanup-test-vm.sh          # Delete resources
│   ├── setup-vm-environment.sh     # Install dev environment
│   ├── vm-auto-shutdown.sh         # Auto-shutdown monitor
│   ├── install-auto-shutdown.sh    # Install auto-shutdown
│   └── vm-startup-script.sh        # VM startup script
├── docs/
│   └── VM-AUTOMATION-GUIDE.md      # Detailed guide
├── examples/
│   └── custom-config.sh            # Customization examples
├── README.md                        # This file
├── QUICKSTART.md                    # Get started fast
├── CONTRIBUTING.md                  # Development guide
├── ARCHITECTURE.md                  # Deep technical details
└── LICENSE                          # MIT License
```

## Requirements

- Google Cloud account
- gcloud CLI installed
- Cloud Workstation (for initial VM creation)
- Compute Engine API enabled

## Troubleshooting

### VM won't start
```bash
vmws status
gcloud compute instances describe <vm-name> --zone=<zone>
```

### Can't connect to code-server
```bash
vmws ssh
sudo systemctl status code-server
sudo systemctl restart code-server
```

### Auto-shutdown not working
```bash
vmws logs
```

## Migration Guide

**From Cloud Workstation to self-managed VM:**

1. **Test the VM** (keep both running)
   ```bash
   # On workstation
   vmws create

   # On local machine
   vmws start
   vmws tunnel
   ```

2. **Validate** (use VM for a few days)
   - Test all your workflows
   - Verify tools work
   - Check performance

3. **Migrate** (when confident)
   - Stop using Cloud Workstation
   - Delete workstation cluster
   - **Save $91-124/month**

## FAQ

**Q: Is this secure?**
A: Yes. Uses IAP (Identity-Aware Proxy) with same Google Cloud SSO as workstations. No public IPs exposed.

**Q: What if my VM shuts down?**
A: Just run `vmws start`. Takes ~30 seconds.

**Q: Can I use a different machine type?**
A: Yes. Edit `scripts/create-test-vm.sh` and change `MACHINE_TYPE`.

**Q: What about backups?**
A: Your data is on a persistent disk. Create snapshots regularly with `gcloud compute disks snapshot`.

**Q: Can I run multiple VMs?**
A: Yes. Use `vmws config --vm-name dev-vm-2` to manage different VMs.

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 10 minutes
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Deep dive into how it works
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development guide
- **[docs/VM-AUTOMATION-GUIDE.md](docs/VM-AUTOMATION-GUIDE.md)** - Detailed usage guide
- **[examples/custom-config.sh](examples/custom-config.sh)** - Customization examples

## Contributing

Pull requests welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code structure explanation
- How to make changes
- Testing guidelines
- Development workflow

## License

MIT License - see [LICENSE](LICENSE) file

## Support

- **Issues:** [Report bugs or request features](https://github.com/benthepsychologist/vm-workstation-manager/issues)
- **Discussions:** Ask questions or share tips
- **Pull Requests:** Contributions welcome!

## Why This Exists

Cloud Workstations are great but expensive ($150/month with $144 going to control plane fees). This project gives you 95% of the functionality for 60-80% less cost by using self-managed VMs with automation.

Perfect for:
- ✅ Solo developers
- ✅ Small teams (2-5 people)
- ✅ Cost-conscious projects
- ✅ Learning GCP infrastructure

## Credits

Created to help developers save money while maintaining the same workflow as Cloud Workstations.

Built with:
- Bash scripting
- Google Cloud Compute Engine
- Identity-Aware Proxy (IAP)
- code-server
- Docker
- Systemd

---

## Ready to Save Money?

**Save $91-124/month. Start today.**

```bash
git clone https://github.com/benthepsychologist/vm-workstation-manager.git
cd vm-workstation-manager
./install.sh
vmws create
```

**Star ⭐ this repo if it helps you!**
