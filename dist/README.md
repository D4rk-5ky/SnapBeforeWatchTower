# PyInstaller output

The standalone Linux executable produced by `build-pyinstaller.sh` is:

```text
dist/SnapBeforeWatchTower
```

`dist/` is intentionally limited to these two files after a successful build:

```text
dist/SnapBeforeWatchTower
dist/README.md
```

The executable bundles Python and Paho MQTT. ZFS, Docker, and the local `mail` command remain external host requirements. Runtime logs are kept outside `dist/` when the executable is run from the project build directory. All generated PyInstaller build state is kept separately under the gitignored project directory `.build-pyinstaller/`, so no build work/cache/virtual-environment files belong in `dist/`.
