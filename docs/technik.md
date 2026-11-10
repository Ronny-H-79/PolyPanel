# Internals

Structure, console usage, stop order and notes for developers.

[← back to the README](../README.md) · [Deutsch](technik.de.md)

## Usage

```bash
polypanel web               # web UI on http://127.0.0.1:8790
polypanel url               # ready-made address including the token
polypanel status            # process, RCON, last log line
polypanel start --wait 240
polypanel stop              # SaveWorld → DoExit → SIGTERM → SIGKILL
polypanel update --check    # is a new Steam build available?
polypanel supervise --all   # auto-restart, schedule, backups
```

## Structure

| File | Purpose |
|---|---|
| `PolyPanel/instance.py` | instance configuration (JSON), paths, writing INI files, start parameters |
| `PolyPanel/runner.py` | start/stop/status/update, RCON shutdown, maintenance lock |
| `PolyPanel/consoled.py` | starts the server on a PTY so Wine opens no window |
| `PolyPanel/rcon.py` | own Source RCON client |
| `PolyPanel/supervisor.py` | health check, auto-restart, schedule, countdown |
| `PolyPanel/registry.py` | several instances, port picking, metrics |
| `PolyPanel/mods.py` · `whitelist.py` · `config.py` · `backups.py` · `snapshots.py` | feature modules |
| `PolyPanel/webui.py` | dashboard, instance pages, JSON API (stdlib `http.server`) |
| `PolyPanel/cli.py` | command line including `wizard` |

## Stop order (deliberate)

1. RCON `SaveWorld` — save the game state
2. RCON `DoExit` — regular shutdown
3. `SIGTERM` to the process group
4. `SIGKILL`

A `kill` without step 1 costs everything since the last autosave.

---

© 2026 Ronny H. · Free to use, all rights reserved — [Licence](../LICENSE)
