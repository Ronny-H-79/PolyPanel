# noah2games — multigame server manager for Linux · web UI in the browser

ARK: Survival Ascended · Satisfactory · 7 Days to Die · Space Engineers — one manager, one web UI.

English · [Deutsch](README.de.md) — the installer asks for the language up front, and the UI can switch
any time (button in the top right, `noah2games lang en` on the console).

[![Donate](https://img.shields.io/badge/Donate-PayPal-00457C?logo=paypal&logoColor=white)](https://www.paypal.com/donate/?business=ronnyhase%40fn.de&item_name=noah2games%20Servermanager&currency_code=EUR)
[![Discord](https://img.shields.io/badge/Discord-Ark--ASA--ASE--Hilfe-5865F2?logo=discord&logoColor=white)](https://discord.gg/ark-ase-asa-hilfe)

[![Ubuntu 24.04](docs/badges/en/ubuntu.svg)](#installation)
[![Arch](docs/badges/en/arch.svg)](#installation)
[![Debian](docs/badges/en/debian.svg)](#installation)
[![Fedora](docs/badges/en/fedora.svg)](#installation)
[![openSUSE](docs/badges/en/opensuse.svg)](#installation)

**[Installation](#installation)** · [Uninstall](#uninstall) · [Features](docs/funktionen.md) · [Access](docs/zugriff.md)

Your own server manager for ARK ASA dedicated servers: start, stop, updates, mods, backups, settings
and player management through a web interface.

> **Not an app for your PC — no Windows or macOS program.** noah2games runs as a service on the Linux
> server and is used in a **browser**: from your PC, laptop, tablet or phone, on your LAN or over VPN.
> You install it on the server **once** (`git clone`, `install.sh`); after that there is nothing to
> download and no program to launch — just the address with a token.

Plain Python (standard library only), SteamCMD for install and updates, Wine for the server process,
RCON for everything the server exposes.

![Dashboard](docs/screenshot-dashboard.png)

## More games (Satisfactory, 7 Days to Die, Space Engineers)

noah2games manages other dedicated servers besides ARK: Survival Ascended. The core (start/stop,
updates, backups, schedules, web UI, multi-instance) is game-agnostic; a **game profile** only
provides what the game needs:

| Profile | Steam app | Launch | Control |
|---|---|---|---|
| `ark` | 2430930 | `ArkAscendedServer.exe` under Wine | Source RCON |
| `satisfactory` | 1690800 | `FactoryServer.sh` (native) | HTTPS API `/api/v1` (bearer token) |
| `7d2d` | 294420 | `startserver.sh` (native) | Telnet (`TelnetPassword` in `serverconfig.xml`) |
| `spaceengineers` | 298740 | `DedicatedServer64/SpaceEngineersDedicated.exe` under Wine | no RCON — start/stop, XML config, server console |

Create an instance:

```bash
noah2games --name factory init --game satisfactory
noah2games --name horde   init --game 7d2d
noah2games --name yard    init --game spaceengineers
noah2games --name factory start
```

The web UI accepts the extra `game` parameter on `POST /api/instances`. Ports: Satisfactory needs
three (`-Port`, `-QueryPort`, `-BeaconPort`), 7 Days to Die game, query and telnet ports. Instance
directories live in `~/noah2games-instances/<name>`.

## Screenshots

| | |
|:--:|:--:|
| ![Settings](docs/screenshot-settings.png) | ![Mods](docs/screenshot-mods.png) |
| ![Overview](docs/screenshot-overview.png) | ![Management](docs/screenshot-manage.png) |

## Installation

```bash
git clone https://github.com/Ronny-H-79/Noah2Games.git noah2games   # once
cd noah2games
./install.sh --check     # check what is missing (changes nothing)
./install.sh             # install
noah2games wizard              # create an instance, download the server, set up the service
```

**Requirements:** Linux, Python ≥ 3.10, Wine, `curl` and `tar`. Missing packages are offered by the
installer (`pacman`, `apt`, `dnf`, `zypper`). SteamCMD is downloaded automatically; root is only needed
to install Wine.

**Where it is tested** — as of 8 November 2026, each with a running ARK ASA server:

| System | Version | Environment |
|---|---|---|
| Ubuntu LTS | 24.04.5 | Python 3.12.3, Wine 9.0 |
| Arch Linux (CachyOS) | current | Python 3.14.9, Wine 11.21 |

Debian, Fedora and openSUSE are supported by the installer as well (`apt`, `dnf`, `zypper`), but noah2games
has not been tested there yet — feedback welcome. 64-bit Wine is required (the ARK server is a Windows
build); Wine older than 8.0 is untested.

Check your own box:

```bash
. /etc/os-release && echo "$PRETTY_NAME"; python3 --version; wine --version
```

The installer asks, in order:

- **language** (German/English)
- whether missing packages (**Wine**, iproute2) should be installed
- **how the UI should be reachable:**
  **Tunnel** — client-side only over SSH,
  **Domain** — public with HTTPS (stored for later),
  **IP** — directly via IP and port (HTTP, open the port in your firewall)
- **only for "Domain"**: whether the UI should run permanently (`noah2games-web.service`) — as root a
  **system service** in `/etc/systemd/system` (starts at boot, no login or `linger` needed), as a normal
  user a user service in `~/.config/systemd/user`

With **"Tunnel"** the last question is skipped: no long-running service is needed, the UI starts with
`noah2games web` when you want it.

At the end you get the command that matches your choice: the SSH tunnel with your user and the
**server IP** (not the hostname — often not resolvable from outside), or
`sudo noah2games proxy --write --cert`, which uses the stored domain.
`--web` / `--no-web` skips the service question.

> **Security:** the UI is an admin console — whoever has the token controls everything. Mode `[3]`
> (direct via IP) is **unencrypted** and the token can be read on the wire. Use `[1]` (SSH tunnel) or
> `[2]` (HTTPS). Details: [docs/zugriff.md](docs/zugriff.md).

### When the install gets stuck

| Message | Cause | Fix |
|---|---|---|
| `fatal: destination path 'noah2games' already exists` | the folder is already there | `cd noah2games && git pull` instead of cloning again |
| `./install.sh: No such file or directory` **after** `cd noah2games` | you are in the package folder `noah2games/noah2games` — only `.py` files live there | `cd ..` — `install.sh` is one level up |
| `noah2games: command not found` | `~/.local/bin` is not in `PATH` | as root the installer links `/usr/local/bin/noah2games`; otherwise `export PATH="$HOME/.local/bin:$PATH"` and open a new shell |

Details, requirements and uninstall: [INSTALL.md](INSTALL.md)

## Uninstall

**The program only** (instances, backups and settings stay):

```bash
./install.sh --uninstall
```

This also stops and removes the systemd units (`noah2games-web`, `noah2games-*`) so nothing points at a missing
file afterwards. If the source folder is already gone:

```bash
systemctl --user disable --now noah2games-web.service noah2games-test.service
rm -f ~/.config/systemd/user/noah2games-*.service ~/.local/bin/noah2games
rm -rf ~/.local/share/noah2games
```

**Everything** — additionally config, token, backups and server files (about 24 GB):

```bash
rm -rf ~/.config/noah2games          # instances, token, mod cache
rm -rf ~/noah2games-backups          # world backups
rm -rf ~/noah2games-snapshots        # instance snapshots
rm -rf ~/arkserver             # the server files (12 GB)
rm -rf ~/.wine-arkserver       # Wine prefix
```

Only the last step is irreversible: worlds and configs live in `~/noah2games-backups` — keep those and you can
restore everything later.

## More

| Topic | File |
|---|---|
| **Features** — overview, screenshots, mod search, Discord notifications | [docs/funktionen.md](docs/funktionen.md) |
| **Access** — SSH tunnel, LAN, HTTPS via nginx, token | [docs/zugriff.md](docs/zugriff.md) |
| **Operation** — self-update, changelog, language | [docs/betrieb.md](docs/betrieb.md) |
| **Internals** — structure, console, stop order | [docs/technik.md](docs/technik.md) |

What changed between versions: [CHANGELOG.en.md](CHANGELOG.en.md) ·
Install details: [INSTALL.md](INSTALL.md)

## Help

Questions, problems or just other server admins: the
**[Ark-ASA-ASE-Hilfe](https://discord.gg/ark-ase-asa-hilfe)** community on Discord helps with settings,
mods and start-up problems. That is also the place for feedback on noah2games.

## Licence

**Free to use, all rights reserved.** Downloading, installing and running it on your own servers is free
of charge — including for a community. Redistribution, modification, selling it or offering it as a
download/service requires written permission. Details: [LICENSE](LICENSE).

© 2026 Ronny H.
