# Quick Start Guide

**Get your development VM running in 10 minutes.**

All commands run from your **local machine** (Mac/Linux). No SSH into workstations required!

---

## Choose Your Path

- **Path 1:** Migrate from Cloud Workstation (copy your existing setup)
- **Path 2:** Start fresh (no workstation needed)

---

## Path 1: Migrate from Cloud Workstation

### Step 1: Install vmws

```bash
git clone https://github.com/benthepsychologist/vm-workstation-manager.git
cd vm-workstation-manager
./bin/vmws install
```

### Step 2: Find your workstation disk

```bash
gcloud compute disks list --filter='name~workstations'
```

Look for: `workstations-XXXXX` and note its region.

### Step 3: Configure

```bash
vmws config \
  --workstation-disk workstations-XXXXX \
  --region northamerica-northeast1 \
  --zone northamerica-northeast1-b \
  --vm-name my-dev-vm
```

### Step 4: Create VM (from your Mac!)

```bash
vmws create
```

Takes ~6 minutes. Copies all your files, projects, dotfiles from workstation.

---

## Path 2: Start Fresh

### Step 1: Install vmws

```bash
git clone https://github.com/benthepsychologist/vm-workstation-manager.git
cd vm-workstation-manager
./bin/vmws install
```

### Step 2: Configure

```bash
vmws config --vm-name my-dev-vm --zone us-central1-a
```

### Step 3: Create fresh VM

```bash
vmws init-fresh
```

Takes ~5 minutes. Creates clean VM with Docker, code-server, neovim.

---

## Daily Use (Both Paths)

```bash
# Start VM
vmws start

# Connect to code-server (web VS Code)
vmws tunnel
# Then open http://localhost:8080

# Or SSH
vmws ssh

# Check status
vmws status

# Stop when done (or auto-shuts after 2hr idle)
vmws stop
```

---

## Daily Workflow Example

```bash
# Morning: Start VM and open code-server
vmws start
vmws tunnel &
open http://localhost:8080

# Code all day in your browser...

# Evening: VM auto-stops after 2hr idle
# Or stop manually: vmws stop
```

---

## All Commands Reference

```bash
vmws create        # Create VM from workstation snapshot
vmws init-fresh    # Create fresh VM (no workstation needed)
vmws start         # Start VM
vmws stop          # Stop VM
vmws status        # Check VM status
vmws tunnel        # Open tunnel to code-server
vmws ssh           # SSH into VM
vmws logs          # View auto-shutdown logs
vmws config        # Configure settings
vmws delete        # Delete VM and all resources
vmws --help        # Show help
```

---

## 💰 Cost Savings

| Scenario | Cost/Month | Savings |
|----------|------------|---------|
| Cloud Workstation | $150 | - |
| Self-managed (24/7) | $59 | **$91 (61%)** |
| Self-managed (8hr/day) | $26 | **$124 (83%)** |

Auto-shutdown after 2hr idle = **massive savings!**

## Troubleshooting

**VM won't start?**
```bash
vmws status
```

**Can't connect to code-server?**
```bash
vmws ssh
sudo systemctl restart code-server
```

**Auto-shutdown not working?**
```bash
vmws logs
```

---

## 📚 Full Documentation

- [README.md](README.md) - Complete overview and features
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical deep dive
- [CONTRIBUTING.md](CONTRIBUTING.md) - Customize and extend
- [PERSISTENT-DISK-CONTENTS.md](PERSISTENT-DISK-CONTENTS.md) - What gets copied
- `vmws --help` - CLI reference

---

## 🎯 Migration Strategy

If migrating from Cloud Workstation:

1. **Week 1:** Create self-managed VM, test it
2. **Week 2:** Use both, verify everything works
3. **Week 3:** Switch to self-managed VM exclusively
4. **Week 4:** Delete Cloud Workstation cluster
5. **Every month after:** Save $91-124 💰

---

**Questions?** [Open an issue](https://github.com/benthepsychologist/vm-workstation-manager/issues) or check the README!
