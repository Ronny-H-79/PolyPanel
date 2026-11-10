#!/usr/bin/env bash
# noah2games - Installer fuer den eigenen Multigame-Servermanager
#               (ARK: Survival Ascended, Satisfactory, 7 Days to Die, Space Engineers)
#
#   ./install.sh                 Installation nach ~/.local/share/noah2games
#   ./install.sh --lang en       Sprache ohne Rueckfrage (de|en)
#   ./install.sh --check         nur pruefen, was fehlt (aendert nichts)
#   ./install.sh --auto          fehlende Pakete ohne Rueckfrage installieren (sudo)
#   ./install.sh --wizard        danach den Einrichtungsassistenten starten
#   ./install.sh --user noah2games     als eigener Dienst-Benutzer installieren (root, empfohlen)
#   ./install.sh --uninstall     wieder entfernen (Instanzen bleiben erhalten)
#
# Umgebungsvariablen: NOAH_HOME (Zielordner), NOAH_BIN (Launcher-Ordner),
#                     PYTHON (Interpreter), NOAH_LANG (de|en)
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${NOAH_HOME:-$HOME/.local/share/noah2games}"
BIN="${NOAH_BIN:-$HOME/.local/bin}"
PY="${PYTHON:-python3}"
RUN_WIZARD=0
UNINSTALL=0
CHECK_ONLY=0
AUTO=0
LANG_SEL="${NOAH_LANG:-}"
WANT_WEB=""
SERVICE_USER=""

while [ $# -gt 0 ]; do
  case "$1" in
    --wizard) RUN_WIZARD=1 ;;
    --uninstall) UNINSTALL=1 ;;
    --check) CHECK_ONLY=1 ;;
    --auto|-y|--yes) AUTO=1 ;;
    --web) WANT_WEB=1 ;;
    --no-web) WANT_WEB=0 ;;
    --user=*) SERVICE_USER="${1#*=}" ;;
    --user) shift; SERVICE_USER="${1:-}" ;;
    --lang=*) LANG_SEL="${1#*=}" ;;
    --lang) shift; LANG_SEL="${1:-}" ;;
    -h|--help) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    de|en) LANG_SEL="$1" ;;
    *) echo "Unbekannte Option: $1"; exit 1 ;;
  esac
  shift
done

# ---------------------------------------------------------------- Dienst-Benutzer
if [ -n "$SERVICE_USER" ]; then
  if [ "$(id -u)" != "0" ]; then
    echo "--user braucht root (Benutzer anlegen, Rechte setzen): sudo ./install.sh --user $SERVICE_USER"
    exit 1
  fi
  case "$SERVICE_USER" in
    *[!a-z0-9_-]*|"") echo "Ungueltiger Benutzername: $SERVICE_USER"; exit 1 ;;
  esac
  if ! id "$SERVICE_USER" >/dev/null 2>&1; then
    useradd -m -s /bin/bash "$SERVICE_USER"
    echo "Benutzer $SERVICE_USER angelegt."
  fi
  SERVICE_UID="$(id -u "$SERVICE_USER")"
  HOME="$(getent passwd "$SERVICE_USER" | cut -d: -f6)"
  export HOME
  [ -n "${NOAH_HOME:-}" ] || DEST="$HOME/.local/share/noah2games"
  [ -n "${NOAH_BIN:-}" ]  || BIN="$HOME/.local/bin"
fi

# ---------------------------------------------------------------- Sprache
if [ -z "$LANG_SEL" ]; then
  if [ -t 0 ] && [ "$CHECK_ONLY" = "0" ]; then
    printf 'Sprache / Language:  [1] Deutsch  [2] English   [1] '
    read -r _a || _a=""
    case "$_a" in
      2|en|EN|En|english|English) LANG_SEL="en" ;;
      *) LANG_SEL="de" ;;
    esac
  else
    LANG_SEL="de"
  fi
fi
case "$LANG_SEL" in
  en|EN|En|english|English) LANG_SEL="en" ;;
  *) LANG_SEL="de" ;;
esac

t() {
  case "$LANG_SEL:$1" in
    en:title)              echo "Installing noah2games" ;;
    de:title)              echo "noah2games installieren" ;;
    en:python_missing)     echo "Python 3 not found (set PYTHON=/path/to/python3)" ;;
    de:python_missing)     echo "Python 3 nicht gefunden (PYTHON=/pfad/zu/python3 setzen)" ;;
    en:python_old)         echo "Error: Python 3.10 or newer required, found %s" ;;
    de:python_old)         echo "Fehler: Python 3.10 oder neuer noetig, gefunden %s" ;;
    en:present)            echo "$2: present" ;;
    de:present)            echo "$2: vorhanden" ;;
    en:missing_ask)        echo "$2 is missing. Install now? [y/N] " ;;
    de:missing_ask)        echo "$2 fehlt. Jetzt installieren? [j/N] " ;;
    en:auto_install)       echo "$2 missing - installing" ;;
    de:auto_install)       echo "$2 fehlt - wird installiert" ;;
    en:installed)          echo "$2 installed" ;;
    de:installed)          echo "$2 installiert" ;;
    en:install_failed)     echo "Installation of $2 failed" ;;
    de:install_failed)     echo "Installation von $2 fehlgeschlagen" ;;
    en:still_missing)      echo "$2 still missing - the server will not start" ;;
    de:still_missing)      echo "$2 fehlt weiterhin - der Server startet damit nicht" ;;
    en:no_pkgmgr)          echo "no package manager detected - please install manually: $2" ;;
    de:no_pkgmgr)          echo "keine Paketverwaltung erkannt - bitte von Hand installieren: $2" ;;
    en:no_sudo)            echo "sudo missing - please install as root: $2" ;;
    de:no_sudo)            echo "sudo fehlt - bitte als root installieren: $2" ;;
    en:check_missing)      echo "$2 missing${3:+ (package: $3)}" ;;
    de:check_missing)      echo "$2 fehlt${3:+ (Paket: $3)}" ;;
    en:uninstall)          echo "Removing noah2games" ;;
    de:uninstall)          echo "noah2games entfernen" ;;
    en:service_removed)    echo "service stopped and removed: $2" ;;
    de:service_removed)    echo "Dienst beendet und entfernt: $2" ;;
    en:removed)            echo "Launcher and program files removed." ;;
    de:removed)            echo "Launcher und Programmdateien entfernt." ;;
    en:kept)               echo "Instances, backups and settings are kept:" ;;
    de:kept)               echo "Instanzen, Backups und Einstellungen sind geblieben:" ;;
    en:steamcmd_later)     echo "SteamCMD: downloaded automatically on first install (no root needed)" ;;
    de:steamcmd_later)     echo "SteamCMD: wird beim ersten Installieren automatisch geladen (kein root noetig)" ;;
    en:all_present)        echo "Everything is present." ;;
    de:all_present)        echo "Alles vorhanden." ;;
    en:pkgs_missing)       echo "Packages are missing - see above." ;;
    de:pkgs_missing)       echo "Es fehlen Pakete - siehe oben." ;;
    en:copied)             echo "Program files: $2" ;;
    de:copied)             echo "Programmdateien: $2" ;;
    en:command)            echo "Command: $2" ;;
    de:command)            echo "Befehl: $2" ;;
    en:service_restarted)  echo "web service restarted (new code active)" ;;
    de:service_restarted)  echo "Web-Dienst neu gestartet (neuer Code aktiv)" ;;
    en:linked_usr_local)   echo "Command available as 'noah2games' (symlink in /usr/local/bin)" ;;
    de:linked_usr_local)   echo "Befehl 'noah2games' verfuegbar (Symlink in /usr/local/bin)" ;;
    en:path_hint)          echo "Note: $2 is not in PATH - e.g. add to ~/.config/fish/config.fish:" ;;
    de:path_hint)          echo "Hinweis: $2 ist nicht im PATH - z. B. in ~/.config/fish/config.fish ergaenzen:" ;;
    en:done)               echo "Done. Next steps:" ;;
    de:done)               echo "Fertig. Naechste Schritte:" ;;
    en:wizard_step)        echo "  noah2games wizard          create an instance, download the server, set up a service" ;;
    de:wizard_step)        echo "  noah2games wizard          Instanz anlegen, Server laden, Dienst einrichten" ;;
    en:supervise_step)     echo "  noah2games supervise --all   watch all instances" ;;
    en:uninstall_step)     echo "  ./install.sh --uninstall   remove noah2games (instances and backups stay)" ;;
    de:uninstall_step)     echo "  ./install.sh --uninstall   noah2games entfernen (Instanzen und Backups bleiben)" ;;
    de:supervise_step)     echo "  noah2games supervise --all   alle Instanzen ueberwachen" ;;
    en:web)                echo "Web interface (after 'noah2games web'):" ;;
    de:web)                echo "Web interface (nach 'noah2games web'):" ;;
    en:net_note)           echo "only with: noah2games web --host 0.0.0.0" ;;
    de:net_note)           echo "nur mit: noah2games web --host 0.0.0.0" ;;
    en:token_hint)         echo "  token is also stored in ~/.config/noah2games/token - show it again with: noah2games url" ;;
    de:token_hint)         echo "  Token auch in ~/.config/noah2games/token - erneut anzeigen mit: noah2games url" ;;
    en:access_q)          echo "How should the web interface be reachable?  [1] client-side only (SSH tunnel)  [2] public via domain with HTTPS  [3] direct via IP and port (HTTP)   [1] " ;;
    de:access_q)          echo "Wie soll die Oberflaeche erreichbar sein?  [1] nur Client-seitig (SSH-Tunnel)  [2] oeffentlich ueber Domain mit HTTPS  [3] direkt ueber IP und Port (HTTP)   [1] " ;;
    en:access_domain_q)   echo "Domain (must point to this server): " ;;
    de:access_domain_q)   echo "Domain (muss auf diesen Server zeigen): " ;;
    en:access_tunnel)     echo "Access from another machine: ssh -N -L 8790:127.0.0.1:8790 $(id -un)@$MYIP" ;;
    de:access_tunnel)     echo "Zugriff von einem anderen Rechner: ssh -N -L 8790:127.0.0.1:8790 $(id -un)@$MYIP" ;;
    en:access_https)      echo "HTTPS einrichten mit: sudo noah2games proxy --write --cert" ;;
    de:access_https)      echo "HTTPS einrichten mit: sudo noah2games proxy --write --cert" ;;
    en:ip_warning_strong)  echo "WARNING: this makes the interface reachable from the internet WITHOUT encryption."; echo "         Whoever reads the token (Wi-Fi, proxy, hosting provider, browser history) can start,"; echo "         stop and delete servers and send console commands. Mode [1] or [2] avoids this." ;;
    de:ip_warning_strong)  echo "WARNUNG: Damit ist die Oberflaeche aus dem Internet erreichbar - UNVERSCHLUESSELT."; echo "         Wer den Token mitliest (WLAN, Proxy, Anbieter, Browser-Verlauf), kann Server starten,"; echo "         stoppen, loeschen und Konsolenbefehle absetzen. Modus [1] oder [2] vermeidet das." ;;
    en:ip_confirm)         echo "Really set it up this way?  [j/N] " ;;
    de:ip_confirm)         echo "Trotzdem so einrichten?  [j/N] " ;;
    en:ip_warning)         echo "Note: reachable over the network without HTTPS - the token protects the UI, traffic is unencrypted. Open port 8790 in the firewall." ;;
    de:ip_warning)         echo "Hinweis: im Netzwerk ohne HTTPS erreichbar - der Token schuetzt die Oberflaeche, die Uebertragung ist unverschluesselt. Port 8790 in der Firewall freigeben." ;;
    en:web_not_needed)     echo "No permanent service needed - the UI starts on demand: noah2games web" ;;
    de:web_not_needed)     echo "Kein Dauerdienst noetig - Oberflaeche startet bei Bedarf: noah2games web" ;;
    en:web_q)              echo "Start the web interface automatically (systemd service)? [y/N] " ;;
    de:web_q)              echo "Web-Oberflaeche automatisch starten (systemd-Dienst)? [j/N] " ;;
    en:web_installed_system) echo "Web interface runs as systemd system service (starts at boot): systemctl status noah2games-web" ;;
    de:web_installed_system) echo "Web-Oberflaeche laeuft als Systemdienst (startet beim Booten): systemctl status noah2games-web" ;;
    en:web_installed_user) echo "Web interface runs as $2 - user service noah2games-web; check: su - $2 -c 'systemctl --user status noah2games-web'" ;;
    de:web_installed_user) echo "Web-Oberflaeche laeuft als Benutzer $2 - User-Dienst noah2games-web; pruefen: su - $2 -c 'systemctl --user status noah2games-web'" ;;
    en:web_installed)      echo "Web interface runs as noah2games-web.service - check: systemctl --user status noah2games-web" ;;
    de:web_installed)      echo "Web-Oberflaeche laeuft als noah2games-web.service - pruefen: systemctl --user status noah2games-web" ;;
    en:web_failed)         echo "Could not enable the service - start manually with: noah2games web" ;;
    de:web_failed)         echo "Dienst konnte nicht aktiviert werden - manuell starten mit: noah2games web" ;;
    en:web_skipped)        echo "No service created - start the UI when needed with: noah2games web" ;;
    de:web_skipped)        echo "Kein Dienst angelegt - Oberflaeche bei Bedarf starten mit: noah2games web" ;;
    en:language_saved)     echo "Language: English" ;;
    de:language_saved)     echo "Sprache: Deutsch" ;;
    *) return 1 ;;
  esac
}

MYIP="$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}')"
[ -n "$MYIP" ] || MYIP="$(hostname -I 2>/dev/null | awk '{print $1}')"
[ -n "$MYIP" ] || MYIP="127.0.0.1"

say()  { printf '  %s\n' "$*"; }
warn() { printf '  ! %s\n' "$*"; }
die()  { printf '%s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- Distribution
PKG_MGR=""
if command -v pacman >/dev/null 2>&1; then PKG_MGR="pacman"
elif command -v apt-get >/dev/null 2>&1; then PKG_MGR="apt"
elif command -v dnf >/dev/null 2>&1; then PKG_MGR="dnf"
elif command -v zypper >/dev/null 2>&1; then PKG_MGR="zypper"
fi

pkg_name() {
  case "$1:$PKG_MGR" in
    wine:pacman) echo "wine" ;;
    wine:apt)    echo "wine" ;;
    wine:dnf)    echo "wine" ;;
    wine:zypper) echo "wine" ;;
    iproute2:pacman) echo "iproute2" ;;
    iproute2:apt)    echo "iproute2" ;;
    iproute2:dnf)    echo "iproute2" ;;
    iproute2:zypper) echo "iproute2" ;;
    *) echo "$1" ;;
  esac
}

have_sudo() { command -v sudo >/dev/null 2>&1; }

install_pkg() {
  local logical="$1" name
  name="$(pkg_name "$logical")"
  if [ -z "$PKG_MGR" ]; then
    warn "$(t no_pkgmgr "$name")"
    return 1
  fi
  if ! have_sudo; then
    warn "$(t no_sudo "$name")"
    return 1
  fi
  case "$PKG_MGR" in
    pacman) sudo pacman -S --needed --noconfirm "$name" ;;
    apt)    sudo apt-get update -qq && sudo apt-get install -y "$name" ;;
    dnf)    sudo dnf install -y "$name" ;;
    zypper) sudo zypper --non-interactive install "$name" ;;
  esac
}

ask_install() {
  local logical="$1" label="$2"
  if [ "$AUTO" = "1" ]; then
    say "$(t auto_install "$label")"
    if install_pkg "$logical"; then say "$(t installed "$label")"; else warn "$(t install_failed "$label")"; fi
    return 0
  fi
  if [ "$CHECK_ONLY" = "1" ]; then
    warn "$(t check_missing "$label" "$(pkg_name "$logical")")"
    return 0
  fi
  printf '  %s ' "$(t missing_ask "" "$label")"
  read -r answer || answer=""
  case "$answer" in
    j|J|y|Y|ja|Ja|yes|Yes)
      if install_pkg "$logical"; then say "$(t installed "$label")"; else warn "$(t install_failed "$label")"; fi ;;
    *) warn "$(t still_missing "$label")" ;;
  esac
}

# ---------------------------------------------------------------- Sprache speichern
save_lang() {
  mkdir -p "$HOME/.config/noah2games"
  "$PY" - "$LANG_SEL" <<'PYEOF'
import json, os, sys
path = os.path.expanduser("~/.config/noah2games/settings.json")
data = {}
try:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
except (OSError, ValueError):
    data = {}
data["lang"] = sys.argv[1]
with open(path, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2)
PYEOF
}

# ---------------------------------------------------------------- Deinstallation
if [ "$UNINSTALL" = "1" ]; then
  t uninstall
  # laufende Dienste zuerst beenden, sonst zeigen sie nach dem Loeschen ins Leere
  for unit in "$HOME"/.config/systemd/user/noah2games-*.service; do
    [ -e "$unit" ] || continue
    name="$(basename "$unit")"
    systemctl --user disable --now "$name" >/dev/null 2>&1 || true
    rm -f "$unit"
    say "$(t service_removed "$name")"
  done
  systemctl --user daemon-reload >/dev/null 2>&1 || true
  rm -f "$BIN/noah2games"
  rm -rf "$DEST"
  say "$(t removed)"
  say "$(t kept)"
  say "  ~/.config/noah2games   ~/arkserver-*   ~/noah2games-backups   ~/noah2games-snapshots"
  exit 0
fi

t title
echo "-------------------"

# ---------------------------------------------------------------- Pruefungen
command -v "$PY" >/dev/null 2>&1 || die "$(t python_missing)"

"$PY" - <<'PYEOF' || exit 1
import sys
if sys.version_info < (3, 10):
    print("Python 3.10 or newer required, found %d.%d / Python 3.10 oder neuer noetig, gefunden %d.%d" % (sys.version_info[:2] * 2))
    sys.exit(1)
print("  Python %d.%d.%d ok" % sys.version_info[:3])
PYEOF

save_lang
say "$(t language_saved)"

MISSING=0

if command -v wine >/dev/null 2>&1; then
  say "$(t present "Wine") $(wine --version 2>/dev/null | head -1)"
else
  MISSING=1
  ask_install wine "Wine"
fi

if command -v ss >/dev/null 2>&1; then
  say "$(t present "iproute2 (ss)")"
else
  MISSING=1
  ask_install iproute2 "iproute2"
fi

for tool in tar curl; do
  if command -v "$tool" >/dev/null 2>&1; then
    say "$(t present "$tool")"
  else
    MISSING=1
    warn "$tool: $(t still_missing "$tool")"
  fi
done

if command -v steamcmd >/dev/null 2>&1 || [ -x "$HOME/steamcmd/steamcmd.sh" ]; then
  say "$(t present "SteamCMD")"
else
  say "$(t steamcmd_later)"
fi

if [ "$CHECK_ONLY" = "1" ]; then
  echo
  if [ "$MISSING" = "1" ]; then t pkgs_missing; else t all_present; fi
  exit 0
fi


# ---------------------------------------------------------------- Zugriff
ACCESS=""
DOMAIN=""
if [ -t 0 ]; then
  printf '  %s' "$(t access_q)"
  read -r _a || _a=""
  case "$_a" in
    3) ACCESS="ip"
       t ip_warning_strong
       printf '  %s' "$(t ip_confirm)"
       read -r _ok || _ok=""
       case "$_ok" in
         j|J|y|Y|ja|Ja|yes|Yes) ;;
         *) ACCESS="tunnel" ;;
       esac ;;
    2) ACCESS="https"
       printf '  %s' "$(t access_domain_q)"
       read -r DOMAIN || DOMAIN="" ;;
    *) ACCESS="tunnel" ;;
  esac
fi
if [ "$ACCESS" = "ip" ]; then
  say "$(t ip_warning)"
fi
if [ -n "$ACCESS" ]; then
  "$PY" - "$ACCESS" "$DOMAIN" <<'PYEOF'
import json, os, sys
path = os.path.expanduser("~/.config/noah2games/settings.json")
data = {}
try:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
except (OSError, ValueError):
    data = {}
data["access"] = sys.argv[1]
if sys.argv[2]:
    data["domain"] = sys.argv[2].strip()
with open(path, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2)
PYEOF
fi

# ---------------------------------------------------------------- Kopieren
mkdir -p "$DEST" "$BIN" "$HOME/.config/noah2games"
cp -a "$SRC/noah2games" "$DEST/"
cp -a "$SRC/README.md" "$DEST/" 2>/dev/null || true
cp -a "$SRC/INSTALL.md" "$DEST/" 2>/dev/null || true
cp -a "$SRC"/CHANGELOG*.md "$DEST/" 2>/dev/null || true
find "$DEST" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
say "$(t copied "$DEST")"

# Installierten Stand festhalten (Commit), damit auch Aenderungen ohne Versionssprung ankommen
if command -v git >/dev/null 2>&1 && [ -d "$SRC/.git" ]; then
  SHA="$(git -C "$SRC" rev-parse --short HEAD 2>/dev/null || true)"
  VER="$(grep -m1 __version__ "$DEST/noah2games/__init__.py" 2>/dev/null | cut -d'"' -f2)"
  if [ -n "$SHA" ]; then
    printf '{"sha": "%s", "version": "%s", "written": "%s"}\n' "$SHA" "$VER" "$(date '+%F %T')" > "$DEST/noah2games/.build"
  else
    # Installation aus einem Archiv (kein .git): alten Stand nicht stehen lassen,
    # sonst meldet die Pruefung dauerhaft "neuer Stand verfuegbar"
    rm -f "$DEST/noah2games/.build"
  fi
fi

cat > "$BIN/noah2games" <<EOF
#!/bin/sh
# noah2games-Launcher (erzeugt von install.sh)
export PYTHONPATH="$DEST\${PYTHONPATH:+\$PYTHONPATH}"
# -P: aktuelles Verzeichnis nicht in sys.path - sonst importiert noah2games aus dem Quellordner
exec "$PY" -P -m noah2games "\$@"
EOF
chmod +x "$BIN/noah2games"
# bei --user gehoert alles dem Dienst-Benutzer, sonst kann er seine Configs nicht schreiben
if [ -n "$SERVICE_USER" ]; then
  chown -R "$SERVICE_USER":"$SERVICE_USER" "$DEST" "$HOME/.config/noah2games" "$BIN/noah2games" 2>/dev/null || true
fi
say "$(t command "$BIN/noah2games")"

case ":$PATH:" in
  *":$BIN:"*) ;;
  *)
    if [ "$(id -u)" = "0" ] && [ -d /usr/local/bin ] && [ -z "$SERVICE_USER" ]; then
      if ln -sf "$BIN/noah2games" /usr/local/bin/noah2games 2>/dev/null; then
        say "$(t linked_usr_local)"
      else
        say "$(t path_hint "$BIN")"
      fi
    else
      say "$(t path_hint "$BIN")"
      say "  fish_add_path $BIN"
      say "  # bash/zsh:  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
    fi ;;
esac

echo
t done
t wizard_step
t supervise_step
t uninstall_step

# ---------------------------------------------------------------- Web-Dienst
if [ -z "$WANT_WEB" ]; then
  if [ "$ACCESS" = "tunnel" ]; then
    # Client-seitig: die Oberflaeche wird bei Bedarf mit "noah2games web" gestartet, kein Dauerdienst noetig
    WANT_WEB=0
    say "$(t web_not_needed)"
  elif [ -t 0 ]; then
    printf '  %s' "$(t web_q)"
    read -r _w || _w=""
    case "$_w" in
      j|J|y|Y|ja|Ja|yes|Yes) WANT_WEB=1 ;;
      *) WANT_WEB=0 ;;
    esac
  else
    WANT_WEB=0
  fi
fi

WEBHOST=""
[ "$ACCESS" = "ip" ] && WEBHOST="--host 0.0.0.0"
if [ "$WANT_WEB" = "1" ]; then
  if [ -n "$SERVICE_USER" ]; then
    UNIT_DIR="$HOME/.config/systemd/user"
    install -d -o "$SERVICE_USER" -g "$SERVICE_USER" "$UNIT_DIR"
    cat > "$UNIT_DIR/noah2games-web.service" <<EOF
[Unit]
Description=noah2games web interface
After=network-online.target

[Service]
Type=simple
WorkingDirectory=$DEST
Environment=PYTHONPATH=$DEST
ExecStart=/usr/bin/python3 -m noah2games web $WEBHOST --port 8790
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF
    chown -R "$SERVICE_USER":"$SERVICE_USER" "$DEST" "$HOME/.config/noah2games" "$BIN/noah2games" "$UNIT_DIR" 2>/dev/null || true
    loginctl enable-linger "$SERVICE_USER" >/dev/null 2>&1 || true
    if su - "$SERVICE_USER" -c "XDG_RUNTIME_DIR=/run/user/$SERVICE_UID systemctl --user daemon-reload && XDG_RUNTIME_DIR=/run/user/$SERVICE_UID systemctl --user enable --now noah2games-web.service" >/dev/null 2>&1; then
      say "$(t web_installed_user "$SERVICE_USER")"
    else
      warn "$(t web_failed)"
    fi
  elif [ "$(id -u)" = "0" ]; then
    # Systemdienst: startet beim Booten, kein Login und kein linger noetig
    UNIT="/etc/systemd/system/noah2games-web.service"
    cat > "$UNIT" <<EOF
[Unit]
Description=noah2games web interface
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$DEST
Environment=PYTHONPATH=$DEST
ExecStart=/usr/bin/python3 -m noah2games web $WEBHOST --port 8790
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    if systemctl daemon-reload 2>/dev/null && systemctl enable --now noah2games-web.service 2>/dev/null; then
      say "$(t web_installed_system)"
    else
      warn "$(t web_failed)"
    fi
  else
    UNIT_DIR="$HOME/.config/systemd/user"
    mkdir -p "$UNIT_DIR"
    cat > "$UNIT_DIR/noah2games-web.service" <<EOF
[Unit]
Description=noah2games web interface
After=network-online.target

[Service]
Type=simple
WorkingDirectory=$DEST
Environment=PYTHONPATH=$DEST
ExecStart=/usr/bin/python3 -m noah2games web $WEBHOST --port 8790
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF
    if systemctl --user daemon-reload 2>/dev/null && systemctl --user enable --now noah2games-web.service 2>/dev/null; then
      say "$(t web_installed)"
    else
      warn "$(t web_failed)"
    fi
  fi
else
  say "$(t web_skipped)"
fi


# laufenden Web-Dienst neu starten, damit der neue Code aktiv ist
if systemctl is-active noah2games-web >/dev/null 2>&1; then
  systemctl restart noah2games-web >/dev/null 2>&1 && say "$(t service_restarted)"
elif systemctl --user is-active noah2games-web >/dev/null 2>&1; then
  systemctl --user restart noah2games-web >/dev/null 2>&1 && say "$(t service_restarted)"
fi

URL="$("$BIN/noah2games" url --quiet 2>/dev/null | head -1 || true)"
TOK="${URL##*token=}"
if [ -n "$TOK" ]; then
  echo
  t web
  echo "  ${URL}"
  if [ "$ACCESS" = "https" ] && [ -n "$DOMAIN" ]; then
    echo "  https://$DOMAIN/?token=$TOK"
  elif [ "$ACCESS" = "ip" ]; then
    echo "  http://$MYIP:8790/?token=$TOK"
  fi
  t token_hint
fi

if [ "$ACCESS" = "https" ] && [ -n "$DOMAIN" ]; then
  echo
  say "HTTPS: sudo noah2games proxy --domain $DOMAIN --write --cert"
elif [ "$ACCESS" = "tunnel" ]; then
  echo
  say "$(t access_tunnel)"
fi

if [ "$RUN_WIZARD" = "1" ]; then
  echo
  exec "$BIN/noah2games" wizard
fi
