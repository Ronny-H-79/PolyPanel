"""Steam-Workshop-Suche ohne API-Key (fuer Spiele, deren Mods Workshop-IDs sind).

Die Workshop-Seite bettet ihren Zustand als JSON in `<script id="valve-ssr-data">` ein;
darin steht `renderContext.queryData` als JSON-String, und darin unter `queries[].state.data`
die Antwort von Steam mit `results[]` (publishedfileid, title, short_description,
subscriptions, preview_url) und `total_count`. Zwei `json.loads` sind noetig, und die
Queries muessen durchsucht werden (Index ist nicht stabil).
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

URL = "https://steamcommunity.com/workshop/browse/"


def clean(text: str, limit: int = 150) -> str:
    """BBCode/HTML/Markdown-Reste aus der Beschreibung entfernen."""
    text = re.sub(r"\[/?[a-zA-Z0-9=*#;:,\.\s\"'\-]+\]", " ", str(text or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\*{1,3}|_{2,}|`{1,3}", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def search(app_id: str, query: str, limit: int = 24, page: int = 1,
           timeout: float = 25.0) -> dict:
    """Trefferliste des Workshops durchsuchen; wirft RuntimeError bei kaputter Antwort."""
    url = (URL + "?appid=%s&searchtext=%s&browsesort=textsearch&section=readytouseitems&p=%d"
           % (app_id, urllib.parse.quote_plus(query), max(1, page)))
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) noah2games",
        "Accept-Language": "de,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        html = resp.read().decode("utf-8", "replace")
    m = re.search(r'id="valve-ssr-data"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise RuntimeError("Workshop-Seite ohne Daten (Steam liefert eine andere Seite)")
    ssr = json.loads(m.group(1))
    raw = (ssr.get("renderContext") or {}).get("queryData")
    if not raw:
        raise RuntimeError("Workshop-Antwort ohne Trefferliste")
    qd = json.loads(raw)
    for q in qd.get("queries") or []:
        data = (q.get("state") or {}).get("data")
        if isinstance(data, dict) and isinstance(data.get("results"), list):
            return data
    return {"results": [], "total_count": 0}


def hits(app_id: str, query: str, limit: int = 24) -> dict:
    """Suchergebnis in das Format der Web-UI bringen (id, name, description, ...)."""
    try:
        data = search(app_id, query)
    except Exception as exc:                      # noqa: BLE001 - Suche darf nicht scheitern
        return {"provider": "steam", "results": [], "has_key": True,
                "error": "Steam-Workshop: %s" % exc.__class__.__name__,
                "note": "Die Suche im Steam-Workshop ist gerade nicht erreichbar.",
                "search_url": (URL + "?appid=%s&searchtext=%s"
                               % (app_id, urllib.parse.quote(query)))}
    treffer = []
    for it in (data.get("results") or [])[:limit]:
        pid = str(it.get("publishedfileid") or "")
        if not pid:
            continue
        treffer.append({
            "id": pid,
            "name": str(it.get("title") or "Mod %s" % pid),
            "description": clean(it.get("short_description")),
            "downloads": int(it.get("subscriptions") or 0),
            "thumbnail": str(it.get("preview_url") or ""),
            "url": "https://steamcommunity.com/sharedfiles/filedetails/?id=%s" % pid,
            "source": "steam",
            "installable": True,
        })
    return {"provider": "steam", "results": treffer,
            "total": int(data.get("total_count") or len(treffer)), "has_key": True,
            "note": ("Volltextsuche im Steam-Workshop. „Installieren\" trägt die Workshop-ID ein, "
                     "der Server lädt sie beim nächsten Start."),
            "search_url": (URL + "?appid=%s&searchtext=%s"
                           % (app_id, urllib.parse.quote(query)))}
