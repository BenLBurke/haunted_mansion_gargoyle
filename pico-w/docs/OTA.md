# OTA updates

The gargoyle checks GitHub for a newer tagged release every
`ota_check_interval_hours` (default 24h) and, if it finds one, downloads and
installs it automatically.

## How it works

1. `ota.check_and_apply()` hits `https://api.github.com/repos/{ota_repo}/releases/latest`
   and compares the tag to `/version.json` on the device.
2. If there's a newer one, it fetches `pico-w/ota_manifest.json` from that
   tag (via `raw.githubusercontent.com`) -- a plain list of files plus the
   release's version string.
3. Every file in that list is downloaded to a staging area first. **If any
   single file fails to download, the whole update is aborted and the
   currently running version is left completely untouched** -- nothing gets
   swapped in until every file has arrived.
4. Once everything's staged, each live file is renamed into
   `/ota_backup/` and replaced by its staged replacement, a marker
   (`/ota_pending.json`) is written, and the device resets.
5. `boot.py` -- which runs before `main.py` on every boot and is the one
   file OTA updates never touch -- notices the pending marker. If
   `main.py` gets far enough to call `ota.confirm_boot()` (very early in
   `run()`, once every module it imports has already proven it compiles and
   runs), the marker and backup are cleared and the update is considered
   good. If that hasn't happened within 2 boots, `boot.py` restores the
   backup itself and clears the marker -- no confirmation needed from the
   (possibly broken) new code to make that happen.

## What this does and doesn't protect against

**Does**: an update that fails to download completely, or that crashes/fails
to boot, is automatically not applied or automatically rolled back. You
should never end up with a bricked device from a bad release.

**Doesn't**: an update that boots fine but has a subtle logic bug (wrong
behavior, not a crash) won't trigger a rollback -- there's no monitoring or
telemetry catching "boots but wrong," only "doesn't boot at all." That's a
deliberate scope cut for a hobby device; catching the subtler case would
need real fleet monitoring.

**One real gap**: if an update leaves `main.py` so broken it won't even
compile (e.g. a syntax error), MicroPython drops to a dead REPL prompt and
just sits there -- it does not reset itself. `boot.py`'s rollback only runs
on the *next* boot, so recovering from this specific failure mode currently
needs 1-2 manual power cycles. A hardware watchdog would close this gap
automatically, but the RP2040's caps out around 8.3 seconds, shorter than
this app's legitimate 10-second HTTPS timeout, so it isn't wired up (see
docs/HARDWARE.md). In practice this only matters for the worst-case failure
mode; a normal runtime exception is caught and handled by the crash-and-
reset wrapper in `main.py` already.

## Cutting a release

1. Bump the version in `pico-w/src/version.json`.
2. Regenerate the manifest: `python3 pico-w/scripts/generate_manifest.py`.
3. Commit both, tag it (`git tag vX.Y.Z`), push the tag, and publish a
   GitHub release for that tag (the release itself doesn't need any
   uploaded assets -- the device reads source files straight from the
   tagged commit).

Devices pick it up on their next scheduled check, or immediately if you
trigger one manually over `mpremote`:

```
mpremote connect <port> exec "import gargoyle_config, ota; ota.check_and_apply(gargoyle_config.load())"
```

## Turning it off

Set `"ota_enabled": false` in `config.json` if you'd rather update by hand
(`mpremote cp -r pico-w/src/. :` + power cycle, as usual).
