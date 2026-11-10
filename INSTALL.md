# Installing noah2games

An installer for your own multigame server manager (ARK: Survival Ascended, Satisfactory,
7 Days to Die, Space Engineers). Everything runs locally: Python standard library plus
SteamCMD and Wine.

[← back to the README](README.md) · [Deutsch](INSTALL.de.md)

## Requirements

| What | Why | Check |
|---|---|---|
| Linux (x86_64) | tested on CachyOS/Arch | `uname -m` |
| Python ≥ 3.10 | the program runs on it | `python3 -V` |
| Wine ≥ 8 | runs the Windows server files | `wine --version` |
| ~30 GB disk per instance | 12.4 GB download + backups | `df -h ~` |
| ~4 GB RAM empty without mods, 11–12 GB with mods/world/players (no upper limit) | ARK needs it | `free -g` |

Missing Wine:

```bash
sudo pacman -S wine           # Arch / CachyOS
sudo apt install wine         # Debian / Ubuntu
```

SteamCMD is downloaded automatically to `~/steamcmd` on first install — no root needed.

## Language

The installer asks first:

```
Sprache / Language:  [1] Deutsch  [2] English   [1]
```

Non-interactive: `./install.sh --lang en` or `NOAH_LANG=en ./install.sh`.
It is stored in `~/.config/noah2games/settings.json`. Changeable later at any time:

- `noah2games lang en` / `noah2games lang de`
- web UI: button in the top right (`EN` / `DE`)

## Installation

On a **server**, use a dedicated service user so nothing runs as root:

```bash
sudo ./install.sh --user noah2games      # creates the user, installs to /home/noah2games, user service + linger
```

Normal install (inside your own account):

```bash
git clone https://github.com/Ronny-H-79/Noah2Games.git noah2games   # or copy the folder
cd noah2games          # this folder contains install.sh - NOT noah2games/noah2games (that is the Python package)
./install.sh --check        # only check what is missing (changes nothing)
./install.sh                # install, asks before adding missing packages
./install.sh --auto         # install missing packages without asking (sudo)
./install.sh --wizard       # install and start the wizard afterwards
```

The installer detects missing packages (e.g. Wine) via `pacman`, `apt`, `dnf` or `zypper` and installs them
with `sudo` on request. `--auto` forces that without asking.

It checks Python and Wine, copies the program files, creates the `noah2games` command and sets up
`~/.config/noah2games`. It needs **no** root rights.

## Web service (optional)

The installer asks: "start the web UI automatically (systemd service)?" Answering yes creates a **system
service** `/etc/systemd/system/noah2games-web.service` as root (`WantedBy=multi-user.target`, starts at boot) —
or as a normal user `~/.config/systemd/user/noah2games-web.service` (`systemctl --user enable --now`).
Without it, start the UI when you need it: `noah2games web`.

## Access from elsewhere

By default `127.0.0.1` only. From another machine via SSH tunnel:
`ssh -N -L 8790:127.0.0.1:8790 user@server`, then open `http://127.0.0.1:8790/?token=…`.
In a LAN/VPN: `noah2games web --host 0.0.0.0`. From the internet via nginx with HTTPS:
`sudo noah2games proxy --domain noah2games.example.de --write --cert` (writes the config, tests with `nginx -t`,
reloads nginx and fetches the certificate). Without nginx, HTTPS also works directly:
`noah2games web --tls-cert cert.pem --tls-key key.pem`. Details in the README.

## Security (short)

The UI is an admin console: **whoever has the token controls everything** — start, stop and delete servers,
add mods, send console commands. Therefore:

- Client install (mode `[1]`) and server with a domain (mode `[2]`): noah2games stays on `127.0.0.1`, access goes
  through the SSH tunnel or nginx with HTTPS. Only mode `[3]` binds directly to the outside.
- **Never expose it unencrypted to the internet.** With `--host 0.0.0.0` and no TLS the token travels in
  clear text through every hop. For public access use HTTPS via `noah2games proxy` or TLS directly.
- The installer warns about mode `[3]` (IP and port) and asks before continuing.

In detail, including what noah2games protects itself: `docs/zugriff.md`, section "Security".

## The token

After installation `noah2games url` shows the address with token, e.g.
`http://127.0.0.1:8790/?token=…`. The key lives in `~/.config/noah2games/token` (mode 0600) and protects the UI
against any website in your browser sending commands to `127.0.0.1` (without token: `HTTP 401`). Details in
the README, section "The token". Reset: delete the file, a new one is created on the next start.

## Set up

```bash
noah2games wizard
```

This runs in the **terminal on the server** — over SSH (`ssh user@server`) or on the console itself.
The wizard asks questions, so it needs an interactive session. The web interface cannot create an
instance; it only shows and manages existing ones.

The wizard asks for name, map, port and session name, creates the instance and offers to download the
server files (~12.4 GB, 10–30 minutes) and to set up a systemd service.

Without prompts, e.g. for scripts:

```bash
noah2games init --name test --dir ~/arkserver-test --map Ragnarok_WP --port 7790 --rcon-port 27025
noah2games update      # download the server files, then noah2games start
```

## Using it

```bash
noah2games web                    # start the web UI
noah2games url                    # show the ready-made address including token
noah2games status                 # process, RCON, last log line
noah2games start --wait 240
noah2games stop                   # SaveWorld → DoExit → SIGTERM
noah2games update --check         # is a Steam build available?
noah2games supervise --all        # auto-restart, scheduled restarts, backups
```

The UI shows a dashboard with all instances (status, CPU, RAM, players), per instance start/stop/update,
one-click RCON commands, player management, whitelist/bans, mod management with images, settings as a form,
backups, snapshots and a schedule.

## Autostart

```bash
systemctl --user daemon-reload
systemctl --user enable --now noah2games-<name>
loginctl enable-linger $USER      # keeps running without a logged-in session
```

## Uninstall

```bash
./install.sh --uninstall
```

Removes the program and launcher. **Kept:** instances (`~/arkserver-*`), settings (`~/.config/noah2games`),
backups (`~/noah2games-backups`), snapshots (`~/noah2games-snapshots`).

## Where things are

| Path | Content |
|---|---|
| `~/.local/share/noah2games` | program |
| `~/.local/bin/noah2games` | launcher |
| `~/.config/noah2games/<name>.json` | instance configuration |
| `~/.config/noah2games/token` | web token (0600) |
| `~/arkserver-<name>` | server files of the instance |
| `~/noah2games-backups/<name>` | world backups (tar.gz) |
| `~/noah2games-snapshots/<name>` | full instance snapshots (rollback after an update) |
