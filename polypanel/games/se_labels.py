"""Deutsche Bezeichnungen fuer die restlichen Space-Engineers-Optionen.

Aufbau: KEY: (Label, Hinweis). Hinweis darf leer sein.
"""

EXTRA = {
    # --- Limits & PCU
    "BlocksInventorySizeMultiplier": ("Block-Inventar (Faktor)", "groesser = mehr Platz in Block-Inventaren"),
    "TotalBotLimit": ("Max. Bots gesamt", "Obergrenze aller NPC-Einheiten"),
    "MaxGridSize": ("Max. Grid-Groesse", "Anzahl Bloecke pro Grid"),
    "MaxBlocksPerPlayer": ("Max. Bloecke pro Spieler", "0 = unbegrenzt"),
    "TotalPCU": ("PCU gesamt", "Baubudget der ganzen Welt"),
    "PiratePCU": ("PCU fuer Piraten", "Budget fuer NPC-Piraten"),
    "GlobalEncounterPCU": ("PCU fuer Begegnungen", "Budget fuer Encounter-Einheiten"),
    "MaxFactionsCount": ("Max. Fraktionen", "Anzahl erlaubter Fraktionen"),
    "BlockLimitsEnabled": ("Blocklimits aktiv", "NONE, GLOBALLY, PER_PLAYER, PER_FACTION"),
    "BlockTypeLimits": ("Limits je Blocktyp", "Liste der Blockbeschraenkungen"),
    "LimitBlocksBy": ("Blocklimit gilt fuer", "Spieler oder Fraktion"),
    "MaxProductionQueueLength": ("Max. Produktionswarteschlange", "Auftraege pro Produktionsblock"),

    # --- Bauen & Technik
    "EnableRemoteBlockRemoval": ("Blöcke aus der Ferne entfernen", "true = Abbau ohne hinzugehen"),
    "EnableSaving": ("Speichern erlaubt", "false = Welt wird nicht gespeichert"),
    "InfiniteAmmo": ("Unendlich Munition", "true = kein Munitionsverbrauch"),
    "EnableContainerDrops": ("Container-Drops", "Loot faellt beim Zerstoeren"),
    "StationVoxelSupport": ("Stations-Voxel", "Voxel an Stationen erlaubt"),
    "EnableRespawnShips": ("Respawn-Schiffe", "true = Startschiffe verfuegbar"),
    "UpdateRespawnDictionary": ("Respawn-Liste erneuern", "Startschiffe neu einlesen"),
    "BlueprintShare": ("Blueprints teilen", "Spieler duerfen Blueprints teilen"),
    "BlueprintShareTimeout": ("Blueprint-Timeout", "Sekunden bis Teilen endet"),
    "EnableScripterRole": ("Scripter-Rolle", "true = Skripte fuer bestimmte Rollen"),
    "EnableTurretsFriendlyFire": ("Geschuetze beschaedigen Freunde", "true = Eigenbeschuss moeglich"),
    "EnableSubgridDamage": ("Subgrid-Schaden", "true = Schaden wird auf Subgrids uebertragen"),
    "EnableSupergridding": ("Supergridding", "true = Bloecke frei skalieren (experimentell)"),
    "EnableVoxelHand": ("Voxel-Hand", "true = Gelaende im Spiel bearbeiten"),
    "EnableSelectivePhysicsUpdates": ("Selektive Physik-Updates", "nur nahe Grids simulieren"),
    "AdjustableMaxVehicleSpeed": ("Einstellbare Max-Geschwindigkeit", "true = Speed-Limit per Mod"),
    "ExperimentalMode": ("Experimentalmodus", "schaltet experimentelle Bloecke frei"),
    "AdaptiveSimulationQuality": ("Adaptive Simulationsqualitaet", "true = Qualitaet passt sich an"),
    "SimplifiedSimulation": ("Vereinfachte Simulation", "weniger Physik, mehr Performance"),
    "SyncDistance": ("Sync-Distanz", "Meter, ab denen Grids synchronisiert werden"),
    "MaxCargoBags": ("Max. Frachtbeutel", "herumliegende Cargo-Bags"),
    "TemporaryContainers": ("Temporaere Container", "true = Beutel verschwinden wieder"),
    "EnableShareInertiaTensor": ("Traegheitstensor teilen", "stabilisiert grosse Grids"),
    "EnableUnsafePistonImpulses": ("Unsichere Kolben-Impulse", "Clang-Risiko, true = alte Physik"),
    "EnableUnsafeRotorTorques": ("Unsichere Rotor-Kraefte", "Clang-Risiko, true = alte Physik"),
    "PrefetchShapeRayLengthLimit": ("Raycast-Laenge", "Limit fuer Formabfragen"),
    "ResetForageableItems": ("Sammelobjekte zuruecksetzen", "true = Pflanzen/Erze erscheinen neu"),
    "ResetForageableItemsTimeM": ("Sammelobjekte-Reset (Minuten)", "Zeit bis Nachwachsen"),
    "ResetForageableItemsDistance": ("Sammelobjekte-Reset (Distanz)", "Meter Abstand zum Spieler"),

    # --- Muell / Aufraeumen
    "TrashRemovalEnabled": ("Muell-Entfernung", "true = ungenutzte Grids werden geloescht"),
    "StopGridsPeriodMin": ("Grids anhalten nach (Minuten)", "Leerlauf bis Stillstand"),
    "TrashFlagsValue": ("Muell-Kriterien", "Bitmaske der Loeschbedingungen"),
    "AFKTimeountMin": ("AFK-Zeit (Minuten)", "ab hier gilt ein Spieler als inaktiv"),
    "BlockCountThreshold": ("Blockzahl-Schwelle", "ab dieser Groesse gilt ein Grid als Muell"),
    "PlayerDistanceThreshold": ("Spielerabstand-Schwelle", "Meter zum naechsten Spieler"),
    "OptimalGridCount": ("Optimale Grid-Anzahl", "Zielwert fuer die Simulation"),
    "PlayerInactivityThreshold": ("Inaktivitaets-Schwelle", "Sekunden ohne Aktion"),
    "PlayerCharacterRemovalThreshold": ("Charakter-Entfernung", "Sekunden bis Leichen verschwinden"),
    "VoxelTrashRemovalEnabled": ("Voxel-Muell entfernen", "abgebaute Voxel aufraeumen"),
    "VoxelPlayerDistanceThreshold": ("Voxel: Spielerabstand", "Meter"),
    "VoxelGridDistanceThreshold": ("Voxel: Gridabstand", "Meter"),
    "VoxelAgeThreshold": ("Voxel: Alter", "Minuten bis Aufraeumen"),
    "TrashCleanerCargoBagsMaxLiveTime": ("Cargo-Beutel Lebenszeit", "Minuten"),
    "EnableTrashSettingsPlatformOverride": ("Plattform-Regeln ueberschreiben", "Server darf Muellregeln setzen"),

    # --- Forschung, Wirtschaft, NPC
    "EnableResearch": ("Forschung", "true = Forschungspunkte aktiv"),
    "EnableGoodBotHints": ("Bot-Hinweise", "Tipps fuer Anfaenger"),
    "OptimalSpawnDistance": ("Optimaler Spawnabstand", "Meter"),
    "EnableAutorespawn": ("Automatischer Respawn", "true = Spieler respawnen automatisch"),
    "EnableBountyContracts": ("Kopfgeld-Auftraege", "true = Contract-System aktiv"),
    "EnableEconomy": ("Wirtschaft", "true = Handel und Kontore"),
    "DepositsCountCoefficient": ("Erzvorkommen (Faktor)", "hoeher = mehr Vorkommen"),
    "DepositSizeDenominator": ("Erzvorkommen-Groesse", "groesser = kleinere Vorkommen"),
    "TradeFactionsCount": ("Handelsfraktionen", "Anzahl NPC-Haendler"),
    "StationsDistanceInnerRadius": ("Stationen: Innenradius", "km"),
    "StationsDistanceOuterRadiusStart": ("Stationen: Aussenradius ab", "km"),
    "StationsDistanceOuterRadiusEnd": ("Stationen: Aussenradius bis", "km"),
    "EconomyTickInSeconds": ("Wirtschafts-Tick", "Sekunden zwischen Berechnungen"),
    "NPCGridClaimTimeLimit": ("NPC-Grid Uebernahmezeit", "Minuten bis Claim endet"),
    "EnablePcuTrading": ("PCU handeln", "true = PCU kaufbar"),
    "ReputationDecayRate": ("Ruf-Verfall", "pro Tag"),
    "EnableFactionPlayerNames": ("Fraktion im Spielernamen", "true = Tag anzeigen"),
    "EnableFactionVoiceChat": ("Fraktions-Sprachchat", "true/false"),
    "EnableSpaceSuitRespawn": ("Respawn im Spacesuit", "true = ohne Medbay"),
    "EnableReducedStatsOnRespawn": ("Geschwaechte Werte nach Respawn", "true/false"),
    "FoodConsumptionRate": ("Nahrungsverbrauch", "Faktor"),
    "EnableSurvivalBuffs": ("Ueberlebens-Buffs", "true = Nahrung gibt Bonus"),
    "EnableRadiation": ("Strahlung", "true = Strahlungsschaeden"),
    "SolarRadiationIntensity": ("Sonnenstrahlung", "Intensitaet"),
    "EnableOrca": ("Orca-Wale", "true/false"),

    # --- Begegnungen (Encounter)
    "GlobalEncounterTimer": ("Begegnungen: Timer", "Sekunden zwischen Encountern"),
    "GlobalEncounterCap": ("Begegnungen: Obergrenze", "gleichzeitig aktive Encounter"),
    "GlobalEncounterEnableRemovalTimer": ("Begegnungen: Entfernen nach Zeit", "true/false"),
    "GlobalEncounterMinRemovalTimer": ("Begegnungen: Entfernen ab", "Minuten"),
    "GlobalEncounterMaxRemovalTimer": ("Begegnungen: Entfernen bis", "Minuten"),
    "GlobalEncounterRemovalTimeClock": ("Begegnungen: Uhrzeit", "Zeitfenster fuer Aufraeumen"),
    "EncounterDensity": ("Begegnungsdichte", "Faktor"),
    "EncounterGeneratorVersion": ("Encounter-Generator", "Version"),
    "EnablePlanetaryEncounters": ("Planeten-Begegnungen", "true = NPC-Stationen auf Planeten"),
    "PlanetaryEncounterTimerMin": ("Planeten-Begegnung: min.", "Sekunden"),
    "PlanetaryEncounterTimerMax": ("Planeten-Begegnung: max.", "Sekunden"),
    "PlanetaryEncounterTimerFirst": ("Planeten-Begegnung: erster Spawn", "Sekunden"),
    "PlanetaryEncounterExistingStructuresRange": ("Planeten-Begegnung: Abstand zu Bauwerken", "Meter"),
    "PlanetaryEncounterAreaLockdownRange": ("Planeten-Begegnung: Sperrbereich", "Meter"),
    "PlanetaryEncounterDesiredSpawnRange": ("Planeten-Begegnung: Spawnabstand", "Meter"),
    "PlanetaryEncounterPresenceRange": ("Planeten-Begegnung: Anwesenheitsradius", "Meter"),
    "PlanetaryEncounterDespawnTimeout": ("Planeten-Begegnung: Despawn", "Minuten"),
    "PredefinedAsteroids": ("Vordefinierte Asteroiden", "true = feste Feldstruktur"),
    "AsteroidAmount": ("Asteroidenmenge", "0 = Standard"),
    "MaxPlanets": ("Max. Planeten", "0 = Standard"),
    "MinimumWorldSize": ("Min. Weltgroesse", "km"),
    "RandomizeSeed": ("Zufaelliger Seed", "true = neue Welt pro Start"),

    # --- Kampf / Match
    "EnableMatchComponent": ("Matchmodus", "true = rundenbasiertes Match"),
    "PreMatchDuration": ("Match: Vorbereitung", "Sekunden"),
    "MatchDuration": ("Match: Dauer", "Minuten"),
    "PostMatchDuration": ("Match: Nachlauf", "Sekunden"),
    "EnableFriendlyFire": ("Friendly Fire", "true = Teammitglieder verletzen"),
    "EnableTeamBalancing": ("Team-Balance", "true = Teams automatisch ausgleichen"),
    "CharacterSpeedMultiplier": ("Charaktergeschwindigkeit", "Faktor"),
    "EnableRecoil": ("Rueckstoss", "true/false"),
    "EnvironmentDamageMultiplier": ("Umgebungsschaden", "Faktor"),
    "EnableGamepadAimAssist": ("Gamepad-Zielhilfe", "true/false"),
    "BackpackDespawnTimer": ("Rucksack-Despawn", "Minuten"),
    "EnableTeamScoreCounters": ("Team-Punktezaehler", "true/false"),
    "MatchRestartWhenEmptyTime": ("Match-Neustart wenn leer", "Minuten"),
    "EnemyTargetIndicatorDistance": ("Feind-Anzeige (Distanz)", "Meter"),
    "WeatherSystem": ("Wettersystem", "true = Wetter auf Planeten"),
    "WeatherLightingDamage": ("Wetterschaden", "true = Wetter verursacht Schaden"),
    "HarvestRatioMultiplier": ("Abbaurate (Faktor)", "hoeher = mehr Ertrag"),
    "ScrapEnabled": ("Schrott", "true = Schrott-Modus"),

    # --- Chat & Netzwerk
    "MaxHudChatMessageCount": ("Chat-Nachrichten im HUD", "Anzahl"),
    "ChatAntiSpamEnabled": ("Anti-Spam", "true = Spamschutz aktiv"),
    "SameMessageTimeout": ("Gleiche Nachricht (Timeout)", "Sekunden"),
    "SpamMessagesTime": ("Spam-Zeitfenster", "Sekunden"),
    "SpamMessagesTimeout": ("Spam-Sperre", "Sekunden"),
    "NetworkType": ("Netzwerktyp", "Steam oder Direct IP"),
    "NetworkParameters": ("Netzwerkparameter", "Feintuning, meist leer"),
    "VerboseNetworkLogging": ("Ausfuehrliches Netzwerk-Log", "true = mehr Logzeilen"),
    "ConsoleCompatibility": ("Konsolen-Kompatibilitaet", "true = Konsolenbefehle erlaubt"),
    "CrossPlatform": ("Plattformuebergreifend", "true = PC + Konsole"),
    "FamilySharing": ("Familiensharing", "true = geteilte Steam-Bibliothek erlaubt"),
    "ServerPasswordSalt": ("Passwort-Salt", "intern, nicht aendern"),
    "DedicatedId": ("Dedicated-ID", "interne Kennung des Servers"),
    "Reserved": ("Reserviert", "nicht belegen"),

    # --- Server-Betrieb
    "Administrators": ("Administratoren", "Steam-ID64, je Zeile einer"),
    "Banned": ("Gesperrte Spieler", "Steam-ID64, je Zeile einer"),
    "GroupID": ("Gruppen-ID", "Steam-Gruppe fuer den Server"),
    "MessageOfTheDay": ("Nachricht des Tages", "Text beim Beitritt"),
    "MessageOfTheDayUrl": ("MOTD-URL", "Quelle fuer den Text"),
    "AutoRestartEnabled": ("Auto-Neustart", "true = Server startet selbst neu"),
    "AutoRestatTimeInMin": ("Auto-Neustart nach (Minuten)", "Intervall"),
    "AutoRestartSave": ("Vor Neustart speichern", "true/false"),
    "AutoUpdateEnabled": ("Auto-Update", "true = SteamCMD-Update automatisch"),
    "AutoUpdateCheckIntervalInMin": ("Update-Pruefung (Minuten)", "Intervall"),
    "AutoUpdateRestartDelayInMin": ("Neustart nach Update (Minuten)", "Verzoegerung"),
    "IgnoreLastSession": ("Letzte Sitzung ignorieren", "true = immer frisch starten"),
    "PremadeCheckpointPath": ("Vorlagen-Welt", "Pfad zur Welt, aus der neu erzeugt wird"),
    "Plugins": ("Plugins", "Plugin-Pfade, je Zeile einer"),
    "WatcherInterval": ("Watcher-Intervall", "Sekunden"),
    "WatcherSimulationSpeedMinimum": ("Watcher: min. Simulationsgeschwindigkeit", "0-1"),
    "ManualActionDelay": ("Verzoegerung manueller Aktionen", "Sekunden"),
    "ManualActionChatMessage": ("Chattext bei Aktionen", "Meldung im Spiel"),
    "AutodetectDependencies": ("Abhaengigkeiten erkennen", "true = Mods pruefen"),
    "SaveChatToLog": ("Chat ins Log schreiben", "true/false"),
    "RemoteApiEnabled": ("Remote-API", "true = REST-API auf RemoteApiPort"),
    "RemoteApiPort": ("Remote-API-Port", "Standard 8080"),
}

EXTRA.update({
    "EnableWolfs": ('Woelfe', 'true = Woelfe auf Planeten'),
    "MinDropContainerRespawnTime": ('Loot-Container: min. Respawn', 'Minuten'),
    "MaxDropContainerRespawnTime": ('Loot-Container: max. Respawn', 'Minuten'),
    "RemoveOldIdentitiesH": ('Alte Identitaeten entfernen', 'Stunden bis Aufraeumen'),
    "SuppressedWarnings": ('Unterdrueckte Warnungen', 'Liste der ausgeblendeten Hinweise'),
    "UseConsolePCU": ('PCU fuer Konsolen', 'eigenes PCU-Limit fuer Konsolen'),
    "OffensiveWordsFiltering": ('Wortfilter', 'true = beleidigende Woerter filtern'),
    "BroadcastControllerMaxOfflineTransmitDistance": ('Broadcast-Sender: Offline-Reichweite', 'Meter'),
    "GridStorageAllowsInventory": ('Grid-Speicher: Inventar', 'true = Inventar im Speicher erlaubt'),
    "GridStorageMaxPerPlayer": ('Grid-Speicher: max. pro Spieler', 'Anzahl'),
    "GridStorageQueueLimit": ('Grid-Speicher: Warteschlange', 'max. Auftraege'),
    "GridStorageRetrievalTimeMaxMinutes": ('Grid-Speicher: Abruf max.', 'Minuten'),
    "GridStorageRetrievalTimeMinMinutes": ('Grid-Speicher: Abruf min.', 'Minuten'),
    "GridStorageRetrievalTimeMultiplier": ('Grid-Speicher: Abruf-Faktor', 'Faktor'),
    "GridStorageMinutesPerPCU": ('Grid-Speicher: Minuten pro PCU', 'Zeitguthaben'),
    "GridStorageMinutesPerKm": ('Grid-Speicher: Minuten pro km', 'Zeitguthaben'),
    "GridStorageExpediteFactor": ('Grid-Speicher: Express-Faktor', 'Beschleunigung'),
    "GridStorageExpediteCostPerSecond": ('Grid-Speicher: Express-Kosten', 'pro Sekunde'),
    "GridStorageCombatCooldown": ('Grid-Speicher: Kampf-Sperre', 'Sekunden'),
    "GridStorageMaxDistance": ('Grid-Speicher: max. Distanz', 'Meter'),
    "Plugins": ('Plugins (Pfade)', 'je Zeile ein Plugin-Pfad'),
})


# ------------------------------------------------------------------ Gruppen
# Die Abschnitte oben ("# --- Titel") bestimmen den Reiter im Einstellungs-Formular.
# Erlaubt sind nur die Gruppen aus SETGROUP_ORDER der Web-UI, eigene Slugs werden
# stillschweigend verworfen - deshalb hier auf bekannte Slugs abgebildet.
import re as _re

_ABSCHNITT = {
    "Limits & PCU": "struct",
    "Bauen & Technik": "struct",
    "Muell / Aufraeumen": "welt",
    "Forschung, Wirtschaft, NPC": "play",
    "Begegnungen (Encounter)": "welt",
    "Kampf / Match": "pvp",
    "Chat & Netzwerk": "netz",
    "Server-Betrieb": "server",
}


def _gruppen() -> dict:
    """{Schluessel: Gruppe} aus den Abschnittskommentaren dieser Datei."""
    text = open(__file__, encoding="utf-8").read()
    aktuell, ergebnis = "weitere", {}
    for zeile in text.splitlines():
        m = _re.match(r"\s*# --- (.+)$", zeile)
        if m:
            aktuell = _ABSCHNITT.get(m.group(1).strip(), "weitere")
            continue
        m = _re.match(r'\s*"([A-Za-z0-9_]+)"\s*:', zeile)
        if m:
            ergebnis[m.group(1)] = aktuell
    return ergebnis


GRUPPE = _gruppen()
