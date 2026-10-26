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

The included executable reports **0.0.16** and was built on Linux x86_64
with Python 3.14.4, glibc 2.43, PyInstaller 6.22.3, and Paho MQTT 2.1.0.
It passed informational CLI and private-worker import checks on the build host.
Other distributions, architectures, and older glibc versions were not tested;
use `./build-pyinstaller.sh` on the intended target platform when needed.
