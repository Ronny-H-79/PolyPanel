# Entwicklung

Hinweise für alle, die an noah2games mitarbeiten wollen.

[← zurück zum README](../README.md)

## Arbeitsweise und Stolpersteine

Jede Version ist als Tag festgehalten (`v0.1.0` … `v0.2.8`), damit sich Änderungen einem Stand
zuordnen lassen. Eine neue Version setzen, taggen und pushen:

```bash
./scripts/release.sh 0.2.9              # Version + Commit + Tag + Push
./scripts/release.sh 0.2.9 --release    # zusätzlich GitHub-Release (braucht gh)
```


<details>
<summary>Technische Hintergründe (aufklappen)</summary>

- Start ohne `-NoBattlEye`: der Server startet unter Wine nicht zuverlässig.
- `RCONEnabled` und `ServerAdminPassword` überleben nur, wenn die Kopfzeile
  `;METADATA=(Diff=true, UseCommands=true)` in der `GameUserSettings.ini` erhalten bleibt —
  sonst generiert ARK die Datei beim Start neu.
- Ein Wine-Konsolenfenster entsteht, wenn der Prozess ohne Terminal startet; ein privates
  `XDG_RUNTIME_DIR` ohne Wayland-Socket verhindert es (Wine 11 nutzt sonst `wayland-0` per Default).
- ASA wertet **kein** stdin aus: die Konsole läuft über RCON, nicht über eine Pipe.
- Nach `kill -9` braucht der Neustart 90–100 s (Welt wird repariert), deshalb `hang_seconds ≥ 180`.

</details>

---

© 2026 Ronny H. · Free to use, all rights reserved — [Licence](../LICENSE)
