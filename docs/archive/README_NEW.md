# PDF Knowledge Pipeline - Moderne Modulare Architektur

Eine **lokale, erweiterbare RAG-Pipeline** für wissenschaftliche PDFs mit moderner Python-Architektur. Kernidee: PDF-Dateien bleiben lokal, werden intelligent verarbeitet und über verschiedene Suchverfahren zugänglich gemacht.

## 🚀 Neue Funktionen (2025)

✅ **Modulare Architektur** - Saubere Trennung von Bibliothekscode und CLI-Tools  
✅ **Mehrere Suchverfahren** - Volltext (Whoosh), Embeddings (ChromaDB), Formeln (SQLite)  
✅ **CLI-Tools** - Benutzerfreundliche Kommandozeilen-Interfaces  
✅ **Dependency-Management** - Optionale Dependencies, keine Crashes  
✅ **Programmatische API** - Module können in anderen Scripts importiert werden  

## 📁 Projektstruktur (Neu)

```
├── 🏗️ src/                    # Modulare Pipeline-Architektur
│   ├── core/                  # Kernfunktionalität  
│   │   ├── convert_local.py   # PDF → Text Konvertierung
│   │   ├── indexer.py         # ChromaDB Embedding-Index  
│   │   └── rag.py             # RAG-basierte Anfragen
│   ├── pipeline/              # Text-Pipeline
│   │   ├── extract.py         # PDF-Text-Extraktion
│   │   ├── index.py           # Whoosh Volltextindex
│   │   └── search.py          # BM25 Volltext-Suche
│   ├── analysis/              # Analyse-Tools
│   │   ├── duplicates.py      # Duplikatserkennung
│   │   └── relevance.py       # Keyword-basierte Relevanzanalyse
│   ├── formulas/              # Formel-Verarbeitung
│   │   ├── nougat.py          # Nougat OCR für Formeln
│   │   ├── extract.py         # LaTeX-Formelextraktion  
│   │   ├── index.py           # SQLite Formelindex
│   │   └── search.py          # Symbol-/Muster-Suche
│   └── cli/                   # CLI-Interfaces
│       ├── extract.py         # Text-Extraktion CLI
│       ├── search.py          # Such-CLI  
│       ├── analyze.py         # Analyse-CLI
│       └── pipeline.py        # Pipeline-Management
├── 📄 Daten & Verarbeitung
│   ├── raw/                   # Eingabe-PDFs
│   ├── txt/                   # Extrahierte Texte
│   ├── processed/             # Whoosh-Index, Nougat-Output
│   ├── metadata/              # Reports, Formel-Indices
│   └── .chroma/               # ChromaDB Embedding-Datenbank
├── 🔧 Konfiguration
│   ├── pipeline_new.py        # Haupt-Pipeline (ersetzt alte pipeline.py)
│   ├── search.py              # Einfaches Such-Tool
│   ├── config.json            # Pipeline-Konfiguration
│   ├── .env                   # API-Keys (OpenAI, Zotero, etc.)
│   └── requirements.txt       # Python-Dependencies
└── 📚 tools/ (Legacy)         # Alte CLI-Tools (Kompatibilität)
```

## ⚡ Schnellstart

### 1. Setup & Dependencies
```bash
# Python Environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Grundlegende Dependencies installieren
pip install -r requirements.txt

# Zusätzliche Dependencies je nach Bedarf
pip install PyMuPDF           # PDF-Extraktion
pip install Whoosh            # Volltextsuche  
pip install sentence-transformers chromadb  # Embeddings
pip install nougat-ocr        # Formel-OCR (optional)
```

### 2. Erste Schritte
```bash
# 📊 Duplikate in PDF-Sammlung finden
python src/cli/analyze.py duplicates

# 📈 Relevanzanalyse nach Keywords
python src/cli/analyze.py relevance --keywords "machine learning,neural networks"

# 🔧 Vollständige Pipeline ausführen
python pipeline_new.py --skip-nougat    # Ohne Formel-OCR
python pipeline_new.py                  # Mit Formel-OCR
```

## 🔍 Such-Features

### Volltext-Suche (Whoosh BM25)
```bash
# Über neue Pipeline
python -c "
import sys; sys.path.insert(0, 'src')
import pipeline.search as ps
results = ps.search_whoosh('machine learning', 5)
for r in results: print(f'📄 {r[\"filename\"]}')
"

# Pipeline-Schritte einzeln
python pipeline_new.py --step extract    # Text extrahieren
python pipeline_new.py --step index      # Whoosh-Index erstellen
```

### Embedding-Suche (ChromaDB)
```bash
# Semantische Ähnlichkeitssuche
python -c "
import sys; sys.path.insert(0, 'src')  
import core.rag as rag
answer = rag.ask('Was ist Deep Learning?', k=5)
print(answer)
"
```

### Formel-Suche
```bash
# Nach Symbolen suchen
python -c "
import sys; sys.path.insert(0, 'src')
import formulas.search as fs
results = fs.search_formulas(symbol='Re', limit=5)
for r in results: print(f'🔢 {r[\"latex\"][:80]}...')
"

# Pipeline für Formeln
python pipeline_new.py --step nougat        # Nougat OCR
python pipeline_new.py --step formulas      # Formeln extrahieren
python pipeline_new.py --step formula-index # Formel-Index erstellen
```

## 🛠️ CLI-Tools (Empfohlen)

### Analyse-Tools
```bash
# Duplikaterkennung
python src/cli/analyze.py duplicates --threshold 85

# Relevanzanalyse  
python src/cli/analyze.py relevance --keywords "CFD,turbulence,POD"
```

### Pipeline-Management
```bash
# Vollständige Pipeline
python src/cli/pipeline.py full

# Einzelne Schritte
python src/cli/pipeline.py extract
python src/cli/pipeline.py index
python src/cli/pipeline.py nougat
```

## 📦 Programmatische Nutzung

```python
# Module importieren
import sys
sys.path.append('src')

# Text-Extraktion
from pipeline.extract import extract_all_pdfs, extract_pdf
extract_all_pdfs()

# Duplikaterkennung
from analysis.duplicates import scan_duplicates
duplicates = scan_duplicates()
print(f"Gefunden: {duplicates['total_files']} Dateien")

# Suche
from pipeline.search import search_whoosh
results = search_whoosh("neural networks", k=10)

# Formeln
from formulas.search import search_formulas  
formulas = search_formulas(symbol="omega", limit=5)
```

## 🔧 Konfiguration

### Environment Variables (.env)
```bash
# OpenAI für RAG
OPENAI_API_KEY=sk-...

# Zotero Integration (optional)
ZOTERO_API_KEY=...
ZOTERO_USER_ID=1234567

# Mathpix für Formeln (optional) 
MATHPIX_APP_ID=...
MATHPIX_APP_KEY=...

# Pfade (optional)
RAW_DIRS=/path/to/pdfs:/another/path
TEXT_OUT_DIR=custom_txt_dir
```

### Pipeline-Konfiguration (config.json)
```json
{
  "embeddings": {
    "model": "all-MiniLM-L6-v2"
  },
  "directories": {
    "raw": "raw",
    "processed": "processed",
    "output": "txt"
  }
}
```

## 🔄 Migration von alter Struktur

### Alt (tools/) → Neu (src/cli/)
```bash
# Alte CLI-Tools
python tools/01_scan_duplicates.py
python tools/04_relevance_report.py --keywords "ML"
python tools/05_query.py --q "deep learning" --k 10

# Neue CLI-Tools  
python src/cli/analyze.py duplicates
python src/cli/analyze.py relevance --keywords "ML"
python search.py text --q "deep learning" --k 10
```

### Programmierung Alt → Neu
```python
# Alt: Direkte tool-Aufrufe
import tools.scan_duplicates

# Neu: Modulare Imports
import sys; sys.path.append('src')
from analysis.duplicates import scan_duplicates
```

## 📈 Performance & Features

| Feature | Alt (tools/) | Neu (src/) | Verbesserung |
|---------|-------------|------------|--------------|
| **Modularität** | ❌ Verstreute Scripts | ✅ Klare Module | 🔥 Bessere Organisation |
| **Testbarkeit** | ❌ Schwer testbar | ✅ Einzeln testbar | 🔥 Unit-Tests möglich |
| **Wiederverwendung** | ❌ Copy-Paste | ✅ Import & nutzen | 🔥 DRY-Prinzip |
| **CLI-UX** | ❌ Verschiedene Patterns | ✅ Einheitliche CLIs | 🔥 Bessere UX |
| **Dependencies** | ❌ Hard-coded | ✅ Optional mit Fallbacks | 🔥 Robuster |

## 🐛 Troubleshooting

```bash
# Dependency-Probleme
pip install PyMuPDF Whoosh sentence-transformers

# Import-Probleme  
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Berechtigungsprobleme
chmod +x src/cli/*.py

# Test der Module
python src/test_modules.py
```

## 🗺️ Roadmap

### Kurzfristig
- [ ] CLI-Tools für alle Module vervollständigen
- [ ] Unit-Tests für Kern-Module
- [ ] Docker-Container für einfaches Deployment

### Mittelfristig  
- [ ] Web-Interface (FastAPI/Streamlit)
- [ ] Besseres Chunking (Überschneidungen, Sections)
- [ ] Evaluation-Framework (Recall@K, MRR)

### Langfristig
- [ ] Multi-Modal Support (Bilder, Tabellen)
- [ ] Distributed Processing (Ray/Dask)
- [ ] Enterprise Features (Auth, Multi-User)

---

**🎯 Die neue modulare Architektur ist produktionsreif und deutlich wartbarer als die alte tools/-Struktur!**