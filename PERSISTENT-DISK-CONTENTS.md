# What's in the Persistent Disk Snapshot?

When you run `vmws create` from a Cloud Workstation, it takes a snapshot of your workstation's **home disk** (`/home` directory). This contains ALL your user data and configurations.

## What Gets Copied ✅

### User Files
- **All your projects**: `~/life-cockpit/`, `~/canonizer/`, etc.
- **Documents and data**: Any files in your home directory
- **Scripts**: Custom scripts you've written

### Dotfiles & Configurations
All your personalization and settings:

```
~/.bashrc              # Bash configuration
~/.bash_history        # Command history
~/.profile             # Shell profile
~/.gitconfig           # Git configuration (name, email, aliases)
~/.ssh/                # SSH keys and config
~/.config/             # Application configs
~/.viminfo             # Vim history
~/.npmrc               # NPM configuration
~/.gsutil/             # Google Cloud Storage tools config
~/.claude/             # Claude Code settings
```

### Application Data
- **NPM packages**: `~/.npm/`
- **Cache files**: `~/.cache/`
- **Local binaries**: `~/.local/bin/`
- **IDE settings**: VS Code/code-server extensions and settings

### Size
From the test VM, the snapshot includes:
- 200GB persistent disk
- Contains actual data (projects, files)
- Incremental snapshots only copy changed blocks
- Initial snapshot: full copy
- Subsequent snapshots: only changes

## What's NOT Copied ❌

### System Packages
These are installed **fresh** on the new VM by `setup-vm-environment.sh`:
- Docker CE
- code-server
- neovim
- System libraries

**Why?** The snapshot only copies **files**, not **installed packages**. Packages are part of the OS, which is a fresh Debian 12 install.

### Operating System
- Boot disk is **brand new** Debian 12
- Not copied from workstation
- Clean OS installation

### System Configurations
- `/etc/` directory (system-wide configs)
- System services
- Kernel settings

**Why?** These live on the boot disk, which is fresh. Only `/home` is snapshotted.

## Architecture Diagram

```
Cloud Workstation
├── Boot Disk (ephemeral) ❌ NOT COPIED
│   └── Operating system, system packages
└── Home Disk (persistent) ✅ COPIED
    └── /home/user/
        ├── Projects (life-cockpit, canonizer, etc.)
        ├── Dotfiles (.bashrc, .gitconfig, .ssh, etc.)
        └── User data (documents, configs, cache)

                  ↓ Snapshot

Self-Managed VM
├── Boot Disk (fresh Debian 12) ❌ NEW
│   └── Fresh OS + packages installed by scripts
└── Data Disk (from snapshot) ✅ YOUR DATA
    └── /mnt/home/user/
        ├── Projects ✅
        ├── Dotfiles ✅
        └── User data ✅
```

## Comparison: `vmws create` vs `vmws init-fresh`

### `vmws create` (Migration)
**Requires:** Cloud Workstation

**You get:**
- ✅ All your projects
- ✅ All your dotfiles (.bashrc, .gitconfig, etc.)
- ✅ All your SSH keys and configs
- ✅ All your application data
- ✅ Complete replica of your user environment

**Fresh install:**
- Docker, code-server, neovim (system packages)
- Operating system (Debian 12)

### `vmws init-fresh` (Standalone)
**Requires:** Nothing (no workstation)

**You get:**
- ✅ Fresh Debian 12 VM
- ✅ Docker, code-server, neovim installed
- ✅ Empty `/mnt/home/` directory
- ❌ No projects
- ❌ No dotfiles (default .bashrc, .profile only)
- ❌ No SSH keys
- ❌ No configurations

**Use case:** Starting fresh, new projects, clean slate

## Why This Design?

### Separation of Concerns
1. **Boot disk** = Operating system (replaceable)
2. **Data disk** = Your files (persistent)

Benefits:
- Easy OS upgrades (replace boot disk)
- Data always safe on separate disk
- Snapshot only what matters (your data)
- Faster snapshots (skip OS files)

### Cost Optimization
- Workstation home disk: pd-balanced ($0.10/GB/month)
- Self-managed data disk: pd-standard ($0.04/GB/month)
- **60% cheaper** for same capacity

## Real Example

Here's what's actually in the test VM's `/mnt/home/user/`:

```bash
$ ls -la /mnt/home/user/ | head -30
total 284
drwxr-x--- 26 ben_getmensio_com ben_getmensio_com  4096 Nov 13 13:11 .
drwxr-xr-x  5 root              root               4096 Nov  6 15:15 ..
-rw-------  1 ben_getmensio_com ben_getmensio_com 14849 Nov 13 12:39 .bash_history
-rw-r--r--  1 ben_getmensio_com ben_getmensio_com   220 Mar 31  2024 .bash_logout
-rw-r--r--  1 ben_getmensio_com ben_getmensio_com  3808 Nov  6 16:01 .bashrc
drwxr-xr-x 13 ben_getmensio_com ben_getmensio_com  4096 Nov 12 23:31 .cache
drwxr-xr-x 10 ben_getmensio_com ben_getmensio_com  4096 Nov 13 13:07 .claude
-rw-------  1 ben_getmensio_com ben_getmensio_com 47372 Nov 13 13:07 .claude.json
drwx------  4 ben_getmensio_com ben_getmensio_com  4096 Nov  6 15:15 .codeoss-cloudworkstations
drwxr-xr-x  8 ben_getmensio_com ben_getmensio_com  4096 Nov  9 11:11 .config
-rw-r--r--  1 ben_getmensio_com ben_getmensio_com    70 Nov 10 17:37 .gitconfig
drwxr-xr-x  3 ben_getmensio_com ben_getmensio_com  4096 Nov 11 14:22 .gsutil
drwxr-xr-x  6 ben_getmensio_com ben_getmensio_com  4096 Nov 11 00:37 .local
drwxr-xr-x  5 ben_getmensio_com ben_getmensio_com  4096 Nov  9 11:10 .npm
-rw-r--r--  1 ben_getmensio_com ben_getmensio_com   807 Mar 31  2024 .profile
drwx------  2 ben_getmensio_com ben_getmensio_com  4096 Nov 13 11:38 .ssh
-rw-r--r--  1 ben_getmensio_com ben_getmensio_com     0 Nov  6 15:15 .sudo_as_admin_successful
-rw-------  1 ben_getmensio_com ben_getmensio_com  1432 Nov 12 10:42 .viminfo
drwxr-xr-x 16 ben_getmensio_com ben_getmensio_com  4096 Nov 13 11:31 canonizer
drwxr-xr-x  7 ben_getmensio_com ben_getmensio_com  4096 Nov 13 10:47 canonizer-registry
drwxr-xr-x  7 ben_getmensio_com ben_getmensio_com  4096 Nov  7 17:08 dogfold
drwxr-xr-x 14 ben_getmensio_com ben_getmensio_com  4096 Nov 11 22:12 life-cli
drwxr-xr-x 13 ben_getmensio_com ben_getmensio_com  4096 Nov 12 23:44 life-cockpit
drwxr-xr-x 13 ben_getmensio_com ben_getmensio_com  4096 Nov 13 12:38 lorch
drwxr-xr-x 18 ben_getmensio_com ben_getmensio_com  4096 Nov 13 11:47 meltano-ingest
drwx------  6 ben_getmensio_com ben_getmensio_com  4096 Nov 12 23:50 phi-data
```

**Everything** in this listing came from the workstation snapshot. Your entire user environment is preserved.

## Summary

**Short answer:** Yes, you get your dotfiles (.bashrc, .gitconfig, etc.) and all "install bits" that are **user-level** (configs, settings, application data).

**You don't get:** System-level packages (Docker, neovim binary). Those are installed fresh by the setup scripts.

**Think of it as:** Copying your `/home` directory to a new computer with a fresh OS installation.
