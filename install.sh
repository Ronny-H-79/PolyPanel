#!/usr/bin/env bash
# polypanel - Installer fuer den eigenen Multigame-Servermanager
#               (ARK: Survival Ascended, Satisfactory, 7 Days to Die, Space Engineers)
#
#   ./install.sh                 Installation nach ~/.local/share/polypanel
#   ./install.sh --lang en       Sprache ohne Rueckfrage (de|en)
#   ./install.sh --check         nur pruefen, was fehlt (aendert nichts)
#   ./install.sh --auto          fehlende Pakete ohne Rueckfrage installieren (sudo)
#   ./install.sh --wizard        optional: danach den Konsolen-Assistenten starten
#   ./install.sh --user polypanel     als eigener Dienst-Benutzer installieren (root, empfohlen)
#   ./install.sh --uninstall     wieder entfernen (Instanzen bleiben erhalten)
#
# Umgebungsvariablen: POLYPANEL_HOME (Zielordner), NOAH_BIN (Launcher-Ordner),
#                     PYTHON (Interpreter), NOAH_LANG (de|en)
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${POLYPANEL_HOME:-$HOME/.local/share/polypanel}"
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

# ---------------------------------------------------------------- root = Dienst-Benutzer
# Als root gestartet: Installation und Server laufen automatisch unter einem eigenen
# Dienst-Benutzer. Nicht aus Bequemlichkeit - Satisfactory startet als root gar nicht,
# und ein Webserver als root ist ohnehin keine gute Idee.
if [ "$(id -u)" = "0" ] && [ -z "$SERVICE_USER" ] && [ "$CHECK_ONLY" = "0" ]; then
  if [ "$UNINSTALL" = "1" ]; then
    # beim Entfernen nur umschalten, wenn es den Benutzer wirklich gibt
    getent passwd "polypanel" >/dev/null 2>&1 && SERVICE_USER="polypanel"
  else
    SERVICE_USER="polypanel"
  fi
fi

# ---------------------------------------------------------------- Dienst-Benutzer
if [ -n "$SERVICE_USER" ]; then
  if [ "$(id -u)" != "0" ]; then
    echo "--user braucht root (Benutzer anlegen, Rechte setzen): sudo ./install.sh --user $SERVICE_USER"
    exit 1
  fi
  case "$SERVICE_USER" in
    *[!a-z0-9_-]*|"") echo "Ungueltiger Benutzername: $SERVICE_USER"; exit 1 ;;
  esac
  if [ "$UNINSTALL" = "0" ] && ! id "$SERVICE_USER" >/dev/null 2>&1; then
    useradd -m -s /bin/bash "$SERVICE_USER"
    echo "Benutzer $SERVICE_USER angelegt."
  fi
  SERVICE_UID="$(id -u "$SERVICE_USER")"
  HOME="$(getent passwd "$SERVICE_USER" | cut -d: -f6)"
  export HOME
  [ -n "${POLYPANEL_HOME:-}" ] || DEST="$HOME/.local/share/polypanel"
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
    en:title)              echo "Installing PolyPanel" ;;
    de:title)              echo "PolyPanel installieren" ;;
    en:python_missing)     echo "Python 3 not found (set PYTHON=/path/to/python3)" ;;
    de:python_missing)     echo "Python 3 nicht gefunden (PYTHON=/pfad/zu/python3 setzen)" ;;
    en:python_old)         echo "Error: Python 3.10 or newer required, found %s" ;;
    de:python_old)         echo "Fehler: Python 3.10 oder neuer noetig, gefunden %s" ;;
    en:present)            echo "${2:-}: present" ;;
    de:present)            echo "${2:-}: vorhanden" ;;
    en:missing_ask)        echo "${2:-} is missing. Install now? [y/N] " ;;
    de:missing_ask)        echo "${2:-} fehlt. Jetzt installieren? [j/N] " ;;
    en:auto_install)       echo "${2:-} missing - installing" ;;
    de:auto_install)       echo "${2:-} fehlt - wird installiert" ;;
    en:installed)          echo "${2:-} installed" ;;
    de:installed)          echo "${2:-} installiert" ;;
    en:install_failed)     echo "Installation of ${2:-} failed" ;;
    de:install_failed)     echo "Installation von ${2:-} fehlgeschlagen" ;;
    en:still_missing)      echo "${2:-} still missing - the server will not start" ;;
    de:still_missing)      echo "${2:-} fehlt weiterhin - der Server startet damit nicht" ;;
    en:no_pkgmgr)          echo "no package manager detected - please install manually: ${2:-}" ;;
    de:no_pkgmgr)          echo "keine Paketverwaltung erkannt - bitte von Hand installieren: ${2:-}" ;;
    en:no_sudo)            echo "sudo missing - please install as root: ${2:-}" ;;
    de:no_sudo)            echo "sudo fehlt - bitte als root installieren: ${2:-}" ;;
    en:multilib_label)     echo "32-bit libraries for SteamCMD" ;;
    de:multilib_label)     echo "32-Bit-Bibliotheken fuer SteamCMD" ;;
    en:multilib_ask)       echo "32-bit libraries for SteamCMD are missing. Install now? [y/N] " ;;
    de:multilib_ask)       echo "32-Bit-Bibliotheken fuer SteamCMD fehlen. Jetzt installieren? [j/N] " ;;
    en:multilib_ok)        echo "32-bit libraries (SteamCMD): present" ;;
    de:multilib_ok)        echo "32-Bit-Bibliotheken (SteamCMD): vorhanden" ;;
    en:multilib_failed)    echo "32-bit libraries are still missing - SteamCMD aborts with 'exit 127'. Install manually: ${2:-}" ;;
    de:multilib_failed)    echo "32-Bit-Bibliotheken fehlen weiterhin - SteamCMD bricht mit 'Exit 127' ab. Von Hand installieren: ${2:-}" ;;
    en:check_missing)      echo "${2:-} missing${3:+ (package: $3)}" ;;
    de:check_missing)      echo "${2:-} fehlt${3:+ (Paket: $3)}" ;;
    en:uninstall)          echo "PolyPanel entfernen" ;;
    de:uninstall)          echo "PolyPanel entfernen" ;;
    en:service_removed)    echo "service stopped and removed: ${2:-}" ;;
    en:service_removed_sys) echo "system service stopped and removed: ${2:-}" ;;
    de:service_removed)    echo "Dienst beendet und entfernt: ${2:-}" ;;
    de:service_removed_sys) echo "Systemdienst beendet und entfernt: ${2:-}" ;;
    en:steam_removed)    echo "removing SteamCMD folder ${2:-} ..." ;;
    de:steam_removed)    echo "entferne SteamCMD-Ordner ${2:-} ..." ;;
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
    en:copied)             echo "Program files: ${2:-}" ;;
    de:copied)             echo "Programmdateien: ${2:-}" ;;
    en:command)            echo "Command: ${2:-}" ;;
    de:command)            echo "Befehl: ${2:-}" ;;
    en:service_restarted)  echo "web service restarted (new code active)" ;;
    de:service_restarted)  echo "Web-Dienst neu gestartet (neuer Code aktiv)" ;;
    en:linked_usr_local)   echo "Command available as 'polypanel' (symlink in /usr/local/bin)" ;;
    de:linked_usr_local)   echo "Befehl 'polypanel' verfuegbar (Symlink in /usr/local/bin)" ;;
    en:path_hint)          echo "Note: ${2:-} is not in PATH - e.g. add to ~/.config/fish/config.fish:" ;;
    de:path_hint)          echo "Hinweis: ${2:-} ist nicht im PATH - z. B. in ~/.config/fish/config.fish ergaenzen:" ;;
    en:done)               echo "Done. Next steps:" ;;
    de:done)               echo "Fertig. Naechste Schritte:" ;;
    en:wizard_step)        echo "  polypanel web             open the web UI - create instances in the browser" ;;
    de:wizard_step)        echo "  polypanel web             Web-Oberflaeche oeffnen - Instanzen im Browser anlegen" ;;
    en:wizard_opt)         echo "  polypanel wizard          optional, console only: guided setup in the terminal" ;;
    de:wizard_opt)         echo "  polypanel wizard          optional, nur Konsole: gefuehrte Einrichtung im Terminal" ;;
    en:supervise_step)     echo "  polypanel supervise --all   watch all instances" ;;
    en:uninstall_step)     echo "  ./install.sh --uninstall   remove polypanel (instances and backups stay)" ;;
    de:uninstall_step)     echo "  ./install.sh --uninstall   polypanel entfernen (Instanzen und Backups bleiben)" ;;
    de:supervise_step)     echo "  polypanel supervise --all   alle Instanzen ueberwachen" ;;
    en:web)                echo "Web interface (after 'polypanel web'):" ;;
    de:web)                echo "Web interface (nach 'polypanel web'):" ;;
    en:net_note)           echo "only with: polypanel web --host 0.0.0.0" ;;
    de:net_note)           echo "nur mit: polypanel web --host 0.0.0.0" ;;
    en:token_hint)         echo "  token is also stored in ~/.config/polypanel/token - show it again with: polypanel url" ;;
    de:token_hint)         echo "  Token auch in ~/.config/polypanel/token - erneut anzeigen mit: polypanel url" ;;
    en:access_q)          echo "How should the web interface be reachable?  [1] client-side only (SSH tunnel)  [2] public via domain with HTTPS  [3] direct via IP and port (HTTP, NOT recommended)   [1] " ;;
    de:access_q)          echo "Wie soll die Oberflaeche erreichbar sein?  [1] nur Client-seitig (SSH-Tunnel)  [2] oeffentlich ueber Domain mit HTTPS  [3] direkt ueber IP und Port (HTTP, nicht empfohlen)   [1] " ;;
    en:access_domain_q)   echo "Domain (must point to this server): " ;;
    de:access_domain_q)   echo "Domain (muss auf diesen Server zeigen): " ;;
    en:access_tunnel)     echo "Access from another machine: ssh -N -L 8790:127.0.0.1:8790 $(id -un)@$MYIP" ;;
    de:access_tunnel)     echo "Zugriff von einem anderen Rechner: ssh -N -L 8790:127.0.0.1:8790 $(id -un)@$MYIP" ;;
    en:access_https)      echo "HTTPS einrichten mit: sudo polypanel proxy --write --cert" ;;
    de:access_https)      echo "HTTPS einrichten mit: sudo polypanel proxy --write --cert" ;;
    en:ip_warning_strong)  echo "WARNING: this makes the interface reachable from the internet WITHOUT encryption."; echo "         Whoever reads the token (Wi-Fi, proxy, hosting provider, browser history) can start,"; echo "         stop and delete servers and send console commands. Mode [1] or [2] avoids this." ;;
    de:ip_warning_strong)  echo "WARNUNG: Damit ist die Oberflaeche aus dem Internet erreichbar - UNVERSCHLUESSELT."; echo "         Wer den Token mitliest (WLAN, Proxy, Anbieter, Browser-Verlauf), kann Server starten,"; echo "         stoppen, loeschen und Konsolenbefehle absetzen. Modus [1] oder [2] vermeidet das." ;;
    en:ip_confirm)         echo "Really set it up this way?  [j/N] " ;;
    de:ip_confirm)         echo "Trotzdem so einrichten?  [j/N] " ;;
    en:ip_warning)         echo "Note: reachable over the network without HTTPS - the token protects the UI, traffic is unencrypted. Open port 8790 in the firewall." ;;
    de:ip_warning)         echo "Hinweis: im Netzwerk ohne HTTPS erreichbar - der Token schuetzt die Oberflaeche, die Uebertragung ist unverschluesselt. Port 8790 in der Firewall freigeben." ;;
    en:web_not_needed)     echo "No permanent service needed - the UI starts on demand: polypanel web" ;;
    de:web_not_needed)     echo "Kein Dauerdienst noetig - Oberflaeche startet bei Bedarf: polypanel web" ;;
    en:web_q)              echo "Start the web interface automatically (systemd service)? [y/N] " ;;
    de:web_q)              echo "Web-Oberflaeche automatisch starten (systemd-Dienst)? [j/N] " ;;
    en:web_installed_system) echo "Web interface runs as systemd system service (starts at boot): systemctl status polypanel-web" ;;
    de:web_installed_system) echo "Web-Oberflaeche laeuft als Systemdienst (startet beim Booten): systemctl status polypanel-web" ;;
    en:web_installed_user) echo "Web interface runs as ${2:-} - user service polypanel-web; check: su - ${2:-} -c 'systemctl --user status polypanel-web'" ;;
    de:web_installed_user) echo "Web-Oberflaeche laeuft als Benutzer ${2:-} - User-Dienst polypanel-web; pruefen: su - ${2:-} -c 'systemctl --user status polypanel-web'" ;;
    en:web_installed)      echo "Web interface runs as polypanel-web.service - check: systemctl --user status polypanel-web" ;;
    de:web_installed)      echo "Web-Oberflaeche laeuft als polypanel-web.service - pruefen: systemctl --user status polypanel-web" ;;
    en:web_failed)         echo "Could not enable the service - start manually with: polypanel web" ;;
    de:web_failed)         echo "Dienst konnte nicht aktiviert werden - manuell starten mit: polypanel web" ;;
    en:web_skipped)        echo "No service created - start the UI when needed with: polypanel web" ;;
    de:web_skipped)        echo "Kein Dienst angelegt - Oberflaeche bei Bedarf starten mit: polypanel web" ;;
    en:as_user)            echo "Running as root - installing as service user $SERVICE_USER (servers must not run as root)" ;;
    de:as_user)            echo "Als root gestartet - Installation und Server laufen als Dienst-Benutzer $SERVICE_USER" ;;
    en:svc_busy)           echo "An installation is running - web service not restarted (that would abort the download). Update takes effect after the next restart." ;;
    de:svc_busy)           echo "Eine Installation laeuft - Web-Dienst nicht neu gestartet (das wuerde den Download abbrechen). Der neue Stand greift nach dem naechsten Neustart." ;;
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
    xvfb:pacman) echo "xorg-server-xvfb" ;;
    xvfb:apt)    echo "xvfb" ;;
    xvfb:dnf)    echo "xorg-x11-server-Xvfb" ;;
    xvfb:zypper) echo "xvfb" ;;
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
  printf '  %s ' "$(t missing_ask "$label")"
  read -r answer || answer=""
  case "$answer" in
    j|J|y|Y|ja|Ja|yes|Yes)
      if install_pkg "$logical"; then say "$(t installed "$label")"; else warn "$(t install_failed "$label")"; fi ;;
    *) warn "$(t still_missing "$label")" ;;
  esac
}

# ---------------------------------------------------------------- Sprache speichern
save_lang() {
  mkdir -p "$HOME/.config/polypanel"
  "$PY" - "$LANG_SEL" <<'PYEOF'
import json, os, sys
path = os.path.expanduser("~/.config/polypanel/settings.json")
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
  for unit in "$HOME"/.config/systemd/user/polypanel-*.service; do
    [ -e "$unit" ] || continue
    name="$(basename "$unit")"
    systemctl --user disable --now "$name" >/dev/null 2>&1 || true
    rm -f "$unit"
    say "$(t service_removed "$name")"
  done
  systemctl --user daemon-reload >/dev/null 2>&1 || true
  # Installation als root legt einen Systemdienst an (/etc/systemd/system) - der muss hier auch weg
  SYS_UD="${PANEL_SYSTEMD_DIR:-/etc/systemd/system}"
  if [ "$(id -u)" = "0" ]; then
    for unit in "$SYS_UD"/polypanel-*.service; do
      [ -e "$unit" ] || continue
      uname="$(basename "$unit")"
      systemctl disable --now "$uname" >/dev/null 2>&1 || true
      rm -f "$unit"
      say "$(t service_removed_sys "$uname")"
    done
    [ -d "$SYS_UD" ] && systemctl daemon-reload >/dev/null 2>&1 || true
    # Symlink nur entfernen, wenn er auf unseren Launcher zeigt
    if [ -L "/usr/local/bin/polypanel" ] && [ "$(readlink "/usr/local/bin/polypanel")" = "$BIN/polypanel" ]; then
      rm -f "/usr/local/bin/polypanel"
    fi
  fi
  rm -f "$BIN/polypanel"
  rm -rf "$DEST"
  say "$(t removed)"
  # SteamCMD mitnehmen: mehrere GB, ohne das Panel nutzt es hier niemand mehr
  for _d in "$HOME/steamcmd" "$HOME/.steam" "$HOME/Steam" "$HOME/steam"; do
    if [ -d "$_d" ]; then
      printf '  %s ' "$(t steam_removed "$_d")"
      rm -rf "$_d" && echo ok
    fi
  done
  say "$(t kept)"
  say "  ~/.config/polypanel   ~/polypanel-instances   ~/polypanel-backups   ~/polypanel-snapshots   ~/.wine"
  exit 0
fi

t title
echo "-------------------"

if [ -n "$SERVICE_USER" ]; then
  say "$(t as_user)"
fi


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

# Xvfb wird ohne Rueckfrage mitinstalliert: der Name "virtueller Bildschirm" klingt fuer
# Anfaenger entbehrlich, ohne Xvfb startet der ARK-Ascended-Server unter Wine aber gar nicht.
if command -v Xvfb >/dev/null 2>&1; then
  say "$(t present "Xvfb")"
else
  MISSING=1
  if [ "$CHECK_ONLY" = "1" ]; then
    warn "$(t check_missing "Xvfb" "$(pkg_name xvfb)")"
  else
    say "$(t auto_install "Xvfb")"
    _root() { if [ "$(id -u)" = "0" ]; then "$@"; else sudo "$@"; fi; }
    case "$PKG_MGR" in
      apt)    _root apt-get update -qq; _root apt-get install -y "$(pkg_name xvfb)" ;;
      dnf)    _root dnf install -y "$(pkg_name xvfb)" ;;
      zypper) _root zypper --non-interactive install "$(pkg_name xvfb)" ;;
      pacman) _root pacman -S --needed --noconfirm "$(pkg_name xvfb)" ;;
      *)      warn "$(t no_pkgmgr "$(pkg_name xvfb)")" ;;
    esac
    if command -v Xvfb >/dev/null 2>&1; then
      say "$(t installed "Xvfb")"
    else
      warn "$(t still_missing "Xvfb")"
    fi
  fi
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

# ---------------------------------------------------------------- 32-Bit-Bibliotheken (SteamCMD)
# SteamCMD ist ein 32-bit-Programm. Fehlen die i386-Bibliotheken, bricht es mit "Exit 127" ab,
# bevor ueberhaupt ein Server installiert ist - deshalb richtet der Installer das selbst ein.
have_multilib() {
  for _p in /lib/ld-linux.so.2 /lib32/ld-linux.so.2 /lib/i386-linux-gnu/ld-linux.so.2 \
            /usr/lib32/ld-linux.so.2 /usr/lib/i386-linux-gnu/ld-linux.so.2; do
    [ -e "$_p" ] && return 0
  done
  return 1
}

multilib_pkgs() {
  case "$PKG_MGR" in
    apt)    echo "lib32gcc-s1 lib32stdc++6 libc6:i386" ;;
    dnf)    echo "glibc.i686 libstdc++.i686" ;;
    zypper) echo "glibc-32bit libstdc++6-32bit" ;;
    pacman) echo "lib32-glibc lib32-gcc-libs" ;;
    *)      echo "" ;;
  esac
}

install_multilib() {
  local pkgs; pkgs="$(multilib_pkgs)"
  [ -n "$pkgs" ] || { warn "$(t no_pkgmgr "$(t multilib_label)")"; return 1; }
  # als root direkt, sonst per sudo - nach dem Umschalten auf den Dienst-Benutzer
  # laeuft der Installer als root weiter und sudo ist evtl. gar nicht installiert
  _root() { if [ "$(id -u)" = "0" ]; then "$@"; else sudo "$@"; fi; }
  if [ "$(id -u)" != "0" ] && ! command -v sudo >/dev/null 2>&1; then
    warn "$(t no_sudo "$(t multilib_label)")"; return 1
  fi
  case "$PKG_MGR" in
    apt)
      _root dpkg --add-architecture i386 || true
      _root apt-get update -qq
      _root apt-get install -y $pkgs || _root apt-get install -y lib32gcc1 lib32stdc++6 libc6:i386
      ;;
    dnf)    _root dnf install -y $pkgs ;;
    zypper) _root zypper --non-interactive install $pkgs ;;
    pacman) _root pacman -S --needed --noconfirm $pkgs ;;
  esac
}

if have_multilib; then
  say "$(t multilib_ok)"
else
  MISSING=1
  if [ "$CHECK_ONLY" = "1" ]; then
    warn "$(t check_missing "$(t multilib_label)" "$(multilib_pkgs)")"
  else
    # ohne Rueckfrage: SteamCMD ist ein 32-Bit-Programm und bricht sonst mit "Exit 127" ab
    say "$(t auto_install "$(t multilib_label)")"
    install_multilib >/dev/null 2>&1 || true
    if have_multilib; then
      say "$(t installed "$(t multilib_label)")"
    else
      warn "$(t multilib_failed "$(multilib_pkgs)")"
    fi
  fi
fi

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
# Ohne Rueckfrage (--auto, Pipe) die gespeicherte Zugriffsart uebernehmen - sonst wuerde die
# Unit bei jedem Update ohne --host neu geschrieben und das Panel waere nur noch lokal erreichbar.
if [ ! -t 0 ] && [ -f "$HOME/.config/polypanel/settings.json" ]; then
  _gespeichert="$("$PY" - "$HOME/.config/polypanel/settings.json" <<'PYEOF'
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        daten = json.load(fh)
except (OSError, ValueError):
    daten = {}
print(str(daten.get("access", "") or ""))
PYEOF
)"
  ACCESS="$_gespeichert"
fi
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
path = os.path.expanduser("~/.config/polypanel/settings.json")
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
mkdir -p "$DEST" "$BIN" "$HOME/.config/polypanel"
cp -a "$SRC/polypanel" "$DEST/"
cp -a "$SRC/README.md" "$DEST/" 2>/dev/null || true
cp -a "$SRC/INSTALL.md" "$DEST/" 2>/dev/null || true
cp -a "$SRC/README.de.md" "$DEST/" 2>/dev/null || true
cp -a "$SRC/INSTALL.de.md" "$DEST/" 2>/dev/null || true
cp -a "$SRC"/CHANGELOG*.md "$DEST/" 2>/dev/null || true
# Lizenz mitkopieren: die Web-UI zeigt sie unter /license, und der Copyright-Hinweis
# muss beim Kunden mit dem Programm ausgeliefert werden.
cp -a "$SRC/LICENSE" "$DEST/" 2>/dev/null || true
find "$DEST" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
say "$(t copied "$DEST")"

# Installierten Stand festhalten (Commit), damit auch Aenderungen ohne Versionssprung ankommen
if command -v git >/dev/null 2>&1 && [ -d "$SRC/.git" ]; then
  SHA="$(git -C "$SRC" rev-parse --short HEAD 2>/dev/null || true)"
  VER="$(grep -m1 __version__ "$DEST/polypanel/__init__.py" 2>/dev/null | cut -d'"' -f2)"
  if [ -n "$SHA" ]; then
    printf '{"sha": "%s", "version": "%s", "written": "%s"}\n' "$SHA" "$VER" "$(date '+%F %T')" > "$DEST/polypanel/.build"
  else
    # Installation aus einem Archiv (kein .git): alten Stand nicht stehen lassen,
    # sonst meldet die Pruefung dauerhaft "neuer Stand verfuegbar"
    rm -f "$DEST/polypanel/.build"
  fi
fi

cat > "$BIN/polypanel" <<EOF
#!/bin/sh
# polypanel-Launcher (erzeugt von install.sh)
export PYTHONPATH="$DEST\${PYTHONPATH:+\$PYTHONPATH}"
# -P: aktuelles Verzeichnis nicht in sys.path - sonst importiert polypanel aus dem Quellordner
exec "$PY" -P -m polypanel "\$@"
EOF
chmod +x "$BIN/polypanel"
# bei --user gehoert alles dem Dienst-Benutzer, sonst kann er seine Configs nicht schreiben
if [ -n "$SERVICE_USER" ]; then
  chown -R "$SERVICE_USER":"$SERVICE_USER" "$DEST" "$HOME/.config/polypanel" "$BIN/polypanel" 2>/dev/null || true
fi
say "$(t command "$BIN/polypanel")"

case ":$PATH:" in
  *":$BIN:"*) ;;
  *)
    if [ "$(id -u)" = "0" ] && [ -d /usr/local/bin ] && [ -z "$SERVICE_USER" ]; then
      if ln -sf "$BIN/polypanel" /usr/local/bin/polypanel 2>/dev/null; then
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
t wizard_opt
t supervise_step
t uninstall_step

# ---------------------------------------------------------------- Web-Dienst
if [ -z "$WANT_WEB" ]; then
  if [ "$ACCESS" = "tunnel" ]; then
    # Client-seitig: die Oberflaeche wird bei Bedarf mit "polypanel web" gestartet, kein Dauerdienst noetig
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
    cat > "$UNIT_DIR/polypanel-web.service" <<EOF
[Unit]
Description=polypanel web interface
After=network-online.target

[Service]
Type=simple
WorkingDirectory=$DEST
Environment=PYTHONPATH=$DEST
ExecStart=/usr/bin/python3 -m polypanel web $WEBHOST --port 8790
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF
    chown -R "$SERVICE_USER":"$SERVICE_USER" "$DEST" "$HOME/.config/polypanel" "$BIN/polypanel" "$UNIT_DIR" 2>/dev/null || true
    loginctl enable-linger "$SERVICE_USER" >/dev/null 2>&1 || true
    if su - "$SERVICE_USER" -c "XDG_RUNTIME_DIR=/run/user/$SERVICE_UID systemctl --user daemon-reload && XDG_RUNTIME_DIR=/run/user/$SERVICE_UID systemctl --user enable --now polypanel-web.service" >/dev/null 2>&1; then
      say "$(t web_installed_user "$SERVICE_USER")"
    else
      warn "$(t web_failed)"
    fi
  elif [ "$(id -u)" = "0" ]; then
    # Systemdienst: startet beim Booten, kein Login und kein linger noetig
    UNIT="/etc/systemd/system/polypanel-web.service"
    cat > "$UNIT" <<EOF
[Unit]
Description=polypanel web interface
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$DEST
Environment=PYTHONPATH=$DEST
ExecStart=/usr/bin/python3 -m polypanel web $WEBHOST --port 8790
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    if systemctl daemon-reload 2>/dev/null && systemctl enable --now polypanel-web.service 2>/dev/null; then
      say "$(t web_installed_system)"
    else
      warn "$(t web_failed)"
    fi
  else
    UNIT_DIR="$HOME/.config/systemd/user"
    mkdir -p "$UNIT_DIR"
    cat > "$UNIT_DIR/polypanel-web.service" <<EOF
[Unit]
Description=polypanel web interface
After=network-online.target

[Service]
Type=simple
WorkingDirectory=$DEST
Environment=PYTHONPATH=$DEST
ExecStart=/usr/bin/python3 -m polypanel web $WEBHOST --port 8790
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF
    if systemctl --user daemon-reload 2>/dev/null && systemctl --user enable --now polypanel-web.service 2>/dev/null; then
      say "$(t web_installed)"
    else
      warn "$(t web_failed)"
    fi
  fi
else
  say "$(t web_skipped)"
fi


# laufenden Web-Dienst neu starten, damit der neue Code aktiv ist
_uid="${SERVICE_UID:-}"
# Laeuft gerade eine SteamCMD-Installation? Dann nicht neu starten - der Dienst wuerde
# den Download als Kindprozess mit abschiessen.
_laeuft_download=""
if [ -n "$SERVICE_USER" ]; then
  pgrep -u "$SERVICE_USER" -f steamcmd >/dev/null 2>&1 && _laeuft_download="ja"
else
  pgrep -u "$(id -u)" -f steamcmd >/dev/null 2>&1 && _laeuft_download="ja"
fi
if [ -n "$_laeuft_download" ]; then
  warn "$(t svc_busy)"
elif [ -n "$SERVICE_USER" ] && [ -n "$_uid" ]; then
  # Dienst laeuft als Dienst-Benutzer - dann aus dessen Sitzung neu starten
  su - "$SERVICE_USER" -c "XDG_RUNTIME_DIR=/run/user/$_uid systemctl --user restart polypanel-web" >/dev/null 2>&1 \
    && say "$(t service_restarted)"
elif systemctl is-active polypanel-web >/dev/null 2>&1; then
  systemctl restart polypanel-web >/dev/null 2>&1 && say "$(t service_restarted)"
elif systemctl --user is-active polypanel-web >/dev/null 2>&1; then
  systemctl --user restart polypanel-web >/dev/null 2>&1 && say "$(t service_restarted)"
fi

URL="$("$BIN/polypanel" url --quiet 2>/dev/null | head -1 || true)"
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
  say "HTTPS: sudo polypanel proxy --domain $DOMAIN --write --cert"
elif [ "$ACCESS" = "tunnel" ]; then
  echo
  say "$(t access_tunnel)"
fi

# Der Token wird beim Lesen der Adresse als root angelegt - Rechte danach noch einmal setzen,
# sonst kann der Dienst-Benutzer seine eigene Config nicht lesen (PermissionError beim Start).
if [ -n "$SERVICE_USER" ]; then
  # Das ganze Home gehoert dem Dienst-Benutzer: sonst scheitern Spiele, die eigene
  # Verzeichnisse anlegen wollen (7D2D bricht mit "Access to the path .local/share/7DaysToDie
  # is denied" ab, wenn .local als root entstanden ist).
  chown -R "$SERVICE_USER":"$SERVICE_USER" "$HOME" 2>/dev/null || true
fi

if [ "$RUN_WIZARD" = "1" ]; then
  echo
  exec "$BIN/polypanel" wizard
fi
