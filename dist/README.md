# PyInstaller output

Run `bash build-pyinstaller.sh` to build the standalone Linux executable.
Immediately after a successful build, dist/ contains exactly:

```text
dist/README.md
dist/SnapBeforeWatchTower
```

The executable bundles Python and Paho MQTT. ZFS, Docker and mail remain external host requirements. Build/cache/venv state stays in .build-pyinstaller/.

Runtime logs always use logs/ beside the actual executable. Running from this directory creates dist/logs/, using [logging].prefix for .log/.err/.digest files. An unwritable folder stops the run before operational commands; no temporary fallback is used.

The build script cleans every dist/ entry except README.md before building, including any runtime logs. Preserve needed logs before rebuilding or deploy the executable outside the build directory before running jobs.
