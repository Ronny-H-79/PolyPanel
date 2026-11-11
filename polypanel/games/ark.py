"""ARK: Survival Ascended - bisheriges Verhalten, jetzt als Spielprofil."""
from __future__ import annotations

from .base import GameProfile


class ArkProfile(GameProfile):
    key = "ark"
    label = "ARK: Survival Ascended"
    server_app_id = "2430930"
    control_kind = "source"
    needs_wine = True
    default_game_port = 7790
    default_query_port = 27016
    default_control_port = 27025
    supports_mods = True
    supports_cluster = True
    install_note = "Windows-Binary, laeuft unter Wine"
    wine_overrides = "mscoree,mshtml="   # ARK braucht kein .NET
    maps = (
        ("Ragnarok_WP", "Ragnarok"),
        ("TheIsland_WP", "The Island"),
        ("ScorchedEarth_WP", "Scorched Earth"),
        ("Aberration_WP", "Aberration"),
        ("Extinction_WP", "Extinction"),
        ("TheCenter_WP", "The Center"),
        ("Astraeos_WP", "Astraeos"),
        ("Valguero_WP", "Valguero"),
        ("LostColony_WP", "Lost Colony"),
        ("Genesis_WP", "Genesis"),
    )

    # Die ARK-Logik liegt unveraendert in Instance (Bestandscode) - das Profil
    # reicht sie nur durch, damit der Kern spielunabhaengig aufrufen kann.
    def exe(self, inst) -> str:
        return inst.ark_exe

    def launch_argv(self, inst) -> list[str]:
        return inst.ark_launch_argv()

    def write_config(self, inst) -> None:
        inst.ark_write_ini()

    def control(self, inst, timeout: float = 10.0):
        from ..rcon import RconClient
        return RconClient("127.0.0.1", inst.rcon_port, inst.admin_pw, timeout=timeout)

    def ready(self, inst) -> bool:
        """ARK meldet die Bereitschaft im Log."""
        from .. import runner
        return runner.ark_server_ready(inst)

    def graceful_stop(self, inst) -> list[str]:
        """Wie bisher: Welt speichern, dann DoExit."""
        steps: list[str] = []
        with self.control(inst, timeout=15) as rc:
            rc.command("SaveWorld", timeout=20)
            steps.append("SaveWorld ok")
            rc.command("DoExit", timeout=8)
            steps.append("DoExit gesendet")
        return steps
