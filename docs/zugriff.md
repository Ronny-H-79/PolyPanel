# Reaching the interface

How to get to the web UI — locally, over an SSH tunnel, in your network or publicly via HTTPS.

[← back to the README](../README.md) · [Deutsch](zugriff.de.md)

## Reaching the interface (also from somewhere else)

By default polypanel listens on `127.0.0.1` only — the UI is then reachable on that machine alone. That is
intentional. Three ways to get to it from elsewhere:

**1. SSH tunnel (recommended, nothing to configure)**

If polypanel runs on a server, build a tunnel from your machine:

```bash
ssh -N -L 8790:127.0.0.1:8790 user@server
```

Get the token in a second terminal on the server:

```bash
ssh root@server polypanel url
```

The output is the full address including the token — open it in your browser
(`http://127.0.0.1:8790/?token=…`), the tunnel forwards it to the server. Traffic is encrypted end to end
by SSH and nothing is exposed.

Where the token lives, if you prefer reading it: `~/.config/polypanel/token` on the server (mode `0600`, so
only the user who installed polypanel can read it — for a root install `/root/.config/PolyPanel/token`).
`polypanel url` shows both the address and the path to the file.

**2. In your own network (LAN, VPN, Tailscale)**

```bash
polypanel web --host 0.0.0.0        # or the VPN address, e.g. --host 100.x.y.z
```

The UI is then reachable at `http://<server-ip>:8790/?token=…` — the token is still required. polypanel warns
at startup that the connection is unencrypted; inside a LAN or a Tailscale network that is acceptable.
For permanent operation add `--host` to `ExecStart` of `polypanel-web.service` and run
`systemctl --user daemon-reload && systemctl --user restart polypanel-web`.

**2b. Directly via IP and port (without HTTPS)**

```bash
polypanel web --host 0.0.0.0
```

Then `http://<server-ip>:8790/?token=…`. The installer picks this with `[3]` and creates the service with
`--host 0.0.0.0` right away. Careful: unencrypted — acceptable in a LAN or behind your own firewall, not
openly on the internet.

**3. From the internet: `polypanel proxy` sets up nginx**

A certificate needs a name pointing at the server (e.g. `PolyPanel.example.de`). polypanel then writes the nginx
configuration — with HTTPS, HTTP redirect, long timeouts for snapshots and no token in the logs:

```bash
polypanel proxy --domain PolyPanel.example.de                       # just print the configuration
polypanel proxy --domain PolyPanel.example.de > PolyPanel.conf           # write it to a file

sudo polypanel proxy --domain PolyPanel.example.de --write --cert   # write, test, reload nginx, get a certificate
```

`--write` creates `/etc/nginx/sites-available/polypanel-<domain>.conf`, links it into `sites-enabled`, runs
`nginx -t` and reloads nginx. If the test fails everything is removed again — no broken nginx is left
behind. `--cert` then calls certbot (`--email you@example.de` optional, otherwise without an address).

Extra login in front of the token:

```bash
sudo htpasswd -c /etc/nginx/.htpasswd-polypanel yourname
sudo polypanel proxy --domain PolyPanel.example.de --write --cert --auth-file /etc/nginx/.htpasswd-PolyPanel
```

**4. Without nginx: HTTPS inside PolyPanel**

Small setup, e.g. in a LAN with your own certificate:

```bash
polypanel web --host 0.0.0.0 --tls-cert /path/cert.pem --tls-key /path/key.pem
```

The UI then speaks HTTPS itself (tested: `HTTP 200` with token, `401` without).

**In every case:** without a token the UI answers `HTTP 401`. The token is not a password but the access
key — whoever has it and can reach the port controls the server.

## Security — what the token means

The UI is an **admin console**, not a shop window: whoever has the token can start, stop and delete
servers, add mods, create backups and send arbitrary console commands. Treat the link like a password.

Three rules follow:

- **`127.0.0.1` is enough wherever something sits in front.** With a client install (mode `[1]`) polypanel runs
  on the server and listens locally; you need the **server address** in the tunnel command
  (`ssh -N -L 8790:127.0.0.1:8790 user@server`) — only SSH has to be open, polypanel itself opens no port.
  With a server install behind a domain (mode `[2]`) polypanel also stays on `127.0.0.1` and nginx forwards the
  requests encrypted. Only mode `[3]` binds to all addresses (`--host 0.0.0.0`) — and that is what the next
  point is about.
- **Unencrypted HTTP on the internet is not an option.** In mode `[3]` the token travels in clear text
  through every hop — Wi-Fi, proxy, hosting provider, corporate network. Whoever reads it has full access.
  If it must be public: mode `[2]` with HTTPS.
- **The token sits in the URL**, so it also lands in browser history and bookmarks. polypanel sets
  `Referrer-Policy: no-referrer` so it does not leak when clicking external links, but sharing the link
  passes it on. Create a new token: `rm ~/.config/polypanel/token` and restart the service
  (`systemctl --user restart polypanel-web` or `systemctl restart polypanel-web`).

What polypanel itself protects: every request without a valid token returns `401`, the token is compared in
constant time, responses carry `nosniff`, `X-Frame-Options: DENY` and a restrictive CSP, mod and player
IDs are validated, and image delivery cannot leave its directory. What polypanel **cannot** do: secure the
machine it runs on — firewall, updates and a strong SSH setup remain your job.

## The token — what it is for

On first start polypanel creates a random key and stores it in `~/.config/polypanel/token` (mode `0600`, readable by
your user only). The address then looks like this:

```
http://127.0.0.1:8790/?token=<your-key>
```

Show it any time with `polypanel url`; `polypanel open` opens it in the browser. It also appears when `polypanel web`
starts and at the end of the installation.

**Why at all, if the UI only runs locally?**
The web server listens on `127.0.0.1` exclusively — it cannot be reached from the internet. The token is
still not pointless:

1. **Any website in your browser may call `http://127.0.0.1:…`.** That is not a network attack but runs
   from inside your own browser. Without a token, any open page could send `POST /api/stop` in the
   background and shut your server down, or issue commands via `/api/command`. With a token it cannot — it
   does not know it.
2. **Other users and programs on the same machine.** The token is the only access control; without it any
   local process could control your servers.

**What the token is not:** no user account, no password, no encryption. Whoever can read the file has full
access — hence `0600`, and hence the token does **not** belong in screenshots, the README or the
repository.

**Without or with a wrong token the UI answers `HTTP 401`.** The token can also be sent as a header
(`X-Token: <key>`), but the query parameter is the practical route.

**Reset the token:** delete `~/.config/polypanel/token` — a new one is created on the next start. Note that old
bookmarks and shared links stop working. Backups and instances are unaffected.

---

© 2026 Ronny H. · Free to use, all rights reserved — [Licence](../LICENSE)
