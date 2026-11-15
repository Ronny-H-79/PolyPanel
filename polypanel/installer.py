"""Installation von SteamCMD und Serverdateien (auch vom Installer genutzt)."""
from __future__ import annotations

import json
import os
import re
import signal
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.request
import zipfile

from .instance import Instance

STEAMCMD_DIR = os.path.expanduser("~/steamcmd")
STEAMCMD_URL = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"
APP_ID = "2430930"  # Vorgabe (ARK); je Instanz entscheidet das Spielprofil


def steamcmd_path() -> str | None:
    """Pfad zu steamcmd.sh - erst im Standardordner, dann im PATH."""
    local = os.path.join(STEAMCMD_DIR, "steamcmd.sh")
    if os.path.exists(local):
        return local
    return shutil.which("steamcmd")


def ensure_steamcmd(log=print) -> str:
    """SteamCMD herunterladen, falls nicht vorhanden. Gibt den Pfad zurueck."""
    found = steamcmd_path()
    if found:
        return found
    log("SteamCMD nicht gefunden - lade nach %s" % STEAMCMD_DIR)
    os.makedirs(STEAMCMD_DIR, exist_ok=True)
    archive = os.path.join(STEAMCMD_DIR, "steamcmd_linux.tar.gz")
    urllib.request.urlretrieve(STEAMCMD_URL, archive)
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(STEAMCMD_DIR)
    os.unlink(archive)
    target = os.path.join(STEAMCMD_DIR, "steamcmd.sh")
    if not os.path.exists(target):
        raise RuntimeError("SteamCMD-Entpacken fehlgeschlagen")
    os.chmod(target, 0o755)
    log("SteamCMD bereit: %s" % target)
    return target


ASA_APP = "2430930"
# Spiele ohne Linux-Server: SteamCMD muss den Windows-Zweig laden.
WINDOWS_ONLY_APPS = {ASA_APP, "3809400", "530870"}
# ARK: Survival Ascended, StarRupture, Empyrion: Galactic Survival


def _plattform_flagge(app_id: str) -> list[str]:
    """Spiele ohne Linux-Server: SteamCMD muss den Windows-Zweig laden.

    Ohne diesen Schalter endet die Installation mit "Failed to install app ... (Invalid platform)".
    """
    if str(app_id) in WINDOWS_ONLY_APPS:
        return ["""+@sSteamCmdForcePlatformType windows"""]
    return []


def _steamcmd_bereit(cmd: str, log=print) -> bool:
    """SteamCMD vor dem ersten Zugriff aktualisieren (sonst "Missing configuration").

    Der Client laedt sich beim Aufruf selbst nach; bricht das ab, ist das Verzeichnis
    halbfertig und jede Installation scheitert. Dann wird der Client neu geholt.
    """
    try:
        r = subprocess.run([cmd, "+quit"], cwd=os.path.dirname(cmd),
                           capture_output=True, text=True, timeout=900)
        if r.returncode == 0:
            return True
        log("SteamCMD-Selbsttest fehlgeschlagen (exit %s) - Client wird neu geladen" % r.returncode)
    except (OSError, subprocess.SubprocessError) as exc:
        log("SteamCMD-Selbsttest nicht moeglich (%s) - Client wird neu geladen" % exc)
    shutil.rmtree(STEAMCMD_DIR, ignore_errors=True)
    return bool(ensure_steamcmd(log=log))


ACTIVE: dict[str, "subprocess.Popen[bytes]"] = {}


def cancel(name: str) -> dict[str, object]:
    """Laufende Installation abbrechen: SteamCMD-Prozessgruppe beenden."""
    proc = ACTIVE.get(name)
    if proc is None:
        return {"ok": False, "error": "keine laufende Installation"}
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except OSError:
        try:
            proc.terminate()
        except OSError:
            pass
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except OSError:
            pass
    ACTIVE.pop(name, None)
    return {"ok": True}


_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07")


def pump_output(stream, emit) -> None:
    """Zeilen aus der SteamCMD-Ausgabe ziehen - auch solche, die nur mit \\r enden.

    SteamCMD meldet Fortschritt mit Wagenruecklauf ohne Zeilenumbruch. Wer zeilenweise
    liest, bekommt deshalb waehrend des gesamten Downloads nichts zu sehen. Hier wird
    blockweise gelesen und an \\r und \\n getrennt, jeder Teil sofort gemeldet.
    """
    pending = ""
    while True:
        chunk = stream.read1(4096)
        if not chunk:
            break
        text = pending + chunk.decode("utf-8", "replace")
        parts = re.split(r"[\r\n]+", text)
        pending = parts.pop()
        for part in parts:
            part = _ANSI.sub("", part).strip()
            if part:
                emit(part)
    rest = _ANSI.sub("", pending).strip()
    if rest:
        emit(rest)


def install_server(inst: Instance, log=None) -> dict:
    """Serverdateien ueber SteamCMD holen; Ausgabe landet in <dir>/.install.log."""
    os.makedirs(inst.directory, exist_ok=True)
    log_path = os.path.join(inst.directory, ".install.log")
    extra = log or (lambda _msg: None)

    with open(log_path, "w", buffering=1) as fh:
        def emit(text: str) -> None:
            text = _ANSI.sub("", str(text)).rstrip()
            if not text:
                return
            fh.write(text + "\n")
            fh.flush()
            extra(text)

        emit("Installation gestartet %s" % time.strftime("%F %T"))
        cmd = ensure_steamcmd(log=emit)
        argv = ([cmd] + _plattform_flagge(inst.profile.server_app_id) +
                ["+force_install_dir", inst.directory, "+login", "anonymous",
                 "+app_update", inst.profile.server_app_id, "validate", "+quit"])
        _steamcmd_bereit(cmd, log=emit)
        emit("steamcmd %s" % " ".join(argv[1:]))
        proc = subprocess.Popen(argv, cwd=os.path.dirname(cmd), start_new_session=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        ACTIVE[inst.name] = proc
        pump_output(proc.stdout, emit)
        proc.wait()
        if proc.returncode != 0:
            try:
                with open(log_path, encoding="utf-8", errors="replace") as lf:
                    letzte = lf.read()[-4000:]
            except OSError:
                letzte = ""
            if "Missing configuration" in letzte or "Failed to install app" in letzte:
                emit("SteamCMD meldet eine defekte Konfiguration - Client wird neu geladen und der Versuch wiederholt")
                shutil.rmtree(STEAMCMD_DIR, ignore_errors=True)
                cmd = ensure_steamcmd(log=emit)
                _steamcmd_bereit(cmd, log=emit)
                argv[0] = cmd
                emit("steamcmd %s" % " ".join(argv[1:]))
                proc = subprocess.Popen(argv, cwd=os.path.dirname(cmd), start_new_session=True,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                ACTIVE[inst.name] = proc
                pump_output(proc.stdout, emit)
                proc.wait()
        ACTIVE.pop(inst.name, None)
        emit("Installation beendet (exit %s)" % proc.returncode)

    if proc.returncode == 0:
        # Nachbereitung (z. B. Wine/.NET fuer Space Engineers) braucht ein EIGENES Log-Handle:
        # der with-Block oben hat fh schon geschlossen, `emit` wuerde mit
        # "I/O operation on closed file" abbrechen - und die Fehlermeldung gleich mit.
        try:
            with open(log_path, "a", buffering=1) as fh2:
                def nach(text: str) -> None:
                    sauber = _ANSI.sub("", str(text)).rstrip()
                    if not sauber:
                        return
                    fh2.write("Laufzeit: %s\n" % sauber)
                    fh2.flush()
                try:
                    inst.profile.post_install(inst, log=nach)
                except Exception as exc:                # noqa: BLE001 - Installation bleibt gueltig
                    nach("Nachbereitung fehlgeschlagen: %s" % exc)

                # AsaApi gehoert bei ARK zum Standard: ohne die API gibt es keine Plugins im
                # Spiel. Ein Fehlschlag darf die Server-Installation nicht kippen - dann
                # bleibt der Knopf "API" in der Oberflaeche als Nachhol-Weg.
                if inst.game == "ark":
                    def api_log(text: str) -> None:
                        sauber = _ANSI.sub("", str(text)).rstrip()
                        if sauber:
                            fh2.write("AsaApi: %s\n" % sauber)
                            fh2.flush()

                    api_log("wird eingerichtet")
                    try:
                        api = install_asaapi(inst, log=api_log)
                        if api.get("ok"):
                            inst.asaapi = True
                            from . import registry
                            registry.save(inst)
                            api_log("AsaApi %s aktiv - Start ueber AsaApiLoader.exe"
                                    % api.get("tag", ""))
                        else:
                            api_log("nicht installiert (%s) - im Panel den Knopf 'API' nutzen"
                                    % api.get("error", "?"))
                    except Exception as exc:            # noqa: BLE001 - Installation bleibt gueltig
                        api_log("Installation fehlgeschlagen: %s" % exc)
        except OSError:
            pass

    return {"ok": proc.returncode == 0, "log": log_path, "exit": proc.returncode}


# --------------------------------------------------------- AsaApi (Plugins im Spiel)
ASAAPI_REPO = "ArkServerApi/AsaApi"
ASAAPI_API = "https://api.github.com/repos/%s/releases/latest" % ASAAPI_REPO
WIN64_REL = os.path.join("ShooterGame", "Binaries", "Win64")
_UA = {"User-Agent": "PolyPanel"}


def asaapi_tag(inst: Instance) -> str:
    """Installierte AsaApi-Version (aus ArkApi/.installed-tag), sonst leer."""
    if inst.game != "ark":
        return ""
    try:
        with open(os.path.join(inst.directory, WIN64_REL, "ArkApi", ".installed-tag"),
                  encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def asaapi_latest(timeout: int = 20) -> dict:
    """Neuestes AsaApi-Release von GitHub holen: {tag, zip, published}."""
    req = urllib.request.Request(ASAAPI_API, headers=dict(_UA, Accept="application/vnd.github+json"))
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        data = json.loads(fh.read().decode("utf-8", "replace"))
    tag = str(data.get("tag_name") or "").strip()
    zips = [str(a.get("browser_download_url") or "") for a in data.get("assets") or []
            if str(a.get("name") or "").lower().endswith(".zip")]
    if not tag or not zips:
        raise RuntimeError("Release ohne ZIP-Datei")
    return {"tag": tag, "zip": zips[0], "published": str(data.get("published_at") or "")}


def _place(src: str, dst: str) -> None:
    """Datei ersetzen, auch wenn das Ziel einem anderen Benutzer gehoert.

    Liegt eine alte Installation als root im Verzeichnis, scheitert `copy2` mit EACCES.
    Loeschen darf der Dienstbenutzer trotzdem (es gilt das Verzeichnisrecht) - also
    entfernen und neu schreiben.
    """
    try:
        shutil.copy2(src, dst)
        return
    except PermissionError:
        pass
    os.unlink(dst)
    shutil.copy2(src, dst)


_ASAAPI_CHECK: dict[str, tuple[float, dict]] = {}


def asaapi_update(inst: Instance, force: bool = False, ttl: int = 1800) -> dict:
    """Vergleicht die installierte AsaApi-Version mit dem neuesten Release.

    GitHub erlaubt nur 60 API-Anfragen pro Stunde - deshalb wird das Ergebnis pro
    Instanz `ttl` Sekunden (Standard 30 Minuten) zwischengespeichert.
    """
    tag = asaapi_tag(inst)
    if not tag:
        return {"installed": "", "available": "", "update": False}
    now = time.time()
    cached = _ASAAPI_CHECK.get(inst.name)
    if cached and not force and now - cached[0] < ttl:
        latest = cached[1]
    else:
        try:
            latest = asaapi_latest()
        except Exception:  # noqa: BLE001 - kein Netz ist kein Fehler
            return {"installed": tag, "available": "", "update": False}
        _ASAAPI_CHECK[inst.name] = (now, latest)

    def _num(wert: str) -> tuple:
        return tuple(int(x) for x in re.findall(r"\d+", str(wert))[:3])

    neuer = bool(latest.get("tag")) and _num(latest["tag"]) > _num(tag)
    return {"installed": tag, "available": latest.get("tag", ""), "update": neuer}


def install_asaapi(inst: Instance, log=None) -> dict:
    """AsaApi samt Plugins im Spiel installieren (komplettes Release-Archiv).

    Es reicht **nicht**, nur `ArkApi/` und `AsaApiLoader.exe` zu kopieren: an der
    ZIP-Wurzel liegen `config.json`, `msdia140.dll`, `libssl-3-x64.dll` und
    `libcrypto-3-x64.dll`. Fehlt `config.json`, wirft AsaApi in der Initialisierung eine
    C++-Exception (0xe06d7363) und der Server startet nie - genau das Fehlerbild, das
    "LoaderFailed, Reason: UnknownLoaderResult" im Konsolenlog erzeugt.

    Vorhandene Plugins (`ArkApi/Plugins`) und der Offsets-Cache (`ArkApi/Cache`)
    bleiben unangetastet. Ausgabe landet in `<verzeichnis>/.asaapi.log`.
    """
    win64 = os.path.join(inst.directory, WIN64_REL)
    server = os.path.join(win64, "ArkAscendedServer.exe")
    log_path = os.path.join(inst.directory, ".asaapi.log")
    extra = log or (lambda _msg: None)

    def emit(text: str) -> None:
        text = _ANSI.sub("", str(text)).rstrip()
        if text:
            fh.write(text + "\n")
            fh.flush()
            extra(text)

    with open(log_path, "w", buffering=1) as fh:
        emit("AsaApi-Installation gestartet %s" % time.strftime("%F %T"))
        if inst.game != "ark":
            emit("AsaApi gibt es nur fuer ARK: Survival Ascended (%s)" % inst.game)
            return {"ok": False, "error": "kein ARK-Server", "log": log_path}
        if not os.path.exists(server):
            emit("Server-exe fehlt (%s) - erst den Server installieren" % server)
            return {"ok": False, "error": "Server-exe fehlt", "log": log_path}
        try:
            rel = asaapi_latest()
        except Exception as exc:  # noqa: BLE001 - Netzfehler sichtbar machen
            emit("Release-Abfrage fehlgeschlagen: %s" % exc)
            return {"ok": False, "error": "Release-Abfrage fehlgeschlagen", "log": log_path}

        emit("Neuestes Release: %s (%s)" % (rel["tag"], os.path.basename(rel["zip"])))
        tmp = tempfile.mkdtemp(prefix="asaapi-")
        try:
            archive = os.path.join(tmp, "asaapi.zip")
            emit("Lade %s" % rel["zip"])
            req = urllib.request.Request(rel["zip"], headers=dict(_UA))
            with urllib.request.urlopen(req, timeout=180) as src, open(archive, "wb") as dst:
                shutil.copyfileobj(src, dst)
            unpack = os.path.join(tmp, "x")
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(unpack)

            if not (os.path.exists(os.path.join(unpack, "ArkApi", "AsaApi.dll"))
                    and os.path.exists(os.path.join(unpack, "AsaApiLoader.exe"))):
                emit("Archiv unvollstaendig (ArkApi/AsaApi.dll oder AsaApiLoader.exe fehlt)")
                return {"ok": False, "error": "Archiv unvollstaendig", "log": log_path}

            for relpath in ("ArkApi/AsaApi.dll", "AsaApiLoader.exe"):
                ziel = os.path.join(win64, relpath.replace("/", os.sep))
                if os.path.exists(ziel):
                    try:
                        shutil.copy2(ziel, ziel + ".bak-asaapi")
                    except PermissionError:
                        pass   # Backup ist nice-to-have, kein Grund zum Abbruch

            os.makedirs(os.path.join(win64, "ArkApi", "Plugins"), exist_ok=True)
            os.makedirs(os.path.join(win64, "ArkApi", "Cache"), exist_ok=True)
            keep = (os.path.join("ArkApi", "Plugins"), os.path.join("ArkApi", "Cache"))
            copied = kept = 0
            for root, _dirs, files in os.walk(unpack):
                relroot = os.path.relpath(root, unpack)
                relroot = "" if relroot == "." else relroot
                for name in files:
                    relpath = os.path.join(relroot, name) if relroot else name
                    if relpath.startswith(keep) and os.path.exists(os.path.join(win64, relpath)):
                        kept += 1
                        continue
                    ziel = os.path.join(win64, relpath)
                    os.makedirs(os.path.dirname(ziel), exist_ok=True)
                    _place(os.path.join(root, name), ziel)
                    copied += 1
            emit("%d Dateien uebernommen, %d vorhandene geschuetzt (Plugins/Cache)"
                 % (copied, kept))

            with open(os.path.join(win64, "ArkApi", ".installed-tag"), "w", encoding="utf-8") as tf:
                tf.write(rel["tag"] + "\n")
            emit("AsaApi %s installiert - Start erfolgt ueber AsaApiLoader.exe" % rel["tag"])
            if not os.path.exists(os.path.join(win64, "config.json")):
                emit("Warnung: config.json fehlt weiterhin - AsaApi laedt nicht")
            return {"ok": True, "tag": rel["tag"], "log": log_path,
                    "dateien": copied, "geschuetzt": kept}
        except Exception as exc:  # noqa: BLE001 - Download/Entpacken sichtbar machen
            emit("Installation fehlgeschlagen: %s" % exc)
            return {"ok": False, "error": str(exc), "log": log_path}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
