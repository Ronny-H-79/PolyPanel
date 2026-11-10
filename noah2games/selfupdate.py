"""Selbst-Update: pruefen, ob es eine neue noah2games-Version gibt, und einspielen.

Es wird kein git vorausgesetzt - noah2games laedt das Quellarchiv von GitHub und ersetzt
nur das Paketverzeichnis. Einstellungen, Instanzen und Backups bleiben unberuehrt.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.request

REPO = "Ronny-H-79/Noah2Games"
BRANCH = "main"
API_COMMIT = "https://api.github.com/repos/%s/commits/%s" % (REPO, BRANCH)
RAW_INIT = "https://raw.githubusercontent.com/%s/%s/noah2games/__init__.py" % (REPO, BRANCH)
CONTENTS = "https://api.github.com/repos/%s/contents/noah2games/__init__.py?ref=%s" % (REPO, BRANCH)
TARBALL = "https://api.github.com/repos/%s/tarball/%s" % (REPO, BRANCH)


def package_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def installed_version() -> str:
    try:
        from . import __version__
        return __version__
    except Exception:  # noqa: BLE001
        return "?"


def _tuple(version: str) -> tuple:
    parts = []
    for piece in (version or "").split("."):
        num = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(num) if num else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def _parse_version(text: str) -> str:
    for line in text.splitlines():
        if line.strip().startswith("__version__"):
            return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def _get(url: str, timeout: int = 10) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "noah2games-selfupdate",
                                               "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


CACHE = os.path.expanduser("~/.config/noah2games/cache/selfupdate.json")
CACHE_TTL = 600          # 10 Minuten: GitHub erlaubt ohne Token nur 60 Anfragen/Stunde


def _cache_read() -> dict:
    try:
        with open(CACHE, encoding="utf-8") as fh:
            data = json.load(fh)
        if time.time() - data.get("_t", 0) < CACHE_TTL:
            return data
    except (OSError, ValueError):
        pass
    return {}


def _cache_write(info: dict) -> None:
    try:
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        payload = dict(info)
        payload["_t"] = time.time()
        with open(CACHE, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
    except OSError:
        pass


BUILD_FILE = os.path.join(package_dir(), ".build")


def remote_commit(timeout: int = 10) -> str:
    """Aktueller Commit auf GitHub (kurz).

    Zuerst `git ls-remote` - das unterliegt nicht dem API-Limit von 60 Anfragen/Stunde.
    """
    try:
        out = subprocess.run(
            ["git", "ls-remote", "https://github.com/%s.git" % REPO, "refs/heads/%s" % BRANCH],
            capture_output=True, text=True, timeout=timeout,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.split()[0][:7]
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        return json.loads(_get(API_COMMIT, timeout).decode())["sha"][:7]
    except Exception:  # noqa: BLE001
        return ""


def local_build() -> dict:
    """Welcher Commit liegt hier installiert? (von install.sh oder apply() geschrieben)"""
    try:
        with open(BUILD_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def write_build(sha: str, version: str) -> None:
    try:
        with open(BUILD_FILE, "w", encoding="utf-8") as fh:
            json.dump({"sha": sha, "version": version, "written": time.strftime("%F %T")}, fh)
    except OSError:
        pass


def check(timeout: int = 10, force: bool = False) -> dict:
    """Vergleicht die installierte Version mit der auf GitHub (10 Minuten gecacht)."""
    local = installed_version()
    if not force:
        cached = _cache_read()
        if cached and cached.get("installed") == local:
            cached.pop("_t", None)
            return cached
    remote = ""
    try:
        # API liefert immer den aktuellen Stand (raw.githubusercontent.com cached bis zu 5 Minuten)
        import base64
        data = json.loads(_get(CONTENTS, timeout).decode("utf-8"))
        remote = _parse_version(base64.b64decode(data.get("content", "")).decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001
        try:
            remote = _parse_version(_get(RAW_INIT, timeout).decode("utf-8", "replace"))
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": "%s: %s" % (exc.__class__.__name__, exc),
                    "installed": local, "available": "", "update": False}
    newer = bool(remote) and _tuple(remote) > _tuple(local)
    local_sha = local_build().get("sha", "")
    commit = remote_commit(timeout)
    changed = bool(commit and local_sha and commit != local_sha)
    info = {"ok": True, "installed": local, "available": remote, "update": newer or changed,
            "commit": commit, "local_commit": local_sha,
            "url": "https://github.com/%s" % REPO}
    _cache_write(info)
    return info


CHANGELOG = "https://api.github.com/repos/%s/contents/CHANGELOG.md?ref=%s" % (REPO, BRANCH)


def _local_changelog(name: str) -> str:
    """Changelog aus der eigenen Installation lesen (kein Netz noetig)."""
    for base in (package_dir(), os.path.dirname(package_dir())):
        path = os.path.join(base, name)
        try:
            with open(path, encoding="utf-8") as fh:
                return fh.read()
        except OSError:
            continue
    return ""


def _changelog_cache(name: str) -> str:
    path = os.path.expanduser("~/.config/noah2games/cache/%s" % name)
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def _store_changelog(name: str, text: str) -> None:
    try:
        path = os.path.expanduser("~/.config/noah2games/cache/%s" % name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    except OSError:
        pass


def changelog(lang: str = "de", timeout: int = 10) -> dict:
    """Komplettes Changelog in der gewuenschten Sprache - lokal zuerst, sonst GitHub."""
    import base64
    name = "CHANGELOG.en.md" if (lang or "").lower().startswith("en") else "CHANGELOG.md"
    local = _local_changelog(name) or _changelog_cache(name)
    # Veraltet? Wenn die installierte Version im Text fehlt, neu holen.
    if local and installed_version() and ("[%s]" % installed_version()) not in local:
        try:
            fresh = _get("https://raw.githubusercontent.com/%s/%s/%s" % (REPO, BRANCH, name),
                         timeout).decode("utf-8", "replace")
            if fresh:
                _store_changelog(name, fresh)
                local = fresh
        except Exception:  # noqa: BLE001
            pass
    if local:
        return {"ok": True, "lang": lang, "file": name, "text": local,
                "url": "https://github.com/%s/blob/%s/%s" % (REPO, BRANCH, name)}

    url = "https://api.github.com/repos/%s/contents/%s?ref=%s" % (REPO, name, BRANCH)
    try:
        data = json.loads(_get(url, timeout).decode("utf-8"))
        text = base64.b64decode(data.get("content", "")).decode("utf-8", "replace")
        _store_changelog(name, text)
        return {"ok": True, "lang": lang, "file": name, "text": text,
                "url": "https://github.com/%s/blob/%s/%s" % (REPO, BRANCH, name)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": "%s: %s" % (exc.__class__.__name__, exc), "text": ""}


def notes(version: str = "", timeout: int = 10) -> dict:
    """Aenderungen einer Version aus CHANGELOG.md holen (lokal zuerst)."""
    import base64
    text = _local_changelog("CHANGELOG.md") or _changelog_cache("CHANGELOG.md")
    if not text:
        try:
            data = json.loads(_get(CHANGELOG, timeout).decode("utf-8"))
            text = base64.b64decode(data.get("content", "")).decode("utf-8", "replace")
            _store_changelog("CHANGELOG.md", text)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": "%s: %s" % (exc.__class__.__name__, exc), "text": ""}

    version = (version or installed_version()).lstrip("v")
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("## ") and ("[%s]" % version) in line:
            start = i
            break
    if start is None:
        return {"ok": True, "version": version, "text": ""}

    out = []
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        out.append(line)
    body = "\n".join(out).strip()
    body = "\n".join(l for l in body.splitlines() if not l.startswith("### "))
    return {"ok": True, "version": version, "text": body}


def _fetch_tarball(timeout: int = 60, attempts: int = 3) -> bytes:
    """Archiv holen - mit Wiederholung und zweiter Quelle (codeload statt API).

    Die API leitet auf codeload.github.com um; wenn ein Zwischennetz dort hakt
    (504), klappt der zweite Weg oft sofort.
    """
    # codeload zuerst: liefert das Archiv direkt, die API leitet nur dorthin um und
    # antwortet derzeit sporadisch mit 503/504
    # nach Commit laden, nicht nach Branch: codeload liefert fuer "main" minutenlang einen
    # veralteten Stand aus dem Cache - dann wuerde ein Update stillschweigend nichts aendern
    sha = remote_commit(timeout)
    urls = []
    if sha:
        urls.append("https://codeload.github.com/%s/tar.gz/%s" % (REPO, sha))
    urls.append("https://codeload.github.com/%s/tar.gz/refs/heads/%s" % (REPO, BRANCH))
    urls.append(TARBALL)
    last = None
    for attempt in range(attempts):
        for url in urls:
            try:
                data = _get(url, timeout)
                if data:
                    return data
            except Exception as exc:  # noqa: BLE001
                last = exc
        if attempt + 1 < attempts:
            time.sleep(2 * (attempt + 1))
    raise last or OSError("Download fehlgeschlagen")


def apply(target: str = "", timeout: int = 60) -> dict:
    """Neue Version herunterladen und das Paketverzeichnis ersetzen."""
    target = target or package_dir()
    work = tempfile.mkdtemp(prefix="noah2games-update-")
    try:
        archive = os.path.join(work, "src.tar.gz")
        with open(archive, "wb") as fh:
            fh.write(_fetch_tarball(timeout))

        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(work, filter="data")

        roots = [d for d in os.listdir(work) if os.path.isdir(os.path.join(work, d))]
        if not roots:
            return {"ok": False, "error": "Archiv enthaelt kein Verzeichnis"}
        new_pkg = os.path.join(work, roots[0], "noah2games")
        if not os.path.isdir(new_pkg):
            return {"ok": False, "error": "Paketordner noah2games/ fehlt im Archiv"}

        # Changelog mitziehen, sonst zeigt die Oberflaeche den Stand der Erstinstallation
        root = os.path.join(work, roots[0])
        for extra in ("CHANGELOG.md", "CHANGELOG.en.md"):
            src = os.path.join(root, extra)
            if os.path.isfile(src):
                try:
                    shutil.copy2(src, os.path.join(os.path.dirname(target.rstrip("/")), extra))
                except OSError:
                    pass

        old_version = installed_version()
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = "%s.bak-%s" % (target.rstrip("/"), stamp)

        # Erst vollstaendig daneben aufbauen, dann per rename tauschen: das laufende
        # Verzeichnis verschwindet nie, und ein Abbruch laesst den alten Stand stehen.
        parent = os.path.dirname(target.rstrip("/"))
        staging = os.path.join(parent, ".noah2games-neu-%d" % os.getpid())
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(new_pkg, staging)
        shutil.rmtree(os.path.join(staging, "__pycache__"), ignore_errors=True)

        moved_old = False
        if os.path.isdir(target):
            os.replace(target, backup)
            moved_old = True
        try:
            os.replace(staging, target)
        except OSError:
            if moved_old and not os.path.isdir(target):
                os.replace(backup, target)      # zurueckrollen
            raise
        prune_backups(target, keep=2)

        new_version = ""
        try:
            with open(os.path.join(target, "__init__.py"), encoding="utf-8") as fh:
                new_version = _parse_version(fh.read())
        except OSError:
            pass
        write_build(remote_commit(), new_version)
        return {"ok": True, "from": old_version, "to": new_version, "backup": backup}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": "%s: %s" % (exc.__class__.__name__, exc)}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def prune_backups(target: str, keep: int = 2) -> list[str]:
    """Alte Sicherungen des Paketverzeichnisses entfernen, die letzten `keep` bleiben."""
    target = target.rstrip("/")
    parent, base = os.path.dirname(target), os.path.basename(target)
    prefix = base + ".bak-"
    try:
        names = sorted(n for n in os.listdir(parent) if n.startswith(prefix))
    except OSError:
        return []
    removed = []
    for name in names[:-keep] if keep else names:
        path = os.path.join(parent, name)
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
            removed.append(path)
    return removed


def _session_env() -> dict:
    """Umgebung fuer `systemctl --user` - auch ohne angemeldete Sitzung (su, ssh, cron)."""
    env = dict(os.environ)
    runtime = env.get("XDG_RUNTIME_DIR") or "/run/user/%d" % os.getuid()
    if os.path.isdir(runtime):
        env["XDG_RUNTIME_DIR"] = runtime
        bus = os.path.join(runtime, "bus")
        if not env.get("DBUS_SESSION_BUS_ADDRESS") and os.path.exists(bus):
            env["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=%s" % bus
    return env


def restart_service() -> dict:
    """Web-Dienst und Supervisor neu starten, damit der neue Code laeuft."""
    env = _session_env()
    done = []
    for service in ("noah2games-web", "noah2games-supervise"):
        for cmd, kind in ((["systemctl", "restart", service], "system"),
                          (["systemctl", "--user", "restart", service], "user")):
            try:
                res = subprocess.run(cmd, capture_output=True, timeout=30, env=env)
                if res.returncode == 0:
                    done.append("%s (%s)" % (service, kind))
                    break
            except (OSError, subprocess.SubprocessError):
                continue
    if done:
        return {"ok": True, "scope": ", ".join(done)}
    return {"ok": False, "error": "kein noah2games-web/noah2games-supervise-Dienst gefunden"}
