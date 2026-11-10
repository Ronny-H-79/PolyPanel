# Zugriff auf die Oberfläche

Wie du die Weboberfläche erreichst — lokal, über SSH-Tunnel, im Netz oder öffentlich per HTTPS.

[← zurück zum README](../README.de.md) · [English](zugriff.md)

## Zugriff auf die Oberfläche (auch von woanders)

Standardmäßig hört noah2games nur auf `127.0.0.1` — die Oberfläche ist damit ausschließlich auf dem
Rechner selbst erreichbar. Das ist Absicht. Drei Wege, von woanders dranzukommen:

**1. SSH-Tunnel (empfohlen, nichts zu konfigurieren)**

Läuft noah2games auf einem Server, baust du von deinem Rechner aus einen Tunnel:

```bash
ssh -N -L 8790:127.0.0.1:8790 nutzer@server
```

Den Token holst du dir in einem zweiten Terminal vom Server:

```bash
ssh root@server noah2games url
```

Die Ausgabe ist die komplette Adresse inklusive Token — die öffnest du in deinem Browser
(`http://127.0.0.1:8790/?token=…`), der Tunnel leitet sie auf den Server. Der Verkehr ist
Ende-zu-Ende durch SSH verschlüsselt, nach außen ist nichts offen.

Wo der Token liegt, falls du ihn lieber direkt liest: `~/.config/noah2games/token` auf dem Server
(Rechte `0600`, also nur für den Benutzer lesbar, der noah2games installiert hat — bei einer
root-Installation `/root/.config/noah2games/token`). `noah2games url` zeigt beides an: die Adresse und den Pfad
zur Datei.

**2. Im eigenen Netz (LAN, VPN, Tailscale)**

```bash
noah2games web --host 0.0.0.0        # oder die VPN-Adresse, z. B. --host 100.x.y.z
```

Dann ist die Oberfläche unter `http://<ip-des-servers>:8790/?token=…` erreichbar — der Token bleibt
Pflicht. noah2games warnt beim Start, dass die Verbindung unverschlüsselt ist; im LAN oder im Tailscale-Netz
ist das vertretbar. Für den Dauerbetrieb `--host` in `ExecStart` von `noah2games-web.service` ergänzen und
`systemctl --user daemon-reload && systemctl --user restart noah2games-web` ausführen.

**2b. Direkt über IP und Port (ohne HTTPS)**

```bash
noah2games web --host 0.0.0.0
```

Dann `http://<server-ip>:8790/?token=…`. Der Installer wählt das mit `[3]` und legt den Dienst
gleich mit `--host 0.0.0.0` an. Achtung: unverschlüsselt — im LAN oder bei eigenem Firewall-Zugriff
vertretbar, offen im Internet nicht.

**3. Aus dem Internet: `noah2games proxy` richtet nginx ein**

Für ein Zertifikat braucht es einen Namen, der auf den Server zeigt (z. B. `noah2games.example.de`).
Dann übernimmt noah2games die nginx-Konfiguration — mit HTTPS, Weiterleitung von HTTP, langen Timeouts
für Snapshots und ohne Token in den Logs:

```bash
noah2games proxy --domain noah2games.example.de                       # Konfiguration nur anzeigen
noah2games proxy --domain noah2games.example.de > noah2games.conf           # in eine Datei schreiben

sudo noah2games proxy --domain noah2games.example.de --write --cert   # schreiben, prüfen, nginx laden, Zertifikat holen
```

`--write` legt `/etc/nginx/sites-available/noah2games-<domain>.conf` an, verlinkt sie nach `sites-enabled`,
lässt `nginx -t` laufen und lädt nginx neu. Schlägt der Test fehl, wird alles wieder entfernt —
kein kaputter nginx bleibt zurück. `--cert` ruft anschließend certbot auf
(`--email du@example.de` optional, sonst ohne Adresse).

Zusätzliche Anmeldung vor dem Token:

```bash
sudo htpasswd -c /etc/nginx/.htpasswd-noah2games deinname
sudo noah2games proxy --domain noah2games.example.de --write --cert --auth-file /etc/nginx/.htpasswd-noah2games
```

**4. Ohne nginx: HTTPS direkt in noah2games**

Kleiner Aufbau, z. B. im LAN mit eigenem Zertifikat:

```bash
noah2games web --host 0.0.0.0 --tls-cert /pfad/cert.pem --tls-key /pfad/key.pem
```

Dann spricht die Oberfläche selbst HTTPS (getestet: `HTTP 200` mit Token, `401` ohne).

**In allen Fällen gilt:** ohne Token antwortet die Oberfläche mit `HTTP 401`. Der Token ist kein
Passwort, sondern der Zugangsschlüssel — wer ihn hat und den Port erreicht, kann den Server steuern.

## Sicherheit — was der Token bedeutet

Die Oberfläche ist eine **Administrationskonsole**, kein Schaufenster: wer den Token hat, kann Server
starten, stoppen und löschen, Mods eintragen, Backups anlegen und über die Konsole beliebige
Server-Befehle absetzen. Behandle den Link wie ein Passwort.

Daraus folgen drei Regeln:

- **`127.0.0.1` genügt überall dort, wo etwas davorsteht.** Bei einer Client-Installation (Modus `[1]`)
  läuft noah2games auf dem Server und hört nur lokal; die **Serveradresse** brauchst du im Tunnelbefehl
  (`ssh -N -L 8790:127.0.0.1:8790 nutzer@server`) — offen sein muss dafür nur SSH, noah2games selbst öffnet
  keinen Port.
  Bei einer Server-Installation mit Domain (Modus `[2]`) bleibt noah2games ebenfalls auf `127.0.0.1`, und
  nginx reicht die Anfragen verschlüsselt weiter. Nur Modus `[3]` bindet direkt an alle Adressen
  (`--host 0.0.0.0`) — und genau dafür gilt der nächste Punkt.
- **Unverschlüsseltes HTTP im Internet ist keine Option.** Im Modus `[3]` (direkt über IP und Port)
  wandert der Token im Klartext über jede Zwischenstation — WLAN, Proxy, Anbieter, Firmennetz. Wer ihn
  dort mitliest, hat Vollzugriff. Wenn es öffentlich sein muss: Modus `[2]` mit HTTPS.
- **Der Token steht in der Adresse**, also auch im Browser-Verlauf und in Lesezeichen. noah2games setzt
  `Referrer-Policy: no-referrer`, damit er nicht über Klicks auf fremde Seiten abfließt; beim Weitergeben
  eines Links geht er trotzdem mit. Neuen Token erzeugen: `rm ~/.config/noah2games/token` und Dienst neu
  starten (`systemctl --user restart noah2games-web` bzw. `systemctl restart noah2games-web`).

Was noah2games selbst absichert: jeder Aufruf ohne gültigen Token endet mit `401`, der Token wird in
konstanter Zeit verglichen, Antworten tragen `nosniff`, `X-Frame-Options: DENY` und eine restriktive
CSP, Mod- und Spieler-IDs werden validiert, und die Bild-Auslieferung kann das Verzeichnis nicht
verlassen. Was noah2games **nicht** kann: deinen Server absichern, auf dem es läuft — Firewall, Updates und
ein starker SSH-Zugang bleiben deine Aufgabe.

## Der Token — wozu der gut ist

Beim ersten Start erzeugt noah2games einen zufälligen Schlüssel und legt ihn in
`~/.config/noah2games/token` ab (Rechte `0600`, also nur für deinen Benutzer lesbar).
Die Adresse sieht damit so aus:

```
http://127.0.0.1:8790/?token=<dein-schluessel>
```

Anzeigen kannst du sie jederzeit mit `noah2games url`; `noah2games open` öffnet sie direkt im Browser. Die
Adresse erscheint auch beim Start von `noah2games web` und am Ende der Installation.

**Warum überhaupt, wo die Oberfläche doch nur lokal läuft?**
Der Webserver hört ausschließlich auf `127.0.0.1` — aus dem Internet ist er nicht erreichbar.
Trotzdem reicht der Token nicht zum Selbstzweck:

1. **Jede Webseite in deinem Browser darf `http://127.0.0.1:…` aufrufen.** Das ist kein Angriff
   über das Netzwerk, sondern läuft aus deinem eigenen Browser heraus. Ohne Token könnte eine
   beliebige offene Seite im Hintergrund `POST /api/stop` schicken und deinen Server herunterfahren,
   oder Befehle per `/api/command` absetzen. Mit Token nicht — sie kennt ihn nicht.
2. **Andere Benutzer und Programme auf demselben Rechner.** Der Token ist die einzige Zugangskontrolle;
   ohne ihn darf jeder lokale Prozess deine Server steuern.

**Was der Token nicht ist:** kein Benutzerkonto, kein Passwort, keine Verschlüsselung.
Wer die Datei lesen kann, hat vollen Zugriff — deshalb `0600` und deshalb gehört der Token
**nicht** in Screenshots, ins README oder ins Repository.

**Ohne oder mit falschem Token antwortet die Oberfläche mit `HTTP 401`.** Der Token lässt sich
alternativ als Header senden (`X-Token: <schlüssel>`), praktisch ist aber der Query-Parameter.

**Token zurücksetzen:** `~/.config/noah2games/token` löschen — beim nächsten Start entsteht ein neuer.
Achtung: danach sind alte Lesezeichen und geteilte Links tot. Backups und Instanzen sind davon
nicht betroffen, die liegen woanders.

