# TBOI Tracker

An interactive Dead God progression tracker for The Binding of Isaac: Repentance.

## Features
- Track achievements, collected items, challenges, and character completion marks
- Manual checklist tracking directly on the website
- Import REPENTOGON progression exports
- Export tracker backups
- Search items, achievements, challenges, and characters
- Automatic local progress saving
- Optional cloud sync across devices
- Optional automatic game sync with the Windows Sync Helper
- Works offline
- Can be added to your phone's Home Screen

Progress is stored locally on each user's device unless Cloud Sync is enabled.

## Automatic game sync

Download the latest successful **TBOISyncHelper-Windows** artifact from
[Build TBOI Sync Helper](https://github.com/Hassan01262011/tboi-tracker/actions/workflows/build-helper.yml),
extract the ZIP, and run `Install.cmd` once with Isaac closed.

The installer now handles the REPENTOGON dependency for you. It finds the Isaac
installation, checks which game edition is installed, and leaves an existing
REPENTOGON installation alone. If REPENTOGON is missing, it asks before downloading
from TeamREPENTOGON's official GitHub releases. Base Repentance uses the compatible
legacy build; Repentance+ uses the current official REPENTOGON Launcher and lets the
user finish the launcher's own setup. Download hashes are verified before files are
installed when the official release provides SHA-256 information.

If the Steam Workshop copy of **TBOI Tracker** is already present, the helper does
not overwrite Steam-managed mod files. Otherwise it installs its bundled exporter.
Setup no longer requires `save1.dat` to exist first: the background helper waits for
the first export after the user starts/continues a run.

On each browser, use **Cloud Sync** and your same existing Sync ID and Secret. Do not
create another code when pairing another device. The selected game save is
authoritative; later game exports replace manual website edits.

The exporter reads achievements/marks on events and checks progression every 120
game updates. The helper checks the export every 2 seconds and retries after network
errors. Visible pages check cloud every 5 seconds and on focus/reconnect. Closed or
suspended phone pages update when reopened; this is not push notifications.

`Disable-Autostart.cmd` removes automatic startup. The log and private pairing
configuration are under `%APPDATA%\TBOISyncHelper`. Never commit or share that
configuration file.

The server authenticates every read/write using a hashed random pairing secret.
Database RLS intentionally has no public policies: clients use only the authenticated
Edge Function, never direct table access. Server timestamps and conditional writes
prevent a stale paired browser from overwriting a more recent cloud update.

Tests: `node --test tests/*.test.cjs` and, with `lupa==2.8`,
`python -m unittest discover -s tests -p "test_*.py"`.
