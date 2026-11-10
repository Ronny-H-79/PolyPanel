# Internals

Structure, console usage, stop order and notes for developers.

[← back to the README](../README.md) · [Deutsch](technik.de.md)

## Usage

```bash
noah2games web               # web UI on http://127.0.0.1:8790
noah2games url               # ready-made address including the token
noah2games status            # process, RCON, last log line
noah2games start --wait 240
noah2games stop              # SaveWorld → DoExit → SIGTERM → SIGKILL
noah2games update --check    # is a new Steam build available?
noah2games supervise --all   # auto-restart, schedule, backups
```

## Structure

| File | Purpose |
|---|---|
| `noah2games/instance.py` | instance configuration (JSON), paths, writing INI files, start parameters |
| `noah2games/runner.py` | start/stop/status/update, RCON shutdown, maintenance lock |
| `noah2games/consoled.py` | starts the server on a PTY so Wine opens no window |
| `noah2games/rcon.py` | own Source RCON client |
| `noah2games/supervisor.py` | health check, auto-restart, schedule, countdown |
| `noah2games/registry.py` | several instances, port picking, metrics |
| `noah2games/mods.py` · `whitelist.py` · `config.py` · `backups.py` · `snapshots.py` | feature modules |
| `noah2games/webui.py` | dashboard, instance pages, JSON API (stdlib `http.server`) |
| `noah2games/cli.py` | command line including `wizard` |

## Stop order (deliberate)

1. RCON `SaveWorld` — save the game state
2. RCON `DoExit` — regular shutdown
3. `SIGTERM` to the process group
4. `SIGKILL`

A `kill` without step 1 costs everything since the last autosave.
