"""Bekannte Blueprints fuer den Gegenstands-Dialog.

Warum eine eigene Liste: `GiveItemToPlayer` braucht den vollstaendigen Blueprint-Pfad, und
der ist je Kategorie unterschiedlich aufgebaut (Weapons/, Items/Consumables/, Resources/,
Items/Armor/<Set>/). Aus einem Namen laesst er sich nicht zuverlaessig raten - deshalb steht
hier pro Eintrag der komplette Pfad, und die Oberflaeche laesst suchen statt tippen.

Alle Eintraege sind auf dem Testserver erprobt oder folgen dem verifizierten Muster der
Kit-Liste. Freie Eingabe bleibt moeglich.
"""

from typing import Iterable

W_A = "/Game/PrimalEarth/CoreBlueprints/Weapons/%s.%s"
C_A = "/Game/PrimalEarth/CoreBlueprints/Items/Consumables/%s.%s"
R_A = "/Game/PrimalEarth/CoreBlueprints/Resources/%s.%s"
I_A = "/Game/PrimalEarth/CoreBlueprints/Items/%s.%s"
ARM = "/Game/PrimalEarth/CoreBlueprints/Items/Armor/%s/%s.%s"

# (Name, Bezeichnung DE, Kategorie-Vorlage, Zusatz fuer die Vorlage (z.B. Ruestungsset))
ITEMS: list[tuple[str, str, str, str]] = [
    # Werkzeuge und Waffen
    ("PrimalItem_WeaponMetalHatchet", "Metall-Axt", "W", ""),
    ("PrimalItem_WeaponMetalPick", "Metall-Picke", "W", ""),
    ("PrimalItem_WeaponStoneHatchet", "Stein-Axt", "W", ""),
    ("PrimalItem_WeaponStonePick", "Stein-Picke", "W", ""),
    ("PrimalItem_WeaponSickle", "Sichel", "W", ""),
    ("PrimalItem_WeaponPike", "Pike", "W", ""),
    ("PrimalItem_WeaponSword", "Schwert", "W", ""),
    ("PrimalItem_WeaponCrossbow", "Armbrust", "W", ""),
    ("PrimalItem_WeaponBow", "Bogen", "W", ""),
    ("PrimalItem_WeaponLongneckRifle", "Longneck-Gewehr", "W", ""),
    ("PrimalItem_WeaponOneShotRifle", "Schrotflinte", "W", ""),
    ("PrimalItem_WeaponMachinedPistol", "Pistole", "W", ""),
    ("PrimalItem_WeaponMachinedSniper", "Scharfschuetzengewehr", "W", ""),
    ("PrimalItem_WeaponRocketLauncher", "Raketenwerfer", "W", ""),
    ("PrimalItem_WeaponC4", "C4", "W", ""),
    ("PrimalItem_WeaponGrenade", "Granate", "W", ""),
    ("PrimalItem_WeaponTorch", "Fackel", "W", ""),
    ("PrimalItem_WeaponSpyglass", "Fernglas", "W", ""),
    # Munition
    ("PrimalItemAmmo_ArrowStone", "Steinpfeile", "I", ""),
    ("PrimalItemAmmo_ArrowFlame", "Feuerpfeile", "I", ""),
    ("PrimalItemAmmo_ArrowTranq", "Tranqpfeile", "I", ""),
    ("PrimalItemAmmo_AdvancedBullet", "Gewehrmunition", "I", ""),
    ("PrimalItemAmmo_SimpleBullet", "Pistolenmunition", "I", ""),
    ("PrimalItemAmmo_SimpleShotgunBullet", "Schrotmunition", "I", ""),
    ("PrimalItemAmmo_Rocket", "Rakete", "I", ""),
    # Verbrauch
    ("PrimalItemConsumable_Narcotic", "Narkotika", "C", ""),
    ("PrimalItemConsumable_Stimulant", "Stimulans", "C", ""),
    ("PrimalItemConsumable_HealSoup", "Medizin-Brew", "C", ""),
    ("PrimalItemConsumable_StaminaSoup", "Energie-Brew", "C", ""),
    ("PrimalItemConsumable_WaterJarRefill", "Wasserkrug", "C", ""),
    ("PrimalItemConsumable_RawMeat", "Rohes Fleisch", "C", ""),
    ("PrimalItemConsumable_CookedMeat", "Gekochtes Fleisch", "C", ""),
    ("PrimalItemConsumable_RawPrimeMeat", "Rohes Primes Fleisch", "C", ""),
    ("PrimalItemConsumable_CookedPrimeMeat", "Gekochtes Primes Fleisch", "C", ""),
    ("PrimalItemConsumable_Berry_Mejoberry", "Mejobeeren", "C", ""),
    ("PrimalItemConsumable_Berry_Amarberry", "Amarbeeren", "C", ""),
    ("PrimalItemConsumable_Berry_Tintoberry", "Tintobeeren", "C", ""),
    ("PrimalItemConsumable_Mindwipe", "Mindwipe-Tonic", "C", ""),
    # Rohstoffe
    ("PrimalItemResource_Stone", "Stein", "R", ""),
    ("PrimalItemResource_Flint", "Feuerstein", "R", ""),
    ("PrimalItemResource_Wood", "Holz", "R", ""),
    ("PrimalItemResource_Thatch", "Stroh", "R", ""),
    ("PrimalItemResource_Fiber", "Fasern", "R", ""),
    ("PrimalItemResource_Hide", "Leder", "R", ""),
    ("PrimalItemResource_Pelt", "Fell", "R", ""),
    ("PrimalItemResource_Chitin", "Chitin", "R", ""),
    ("PrimalItemResource_Keratin", "Keratin", "R", ""),
    ("PrimalItemResource_Metal", "Metallbarren", "R", ""),
    ("PrimalItemResource_MetalIngot", "Metallbarren (Ingot)", "R", ""),
    ("PrimalItemResource_Obsidian", "Obsidian", "R", ""),
    ("PrimalItemResource_Crystal", "Kristall", "R", ""),
    ("PrimalItemResource_Charcoal", "Holzkohle", "R", ""),
    ("PrimalItemResource_Gunpowder", "Schwarzpulver", "R", ""),
    ("PrimalItemResource_Sparkpowder", "Funkenpulver", "R", ""),
    ("PrimalItemResource_CementingPaste", "Zementpaste", "R", ""),
    ("PrimalItemResource_Polymer_Organic", "Organisches Polymer", "R", ""),
    ("PrimalItemResource_Element", "Element", "R", ""),
    ("PrimalItemResource_Silicon", "Silizium", "R", ""),
    ("PrimalItemResource_SilicaPearls", "Siliziumperlen", "R", ""),
    ("PrimalItemResource_BlackPearl", "Schwarze Perlen", "R", ""),
    ("PrimalItemResource_Oil", "Oel", "R", ""),
    ("PrimalItemResource_CactusSap", "Kaktussaft", "R", ""),
    # Ruestung (Riot-Set, im Kit erprobt)
    ("PrimalItemArmor_RiotHelmet", "Riot-Helm", "A", "Riot"),
    ("PrimalItemArmor_RiotShirt", "Riot-Brust", "A", "Riot"),
    ("PrimalItemArmor_RiotPants", "Riot-Hose", "A", "Riot"),
    ("PrimalItemArmor_RiotBoots", "Riot-Stiefel", "A", "Riot"),
    ("PrimalItemArmor_RiotGloves", "Riot-Handschuhe", "A", "Riot"),
    ("PrimalItemArmor_GhillieHelmet", "Ghillie-Kapuze", "A", "Ghillie"),
    ("PrimalItemArmor_GhillieShirt", "Ghillie-Hemd", "A", "Ghillie"),
    ("PrimalItemArmor_GhilliePants", "Ghillie-Hose", "A", "Ghillie"),
    ("PrimalItemArmor_GhillieBoots", "Ghillie-Schuhe", "A", "Ghillie"),
    ("PrimalItemArmor_GhillieGloves", "Ghillie-Handschuhe", "A", "Ghillie"),
    ("PrimalItemArmor_HazardSuitHelmet", "Hazard-Helm", "A", "Hazard"),
    ("PrimalItemArmor_HazardSuitShirt", "Hazard-Anzug", "A", "Hazard"),
    ("PrimalItemArmor_HazardSuitPants", "Hazard-Hose", "A", "Hazard"),
    ("PrimalItemArmor_HazardSuitBoots", "Hazard-Stiefel", "A", "Hazard"),
    ("PrimalItemArmor_HazardSuitGloves", "Hazard-Handschuhe", "A", "Hazard"),
]

VORLAGEN = {"W": W_A, "C": C_A, "R": R_A, "I": I_A, "A": ARM}


def blueprint(name: str, art: str, extra: str) -> str:
    if art == "A":
        return ARM % (extra, name, name)
    return VORLAGEN[art] % (name, name)


def eintraege() -> Iterable[dict]:
    for name, label, art, extra in ITEMS:
        yield {"name": name, "label": label, "bp": blueprint(name, art, extra)}


def suche(q: str, limit: int = 40) -> list[dict]:
    """Filtert nach Bezeichnung, Blueprint-Name oder Kategorie - ohne Gross-/Kleinschreibung."""
    wort = (q or "").strip().lower()
    treffer = []
    for e in eintraege():
        hay = (e["label"] + " " + e["name"]).lower()
        if not wort or wort in hay:
            treffer.append(e)
        if len(treffer) >= limit:
            break
    return treffer

# ------------------------------------------------------------------ 7 Days to Die
# 7D2D kennt keine Blueprints: `give <Spieler> <Itemname> <Anzahl>` erwartet den internen
# Itemnamen (z. B. gunHandgunT1Pistol). Auswahl der gebraeuchlichsten Gegenstaende.
SDTD_ITEMS: list[tuple[str, str]] = [
    ("meleeToolRepairT1ClawHammer", "Hammer (Reparatur)"),
    ("meleeToolPickT1IronPickaxe", "Eisen-Spitzhacke"),
    ("meleeToolAxeT1IronFireaxe", "Eisen-Axt"),
    ("meleeToolShovelT1IronShovel", "Eisen-Schaufel"),
    ("meleeWeaponKnifeT1Hunter", "Jagdmesser"),
    ("meleeWeaponClubT1Wooden", "Holzschlaeger"),
    ("meleeWeaponSpearT1Stone", "Steinspeer"),
    ("meleeWeaponBatT1Wooden", "Holzschlaeger (Baseball)"),
    ("gunHandgunT1Pistol", "Pistole"),
    ("gunHandgunT2Magnum44", "Magnum .44"),
    ("gunShotgunT1PipeShotgun", "Rohr-Schrotflinte"),
    ("gunShotgunT2PumpShotgun", "Pump-Schrotflinte"),
    ("gunRifleT1HuntingRifle", "Jagdgewehr"),
    ("gunRifleT2LeverActionRifle", "Unterheblergewehr"),
    ("gunMGT1AK47", "AK-47"),
    ("gunMGT2M60", "M60"),
    ("gunBowT1WoodenBow", "Holzbogen"),
    ("gunBowT3CompoundBow", "Compoundbogen"),
    ("gunToolNailgun", "Nagelpistole"),
    ("ammo9mmBullet", "Munition 9 mm"),
    ("ammo762mmBullet", "Munition 7,62 mm"),
    ("ammoShotgunShell", "Schrotpatronen"),
    ("ammoArrowIron", "Eisenpfeile"),
    ("medicalFirstAidBandage", "Erste-Hilfe-Verband"),
    ("medicalFirstAidKit", "Erste-Hilfe-Kasten"),
    ("medicalAntibiotics", "Antibiotika"),
    ("drinkCanBeer", "Bier"),
    ("drinkPureMineralWater", "Mineralwasser"),
    ("foodCanChili", "Chili-Dose"),
    ("foodBaconAndEggs", "Speck mit Ei"),
    ("foodMeatStew", "Fleischeintopf"),
    ("resourceRockSmall", "Stein"),
    ("resourceWood", "Holz"),
    ("resourceScrapIron", "Eisenschrott"),
    ("resourceForgedIron", "Geschmiedetes Eisen"),
    ("resourceForgedSteel", "Geschmiedeter Stahl"),
    ("resourceCement", "Zement"),
    ("resourceConcreteMix", "Betonmischung"),
    ("resourceGunPowder", "Schwarzpulver"),
    ("resourceBrass", "Messing"),
    ("resourceRepairKit", "Reparaturset"),
    ("toolBellows", "Blasebalg"),
    ("toolForgeCrucible", "Schmelztiegel"),
    ("modArmorCoolingMesh", "Kuehlgewebe (Ruestung)"),
    ("casinoCoin", "Casino-Muenze"),
    ("meleeToolFlashlight02", "Taschenlampe"),
]

# Spiele mit eigenem Katalog: Schluessel ist der Spielname der Instanz
GAMES = {"ark": "ark", "asa": "ark", "ase": "ark", "arkse": "ark", "7d2d": "7d2d", "sv7dtd": "7d2d"}


def eintraege_spiel(game: str = "") -> list[dict]:
    """Katalog fuer ein Spiel; leer, wenn es keinen gibt."""
    art = GAMES.get((game or "").lower(), "ark")
    if art == "7d2d":
        return [{"name": n, "label": lb, "cat": "7D2D"} for n, lb in SDTD_ITEMS]
    return eintraege()


def suche_spiel(q: str, game: str = "", limit: int = 40) -> list[dict]:
    wort = (q or "").strip().lower()
    treffer = []
    for e in eintraege_spiel(game):
        if not wort or wort in (e["label"] + " " + e["name"]).lower():
            treffer.append(e)
        if len(treffer) >= limit:
            break
    return treffer
