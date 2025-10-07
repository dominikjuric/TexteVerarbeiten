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
├── docs/
│   ├── architecture/ # Aktuelle Architekturunterlagen
│   └── archive/      # Historische Notizen/Reports
├── scripts/
│   └── legacy/       # Ältere Pipeline-/Utility-Skripte
├── processed/        # Verarbeitete Daten (ignored)
├── raw/              # Eingabe-PDFs (ignored)
├── txt/              # Extrahierte Texte (ignored)
├── metadata/         # Metadaten, Reports
├── requirements.txt  # Basis-Abhängigkeiten
├── requirements-nougat.txt  # Nougat-/Vision-Extras
└── config.json       # Optionale Legacy-Konfiguration
```
### Weiterführende Dokumente
- `docs/architecture/wissenspipeline-anpassen.md` – Detaillierte Architektur-Notizen (DE)
- `docs/archive/` – Historische READMEs, Reports und Audits


## Installation & Verwendung

### 1. Abhängigkeiten installieren
```sh
pip install -r requirements.txt
# Zusätzlich für vollständige Funktionalität:
pip install sentence-transformers chromadb openai-whisper
pip install pymupdf whoosh  # Für PDF-Verarbeitung
   ```

### 2. CLI-Tools verwenden (empfohlen)

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
python src/cli/pipeline.py --action extract
python src/cli/pipeline.py --action index
```

### 3. Programmatische Verwendung

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

### 4. Formelverarbeitung (optional)

```python
from pathlib import Path
from src.formulas.nougat_processor import process_pdf_with_nougat

result = process_pdf_with_nougat(Path("raw/math_paper.pdf"), pages="1-3")
if result["success"]:
    print(f"Output gespeichert in: {result['output_path']}")
else:
    print(f"Nougat-Fehler: {result.get('error')}")
```

## Konfiguration

Bearbeite `config.json` für Anpassungen:

```json
{
  "raw_dirs": ["raw/"],
  "output_dirs": {"txt": "txt/", "processed": "processed/"},
  "search_index": "processed/whoosh_index/",
  "similarity_threshold": 80,
  "max_file_size_mb": 100
}
```

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
