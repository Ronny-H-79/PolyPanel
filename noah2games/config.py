"""Config-Editor fuer GameUserSettings.ini und Game.ini (mit Sicherungskopie)."""
from __future__ import annotations

import os
import shutil
import time

from .instance import Instance

FILES = {"gus": "GameUserSettings.ini", "game": "Game.ini"}

MAX_BYTES = 512 * 1024

# Haeufig gebrauchte Einstellungen: (datei, sektion, schluessel, label, hinweis)
KNOWN = [
    # (datei, sektion, schluessel, label, hinweis, typ)
    ("gus", "MessageOfTheDay", "Message", "MOTD-Text", "erscheint beim Verbinden, mehrere Zeilen erlaubt", "longtext"),
    ("gus", "MessageOfTheDay", "Duration", "MOTD-Dauer (Sekunden)", "Standard 60", "int"),
    ("gus", "ServerSettings", "ServerPVE", "PvE-Modus", "PvP aus, PvE an", "bool"),
    ("gus", "ServerSettings", "ServerHardcore", "Hardcore", "Tod = Charakter weg", "bool"),
    ("gus", "ServerSettings", "DifficultyOffset", "Schwierigkeit", "0.0 - 1.0 (1.0 = max. Level)", "float"),
    ("gus", "ServerSettings", "OverrideOfficialDifficulty", "Offizielle Schwierigkeit ueberschreiben", "z. B. 5.0", "float"),
    ("gus", "ServerSettings", "MaxPlayers", "Max. Spieler", "1 - 70 (auf Steam)", "int"),
    ("gus", "ServerSettings", "ServerAdminPassword", "Admin-Passwort", "leer = kein Admin-Zugang", "text"),
    ("gus", "ServerSettings", "ServerPassword", "Server-Passwort", "leer = Server offen", "text"),
    ("gus", "ServerSettings", "RCONEnabled", "RCON aktiv", "muss True sein fuer diesen Manager", "bool"),
    ("gus", "ServerSettings", "RCONPort", "RCON-Port", "TCP-Port", "int"),
    ("gus", "ServerSettings", "AutoSavePeriodMinutes", "Autosave (Minuten)", "Standard 15", "float"),
    ("gus", "ServerSettings", "TamingSpeedMultiplier", "Zaehmgeschwindigkeit", "1.0 = offiziell, 5.0 = 5x", "float"),
    ("gus", "ServerSettings", "XPMultiplier", "XP-Multiplikator", "1.0 = offiziell", "float"),
    ("gus", "ServerSettings", "HarvestAmountMultiplier", "Erntemenge", "1.0 = offiziell", "float"),
    ("gus", "ServerSettings", "HarvestHealthMultiplier", "Ernte-Zaehigkeit", "hoeher = mehr pro Schlag", "float"),
    ("gus", "ServerSettings", "DinoCharacterFoodDrainMultiplier", "Dino-Futterverbrauch", "1.0 = offiziell", "float"),
    ("gus", "ServerSettings", "PlayerCharacterFoodDrainMultiplier", "Spieler-Hunger", "1.0 = offiziell", "float"),
    ("gus", "ServerSettings", "PlayerCharacterWaterDrainMultiplier", "Spieler-Durst", "1.0 = offiziell", "float"),
    ("gus", "ServerSettings", "DinoCountMultiplier", "Dino-Dichte", "1.0 = offiziell", "float"),
    ("gus", "ServerSettings", "DayTimeSpeedScale", "Tagesgeschwindigkeit", "1.0 = offiziell", "float"),
    ("gus", "ServerSettings", "NightTimeSpeedScale", "Nachtgeschwindigkeit", "1.0 = offiziell", "float"),
    ("gus", "ServerSettings", "AllowThirdPersonPlayer", "Third-Person erlauben", "", "bool"),
    ("gus", "ServerSettings", "ShowMapPlayerLocation", "Eigene Position auf Karte", "", "bool"),
    ("gus", "ServerSettings", "AllowCaveBuildingPvE", "Bauen in Hoehlen (PvE)", "", "bool"),
    ("gus", "ServerSettings", "KickIdlePlayersPeriod", "Idle-Kick nach (Sekunden)", "3600 = 1 Stunde", "int"),
    ("gus", "ServerSettings", "AdminLogging", "Admin-Befehle im Chat loggen", "", "bool"),
    ("gus", "SessionSettings", "SessionName", "Session-Name", "Name in der Serverliste", "text"),
    ("game", "/script/shootergame.shootergamemode", "MatingIntervalMultiplier", "Paarungsintervall", "1.0 = offiziell", "float"),
    ("game", "/script/shootergame.shootergamemode", "EggHatchSpeedMultiplier", "Ei-Schluepfgeschwindigkeit", "1.0 = offiziell", "float"),
    ("game", "/script/shootergame.shootergamemode", "BabyMatureSpeedMultiplier", "Baby-Wachstum", "1.0 = offiziell", "float"),
    ("game", "/script/shootergame.shootergamemode", "BabyFoodConsumptionSpeedMultiplier", "Baby-Futterverbrauch", "1.0 = offiziell", "float"),
    ("game", "/script/shootergame.shootergamemode", "BabyImprintingStatScaleMultiplier", "Praegungs-Bonus", "1.0 = offiziell", "float"),
    ("game", "/script/shootergame.shootergamemode", "CropGrowthSpeedMultiplier", "Pflanzenwachstum", "1.0 = offiziell", "float"),
    ("game", "/script/shootergame.shootergamemode", "LayEggIntervalMultiplier", "Ei-Abstand", "1.0 = offiziell", "float"),
    ("game", "/script/shootergame.shootergamemode", "StructureDamageMultiplier", "Struktur-Schaden", "1.0 = offiziell", "float"),
    ("game", "/script/shootergame.shootergamemode", "PerLevelStatsMultiplier_DinoTamed_Add[0]", "Dino-HP pro Level (zusaetzlich)", "1.0 = offiziell", "float"),
    ("gus", "ServerSettings", "NoTributeDownloads", "Tribute-Downloads sperren", "kein Herunterladen von Obelisken/Transmittern", "bool"),
    ("gus", "ServerSettings", "PreventDownloadSurvivors", "Spieler-Download sperren", "", "bool"),
    ("gus", "ServerSettings", "PreventDownloadItems", "Item-Download sperren", "", "bool"),
    ("gus", "ServerSettings", "PreventDownloadDinos", "Dino-Download sperren", "", "bool"),
    ("gus", "ServerSettings", "PreventUploadSurvivors", "Spieler-Upload sperren", "", "bool"),
    ("gus", "ServerSettings", "PreventUploadItems", "Item-Upload sperren", "", "bool"),
    ("gus", "ServerSettings", "PreventUploadDinos", "Dino-Upload sperren", "", "bool"),
    ("gus", "ServerSettings", "CrossARKAllowForeignDinoDownloads", "Fremde Cluster-Dinos erlauben", "", "bool"),
    ("gus", "ServerSettings", "AllowFlyerCarryPvP", "Flieger tragen Spieler (PvP)", "", "bool"),
    ("gus", "ServerSettings", "AllowRaidDinoFeeding", "Raid-Dinos füttern", "", "bool"),
    ("gus", "ServerSettings", "AllowMultipleAttachedC4", "Mehrere C4 an einem Ziel", "", "bool"),
    ("gus", "ServerSettings", "PreventOfflinePvP", "Offline-Raid-Schutz", "", "bool"),
    ("gus", "ServerSettings", "PreventOfflinePvPInterval", "Schutz-Verzögerung (Sekunden)", "", "float"),
    ("gus", "ServerSettings", "PreventTribeAlliances", "Tribe-Allianzen verbieten", "", "bool"),
    ("gus", "ServerSettings", "MaxNumberOfPlayersInTribe", "Max. Spieler pro Tribe", "", "int"),
    ("gus", "ServerSettings", "TribeNameChangeCooldown", "Tribe-Namenswechsel (Sekunden)", "", "float"),
    ("gus", "ServerSettings", "PvPStructureDecay", "Struktur-Verfall im PvP", "", "bool"),
    ("gus", "ServerSettings", "PvEStructureDecayPeriodMultiplier", "Verfallszeit (PvE)", "höher = langsamer", "float"),
    ("gus", "ServerSettings", "DisableStructureDecayPvE", "Struktur-Verfall (PvE) aus", "", "bool"),
    ("gus", "ServerSettings", "ForceAllStructureLocking", "Alle Strukturen abschließbar", "", "bool"),
    ("gus", "ServerSettings", "AlwaysAllowStructurePickup", "Strukturen immer aufhebbar", "", "bool"),
    ("gus", "ServerSettings", "StructurePickupTimeAfterPlacement", "Aufheben erlaubt nach (Sekunden)", "", "float"),
    ("gus", "ServerSettings", "OverrideStructurePlatformPrevention", "Bauen auf Plattformen erlauben", "", "bool"),
    ("gus", "ServerSettings", "TheMaxStructuresInRange", "Max. Strukturen im Umkreis", "", "int"),
    ("gus", "ServerSettings", "StructureDamageRepairCooldown", "Reparatur-Cooldown (Sekunden)", "", "float"),
    ("gus", "ServerSettings", "AutoDestroyDecayedDinos", "Verfallene Dinos entfernen", "", "bool"),
    ("gus", "ServerSettings", "DisableDinoDecayPvE", "Dino-Verfall (PvE) aus", "", "bool"),
    ("gus", "ServerSettings", "PvEDinoDecayPeriodMultiplier", "Dino-Verfallszeit (PvE)", "höher = langsamer", "float"),
    ("gus", "ServerSettings", "MaxTamedDinos", "Max. gezähmte Dinos", "", "int"),
    ("gus", "ServerSettings", "MaxPersonalTamedDinos", "Max. Dinos pro Spieler", "", "int"),
    ("gus", "ServerSettings", "AllowAnyoneBabyImprintCuddle", "Jeder darf Babys prägen", "", "bool"),
    ("gus", "ServerSettings", "DisableImprintDinoBuff", "Prägungs-Bonus abschalten", "", "bool"),
    ("gus", "ServerSettings", "RaidDinoCharacterFoodDrainMultiplier", "Raid-Dino-Futterverbrauch", "", "float"),
    ("gus", "ServerSettings", "ShowFloatingDamageText", "Schadenszahlen anzeigen", "", "bool"),
    ("gus", "ServerSettings", "AllowFlyingStaminaRecovery", "Ausdauer im Flug erholen", "", "bool"),
    ("gus", "ServerSettings", "ClampItemSpoilingTimes", "Verfallszeiten begrenzen", "", "bool"),
    ("gus", "ServerSettings", "ClampResourceHarvestDamage", "Ernte-Schaden begrenzen", "", "bool"),
    ("gus", "ServerSettings", "bDisableStructurePlacementCollision", "Kollision beim Bauen aus", "", "bool"),
    ("gus", "ServerSettings", "ResourceNoReplenishRadiusPlayers", "Kein Nachwachsen um Spieler", "", "float"),
    ("gus", "ServerSettings", "ResourceNoReplenishRadiusStructures", "Kein Nachwachsen um Bauten", "", "float"),
    ("gus", "ServerSettings", "AllowHitMarkers", "Treffer-Markierungen", "", "bool"),
    ("game", "/script/shootergame.shootergamemode", "TamedDinoCharacterFoodDrainMultiplier", "Gezähmte Dinos: Futterverbrauch", "", "float"),
    ("game", "/script/shootergame.shootergamemode", "WildDinoCharacterFoodDrainMultiplier", "Wilde Dinos: Futterverbrauch", "", "float"),
    ("game", "/script/shootergame.shootergamemode", "WildDinoTorporDrainMultiplier", "Wilde Dinos: Betäubung", "", "float"),
    ("game", "/script/shootergame.shootergamemode", "TamedDinoTorporDrainMultiplier", "Gezähmte Dinos: Betäubung", "", "float"),
    ("game", "/script/shootergame.shootergamemode", "PlayerHarvestingDamageMultiplier", "Spieler-Ernteschaden", "", "float"),
    ("game", "/script/shootergame.shootergamemode", "DinoHarvestingDamageMultiplier", "Dino-Ernteschaden", "", "float"),
    ("game", "/script/shootergame.shootergamemode", "CraftingSkillBonusMultiplier", "Handwerks-Bonus", "", "float"),
    ("game", "/script/shootergame.shootergamemode", "PassiveTameIntervalMultiplier", "Passives Zähmen: Intervall", "", "float"),
    ("game", "/script/shootergame.shootergamemode", "FuelConsumptionMultiplier", "Treibstoffverbrauch", "", "float"),
    ("game", "/script/shootergame.shootergamemode", "MatingRangeMultiplier", "Paarungs-Reichweite", "", "float"),
    ("game", "/script/shootergame.shootergamemode", "bDisableDinoTaming", "Zähmen komplett aus", "", "bool"),
    ("game", "/script/shootergame.shootergamemode", "bDisableFriendlyFire", "Eigenbeschuss aus", "", "bool"),
]


def path_for(inst: Instance, which: str) -> str:
    name = FILES.get(which)
    if not name:
        raise ValueError("unbekannte Datei: %s" % which)
    return os.path.join(inst.config_dir, name)


def read(inst: Instance, which: str) -> str:
    path = path_for(inst, which)
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError as exc:
        return "; Datei konnte nicht gelesen werden: %s" % exc


def write(inst: Instance, which: str, text: str) -> str:
    if len(text) > MAX_BYTES:
        raise ValueError("Datei zu gross (max %d Bytes)" % MAX_BYTES)
    path = path_for(inst, which)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    backup = ""
    if os.path.exists(path):
        backup = "%s.bak-%s" % (path, time.strftime("%Y%m%d-%H%M%S"))
        shutil.copy2(path, backup)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return backup


def known_for(which: str) -> list[dict]:
    from .i18n import setting
    out = []
    for (f, section, key, label, hint, _typ) in KNOWN:
        if f != which:
            continue
        label, hint = setting(key, label, hint)
        out.append({"section": section, "key": key, "label": label, "hint": hint})
    return out


def _parse_ini(text: str) -> dict[tuple[str, str], str]:
    """{ (sektion_klein, schluessel_klein): wert } aus einer INI."""
    values: dict[tuple[str, str], str] = {}
    section = ""
    for line in text.splitlines():
        raw = line.strip()
        if not raw or raw.startswith(";") or raw.startswith("#"):
            continue
        if raw.startswith("[") and raw.endswith("]"):
            section = raw[1:-1].strip().lower()
        elif "=" in raw:
            key, _, val = raw.partition("=")
            values[(section, key.strip().lower())] = val.strip()
    return values


# Reiter im Einstellungs-Formular: Schluessel -> Gruppe. Bewusst hier gepflegt,
# damit die Gruppierung zentral steht und nicht im JavaScript steckt.
_SRV = {"ServerPassword", "ServerAdminPassword", "MaxPlayers", "RCONEnabled", "RCONPort",
        "AutoSavePeriodMinutes", "KickIdlePlayersPeriod", "AdminLogging"}
_PVP = {"ServerPVE", "ServerHardcore", "AllowFlyerCarryPvP", "AllowRaidDinoFeeding",
        "AllowMultipleAttachedC4", "PreventOfflinePvP", "PreventOfflinePvPInterval",
        "PreventTribeAlliances", "MaxNumberOfPlayersInTribe", "TribeNameChangeCooldown"}
_DINO = {"MaxTamedDinos", "MaxPersonalTamedDinos", "AllowAnyoneBabyImprintCuddle",
         "DisableImprintDinoBuff", "RaidDinoCharacterFoodDrainMultiplier",
         "DinoCharacterFoodDrainMultiplier", "DinoCountMultiplier"}
_HUD = {"AllowThirdPersonPlayer", "ShowMapPlayerLocation", "ShowFloatingDamageText", "AllowHitMarkers"}
_STRUCT_EXTRA = {"AllowCaveBuildingPvE", "AutoDestroyDecayedDinos", "DisableDinoDecayPvE",
                 "PvEDinoDecayPeriodMultiplier", "bDisableStructurePlacementCollision"}
_TRANSFER_IN = {"NoTributeDownloads", "CrossARKAllowForeignDinoDownloads"}
GROUPS = ("srv", "play", "pvp", "struct", "dino", "transfer", "hud", "motd", "game")


def group_of(which: str, section: str, key: str) -> str:
    """Einstellung einem Reiter zuordnen (Reihenfolge der Pruefungen ist wichtig)."""
    if which == "game":
        return "game"
    if section == "MessageOfTheDay":
        return "motd"
    if key in _SRV or section == "SessionSettings":
        return "srv"
    if key.startswith(("PreventDownload", "PreventUpload")) or key in _TRANSFER_IN:
        return "transfer"
    if key in _PVP:
        return "pvp"
    if "Structure" in key or key in _STRUCT_EXTRA:
        return "struct"
    if key in _DINO:
        return "dino"
    if key in _HUD:
        return "hud"
    return "play"


def read_values(inst: Instance) -> list[dict]:
    """Alle bekannten Einstellungen mit aktuellem Wert (GUI-Formular)."""
    from .i18n import setting
    cache: dict[str, dict[tuple[str, str], str]] = {}
    out: list[dict] = []
    for (which, section, key, label, hint, typ) in KNOWN:
        label, hint = setting(key, label, hint)
        if which not in cache:
            cache[which] = _parse_ini(read(inst, which))
        value = cache[which].get((section.lower(), key.lower()), "")
        out.append({"file": which, "section": section, "key": key, "label": label,
                    "hint": hint, "type": typ, "value": value,
                    "group": group_of(which, section, key)})
    return out


def set_value(inst: Instance, which: str, section: str, key: str, value: str) -> None:
    """Einzelwert zeilenweise ersetzen/ergaenzen - Kommentare und Reihenfolge bleiben erhalten."""
    path = path_for(inst, which)
    backup = ""
    if os.path.exists(path):
        backup = "%s.bak-%s" % (path, time.strftime("%Y%m%d-%H%M%S"))
        shutil.copy2(path, backup)
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    else:
        lines = ["[%s]" % section]

    target = section.lower()
    current = ""
    start = end = -1
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            name = stripped[1:-1].strip().lower()
            if current == target and end < 0:
                end = idx
            current = name
            if name == target and start < 0:
                start = idx
    if start >= 0 and end < 0:
        end = len(lines)
    if start < 0:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("[%s]" % section)
        lines.append("%s=%s" % (key, value))
    else:
        replaced = False
        for idx in range(start + 1, end):
            stripped = lines[idx].strip()
            if stripped.lower().startswith(key.lower() + "=") or stripped.lower().startswith(key.lower() + " ="):
                lines[idx] = "%s=%s" % (key, value)
                replaced = True
                break
        if not replaced:
            lines.insert(end, "%s=%s" % (key, value))

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
