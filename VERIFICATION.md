# Release verification — 0.0.16

Verified on 2026-10-07 in the Windows workspace. This is a source release; the earlier 0.0.15 project, ZIP, checksum and comparison report remain unchanged. A baseline of the 0.0.15 ZIP was recorded before edits.

## Changes

This release adds three optional TOML settings: [logging].prefix and [report].title/comment. Prefixes are used for .log/.err/.digest names, retention and mail attachments. The report title is an email body heading and overrides the MQTT title when nonempty; comment preserves decoded TOML newlines in email and the JSON payload. The Home Assistant example displays the optional comment.

The user explicitly selected fixed logs/ storage beside the actual script/executable. There is no temporary fallback, even for an executable in dist/. An unwritable log directory stops the run before ZFS/Docker work. Root enforcement and all snapshot/continuation/dry-run safety rules remain intact.

## Checks performed

| Check | Result |
| --- | --- |
| Offline suite | PASS — 62/62 tests; external operations and notification transports are mocked |
| Newline handling | PASS — escaped-newline, multiline basic/literal TOML strings, blank lines, trailing newline, literal backslashes, exact email body, MQTT JSON round-trip and mocked Paho worker publication |
| Report propagation | PASS — shared title precedence and empty legacy-title fallback; main success, continued dataset failure and non-root failure carry the title/comment into mail/MQTT |
| Prefix behavior | PASS — real disposable .log/.err files, mocked-Docker .digest creation, dry-run/count/age protection, exact-prefix retention and overlapping-prefix attachment exclusion |
| Fixed log storage | PASS — source and mocked frozen executable paths (including dist), non-root folder selection and mocked unwritable-folder refusal before external work |
| Validation | PASS — wrong tables/types/keys, NUL, unsafe path/glob prefixes and multiline titles are rejected before operation/report work |
| CLI | PASS — -h/--help and --version; missing config, invalid/retired flags and missing files fail at parser boundary; version is 0.0.16 |
| Compilation | PASS — all four .py files plus the PyInstaller .spec compile in memory |
| Build script syntax | PASS — GNU Bash 5.2.37 parses build-pyinstaller.sh with -n, executing no commands |
| Configuration/docs | PASS — all 27 supported settings appear in TOML and usage references; safe example loads with dry-run and notifications disabled |
| Code map | PASS — all 121 function/class definition occurrences, including methods, nested helper and tests, are named and explained; commands and build controls remain documented |
| Runtime preservation | PASS — all original module-level functions/classes retained; unmodified snapshot, command, duration, error/continuation helpers compare identically by AST; MQTT worker/publish/TLS/auth transport is unchanged by AST |
| Required originals | PASS — all 20 paths from 0.0.15 retained, including the existing manifest; seven files remain byte-identical |
| Disclaimer/version history | PASS — exact disclaimer after README title; SAFETY.md unchanged; complete earlier version entries retained; 0.0.15 -> 0.0.16 |
| Build inputs | PASS — build script, spec, dependency files and .gitignore are byte-identical |
| Home Assistant | PASS — exact source comparison verifies only optional comment extraction/display was added; topic/trigger/status branching remain unchanged |

## Packaging

The project retains all 20 prior-release files. manifest.sha256 is regenerated and covers every other file, excluding itself. A ZIP checksum and manifest-comparison JSON accompany the source ZIP. The comparison records source/release hashes, path preservation, original ZIP metadata, ZIP CRC/member/byte verification, extracted-file equality, extracted CLI/compile/test results and forbidden-artifact checks. It also verifies that all 19 originally uploaded project paths remain present.

No cache, bytecode, logs, credentials, generated executable, build workspace or temporary verification helper is included. Static build inputs and dist/README.md remain required project files.

From the extracted project directory on Linux:

```bash
sha256sum -c manifest.sha256
python3 -B -m unittest discover -s tests -v
```

## Operational boundary and untested integration

No real Linux/ZFS, Docker daemon, mail transport, MQTT broker/TLS/authentication, Home Assistant automation or Pushover delivery was exercised. No Linux PyInstaller executable was built. Paho/PyInstaller and a YAML parser are unavailable in the verification interpreter; the Home Assistant example was checked by precise source comparison, not loaded into Home Assistant.

Fixed-directory selection and refusal to fall back were tested locally; Linux ownership/permission and real frozen execution still need a disposable deployment test. If log setup fails, mail cannot attach logs and is not attempted from the operation flow. An enabled MQTT reporter can still attempt the final exception report, subject to its normal transport limits; actual delivery was not tested.

The unchanged build script cleans every generated dist/ entry before rebuilding, including dist/logs/ if jobs have been run there. Preserve needed logs before rebuilding or deploy the executable outside the build directory. Its two-file layout applies immediately after a successful build; runtime creates logs/ beside the executable as requested.

Dry-run still lists ZFS, writes logs, removes an empty current error file at final cleanup and can send enabled notifications. It suppresses snapshot creation/destruction and old-log deletion, and skips Docker. Changing logging.prefix leaves older-prefix log files in place. It does not change snapshot naming or snapshot retention. Report settings do not enable either notification channel.
