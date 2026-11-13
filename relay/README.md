# Report-Relay

Kleiner Weiterleitungsdienst für die Fehlermeldungen der Panels. Das Panel schickt seine
Meldung an die **eigene** Adresse; das Relay reicht sie an die Discord-Webhook-Adresse
weiter. Damit steht die Discord-Adresse nur auf deinem Server und nie im Panel-Repo.

Nur Standardbibliothek, kein pip, keine Abhängigkeiten.

## Adressen

    POST https://<deine-domain>/report/<PATH_KEY>    Meldung weiterleiten
    GET  https://<deine-domain>/health               Lebenszeichen

Das Panel erwartet `{"ok": true}` als Antwort; alles andere zeigt es als Fehler an.

## Einrichtung (root)

```bash
# 1) Benutzer und Programm
useradd --system --no-create-home --shell /usr/sbin/nologin reportrelay
install -d -o root -g root /opt/report-relay
install -m 0755 report-relay.py /opt/report-relay/
install -m 0644 report-relay.service /etc/systemd/system/

# 2) Konfiguration - Schlüssel und Discord-Adresse eintragen
SCHLUESSEL="$(head -c 24 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 32)"
install -m 0640 -o root -g reportrelay /dev/null /etc/report-relay.conf
cat > /etc/report-relay.conf <<EOF
DISCORD_URL=https://discord.com/api/webhooks/...
PATH_KEY=$SCHLUESSEL
LISTEN=127.0.0.1
PORT=8787
RATE_PER_IP=10
RATE_TOTAL=120
MAX_BYTES=65536
EOF
echo "Panel-Adresse: https://<deine-domain>/report/$SCHLUESSEL"

# 3) Dienst
systemctl daemon-reload
systemctl enable --now report-relay
systemctl status report-relay --no-pager
```

## nginx

```nginx
location /report/ {
    proxy_pass http://127.0.0.1:8787;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $remote_addr;
    client_max_body_size 64k;
    proxy_read_timeout 20s;
}

location = /health {
    proxy_pass http://127.0.0.1:8787;
    access_log off;
}
```

Danach `nginx -t && systemctl reload nginx`. TLS mit `certbot --nginx -d <deine-domain>`
(oder Zertifikat aus dem vorhandenen Setup übernehmen) — das Panel spricht nur `https://`.

## Test

```bash
curl -s https://<deine-domain>/health
curl -s -X POST https://<deine-domain>/report/<PATH_KEY> \
  -H 'Content-Type: application/json' \
  -d '{"content":"Testmeldung vom Relay"}'
```

Beides muss `{"ok": true}` liefern, die Meldung im Discord-Kanal auftauchen.

## Panel darauf zeigen lassen

```bash
./install.sh --report-hook https://<deine-domain>/report/<PATH_KEY>
```

Ohne Adresse bleibt der Knopf „Fehler melden" versteckt. Wer die Adresse im Installer
als Standard eintragen will, setzt `DEFAULT_HOOK` in `install.sh` auf diese URL — die ist
öffentlich unbedenklich, weil sie nur weiterleitet und mengenbegrenzt ist.

## Grenzen

- `RATE_PER_IP`/`RATE_TOTAL` schützen den Kanal vor Spam; bei Überschreitung antwortet das
  Relay mit `429`.
- Weitergeleitet werden nur `content`, `embeds`, `username`, `avatar_url` — alles andere
  wird verworfen, damit Fremde keine Mentions, Rollen-Pings oder Datei-Uploads einschleusen.
- Es werden keine Meldungen gespeichert; das Relay reicht nur durch und protokolliert
  Pfad und Statuscode.
