"""Die Routing-Tabelle muss vollstaendig und eindeutig sein."""
from __future__ import annotations

import unittest

from polypanel import webui


class RoutenTest(unittest.TestCase):
    def test_jede_route_hat_eine_methode(self) -> None:
        for pfad, name in webui._POST_ROUTES.items():
            self.assertTrue(pfad.startswith("/api/"), pfad)
            self.assertTrue(callable(getattr(webui.Handler, name, None)), "%s fehlt" % name)

    def test_keine_doppelten_pfade(self) -> None:
        pfade = list(webui._POST_ROUTES)
        self.assertEqual(len(pfade), len(set(pfade)))

    def test_praefixe_zeigen_auf_methoden(self) -> None:
        for praefix, name in webui._POST_PREFIXE:
            self.assertTrue(praefix.endswith("/"), praefix)
            self.assertTrue(callable(getattr(webui.Handler, name, None)), name)

    def test_get_routen_bleiben_erreichbar(self) -> None:
        with open(webui.__file__, encoding="utf-8") as fh:
            quelle = fh.read()
        for pfad in ("/api/instances", "/api/host", "/api/changelog", "/api/config", "/api/mods"):
            self.assertIn('path == "%s"' % pfad, quelle)


if __name__ == "__main__":
    unittest.main()
