# OTA updates

`gargoyle-ota-check.timer` runs `scripts/ota_apply.py` every
`ota_check_interval_hours` (default 24h, set at install time from
`config.yaml` -- see the note on changing it below). If GitHub has a newer
tagged release than what's currently checked out, it applies it and
verifies the service actually comes back up before considering it done.

## How it works

`/opt/gargoyle` is a real git clone of this repo (not a copy) specifically
so updates can be plain git operations. Each check:

1. Asks `https://api.github.com/repos/{ota_repo}/releases/latest` for the
   newest tag and compares it to `git describe --tags --exact-match` (i.e.
   "what tag is currently checked out").
2. If there's a newer one: `git fetch --tags`, `git checkout <tag>`,
   reinstall `pi-zero/requirements.txt` into the venv, then
   `systemctl restart gargoyle`.
3. Waits and checks `systemctl is-active gargoyle` a few times. If it comes
   up healthy, done. **If it doesn't, this checks the previous tag back
   out, reinstalls dependencies, and restarts again** -- so a broken release
   gets rolled back automatically, not left running (or crash-looping).

This runs as its own systemd service/timer, deliberately *not* as part of
the gargoyle app process itself -- the app can't reliably watch its own
restart to see whether it worked, since `systemctl restart` kills the old
process before it could ever check. `ota_apply.py` is also intentionally
dependency-free (stdlib only, run with the system `python3`, not the app's
venv), so it keeps working even if a bad update broke the venv itself --
that's exactly the scenario it exists to recover from.

## What this does and doesn't protect against

**Does**: a release that fails to build (dependency install fails) or
fails to bring the service up healthy gets rolled back to the last known-
good tag automatically.

**Doesn't**: a release that starts up fine but has a subtle logic bug
(wrong behavior, not a crash/failure to start) won't trigger a rollback --
`systemctl is-active` only tells you the process is running, not that it's
behaving correctly. Catching that class of problem would need real
monitoring/telemetry, which is out of scope here.

## Cutting a release

Tag it (`git tag vX.Y.Z`, push the tag) and publish a GitHub release for
that tag -- no build step or uploaded assets needed, devices just check out
that commit directly.

## Checking on it

```
journalctl -u gargoyle-ota-check -f      # update check/apply logs
systemctl list-timers gargoyle-ota-check  # when it last ran / runs next
```

To trigger a check immediately rather than waiting for the timer:

```
sudo systemctl start gargoyle-ota-check.service
```

## Changing the check interval

`ota_check_interval_hours` in `config.yaml` is read once, at install time,
to set the timer's interval -- editing the config afterwards doesn't
retroactively change an already-installed timer. To change it on a device
that's already set up:

```
sudo systemctl edit gargoyle-ota-check.timer
```

and set `OnUnitActiveSec=` under `[Timer]`, or just re-run
`scripts/install.sh` (safe to run again; it reinstalls the timer using
whatever's currently in `config.yaml`).

## Turning it off

Set `ota_enabled: false` in `/etc/gargoyle/config.yaml` -- `ota_apply.py`
checks this itself and skips the whole check when it's off (the timer still
fires, it just no-ops immediately). Or disable the timer entirely:
`sudo systemctl disable --now gargoyle-ota-check.timer`.
