"""Web-UI fuer PolyPanel: Dashboard mit Instanzen + Instanzseiten + JSON-API."""
from __future__ import annotations

import json
import os
import re
import hmac
import secrets
import shutil
import ssl
import threading
import time
import urllib.parse
from html import escape as html_escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .instance import Instance
from . import commands as cmdreg
from . import i18n
from . import backups as bk
from . import config as cfgfile
from . import metrics
from . import notify as notify_mod
from . import mods as modlib
from . import games, registry
from . import runner
from . import snapshots as snap
from . import supervisor
from . import whitelist as wl
from .rcon import RconClient

from .paths import TOKEN_PATH
RE_PLAYER = re.compile(r"^\s*(\d+)\.\s*(.+?)\s*,\s*([0-9A-Za-z]{15,32})\s*$")
INSTALLS: dict[str, dict] = {}
# Laufende Aktion je Instanz (start/stop/restart/update). Die Oberflaeche sperrt danach
# die Knoepfe: waehrend stop gar keiner, waehrend start/restart/update nur Stop.
ACTIONS: dict[str, str] = {}


def token() -> str:
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH) as fh:
            t = fh.read().strip()
            if t:
                return t
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    t = secrets.token_urlsafe(24)
    with open(os.open(TOKEN_PATH, os.O_CREAT | os.O_WRONLY, 0o600), "w") as fh:
        fh.write(t)
    return t


def _render(template: str) -> str:
    """Sprachkatalog und Sprachcode einsetzen."""
    from . import __version__
    return (template
            .replace("__LANGJSON__", json.dumps(i18n.catalog(), ensure_ascii=False))
            .replace("__VERSION__", __version__)
            .replace("__LANG__", i18n.lang()))


def _log_step(inst: Instance, text: str) -> None:
    """Schritte von Start/Stop/Restart mitschreiben.

    Ohne diesen Mitschrieb ist ein fehlgeschlagener Start unsichtbar: der Server bleibt aus und
    niemand sieht, warum (die Ausnahme lief bisher in einem Thread ins Leere).
    """
    try:
        os.makedirs(inst.directory, exist_ok=True)
        with open(os.path.join(inst.directory, ".start.log"), "a", encoding="utf-8") as fh:
            fh.write("%s  %s\n" % (time.strftime("%F %T"), text))
    except OSError:
        pass


def rcon_cmd(inst: Instance, cmd: str, timeout: float = 12.0) -> str:
    with inst.control(timeout=timeout) as rc:
        return rc.command(cmd, timeout=timeout + 5)


def players(inst: Instance) -> list[dict[str, str]]:
    try:
        out = rcon_cmd(inst, "ListPlayers", timeout=10)
    except Exception:  # noqa: BLE001
        return []
    found = []
    for line in out.splitlines():
        m = RE_PLAYER.match(line)
        if m:
            found.append({"id": m.group(1), "name": m.group(2).strip(), "steamid": m.group(3)})
    return found


SHARED_CSS = """
:root{--bg:#06090e;--fg:#c8f0e0;--dim:#4e6b64;--acc:#25e6a4;--warn:#ffb454;--err:#ff5f6d}
*{box-sizing:border-box}
body{margin:0;color:var(--fg);font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;
min-height:100vh;
background:
 linear-gradient(170deg,#05090f 0%,#070d14 55%,#04070b 100%);
background-attachment:fixed}

body::after{content:"";position:fixed;inset:0;pointer-events:none;z-index:1;
background:radial-gradient(135% 100% at 50% 40%, transparent 58%, rgba(2,6,10,.42) 100%)}
#bg{position:fixed;inset:0;z-index:0;opacity:1}
header,main,.cards{position:relative;z-index:2}
header{padding:16px 24px;border-bottom:1px solid #16302a;display:flex;gap:14px;align-items:center;
flex-wrap:wrap;background:rgba(7,17,23,.58);backdrop-filter:blur(12px) saturate(120%);
-webkit-backdrop-filter:blur(12px) saturate(120%);border-bottom-color:rgba(64,255,199,.18)}
h1{font-size:15px;margin:0;letter-spacing:.18em;text-transform:uppercase;color:var(--acc)}
a{color:var(--acc);text-decoration:none}
.badge.warn{border-color:#e67e22;color:#e67e22}
.badge.ok{border-color:#25e6a4;color:#25e6a4}
.badge{padding:2px 8px;border:1px solid var(--dim);border-radius:3px;font-size:11px;color:var(--dim)}
.badge.on{border-color:var(--acc);color:var(--acc)}
.badge.off{border-color:var(--err);color:var(--err)}
.badge.warn{border-color:var(--warn);color:var(--warn)}
main{padding:22px 24px;display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(340px,1fr))}
section{border:1px solid rgba(64,255,199,.14);border-radius:12px;padding:16px 18px;
background:linear-gradient(180deg,rgba(14,27,35,.62),rgba(7,14,20,.74));
backdrop-filter:blur(14px) saturate(115%);box-shadow:0 10px 30px rgba(0,0,0,.35),inset 0 1px 0 rgba(255,255,255,.04)}
h2{font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--dim);margin:0 0 12px}
button{background:#0f1a1f;color:var(--fg);border:1px solid #22453c;border-radius:3px;padding:6px 11px;
font:inherit;font-size:11px;cursor:pointer;letter-spacing:.06em}
button:hover{border-color:var(--acc);color:var(--acc)}
button:disabled{opacity:.35;cursor:not-allowed;border-color:#1b3a33;color:var(--dim)}
button:disabled:hover{border-color:#1b3a33;color:var(--dim)}
button.primary{border-color:var(--acc);color:var(--acc)}
button.danger:hover{border-color:var(--err);color:var(--err)}
.plTile{cursor:pointer}
.plTile:hover b{color:var(--acc)}
.plModal{display:none;position:fixed;inset:0;background:rgba(3,7,10,.78);z-index:60;
 align-items:center;justify-content:center;padding:24px}
.plModal.on{display:flex}
.plBox{background:#08110f;border:1px solid #22453c;border-radius:4px;padding:14px 16px;
 min-width:min(720px,94vw);max-height:80vh;overflow:auto;box-shadow:0 0 40px rgba(37,230,164,.12)}
.plBody{margin-top:10px}
.plTable{width:100%;border-collapse:collapse;font-size:12px}
.plTable th{text-align:left;color:var(--dim);font-weight:400;padding:4px 6px;border-bottom:1px solid #16302a}
.plTable td{padding:5px 6px;border-bottom:1px solid #0e211c;vertical-align:middle}
.plTable td.mono{font-family:ui-monospace,monospace;color:var(--dim);font-size:11px}
.plAct{text-align:right;white-space:nowrap}
.plMsg{color:var(--acc);font-size:11.5px;padding:4px 0}
#log{height:48vh;min-height:280px;max-height:none;resize:vertical;border:1px solid var(--line);
border-radius:8px;padding:10px 12px;background:rgba(0,0,0,.28)}
pre{margin:0;max-height:230px;overflow:auto;font-size:11.5px;white-space:pre-wrap;word-break:break-word;
color:#9fc4b8}
textarea{width:100%;min-height:250px;background:rgba(12,24,30,.9);border:1px solid #22453c;color:#9fc4b8;
font:11.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;border-radius:3px;padding:8px}
input,select{width:100%;background:rgba(12,24,30,.9);border:1px solid #22453c;color:var(--fg);padding:7px 9px;
font:inherit;border-radius:3px;margin-bottom:6px}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.kv{display:grid;grid-template-columns:auto 1fr;gap:2px 12px;font-size:12px}
.kv span:nth-child(odd){color:var(--dim)}
.p{border-top:1px solid #12241f;padding:7px 0;display:flex;gap:8px;justify-content:space-between;
align-items:center;flex-wrap:wrap}
.p small{color:var(--dim)}
#out{color:var(--warn);margin-top:8px}
.tabs{display:flex;gap:6px;padding:12px 24px 0;flex-wrap:wrap;position:relative;z-index:2}
.tabs button{background:rgba(10,22,28,.85);border:1px solid rgba(64,255,199,.22);
border-radius:10px;padding:9px 18px;font-size:12.5px;letter-spacing:.07em;font-weight:600;
color:#a8d8c8;cursor:pointer;transition:color .12s,background .12s,border-color .12s,box-shadow .12s}
.tabs button:hover{color:#e6fff5;border-color:rgba(64,255,199,.45);background:rgba(18,38,44,.9)}
.tabs button.on{border-color:var(--acc);color:#04120d;background:linear-gradient(180deg,#4df3bb,#1fd79a);
box-shadow:0 6px 18px rgba(37,230,164,.28),inset 0 1px 0 rgba(255,255,255,.35)}
.tabs{background:rgba(6,14,19,.55);backdrop-filter:blur(10px);border-bottom:1px solid rgba(64,255,199,.14);padding-bottom:10px}
.tab.wide{grid-column:1/-1}
.tab{display:none}
.tab.on{display:block}
.setrow{display:grid;grid-template-columns:1fr 190px;gap:8px;align-items:center;
padding:6px 0;border-top:1px solid #12241f}
.setrow label b{font-weight:500;display:block}
.setrow label small{color:var(--dim);font-size:10.5px}
.setrow input[type=text],.setrow input[type=number]{margin:0}
.setrow .bool{display:flex;justify-content:flex-end}
.setrow input[type=checkbox]{width:auto;transform:scale(1.25);margin:0}
.cards{display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));padding:24px 24px 24px}
.cardgrid{display:grid;grid-template-columns:minmax(0,1fr);gap:12px;align-items:start}
.cardmain{display:flex;flex-direction:column;gap:10px;min-width:0}
@container (min-width:560px){.cardgrid{grid-template-columns:minmax(0,1.15fr) minmax(0,.85fr)}}
@media (min-width:900px){.card.running{grid-column:span 2}}
.hdr-icons{margin-left:auto;display:inline-flex;align-items:center;gap:6px}
.iconlink{display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;
border:1px solid #1d3a32;border-radius:6px;background:#0b1116;transition:filter .15s,border-color .15s}
.iconlink:hover{filter:brightness(1.18);border-color:#2c5c4c}
.iconlink svg{width:22px;height:22px;display:block}
.iconlink.discord svg{fill:#5865F2}
.iconlink.paypal svg{fill:#003087}
.sitefoot{position:relative;z-index:2;width:100%;box-sizing:border-box;margin:26px 0 0;padding:16px 24px 22px;
border-top:1px solid rgba(64,255,199,.14);display:flex;flex-wrap:wrap;gap:8px 20px;
align-items:center;justify-content:center;font-size:11.5px;letter-spacing:.04em;color:var(--dim)}
.sitefoot .flinks{display:inline-flex;flex-wrap:wrap;gap:16px;align-items:center}
.sitefoot a{color:#a8d8c8;text-decoration:none;border-bottom:1px solid rgba(64,255,199,.28);
padding-bottom:1px;transition:color .12s,border-color .12s}
.sitefoot a:hover{color:#e6fff5;border-color:var(--acc)}
.lic{padding:24px}
.lictext{margin:0;white-space:pre-wrap;max-height:none;font-size:12px;line-height:1.65;color:#b9d6cc}
.lichead{display:flex;flex-wrap:wrap;gap:10px;align-items:baseline;margin:0 0 12px}
.lichead h2{margin:0}
.lichead .meta{color:var(--dim);font-size:11.5px}
.settabs{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 10px;border-bottom:1px solid #16302a;padding-bottom:8px}
.settabs button small{opacity:.55;font-size:10px;margin-left:4px}
.settabs button.on{border-color:var(--acc);color:var(--acc)}
.setgroup{display:none}
.setgroup.on{display:block}
.logwrap{background:rgba(5,13,18,.85);border:1px solid #12241f;border-radius:4px;padding:6px 8px;min-width:0}
.loghead{font-size:9px;letter-spacing:.16em;text-transform:uppercase;color:var(--dim);margin-bottom:4px}
.cardlog{margin:0;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:9.5px;line-height:1.35;
color:#9fb8ae;white-space:pre-wrap;word-break:break-word;max-height:132px;overflow:hidden}
.card{border:1px solid rgba(64,255,199,.16);border-radius:14px;padding:16px 18px;
background:linear-gradient(180deg,rgba(16,31,40,.66),rgba(7,14,20,.78));
backdrop-filter:blur(16px) saturate(115%);box-shadow:0 14px 34px rgba(0,0,0,.38),inset 0 1px 0 rgba(255,255,255,.05);
display:flex;flex-direction:column;gap:10px;position:relative;overflow:hidden;container-type:inline-size}
.card .bgimg{position:absolute;inset:0;background-size:cover;background-position:center;
opacity:.62;filter:saturate(.9) contrast(1.05) brightness(.95);z-index:0}
.card .bgimg::after{content:"";position:absolute;inset:0;
background:linear-gradient(180deg,rgba(6,9,14,.30) 0%,rgba(6,9,14,.62) 45%,rgba(6,9,14,.88) 100%)}
.card>*{position:relative;z-index:1}
.card h3{margin:0;font-size:14px;letter-spacing:.06em}
.card .meta{color:var(--dim);font-size:11.5px}
#mods{max-height:430px;overflow-y:auto;padding-right:4px}
#modhits{max-height:420px;overflow-y:auto;padding-right:6px;margin:6px 0;
border-top:1px solid #16302a;border-bottom:1px solid #16302a}
#modhits .p{padding:6px 0;border-bottom:1px solid #10201b}
#modhits .p:last-child{border-bottom:0}
.taskrow{display:flex;gap:5px;row-gap:2px;align-items:center;flex-wrap:wrap;padding:2px 0;border-bottom:1px solid #10201b}
.taskrow select{width:auto;min-width:120px}
.taskrow select,.taskrow input{width:auto;padding:3px 6px;font-size:12px}
.taskrow input[type=time]{width:auto}
.dayboxes{display:flex;gap:3px}
.daybox{display:inline-flex;align-items:center;gap:5px;font-size:12px;color:var(--dim);
background:#0b1418;border:1px solid #16302a;border-radius:3px;padding:4px 7px;white-space:nowrap}
.daybox input{appearance:none;-webkit-appearance:none;width:13px;height:13px;margin:0;cursor:pointer;
background:#0a1519;border:1px solid #24554a;border-radius:2px;position:relative;transition:background .12s,border-color .12s}
.daybox input:checked{background:#2f7d68;border-color:#2f7d68}
.daybox input:checked::after{content:"";position:absolute;left:3.5px;top:1px;width:4px;height:8px;
border:solid #04140f;border-width:0 2px 2px 0;transform:rotate(45deg)}
.daybox input:hover{border-color:#3f8a76}
.hint{font-size:11px;color:var(--dim);line-height:1.4;margin:4px 0 2px;max-width:62ch}
#modhitsum{font-size:12.5px;color:var(--acc);font-weight:600;margin:8px 0 2px;min-height:1em}
.thumb{width:44px;height:44px;border-radius:4px;object-fit:cover;border:1px solid #16302a;flex:0 0 44px}
.mrow{display:flex;gap:10px;align-items:center}
.mrow .txt{min-width:0}
.mrow .txt b{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:200px}
.modal{position:fixed;inset:0;background:rgba(2,5,7,.82);display:none;z-index:50;
align-items:center;justify-content:center;padding:24px}
.modal.on{display:flex}
.mbox{background:#0b1116;border:1px solid #1d3a32;border-radius:8px;max-width:640px;width:100%;
max-height:80vh;overflow:auto;padding:18px 20px;position:relative}
.mbox img.big{width:96px;height:96px;border-radius:6px;border:1px solid #16302a;float:left;margin:0 14px 8px 0}
.mbox h3{margin:0 0 4px;font-size:15px}
.mbox .desc{white-space:pre-wrap;font-size:12px;color:#9fc4b8;margin-top:10px;clear:both}
.mbox .close{position:absolute;top:10px;right:12px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:2px 0}
.stats div{background:#0a1418;border:1px solid #12241f;border-radius:4px;padding:6px 8px}
.stats b{display:block;font-size:15px;color:var(--fg);font-weight:500}
.stats small{display:block;color:var(--dim);font-size:9.5px;letter-spacing:.14em;text-transform:uppercase}
.spark{width:100%;height:38px;display:block}
.hostbar{display:flex;gap:10px;align-items:center;font-size:11px;color:var(--dim)}
"""

BG_JS = """
// Sternenfeld: drei Tiefenebenen ziehen langsam, dazu ein zarter Nebel
const cv=document.getElementById('bg');
if(cv){
  const ctx=cv.getContext('2d',{alpha:false});
  let W=0,H=0,dpr=Math.min(devicePixelRatio||1,2),steren=[],t0=performance.now(),lauf=true;
  const ruhig=matchMedia('(prefers-reduced-motion: reduce)').matches;
  const nebel=[
    {h:[40,120,180], x:.22, y:.26, r:.62, a:.16, sx:.031, sy:.043},
    {h:[110,70,170], x:.78, y:.20, r:.52, a:.13, sx:.026, sy:.037},
    {h:[30,150,140], x:.62, y:.86, r:.58, a:.11, sx:.021, sy:.029}
  ];

  function build(){
    W=cv.width=innerWidth*dpr; H=cv.height=innerHeight*dpr;
    cv.style.width=innerWidth+'px'; cv.style.height=innerHeight+'px';
    const n=Math.round((innerWidth*innerHeight)/5200);
    steren=Array.from({length:n},()=>{
      const tiefe=Math.random();                       // 0 = fern, 1 = nah
      return {x:Math.random()*W, y:Math.random()*H, z:tiefe,
              gros:(0.4+tiefe*1.5)*dpr,                  // Groesse
              vx:(0.02+tiefe*0.10)*dpr,                 // Drift nach rechts
              vy:(0.01+tiefe*0.05)*dpr,
              ph:Math.random()*6.283, tw:0.4+Math.random()*1.6};
    });
  }
  addEventListener('resize',build);
  document.addEventListener('visibilitychange',()=>{ lauf=!document.hidden; if(lauf) requestAnimationFrame(frame); });
  build();

  function nebelFleck(n,t){
    const cx=(n.x + Math.sin(t*n.sx)*0.06)*W;
    const cy=(n.y + Math.cos(t*n.sy)*0.05)*H;
    const r=n.r*Math.max(W,H)*0.7;
    const [rh,rg,rb]=n.h;
    const g=ctx.createRadialGradient(cx,cy,0,cx,cy,r);
    g.addColorStop(0,'rgba('+rh+','+rg+','+rb+','+n.a+')');
    g.addColorStop(1,'rgba('+rh+','+rg+','+rb+',0)');
    ctx.fillStyle=g; ctx.fillRect(0,0,W,H);
  }

  function frame(now){
    if(!lauf) return;
    const t=ruhig?0:(now-t0)/1000;
    ctx.globalCompositeOperation='source-over';
    ctx.fillStyle='#04070c'; ctx.fillRect(0,0,W,H);
    ctx.globalCompositeOperation='lighter';
    for(const n of nebel) nebelFleck(n,t);

    for(const s of steren){
      if(!ruhig){ s.x+=s.vx; s.y+=s.vy; }
      if(s.x>W+4) s.x=-4;
      if(s.y>H+4) s.y=-4;
      const funkeln = ruhig ? 0.85 : 0.65 + Math.sin(t*s.tw + s.ph)*0.35;
      const a=(0.25+s.z*0.65)*funkeln;
      ctx.fillStyle='rgba(214,240,255,'+a.toFixed(3)+')';
      ctx.beginPath(); ctx.arc(s.x,s.y,s.gros,0,6.283); ctx.fill();
      if(s.z>0.88 && !ruhig){                       // wenige grosse Sterne mit Hof
        const g=ctx.createRadialGradient(s.x,s.y,0,s.x,s.y,s.gros*7);
        g.addColorStop(0,'rgba(190,235,255,'+(a*0.35).toFixed(3)+')');
        g.addColorStop(1,'rgba(190,235,255,0)');
        ctx.fillStyle=g; ctx.fillRect(s.x-s.gros*7,s.y-s.gros*7,s.gros*14,s.gros*14);
      }
    }
    ctx.globalCompositeOperation='source-over';
    if(!ruhig) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}
"""

PAYPAL_URL = ("https://www.paypal.com/donate/?business=ronnyhase%40fn.de"
              "&item_name=PolyPanel%20Servermanager&currency_code=EUR")
DISCORD_URL = "https://discord.gg/ark-ase-asa-hilfe"

HEADER_ICONS = """
<span class="hdr-icons">
<a class="iconlink discord" href="__DISCORD_URL__" target="_blank" rel="noopener"
   data-tp="ui.discord" data-ttitle="ui.discord" title="Discord: Ark-ASA-ASE-Hilfe" aria-label="Discord">
  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189Z"/></svg></a>
<a class="iconlink paypal" href="__PAYPAL_URL__"
   target="_blank" rel="noopener" data-ttitle="ui.donate" title="Spenden via PayPal" aria-label="PayPal">
  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15.607 4.653H8.941L6.645 19.251H1.82L4.862 0h7.995c3.754 0 6.375 2.294 6.473 5.513-.648-.478-2.105-.86-3.722-.86m6.57 5.546c0 3.41-3.01 6.853-6.958 6.853h-2.493L11.595 24H6.74l1.845-11.538h3.592c4.208 0 7.346-3.634 7.153-6.949a5.24 5.24 0 0 1 2.848 4.686M9.653 5.546h6.408c.907 0 1.942.222 2.363.541-.195 2.741-2.655 5.483-6.441 5.483H8.714Z"/></svg></a>
</span>
"""
HEADER_ICONS = (HEADER_ICONS.replace("__PAYPAL_URL__", PAYPAL_URL)
                            .replace("__DISCORD_URL__", DISCORD_URL))

# Gemeinsamer Fuß: Copyright, Lizenz-Seite, Spenden- und Community-Link.
# Der Lizenz-Link bekommt das Token per Skript, damit er auf jeder Seite funktioniert.
FOOTER = """<footer class="sitefoot">
<span class="fmeta">PolyPanel __VERSION__ · © 2026 Ronny H. ·
  <span data-t="foot.rights">alle Rechte vorbehalten</span></span>
<span class="flinks">
  <a data-tok="/license" data-t="foot.license" title="Lizenz">Lizenz</a>
  <a href="__PAYPAL_URL__" target="_blank" rel="noopener" data-t="foot.donate"
     data-ttitle="ui.donate" title="Spenden via PayPal">PayPal</a>
  <a href="__DISCORD_URL__" target="_blank" rel="noopener" data-t="foot.discord"
     data-ttitle="ui.discord" title="Discord: Ark-ASA-ASE-Hilfe">Discord-Community</a>
</span>
</footer>
<script>(function(){var t=new URLSearchParams(location.search).get('token')||'';
document.querySelectorAll('a[data-tok]').forEach(function(a){
  a.href=a.dataset.tok+(t?'?token='+encodeURIComponent(t):'');});
/* Der Fuß steht nach dem Hauptskript: Texte hier noch einmal in der aktiven Sprache setzen. */
if(typeof applyLang==='function') applyLang();})();</script>"""
FOOTER = (FOOTER.replace("__PAYPAL_URL__", PAYPAL_URL)
                .replace("__DISCORD_URL__", DISCORD_URL))

DASH = """<!doctype html><html lang="__LANG__"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>PolyPanel</title>
<style>""" + SHARED_CSS + """</style></head><body>
<canvas id="bg"></canvas>
<header><h1>PolyPanel</h1><span class="badge" id="cnt">…</span>
<span class="badge" data-t="dash.dashboard">Dashboard</span>
<span class="hostbar"><span id="hostcpu">CPU –</span><span id="hostram">RAM –</span>
  <button onclick="polyPanelUpdate()" id="verbtn" style="padding:2px 8px">PolyPanel</button>
  <button onclick="openChangelog()" id="clogbtn" style="padding:2px 8px"
    data-t="self.changelog" title="Changelog">Changelog</button>
  <button onclick="toggleLang()" id="langbtn" style="padding:2px 8px">EN</button></span>""" + HEADER_ICONS + """</header>
<div class="modal" id="modal" onclick="if(event.target.id==='modal')closeModal()">
  <div class="mbox"><button class="close" onclick="closeModal()">×</button>
    <div id="mbody">…</div></div>
</div>
<script>
const GAMESHINT = {
  ark:            {install: "~50 GB über SteamCMD (Windows-Binary, Wine)", ports: "Spiel 7777 · Query 27016 · RCON 27025", ram: "8–16 GB (ohne Mods)"},
  arkse:          {install: "~20 GB über SteamCMD (nativ, Linux)",         ports: "Spiel 7777 · Query 7778 · RCON 27020", ram: "6–10 GB (ohne Mods)"},
  satisfactory:   {install: "~12 GB über SteamCMD (nativ)",                 ports: "Spiel 7777 · Query 15777 · Beacon 15000", ram: "6–12 GB (ohne Mods)"},
  "7d2d":         {install: "~18 GB über SteamCMD (nativ)",                 ports: "Spiel 26900 · Telnet 8081",        ram: "4–8 GB (ohne Mods)"},
  spaceengineers: {install: "~8 GB über SteamCMD (Windows-Binary, Wine)",   ports: "Spiel 27016 · Steam 27015",        ram: "4–8 GB (ohne Mods)"}
};
const GAMEMAPS = __GAMEMAPS__;
function fillMap(){
  const g=(document.getElementById('ngame')||{}).value||'ark';
  const m=document.getElementById('nmap'); if(!m) return;
  const list=GAMEMAPS[g]||[];
  m.style.display=list.length?'':'none';
  m.innerHTML=list.map(function(x){ return '<option value="'+x[0]+'">'+x[1]+'</option>'; }).join('');
}
function updateHint(){
  const g=(document.getElementById('ngame')||{}).value||'ark';
  const h=GAMESHINT[g]; if(!h) return;
  const set=(id,v)=>{ const e=document.getElementById(id); if(e) e.textContent=v; };
  set('hint_install', h.install); set('hint_ports', h.ports); set('hint_ram', h.ram);
}
document.addEventListener('DOMContentLoaded', function(){ updateHint(); fillMap(); });
</script>
<main>
  <section><h2 data-t="dash.new_instance">Neue Instanz</h2>
    <input id="nname" data-tp="dash.name_ph" placeholder="Name">
    <select id="ngame" onchange="toggleMap()">__GAMES__</select>
    <select id="nmap"></select>
    <input id="nport" data-tp="dash.port_ph" placeholder="Port">
    <input id="nsession" data-tp="dash.session_ph" placeholder="Spieleserver-Name">
    <div class="row"><button class="primary" onclick="createInst()" data-t="dash.create">Anlegen</button></div>
    <pre id="out">–</pre>
  </section>
  <section><h2 data-t="dash.note">Hinweis</h2>
    <div class="kv">
      <span data-t="dash.install_label">Installation</span><span id="hint_install" data-t="dash.install_size">SteamCMD</span>
      <span data-t="dash.ports_label">Ports</span><span id="hint_ports" data-t="dash.ports">Ports</span>
      <span data-t="dash.memory_label">Speicher</span><span id="hint_ram" data-t="dash.memory">RAM</span>
    </div>
  </section>
</main>
<div id="actbanner" style="display:none;margin:10px 0;padding:10px 14px;border-radius:8px;background:#123;border:1px solid #2a6;color:#bfe"></div>
<div class="cards" id="cards"></div>
<script>""" + BG_JS + """
const L=__LANGJSON__;
async function toggleLang(){
  const next = (L.lang === 'de') ? 'en' : 'de';
  try{ await fetch('/api/lang?set=' + next + '&token=' + encodeURIComponent(T), {method:'POST'}); }
  catch(e){ alert(L['msg.lang_failed'] + ' ' + e); return; }
  location.reload();
}
function applyLang(){
  document.querySelectorAll('[data-t]').forEach(e=>{const k=e.dataset.t;if(L[k])e.textContent=L[k];});
  document.querySelectorAll('[data-tp]').forEach(e=>{const k=e.dataset.tp;if(L[k])e.placeholder=L[k];});
  const lb=document.getElementById('langbtn'); if(lb) lb.textContent=(L.lang==='de')?'EN':'DE';
}
const T=new URLSearchParams(location.search).get('token')||'';

// Klicks nicht verlieren: waehrend der Knopf gedrueckt ist, den DOM nicht neu bauen.
// Ohne das ersetzt der 3-5-s-Poll die Karten/Listen genau unter dem Mauszeiger und der
// Klick landet im Nichts - das Symptom "reagiert erst beim zweiten Klick".
document.addEventListener('pointerdown', () => { window.__pressed = 1; }, true);
['pointerup', 'pointercancel'].forEach(function (t) {
  document.addEventListener(t, () => { window.__pressed = 0; }, true);
});
window.addEventListener('blur', () => { window.__pressed = 0; });

const api=(p,o)=>fetch(p+(p.includes('?')?'&':'?')+'token='+encodeURIComponent(T),o).then(r=>r.text());
let DATA=[];
let LOGTIMER=null, LOGS={};   // Karten-Log: Timer und letzte Zeilen je Instanz
function fmtUp(s){ if(!s) return '–'; const h=Math.floor(s/3600), m=Math.floor(s%3600/60);
  return h? h+'h '+m+'m' : m+'m'; }
function spark(cv, a, b, amax, bmax){
  const ctx=cv.getContext('2d'), W=cv.width, H=cv.height, P=2;
  const line=(arr,max,color)=>{ if(!arr||arr.length<2)return;
    ctx.beginPath(); ctx.strokeStyle=color; ctx.lineWidth=1.4;
    arr.forEach((v,idx)=>{ const x=P+idx/(arr.length-1)*(W-2*P);
      const y=H-P-Math.min(1,v/(max||1))*(H-2*P);
      idx?ctx.lineTo(x,y):ctx.moveTo(x,y); });
    ctx.stroke(); };
  ctx.clearRect(0,0,W,H);
  ctx.strokeStyle='rgba(37,230,164,.10)'; ctx.lineWidth=1;
  ctx.beginPath(); ctx.moveTo(0,H-P); ctx.lineTo(W,H-P); ctx.stroke();
  line(b, bmax, 'rgba(120,170,255,.55)');
  line(a, amax, 'rgba(37,230,164,.95)');
}
async function load(){
  if(window.__pressed){ setTimeout(load, 400); return; }   // Klick laeuft noch
  const _b=document.getElementById('actbanner'); if(_b && _b.dataset.done==='1'){ _b.style.display='none'; }
  const list=JSON.parse(await api('/api/instances'));
  DATA=list;
  const _now=Date.now();
  Object.keys(window.LOCAL_ACT||{}).forEach(n=>{
    const l=window.LOCAL_ACT[n], s=list.find(x=>x.name===n);
    if(!s || _now-l.ts>25000 || s.action) delete window.LOCAL_ACT[n];
  });
  document.getElementById('cnt').textContent=list.length+' '+L[list.length===1?'dash.instance_single':'dash.instances'];
  document.getElementById('cards').innerHTML=list.map(i=>`
    <div class="card${i.running?' running':''}">
      ${i.map_image?`<div class="bgimg" style="background-image:url('${i.map_image}?token=${encodeURIComponent(T)}')"></div>`:''}
      <div class="cardgrid"><div class="cardmain">
      <div class="row" style="justify-content:space-between">
        <h3>${i.name}</h3>
        <span class="badge ${i.running?(i.ready?'on':'warn'):'off'}">${i.running?(i.ready?L['status.running']:L['status.starting']):L['status.off']}</span>
      </div>
      <div class="meta">${i.game && i.game!=="ark"
        ? `${i.game_label} · Port ${i.port}`
        : `${i.map} · Port ${i.port} · RCON ${i.rcon_port}`}</div>
      <div class="meta">${i.installed?('Build '+i.build+' · '+i.size_gb+' GB'):L['dash.not_installed']}</div>
      ${i.running?`<div class="stats">
        <div title="${L['dash.cpu_title'].replace('{p}',(i.cpu_pct!==undefined?i.cpu_pct:(i.cpu/(i.cores||navigator.hardwareConcurrency||1))).toFixed(1)).replace('{c}',(i.cpu/100).toFixed(1)).replace('{n}',i.cores||navigator.hardwareConcurrency||1)}"><b>${(i.cpu_pct!==undefined?i.cpu_pct:(i.cpu/(i.cores||navigator.hardwareConcurrency||1))).toFixed(1)}%</b><small>${L['dash.cpu']}</small></div>
        <div title="Spitze: ${i.ram_peak_gb||0} GB"><b>${i.ram_gb.toFixed(1)}G</b><small>${L['dash.ram']}</small></div>
        <div class="plTile" onclick="showPlayers('${i.name}')" title="${L['dash.players_hint']}"><b>${i.players}</b><small>${L['dash.players']}</small></div>
        <div><b>${fmtUp(i.uptime)}</b><small>${L['dash.uptime']}</small></div>
      </div><canvas class="spark" width="300" height="38"></canvas>`:''}
      <div class="row">
        ${(()=>{
          const la=(window.LOCAL_ACT||{})[i.name];
          const a=i.action || (la&&la.what) || '';
          // Waehrend Stop ist alles gesperrt. Waehrend Start/Restart/Update (und solange die
          // Instanz hochfaehrt) bleibt nur Stop bedienbar - zum Abbrechen.
          const startingNow = (a==='start'||a==='restart'||a==='update') || (i.running && !i.ready);
          const stoppingNow = (a==='stop');
          const off = ' disabled';
          const menu = (dis)=>`<a href="/i/${i.name}?token=${encodeURIComponent(T)}"><button${dis}>${L['common.menu']}</button></a>`;
          const bStart = (dis)=>`<button onclick="act('${i.name}','start')"${dis}>${L['common.start']}</button>`;
          const bRestart=(dis)=>`<button onclick="act('${i.name}','restart')"${dis}>${L['common.restart']}</button>`;
          const bUpdate = (dis)=>`<button onclick="updInst('${i.name}')"${dis}>${L['common.update']}</button>`;
          const bStop   = (dis)=>`<button class="danger" onclick="act('${i.name}','stop')"${dis}>${L['common.stop']}</button>`;
          const bDel    = (dis)=>`<button class="danger" onclick="delInst('${i.name}',${i.size_gb||0})"${dis}>${L['common.delete']}</button>`;
          if(!i.installed)
            return `<button class="primary" onclick="install('${i.name}')"${startingNow||stoppingNow?off:''}>${L['dash.install']}</button>
                    <button class="danger" onclick="delInst('${i.name}',0)"${startingNow||stoppingNow?off:''}>${L['common.delete']}</button>`;
          // Menue bleibt immer bedienbar - von dort kommt man an Log, Konfig und alles weitere.
          if(stoppingNow)
            return menu('')+bStart(off)+bRestart(off)+bUpdate(off)+bStop(off)+bDel(off);
          if(startingNow)
            return menu('')+bStart(off)+bRestart(off)+bUpdate(off)+bStop('')+bDel(off);
          // Update ist bewusst auch bei gestoppter Instanz bedienbar: genau dann
          // lassen sich die Serverdateien tauschen.
          return menu('')+bStart(i.running?off:'')+bRestart(i.running?'':off)+
                 bUpdate('')+bStop(i.running?'':off)+bDel('');
        })()}
      </div>
      </div>${i.running?`<div class="logwrap"><div class="loghead">${L['dash.log']}</div><pre class="cardlog" data-inst="${i.name}">…</pre></div>`:''}
      </div>
    </div>`).join('');
  const canvases=[...document.querySelectorAll('.spark')];
  canvases.forEach(cv=>{
    const name=cv.closest('.card').querySelector('h3').textContent.trim();
    const d=DATA.find(x=>x.name===name); if(!d)return;
    const rmax=Math.max(1,...(d.ram_hist||[0]));
    // CPU als Anteil des Servers (0-100), damit die Achse immer bei 100 % endet
    const chist=d.cpu_hist_pct||(d.cpu_hist||[]).map(v=>v/(d.cores||1));
    spark(cv, chist, d.ram_hist||[], 100, rmax*1.15);
  });
  // Lebendes Server-Log rechts in der Karte; die letzte Fassung ueberlebt den 3-Sekunden-Refresh
  const logBoxes=[...document.querySelectorAll('.cardlog')];
  logBoxes.forEach(el=>{ const t=LOGS[el.dataset.inst]; if(t) el.textContent=t; });
  clearInterval(LOGTIMER);
  if(logBoxes.length){
    const pull=async()=>{ for(const el of logBoxes){
        try{ const txt=(await api('/api/logs?name='+encodeURIComponent(el.dataset.inst)+'&n=10')).trim();
          LOGS[el.dataset.inst]=txt; el.textContent=txt||L['dash.log_empty'];
        }catch(e){}
    } };
    pull();
    LOGTIMER=setInterval(pull,2500);
  }
}
async function loadHost(){
  if(window.__pressed){ setTimeout(loadHost, 400); return; }   // Klick laeuft noch
  try{ const h=JSON.parse(await api('/api/host'));
    document.getElementById('hostcpu').textContent='CPU '+h.cpu.toFixed(1)+'%';
    document.getElementById('hostram').textContent='RAM '+h.ram_used_gb+'/'+h.ram_total_gb+' GB ('+h.ram_pct+'%)';
  }catch(e){}
}
async function act(name,what){
  // Stop/Restart optisch bestaetigen: Button sperren, Banner zeigen, Status pollen
  const btns=[...document.querySelectorAll('button')].filter(b=>{
    const oc=b.getAttribute('onclick')||''; return oc.includes("'"+name+"'") && oc.includes("'"+what+"'");
  });
  const TXT={stop:L['act.stopping'], start:L['act.starting'], restart:L['act.restarting']};
  const alt=TXT[what]||L['act.working'];
  btns.forEach(b=>{ b.disabled=true; b.dataset.old=b.textContent; b.textContent='…'; });
  const banner=document.getElementById('actbanner');
  if(banner){ banner.style.display=''; banner.textContent=alt.replace('{n}',name); }
  try{
    await api('/api/'+what+'?name='+encodeURIComponent(name),{method:'POST'});
  }catch(e){
    if(banner){ banner.textContent='Fehler: '+e; }
    btns.forEach(b=>{ b.disabled=false; b.textContent=b.dataset.old||b.textContent; });
    return;
  }
  if(what==='stop'){
    const t0=Date.now();
    while(Date.now()-t0 < 70000){
      await new Promise(r=>setTimeout(r,1500));
      let st=null;
      try{ st=JSON.parse(await api('/api/status?name='+encodeURIComponent(name))); }catch(e){}
      if(st && !st.running){
        if(banner){ banner.textContent=L['act.stopped'].replace('{n}',name); setTimeout(()=>{banner.style.display='none';},2500); }
        load(); return;
      }
      if(banner) banner.textContent=alt.replace('{n}',name)+' ('+Math.round((Date.now()-t0)/1000)+' s)';
    }
    if(banner) banner.textContent=L['act.stop_timeout'].replace('{n}',name);
    load(); return;
  }
  // Start/Restart: warten bis der Server wirklich laeuft
  if(what==='start'||what==='restart'){
    const t0=Date.now();
    while(Date.now()-t0 < 90000){
      await new Promise(r=>setTimeout(r,1500));
      let st=null;
      try{ st=JSON.parse(await api('/api/status?name='+encodeURIComponent(name))); }catch(e){}
      if(st && st.running){
        if(banner){ banner.textContent=L['act.running'].replace('{n}',name); setTimeout(()=>{banner.style.display='none';},2500); }
        load(); return;
      }
      if(banner) banner.textContent=alt.replace('{n}',name)+' ('+Math.round((Date.now()-t0)/1000)+' s)';
    }
    if(banner){
      banner.textContent=alt.replace('{n}',name)+' — '+(L['act.slow']||'keine Rückmeldung');
      setTimeout(()=>{ banner.style.display='none'; }, 6000);
    }
    load();
    return;
  }
  setTimeout(load,1500);
}


async function updInst(name){
  if(!confirm(L['msg.confirm_update'])) return;
  window.LOCAL_ACT = window.LOCAL_ACT || {};
  window.LOCAL_ACT[name]={what:'update',ts:Date.now()};
  load();
  try{
    await api('/api/update?name='+encodeURIComponent(name), {method:'POST'});
    alert(L['msg.update_started']);
    setTimeout(load, 1500);
  }catch(e){ alert(String(e)); }
}
async function delInst(name, sizeGb){
  if(!confirm(L['msg.confirm_instance_delete'].replace('{n}', name))) return;
  // ohne Installation gibt es keine Serverdaten - dann faellt die Rueckfrage weg
  let files = sizeGb ? 0 : 1;
  if(sizeGb && confirm(L['msg.confirm_instance_files'].replace('{n}', name).replace('{size}', sizeGb))){
    files = 1;
  }
  const msg = document.getElementById('instmsg');
  if(msg) msg.textContent='…';
  try{
    const raw = await api('/api/instance/delete?name='+encodeURIComponent(name)+'&files='+files, {method:'POST'});
    let r; try{ r = JSON.parse(raw); }catch(e){ r = {ok:true}; }
    if(r.ok){
      const frei = r.freed_gb >= 1 ? (Math.round(r.freed_gb).toLocaleString('de-DE')+' GB')
                 : (r.freed_mb ? (r.freed_mb.toLocaleString('de-DE')+' MB') : '');
      if(msg) msg.textContent = frei
        ? (frei+' freigegeben · '+name+' entfernt')
        : (name+' entfernt' + (files ? ' · Dateien blieben liegen' : ' · Dateien behalten'));
      if(r.hint) alert(r.hint);
      load();
    } else { alert(r.error || 'Fehler'); }
  }catch(e){ alert(String(e)); }
}
function toggleMap(){
  if(typeof fillMap==='function') fillMap();
  if(typeof updateHint==='function') updateHint();
}
async function createInst(){
  const name=document.getElementById('nname').value.trim();
  if(!name){alert('Name fehlt');return;}
  const q=new URLSearchParams({name:name,game:document.getElementById('ngame').value,
    map:document.getElementById('nmap').value,
    port:document.getElementById('nport').value,session:document.getElementById('nsession').value}).toString();
  document.getElementById('out').textContent=await api('/api/instances?'+q,{method:'POST'});
  setTimeout(load,800);
}
async function install(name){
  document.getElementById('out').textContent=await api('/api/install?name='+name,{method:'POST'});
  // Fortschrittsbalken ueber der Ausgabe: SteamCMD meldet Prozentwerte, die hier live einlaufen
  let bar=document.getElementById('instbar'), label=document.getElementById('instbarlabel');
  if(!bar){
    const out=document.getElementById('out');
    label=document.createElement('div'); label.id='instbarlabel';
    label.style.cssText='font-size:12px;color:var(--dim);margin:8px 0 4px;display:none';
    bar=document.createElement('div'); bar.id='instbar';
    bar.style.cssText='height:14px;border-radius:7px;background:rgba(255,255,255,.08);overflow:hidden;display:none;margin-bottom:10px';
    bar.innerHTML='<div id="instbarfill" style="height:100%;width:0%;background:linear-gradient(90deg,#2f81f7,#56d364);transition:width .6s"></div>';
    out.parentNode.insertBefore(label,out); out.parentNode.insertBefore(bar,out);
  }
  const fill=bar.querySelector('#instbarfill');
  let stopBtn=document.getElementById('instcancel');
  if(!stopBtn){
    stopBtn=document.createElement('button'); stopBtn.id='instcancel';
    stopBtn.textContent=L['inst.cancel']||'Installation abbrechen';
    stopBtn.style.cssText='margin:0 0 10px;padding:4px 10px;font-size:12px';
    stopBtn.onclick=async()=>{
      if(!confirm(L['inst.cancel_ask']||'Installation wirklich abbrechen?')) return;
      try{ await api('/api/install/cancel?name='+encodeURIComponent(name),{method:'POST'}); }
      catch(e){ alert((L['inst.action_failed']||'Aktion fehlgeschlagen:')+' '+e); }
      stopBtn.remove(); setTimeout(load,800);
    };
    out.parentNode.insertBefore(stopBtn,out);
  }
  const t=setInterval(async()=>{
    const l=await api('/api/install/log?name='+name);
    document.getElementById('out').textContent=l;
    try{
      const p=JSON.parse(await api('/api/install/progress?name='+name));
      if(p && p.percent!==null && p.percent!==undefined && p.percent>0){
        bar.style.display='block'; label.style.display='block';
        fill.style.width=Math.max(2,Math.min(100,p.percent))+'%';
        const ph=p.phase?(L['inst.phase_'+p.phase]||''):'';
        label.textContent=(ph?ph+' — ':'')+Number(p.percent).toFixed(1)+' %';
      }
    }catch(e){}
    if(l.startsWith('[fertig]')){
      clearInterval(t);
      if(bar && bar.style.display==='block'){
        fill.style.width='100%';
        label.textContent=(L['inst.phase_done']||'fertig')+' — 100 %';
        setTimeout(()=>{bar.style.display='none';label.style.display='none';},6000);
      }
    }
  },2000);
}

let _polyPanelInfo=null;
async function checkPolyPanel(){
  try{ _polyPanelInfo=JSON.parse(await api('/api/selfupdate')); }catch(e){ return; }
  const b=document.getElementById('verbtn');
  if(!b||!_polyPanelInfo||!_polyPanelInfo.ok) return;
  if(!_polyPanelInfo.update){
    b.textContent='PolyPanel '+_polyPanelInfo.installed+' · '+L['self.current_build']; b.className='';
    b.disabled=true; b.style.cursor='default'; b.style.opacity='.7';
    b.title=L['self.up_to_date'];
    return;
  }
  else if(_polyPanelInfo.available && _polyPanelInfo.available!==_polyPanelInfo.installed){
    b.textContent='PolyPanel update: '+_polyPanelInfo.installed+' → '+_polyPanelInfo.available;
    b.className='badge on';
  } else {
    // gleiche Version, nur neuer Commit: nur ein Hinweis, nicht klickbar
    b.textContent='PolyPanel '+_polyPanelInfo.installed+' · '+L['self.new_build'];
    b.className='badge';
    b.disabled=true; b.style.cursor='default'; b.style.opacity='.7';
    b.title=L['self.build_only'];
    return;
  }
  b.disabled=false; b.style.cursor=''; b.style.opacity='';

  b.title = _polyPanelInfo.update ? L['self.click_update'] : L['self.up_to_date'];
}

function closeModal(){ const m=document.getElementById('modal'); if(m) m.classList.remove('on'); }
function _links(html){
  let out='', i=0;
  while(true){
    const a=html.indexOf('[', i), b=html.indexOf('](', a+1), c=html.indexOf(')', b+2);
    if(a<0||b<0||c<0){ out+=html.slice(i); break; }
    const label=html.slice(a+1,b);
    if(b-a>80 || label.indexOf('<')>=0){ out+=html.slice(i,a+1); i=a+1; continue; }
    out+=html.slice(i,a);
    out+='<a href="'+html.slice(b+2,c)+'" target="_blank">'+html.slice(a+1,b)+'</a>';
    i=c+1;
  }
  return out;
}
function _mdToHtml(text){
  const esc=s=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;');
  const out=[];
  for(const raw of text.split(String.fromCharCode(10))){
    const line=raw.split(String.fromCharCode(13)).join('');
    if(line.startsWith('### ')) out.push('<h4 style="margin:10px 0 4px">'+esc(line.slice(4))+'</h4>');
    else if(line.startsWith('## ')) out.push('<h3 style="margin:14px 0 6px;color:var(--acc)">'+esc(line.slice(3))+'</h3>');
    else if(line.startsWith('# ')) out.push('<h3 style="margin:0 0 8px">'+esc(line.slice(2))+'</h3>');
    else if(line.startsWith('  - ')||line.startsWith('    - ')) out.push('<div class="meta" style="padding-left:26px">• '+esc(line.trim().slice(2))+'</div>');
    else if(line.startsWith('- ')) out.push('<div style="margin:3px 0 3px 12px">• '+esc(line.slice(2))+'</div>');
    else if(line.trim()==='') out.push('<div style="height:4px"></div>');
    else out.push('<div class="meta">'+esc(line)+'</div>');
  }
  let html=out.join('');
  const bold=html.split('**');
  html=bold.map((part,i)=> (i%2) ? '<b>'+part+'</b>' : part).join('');
  const code=html.split('`');
  html=code.map((part,i)=> (i%2) ? '<code>'+part+'</code>' : part).join('');
  html=_links(html);
  return html;
}
async function openChangelog(){
  const box=document.getElementById('mbody');
  box.innerHTML='<div class="meta">'+L['common.loading']+'</div>';
  document.getElementById('modal').classList.add('on');
  let d;
  try{ d=JSON.parse(await api('/api/changelog?lang='+encodeURIComponent(L.lang||'de'))); }
  catch(e){ box.innerHTML='<div class="meta">'+L['mods.search_failed']+'</div>'; return; }
  if(!d.ok){ box.innerHTML='<div class="meta">'+(d.error||'')+'</div>'; return; }
  box.innerHTML='<div style="max-height:64vh;overflow:auto;padding-right:6px">'+_mdToHtml(d.text)+'</div>'+
    (d.url?('<div style="margin-top:10px"><a href="'+d.url+'" target="_blank">'+L['self.on_github']+'</a></div>'):'');
}
async function polyPanelUpdate(){
  if(!_polyPanelInfo){ await checkPolyPanel(); }
  if(!_polyPanelInfo || !_polyPanelInfo.ok) return;
  if(!_polyPanelInfo.update){ alert(L['self.up_to_date']); return; }
  let notes='';
  try{ const n=JSON.parse(await api('/api/selfupdate/notes?v='+encodeURIComponent(_polyPanelInfo.available)));
       if(n.ok && n.text) notes=String.fromCharCode(10,10)+n.text.slice(0,900); }catch(e){}
  if(!confirm(L['self.confirm'].replace('{v}', _polyPanelInfo.available)+notes)) return;
  const b=document.getElementById('verbtn');
  b.textContent='…';
  let res=null;
  try{ res=JSON.parse(await api('/api/selfupdate',{method:'POST'})); }
  catch(e){ alert(L['self.failed']+' '+(e&&e.message?e.message:'')); await checkPolyPanel(); return; }
  if(res && res.ok===false){
    alert(L['self.failed']+' '+(res.error||''));
    await checkPolyPanel();
    return;
  }
  alert(L['self.done']);
  setTimeout(()=>location.reload(), 4000);
}
applyLang(); load(); loadHost(); checkPolyPanel(); setInterval(load,3000); setInterval(loadHost,3000);
</script>""" + FOOTER + """
<div id="plModal" class="plModal"><div class="plBox">
  <div class="row" style="justify-content:space-between">
    <b id="plTitle">Spieler</b>
    <button onclick="closePlayers()">×</button>
  </div>
  <div id="plBody" class="plBody">…</div>
</div></div>
<script>
function closePlayers(){ document.getElementById('plModal').classList.remove('on'); }
function plRow(inst, pl){
  const n = String(pl.name).replace(/</g, '&lt;');
  const id = String(pl.steamid);
  // Aktionen ueber data-Attribute: keine verschachtelten Quotes im HTML
  return '<tr><td>'+n+'</td><td class="mono">'+id+'</td><td class="plAct">'+
    '<button data-inst="'+inst+'" data-eos="'+id+'" data-act="kick">'+L['dash.kick']+'</button>'+
    '<button class="danger" data-inst="'+inst+'" data-eos="'+id+'" data-act="ban">'+L['dash.ban']+'</button>'+
    '<button data-inst="'+inst+'" data-eos="'+id+'" data-act="unban">'+L['dash.unban']+'</button>'+
    '</td></tr>';
}
async function showPlayers(inst){
  const box=document.getElementById('plModal'), body=document.getElementById('plBody');
  document.getElementById('plTitle').textContent=L['dash.players']+' · '+inst;
  body.innerHTML='…'; box.classList.add('on');
  let list=[];
  try{ list=JSON.parse(await api('/api/players?name='+encodeURIComponent(inst))); }
  catch(e){ body.textContent=String(e); return; }
  if(!list.length){ body.innerHTML='<span style="color:var(--dim)">– '+L['inst.no_players']+' –</span>'; return; }
  body.innerHTML='<table class="plTable"><thead><tr><th>'+L['dash.players']+'</th><th>'+L['dash.eos_id']+'</th><th></th></tr></thead><tbody>'+
    list.map(function(pl){ return plRow(inst, pl); }).join('')+'</tbody></table>';
}
async function plAct(inst, eos, action){
  if(action==='ban' && !confirm(L['dash.ban_confirm'].replace('{id}', eos))) return;
  try{
    const r=await api('/api/player/action?name='+encodeURIComponent(inst)+'&steamid='+encodeURIComponent(eos)+'&action='+action,{method:'POST'});
    document.getElementById('plBody').insertAdjacentHTML('afterbegin','<div class="plMsg">'+action+': '+(r||'ok')+'</div>');
    setTimeout(function(){ showPlayers(inst); }, 1200);
  }catch(e){ alert(String(e)); }
}
document.addEventListener('click', function(ev){
  const b=ev.target.closest('button[data-act]');
  if(b) plAct(b.dataset.inst, b.dataset.eos, b.dataset.act);
});
</script>
</body></html>"""

INST = """<!doctype html><html lang="__LANG__"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>PolyPanel · __NAME__</title>
<style>""" + SHARED_CSS + """
body:not([data-game="ark"]) .ark-only{display:none !important}
body:not([data-game="ark"]):not([data-game="arkse"]) .arkcmd{display:none !important}
body:not([data-game="ark"]):not([data-game="arkse"]) .tab-mods > *:not(h2):not(#mods-nonark):not(#mods-installed){display:none !important}
body[data-game="ark"] #mods-nonark{display:none !important}
body[data-game="ark"] #mods-installed,body[data-game="arkse"] #mods-installed{display:none !important}
</style></head><body data-game="__GAME__">
<canvas id="bg"></canvas>
<div class="modal" id="modal" onclick="if(event.target.id==='modal')closeModal()">
  <div class="mbox">
    <button class="close" onclick="closeModal()">×</button>
    <div id="mbody">…</div>
  </div>
</div>
<header>
  <a href="/?token=__TOK__" style="font-size:15px;letter-spacing:.18em;color:var(--acc)">PolyPanel</a>
  <a href="/?token=__TOK__" style="margin-left:6px"><button data-t="common.back_dashboard">← Dashboard</button></a>
  <span class="badge" id="st">…</span><span class="badge" id="rd">…</span>
  <span class="badge">__NAME__</span><span class="badge" id="upd" role="button" tabindex="0">UPDATE ?</span>
  <button onclick="toggleLang()" id="langbtn" style="padding:2px 8px">EN</button>""" + HEADER_ICONS + """
</header>
<div class="tabs">
  <button class="on" data-tab="overview" onclick="showTab('overview',this)" data-t="tabs.overview">Übersicht</button>
  <button data-tab="settings" onclick="showTab('settings',this)" data-t="tabs.settings">Einstellungen</button>
  <button data-tab="mods" onclick="showTab('mods',this)" data-t="tabs.mods">Mods</button>
  <button data-tab="server" onclick="showTab('server',this)" data-t="tabs.manage">Verwaltung</button>
</div>
<main>
  <section class="tab tab-overview on wide" id="logsec"><h2 data-t="inst.log">Server-Log</h2><pre id="log">…</pre></section>

  <section class="tab tab-overview on"><h2 data-t="inst.commands">Befehle</h2>
    <div id="cmds" class="arkcmd"></div>
    <input id="cmd" data-tp="inst.rcon_free" placeholder="RCON"
      onkeydown="if(event.key==='Enter')rcon()" style="margin-top:10px">
    <div class="row"><button onclick="rcon()" data-t="common.send">Senden</button></div>
    <pre id="out">–</pre>
  </section>

  <section class="tab tab-overview on"><h2 data-t="inst.players">Spieler</h2><div id="players">…</div></section>

  <section class="tab tab-server ark-only"><h2 data-t="wl.title">Whitelist &amp; Bans</h2>
    <div class="row" style="margin-bottom:8px">
      <button id="wlbtn" onclick="toggleWl()">Whitelist …</button>
      <span class="meta" id="wlcount"></span>
    </div>
    <input id="pid" data-tp="wl.id_ph" placeholder="ID" onkeydown="if(event.key==='Enter')addWl()">
    <div class="row">
      <button onclick="addWl()" data-t="wl.add">Auf Whitelist</button>
      <button class="danger" onclick="banId()" data-t="wl.ban">Bannen</button>
    </div>
    <div class="meta" style="margin:10px 0 2px">Whitelist</div>
    <div id="wllist">…</div>
    <div class="meta" style="margin:10px 0 2px" data-t="wl.banned_list">Gebannt (über PolyPanel)</div>
    <div id="banlist">…</div>
    <pre id="wlmsg">–</pre>
  </section>

  <section class="tab tab-mods"><h2 data-t="tabs.mods">Mods</h2>
    <div id="mods-installed">
      <div class="row" style="align-items:center;margin:0 0 6px">
        <b data-t="mods.installed">Installierte Mods</b>
        <span class="meta" id="mods-installed-count"></span>
        <span class="meta" id="mods-installed-path">…</span>
        <button onclick="loadInstalledMods()" data-t="common.refresh">Aktualisieren</button>
      </div>
      <div id="mods-installed-list">…</div>
    </div>
    <div id="mods-nonark" style="display:none">
      <p class="hint" data-t="mods.local_hint">Dieses Spiel wird nicht über CurseForge verwaltet. Mods legst du direkt im Ordner ab – PolyPanel zeigt dir, was dort liegt.</p>
      <p class="hint" data-t="mods.search_how">So funktioniert die Suche: sie filtert die 50 meistgeladenen Mods (Nexus) und passende GitHub-Repos nach deinem Begriff – kurze Wörter genügen, z. B. „ui", „trader", „vehicle". Eine echte Volltextsuche bietet nur die Nexus-Webseite.</p>
      <div class="row" style="margin:10px 0">
        <input id="modq" data-tp="mods.search_ph" placeholder="Mod suchen" style="flex:1"
          oninput="suggestLocalMods()" onkeydown="if(event.key==='Enter'){clearTimeout(_modTimer);searchLocalMods()}" autocomplete="off">
        <button onclick="searchLocalMods()" data-t="mods.search">Suchen</button>
        <button onclick="loadLocalMods()" data-t="common.refresh">Aktualisieren</button>
      </div>
      <div id="modhits-local"></div>
      <div id="nexusbox" style="display:none;margin-top:14px">
        <div class="setrow"><label><b>NexusMods-API-Key</b>
          <small><span data-t="mods.nexus_hint">Persönlicher Key — ganz unten auf dieser Seite:</span>
            <a href="https://www.nexusmods.com/settings/api-keys" target="_blank" rel="noopener">nexusmods.com/settings/api-keys</a></small></label>
          <input id="nexuskey" type="password" placeholder="…"></div>
        <div class="row" style="align-items:center">
          <button onclick="saveNexusKey()" data-t="common.save">Speichern</button>
          <span id="nexusstate" class="badge">…</span>
        </div>
      </div>
    </div>
    <div id="mods">…</div>
    <div class="row" style="margin-top:8px">
      <input id="modid" data-tp="mods.search_ph" placeholder="Mod suchen oder ID eingeben"
        oninput="suggestMods()" onkeydown="if(event.key==='Enter')searchMods()"
        autocomplete="off" style="flex:1">
      <button onclick="searchMods()" data-t="mods.search">Suchen</button>
      <button onclick="addMod()" data-t="common.add">Hinzufügen</button>
    </div>
    <div class="row"><span class="meta" id="keystate"></span></div>
    <div class="hint" data-t="mods.search_hint">Die CurseForge-API liefert höchstens 50 Treffer pro Abfrage.
      Für mehr Ergebnisse den Begriff eingrenzen.</div>
    <div id="modhitsum"></div>
    <div id="modhits"></div>
    <div class="row"><span class="meta" id="modsize"></span></div>
    <div class="setrow" style="margin-top:10px">
      <label><b data-t="mods.key">CurseForge-API-Key</b>
        <small><span data-t="mods.key_hint">optional - ohne Key ist die Suche unzuverlaessig</span>
          <a href="https://console.curseforge.com" target="_blank" rel="noopener">console.curseforge.com</a></small></label>
      <input id="cfkey" type="password" placeholder="…">
    </div>
    <div class="row"><button onclick="saveKey()" data-t="common.save">Speichern</button>
      <span class="meta" id="cfkeymsg"></span></div>
    <pre id="modout" style="margin-top:8px">–</pre>
  </section>

  <section class="tab tab-settings ark-only"><h2 data-t="cl.title">Cluster</h2>
    <div class="meta" data-t="cl.hint">Mehrere Karten teilen sich Spieler, Dinos und Gegenstände, wenn sie dieselbe
      Cluster-ID und dasselbe Verzeichnis benutzen. Ohne eigene Angabe gilt: ID = Instanzname,
      Verzeichnis = &lt;instanz&gt;/clusters (also kein Teilen).</div>
    <div class="setrow" style="margin-top:8px">
      <label><b data-t="cl.id">Cluster-ID</b><small data-t="cl.id_hint">identisch auf allen Karten, die geteilt werden sollen</small></label>
      <input id="clid" placeholder="z. B. Drachenbande">
    </div>
    <div class="setrow">
      <label><b data-t="cl.dir">Cluster-Verzeichnis</b><small data-t="cl.dir_hint">gemeinsamer Pfad für alle Karten, leer = nur diese Instanz</small></label>
      <input id="cldir" placeholder="z. B. /home/ronny/arkcluster">
    </div>
    <div class="setrow">
      <label><b data-t="cl.filter">Übertragungen ohne Filterprüfung</b><small data-t="cl.filter_hint">an = -NoTransferFromFiltering wird gesetzt (übliche Einstellung für Cluster)</small></label>
      <div class="bool"><input type="checkbox" id="clfilt" checked></div>
    </div>
    <div class="row" style="margin-top:6px">
      <button class="primary" onclick="saveCluster()" data-t="common.save">Speichern</button>
      <span class="meta" id="clmsg"></span>
    </div>
  </section>

  <section class="tab tab-settings"><h2 data-t="set.gui">Einstellungen (GUI)</h2>
    <div id="settings">lädt …</div>
    <div class="row" style="margin-top:10px">
      <button class="primary" onclick="saveSettings()" data-t="set.save_changes">Änderungen speichern</button>
      <span class="meta" id="setmsg"></span>
    </div>
  </section>

  <section class="tab tab-settings ark-only"><h2 data-t="set.raw">INI direkt bearbeiten</h2>
    <select id="cfgfile" onchange="loadCfg()">
      <option value="gus">GameUserSettings.ini</option>
      <option value="game">Game.ini</option>
    </select>
    <textarea id="cfgtext"></textarea>
    <div class="row" style="margin-top:6px"><button onclick="saveCfg()" data-t="common.save">Speichern</button>
      <span class="meta" id="cfgmsg"></span></div>
  </section>

  <section class="tab tab-server"><h2 data-t="snap.title">Instanz-Snapshot (Rollback)</h2>
    <div class="meta" data-t="snap.hint_text">Komplette Kopie der Serverdateien inklusive Mods – für den Fall, dass ein ARK-Update
      die Installation zerschießt. Ein Welt-Backup hilft dort nicht, weil SteamCMD immer die neue
      Programmversion liefert. Platzbedarf: ca. 12 GB pro Snapshot.</div>
    <div id="snaps" style="margin-top:10px">…</div>
    <div class="row" style="margin-top:8px">
      <button class="primary" onclick="makeSnap()" data-t="snap.create">Snapshot erstellen</button>
      <span class="meta" id="snapmsg"></span>
    </div>
    <div class="setrow"><label><b data-t="snap.times">Snapshot-Uhrzeiten</b>
      <small data-t="snap.times_hint">hint</small></label>
      <input id="snapTimes" type="text" placeholder="04:00"></div>
    <div class="setrow" style="margin-top:10px"><label><b data-t="snap.keep">Auto-Snapshots behalten</b>
      <small data-t="snap.keep_hint">hint</small></label>
      <input id="snapKeep" type="number" min="1" max="40" placeholder="3"></div>
  </section>

  <section class="tab tab-server"><h2 data-t="notify.title">Benachrichtigungen (Discord)</h2>
    <div class="meta" data-t="notify.hint">Webhook-Adresse aus Discord (Servereinstellungen → Integrationen → Webhooks).
      Meldungen: Absturz, Hänger-Neustart, neues Server-Update, Backup-Fehler.</div>
    <div class="setrow" style="margin-top:8px">
      <label><b data-t="notify.url">Webhook-URL</b><small data-t="notify.url_hint">leer = keine Meldungen</small></label>
      <input id="hookurl" data-tp="notify.url_ph" placeholder="https://discord.com/api/webhooks/…">
    </div>
    <div class="row" style="margin-top:8px">
      <button class="primary" onclick="saveHook()" data-t="common.save">Speichern</button>
      <button onclick="testHook()" data-t="notify.test">Test senden</button>
      <span class="meta" id="hookmsg"></span>
    </div>
  </section>

  <section class="tab tab-server wide"><h2 data-t="sched.title">Zeitplan</h2>
    <div id="tasklist"></div>
    <div class="row" style="margin:6px 0 12px">
      <button onclick="addTask()" data-t="sched.add">Aufgabe hinzufügen</button>
      <button class="primary" onclick="saveTasks()" data-t="common.save">Speichern</button>
      <span class="meta" id="taskmsg"></span>
    </div>
    <div class="meta" data-t="sched.legend" style="margin:0 0 10px">Uhrzeit 05:00, Tage leer = täglich.
      Aktionen laufen im Supervisor; Neustart nutzt die Vorwarnung unten.</div>
    <div class="setrow"><label><b data-t="sched.restart_times">Neustart-Uhrzeiten (alt)</b>
      <small data-t="sched.restart_hint">hint</small></label>
      <input id="schedRestart" type="text" placeholder="05:00,17:00"></div>
    <div class="setrow"><label><b data-t="sched.warn">Vorwarnung vor Neustart</b>
      <small data-t="sched.warn_hint">hint</small></label>
      <input id="schedWarn" type="number" placeholder="5"></div>
    <div class="setrow"><label><b data-t="sched.keep">Backups behalten</b>
      <small data-t="sched.keep_hint">hint</small></label>
      <input id="schedKeep" type="number" placeholder="10"></div>
    <div class="row" style="margin-top:10px"><button onclick="saveSchedule()" data-t="common.save">Speichern</button></div>
    <pre id="schedmsg">–</pre>
  </section>


</main>
<script>""" + BG_JS + """
const NAME='__NAME__';
const L=__LANGJSON__;
async function toggleLang(){
  const next = (L.lang === 'de') ? 'en' : 'de';
  try{ await fetch('/api/lang?set=' + next + '&token=' + encodeURIComponent(T), {method:'POST'}); }
  catch(e){ alert(L['msg.lang_failed'] + ' ' + e); return; }
  location.reload();
}
function applyLang(){
  document.querySelectorAll('[data-t]').forEach(e=>{const k=e.dataset.t;if(L[k])e.textContent=L[k];});
  document.querySelectorAll('[data-tp]').forEach(e=>{const k=e.dataset.tp;if(L[k])e.placeholder=L[k];});
  const lb=document.getElementById('langbtn'); if(lb) lb.textContent=(L.lang==='de')?'EN':'DE';
}
const T=new URLSearchParams(location.search).get('token')||'';

// Klicks nicht verlieren: waehrend der Knopf gedrueckt ist, den DOM nicht neu bauen.
// Ohne das ersetzt der 3-5-s-Poll die Karten/Listen genau unter dem Mauszeiger und der
// Klick landet im Nichts - das Symptom "reagiert erst beim zweiten Klick".
document.addEventListener('pointerdown', () => { window.__pressed = 1; }, true);
['pointerup', 'pointercancel'].forEach(function (t) {
  document.addEventListener(t, () => { window.__pressed = 0; }, true);
});
window.addEventListener('blur', () => { window.__pressed = 0; });

const api=(p,o)=>fetch(p+(p.includes('?')?'&':'?')+'token='+encodeURIComponent(T)+'&name='+NAME,o).then(r=>r.text());
async function refresh(){
  if(window.__pressed){ setTimeout(refresh, 400); return; }   // Klick laeuft noch
  try{
    const s=JSON.parse(await api('/api/status'));
    const st=document.getElementById('st'); st.textContent=s.running?L['status.running']:L['status.off'];
    st.className='badge '+(s.running?'on':'off');
    const rd=document.getElementById('rd'); rd.textContent=s.ready?L['status.ready']:L['status.starting'];
    rd.className='badge '+(s.ready?'on':'');
    const infoEl=document.getElementById('info');
    if(infoEl){ const rows=[['PID',s.pid??'–'],['RCON',s.rcon??'–']];
      infoEl.innerHTML=rows.map(([k,v])=>`<span>${k}</span><span>${v}</span>`).join(''); }
  }catch(e){}
  try{ const _l=document.getElementById('log'); _l.textContent=await api('/api/logs?n=150');
       const _end=()=>{_l.scrollTop=_l.scrollHeight;};
       _end(); requestAnimationFrame(()=>{_end(); setTimeout(_end,60);}); }catch(e){}
  try{
    const pl=JSON.parse(await api('/api/players'));
    document.getElementById('players').innerHTML=pl.length?pl.map(p=>
      `<div class="p"><span><b>${p.name}</b><br><small>${p.steamid}</small></span>
       <span class="row">
         <button onclick="pa('${p.steamid}','kick')">${L['inst.kick']}</button>
         <button class="danger" onclick="pa('${p.steamid}','ban')">${L['inst.ban']}</button>
         <button onclick="pa('${p.steamid}','whitelist')">${L['inst.whitelist']}</button>
         <button onclick="give('${p.steamid}')">${L['inst.item']}</button>
       </span></div>`).join('')
      :'<span style="color:var(--dim)">– '+L['inst.no_players']+' –</span>';
  }catch(e){}
}
window.LOCAL_ACT = window.LOCAL_ACT || {};
async function act(name,what){
  window.LOCAL_ACT[name]={what:what,ts:Date.now()};   // sofort sperren, nicht erst nach dem Refresh
  load();
  try{ await api('/api/'+what+'?name='+name,{method:'POST'}); }
  catch(e){ alert((L['inst.action_failed']||'Aktion fehlgeschlagen:')+'\\n\\n'+(e&&e.message?e.message:e)); return; }
  setTimeout(refresh,1200);
}
async function updCheck(){
  try{ const u=JSON.parse(await api('/api/update'+(window.__updForce?'?refresh=1':''))); window.__updForce=false; const b=document.getElementById('upd');
    if(u.installed==null || u.available==null){
      b.style.display=''; b.className='badge';
      b.textContent=L['status.update_unknown'];
      b.title=(u.reason==='not_installed')?L['status.reason_not_installed']:L['status.reason_steam_unreachable'];
      b.style.cursor='pointer';
      b.onclick=()=>{window.__updForce=true;updCheck();};
      b.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();window.__updForce=true;updCheck();}};
      return;
    }
    b.style.display='';
    if(u.up_to_date){
      // Build ist aktuell: Klick prüft erneut
      b.textContent=L['status.current']+' '+u.installed; b.className='badge on';
      b.title=L['status.hint_current']; b.style.cursor='pointer';
      b.onclick=()=>{window.__updForce=true;updCheck();}; b.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();updCheck();}};
    } else {
      // Update verfuegbar: Klick startet es (mit Rueckfrage) - auch hier auf der Instanzseite
      b.textContent=L['status.update_available']+' '+u.installed+'→'+u.available; b.className='badge off';
      b.title=L['status.hint_update']; b.style.cursor='pointer';
      b.onclick=doUpdate; b.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();doUpdate();}};
    }
  }catch(e){}
}
const JOIN_NL=String.fromCharCode(10);
let UPDATE_POLL=null;
async function updateProgress(){
  try{
    const s=JSON.parse(await api('/api/update/progress'));
    const out=document.getElementById('out');
    if(out && s.log && s.log.length){ out.textContent=s.log.join(JOIN_NL); }
    if(!s.active){
      if(UPDATE_POLL){ clearInterval(UPDATE_POLL); UPDATE_POLL=null; setTimeout(refresh,1500); }
    }
  }catch(e){}
}
async function doUpdate(){
  if(!confirm(L['msg.confirm_update']))return;
  const out=document.getElementById('out');
  if(out) out.textContent=L['msg.update_started'];
  if(!UPDATE_POLL) UPDATE_POLL=setInterval(updateProgress, 2000);
  let res;
  try{ res=await api('/api/update',{method:'POST'}); }
  catch(e){ if(out) out.textContent=L['msg.update_failed']+' '+(e&&e.message?e.message:''); }
  if(typeof res==='string' && out) out.textContent=res;
  updateProgress();
  setTimeout(refresh, 3000);
}
async function rcon(){ const c=document.getElementById('cmd').value.trim(); if(!c)return;
  document.getElementById('out').textContent=await api('/api/rcon?cmd='+encodeURIComponent(c),{method:'POST'}); }
let CMDS=null;
async function loadCmds(){ if(CMDS)return CMDS; CMDS=JSON.parse(await api('/api/commands')); return CMDS; }
async function renderCmds(){
  const list=await loadCmds(); const groups={};
  list.forEach(c=>{(groups[c.group]=groups[c.group]||[]).push(c);});
  document.getElementById('cmds').innerHTML=Object.entries(groups).map(([g,items])=>
    `<div style="margin-bottom:8px"><div style="color:var(--dim);font-size:10px;letter-spacing:.14em;
      text-transform:uppercase;margin:6px 0 4px">${g}</div>
     <div class="row">${items.map(c=>
       `<button class="${c.danger?'danger':''}" title="${c.note||''}"
          onclick="runCmd('${c.id}')">${c.label}</button>`).join('')}</div></div>`).join('');
}
async function runCmd(id){
  const c=(await loadCmds()).find(x=>x.id===id); if(!c)return;
  const params=new URLSearchParams({id:id});
  for(const [name,question,def] of c.args){
    const v=prompt(question,def); if(v===null)return; params.set(name,v);
  }
  if(c.confirm&&!confirm((c.note||c.label)+String.fromCharCode(10,10)+'Wirklich ausfuehren?'))return;
  document.getElementById('out').textContent='…';
  document.getElementById('out').textContent=await api('/api/command?'+params.toString(),{method:'POST'});
  setTimeout(refresh,1500);
}
function modRow(m, active){
  const label = m.state==='valid' ? L['mods.loaded'] : (m.state==='cooked' ? L['mods.old_engine'] : L['mods.unknown']);
  const sub = `${m.id}${active?' · '+label+(m.issue?' · '+(L['mods.issue_'+m.issue]||m.issue):''):' · '+L['mods.on_disk']}`;
  const thumb = m.thumbnail
    ? `<img class="thumb" src="${m.thumbnail}" alt="" loading="lazy">`
    : '<div class="thumb"></div>';
  const actions = active
    ? `<button onclick="modInfo('${m.id}')">${L['common.info']}</button>
       <button onclick="delModFiles('${m.id}')">${L['common.delete']}</button>
       <button class="danger" onclick="delMod('${m.id}')">${L['common.disable']}</button>`
    : `<button onclick="modInfo('${m.id}')">Info</button>
       <button class="primary" onclick="enableMod('${m.id}')">${L['common.enable']}</button>
       <button class="danger" onclick="delModFiles('${m.id}')">${L['common.delete']}</button>`;
  return `<div class="p"><span class="mrow">${thumb}
      <span class="txt"><b>${m.title||m.name||('Mod '+m.id)}</b>${m.outdated?' <span class="badge warn">'+L['mods.outdated']+'</span>':''}
      <small>${sub}${m.outdated&&m.age_days!=null?(' · '+L['mods.updated_ago']+' '+m.age_days+' '+L['mods.days']):''}${m.summary?(' · '+m.summary):''}</small></span></span>
    <span class="row">${actions}</span></div>`;
}
async function modInfo(id){
  document.getElementById('mbody').innerHTML='lädt …';
  document.getElementById('modal').classList.add('on');
  const m=JSON.parse(await api('/api/mod/meta?id='+id));
  const img=m.thumbnail?`<img class="big" src="${m.thumbnail}" alt="">`:'';
  const cats=(m.categories||[]).join(', ');
  document.getElementById('mbody').innerHTML=`${img}
    <h3>${m.title||('Mod '+id)}</h3>
    <div class="meta">${id}${m.downloads?(' · '+m.downloads.toLocaleString('de-DE')+' Downloads'):''}${cats?(' · '+cats):''}</div>
    <div class="desc">${(m.description||m.summary||L['mods.no_desc']).replace(/</g,'&lt;')}</div>
    ${m.url?`<div style="margin-top:12px"><a href="${m.url}" target="_blank">Auf CurseForge öffnen</a></div>`:''}`;
}
function closeModal(){ document.getElementById('modal').classList.remove('on'); }
function showTab(name, btn){
  document.querySelectorAll('.tab').forEach(el=>el.classList.toggle('on', el.classList.contains('tab-'+name)));
  document.querySelectorAll('.tabs button').forEach(b=>b.classList.remove('on'));
  if(btn) btn.classList.add('on');
  try{ localStorage.setItem('PolyPanel.tab', name); if(history.replaceState) history.replaceState(null,'','#'+name); }catch(e){}
  if(name==='mods'){
    if(!['ark','arkse'].includes(document.body.dataset.game)) loadInstalledMods();   // ARK hat seine Liste darunter
    if(document.body.dataset.game!=='ark'){
      const pane=document.getElementById('mods-nonark');
      if(pane) pane.style.display='';
      loadLocalMods();
      const nb=document.getElementById('nexusbox');
      if(nb) nb.style.display = (document.body.dataset.game==='7d2d') ? '' : 'none';
    }
  }
  if(name==='overview'){ const l=document.getElementById('log');
    if(l){ requestAnimationFrame(()=>{ l.scrollTop=l.scrollHeight; }); } }
}
function restoreTab(){
  let t='';
  try{ t = (location.hash||'').replace('#','') || localStorage.getItem('PolyPanel.tab') || ''; }catch(e){}
  const known=['overview','settings','mods','server'];
  if(!known.includes(t)) t='overview';
  const b=document.querySelector('.tabs button[data-tab="'+t+'"]');
  if(b) showTab(t, b); else showTab('overview', document.querySelector('.tabs button'));
}
window.addEventListener('hashchange', ()=>{
  const t=(location.hash||'').replace('#','');
  if(['overview','settings','mods','server'].includes(t)){
    const b=document.querySelector('.tabs button[data-tab="'+t+'"]');
    if(b) showTab(t, b);
  }
});
let SETTINGS=[];
let TASKS=[];
const TASK_ACTS=['restart','start','stop','update','backup','saveworld','dinowipe','broadcast','rcon'];
const TASK_DAYS=[1,2,3,4,5,6,7];
function renderTasks(){
  const box=document.getElementById('tasklist'); if(!box) return;
  if(!TASKS.length){ box.innerHTML='<div class="meta" data-empty="1">'+(L['sched.empty']||'-')+'</div>'; return; }
  box.innerHTML=TASKS.map((t,i)=>{
    const needArg=(t.action==='broadcast'||t.action==='rcon');
    const days=TASK_DAYS.map(d=>`<label class="daybox" title="${L['sched.day'+d]||d}">
        <input type="checkbox" data-i="${i}" data-day="${d}" ${(t.days||[]).includes(d)?'checked':''}>${L['sched.d'+d]||d}</label>`).join('');
    return `<div class="taskrow" data-i="${i}">
      <select data-i="${i}" data-f="action">${TASK_ACTS.map(a=>
        `<option value="${a}" ${t.action===a?'selected':''}>${L['sched.a.'+a]||a}</option>`).join('')}</select>
      <input type="time" data-i="${i}" data-f="time" value="${t.time||'05:00'}">
      <span class="dayboxes">${days}</span>
      <input data-i="${i}" data-f="arg" placeholder="${L['sched.arg_ph']||''}"
             value="${(t.arg||'').replace(/"/g,'&quot;')}" ${needArg?'':'disabled'} style="flex:1;min-width:80px">
      <label class="daybox"><input type="checkbox" data-i="${i}" data-f="on" ${t.on!==false?'checked':''}>${L['sched.on']||'an'}</label>
      <button class="danger" onclick="delTask(${i})">×</button>
    </div>`;
  }).join('');
  box.querySelectorAll('[data-f]').forEach(el=>{
    const ev=(el.type==='checkbox'||el.tagName==='SELECT')?'change':'input';
    el.addEventListener(ev,()=>collectTasks());
  });
  box.querySelectorAll('[data-day]').forEach(el=>el.addEventListener('change',()=>collectTasks()));
}
function collectTasks(){
  const box=document.getElementById('tasklist');
  box.querySelectorAll('.taskrow').forEach(row=>{
    const i=Number(row.dataset.i); if(!TASKS[i]) return;
    row.querySelectorAll('[data-f]').forEach(el=>{
      const f=el.dataset.f;
      if(el.type==='checkbox') TASKS[i][f]=el.checked;
      else TASKS[i][f]=el.value;
    });
    TASKS[i].days=[...row.querySelectorAll('[data-day]')].filter(c=>c.checked).map(c=>Number(c.dataset.day));
  });
  // Argumentfeld je nach Aktion freischalten
  box.querySelectorAll('.taskrow').forEach(row=>{
    const i=Number(row.dataset.i), sel=row.querySelector('[data-f="action"]'), arg=row.querySelector('[data-f="arg"]');
    if(sel&&arg) arg.disabled=!(sel.value==='broadcast'||sel.value==='rcon');
  });
}
function addTask(){ collectTasks(); TASKS.push({id:'t'+Date.now(),action:'restart',time:'05:00',days:[],arg:'',on:true}); renderTasks(); }
function delTask(i){ collectTasks(); TASKS.splice(i,1); renderTasks(); }
async function saveTasks(){
  collectTasks();
  const msg=document.getElementById('taskmsg');
  try{
    const r=await fetch('/api/tasks?name='+encodeURIComponent(NAME)+'&token='+encodeURIComponent(T),
      {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tasks:TASKS})});
    const d=JSON.parse(await r.text());
    TASKS=d.tasks||TASKS; renderTasks();
    msg.textContent=L['sched.saved']||'ok';
  }catch(e){ msg.textContent=String(e); }
}
async function loadCluster(){
  try{
    const c=JSON.parse(await api('/api/cluster'));
    const id=document.getElementById('clid'), dir=document.getElementById('cldir'), f=document.getElementById('clfilt');
    // Vorgabewerte stehen direkt im Feld, damit man den Pfad sieht und nur aendern muss
    if(id){ id.value = c.cluster_id || ''; id.placeholder = c.cluster_id || ''; }
    if(dir){ dir.value = c.cluster_dir || ''; dir.placeholder = c.cluster_dir || ''; }
    if(f) f.checked = !!c.transfer_filtering;
  }catch(e){}
}
async function saveCluster(){
  const id=document.getElementById('clid').value.trim();
  const dir=document.getElementById('cldir').value.trim();
  const f=document.getElementById('clfilt').checked ? '1' : '0';
  const msg=document.getElementById('clmsg');
  try{
    msg.textContent = await api('/api/cluster?cluster_id='+encodeURIComponent(id)+
      '&cluster_dir='+encodeURIComponent(dir)+'&transfer_filtering='+f, {method:'POST'});
    loadCluster();
  }catch(e){ msg.textContent=String(e); }
}
const SETGROUP_ORDER=['srv','play','pvp','struct','dino','transfer','hud','motd','game',
               'server','netz','welt','spieler','weitere'];
function _setField(v){
  const i=SETTINGS.indexOf(v);
  let field;
  if(v.type==='bool'){
    const on=(v.value||'').toLowerCase()==='true';
    field=`<div class="bool"><input type="checkbox" data-i="${i}" ${on?'checked':''}></div>`;
  } else if(v.type==='longtext'){
    field=`<textarea data-i="${i}" rows="4" style="width:100%;resize:vertical"
             >${(v.value||'').replace(/\\n/g,String.fromCharCode(10)).replace(/</g,'&lt;')}</textarea>`;
  } else {
    const t=(v.type==='int'||v.type==='float')?'number':'text';
    field=`<input type="${t}" data-i="${i}" value="${(v.value||'').replace(/"/g,'&quot;')}"
             placeholder="${v.type==='bool'?'True/False':''}">`;
  }
  return `<div class="setrow"><label><b>${v.label}</b><small>${v.key}${v.hint?(' · '+v.hint):''}</small></label>${field}</div>`;
}
function showSetGroup(g){
  document.querySelectorAll('#settings .setgroup').forEach(el=>el.classList.toggle('on', el.dataset.g===g));
  document.querySelectorAll('#settabs button').forEach(b=>b.classList.toggle('on', b.dataset.g===g));
  try{ localStorage.setItem('PolyPanel.setgroup', g); }catch(e){}
}


async function saveNexusKey(){
  const el=document.getElementById('nexuskey');
  if(!el) return;
  try{
    const msg=await api('/api/mods/nexuskey?key='+encodeURIComponent(el.value),{method:'POST'});
    el.value=''; alert(msg);
  }catch(e){ alert('Fehler: '+e); }
}

async function loadInstalledMods(){
  const liste=document.getElementById('mods-installed-list');
  const pfad=document.getElementById('mods-installed-path');
  const anz=document.getElementById('mods-installed-count');
  if(!liste) return;
  try{
    const d=JSON.parse(await api('/api/mods/installed'));
    if(pfad) pfad.textContent=d.path||'—';
    const e=d.entries||[];
    if(anz) anz.textContent = e.length ? ('· '+e.length) : '';
    const ids = d.workshop_ids || [];
    const idsBlock = ids.length
      ? '<div class="setrow"><label><b>'+(L['mods.workshop_ids']||'Eingetragene Workshop-Mods')+'</b>'
        + '<small>'+ids.join(', ')+'</small></label>'
        + '<span class="meta">'+(L['mods.workshop_note']||'geladen beim nächsten Start')+'</span></div>'
      : '';
    if(!e.length){
      liste.innerHTML = idsBlock || '<p class="hint">'+(L['mods.local_empty']||'keine Mods im Ordner')+'</p>';
      return;
    }
    liste.innerHTML = idsBlock + e.map(function(m){
      const schluessel = m.key || m.name;
      return '<div class="row" style="align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.06)">'
        + '<div style="flex:1"><b>'+m.name+'</b><br><small style="color:var(--dim)">'+(m.size_mb||0)+' MB'
        + (m.active===false ? ' · '+(L['mods.inactive']||'inakt.') : '')
        + (m.source==='curseforge' ? ' · CurseForge' : '')+'</small></div>'
        + '<button class="danger" data-mod="'+schluessel+'">'+(L['mods.uninstall']||'Deinstallieren')+'</button>'
        + '</div>';
    }).join('');
    liste.querySelectorAll('button[data-mod]').forEach(function(b){
      b.onclick=function(){ uninstallMod(b.dataset.mod); };
    });
  }catch(err){ liste.textContent='Fehler: '+err; }
}
async function uninstallMod(key){
  const kurz = String(key).split('/').pop();
  const frage = (L['mods.uninstall_ask']||'Mod löschen: %s?').replace('%s', kurz);
  if(!confirm(frage)) return;
  const msg = await api('/api/mods/uninstall?id='+encodeURIComponent(key),{method:'POST'});
  alert(msg);
  loadInstalledMods();
}
async function loadLocalMods(){
  const spiel = document.body.dataset.game;
  const variante = ['arkse','spaceengineers'].includes(spiel) ? 'steam'
                 : (spiel === 'satisfactory' ? 'ficsit' : '');
  [['mods.local_hint','mods.local_hint_'+variante],['mods.search_how','mods.search_how_'+variante]].forEach(function(paar){
    if(!variante) return;
    const el=document.querySelector('[data-t="'+paar[0]+'"]'); if(!el) return;
    const key = paar[1];
    el.dataset.t = key; if(L[key]) el.textContent = L[key];
  });
  try{
    const d=JSON.parse(await api('/api/mods/local'));
    const st=document.getElementById('nexusstate');
    if(st && d.nexus_key!==null && d.nexus_key!==undefined){
      st.textContent = d.nexus_key ? (L['mods.api_on']||'API aktiv') : (L['mods.api_off']||'kein Key');
      st.className = 'badge ' + (d.nexus_key ? 'on' : 'off');
    }
  }catch(e){}
  loadInstalledMods();
}


let _modTimer=null, _modSeq=0;
function suggestLocalMods(){          // Vorschlaege beim Tippen, ohne Enter
  clearTimeout(_modTimer);
  const box=document.getElementById('modhits-local');
  const q=((document.getElementById('modq')||{}).value||'').trim();
  if(q.length<2){ _modSeq++; if(box) box.innerHTML=''; return; }
  _modTimer=setTimeout(searchLocalMods, 450);
}
async function searchLocalMods(){
  const box=document.getElementById('modhits-local');
  const q=(document.getElementById('modq')||{}).value||'';
  if(!box) return;
  if(!q.trim()){ box.innerHTML=''; return; }
  const seq=++_modSeq;
  box.innerHTML='<p class="hint">…</p>';
  try{
    const d=JSON.parse(await api('/api/mods/search?q='+encodeURIComponent(q)));
    if(seq!==_modSeq) return;                     // veraltete Antwort verwerfen
    if(!d.results || !d.results.length){
      box.innerHTML = (d.search_url
        ? '<div class="hint">'+(d.note||'')+'<br><a href="'+d.search_url+'" target="_blank" rel="noopener">'
          + (L['mods.open_site']||'Suche auf der Webseite öffnen') +'</a></div>'
        : '<p class="hint">'+(d.error||L['mods.none_active']||'keine Treffer')+'</p>');
      return;
    }
    box.innerHTML=d.results.map(function(m,i){
      const quelle = m.source==='nexus' ? '<small class="badge" style="margin-left:6px">Nexus</small>'
        : (m.source==='github' ? '<small class="badge" style="margin-left:6px">GitHub</small>'
        : (m.source==='steam' ? '<small class="badge" style="margin-left:6px">Steam</small>' : ''));
      const fertig = m.installed ? '<small class="badge on" style="margin-left:6px">'+(L['mods.already']||'eingetragen')+'</small>' : '';
      const zahlen = m.downloads ? (m.downloads.toLocaleString('de-DE')+' '+(L['mods.subs']||'Abonnenten')+' · ') : '';
      const bild = m.thumbnail ? '<img class="thumb" src="'+m.thumbnail+'" alt="" loading="lazy">' : '<div class="thumb"></div>';
      return '<div class="setrow"><span class="mrow">'+bild+'<label><b>'+m.name+'</b>'+quelle+fertig+'<small>'+zahlen+(m.description||'')+'</small></label></span>'
        + (m.installable && m.id
            ? '<span style="display:flex;gap:6px"><button class="modinstall" data-id="'+m.id+'"'
              + (m.installed?' disabled style="opacity:.5"':'')+'>'+(m.installed?(L['mods.already']||'eingetragen'):(L['mods.install']||'Installieren'))+'</button>'
              + (m.url?'<a href="'+m.url+'" target="_blank" rel="noopener"><button type="button">↗</button></a>':'')+'</span></div>'
            : (m.url
              ? '<a href="'+m.url+'" target="_blank" rel="noopener"><button type="button">'+(L['mods.open_site']||'Öffnen')+'</button></a></div>'
              : '<button class="modinstall" data-id="'+m.id+'">'+(L['mods.install']||'Installieren')+'</button></div>'));
    }).join('');
    box.querySelectorAll('.modinstall').forEach(function(b){
      b.onclick=function(){ installLocalMod(b.dataset.id); };
    });
  }catch(e){ box.textContent='Fehler: '+e; }
}
async function installLocalMod(id){
  const box=document.getElementById('modhits-local');
  if(box) box.innerHTML='<p class="hint">'+(L['mods.installing']||'wird installiert …')+'</p>';
  try{
    const msg=await api('/api/mods/install?id='+encodeURIComponent(id),{method:'POST'});
    if(box) box.innerHTML='<p class="hint">'+msg+'</p>';
    loadLocalMods();
  }catch(e){ if(box) box.textContent='Fehler: '+e; }
}

function filterSettings(q){
  q=(q||'').trim().toLowerCase();
  const groups=[...document.querySelectorAll('#settings .setgroup')];
  if(!q){ showSetGroup(window.__setGroup||(groups[0]&&groups[0].dataset.g)); return; }
  groups.forEach(g=>{
    g.classList.add('on');
    let sichtbar=0;
    g.querySelectorAll('.setrow').forEach(r=>{
      const treffer=r.textContent.toLowerCase().includes(q);
      r.style.display=treffer?'':'none';
      if(treffer) sichtbar++;
    });
    g.querySelectorAll('.meta').forEach(m=>{
      let n=m.nextElementSibling, hat=false;
      while(n && !n.classList.contains('meta')){
        if(n.classList.contains('setrow') && n.style.display!=='none'){ hat=true; break; }
        n=n.nextElementSibling;
      }
      m.style.display=hat?'':'none';
    });
    g.style.display=sichtbar?'':'none';
  });
}
async function loadSettings(){
  SETTINGS=JSON.parse(await api('/api/settings'));
  const byGroup={};
  SETTINGS.forEach(v=>{ const g=v.group||'play'; (byGroup[g]=byGroup[g]||[]).push(v); });
  const present=SETGROUP_ORDER.filter(g=>byGroup[g]);
  const tabs=present.map(g=>{
    const n=byGroup[g].length;
    return `<button data-g="${g}" onclick="showSetGroup('${g}')">${L['setg.'+g]||g} <small>${n}</small></button>`;
  }).join('');
  const blocks=present.map(g=>{
    const bySect={};
    byGroup[g].forEach(v=>{ (bySect[v.file+'|'+v.section]=bySect[v.file+'|'+v.section]||[]).push(v); });
    const inner=Object.entries(bySect).map(([k,list])=>{
      const p=k.split('|'), g=document.body.dataset.game;
      const file=p[0]==='gus'?'GameUserSettings.ini':
        (p[0]==='instance'?(g==='7d2d'?'serverconfig.xml':(g==='arkse'?'Startzeile / Instanz':'ServerSettings.ini')):'Game.ini');
      return `<div class="meta" style="margin:10px 0 2px;opacity:.75">${file} · ${p[1]}</div>`+
        list.map(_setField).join('');
    }).join('');
    return `<div class="setgroup" data-g="${g}">${inner}</div>`;
  }).join('');
  document.getElementById('settings').innerHTML=
    `<input id="setsearch" type="search" oninput="filterSettings(this.value)" placeholder="${L['set.search']||'Einstellungen durchsuchen'}" style="width:100%;margin:0 0 10px;padding:7px 10px;box-sizing:border-box">`+
    `<div class="settabs" id="settabs">${tabs}</div>`+blocks;
  let g=''; try{ g=localStorage.getItem('PolyPanel.setgroup')||''; }catch(e){}
  if(!byGroup[g]) g=present[0]||'play';
  showSetGroup(g);
}
async function saveSettings(){
  const payload=[];
  document.querySelectorAll('#settings input, #settings textarea').forEach(el=>{
    const v=SETTINGS[Number(el.dataset.i)];
    let value;
    if(el.type==='checkbox') value=el.checked?'True':'False';
    else if(el.tagName==='TEXTAREA') value=el.value.split(String.fromCharCode(13)).join('').split(String.fromCharCode(10)).join(String.fromCharCode(92)+'n').trim();
    else value=el.value.trim();
    if(value!=='' && value!==v.value){
      payload.push({file:v.file,section:v.section,key:v.key,value:value});
    }
  });
  if(!payload.length){document.getElementById('setmsg').textContent=L['set.no_changes'];return;}
  const r=await fetch('/api/settings?name='+NAME+'&token='+encodeURIComponent(T),
    {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  document.getElementById('setmsg').textContent=await r.text();
  loadSettings(); loadCfg();
}
async function loadWl(){
  const w=JSON.parse(await api('/api/whitelist'));
  const b=JSON.parse(await api('/api/bans'));
  const btn=document.getElementById('wlbtn');
  btn.textContent='Whitelist '+(w.enabled?L['wl.on']:L['wl.off']);
  btn.className=w.enabled?'primary':'';
  document.getElementById('wlcount').textContent=w.players.length+' '+L['wl.entries']+' · '+(w.exists?L['wl.file_present']:L['wl.file_missing']);
  document.getElementById('wllist').innerHTML=w.players.length?w.players.map(p=>
    `<div class="p"><span><b>${p}</b></span>
      <span class="row"><button onclick="delWl('${p}')">${L['common.remove']}</button></span></div>`).join('')
    :'<span style="color:var(--dim)">– '+(L['common.empty'])+' –</span>';
  document.getElementById('banlist').innerHTML=(b.bans||[]).length?b.bans.map(p=>
    `<div class="p"><span><b>${p}</b></span>
      <span class="row"><button onclick="unbanId('${p}')">Entbannen</button></span></div>`).join('')
    :'<span style="color:var(--dim)">– '+L['bk.none_dash']+' –</span>';
}
async function toggleWl(){
  const w=JSON.parse(await api('/api/whitelist'));
  document.getElementById('wlmsg').textContent=await api('/api/whitelist/enable?on='+(w.enabled?0:1),{method:'POST'});
  loadWl();
}
async function addWl(){
  const id=document.getElementById('pid').value.trim(); if(!id)return;
  document.getElementById('wlmsg').textContent=await api('/api/whitelist/add?id='+encodeURIComponent(id),{method:'POST'});
  document.getElementById('pid').value=''; loadWl();
}
async function delWl(id){
  document.getElementById('wlmsg').textContent=await api('/api/whitelist/remove?id='+encodeURIComponent(id),{method:'POST'});
  loadWl();
}
async function banId(){
  const id=document.getElementById('pid').value.trim(); if(!id)return;
  if(!confirm('Spieler '+id+' bannen?'))return;
  document.getElementById('wlmsg').textContent=await api('/api/ban?id='+encodeURIComponent(id),{method:'POST'});
  document.getElementById('pid').value=''; loadWl();
}
async function unbanId(id){
  document.getElementById('wlmsg').textContent=await api('/api/unban?id='+encodeURIComponent(id),{method:'POST'});
  loadWl();
}
async function loadMods(){
  try{
    const d=JSON.parse(await api('/api/mods'));
    document.getElementById('modsize').textContent=d.size_mb?(d.size_mb>=1024?(d.size_mb/1024).toFixed(1)+' GB':d.size_mb+' MB')+' '+L['mods.size_on_disk']:'';
    const active=(d.active||[]), inactive=(d.inactive||[]);
    document.getElementById('mods').innerHTML =
      `<div class="meta" style="margin:6px 0 2px">${L['mods.active']} (${active.length})</div>` +
      (active.length?active.map(m=>modRow(m,true)).join(''):'<span style="color:var(--dim)">– '+L['mods.none_active']+' –</span>') +
      `<div class="meta" style="margin:14px 0 2px">${L['mods.inactive']} (${inactive.length})</div>` +
      (inactive.length?inactive.map(m=>modRow(m,false)).join(''):'<span style="color:var(--dim)">– '+L['mods.none_inactive']+' –</span>');
    if((d.missing_meta||[]).length && !META_BUSY){
      META_BUSY=true;
      api('/api/mods/refresh',{method:'POST'}).then(()=>{META_BUSY=false; loadMods();}).catch(()=>{META_BUSY=false;});
    }
  }catch(e){}
}
let META_BUSY=false;
async function enableMod(id){
  document.getElementById('modout').textContent=await api('/api/mods/add?id='+id,{method:'POST'});
  loadMods();
}


let _suggTimer=null;
function suggestMods(){
  clearTimeout(_suggTimer);
  const q=document.getElementById('modid').value.trim();
  const box=document.getElementById('modhits');
  if(q.length<2){ box.innerHTML=''; return; }
  _suggTimer=setTimeout(async()=>{
    let data;
    try{ data=JSON.parse(await api('/api/mods/suggest?q='+encodeURIComponent(q))); }
    catch(e){ return; }
    const hits=(data.results||[]).slice(0,8);
    const sum=document.getElementById('modhitsum');
    if(sum) sum.textContent=hits.length? (hits.length+' '+L['mods.suggestions']) : '';
    if(!hits.length){
      box.innerHTML = (data.needs_key && q.length>=2)
        ? '<div class="meta">'+(L['mods.suggest_needs_key']||'Vorschläge beim Tippen brauchen einen CurseForge-API-Key.')+
          ' · <a href="https://console.curseforge.com" target="_blank" rel="noopener">'+L['mods.key']+'</a></div>'
        : '<div class="meta">'+L['mods.search_empty']+
          (data.needs_key?(' · <a href="https://console.curseforge.com" target="_blank">'+L['mods.key']+'</a>'):'')+'</div>';
      return;
    }
    box.innerHTML=hits.map(m=>`<div class="p" style="cursor:pointer" onclick="addModId('${m.id}')">
        <span class="mrow">
          ${m.thumbnail?`<img class="thumb" src="${m.thumbnail}" alt="" loading="lazy">`:'<div class="thumb"></div>'}
          <span class="txt"><b>${m.title||('Mod '+m.id)}</b>
          <small>${m.id}${m.downloads?(' · '+m.downloads.toLocaleString('de-DE')):''}${m.summary?(' · '+m.summary.slice(0,80)):''}</small></span>
        </span>
        <span class="row"><span class="badge">+</span></span></div>`).join('');
  }, 350);
}
async function searchMods(){
  const q=document.getElementById('modid').value.trim();
  const box=document.getElementById('modhits');
  const _sum=document.getElementById('modhitsum');
  if(!q){ box.innerHTML=''; if(_sum) _sum.textContent=''; return; }
  box.innerHTML='<div class="meta">'+L['common.loading']+'</div>';
  let data;
  try{ data=JSON.parse(await api('/api/mods/search?q='+encodeURIComponent(q))); }
  catch(e){ box.innerHTML='<div class="meta">'+L['mods.search_failed']+'</div>'; return; }
  const hits=(data.results||[]);
  if(!hits.length){
    box.innerHTML='<div class="meta">'+L['mods.search_empty']+
      (data.needs_key?(' · <a href="https://console.curseforge.com" target="_blank">'+L['mods.key']+'</a>'):'')+'</div>';
    return;
  }
  const sum=document.getElementById('modhitsum');
  if(sum){ const tot=data.total||hits.length;
    sum.textContent=((tot>hits.length)
      ? (hits.length+' / '+tot.toLocaleString('de-DE')+' '+L['mods.hits'])
      : (tot.toLocaleString('de-DE')+' '+L['mods.hits']))
      + ((tot>hits.length)?(' · '+L['mods.limit_note']):''); }
  box.innerHTML=hits.map(m=>`<div class="p"><span class="mrow">
      ${m.thumbnail?`<img class="thumb" src="${m.thumbnail}" alt="" loading="lazy">`:'<div class="thumb"></div>'}
      <span class="txt"><b>${m.title||('Mod '+m.id)}</b>
      <small>${m.id}${m.downloads?(' · '+m.downloads.toLocaleString('de-DE')+' Downloads'):''}${m.summary?(' · '+m.summary.slice(0,90)):''}</small></span></span>
      <span class="row"><button class="primary" onclick="addModId('${m.id}')">${L['mods.add_hit']}</button></span></div>`).join('');
}
async function addModId(id){
  const out=document.getElementById('modout');
  out.textContent=await api('/api/mods/add?id='+encodeURIComponent(id),{method:'POST'});
  loadMods();
}
async function loadKeyState(){
  const el=document.getElementById('keystate'); if(!el) return;
  try{
    const d=JSON.parse(await api('/api/mods/key'));
    el.textContent = d.has_key ? (L['mods.key_on']+(d.masked?(' · '+d.masked):'')) : L['mods.key_off'];
    el.style.color = d.has_key ? 'var(--ok,#3ecf8e)' : '';
  }catch(e){ el.textContent=''; }
}
async function saveKey(){
  const v=document.getElementById('cfkey').value.trim();
  try{ await api('/api/mods/key?key='+encodeURIComponent(v),{method:'POST'});
       document.getElementById('cfkeymsg').textContent=L['notify.saved'];
       document.getElementById('cfkey').value=''; loadKeyState(); }
  catch(e){ document.getElementById('cfkeymsg').textContent=L['notify.failed']; }
}
async function addMod(){
  const id=document.getElementById('modid').value.trim(); if(!/^[0-9]+$/.test(id)){alert('nur Zahlen');return;}
  document.getElementById('modout').textContent=await api('/api/mods/add?id='+id,{method:'POST'});
  document.getElementById('modid').value=''; loadMods();
}
async function delMod(id){
  if(!confirm('Mod '+id+' aus der Liste entfernen?'))return;
  document.getElementById('modout').textContent=await api('/api/mods/remove?id='+id,{method:'POST'});
  loadMods();
}
async function delModFiles(id){
  if(!confirm('Heruntergeladene Dateien von Mod '+id+' loeschen?'))return;
  document.getElementById('modout').textContent=await api('/api/mods/delete-files?id='+id,{method:'POST'});
  loadMods();
}
async function loadCfg(){
  const f=document.getElementById('cfgfile').value;
  document.getElementById('cfgtext').value=await api('/api/config?file='+f);
  document.getElementById('cfgmsg').textContent='';
}
async function saveCfg(){
  const f=document.getElementById('cfgfile').value;
  const t=document.getElementById('cfgtext').value;
  const r=await fetch('/api/config?file='+f+'&name='+NAME+'&token='+encodeURIComponent(T),
    {method:'POST',body:t});
  document.getElementById('cfgmsg').textContent=await r.text();
}
async function loadSnaps(){
  try{
    const list=JSON.parse(await api('/api/snapshots'));
    document.getElementById('snaps').innerHTML=list.length?list.map(x=>
      `<div class="p"><span><b>${x.mtime}</b><br><small>${x.name} · ${x.size_gb} GB</small></span>
       <span class="row">
         <button onclick="restoreSnap('${x.name}')">${L['snap.restore']}</button>
         <button class="danger" onclick="delSnap('${x.name}')">${L['common.delete']}</button>
       </span></div>`).join(''):'<span style="color:var(--dim)">– '+(L['snap.none'])+' –</span>';
  }catch(e){}
}
async function makeSnap(){
  document.getElementById('snapmsg').textContent='kopiert … (kann 1–2 Minuten dauern)';
  document.getElementById('snapmsg').textContent=await api('/api/snapshot',{method:'POST'});
  loadSnaps();
}
async function restoreSnap(name){
  if(!confirm(L['msg.confirm_snapshot']))return;
  document.getElementById('snapmsg').textContent='spielt zurück …';
  document.getElementById('snapmsg').textContent=await api('/api/snapshot/restore?file='+encodeURIComponent(name),{method:'POST'});
  setTimeout(refresh,3000);
}
async function delSnap(name){
  if(!confirm('Snapshot '+name+' löschen?'))return;
  document.getElementById('snapmsg').textContent=await api('/api/snapshot/delete?file='+encodeURIComponent(name),{method:'POST'});
  loadSnaps();
}
async function loadBackups(){
  const box=document.getElementById('backups');
  if(!box) return;                       // Backup-Box wurde entfernt
  try{
    const list=JSON.parse(await api('/api/backups'));
    box.innerHTML=list.length?list.slice(0,8).map(b=>
      `<div class="p"><span><b>${b.mtime} · ${L['bk.kind_'+({manuell:'manual',geplant:'auto','vor Restore':'pre_restore','älter':'old'}[b.kind]||'old')]}</b><br><small>${b.file} · ${b.size_mb} MB</small></span>
       <span class="row">
         <button onclick="restoreBk('${b.file}')">${L['bk.restore']}</button>
         <button class="danger" onclick="delBk('${b.file}')">${L['common.delete']}</button>
       </span></div>`).join(''):'<span style="color:var(--dim)">– '+L['bk.none']+' –</span>';
  }catch(e){}
}
async function makeBackup(){
  const msg=document.getElementById('bkmsg'); if(msg) msg.textContent='sichert …';
  const res=await api('/api/backup',{method:'POST'});
  if(msg) msg.textContent=res;
  loadBackups();
}
async function restoreBk(f){
  if(!confirm(L['msg.confirm_restore']))return;
  const m=document.getElementById('bkmsg'); if(m) m.textContent='spielt ein …';
  const r=await api('/api/backup/restore?file='+encodeURIComponent(f),{method:'POST'});
  if(m) m.textContent=r;
  setTimeout(refresh,3000);
}
async function delBk(f){
  if(!confirm('Backup '+f+' löschen?'))return;
  document.getElementById('bkmsg').textContent=await api('/api/backup/delete?file='+encodeURIComponent(f),{method:'POST'});
  loadBackups();
}

async function loadHooks(){
  try{ const d=JSON.parse(await api('/api/webhook')); document.getElementById('hookurl').value=d.url||''; }catch(e){}
}
async function saveHook(){
  const url=document.getElementById('hookurl').value.trim();
  try{ await api('/api/webhook?url='+encodeURIComponent(url),{method:'POST'});
       document.getElementById('hookmsg').textContent=L['notify.saved']; }
  catch(e){ document.getElementById('hookmsg').textContent=L['notify.failed']; }
}
async function testHook(){
  const url=document.getElementById('hookurl').value.trim();
  const msg=document.getElementById('hookmsg');
  msg.textContent='…';
  try{ const r=JSON.parse(await api('/api/notify/test?url='+encodeURIComponent(url),{method:'POST'}));
       msg.textContent = r.ok ? L['notify.test_ok'] : (L['notify.test_fail']+': '+r.error); }
  catch(e){ msg.textContent=L['notify.test_fail']; }
}
async function loadSchedule(){
  const s=JSON.parse(await api('/api/schedule'));
  document.getElementById('schedRestart').value=(s.restart_times||[]).join(',');
  TASKS=(s.tasks||[]).map(t=>Object.assign({days:[]},t));
  renderTasks();
  document.getElementById('schedWarn').value=s.warn_minutes;
  document.getElementById('schedKeep').value=s.backups_keep;
  const sk=document.getElementById('snapKeep'); if(sk) sk.value=(s.snapshot_keep!==undefined?s.snapshot_keep:3);
  const st=document.getElementById('snapTimes'); if(st) st.value=(s.snapshot_times||[]).join(',');
}
async function saveSchedule(){
  const p=new URLSearchParams({restart:document.getElementById('schedRestart').value,
    warn:document.getElementById('schedWarn').value,
    keep:document.getElementById('schedKeep').value,
    snapkeep:(document.getElementById('snapKeep')||{}).value||'',
    snaptimes:(document.getElementById('snapTimes')||{}).value||''});
  document.getElementById('schedmsg').textContent=await api('/api/schedule?'+p.toString(),{method:'POST'});
}
async function pa(sid,action){ if(!confirm(action+' für '+sid+'?'))return;
  document.getElementById('out').textContent=await api('/api/player/action?steamid='+sid+'&action='+action,{method:'POST'});
  setTimeout(refresh,1500); }
async function give(sid){ const bp=prompt('Blueprint','PrimalItemResource_Stone_C'); if(!bp)return;
  const q=prompt('Menge','10')||'10';
  document.getElementById('out').textContent=await api('/api/player/give?steamid='+sid+'&bp='+encodeURIComponent(bp)+'&qty='+q,{method:'POST'}); }
applyLang(); restoreTab(); setTimeout(restoreTab, 250); refresh(); updCheck(); renderCmds(); loadMods(); loadKeyState(); loadCfg(); loadWl(); loadSettings(); loadCluster(); loadSnaps(); loadBackups(); loadSchedule(); loadHooks();
setInterval(refresh,5000); setInterval(updCheck,300000);
</script>""" + FOOTER + """
</body></html>"""

LICENSE_PAGE = """<!doctype html><html lang="__LANG__"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>PolyPanel · __TITLE__</title>
<style>""" + SHARED_CSS + """</style></head><body>
<canvas id="bg"></canvas>
<header><h1>PolyPanel</h1><span class="badge" data-t="license.title">__TITLE__</span>
<span class="hostbar"><a href="/?token=__TOK__"><button>← Dashboard</button></a></span>""" + HEADER_ICONS + """</header>
<main>
  <section class="lic">
    <div class="lichead"><h2>__TITLE__</h2>
      <span class="meta">__SHORT__</span></div>
    <pre class="lictext">__TEXT__</pre>
    <p class="meta" style="margin:14px 0 0;color:var(--dim);font-size:11.5px">__HINT__</p>
  </section>
</main>""" + FOOTER + """
<script>const L=__LANGJSON__;
function applyLang(){document.querySelectorAll('[data-t]').forEach(function(e){
  var k=e.dataset.t; if(L[k]) e.textContent=L[k]; });}
applyLang();</script>
<script>""" + BG_JS + """</script>
</body></html>"""


def license_text() -> str:
    """Lizenztext in der aktiven Sprache aus der Datei LICENSE neben dem Paket."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for path in (os.path.join(root, "LICENSE"),
                 os.path.expanduser("~/.local/share/PolyPanel/LICENSE")):
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as fh:
            raw = fh.read().strip()
        parts = raw.split("\n---\n")
        if len(parts) >= 2:
            return (parts[0] if i18n.lang() == "de" else parts[1]).strip()
        return raw
    return ("Copyright (c) 2026 Ronny H. (https://github.com/Ronny-H-79)\n\n"
            + i18n.t("license.short"))


def license_page(tok: str) -> str:
    title = i18n.t("license.title")
    return _render(LICENSE_PAGE
                   .replace("__TITLE__", title)
                   .replace("__SHORT__", i18n.t("license.short"))
                   .replace("__HINT__", i18n.t("license.hint"))
                   .replace("__TEXT__", html_escape(license_text()))
                   .replace("__TOK__", urllib.parse.quote(tok)))


PLAYER_ACTIONS = {
    "kick": "KickPlayer %s",
    "ban": "BanPlayer %s",
    "unban": "UnbanPlayer %s",
    "whitelist": "AllowPlayerToJoinNoCheck %s",
    "unwhitelist": "DisallowPlayerToJoinNoCheck %s",
}


_PROGRESS_RE = re.compile(r"progress:\s*([0-9]+(?:\.[0-9]+)?)")
_STATE_RE = re.compile(r"Update state \(0x[0-9a-f]+\)\s*([a-z ]+?)(?:,|$)")


def install_progress(inst) -> dict[str, object]:
    """Fortschritt der laufenden Installation aus .install.log lesen.

    SteamCMD schreibt Zeilen wie
    ``Update state (0x61) downloading, progress: 42.31 (123 / 456)``.
    Daraus wird Prozentwert und Phase gezogen, damit die Oberflaeche einen Balken zeigen kann.
    """
    log_path = os.path.join(inst.directory, ".install.log")
    daten: dict[str, object] = {"running": inst.name in INSTALLS, "percent": None,
                                "phase": "", "done": False}
    try:
        with open(log_path, encoding="utf-8", errors="replace") as fh:
            zeilen = fh.readlines()[-400:]
    except OSError:
        return daten
    for zeile in reversed(zeilen):
        if "Success! App" in zeile or "Installation beendet" in zeile:
            daten["done"] = True
            daten["percent"] = 100.0
            daten["phase"] = "done"
            return daten
        m = _PROGRESS_RE.search(zeile)
        if m:
            daten["percent"] = float(m.group(1))
            s = _STATE_RE.search(zeile)
            daten["phase"] = (s.group(1).strip() if s else "downloading")
            return daten
        s = _STATE_RE.search(zeile)
        if s and not daten["phase"]:
            daten["phase"] = s.group(1).strip()
    return daten


def _start_install(inst: Instance) -> None:
    """Installation im Hintergrund ueber den gemeinsamen Installer."""
    from . import installer
    INSTALLS[inst.name] = {"log": os.path.join(inst.directory, ".install.log"),
                           "started": time.time()}

    def run() -> None:
        try:
            result = installer.install_server(inst)
            # Dienst gleich mit anlegen: Ueberwachung und Autostart ohne Handarbeit
            if result.get("ok"):
                from . import units
                u = units.install(inst)
                try:
                    with open(os.path.join(inst.directory, ".install.log"), "a") as fh:
                        if u.get("ok"):
                            fh.write("Dienst eingerichtet: %s (%s)\n"
                                     % (u["path"], "System" if u["system"] else "Benutzer"))
                        else:
                            fh.write("Dienst konnte nicht eingerichtet werden: %s\n"
                                     % (u.get("error") or u.get("message")))
                except OSError:
                    pass
        except Exception as exc:  # noqa: BLE001
            try:
                with open(os.path.join(inst.directory, ".install.log"), "a") as fh:
                    fh.write("Fehler: %s\n" % exc)
            except OSError:
                pass
        finally:
            INSTALLS.pop(inst.name, None)

    threading.Thread(target=run, daemon=True).start()



def _translate_hits(data: dict, field: str, limit: int = 24) -> dict:
    """Mod-Beschreibungen in der deutschen Oberflaeche uebersetzen (Cache, fehlertolerant)."""
    if i18n.lang() != "de":
        return data
    try:
        from . import translate
        translate.translate_items(data.get("results") or [], field, limit=limit)
    except Exception:                       # noqa: BLE001 - Suche darf nie scheitern
        pass
    return data


def _uebersetzte_settings(inst) -> list:
    """Einstellungen mit Label und Hinweis in der aktuellen Sprache.

    Je Spiel kommen die Labels deutsch aus dem Profil (``*_labels.py``); fuer Englisch
    uebersetzt ``i18n.setting()`` sie (kuratierte Tabelle, sonst lesbarer Schluesselname).
    """
    from . import i18n as _i18n
    if inst.game == "ark":
        felder = cfgfile.read_values(inst)
    else:
        felder = inst.profile.settings(inst)
    for feld in felder:
        if not isinstance(feld, dict):
            continue
        label, hint = _i18n.setting(feld.get("key", ""), feld.get("label", ""), feld.get("hint", ""))
        feld["label"], feld["hint"] = label, hint
    return felder


def _dirs_mb(rel: list, basis: str) -> float:
    """Groesse mehrerer Unterordner (relativ zu basis) in MB."""
    total = 0
    for eintrag in rel or []:
        for ordner, _dirs, dateien in os.walk(os.path.join(basis, eintrag)):
            for datei in dateien:
                try:
                    total += os.path.getsize(os.path.join(ordner, datei))
                except OSError:
                    pass
    return round(total / 1024 / 1024, 1)


def _installed_mods(inst) -> dict:
    """Installierte Mods einheitlich fuer alle Spiele.

    ARK (ASA) fuehrt seine Mods ueber CurseForge-IDs in der Konfiguration, alle anderen
    Spiele ueber Ordner im Mod-Verzeichnis. Der Mods-Reiter soll in beiden Faellen oben
    dieselbe Liste zeigen, deshalb hier ein gemeinsames Format:
    ``{"path", "entries": [{name, size_mb, source, active}], "workshop_ids"}``.
    """
    if inst.game == "ark":
        ordner = modlib.installed_dirs(inst)
        daten = modlib.list_all_enriched(inst)
        basis = modlib.mods_dir(inst)
        eintraege = []
        for gruppe, aktiv in (("active", True), ("inactive", False)):
            for eintrag in daten.get(gruppe) or []:
                eintraege.append({
                    "name": eintrag.get("title") or eintrag.get("name") or str(eintrag.get("id")),
                    "size_mb": _dirs_mb(ordner.get(str(eintrag.get("id")), []), basis),
                    "source": "curseforge",
                    "active": aktiv,
                })
        return {"path": basis, "entries": eintraege, "workshop_ids": None}
    lokal = _local_mods(inst)
    for eintrag in lokal.get("entries", []):
        eintrag.setdefault("source", "local")
        eintrag.setdefault("active", True)
    return lokal


def _uninstall_mod(inst, key: str) -> str:
    """Mod-Ordner entfernen - nur echte Mod-Ordner dieser Instanz.

    ``key`` ist der relative Pfad aus der Liste (``Name`` oder ``GameFeatures/Name``).
    Alles ausserhalb des Mod-Verzeichnisses wird abgelehnt, damit ein manipulierter
    Aufruf keine fremden Ordner loeschen kann.
    """
    pfad = inst.profile.mods_path(inst)
    if not pfad:
        raise RuntimeError("Dieses Spiel hat keinen Mod-Ordner")
    basis = os.path.realpath(pfad)
    teile = [t for t in str(key).replace(os.sep, "/").split("/") if t]
    if not teile or len(teile) > 2 or any(t in (".", "..") for t in teile):
        raise RuntimeError("ungueltiger Mod-Name")
    if len(teile) == 2 and teile[0] != "GameFeatures":
        raise RuntimeError("ungueltiger Pfad")
    ziel = os.path.realpath(os.path.join(basis, *teile))
    if not ziel.startswith(basis + os.sep) or not os.path.isdir(ziel):
        raise RuntimeError("Mod-Ordner nicht gefunden: %s" % key)
    mb = _dirs_mb([""], ziel)
    shutil.rmtree(ziel)
    return "%s entfernt (%s MB frei)" % (teile[-1], mb)


def _local_mods(inst) -> dict:
    """Mods im spieleigenen Ordner auflisten (7D2D, Satisfactory, Space Engineers)."""
    pfad = inst.profile.mods_path(inst)
    eintraege = []
    if pfad and os.path.isdir(pfad):
        # SML legt GameFeatures-Mods eine Ebene tiefer ab (Mods/GameFeatures/<Name>) -
        # ohne Aufloesen stuende in der Liste nur ein Eintrag "GameFeatures".
        kandidaten = []
        for name in sorted(os.listdir(pfad)):
            voll = os.path.join(pfad, name)
            if not os.path.isdir(voll):
                continue
            if name == "GameFeatures":
                for sub in sorted(os.listdir(voll)):
                    if os.path.isdir(os.path.join(voll, sub)):
                        kandidaten.append((sub, os.path.join(voll, sub)))
            else:
                kandidaten.append((name, voll))
        for name, voll in kandidaten:
            schluessel = os.path.relpath(voll, pfad).replace(os.sep, "/")
            try:
                mb = sum(os.path.getsize(os.path.join(w, f))
                         for w, _, fs in os.walk(voll) for f in fs) / 1024 / 1024
            except OSError:
                mb = 0
            eintraege.append({"name": name, "size_mb": round(mb, 1),
                              "workshop": name.isdigit(), "key": schluessel})
    hat_key = False
    if hasattr(inst.profile, "nexus_key"):
        try:
            hat_key = bool(inst.profile.nexus_key())
        except Exception:                       # noqa: BLE001
            hat_key = False
    return {"path": pfad, "entries": eintraege,
            "workshop_ids": ([int(m) for m in inst.mods] if inst.game == "arkse"
                             else [int(m) for m in inst.profile.workshop_ids(inst)
                                   if str(m).isdigit()] if inst.game == "spaceengineers" else None),
            "nexus_key": hat_key if inst.game == "7d2d" else None}


class Handler(BaseHTTPRequestHandler):
    server_version = "PolyPanel"

    def _auth(self) -> bool:
        q = urllib.parse.urlparse(self.path).query
        tok = urllib.parse.parse_qs(q).get("token", [""])[0] or self.headers.get("X-Token", "")
        return hmac.compare_digest(tok, token())

    def end_headers(self) -> None:
        """Sicherheits-Header auf jeder Antwort."""
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; "
                         "script-src 'self' 'unsafe-inline'; connect-src 'self'")
        super().end_headers()

    def _send(self, code: int, body: bytes, ctype: str = "text/plain; charset=utf-8") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data) -> None:
        self._send(200, json.dumps(data, ensure_ascii=False).encode(), "application/json")

    def _html(self, text: str) -> None:
        self._send(200, text.encode(), "text/html; charset=utf-8")

    def _inst(self, q: dict) -> Instance | None:
        name = q.get("name", [""])[0]
        if not name:
            parts = urllib.parse.urlparse(self.path).path.strip("/").split("/")
            if len(parts) == 2 and parts[0] == "i":
                name = parts[1]
        if not name:
            known = registry.names()
            name = known[0] if known else ""
        try:
            return registry.load(name) if name else None
        except TypeError:
            return None

    def log_message(self, *_args) -> None:
        pass

    # ------------------------------------------------------------------ GET
    def do_GET(self) -> None:  # noqa: N802
        if not self._auth():
            self._send(401, b"token fehlt")
            return
        u = urllib.parse.urlparse(self.path)
        # keep_blank_values: ein geleertes Feld (z. B. Uhrzeiten) muss auch geleert ankommen
        path, q = u.path, urllib.parse.parse_qs(u.query, keep_blank_values=True)
        tok = q.get("token", [""])[0]

        if path == "/":
            games_opts = "".join('<option value="%s">%s</option>' % (k, v)
                                 for k, v in games.labels().items())
            gamemaps = json.dumps({k: [list(m) for m in p.maps]
                                   for k, p in games.PROFILES.items() if p.maps},
                                  ensure_ascii=False)
            self._html(_render(DASH.replace("__GAMES__", games_opts)
                                  .replace("__GAMEMAPS__", gamemaps)))
            return
        if path.startswith("/i/"):
            inst = self._inst(q)
            if not inst:
                self._send(404, b"Instanz nicht gefunden")
                return
            self._html(_render(INST.replace("__NAME__", inst.name).replace("__TOK__", tok)
                                   .replace("__GAME__", inst.game)))
            return
        if path in ("/license", "/lizenz"):
            self._html(license_page(tok))
            return

        if path.startswith("/static/maps/"):
            name = os.path.basename(path)
            base = os.path.expanduser("~/.config/polypanel/static/maps")
            full = os.path.join(base, name)
            if not name.endswith(".jpg") or not os.path.isfile(full):
                self._send(404, b"kein Bild")
                return
            with open(full, "rb") as fh:
                blob = fh.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(blob)))
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            self.wfile.write(blob)
            return
        if path == "/api/host":
            self._json(metrics.host())
            return
        if path == "/api/selfupdate":
            from . import selfupdate
            self._json(selfupdate.check())
            return
        if path == "/api/changelog":
            from . import selfupdate
            self._json(selfupdate.changelog(i18n.lang()))
            return
        if path == "/api/selfupdate/notes":
            from . import selfupdate
            self._json(selfupdate.notes(q.get("v", [""])[0]))
            return

        if path == "/api/instances":
            out = []
            for name in registry.names():
                obj = registry.load(name)
                if obj:
                    row = registry.info(obj)
                    row["action"] = ACTIONS.get(row["name"], "")
                    out.append(row)
            self._json(out)
            return

        # Mods: Suche und Key-Status brauchen keine Instanz
        if path == "/api/mods/search":
            term = q.get("q", [""])[0]
            inst_m = self._inst(q)
            if inst_m is not None and inst_m.game != "ark":
                # 7D2D/Satisfactory/SE/ASE: eigener Anbieter je Spielprofil
                try:
                    payload = inst_m.profile.mods_search(inst_m, term)
                    self._json(_translate_hits(payload, "description"))
                except Exception as exc:          # noqa: BLE001
                    self._json({"results": [], "error": str(exc)})
                return
            key = modlib._api_key()
            results = modlib.search(term, limit=50)
            self._json(_translate_hits({"results": results, "total": modlib.api_total(),
                                        "needs_key": not bool(key), "has_key": bool(key)},
                                       "summary"))
            return
        if path == "/api/mods/suggest":
            self._json(_translate_hits(modlib.suggest(q.get("q", [""])[0]), "summary", limit=8))
            return
        if path == "/api/update/progress":
            inst_p = self._inst(q)
            state = dict(runner.UPDATE_STATE)
            log = runner.update_log_path(inst_p) if inst_p else ""
            lines = runner.tail(log, 40) if log and os.path.exists(log) else []
            state["log"] = lines
            state["active"] = bool(state.get("running"))
            self._json(state)
            return

        if path == "/api/mods/key":
            key = modlib._api_key()
            self._json({"has_key": bool(key),
                        "masked": (key[:3] + "…" + key[-3:]) if len(key) > 8 else ""})
            return

        inst = self._inst(q)
        if path == "/api/install/cancel":
            if not inst:
                self._json({"ok": False, "error": "keine Instanz"})
                return
            from . import installer as _inst_mod
            ergebnis = _inst_mod.cancel(inst.name)
            INSTALLS.pop(inst.name, None)
            try:
                with open(os.path.join(inst.directory, ".install.log"), "a") as fh:
                    fh.write("\nInstallation abgebrochen durch Benutzer\n")
            except OSError:
                pass
            self._json(ergebnis)
            return
        if path == "/api/install/progress":
            if not inst:
                self._json({"running": False, "percent": None, "phase": "", "done": False})
                return
            self._json(install_progress(inst))
            return
        if path == "/api/install/log":
            if not inst:
                self._send(404, b"keine Instanz")
                return
            log_path = os.path.join(inst.directory, ".install.log")
            state = "laeuft" if inst.name in INSTALLS else "fertig"
            lines = runner.tail(log_path, 40) if os.path.exists(log_path) else []
            self._send(200, ("[%s]\n" % state + "\n".join(lines)).encode())
            return
        if not inst:
            self._send(404, b"keine Instanz")
            return

        if path == "/api/status":
            self._json(runner.status(inst))
        elif path == "/api/logs":
            self._send(200, "\n".join(runner.tail(inst.log_path, int(q.get("n", ["30"])[0]))).encode())
        elif path == "/api/console":
            self._send(200, "\n".join(runner.tail_console(inst, int(q.get("n", ["40"])[0]))).encode())
        elif path == "/api/players":
            self._json(players(inst))
        elif path == "/api/update":
            self._json(runner.check_update(inst, 0 if q.get("refresh") else None))
        elif path == "/api/lang":
            self._json({"lang": i18n.lang(), "catalog": i18n.catalog()})

        elif path == "/api/webhook":
            self._json({"url": inst.webhook_url if inst else "", "log": notify_mod.log_path(inst) if inst else ""})
        elif path == "/api/commands":
            self._json([i18n.command(c) for c in cmdreg.COMMANDS])
        elif path == "/api/mods/local":
            self._json(_local_mods(inst))
        elif path == "/api/mods/installed":
            self._json(_installed_mods(inst))
        elif path == "/api/mods/search":
            q = q.get("q", [""])[0].strip()
            if not q:
                self._json({"results": [], "search_url": ""})
            else:
                try:
                    self._json(_translate_hits(inst.profile.mods_search(inst, q), "description"))
                except Exception as exc:      # noqa: BLE001 - Suche darf nie 500en
                    self._json({"results": [], "error": str(exc)})
        elif path == "/api/mods":
            data = modlib.list_all_enriched(inst)
            data["size_mb"] = modlib.mod_size_mb(inst)
            self._json(data)
        elif path == "/api/config":
            which = q.get("file", ["gus"])[0]
            self._send(200, cfgfile.read(inst, which).encode())
        elif path == "/api/mod/meta":
            self._json(modlib.meta(q.get("id", [""])[0], force=q.get("force", [""])[0] == "1"))
        elif path == "/api/whitelist":
            self._json(wl.info(inst))
        elif path == "/api/bans":
            self._json({"bans": wl.bans(inst)})
        elif path == "/api/snapshots":
            self._json(snap.listing(inst))
        elif path == "/api/cluster":
            self._json({
                "cluster_id": inst.cluster_id or inst.name,
                "cluster_id_custom": bool(inst.cluster_id),
                "cluster_dir": inst.cluster_path,
                "cluster_dir_custom": bool(inst.cluster_dir),
                "transfer_filtering": bool(inst.cluster_transfer_filtering),
            })
        elif path == "/api/settings":
            if inst.game != "ark":
                self._json(_uebersetzte_settings(inst))     # nur die Felder dieses Spiels
            else:
                self._json(_uebersetzte_settings(inst))
        elif path == "/api/backups":
            self._json(bk.listing(inst))
        elif path == "/api/schedule":
            self._json({
                "restart_times": inst.restart_times,
                "backup_times": inst.backup_times,
                "warn_minutes": inst.warn_minutes,
                "backups_keep": inst.backups_keep,
                "snapshot_keep": inst.snapshot_keep,
                "snapshot_times": inst.snapshot_times,
                "tasks": inst.tasks,
                "actions": list(supervisor.Supervisor.TASK_ACTIONS),
            })
        elif path == "/api/config/known":
            self._json(cfgfile.known_for(q.get("file", ["gus"])[0]))
        else:
            self._send(404, b"unbekannt")

    # ------------------------------------------------------------------ POST
    def do_POST(self) -> None:  # noqa: N802
        if not self._auth():
            self._send(401, b"token fehlt")
            return
        u = urllib.parse.urlparse(self.path)
        # keep_blank_values: ein geleertes Feld (z. B. Uhrzeiten) muss auch geleert ankommen
        path, q = u.path, urllib.parse.parse_qs(u.query, keep_blank_values=True)

        if path == "/api/selfupdate":
            from . import selfupdate

            # synchron einspielen, damit die Oberflaeche Erfolg oder Fehler zeigen kann
            result = selfupdate.apply()
            if result.get("ok"):
                threading.Timer(1.0, selfupdate.restart_service).start()
            self._json(result)
            return

        if path == "/api/mods/uninstall":
            inst_m = self._inst(q)
            schluessel = q.get("id", [""])[0].strip()
            if inst_m is None or not schluessel:
                self._send(400, b"Instanz oder Mod fehlt")
                return
            try:
                self._send(200, _uninstall_mod(inst_m, schluessel).encode())
            except (RuntimeError, OSError) as exc:
                self._send(400, str(exc).encode())
            return

        if path == "/api/mods/nexuskey":
            key = q.get("key", [""])[0].strip()
            from .games.sv7dtd import SevenDaysProfile
            SevenDaysProfile.set_nexus_key(key)
            self._send(200, ("Nexus-Key gespeichert" if key else "Nexus-Key gelöscht").encode())
            return

        if path == "/api/mods/install":
            inst_m = self._inst(q)
            mid = q.get("id", [""])[0].strip()
            if inst_m is None or not mid:
                self._send(400, b"Instanz oder Mod-ID fehlt")
                return
            try:
                msg = inst_m.profile.mods_install(inst_m, mid, log=lambda m: None)
                if inst_m.game == "arkse":          # Mod-Liste steht in der Instanz-Config
                    registry.save(inst_m)
                    inst_m.write_ini()
                self._send(200, msg.encode())
            except Exception as exc:              # noqa: BLE001 - Fehler an die UI
                self._send(400, str(exc).encode())
            return

        if path == "/api/instances":
            port = q.get("port", [""])[0]
            try:
                inst = registry.create(
                    q.get("name", [""])[0].strip(),
                    q.get("map", ["Ragnarok_WP"])[0],
                    int(port) if port.isdigit() else None,
                    q.get("session", [""])[0],
                    game=q.get("game", ["ark"])[0],
                )
            except (ValueError, RuntimeError) as exc:
                self._send(200, ("Fehler: %s" % exc).encode())
                return
            inst.write_ini()
            self._send(200, ("Instanz '%s' angelegt - Port %d, RCON %d\nJetzt 'Installieren' druecken."
                             % (inst.name, inst.port, inst.rcon_port)).encode())
            return

        if path == "/api/mods/key":
            i18n.put("curseforge_key", q.get("key", [""])[0].strip())
            self._send(200, b"ok")
            return

        inst = self._inst(q)
        if not inst:
            self._send(404, b"keine Instanz")
            return

        if path == "/api/install":
            if inst.name in INSTALLS:
                self._send(200, b"Installation laeuft bereits")
                return
            _start_install(inst)
            self._send(200, ("Installation gestartet: %s\nDauer je nach Leitung 10-30 Minuten."
                             % inst.directory).encode())
            return
        if (path == "/api/start") and runner.is_running(inst):
            self._json({"ok": True, "info": "laeuft bereits"})
            return
        if path in ("/api/start", "/api/restart", "/api/update"):
            def _act() -> None:
                _log_step(inst, "%s angefordert" % path.split("/")[-1])
                ACTIONS[inst.name] = path.rsplit("/", 1)[-1]
                try:
                    if path == "/api/start":
                        _log_step(inst, "start: PID %s" % runner.start(inst))
                    elif path == "/api/restart":
                        _log_step(inst, "restart: %s" % runner.restart(inst))
                    else:
                        _log_step(inst, "update: %s" % runner.update_installed(inst))
                except Exception as exc:  # noqa: BLE001 - der Grund muss sichtbar werden
                    _log_step(inst, "%s fehlgeschlagen: %s" % (path.split("/")[-1], exc))
                    supervisor.notify(inst, "%s fehlgeschlagen: %s" % (path.split("/")[-1], exc))
                    supervisor.notify_event(inst, "Aktion fehlgeschlagen", str(exc)[:500], "error",
                                            {"Instanz": inst.name})
                finally:
                    ACTIONS.pop(inst.name, None)
            threading.Thread(target=_act, daemon=True).start()
            self._json({"ok": True, "info": "%s ausgeloest" % path.split("/")[-1]})
        elif path == "/api/stop":
            def _stop() -> None:
                _log_step(inst, "stop angefordert")
                ACTIONS[inst.name] = "stop"
                try:
                    _log_step(inst, "stop: %s" % runner.stop(inst))
                except Exception as exc:  # noqa: BLE001
                    _log_step(inst, "stop fehlgeschlagen: %s" % exc)
                finally:
                    ACTIONS.pop(inst.name, None)
            threading.Thread(target=_stop, daemon=True).start()
            self._json({"ok": True, "info": "stop ausgeloest"})
        elif path == "/api/rcon":
            cmd = q.get("cmd", [""])[0]
            try:
                self._send(200, (rcon_cmd(inst, cmd) or "(keine Antwort)").encode())
            except Exception as exc:  # noqa: BLE001
                self._send(200, ("RCON-Fehler: %s" % exc).encode())
        elif path == "/api/whitelist/add":
            try:
                wl.add_to_whitelist(inst, q.get("id", [""])[0])
                self._send(200, ("%s auf die Whitelist gesetzt" % q.get("id", [""])[0]).encode())
            except ValueError as exc:
                self._send(200, ("Fehler: %s" % exc).encode())
        elif path == "/api/whitelist/remove":
            try:
                wl.remove_from_whitelist(inst, q.get("id", [""])[0])
                self._send(200, ("%s von der Whitelist entfernt" % q.get("id", [""])[0]).encode())
            except ValueError as exc:
                self._send(200, ("Fehler: %s" % exc).encode())
        elif path == "/api/whitelist/enable":
            on = q.get("on", ["0"])[0] == "1"
            wl.set_enabled(inst, on)
            self._send(200, ("Whitelist %s - Neustart noetig" % ("AN" if on else "AUS")).encode())
        elif path == "/api/ban":
            pid = q.get("id", [""])[0]
            try:
                out = rcon_cmd(inst, "BanPlayer %s" % pid)
                wl.record_ban(inst, pid)
                self._send(200, ("%s: %s" % (pid, out or "gebannt")).encode())
            except Exception as exc:  # noqa: BLE001
                self._send(200, ("RCON-Fehler: %s" % exc).encode())
        elif path == "/api/unban":
            pid = q.get("id", [""])[0]
            try:
                out = rcon_cmd(inst, "UnbanPlayer %s" % pid)
                wl.forget_ban(inst, pid)
                self._send(200, ("%s: %s" % (pid, out or "entbannt")).encode())
            except Exception as exc:  # noqa: BLE001
                self._send(200, ("RCON-Fehler: %s" % exc).encode())
        elif path == "/api/webhook":
            url = q.get("url", [""])[0].strip()
            if url and not url.startswith("https://"):
                self._send(400, b"Webhook muss mit https:// beginnen")
                return
            inst.webhook_url = url
            registry.save(inst)
            self._send(200, ("ok").encode())
            return
        elif path == "/api/instance/delete":
            files = q.get("files", ["0"])[0] in ("1", "true", "yes")
            if runner.is_running(inst):
                runner.stop(inst, timeout=90)
            try:
                result = registry.forget(inst.name, delete_files=files)
            except Exception as exc:  # noqa: BLE001
                self._json({"ok": False, "error": str(exc)[:200]})
                return
            self._json(result)
            return
        elif path == "/api/notify/test":
            url = q.get("url", [""])[0].strip() or inst.webhook_url
            result = notify_mod.test(inst, url)
            self._json(result)
            return
        elif path == "/api/mods/refresh":
            ids = [m["id"] for m in modlib.list_all(inst)["active"] + modlib.list_all(inst)["inactive"]]
            self._json(modlib.refresh_meta(ids))
        elif path == "/api/mods/add":
            try:
                modlib.add_mod(inst, q.get("id", [""])[0])
                self._send(200, ("Mod %s eingetragen. Server neu starten, damit er sie laedt."
                                 % q.get("id", [""])[0]).encode())
            except ValueError as exc:
                self._send(200, ("Fehler: %s" % exc).encode())
        elif path == "/api/mods/remove":
            modlib.remove_mod(inst, q.get("id", [""])[0])
            self._send(200, ("Mod %s aus der Liste entfernt." % q.get("id", [""])[0]).encode())
        elif path == "/api/mods/delete-files":
            ok = modlib.remove_folder(inst, q.get("id", [""])[0])
            self._send(200, (("Dateien geloescht." if ok else "Keine Dateien gefunden.")).encode())
        elif path == "/api/snapshot":
            try:
                info = snap.create(inst)
                self._send(200, ("Snapshot erstellt: %s (%.1f GB)" % (info["name"], info["size_gb"])).encode())
            except Exception as exc:  # noqa: BLE001
                self._send(200, ("Snapshot-Fehler: %s" % exc).encode())
        elif path == "/api/snapshot/restore":
            try:
                snapname = q.get("file", [""])[0] or q.get("snap", [""])[0]
                self._send(200, snap.restore(inst, snapname).encode())
            except Exception as exc:  # noqa: BLE001
                self._send(200, ("Restore-Fehler: %s" % exc).encode())
        elif path == "/api/snapshot/delete":
            ok = snap.delete(inst, q.get("file", [""])[0] or q.get("snap", [""])[0])
            self._send(200, (("geloescht" if ok else "nicht gefunden")).encode())
        elif path == "/api/cluster":
            inst.cluster_id = (q.get("cluster_id", [""])[0] or "").strip()[:64]
            inst.cluster_dir = (q.get("cluster_dir", [""])[0] or "").strip()
            inst.cluster_transfer_filtering = q.get("transfer_filtering", ["1"])[0] not in ("0", "false", "False")
            registry.save(inst)
            self._send(200, ("Cluster gespeichert - ID %s, Verzeichnis %s. Neustart noetig."
                             % (inst.cluster_name, inst.cluster_path)).encode())
        elif path == "/api/settings":
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8", "replace") if length else "[]"
            try:
                items = json.loads(raw)
            except ValueError:
                items = []
            if inst.game != "ark":
                changed = inst.profile.apply_settings(inst, items)
                inst.save(os.path.expanduser("~/.config/polypanel/%s.json" % inst.name))
                inst.write_ini()
            else:
                changed = 0
                for item in items:
                    try:
                        cfgfile.set_value(inst, item["file"], item["section"], item["key"],
                                          str(item.get("value", "")))
                        changed += 1
                    except (KeyError, TypeError):
                        continue
            self._send(200, ("%d Einstellung(en) gespeichert - wirksam nach Neustart"
                             % changed).encode())
        elif path == "/api/backup":
            try:
                info = bk.create(inst)
                self._send(200, ("Backup erstellt: %s (%.1f MB)" % (info["file"], info["size_mb"])).encode())
            except Exception as exc:  # noqa: BLE001
                self._send(200, ("Backup-Fehler: %s" % exc).encode())
        elif path == "/api/backup/restore":
            fname = q.get("file", [""])[0]
            try:
                self._send(200, bk.restore(inst, fname).encode())
            except Exception as exc:  # noqa: BLE001
                self._send(200, ("Restore-Fehler: %s" % exc).encode())
        elif path == "/api/backup/delete":
            ok = bk.delete(inst, q.get("file", [""])[0])
            self._send(200, (("geloescht" if ok else "nicht gefunden")).encode())
        elif path == "/api/tasks":
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8", "replace") if length else "{}"
            try:
                payload = json.loads(raw)
            except ValueError:
                self._send(400, b"ungueltiges JSON")
                return
            tasks = payload.get("tasks") if isinstance(payload, dict) else None
            if not isinstance(tasks, list):
                self._send(400, b"tasks fehlt")
                return
            clean = []
            for item in tasks[:50]:
                if not isinstance(item, dict):
                    continue
                action = str(item.get("action") or "").strip()
                if action not in supervisor.Supervisor.TASK_ACTIONS:
                    continue
                tm = str(item.get("time") or "").strip()
                if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", tm):
                    continue
                days = [int(d) for d in (item.get("days") or []) if str(d).isdigit() and 1 <= int(d) <= 7]
                clean.append({
                    "id": str(item.get("id") or "")[:32] or "t%d-%d" % (int(time.time() * 1000), len(clean)),
                    "action": action,
                    "time": tm,
                    "days": sorted(set(days)),
                    "arg": str(item.get("arg") or "")[:300],
                    "on": bool(item.get("on", True)),
                })
            inst.tasks = clean
            registry.save(inst)
            self._json({"ok": True, "tasks": clean})
        elif path == "/api/schedule":
            def _times(key: str) -> list[str]:
                raw = q.get(key, [""])[0]
                return [t.strip() for t in raw.split(",") if t.strip()]
            if "restart" in q:
                inst.restart_times = _times("restart")
            if "warn" in q and q["warn"][0].isdigit():
                inst.warn_minutes = int(q["warn"][0])
            if "keep" in q and q["keep"][0].isdigit():
                inst.backups_keep = int(q["keep"][0])
            if "snaptimes" in q:
                inst.snapshot_times = _times("snaptimes")
            if "snapkeep" in q and q["snapkeep"][0].isdigit():
                inst.snapshot_keep = max(1, min(20, int(q["snapkeep"][0])))
            registry.save(inst)
            self._send(200, ("Zeitplan gespeichert: Neustart %s | Backup %s | Vorwarnung %d min"
                             % (", ".join(inst.restart_times) or "-",
                                ", ".join(inst.backup_times) or "-", inst.warn_minutes)).encode())
        elif path == "/api/config":
            which = q.get("file", ["gus"])[0]
            length = int(self.headers.get("Content-Length") or 0)
            text = self.rfile.read(length).decode("utf-8", "replace") if length else ""
            try:
                backup = cfgfile.write(inst, which, text)
                self._send(200, ("gespeichert%s" % ((" (Sicherung: %s)" % os.path.basename(backup))
                                                   if backup else "")).encode())
            except ValueError as exc:
                self._send(200, ("Fehler: %s" % exc).encode())
        elif path == "/api/lang":
            value = q.get("set", [""])[0].lower()
            try:
                i18n.set_lang(value)
                self._send(200, ("lang=%s" % value).encode())
            except ValueError:
                self._send(400, b"unbekannte Sprache")
        elif path == "/api/command":
            entry = cmdreg.by_id(q.get("id", [""])[0])
            if not entry:
                self._send(400, b"unbekannter Befehl")
                return
            values = {name: q.get(name, [""])[0] for name, _qq, _dd in entry["args"]}
            cmd = cmdreg.build(entry["id"], values) or ""
            try:
                out = rcon_cmd(inst, cmd)
                self._send(200, ("$ %s\n%s" % (cmd, out or "(keine Antwort)")).encode())
            except Exception as exc:  # noqa: BLE001
                self._send(200, ("$ %s\nRCON-Fehler: %s" % (cmd, exc)).encode())
        elif path == "/api/player/action":
            steamid = q.get("steamid", [""])[0]
            tpl = PLAYER_ACTIONS.get(q.get("action", [""])[0])
            if not steamid or not tpl:
                self._send(400, b"steamid/action fehlt")
                return
            try:
                self._send(200, (rcon_cmd(inst, tpl % steamid) or "ok").encode())
            except Exception as exc:  # noqa: BLE001
                self._send(200, ("RCON-Fehler: %s" % exc).encode())
        elif path == "/api/player/give":
            steamid = q.get("steamid", [""])[0]
            bp = q.get("bp", [""])[0]
            qty = q.get("qty", ["1"])[0]
            if not steamid or not bp:
                self._send(400, b"steamid/bp fehlt")
                return
            try:
                self._send(200, rcon_cmd(inst, "GiveItemToPlayer %s %s %s 0 0" % (steamid, bp, qty)).encode())
            except Exception as exc:  # noqa: BLE001
                self._send(200, ("RCON-Fehler: %s" % exc).encode())
        else:
            self._send(404, b"unbekannt")


def serve(host: str = "127.0.0.1", port: int = 8790,
          cert: str = "", key: str = "") -> None:
    srv = ThreadingHTTPServer((host, port), Handler)
    scheme = "http"
    if cert and key:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert, key)
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
        scheme = "https"
    print("PolyPanel UI: %s://%s:%d/?token=%s" % (scheme, host, port, token()), flush=True)
    srv.serve_forever()
