# PDF Knowledge Pipeline - Restructured

## Neue Modulare Architektur

Die Pipeline wurde umstrukturiert für bessere Organisation und Wartbarkeit:

```
src/
├── core/              # Kernfunktionalität
│   ├── convert_local.py    # PDF-zu-Text Konvertierung
│   ├── indexer.py          # ChromaDB Indexierung
│   └── rag.py              # RAG-basierte Anfragen
├── pipeline/          # Pipeline-Module
│   ├── extract.py          # Text-Extraktion (tools/02_extract_text.py)
│   ├── index.py            # Whoosh-Indexierung (tools/03_build_index.py)
│   └── search.py           # Volltext-Suche (tools/05_query.py)
├── analysis/          # Analyse-Tools
│   ├── duplicates.py       # Duplikatserkennung (tools/01_scan_duplicates.py)
│   └── relevance.py        # Relevanzanalyse (tools/04_relevance_report.py)
├── formulas/          # Formel-spezifische Module
│   ├── nougat.py           # Nougat OCR (tools/06_nougat_batch.py)
│   ├── extract.py          # Formelextraktion (tools/07_extract_formulas.py)
│   ├── index.py            # Formelindizierung (tools/08_build_formula_index.py)
│   └── search.py           # Formelsuche (tools/09_search_formula.py)
└── cli/               # CLI-Interfaces
    ├── extract.py          # Text-Extraktion CLI
    ├── search.py           # Such-CLI (kombiniert Text + Formeln)
    ├── analyze.py          # Analyse-CLI
    └── pipeline.py         # Pipeline-Management CLI
```

## Neue Usage

### 1. Komplette Pipeline ausführen:
```bash
python pipeline_new.py                    # Vollständige Pipeline
python pipeline_new.py --skip-nougat      # Ohne Nougat OCR
python pipeline_new.py --step extract     # Nur Text-Extraktion
```

### 2. CLI-Module nutzen:
```bash
# Text-Extraktion
python -m src.cli.extract

# Suche (kombiniert Text + Formeln)
python -m src.cli.search text --q "POD reconstruction" --k 10
python -m src.cli.search formula --symbol Re --limit 5
python -m src.cli.search combined --q "fluid dynamics" --symbol omega

# Analyse
python -m src.cli.analyze duplicates
python -m src.cli.analyze relevance --keywords "CFD,turbulence,flow"

# Pipeline-Management
python -m src.cli.pipeline full
python -m src.cli.pipeline extract
python -m src.cli.pipeline nougat
```

### 3. Programmierung mit neuen Modulen:
```python
from src.pipeline.search import search_whoosh
from src.formulas.search import search_formulas
from src.analysis.duplicates import scan_duplicates

# Volltext-Suche
results = search_whoosh("machine learning", k=5)

# Formelsuche
formulas = search_formulas(symbol="Re", limit=10)

# Duplikaterkennung
duplicates = scan_duplicates()
```

## Vorteile der Umstrukturierung

1. **Klare Trennung**: Bibliothekscode vs. CLI-Interface
2. **Bessere Imports**: Logische Modulstruktur
3. **Testbarkeit**: Jedes Modul einzeln testbar
4. **Wiederverwendbarkeit**: Funktionen können einfach importiert werden
5. **Erweiterbarkeit**: Neue Module können leicht hinzugefügt werden

## Migration

- **Alte tools/** bleiben vorerst erhalten für Kompatibilität
- **Neue Funktionalität** sollte die src/**-Module verwenden
- **pipeline_new.py** ersetzt das alte pipeline.py
- **CLI-Module** bieten benutzerfreundlichere Interfaces

## Nächste Schritte

1. Testen der neuen Module
2. Schrittweise Migration von tools/ zu src/
3. Erweiterung der CLI-Interfaces
4. Unit-Tests für alle Module hinzufügen