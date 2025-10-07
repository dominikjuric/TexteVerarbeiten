# Konfiguration der PDF-Pipeline

Dieses Dokument erklärt, wie die Pipeline über JSON-Dateien und Umgebungsvariablen konfiguriert wird.

## 1. Schnellstart

1. Kopiere die Vorlage:
   ```bash
   cp config/config.example.json config/config.json
   ```
2. Trage deine lokalen Pfade und API-Schlüssel ein.
3. Alternativ kannst du sensible Werte in einer `.env`-Datei oder als Umgebungsvariablen hinterlegen.

## 2. Aufbau der Konfigurationsdatei

```json
{
  "paths": {
    "raw": "raw",
    "text": "txt",
    "processed": "processed",
    "metadata": "metadata",
    "logs": "logs",
    "chroma": ".chroma",
    "whoosh_index": "processed/whoosh_index",
    "chunks": "processed/chunks"
  },
  "models": {
    "chat": "gpt-4o-mini",
    "embedding": "all-MiniLM-L6-v2",
    "nougat": "facebook/nougat-base"
  },
  "services": {
    "openai": {
      "api_key": ""
    },
    "mathpix": {
      "app_id": "",
      "app_key": ""
    },
    "zotero": {
      "user_id": "",
      "api_key": ""
    }
  },
  "pipeline": {
    "default_batch_size": 8,
    "default_index_batch_size": 200,
    "overwrite_outputs": false,
    "parallelism": 0
  },
  "rag": {
    "collection": "papers",
    "persist_path": ".chroma",
    "history_limit": 10,
    "temperature": 0.0,
    "results_per_query": 5,
    "cache_size": 64,
    "chunking": {
      "size": 1200,
      "overlap": 200,
      "max_size": 2400,
      "large_document_threshold": 60000,
      "target_chunk_count": 256,
      "min_size": 400
    },
    "chroma_settings": {
      "chroma_db_impl": "duckdb+parquet",
      "anonymized_telemetry": false,
      "allow_reset": false
    },
    "collection_metadata": {
      "hnsw:space": "cosine"
    }
  },
  "formulas": {
    "markdown_dir": "processed/nougat_md",
    "text_dir": "processed/nougat_txt",
    "metadata_file": "metadata/formulas.jsonl",
    "index_db": "metadata/formula_index.sqlite"
  }
}
```

### Wichtige Sektionen
- **paths** – Standardverzeichnisse für Eingaben, Ausgaben, Logs und Vektordatenbanken.
- **models** – Voreingestellte Modellnamen für Chat, Embeddings und Nougat.
- **services** – Zugangsdaten für externe APIs. Leere Strings können durch `.env`-Variablen überschrieben werden.
- **pipeline** – Defaults für Batchgrößen, Überschreibungsstrategie und optionale Parallelisierung.
- **rag** – Standardparameter für Retrieval-Augmented-Generation inkl. Chunking-, Cache- und Chroma-Tuning.
- **formulas** – Pfade für Nougat-Markdown, ersetzte Textausgaben, JSONL-Metadaten und die SQLite-Indexdatei.

### Erweiterte Optionen

- `paths.chunks` – Zielordner für die generierten Chunk-JSONL-Dateien.
- `pipeline.parallelism` – Anzahl gleichzeitiger Extraktions-Worker (0 = automatisch deaktiviert).
- `rag.chunking` – Feintuning der adaptiven Chunk-Größe (Zeichen, Overlap, Schwellenwerte).
- `rag.cache_size` – Anzahl der gespeicherten Fragen/Antworten und Embeddings für wiederholte Queries.
- `rag.chroma_settings` & `rag.collection_metadata` – Optimierungsparameter für den PersistentClient bzw. den HNSW-Index.

## 3. Lade-Reihenfolge

Die Pipeline lädt Konfigurationen in folgender Reihenfolge:

1. **`PIPELINE_CONFIG_PATH`** – Falls gesetzt, wird diese Datei zuerst eingelesen.
2. `config.json` im Projektwurzelverzeichnis.
3. `config/config.json` oder `config/config.local.json` (lokale Overrides).
4. `config/config.example.json` – liefert Defaultwerte, falls nichts anderes existiert.
5. Environment-Variablen (`OPENAI_API_KEY`, `MATHPIX_APP_ID`, ...), z. B. aus `.env`.

Spätere Quellen überschreiben frühere Werte. Auf diese Weise kannst du sensible Daten außerhalb des Git-Repos halten.

## 4. Pfade programmatisch auflösen

Über `src.config.resolve_path("chroma")` erhältst du den absoluten Pfad zu einem konfigurierten Verzeichnis. Beispiel:

```python
from src.config import resolve_path

chroma_dir = resolve_path("chroma")
print(chroma_dir)
```

## 5. API-Keys sicher verwalten

- Lege sensible Werte bevorzugt in `.env` ab (liegt bereits in `.gitignore`).
- Alternativ kannst du eine `config/config.local.json` anlegen, die **nicht** eingecheckt wird.
- Stelle sicher, dass `OPENAI_API_KEY` gesetzt ist, bevor du RAG-Funktionen nutzt; andernfalls schlägt die Session-Initialisierung fehl.

## 6. Troubleshooting

| Problem | Ursache | Lösung |
| --- | --- | --- |
| `RuntimeError: OPENAI_API_KEY fehlt` | Kein Schlüssel in Config/Umgebung | `.env` oder `config/config.json` aktualisieren |
| Nougat wird nicht gefunden | Falsches Modell oder CLI nicht installiert | `nougat`-Pfad in `models.nougat` setzen und CLI installieren |
| Whoosh-Index landet am falschen Ort | `paths.whoosh_index` zeigt auf veraltetes Verzeichnis | Pfad in Konfiguration anpassen |

## 7. Weiterführende Ressourcen

- `README.md` – Überblick über Funktionen und Projektstruktur.
- `docs/tutorials/first_pipeline_run.md` – Schritt-für-Schritt-Anleitung für den ersten Lauf.
- `scripts/setup.sh` – Setup-Skript zum Installieren der Abhängigkeiten.
