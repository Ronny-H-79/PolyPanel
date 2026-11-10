"""Spielprofile: Registrierung und Auswahl."""
from __future__ import annotations

from .ark import ArkProfile
from .arkse import ArkSeProfile
from .base import GameProfile
from .satisfactory import SatisfactoryProfile
from .spaceengineers import SpaceEngineersProfile
from .sv7dtd import SevenDaysProfile

PROFILES: dict[str, GameProfile] = {
    p.key: p for p in (ArkProfile(), ArkSeProfile(), SatisfactoryProfile(),
                       SpaceEngineersProfile(), SevenDaysProfile())
}

DEFAULT_GAME = "ark"


def get(key: str | None) -> GameProfile:
    """Profil zu einem Schluessel; unbekannt/leer faellt auf ARK zurueck."""
    return PROFILES.get((key or DEFAULT_GAME).strip().lower(), PROFILES[DEFAULT_GAME])


def keys() -> list[str]:
    return list(PROFILES)


def labels() -> dict[str, str]:
    return {k: p.label for k, p in PROFILES.items()}
