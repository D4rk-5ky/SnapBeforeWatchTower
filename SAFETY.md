# SnapBeforeWatchTower safety and liability notice

## ⚠️ Disclaimer / Liability

**Use this script at your own risk.**

The author takes **no responsibility or liability** for any data loss, service disruption, misconfiguration, service outage, missed backups, credential exposure, or other damage that may occur from using this script.

Before running it in production, you **must**:

- Read the entire source code
- Understand exactly what it does (and what it does *not* do)
- Review and adapt it to your own environment
- Test it carefully in a non‑production setup

By using this script, **you accept full responsibility** for its effects.

⚠️ AI-assisted / vibe-coded experimental software. Use at your own risk.

## Disclaimer

This project is AI-assisted / vibe-coded software created as a hobby project. It has not been professionally audited and may contain bugs, unsafe behavior, data-loss issues, security problems, or incorrect assumptions.

You are responsible for reviewing the code, testing it in a safe environment, making backups, and understanding what it does before using it on real data. The author is not responsible for damage, data loss, broken systems, security issues, or other problems caused by using this software.

---

## SnapBeforeWatchTower data-loss warning

SnapBeforeWatchTower can create and destroy ZFS snapshots and delete managed `.log`, `.err`, and `.digest` files. A real `create` or `delete` run can therefore remove data that you intended to keep if the configured datasets or retention policy are wrong.

Start with `dry_run = true`, inspect the resulting logs and planned deletions, test on a non-production system, and keep independent verified backups before enabling real deletion.

## License

No license is implied unless explicitly added. Use, modify, and run SnapBeforeWatchTower entirely at your own risk.
