# PDF-Textverarbeitungspipeline

Eine modulare Python-Pipeline für PDF-Verarbeitung, Volltextsuche und Dokumentenanalyse mit KI-Integration.

## Kernfunktionen
- Modulare Architektur mit klarer Trennung von Pipeline, Analyse und UI-Komponenten
- PDF-Textextraktion mit PyMuPDF und optionalem OCR-Fallback
- BM25-Volltextsuche über Whoosh mit Ranking und Filterung
- Embedding-basiertes semantisches Retrieval mit ChromaDB (optional)
- Duplikatserkennung via Hash-Vergleich und Fuzzy-String-Matching
- CLI-Tools für benutzerfreundliche Bedienung
- Formel-Extraktion mit Nougat-OCR (optional)

## Anforderungen & Ziele
- Lokale Verarbeitung (Textextraktion, OCR, Indexierung) ohne Cloud-Zwang; Datenschutz hat Priorität.
- Zotero 7 dient als Queue: Tags wie `/to_process` -> `/processed` -> `/error` steuern den Durchlauf.
- Zwei Retrieval-Pfade: BM25 für Debug/Filter, ChromaDB für semantische Suche.
- Wissenschaftliche PDFs werden bevorzugt mit Nougat (CLI) verarbeitet; Mathpix bleibt optional.
- Formel- und Markdown-Ausgaben sollen wiederverwendbar (Formelindex, RAG-Kontext) gespeichert werden.

## Projektstruktur
```
.
├── src/              # Hauptcode (modulare Pipeline)
│   ├── pipeline/     # Extraktion, Indexierung, Suche
│   ├── analysis/     # Analysen (Duplikate, Relevanz)
│   ├── core/         # RAG/Embedding-Funktionen
│   ├── formulas/     # Nougat & Formel-Index
│   └── cli/          # Moderne CLI-Einstiegspunkte
├── config/
│   └── config.example.json  # Vorlage für Pfade, Modelle, API-Keys
├── docs/
│   ├── architecture/ # Aktuelle Architekturunterlagen
│   ├── archive/      # Historische Notizen/Reports
│   ├── setup/        # Setup- und Konfigurationsanleitungen
│   └── tutorials/    # Schritt-für-Schritt-Guides
├── scripts/
│   ├── setup.sh      # Bootstrap-Skript für virtuelle Umgebung & Dependencies
│   └── legacy/       # Ältere Pipeline-/Utility-Skripte
├── processed/        # Verarbeitete Daten (ignored)
├── raw/              # Eingabe-PDFs (ignored)
├── txt/              # Extrahierte Texte (ignored)
├── metadata/         # Metadaten, Reports
├── tools/            # Automatisierung & Hilfsskripte
├── requirements.txt  # Basis-Abhängigkeiten
└── requirements-nougat.txt  # Nougat-/Vision-Extras
```
### Weiterführende Dokumente
- `docs/setup/configuration.md` – Vollständige Dokumentation zur Konfiguration
- `docs/tutorials/first_pipeline_run.md` – Tutorial für den ersten Pipeline-Lauf
- `docs/architecture/wissenspipeline-anpassen.md` – Detaillierte Architektur-Notizen (DE)
- `docs/archive/` – Historische READMEs, Reports und Audits


## Installation & Verwendung

### 1. Umgebung einrichten
```sh
./scripts/setup.sh              # installiert requirements.txt in .venv
INSTALL_NOUGAT=1 ./scripts/setup.sh  # optional: Nougat-Extras mitinstallieren
```

### 2. Konfiguration anpassen
- Kopiere `config/config.example.json` nach `config/config.json`.
- Ergänze Pfade, Standardmodelle und API-Schlüssel nach Bedarf.
- Details siehe `docs/setup/configuration.md`.

### 3. CLI-Tools verwenden (empfohlen)

#### Dokumente analysieren
```sh
# Duplikate finden und Relevanz bewerten
python src/cli/analyze.py

# Spezifische Analyse
python -c "from src.analysis.duplicates import scan_duplicates; scan_duplicates()"
```

#### Suchen und Indizieren
```sh 
# BM25-Volltext-Suche
python src/cli/search.py "machine learning"

# Pipeline ausführen (PDF → Text → Index)
python src/cli/pipeline.py extract --batch-size 4
python src/cli/pipeline.py index --batch-size 200
# Komplettpipeline inkl. Index und optional Nougat
python src/cli/pipeline.py full --batch-size 4 --index-batch-size 200
```

### 4. Programmatische Verwendung

#### PDF-Textextraktion
```python
from src.pipeline.extract import extract_text_from_pdf

# Einfache Textextraktion
text = extract_text_from_pdf("raw/document.pdf")
print(f"Extrahiert: {len(text)} Zeichen")

# Mit Speicherung in txt/
from src.pipeline.extract import process_pdf
process_pdf("raw/document.pdf", "txt/")
```

#### Suchfunktionen
```python
from src.pipeline.search import search_documents

# BM25-Suche im Index  
results = search_documents("neural networks", limit=5)
for doc, score in results:
    print(f"{score:.2f}: {doc}")

# Erweiterte Suche mit Filtern
from src.pipeline.index import build_index
build_index("txt/", "processed/whoosh_index/")
```

#### Duplikatsanalyse
```python
from src.analysis.duplicates import scan_duplicates

# Vollständige Duplikatsanalyse
result = scan_duplicates()
print(f"Dateien: {result['total_files']}")
print(f"Hash-Duplikate: {len(result['duplicate_hashes'])}")
print(f"Ähnliche Namen: {len(result['similar_names'])}")
```

#### RAG-Funktionen (bei verfügbaren Abhängigkeiten)
```python
from src.core.rag import rag_search

# Semantische Suche mit Embeddings
try:
    answer = rag_search("What is deep learning?")
    print(f"Antwort: {answer}")
except ImportError:
    print("ChromaDB/sentence-transformers nicht verfügbar")
```

### 5. Formelverarbeitung (optional)

```python
from pathlib import Path
from src.formulas.nougat_processor import process_pdf_with_nougat

result = process_pdf_with_nougat(Path("raw/math_paper.pdf"), pages="1-3")
if result["success"]:
    print(f"Output gespeichert in: {result['output_path']}")
else:
    print(f"Nougat-Fehler: {result.get('error')}")
```

```sh
# Formel-Extraktion und Indexaufbau (setzt Nougat-Markdown voraus)
python src/cli/pipeline.py formulas
python src/cli/pipeline.py formula-index
```

Die Verzeichnisse für Nougat-Markdown (`processed/nougat_md/`), ersetzte Texte (`processed/nougat_txt/`),
das JSONL mit Formelmetadaten (`metadata/formulas.jsonl`) und die SQLite-Datenbank (`metadata/formula_index.sqlite`)
können über die Config-Sektion `formulas` angepasst werden.

## Konfiguration

- Vollständige Feldbeschreibung: `docs/setup/configuration.md`
- Lokale Anpassungen in `config/config.json` oder `.env` vornehmen
- Sensible Werte (API-Keys) werden von Umgebungsvariablen wie `OPENAI_API_KEY`, `MATHPIX_APP_ID` übersteuert

## Funktionsübersicht

### Pipeline-Module (`src/pipeline/`)
- **extract.py**: PDF→Text-Konvertierung mit PyMuPDF
- **index.py**: Whoosh-BM25-Indexierung für Volltext-Suche  
- **search.py**: Suchfunktionen mit Ranking und Filterung

### Analyse-Tools (`src/analysis/`)
- **duplicates.py**: Hash-basierte + Fuzzy-Duplikatserkennung
- **relevance.py**: Keyword-Extraktion und Relevanz-Scoring

### KI-Integration (`src/core/`) 
- **convert_local.py**: Lokale PDF-Verarbeitung
- **indexer.py**: ChromaDB-Embedding-Speicher
- **rag.py**: Retrieval-Augmented Generation

### Benutzer-Interface (`src/cli/`)
- **analyze.py**: Ein-Kommando-Analyse (Duplikate + Relevanz)
- **search.py**: Interaktive Suchschnittstelle
- **pipeline.py**: Batch-Verarbeitung und Indexverwaltung

## Architektur-Verbesserungen

1. **Modulare Architektur**: Klare Trennung von Pipeline, Analyse und UI
2. **Robuste Imports**: Optionale Abhängigkeiten mit Fallback-Verhalten
3. **CLI-Integration**: Benutzerfreundliche Kommandozeilen-Tools
4. **Konsistente APIs**: Einheitliche Funktionssignaturen und Rückgabewerte
5. **Bessere Tests**: Einfachere Unit-Tests durch modulare Struktur
6. **Dokumentation**: Vollständige Docstrings und Nutzungsbeispiele

Dieses Design unterstützt sowohl interaktive Nutzung als auch programmatische Integration in größere Workflows.
