# Dead God Tracker

An interactive Dead God progression tracker for The Binding of Isaac: Repentance.

## Features
- Top 10 item unlock priorities
- Top 10 character priorities
- Automatic progress saving
- Search unlocks and characters
- Import/export progress
- Works offline
- Can be added to your phone's Home Screen

Progress is stored locally on each user's device.
# Automatic game sync

Download the latest successful **TBOISyncHelper-Windows** artifact from
[Build TBOI Sync Helper](https://github.com/Hassan01262011/tboi-tracker/actions/workflows/build-helper.yml).
Extract the ZIP and run `Install.cmd` once with Isaac closed. It backs up and
updates the exporter, reuses your existing helper pairing, and starts the helper
at Windows sign-in. No administrator rights or database keys are required.

On each browser, use **Cloud sync** and your same existing Sync ID and Secret.
Do not create another code when pairing another device. The selected game save
is authoritative; later game exports replace manual website edits.

The exporter reads achievements/marks on events and checks progression every
120 game updates. The helper checks the export every 2 seconds and retries after
network errors. Visible pages check cloud every 5 seconds and on focus/reconnect.
Closed or suspended phone pages update when reopened; this is not push notifications.

`Disable-Autostart.cmd` removes automatic startup. The log and private pairing
configuration are under `%APPDATA%\TBOISyncHelper`. Never commit that configuration.

The server authenticates every read/write using a hashed random pairing secret.
Database RLS intentionally has no public policies: clients use only the authenticated
Edge Function, never direct table access. Server timestamps and conditional writes
prevent a stale paired browser from overwriting a more recent cloud update.

Tests: `node --test tests/*.test.cjs` and, with `lupa==2.8`,
`python -m unittest discover -s tests -p "test_*.py"`.
