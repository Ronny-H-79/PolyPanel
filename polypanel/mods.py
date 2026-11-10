"""Mod-Verwaltung: Liste, hinzufuegen/entfernen, Ladefehler erkennen.

ASA laedt Mods ueber den Startparameter `-mods=<id>,<id>`; der Server holt sie
beim Start selbst von CurseForge in ShooterGame/Binaries/Win64/ShooterGame/Mods/<app>/.
"""
from __future__ import annotations

import os
import re
import time

from .instance import Instance
from . import registry, runner

RE_VALID = re.compile(r"Mod valid:\s*(.+?)\s*\((\d+)\)")
RE_LOAD = re.compile(r"LoadGameMods Loading Mod .*?/Mods/(\d+)/(\d+)_(\d+)/")
RE_COOKED = re.compile(r"Mod \[(\d+)\] was cooked by a previous engine version")


def mods_dir(inst: Instance) -> str:
    return os.path.join(inst.directory, "ShooterGame", "Binaries", "Win64", "ShooterGame", "Mods")


def installed_dirs(inst: Instance) -> dict[str, list[str]]:
    """{mod_id: [ordner, ...]} aus dem Mods-Verzeichnis."""
    found: dict[str, list[str]] = {}
    base = mods_dir(inst)
    try:
        apps = os.listdir(base)
    except OSError:
        return found
    for app in apps:
        app_dir = os.path.join(base, app)
        if not os.path.isdir(app_dir):
            continue
        for entry in os.listdir(app_dir):
            m = re.match(r"(\d+)_(\d+)$", entry)
            if m:
                found.setdefault(m.group(1), []).append(os.path.join(app, entry))
    return found


def log_status(inst: Instance) -> dict[str, dict]:
    """Zustand je Mod aus dem aktuellen Log: valid / cooked / unbekannt."""
    status: dict[str, dict] = {}
    try:
        lines = runner.tail(inst.log_path, 4000)
    except OSError:
        return status
    for line in lines:
        m = RE_VALID.search(line)
        if m:
            status[m.group(2)] = {"name": m.group(1).strip(), "state": "valid"}
            continue
        m = RE_COOKED.search(line)
        if m:
            status.setdefault(m.group(1), {"name": "", "state": "cooked"})
    return status


def list_mods(inst: Instance) -> list[dict]:
    """Konfigurierte Mods mit Download- und Ladestatus."""
    folders = installed_dirs(inst)
    states = log_status(inst)
    out = []
    for mod_id in inst.mods:
        mid = str(mod_id)
        state = states.get(mid, {})
        dirs = folders.get(mid, [])
        out.append({
            "id": mid,
            "name": state.get("name") or "",
            "downloaded": bool(dirs),
            "folder": dirs[0] if dirs else "",
            "state": state.get("state", "unbekannt"),
            "issue": ("not_downloaded" if not dirs
                      else ("cooked" if state.get("state") == "cooked" else "")),
        })
    return out


def set_mods(inst: Instance, ids: list[str]) -> None:
    clean: list[int] = []
    for raw in ids:
        raw = str(raw).strip()
        if raw.isdigit() and int(raw) not in clean:
            clean.append(int(raw))
    inst.mods = clean
    registry.save(inst)
    inst.write_ini()


def add_mod(inst: Instance, mod_id: str) -> None:
    """Mod-ID eintragen. Nur Ziffern - der Wert landet in der Server-Kommandozeile."""
    mod_id = str(mod_id).strip()
    if not re.fullmatch(r"[0-9]{1,10}", mod_id):
        raise ValueError("Mod-ID muss eine Zahl sein (z. B. 947033)")
    if mod_id in [str(m) for m in inst.mods]:
        return
    set_mods(inst, [str(m) for m in inst.mods] + [mod_id])


def remove_mod(inst: Instance, mod_id: str) -> None:
    set_mods(inst, [str(m) for m in inst.mods if str(m) != str(mod_id)])


def remove_folder(inst: Instance, mod_id: str) -> bool:
    """Geladene Mod-Dateien loeschen (Platz sparen); Konfiguration bleibt unberuehrt."""
    import shutil
    folders = installed_dirs(inst).get(str(mod_id), [])
    if not folders:
        return False
    for rel in folders:
        shutil.rmtree(os.path.join(mods_dir(inst), rel), ignore_errors=True)
    return True


def mod_size_mb(inst: Instance) -> float:
    total = 0
    base = mods_dir(inst)
    for root, _dirs, files in os.walk(base):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return round(total / (1024 ** 2), 1)


def list_all(inst: Instance) -> dict:
    """Aktive Mods (in der Konfiguration) und inaktive (nur auf der Platte)."""
    active = list_mods(inst)
    active_ids = {m["id"] for m in active}
    states = log_status(inst)
    inactive = []
    for mod_id, dirs in installed_dirs(inst).items():
        if mod_id in active_ids:
            continue
        state = states.get(mod_id, {})
        inactive.append({
            "id": mod_id,
            "name": state.get("name") or "",
            "folder": dirs[0],
            "state": state.get("state", "unbekannt"),
        })
    inactive.sort(key=lambda m: m["id"])
    return {"active": active, "inactive": inactive}


# ---------------------------------------------------------------- Metadaten
META_DIR = os.path.expanduser("~/.config/polypanel/cache/mods")
META_TTL = 24 * 3600


def _cache_path(mod_id: str) -> str:
    return os.path.join(META_DIR, "%s.json" % mod_id)


def _strip_html(text: str) -> str:
    import html as _html
    import re as _re
    text = _re.sub(r"<br\s*/?>", "\n", text)
    text = _re.sub(r"</p>|</li>|</h[1-6]>", "\n", text)
    text = _re.sub(r"<li[^>]*>", "• ", text)
    text = _re.sub(r"<[^>]+>", "", text)
    text = _html.unescape(text)
    text = _re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def meta(mod_id: str, force: bool = False) -> dict:
    """Titel, Beschreibung, Bild und Link von CurseForge (via cfwidget, mit Cache)."""
    import json as _json
    import time as _time
    import urllib.request

    path = _cache_path(str(mod_id))
    if not force and os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                data = _json.load(fh)
            if _time.time() - data.get("_fetched", 0) < META_TTL:
                return data
        except (OSError, ValueError):
            pass

    try:
        req = urllib.request.Request(
            "https://api.cfwidget.com/%s" % mod_id,
            headers={"User-Agent": "PolyPanel/0.1 (+local)"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = _json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"id": str(mod_id), "title": "", "summary": "", "error": str(exc)[:80]}

    data = {
        "id": str(raw.get("id", mod_id)),
        "title": raw.get("title") or "",
        "summary": raw.get("summary") or "",
        "description": _strip_html(raw.get("description") or "")[:4000],
        "thumbnail": raw.get("thumbnail") or "",
        "url": (raw.get("urls") or {}).get("curseforge", ""),
        "downloads": (raw.get("downloads") or {}).get("total", 0),
        "categories": raw.get("categories") or [],
        "updated": (raw.get("files") or [{}])[0].get("uploaded_at", "") if raw.get("files") else "",
        "latest_file": ((raw.get("files") or [{}])[0].get("id") if raw.get("files") else None),
        "latest_name": ((raw.get("files") or [{}])[0].get("display", "") if raw.get("files") else ""),
        "_fetched": _time.time(),
    }
    try:
        os.makedirs(META_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            _json.dump(data, fh, ensure_ascii=False)
    except OSError:
        pass
    return data


def cached_meta(mod_id: str) -> dict:
    """Nur aus dem Cache lesen - blockiert nie (wichtig bei vielen Mods)."""
    import json as _json
    import time as _time
    path = _cache_path(str(mod_id))
    try:
        with open(path, encoding="utf-8") as fh:
            data = _json.load(fh)
        if _time.time() - data.get("_fetched", 0) < META_TTL:
            return data
    except (OSError, ValueError):
        pass
    return {}


def _age_days(stamp: str) -> int | None:
    """Tage seit einem ISO-Zeitstempel (z. B. 2026-11-03T08:52:46.157Z)."""
    import datetime as _dt
    if not stamp:
        return None
    try:
        txt = stamp.replace("Z", "+00:00")
        when = _dt.datetime.fromisoformat(txt)
        if when.tzinfo is None:
            when = when.replace(tzinfo=_dt.timezone.utc)
        delta = _dt.datetime.now(_dt.timezone.utc) - when
        return max(0, int(delta.total_seconds() // 86400))
    except (ValueError, TypeError):
        return None


def list_all_enriched(inst: Instance) -> dict:
    """Liste fuer die UI - ausschliesslich aus dem Cache, nie mit Netzwerkzugriff."""
    data = list_all(inst)
    installed = installed_dirs(inst)
    missing = []
    for group in ("active", "inactive"):
        for item in data[group]:
            info = cached_meta(item["id"])
            # installierte Datei-IDs dieses Mods (Ordnername <modid>_<fileid>)
            have = []
            for rel in installed.get(str(item["id"]), []):
                tail = os.path.basename(rel).split("_")[-1]
                if tail.isdigit():
                    have.append(int(tail))
            item["installed_files"] = have
            item["latest_file"] = info.get("latest_file")
            item["latest_name"] = info.get("latest_name", "")
            item["updated"] = info.get("updated", "")
            item["age_days"] = _age_days(info.get("updated", ""))
            item["outdated"] = bool(item["latest_file"] and have and int(item["latest_file"]) not in have)
            item["title"] = info.get("title") or item.get("name") or ""
            item["summary"] = info.get("summary", "")
            item["thumbnail"] = info.get("thumbnail", "")
            item["url"] = info.get("url", "")
            item["downloads"] = info.get("downloads", 0)
            item["meta_cached"] = bool(info)
            if not info:
                missing.append(item["id"])
    data["missing_meta"] = missing
    return data


def refresh_meta(ids: list[str], workers: int = 6) -> dict:
    """Fehlende/veraltete Metadaten parallel holen (Threads), damit 10 Mods nicht 80 s brauchen."""
    from concurrent.futures import ThreadPoolExecutor
    ids = [str(i) for i in ids if str(i).isdigit()]
    done = failed = 0
    with ThreadPoolExecutor(max_workers=min(workers, max(1, len(ids)))) as pool:
        for result in pool.map(lambda i: meta(i, force=True), ids):
            if result.get("error"):
                failed += 1
            else:
                done += 1
    return {"ok": done, "failed": failed, "total": len(ids)}


# --------------------------------------------------------------- Suche
SEARCH_DIR = os.path.join(os.path.dirname(META_DIR), "search")


def _search_cache_path(term: str, limit: int = 0) -> str:
    """Cache-Datei je Suchbegriff, Trefferzahl und Modus (mit/ohne API-Key).

    Ohne den Modus im Namen wuerde ein Ergebnis vom Notbehelf (wenige Treffer, kein Key)
    eine spaetere Suche mit Key eine Stunde lang bedienen.
    """
    import hashlib
    mode = "k" if _api_key() else "n"
    raw = "%s|%s|%s" % (term.lower().strip(), limit, mode)
    key = hashlib.sha1(raw.encode()).hexdigest()[:16]
    return os.path.join(SEARCH_DIR, "%s-%s-%s.json" % (key, mode, limit or 0))


def _ddg_slugs(term: str, limit: int = 18) -> list[str]:
    """Mod-Slugs ueber die DuckDuckGo-HTML-Suche finden (kein API-Key noetig)."""
    import json as _json
    import re as _re
    import urllib.parse
    import urllib.request

    query = "site:curseforge.com/ark-survival-ascended/mods %s" % term
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 PolyPanel/0.1",
        "Accept-Language": "en-US,en;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 - Suche darf nie werfen
        return []

    found = _re.findall(r"curseforge\.com/ark-survival-ascended/mods/([a-z0-9][a-z0-9-]*)", html)
    out: list[str] = []
    for slug in found:
        if slug not in out and slug not in ("search", "category"):
            out.append(slug)
        if len(out) >= limit:
            break
    return out


def _by_slug(slug: str) -> dict:
    """Metadaten zu einem CurseForge-Slug (api.cfwidget.com akzeptiert den Pfad)."""
    import json as _json
    import urllib.request

    url = "https://api.cfwidget.com/ark-survival-ascended/mods/%s" % slug
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PolyPanel/0.1 (+local)"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = _json.loads(resp.read().decode("utf-8"))
        return {
            "id": str(raw.get("id", "")),
            "title": raw.get("title") or slug,
            "summary": raw.get("summary") or "",
            "thumbnail": raw.get("thumbnail") or "",
            "downloads": (raw.get("downloads") or {}).get("total", 0),
            "slug": slug,
        }
    except Exception:  # noqa: BLE001
        return {}


def _api_key() -> str:
    """CurseForge-API-Key aus den Einstellungen (optional)."""
    try:
        from . import i18n
        return i18n.get("curseforge_key", "")
    except Exception:  # noqa: BLE001
        return ""


_API_STATE = {"total": 0}


def api_total() -> int:
    """Gesamttreffer der letzten API-Suche (0, wenn ohne Key gesucht wurde)."""
    return int(_API_STATE.get("total") or 0)


def _search_api(term: str, limit: int = 12) -> list[dict]:
    """Offizielle CurseForge-Suche - braucht einen API-Key, dafuer zuverlaessig."""
    import json as _json
    import urllib.parse
    import urllib.request

    key = _api_key()
    if not key:
        return []
    params = urllib.parse.urlencode({
        "gameId": 83374, "searchFilter": term, "pageSize": limit,
        "sortField": 2, "sortOrder": "desc",
    })
    req = urllib.request.Request(
        "https://api.curseforge.com/v1/mods/search?" + params,
        headers={"x-api-key": key, "Accept": "application/json", "User-Agent": "PolyPanel/0.1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return []
    try:
        _API_STATE["total"] = int((data.get("pagination") or {}).get("totalCount") or 0)
    except (TypeError, ValueError):
        _API_STATE["total"] = 0
    out = []
    for m in data.get("data", []):
        logo = (m.get("logo") or {}).get("thumbnailUrl") or ""
        out.append({
            "id": str(m.get("id", "")),
            "title": m.get("name") or "",
            "summary": m.get("summary") or "",
            "thumbnail": logo,
            "downloads": m.get("downloadCount", 0),
            "slug": (m.get("links") or {}).get("websiteUrl", "").rstrip("/").split("/")[-1],
        })
    return [x for x in out if x["id"]]


def search(term: str, limit: int = 12, force: bool = False) -> list[dict]:
    """Mods nach Namen suchen. Ergebnis wird eine Stunde zwischengespeichert."""
    import json as _json
    import time as _time

    term = (term or "").strip()
    if not term:
        return []

    path = _search_cache_path(term, limit)
    if not force:
        try:
            with open(path, encoding="utf-8") as fh:
                data = _json.load(fh)
            cached = data.get("results", [])
            if _time.time() - data.get("_fetched", 0) < 3600 and cached:
                _API_STATE["total"] = int(data.get("_total") or 0)
                return cached
        except (OSError, ValueError):
            pass

    results = _search_api(term, limit)
    if results:
        try:
            os.makedirs(SEARCH_DIR, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                _json.dump({"term": term, "results": results, "_fetched": _time.time(),
                            "_total": _API_STATE.get("total", 0)},
                           fh, ensure_ascii=False)
        except OSError:
            pass
        return results

    # Slug oder komplette CurseForge-Adresse: direkt aufloesen (kein API-Key noetig)
    import re as _re
    m_slug = _re.search(r"curseforge\.com/ark-survival-ascended/mods/([a-z0-9][a-z0-9-]*)", term.lower())
    candidate = m_slug.group(1) if m_slug else (term.lower() if _re.fullmatch(r"[a-z][a-z0-9-]{2,60}", term.lower()) else "")
    if candidate and not term.isdigit():
        one = _by_slug(candidate)
        if one.get("id"):
            try:
                os.makedirs(SEARCH_DIR, exist_ok=True)
                with open(path, "w", encoding="utf-8") as fh:
                    _json.dump({"term": term, "results": [one], "_fetched": _time.time()},
                               fh, ensure_ascii=False)
            except OSError:
                pass
            return [one]

    if term.isdigit():                       # direkte Mod-ID
        info = meta(term)
        results = [{"id": str(term), "title": info.get("title") or ("Mod " + term),
                    "summary": info.get("summary", ""), "thumbnail": info.get("thumbnail", ""),
                    "downloads": info.get("downloads", 0), "slug": ""}]
    else:
        from concurrent.futures import ThreadPoolExecutor
        slugs = _ddg_slugs(term, limit=limit + 4)[:limit]
        results = []
        if slugs:
            with ThreadPoolExecutor(max_workers=min(6, len(slugs))) as pool:
                for item in pool.map(_by_slug, slugs):
                    if item.get("id"):
                        results.append(item)
        results.sort(key=lambda r: (-int(r.get("downloads") or 0), r.get("title", "")))

    if results:
        try:
            os.makedirs(SEARCH_DIR, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                _json.dump({"term": term, "results": results, "_fetched": _time.time(),
                            "_total": _API_STATE.get("total", 0)},
                           fh, ensure_ascii=False)
        except OSError:
            pass
    return results


def local_index() -> list[dict]:
    """Bereits bekannte Mods aus dem Metadaten-Cache (schnell, ohne Netz)."""
    import json as _json
    out: list[dict] = []
    try:
        files = [f for f in os.listdir(META_DIR) if f.endswith(".json")]
    except OSError:
        return out
    for name in files:
        try:
            with open(os.path.join(META_DIR, name), encoding="utf-8") as fh:
                d = _json.load(fh)
        except (OSError, ValueError):
            continue
        if d.get("id"):
            out.append({"id": str(d["id"]), "title": d.get("title", ""),
                        "summary": d.get("summary", ""), "thumbnail": d.get("thumbnail", ""),
                        "downloads": d.get("downloads", 0), "slug": ""})
    return out


def suggest(term: str, limit: int = 8) -> dict:
    """Vorschlaege beim Tippen: lokaler Index zuerst, danach die Suche (falls Key)."""
    term = (term or "").strip().lower()
    if len(term) < 2:
        return {"results": [], "needs_key": not bool(_api_key()), "source": "none"}

    local = [m for m in local_index()
             if term in (m["title"] or "").lower() or term in (m["summary"] or "").lower()]
    local.sort(key=lambda m: (0 if (m["title"] or "").lower().startswith(term) else 1,
                              -int(m.get("downloads") or 0)))
    results = local[:limit]
    if len(results) >= limit:
        return {"results": results, "needs_key": not bool(_api_key()), "source": "cache"}

    seen = {m["id"] for m in results}
    for item in search(term, limit=limit):
        if item["id"] not in seen:
            results.append(item)
            seen.add(item["id"])
        if len(results) >= limit:
            break
    return {"results": results, "needs_key": not bool(_api_key()), "source": "mixed"}
