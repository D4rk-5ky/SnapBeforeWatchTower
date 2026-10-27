# Package comparison — SnapBeforeWatchTower 0.0.20

Baseline: verified 0.0.19 ZIP, SHA-256 `10f998da674ca81676e5dfe9f25970de30a23c650a0699e589fce40aa5ed5b2e`.
All **27 previous-release paths remain**, with 17 updated files and
10 unchanged. No file is added, moved or removed in this release.
The private-file exclusions and configs/modules layout requested for 0.0.19 remain.

| Previous path | Content | Previous SHA-256 |
| --- | --- | --- |
| `.gitignore` | Unchanged | `22ea7b61a9ab1a3b6d2a393451cd6e089ed0b696b3f8f2d99973ebfcf8c15648` |
| `PACKAGE_MANIFEST.md` | Updated | `c6e8cef8ad20102bacba96b46da9ab708b6641930ef7a5c2204c015409a1741d` |
| `README.md` | Updated | `fa1f8da20aa4c24e3ecbae894fb745ae1873ba1bc3a5a1f3dc7f9dafd5acc321` |
| `SAFETY.md` | Unchanged | `31e0fdd8dff60529f67fa5a27c0c5b0f9cec2b983c3b923d05443027b91fe1ad` |
| `SnapBeforeWatchTower.py` | Updated | `5fb0fded0de6d0f7e667870cb7e709d204e1ddd58782cfa3905f399341f2577f` |
| `SnapBeforeWatchTower.spec` | Unchanged | `a847d9c0d5666a5e3e95f6ad505be1522ff1bf3a0b02dc0032a728e933989dc4` |
| `VERIFICATION.md` | Updated | `5017696021213b4b1949322ce6e0c5c8439f32e142c7dbda9cec7c6bb0a7bc6f` |
| `VERSIONING.md` | Updated | `e98fc6cd4e143ed00602465184bfcf6b890b1cee4117bfbb877e3a2e160f1b96` |
| `build-pyinstaller.sh` | Unchanged | `59e2f473255e010e01580de8e8de9a3e03e4e41339a68983c7697fde8bd7fd25` |
| `commented_code_map.md` | Updated | `1a9dab1e21b4a6666444ce35a90ccc047abc9a2953d366d463fbf41ad39457c9` |
| `configs/config-example.toml` | Updated | `c53bb1a59672e5c372c1943fb9c85fc29715763b7e437727b1765c71969b5883` |
| `configs/config.example.md` | Updated | `0f34724404a200590728261a42a73ae78898a3123948e8c052f7acf4baeca56a` |
| `configs/datasets.example.txt` | Unchanged | `d45c98aca4532b1c2a4712cb28029ef7d086bc4a31186cecaa194d2ae01be835` |
| `dist/README.md` | Updated | `250faf84bb96f27decbf04f47fcd8ca232efcbcc91954156db257bc2f03fa711` |
| `dist/SnapBeforeWatchTower` | Updated | `f29b5ba9a67cb377e9418de2b7a8a3439036ba46d8122a2367964895fdcff6fa` |
| `homeassistant/SnapBeforeWatchtower-mqtt-persistent-notification.yaml` | Unchanged | `e63063d78b57dcf4cffb1bbcd139bce36519a69ed094819912be3f70152f5df4` |
| `homeassistant/live-preview-card.yaml` | Unchanged | `e04fa079bdd70db93235753587055d3325f5baf1827aaa0423578174bd7daf74` |
| `homeassistant/success-failure-automation.yaml` | Unchanged | `c71a9f8a7b74601b463ff72ee5c1beb56aebda5790731261cdffc8cf18f0f4b9` |
| `manifest.sha256` | Updated | `d33106ff8c1f20602b288592382f0689081e7e34f4ab5fccc8d5789b4e93a2cb` |
| `modules/__init__.py` | Unchanged | `2c34e245d17189004592c8d869d535488e269423b7c5daaf781969fbfb7bc1cb` |
| `modules/mqtt_report.py` | Updated | `72ffe5aedfbfd3c9292dfe0ac7c27264e6165e2db1ee83ac054d212884287891` |
| `modules/mqtt_reporting.py` | Updated | `cb09121109cd3551b1541848539dee28b19bba493097a4bdc2c4a60d5c51a73f` |
| `requirements-build.txt` | Unchanged | `66dcb6090f12a0522c98db64b1c28d991d810bf52e47409e57747ee48e81ffbc` |
| `requirements-mqtt.txt` | Updated | `d24e5e5ebebb2b4012db649f9d8ad9694566b346265ae218aa64c748b11e7fc5` |
| `tests/test_app.py` | Updated | `6c2cacc9f7aa154581fabca75542456e252ed0416fd7ef4bb0b9999de10f4a23` |
| `tests/test_mqtt.py` | Updated | `6263827fdd0b371496408d7fea998cb469a9ddfb9f0c70b005eb211b61a7889b` |
| `versioning.md` | Updated | `e98fc6cd4e143ed00602465184bfcf6b890b1cee4117bfbb877e3a2e160f1b96` |

Final hashes for all 26 other project files are in manifest.sha256, excluding only
itself. The external ZIP checksum covers the entire archive, including that manifest.
All previous file modes are preserved; directories remain 0755. dist/ contains only
the README and rebuilt executable.

Relative to the initial 25-file input, the two explicitly removed host lists stay
removed and the approved example/module moves remain accounted for as documented
in the preserved 0.0.19 history. No original necessary file beyond those approved
removals is lost. config.toml and datasets are private ignored inputs, not shipped.
Both earlier release ZIPs and the initial supplied archive remain unchanged.

Check safe unique relative paths, regular files, CRCs, exact staged/extracted bytes,
file permissions, all 26 SHA-256 entries, a fresh 90-test run, CLI and source/frozen
worker checks. Exclude bytecode/caches, temporary files, runtime logs, JSON config/state
files, build work/cache/venv and private runtime inputs. All verification/build scratch
files remain outside the delivered project. No helper file or documentation directory
is introduced by this change.
