"""Vollstaendige Instanz-Snapshots (Serverdateien + Mods + Config) fuer Rollback nach Updates.

Ein Welt-Backup schuetzt nur Daten. Wenn ein ARK-Update die Installation zerschiest,
hilft nur eine Kopie der Programmdateien - SteamCMD liefert immer die neue Version.
"""
from __future__ import annotations

import os
import shutil
import time

from .instance import Instance
from . import runner

BASE = os.path.expanduser("~/polypanel-snapshots")
IGNORE = shutil.ignore_patterns("Logs", ".runtime", ".trash", "Crashes", "*.log",
                                "*.sock", ".PolyPanel-*", "steamapps/downloading")


def _dir(inst: Instance) -> str:
    path = os.path.join(BASE, inst.name)
    os.makedirs(path, exist_ok=True)
    return path


def create(inst: Instance, label: str = "snapshot") -> dict:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    name = "%s_%s" % (label, stamp)
    target = os.path.join(_dir(inst), name)
    # gleiche Sekunde (zwei Aufgaben gleichzeitig) darf nicht kollidieren
    suffix = 2
    while os.path.exists(target):
        name = "%s_%s-%d" % (label, stamp, suffix)
        target = os.path.join(_dir(inst), name)
        suffix += 1
    src = inst.directory
    if not os.path.isdir(src):
        raise RuntimeError("Instanzverzeichnis fehlt: %s" % src)
    shutil.copytree(src, target, ignore=IGNORE, symlinks=True)
    size = 0
    for root, _dirs, files in os.walk(target):
        for f in files:
            try:
                size += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return {"name": name, "path": target, "size_gb": round(size / (1024 ** 3), 2),
            "created": time.strftime("%Y-%m-%d %H:%M:%S")}


def listing(inst: Instance) -> list[dict]:
    out: list[dict] = []
    folder = _dir(inst)
    for name in sorted(os.listdir(folder), reverse=True):
        path = os.path.join(folder, name)
        if not os.path.isdir(path):
            continue
        size = 0
        for root, _dirs, files in os.walk(path):
            for f in files:
                try:
                    size += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
        out.append({"name": name, "path": path,
                    "size_gb": round(size / (1024 ** 3), 2),
                    "mtime": time.strftime("%Y-%m-%d %H:%M",
                                           time.localtime(os.path.getmtime(path)))})
    return out


def restore(inst: Instance, name: str) -> str:
    """Aktuelle Installation beiseitelegen und den Snapshot zurueckspielen."""
    src = os.path.join(_dir(inst), os.path.basename(name))
    if not os.path.isdir(src):
        raise RuntimeError("Snapshot nicht gefunden: %s" % name)

    with runner.maintenance(inst, "Snapshot-Restore"):
        was_running = runner.is_running(inst)
        steps: list[str] = []
        if was_running:
            steps.append("stop: " + runner.stop(inst, timeout=90))
            time.sleep(3)

        broken = "%s.broken-%s" % (inst.directory, time.strftime("%Y%m%d-%H%M%S"))
        try:
            os.replace(inst.directory, broken)
            steps.append("aktuelle Installation gesichert: %s" % os.path.basename(broken))
        except OSError as exc:
            raise RuntimeError("konnte aktuelle Installation nicht beiseitelegen: %s" % exc)

        shutil.copytree(src, inst.directory, symlinks=True)
        steps.append("Snapshot eingespielt: %s" % os.path.basename(name))

        if was_running:
            runner.start(inst)
            steps.append("start")
        return " | ".join(steps)


def delete(inst: Instance, name: str) -> bool:
    path = os.path.join(_dir(inst), os.path.basename(name))
    if not os.path.isdir(path):
        return False
    shutil.rmtree(path, ignore_errors=True)
    return True
