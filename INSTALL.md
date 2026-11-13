# Installing PolyPanel

An installer for your own multigame server manager (ARK: Survival Ascended, ARK: Survival Evolved,
Satisfactory, 7 Days to Die, Space Engineers). Everything runs locally: Python standard library
plus SteamCMD and Wine.

[← back to the README](README.md) · [Deutsch](INSTALL.de.md)

## Requirements

| What | Why | Check |
|---|---|---|
| Linux (x86_64) | tested on CachyOS/Arch | `uname -m` |
| Python ≥ 3.10 | the program runs on it | `python3 -V` |
| Wine ≥ 8 | runs the Windows server files | `wine --version` |
| ~30 GB disk per instance | 12.4 GB download + backups | `df -h ~` |
| ~10 GB RAM without mods, more with mods and players (no upper limit) | ARK needs it | `free -g` |

Missing Wine:

```bash
sudo pacman -S wine           # Arch / CachyOS
sudo apt install wine         # Debian / Ubuntu
```

SteamCMD is downloaded automatically to `~/steamcmd` on first install — no root needed. The required
32-bit libraries are installed by the installer itself (lib32gcc, libc6:i386 or the distribution's
packages); without them SteamCMD aborts with “exit 127”.

## Language

The installer asks first:

```
Sprache / Language:  [1] Deutsch  [2] English   [1]
```

Non-interactive: `./install.sh --lang en` or `NOAH_LANG=en ./install.sh`.
It is stored in `~/.config/polypanel/settings.json`. Changeable later at any time:

- `polypanel lang en` / `polypanel lang de`
- web UI: button in the top right (`EN` / `DE`)

## Installation

Install in your own user account — **without sudo**:

```bash
git clone https://github.com/Ronny-H-79/PolyPanel.git polyPanel
cd polyPanel && ./install.sh
```

Everything goes to `~/.local/share/polypanel`, instances to `~/polypanel-instances`, servers run as your
user. **Satisfactory only starts this way** — the server refuses to run as root.

Starting `install.sh` as **root** is handled automatically: it creates the service user `polypanel` and
installs there (`/home/polypanel`), so neither the panel nor the servers run as root. A different name
via `--user <name>`.

On a **server**, use a dedicated service user so nothing runs as root:

```bash
sudo ./install.sh --user polypanel      # creates the user, installs to /home/PolyPanel, user service + linger
```

Normal install (inside your own account):

```bash
git clone https://github.com/Ronny-H-79/PolyPanel.git polypanel   # or copy the folder
cd polypanel          # this folder contains install.sh - NOT PolyPanel/polypanel (that is the Python package)
./install.sh --check        # only check what is missing (changes nothing)
./install.sh                # install, asks before adding missing packages
./install.sh --auto         # install missing packages without asking (sudo)
./install.sh --wizard       # install and start the wizard afterwards
```

The installer detects missing packages (e.g. Wine) via `pacman`, `apt`, `dnf` or `zypper` and installs them
with `sudo` on request. `--auto` forces that without asking.

It checks Python and Wine, copies the program files, creates the `polypanel` command and sets up
`~/.config/polypanel`. It needs **no** root rights.

## Web service (optional)

The installer asks: "start the web UI automatically (systemd service)?" Answering yes creates a **system
service** `/etc/systemd/system/polypanel-web.service` as root (`WantedBy=multi-user.target`, starts at boot) —
or as a normal user `~/.config/systemd/user/polypanel-web.service` (`systemctl --user enable --now`).
Without it, start the UI when you need it: `polypanel web`.

## Access from elsewhere

By default `127.0.0.1` only. From another machine via SSH tunnel:
`ssh -N -L 8790:127.0.0.1:8790 user@server`, then open `http://127.0.0.1:8790/?token=…`.
In a LAN/VPN: `polypanel web --host 0.0.0.0`. From the internet via nginx with HTTPS:
`sudo polypanel proxy --domain PolyPanel.example.de --write --cert` (writes the config, tests with `nginx -t`,
reloads nginx and fetches the certificate). Without nginx, HTTPS also works directly:
`polypanel web --tls-cert cert.pem --tls-key key.pem`. Details in the README.

## Security (short)

The UI is an admin console: **whoever has the token controls everything** — start, stop and delete servers,
add mods, send console commands. Therefore:

- Client install (mode `[1]`) and server with a domain (mode `[2]`): polypanel stays on `127.0.0.1`, access goes
  through the SSH tunnel or nginx with HTTPS. Only mode `[3]` binds directly to the outside.
- **Never expose it unencrypted to the internet.** With `--host 0.0.0.0` and no TLS the token travels in
  clear text through every hop. For public access use HTTPS via `polypanel proxy` or TLS directly.
- The installer warns about mode `[3]` (IP and port) and asks before continuing.

In detail, including what polypanel protects itself: `docs/zugriff.md`, section "Security".

## The token

After installation `polypanel url` shows the address with token, e.g.
`http://127.0.0.1:8790/?token=…`. The key lives in `~/.config/polypanel/token` (mode 0600) and protects the UI
against any website in your browser sending commands to `127.0.0.1` (without token: `HTTP 401`). Details in
the README, section "The token". Reset: delete the file, a new one is created on the next start.

## Set up

**Normal way — in the browser:**

```bash
polypanel web
```

Open the printed address with token, enter an instance name, pick the game (and map for ARK), press
**Anlegen / Create**, then **Install** on the new card. That downloads the server files (~20 GB for
ARK Evolved) and the service is registered automatically.

**Optional, console only — the wizard:**

```bash
polypanel wizard
```

This runs in the **terminal on the server** — over SSH (`ssh user@server`) or on the console itself.
The wizard asks questions, so it needs an interactive session. It is not required: the same steps are
in the web interface (name, game, map, **Anlegen**, **Installieren**).

The wizard asks for name, map, port and session name, creates the instance and offers to download the
server files (~12.4 GB, 10–30 minutes) and to set up a systemd service.

Without prompts, e.g. for scripts:

```bash
polypanel init --name test --dir ~/arkserver-test --map Ragnarok_WP --port 7790 --rcon-port 27025
polypanel update      # download the server files, then polypanel start
```

## Using it

```bash
polypanel web                    # start the web UI
polypanel url                    # show the ready-made address including token
polypanel status                 # process, RCON, last log line
polypanel start --wait 240
polypanel stop                   # SaveWorld → DoExit → SIGTERM
polypanel update --check         # is a Steam build available?
polypanel supervise --all        # auto-restart, scheduled restarts, backups
```

The UI shows a dashboard with all instances (status, CPU, RAM, players), per instance start/stop/update,
one-click RCON commands, player management, whitelist/bans, mod management with images, settings as a form,
backups, snapshots and a schedule.

## Autostart

```bash
systemctl --user daemon-reload
systemctl --user enable --now polypanel-<name>
loginctl enable-linger $USER      # keeps running without a logged-in session
```

**Token forgotten or address lost?**

```bash
polypanel token          # web token plus file path and address
polypanel token --quiet  # only the token (for scripts)
polypanel url            # ready-made address including the token
```

The token is also stored in `~/.config/polypanel/token` (mode `600`).

## Uninstall

```bash
cd ~/polypanel          # your clone of the repo
./install.sh --uninstall
```

Removes the program and launcher. **Kept:** instances (`~/arkserver-*`), settings (`~/.config/polypanel`),
backups (`~/polypanel-backups`), snapshots (`~/polypanel-snapshots`).

**SteamCMD** (`~/steamcmd`, `~/.steam`, `~/Steam`) is removed by `--uninstall` as well.

### Remove everything (instances and worlds too)

```bash
cd ~/polypanel          # your clone of the repo
./install.sh --uninstall
rm -rf ~/polypanel-instances ~/.config/polypanel ~/polypanel-backups ~/polypanel-snapshots
rm -rf ~/.wine ~/.polypanel-wine-se # wine prefixes (default and Space Engineers)
rm -f /etc/systemd/system/polypanel-*.service
systemctl daemon-reload
```

Where things live: program `~/.local/share/polypanel` and `~/.local/bin/polypanel`, settings and
token `~/.config/polypanel`, instances with worlds `~/polypanel-instances/<name>`, SteamCMD `~/steamcmd`,
`~/.steam` and `~/Steam`.

## Where things are

| Path | Content |
|---|---|
| `~/.local/share/polypanel` | program |
| `~/.local/bin/polypanel` | launcher |
| `~/.config/polypanel/<name>.json` | instance configuration |
| `~/.config/polypanel/token` | web token (0600) |
| `~/polypanel-instances/<name>` | server files of the instance |
| `~/polypanel-backups/<name>` | world backups (tar.gz) |
| `~/polypanel-snapshots/<name>` | full instance snapshots (rollback after an update) |

---

© 2026 Ronny H. · Free to use, all rights reserved — [Licence](LICENSE)
