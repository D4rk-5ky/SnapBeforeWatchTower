# SnapBeforeWatchTower

## ⚠️ Disclaimer / Liability Notice

**This script is provided “as is”, without warranty of any kind.**  
By using this script, **you agree that I am not liable for any data loss, system damage, service interruption, or other issues** that may occur as a result of running it.

This script performs **destructive operations**, including but not limited to:

- Creating **ZFS snapshots**
- **Destroying ZFS snapshots**
- Deleting log files (`.log`, `.err`, `.digest`)
- Executing system-level commands (`zfs`, `docker`, `mail`)

⚠️ **Always test on a non-production system first.**  
⚠️ **Always ensure you have verified backups.**  
⚠️ **You are fully responsible for reviewing and understanding the code before running it.**

---

## Overview

**SnapBeforeWatchTower** is a Python 3 utility designed to safely manage **ZFS snapshots** around Docker environments.

It supports:

- Creating ZFS snapshots
- Capturing **Docker image digests** at snapshot time
- Enforcing snapshot retention (time + count)
- Cleaning up old snapshots and log groups
- Structured logging with automatic fallback
- Optional email notifications (errors and/or success)
- Optional backup title and comment metadata in terminal output, logs, and email bodies

The script **must normally be run as root**.

---

## Key Requirements (Not Optional)

❗ **ZFS is required**  
❗ **Docker is required**  
❗ **A dataset file is required**

The script will **always** attempt to:

- Read datasets from a file passed via `--file`
- Run `docker images --digests` when using `--command create`

If any mandatory requirement is missing or misconfigured, the script will fail safely.

---

## Features

- ✅ ZFS snapshot creation
- ✅ Safe snapshot deletion with strict name matching
- ✅ Guaranteed retention of newest snapshots
- ✅ Docker image digest capture (`.digest` file)
- ✅ Dataset-driven operation
- ✅ Time-based + count-based retention
- ✅ Log rotation and cleanup
- ✅ Separate `.log`, `.err`, and `.digest` files per run
- ✅ Dry-run mode (no destructive changes)
- ✅ Optional email notifications
- ✅ Optional backup title and comment metadata
- ✅ Root enforcement with automatic `/tmp` fallback logging

---

## System Requirements

### Operating System
- Linux with **ZFS**

### Python
- Python **3.9+** recommended

### Required Commands

The following **must** be available in `$PATH`:

- `zfs`
- `docker`
- `mail` (only required if email notifications are used)

---

## Dataset File (Mandatory)

The dataset file **must exist** and contain **one ZFS dataset per line**.

Example `datasets.txt`:

```text
tank/data
tank/docker
tank/vms
```

- Blank lines are ignored
- Invalid datasets will cause errors during execution

---

## Usage

### Create snapshots + cleanup

```bash
sudo ./SnapBeforeWatchTower.py \
  --command create \
  --file datasets.txt \
  --older-than 7d \
  --retain-count 10 \
  --send-mail you@example.com \
  --mail-on-success
```

### Create snapshots + cleanup with title and comment

```bash
sudo ./SnapBeforeWatchTower.py \
  --command create \
  --file datasets.txt \
  --older-than 7d \
  --retain-count 10 \
  --send-mail you@example.com \
  --mail-on-success \
  --backup-title "Before Watchtower update" \
  --backup-comment "Manual snapshot before Docker containers are updated"
```

### Delete snapshots only

```bash
sudo ./SnapBeforeWatchTower.py \
  --command delete \
  --file datasets.txt \
  --older-than 7d \
  --retain-count 10 \
  --send-mail you@example.com
```

### Dry-run (no changes)

```bash
sudo ./SnapBeforeWatchTower.py \
  --command create \
  --file datasets.txt \
  --older-than 7d \
  --retain-count 10 \
  --dry-run
```

### Dry-run with title and comment

```bash
sudo ./SnapBeforeWatchTower.py \
  --command create \
  --file datasets.txt \
  --older-than 7d \
  --retain-count 10 \
  --dry-run \
  --backup-title "Test run" \
  --backup-comment "Verify what would happen without creating or deleting anything"
```

---

## Command-Line Options

| Flag | Description |
|----|------------|
| `-c`, `--command` | `create` or `delete` |
| `-f`, `--file` | Dataset file (**required**) |
| `-o`, `--older-than` | Retention cutoff (`Nd`, `Nw`, `Nm`) |
| `-r`, `--retain-count` | Always keep this many newest snapshots |
| `-s`, `--send-mail EMAIL` | Enable email notifications |
| `-mos`, `--mail-on-success` | Send mail **also on success** (requires `-s`) |
| `--backup-title TEXT` | Optional backup title written to terminal output, logs, and the top of email bodies |
| `--backup-comment TEXT` | Optional backup comment written to terminal output, logs, and the top of email bodies |
| `-d`, `--dry-run` | Show actions without making changes |

---

## Backup Title and Comment

The optional `--backup-title` and `--backup-comment` fields can be used to describe why the script is being run.

Example:

```bash
--backup-title "Before Watchtower update"
--backup-comment "Manual snapshot before Docker containers are updated"
```

When provided, the title and comment are included in:

- Terminal output
- The main `.log` file
- The top of success email bodies
- The top of error email bodies

Example terminal/log output:

```text
Backup metadata:
Title: Before Watchtower update
Comment: Manual snapshot before Docker containers are updated
```

Example email body header:

```text
Title: Before Watchtower update
Comment: Manual snapshot before Docker containers are updated
```

The title and comment **do not change the email subject**.

Email subjects still use the normal success/error style, for example:

```text
SnapBeforeWatchTower SUCCESS - logs attached
SnapBeforeWatchTower FAILED - logs attached
```

---

## Snapshot Naming Convention

Only snapshots matching **this exact format** are managed:

```text
SnapBeforeWatchTower-Date-YYYY-MM-DD_HH_MM_SS
```

Snapshots not matching this format are **never deleted**.

---

## Retention Logic (Important)

Retention is applied **per dataset**:

1. Snapshots are sorted by timestamp (newest first)
2. The newest `--retain-count` snapshots are **always kept**
3. Older snapshots are deleted **only if**:
   - They are older than `--older-than`
   - They are not in the retained set

This guarantees **no accidental full snapshot deletion**.

---

## Logging Behavior

Each run produces a **log group** sharing the same timestamp:

- `.log` → main log (INFO + DEBUG)
- `.err` → errors only (removed if empty)
- `.digest` → Docker image digests (create mode only)

If `--backup-title` and/or `--backup-comment` are provided, they are written near the start of the terminal output and `.log` file.

### Log location

- **Root execution** → `./logs/`
- **Non-root execution** → `/tmp/SnapBeforeWatchTower/`

If not run as root:
- The script logs the error
- Optionally sends mail
- Exits without touching ZFS or Docker

---

## Email Notifications

### Error mail (`--send-mail`)

- Sent **only on failure**
- Subject stays in the normal error format
- If provided, `--backup-title` and `--backup-comment` are written at the top of the mail body
- Attaches:
  - Latest `.log`
  - `.err` **only if non-empty**

### Success mail (`--send-mail --mail-on-success`)

- Sent **only if run completed without errors**
- Subject stays in the normal success format
- If provided, `--backup-title` and `--backup-comment` are written at the top of the mail body
- Attaches:
  - Latest `.log`
  - `.err` **only if non-empty**

No empty error files are ever attached.

---

## Safety Notes

- ❗ **This script destroys ZFS snapshots**
- ❗ Docker **must be running** for snapshot creation
- ❗ Dataset file **must exist**
- ❗ Must be run as **root** for full functionality
- ❗ Designed for **automation (cron/systemd)**

---

## License

No license is implied unless explicitly added.  
Use, modify, and run this script **entirely at your own risk**.