# SnapBeforeWatchTower

## ⚠️ Disclaimer / Liability Notice

**This script is provided “as is”, without warranty of any kind.**  
By using this script, **you agree that I am not liable for any data loss, system damage, service interruption, or other issues** that may occur as a result of running it.

This script performs **destructive operations**, including but not limited to:

- Creating **ZFS snapshots**
- **Destroying ZFS snapshots**
- Deleting log files
- Executing system-level commands (`zfs`, `docker`, `mail`)

⚠️ **Always test on a non-production system first.**  
⚠️ **Always ensure you have verified backups.**  
⚠️ **You are fully responsible for reviewing and understanding the code before running it.**

---

## Overview

**SnapBeforeWatchTower** is a Python 3 utility designed to:

- Create ZFS snapshots for one or more datasets
- Capture **Docker image digests** before snapshot creation
- Enforce snapshot retention using:
  - Time-based retention (`--older-than`)
  - Count-based retention (`--retain-count`)
- Clean up old snapshots and old log files safely
- Generate structured logs and error reports
- Optionally send email notifications with logs attached

The script **must be run as root**.

---

## Key Requirements (Not Optional)

❗ **Docker is required**  
❗ **A dataset file is required**

The script will **always** attempt to:
- Run `docker images --digests`
- Read datasets from a file passed via `--file`

If either requirement is missing or misconfigured, the script will fail.

---

## Features

- ✅ ZFS snapshot creation
- ✅ Safe snapshot deletion logic
- ✅ Docker image digest capture (**mandatory**)
- ✅ Dataset-driven operation (**mandatory**)
- ✅ Log rotation and cleanup
- ✅ Separate `.log`, `.err`, and `.digest` files
- ✅ Optional email notifications
- ✅ Root-only execution enforcement with safe fallback logging

---

## System Requirements

### Operating System
- Linux with **ZFS**

### Python
- Python **3.9+** recommended

### Required Commands (Mandatory)

The following **must** be available in `$PATH`:

- `zfs`
- `docker`
- `mail` (required if `--send-mail` is used)

---

## Dataset File (Mandatory)

The dataset file **must exist** and contain **one ZFS dataset per line**.

Example `datasets.txt`:

```
tank/data
tank/docker
tank/vms
```

Blank lines are ignored.

---

## Usage

```
# To Create snapshots & cleanup

sudo ./SnapBeforeWatchTower.py   --command create   --file datasets.txt   --older-than 7d   --retain-count 10   --send-mail you@example.com

# To only delete snapshots for cleanup

sudo ./SnapBeforeWatchTower.py   --command delete   --file datasets.txt   --older-than 7d   --retain-count 10   --send-mail you@example.com
```

---

## Snapshot Naming Convention

Snapshots created by this script follow this exact format:

```
SnapBeforeWatchTower-Date-YYYY-MM-DD_HH_MM_SS
```

Only snapshots matching this format are managed or deleted.

---

## Safety Notes

- ❗ This script **destroys ZFS snapshots**
- ❗ Docker **must be running**
- ❗ Dataset file **must exist**
- ❗ Must be run as **root**
- ❗ Designed for **automation (cron/systemd)**

---

## License

No license is implied unless explicitly added.  
Use, modify, and run this script **entirely at your own risk**.
