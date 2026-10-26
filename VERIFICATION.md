# Release verification — 0.0.16

Verified on 2026-10-26 against the completed 0.0.15 project and the original
supplied ZIP. This release adds a run name to report metadata and the email body.

## Behavior verified

```toml
[report]
name = "Nightly Docker snapshots"
comment = "Before Watchtower updates."
```

Email body starts with `Nightly Docker snapshots`, a blank line, then
`Before Watchtower updates.`, followed by outcome/log content. The email subject
retains its existing success/failure wording. MQTT `name` and `job` carry the
run name, `comment` carries the comment, and `title` stays independently configured.
Omitting or emptying the name preserves the previous heading/name fallbacks.

| Check | Result |
| --- | --- |
| Version | PASS — 0.0.15 to 0.0.16; source and rebuilt binary agree |
| Offline suite | PASS — 67 tests including four new name-specific tests |
| Email content | PASS — actual `MailTo()` formatting puts name then multiline comment before outcome/logs, uses configured attachments and preserves subject |
| All mail paths | PASS — combined real-config coordinator test checks name/title/comment on success, aggregate command failure, missing dataset, fatal failure and non-root refusal |
| MQTT semantics | PASS — distinct name/title, name/job fallback, unchanged comment, live/dry-run success/failure propagation and JSON/worker round-trip |
| Validation | PASS — optional/empty/trimmed/Unicode name; invalid type/newline/CR/NUL rejected; invalid name stops before operations/reporting |
| Backward compatibility | PASS — unnamed configs and old optional helper calls retain their fallbacks; appended helper parameters preserve existing positional meanings |
| Existing safety tests | PASS — retention count/age, unmanaged/malformed names, failed-list boundary, dry-run suppression, root enforcement, continuation and final failure |
| Compile | PASS — four Python files plus PyInstaller spec compile in memory |
| Shell | PASS — `bash -n build-pyinstaller.sh` |
| Help/version/parser | PASS — source and binary help aliases/version work; new report behavior documented; missing config/invalid flags exit 2 without traceback |
| Config example | PASS — all 28 options across five tables, starts dry-run with mail/MQTT disabled |
| Documentation | PASS — README/reference cover settings; code map names every Python function/class/method; histories identical; original disclaimer unchanged |
| Home Assistant example | PASS — YAML parses and Jinja name template renders named, legacy title, legacy job, empty JSON and absent JSON cases |
| Source-change audit | PASS — app changes limited to report validation/loading, mail formatting and name forwarding/help; MQTT changes limited to payload/reporter; other active functions unchanged |
| Build inputs/safety files | PASS — build script/spec, dependency files, host dataset lists and SAFETY byte-for-byte preserved from 0.0.15 |
| Real PyInstaller build | PASS — unchanged recipe builds version 0.0.16; dist contains exactly README + executable |
| Frozen MQTT import | PASS — empty private-worker JSON reaches sanitized `KeyError` after bundled Paho import; no broker request attempted |
| Archive preservation | PASS — 25/25 previous-release paths and 23/23 original paths retained; no added/removed project file relative to 0.0.15 |
| Clean ZIP/fresh extraction | PASS — CRC, exact file list, content hashes, executable modes, all 67 tests and help/version after extraction |
| Checksums | PASS — `manifest.sha256` verifies all other 24 project files after extraction |

## Limits

External application commands and notification transport are mocked in tests.
No real ZFS snapshot creation/listing/destruction, Docker capture, local mail
delivery, MQTT broker/authentication/TLS exchange, Home Assistant action,
Pushover notification or production deployment was exercised. YAML/Jinja checks
are offline checks, not a complete Home Assistant runtime test.

The executable was rebuilt on Linux x86_64 with Python 3.14.4, glibc 2.43,
PyInstaller 6.22.3 and Paho MQTT 2.1.0. Other distributions, architectures and
older glibc versions are untested; rebuild on the intended target as needed.
The source requires Python 3.11+. PyInstaller optional/platform-specific import
warnings do not certify every path; CLI and bundled Paho import checks passed.
All build environments, work/cache and scratch files are excluded from delivery.

`PACKAGE_MANIFEST.md` compares actual delivered paths with both baselines.
`manifest.sha256` excludes itself to avoid self-reference. Integrity and offline
regression checks cannot certify data safety or notification delivery.
