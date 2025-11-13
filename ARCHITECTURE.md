# Architecture Overview

Deep dive into how VM Workstation Manager works.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Local Machine (Mac/Linux)                │
│                                                               │
│   ┌──────────────────────────────────────────────────────┐  │
│   │  vmws CLI                                            │  │
│   │  - Config: ~/.vmws/config                            │  │
│   │  - Commands: start, stop, tunnel, status             │  │
│   └──────────────┬───────────────────────────────────────┘  │
│                  │                                            │
└──────────────────┼────────────────────────────────────────────┘
                   │
                   │ gcloud compute ssh
                   │ (IAP Tunnel)
                   │
┌──────────────────▼────────────────────────────────────────────┐
│                    Google Cloud Platform                      │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Cloud Workstation (Optional - for VM creation)        │  │
│  │                                                         │  │
│  │  - Has your development environment                    │  │
│  │  - Runs vmws create                                    │  │
│  │  - Source for disk snapshot                            │  │
│  │  - Home disk: 200GB at /home/user                      │  │
│  └────────────────────────────────────────────────────────┘  │
│                         │                                     │
│                         │ Snapshot                            │
│                         ▼                                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Self-Managed Development VM                           │  │
│  │                                                         │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │ Boot Disk (50GB pd-standard)                     │  │  │
│  │  │ - Debian 12                                      │  │  │
│  │  │ - System packages                                │  │  │
│  │  │ - Mounted at /                                   │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  │                                                         │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │ Data Disk (200GB pd-standard)                    │  │  │
│  │  │ - Snapshot from workstation                      │  │  │
│  │  │ - Your files, configs, projects                  │  │  │
│  │  │ - Mounted at /mnt/home                           │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  │                                                         │  │
│  │  Services:                                              │  │
│  │  ┌─────────────────────────────────────┐               │  │
│  │  │ code-server (port 8080)             │               │  │
│  │  │ - Web-based VS Code                 │               │  │
│  │  │ - WorkingDirectory: /mnt/home/user  │               │  │
│  │  │ - Auth: none (via IAP)              │               │  │
│  │  └─────────────────────────────────────┘               │  │
│  │  ┌─────────────────────────────────────┐               │  │
│  │  │ Docker CE                           │               │  │
│  │  │ - Latest from docker.com            │               │  │
│  │  │ - User in docker group              │               │  │
│  │  └─────────────────────────────────────┘               │  │
│  │  ┌─────────────────────────────────────┐               │  │
│  │  │ vm-auto-shutdown service            │               │  │
│  │  │ - Monitors connections every 5min   │               │  │
│  │  │ - Shuts down after 2hr idle         │               │  │
│  │  └─────────────────────────────────────┘               │  │
│  │                                                         │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

## Data Flow

### VM Creation (vmws create)

```
1. User runs: vmws create
   └─ From Cloud Workstation

2. run-vm-test-workflow.sh
   ├─ [1/8] create-test-vm.sh
   │   ├─ gcloud compute disks snapshot (workstation home disk)
   │   │   └─ Creates: workstation-snapshot-YYYYMMDD-HHMMSS
   │   ├─ gcloud compute disks create (from snapshot)
   │   │   └─ Creates: test-vm-from-workstation-disk (200GB)
   │   └─ gcloud compute instances create
   │       ├─ Boot: Debian 12 (50GB pd-standard)
   │       ├─ Data: test-vm-from-workstation-disk (attached)
   │       └─ Startup script: mounts /dev/sda to /mnt/home
   │
   ├─ [2/8] Wait for SSH ready
   │   └─ Polls: gcloud compute ssh ... --command="echo ready"
   │
   ├─ [3/8] Fix file permissions
   │   └─ chown -R ben_getmensio_com:ben_getmensio_com /mnt/home/user
   │
   ├─ [4/8] setup-vm-environment.sh
   │   ├─ apt-get install neovim curl wget
   │   ├─ Install Docker CE
   │   │   ├─ Add Docker GPG key
   │   │   ├─ Add Docker apt repo
   │   │   ├─ apt-get install docker-ce docker-ce-cli
   │   │   └─ usermod -aG docker $USER
   │   ├─ Install code-server
   │   │   ├─ curl https://code-server.dev/install.sh
   │   │   ├─ Create config: ~/.config/code-server/config.yaml
   │   │   ├─ Create systemd service
   │   │   └─ systemctl enable --now code-server
   │   └─ Return versions
   │
   ├─ [5/8] install-auto-shutdown.sh
   │   ├─ Copy vm-auto-shutdown.sh to /usr/local/bin
   │   ├─ Create systemd service
   │   └─ systemctl enable --now vm-auto-shutdown
   │
   ├─ [6/8] Run validation tests
   │   ├─ Test: Disk mounted
   │   ├─ Test: Files accessible
   │   ├─ Test: life-cockpit exists
   │   ├─ Test: File read access
   │   ├─ Test: Docker running
   │   └─ Test: code-server running
   │
   ├─ [7/8] Generate cost analysis
   │   └─ Add cost tables to report
   │
   └─ [8/8] Finalize report
       └─ Create: vm-test-report-YYYYMMDD-HHMMSS.md
```

### Daily Usage (vmws start → vmws tunnel)

```
1. User runs: vmws start
   ├─ Check VM status
   ├─ If TERMINATED:
   │   └─ gcloud compute instances start
   ├─ Wait for SSH ready
   └─ Print success

2. User runs: vmws tunnel
   ├─ Check VM is RUNNING
   └─ gcloud compute ssh ... -- -L 8080:localhost:8080 -N
       └─ Port 8080 (local) → 8080 (VM code-server)

3. User opens: http://localhost:8080
   ├─ Browser → localhost:8080
   ├─ SSH tunnel → IAP → VM:8080
   └─ code-server serves VS Code interface

4. Auto-shutdown monitors
   ├─ Every 5 minutes:
   │   ├─ Count SSH connections (who)
   │   ├─ Count code-server connections (ss -tn | grep :8080)
   │   └─ If both == 0:
   │       ├─ Increment idle counter
   │       └─ If idle >= 120 minutes:
   │           └─ shutdown -h now
   └─ If connections > 0:
       └─ Reset idle counter
```

## Security Model

### Identity & Access

```
User (Your Google Account)
    │
    ├─ Authenticates to: Google Cloud
    │   └─ Managed by: Google IAM
    │
    └─ Connects via: Identity-Aware Proxy (IAP)
        │
        ├─ No public IP required
        ├─ Encrypted tunnel
        ├─ Automatic Google SSO
        │
        └─> VM (Private IP only)
            └─ Services listen on localhost only
                ├─ code-server: 127.0.0.1:8080
                └─ SSH: via IAP tunnel
```

### Network Isolation

- VM has **no external IP** (optional)
- All services bind to **127.0.0.1** (localhost)
- Access only via **IAP tunnel**
- Firewall rules: **SSH via IAP only**

### Authentication Layers

1. **Google Cloud SSO** - Your Google account
2. **IAP** - Google's identity-aware proxy
3. **SSH Keys** - Managed by gcloud
4. **code-server** - No password (secured by IAP)

## Storage Architecture

### Disk Types

```
┌─────────────────────────────────────────────┐
│ Cloud Workstation                           │
├─────────────────────────────────────────────┤
│ Boot Disk (ephemeral)                       │
│ - 50GB pd-ssd                               │
│ - Recreated on restart                      │
│ - OS and system packages                    │
├─────────────────────────────────────────────┤
│ Home Disk (persistent)                      │
│ - 200GB pd-balanced                         │
│ - Survives restarts                         │
│ - Your data, configs, projects              │
│ - Mounted at: /home                         │
└─────────────────────────────────────────────┘
                │
                │ Snapshot
                ▼
┌─────────────────────────────────────────────┐
│ Self-Managed VM                             │
├─────────────────────────────────────────────┤
│ Boot Disk (persistent)                      │
│ - 50GB pd-standard                          │
│ - Fresh Debian 12 install                   │
│ - System packages                           │
│ - Mounted at: /                             │
├─────────────────────────────────────────────┤
│ Data Disk (persistent)                      │
│ - 200GB pd-standard                         │
│ - Cloned from workstation home              │
│ - Your data, configs, projects              │
│ - Mounted at: /mnt/home                     │
└─────────────────────────────────────────────┘
```

### Why This Design?

1. **Separate OS from data**
   - Easy OS upgrades (replace boot disk)
   - Data always safe on separate disk
   - Can snapshot data disk independently

2. **pd-standard for cost savings**
   - Workstation: pd-balanced ($0.10/GB/mo)
   - Self-managed: pd-standard ($0.04/GB/mo)
   - 60% cheaper for same capacity

3. **Persistent boot disk**
   - Unlike workstation (ephemeral boot)
   - No need to reinstall on every start
   - Faster startup time

## Service Management

### Systemd Services

```
/etc/systemd/system/
├── code-server.service
│   ├── ExecStart: /usr/bin/code-server
│   ├── User: ben_getmensio_com
│   ├── WorkingDirectory: /mnt/home/user
│   └── Restart: on-failure
│
└── vm-auto-shutdown.service
    ├── ExecStart: /usr/local/bin/vm-auto-shutdown.sh
    ├── Restart: always
    └── RestartSec: 10
```

### Service Dependencies

```
network.target
    │
    ├─> code-server.service
    │   └─> Requires: /mnt/home mounted
    │
    └─> vm-auto-shutdown.service
        └─> Monitors: code-server connections
```

## Cost Model

### Resource Pricing (us-central1)

| Resource | Type | Size | Price/Month |
|----------|------|------|-------------|
| VM Compute | e2-standard-2 | 2 vCPU, 8GB | $49.28 (24/7) |
| Boot Disk | pd-standard | 50GB | $2.00 |
| Data Disk | pd-standard | 200GB | $8.00 |
| Snapshot | Incremental | ~4GB | $0.13 |
| **Total (running 24/7)** | | | **$59.41** |
| **Total (8hr/day)** | | | **$26.43** |

### Cost Optimization Strategies

1. **Auto-shutdown** (2hr idle)
   - Reduces compute hours by 50-75%
   - No charge while stopped
   - Disks still charged (always)

2. **Right-sizing**
   - Use e2-standard-2 (2 vCPU) for light work
   - Upgrade to e2-standard-4 (4 vCPU) if needed
   - Only pay for what you use

3. **Disk optimization**
   - Use pd-standard (60% cheaper than pd-balanced)
   - Resize down if using <50GB
   - Delete old snapshots

## Failure Modes & Recovery

### VM Won't Start

**Cause:** Quota limits, zone unavailable
**Recovery:**
```bash
vmws status  # Check actual status
gcloud compute instances describe ... # Detailed info
gcloud compute instances start ... --zone=different-zone
```

### code-server Won't Connect

**Cause:** Service crashed, port conflict
**Recovery:**
```bash
vmws ssh
sudo systemctl status code-server
sudo journalctl -u code-server -n 50
sudo systemctl restart code-server
```

### Auto-shutdown Not Working

**Cause:** Service failed, script error
**Recovery:**
```bash
vmws logs
sudo systemctl status vm-auto-shutdown
sudo systemctl restart vm-auto-shutdown
```

### Data Disk Not Mounted

**Cause:** Startup script failed
**Recovery:**
```bash
vmws ssh
sudo mount /dev/sda /mnt/home
sudo vim /etc/fstab  # Add permanent entry
```

## Performance Characteristics

### VM Startup Time

- **Cold start:** ~30 seconds
- **SSH ready:** +10 seconds
- **Services ready:** +5 seconds
- **Total:** ~45 seconds

### Snapshot Creation

- **Initial snapshot:** ~2-3 minutes (200GB disk)
- **Incremental:** <1 minute (only changes)

### IAP Tunnel Latency

- **Typical:** 50-100ms overhead
- **Bandwidth:** ~50-100 Mbps
- **Good for:** Code editing, terminal
- **Not ideal for:** Large file transfers

## Scalability

### Single Developer

- ✅ Perfect fit
- ✅ Cost-effective
- ✅ Easy to manage

### Small Team (2-5 devs)

- ✅ Each dev gets own VM
- ✅ Use vmws config per developer
- ✅ Shared project on Cloud Storage
- ⚠️  Manual VM management

### Large Team (5+ devs)

- ⚠️  Consider Cloud Workstations
- ⚠️  Or build orchestration layer
- ⚠️  Team-wide config management

## Future Enhancements

Potential improvements:

1. **Multi-VM management**
   - Manage multiple VMs from one CLI
   - Team configuration

2. **Terraform modules**
   - Infrastructure as code
   - Repeatable deployments

3. **Custom images**
   - Pre-bake Docker, code-server
   - Faster creation time

4. **Backup automation**
   - Automatic daily snapshots
   - Retention policies

5. **Monitoring**
   - Cloud Monitoring integration
   - Alert on failures

6. **Cost tracking**
   - Show actual costs
   - Budget alerts

## References

- [Google Compute Engine Docs](https://cloud.google.com/compute/docs)
- [IAP for TCP Forwarding](https://cloud.google.com/iap/docs/using-tcp-forwarding)
- [Systemd Service Files](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [code-server Documentation](https://coder.com/docs/code-server)
