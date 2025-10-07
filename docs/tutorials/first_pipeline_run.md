# Tutorial: Erster Pipeline-Lauf

Dieses Tutorial führt dich in weniger als 15 Minuten vom frischen Checkout zum ersten erfolgreichen Pipeline-Lauf.

## Voraussetzungen
- Python 3.10 oder höher
- Git und (optional) Tesseract für OCR
- OpenAI-API-Key, falls du die RAG-Funktionen testen möchtest

## Schritt 1 – Umgebung vorbereiten
```bash
# Repository klonen (falls noch nicht geschehen)
git clone git@github.com:dein-account/TexteVerarbeiten.git
cd TexteVerarbeiten

# Setup-Skript ausführen
./scripts/setup.sh
```

> 💡 Setze `INSTALL_NOUGAT=1`, wenn du die Nougat-Extras installieren möchtest: `INSTALL_NOUGAT=1 ./scripts/setup.sh`.

## Schritt 2 – Konfiguration anpassen
```bash
cp config/config.example.json config/config.json
nano config/config.json  # oder Editor deiner Wahl
```

- Aktualisiere `paths` (z. B. `raw`, `txt`) passend zu deinem Dateisystem.
- Trage API-Schlüssel unter `services` ein oder nutze `.env`.
- Passe `rag.results_per_query` an, falls du mehr/weniger Kontextblöcke möchtest.

## Schritt 3 – Daten vorbereiten
1. Lege ein paar PDFs im Verzeichnis `raw/` ab.
2. Falls du mit Zotero arbeitest, stelle sicher, dass `config/config.json` deine `zotero`-Credentials enthält.

## Schritt 4 – Pipeline ausführen
```bash
source .venv/bin/activate
python src/cli/pipeline.py full --batch-size 4 --index-batch-size 100
```

Die CLI zeigt nach jedem Schritt eine Zusammenfassung inklusive Fehlern und Metadatenwarnungen.
Wenn Nougat aktiviert ist, folgen automatisch Formel-Extraktion und LaTeX-Indexaufbau.

## Schritt 5 – Ergebnisse prüfen
- Extrahierte Texte findest du unter `txt/` (oder deinem konfigurierten Pfad).
- Der Whoosh-Index landet im Verzeichnis `processed/whoosh_index/`.
- Die erzeugten Chunk-JSONLs liegen unter `processed/chunks/` und enthalten pro PDF alle Textsegmente.
- Wenn du Nougat aktiviert hast, liegen Nougat-Markdowns unter `processed/nougat_md/`,
  ersetzte Texte in `processed/nougat_txt/` und der Formel-Index in `metadata/formula_index.sqlite`.
- In den Metadaten (`metadata/*.json`) findest du zusätzlich eine `chunks`-Sektion mit Statistik (Anzahl, Strategie, Größe).

## Schritt 6 – RAG-Abfrage starten (optional)
```bash
python src/cli/rag_cli.py
# Beispiel-Session:
# > Frage: Welche Paper behandeln Transformer-Architekturen?
```

Das CLI zeigt dir Quellen samt Seitenangaben, sofern in der ChromaDB vorhanden.

## Troubleshooting
| Problem | Ursache | Lösung |
| --- | --- | --- |
| `RuntimeError: OPENAI_API_KEY fehlt` | Kein API-Key gesetzt | `.env` ergänzen oder `config/config.json` aktualisieren |
| Keine PDFs gefunden | `raw`-Pfad falsch konfiguriert | `paths.raw` prüfen | 
| Nougat schlägt fehl | CLI nicht installiert | Setup erneut mit `INSTALL_NOUGAT=1` ausführen |

## Nächste Schritte
- Lies `docs/setup/configuration.md` für Details zu Pfaden und API-Keys.
- Automatisiere deine Zotero-Queue mit `tools/run_zotero_queue.py`.
- Experimentiere mit `src/rag.py` und passe Prompts an deine Domäne an.
