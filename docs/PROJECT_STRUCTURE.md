# VDEh-Bibliotheksanalyse - Projektstruktur

## Übersicht

```
analysis/
├── config/                             # Konfigurationsdateien
│   └── report_config.yaml              # Report-Generator Konfiguration
│
├── data/                               # Datenverzeichnisse
│   ├── vdeh/                           # VDEh Daten
│   │   ├── raw/                        # Rohdaten (MARC21 XML)
│   │   └── processed/                  # Verarbeitete Daten
│   │       ├── 01_parsed_data.parquet
│   │       ├── 04_dnb_enriched_data.parquet
│   │       └── 05_fused_data.parquet
│   ├── ub_tubaf/                       # UB TUBAF Daten
│   │   └── processed/
│   ├── comparison/                     # Vergleichsergebnisse
│   └── processed/                      # Allgemeine verarbeitete Daten
│       └── report_analysis_results.json # Report-Analyse-Cache
│
├── docs/                               # Dokumentation
│   ├── REPORT_GENERATOR.md             # Report-Generator vollständige Doku
│   └── PROJECT_STRUCTURE.md            # Diese Datei
│
├── notebooks/                          # Jupyter Notebooks
│   ├── 01_vdeh_preprocessing/          # VDEh Verarbeitungspipeline
│   │   ├── 01_vdeh_data_loading.ipynb
│   │   ├── 04_vdeh_data_enrichment.ipynb
│   │   └── 05_vdeh_data_fusion.ipynb
│   ├── 02_ub_preprocessing/            # UB TUBAF Verarbeitung
│   └── 03_comparison/                  # VDEh vs. UB Vergleich
│
├── paper/                              # Report-Generator Dateien
│   ├── sections/                       # Jinja2-Templates für Report-Abschnitte
│   │   ├── 01_abstract.md.jinja
│   │   ├── 02_einleitung.md.jinja
│   │   ├── 03_datenaufbereitung.md.jinja
│   │   ├── 04_ergebnisse.md.jinja
│   │   ├── 05_diskussion.md.jinja
│   │   ├── 06_fazit.md.jinja
│   │   └── 07_literatur.md.jinja
│   ├── templates/                      # LaTeX-Templates
│   │   └── koma-article.tex            # Deutsches wissenschaftliches Layout
│   ├── figures/                        # Generierte Grafiken (geplant)
│   └── build/                          # Output-Verzeichnis
│       ├── report.md                   # Generierter Report (Markdown)
│       └── report.pdf                  # Generierter Report (PDF)
│
├── report/                             # Report-Generator Python-Module
│   ├── __init__.py
│   ├── report_builder.py               # Jinja2-Rendering & Pandoc-Export
│   └── analysis_runner.py              # Analyse-Orchestrierung
│
├── src/                                # Source Code Module
│   ├── parsers/                        # VDEh & MAB2 Parser
│   │   ├── vdeh_parser.py
│   │   ├── marc21_parser.py
│   │   └── base_parser.py
│   ├── fusion/                         # KI-Fusion Engine
│   │   ├── fusion_engine.py
│   │   ├── ollama_client.py
│   │   └── utils.py
│   ├── comparison/                     # Dubletten-Erkennung
│   │   └── matcher.py
│   ├── utils/                          # Utilities
│   │   └── notebook_utils.py
│   ├── dnb_api.py                      # DNB SRU API Client
│   ├── loc_api.py                      # Library of Congress API
│   └── config_loader.py
│
├── scripts/                            # Utility-Scripts
│   ├── test_fusion_engine.py
│   └── compare_dnb_strategies.py
│
├── run_report.py                       # Report-Generator Hauptskript ⭐
├── REPORT_QUICKSTART.md                # Schnellstart-Anleitung ⭐
├── README.md                           # Projekt-README
└── config.yaml                         # Legacy-Konfiguration (VDEh-Pipeline)
```

## Komponenten-Übersicht

### 1. VDEh-Datenverarbeitungs-Pipeline

**Zweck:** Aufbereitung und Anreicherung des VDEh-Bestandes

**Hauptschritte:**
1. **XML Parsing** (`notebooks/01_vdeh_preprocessing/01_*.ipynb`)
   - Input: `data/vdeh/raw/marcVDEH.xml`
   - Output: `data/vdeh/processed/01_parsed_data.parquet`
   - Records: 58.760

2. **DNB-Anreicherung** (`notebooks/01_vdeh_preprocessing/04_*.ipynb`)
   - Triple-Strategy: ISBN/ISSN + Titel/Autor + Titel/Jahr
   - Output: `data/vdeh/processed/04_dnb_enriched_data.parquet`
   - Erfolgsrate: ~60%

3. **KI-Fusion** (`notebooks/01_vdeh_preprocessing/05_*.ipynb`)
   - Ollama LLM (llama3.3:70b) für Varianten-Auswahl
   - Output: `data/vdeh/processed/05_fused_data.parquet`
   - Akzeptanzrate: ~45%

**Code-Module:**
- `src/parsers/marc21_parser.py` - MARC21-Feldextraktion
- `src/dnb_api.py` - DNB SRU API Client
- `src/fusion/fusion_engine.py` - KI-gestützte Fusion

### 2. Report-Generator (NEU in v2.3.0)

**Zweck:** Automatische Generierung wissenschaftlicher Reports

**Architektur:**
```
run_report.py
    ↓
AnalysisRunner (report/analysis_runner.py)
    ↓
    ├── Datenqualitäts-Analyse
    ├── Dubletten-Erkennung
    ├── Seitenzahlen-Analyse
    └── DNB-Anreicherungs-Statistiken
    ↓
ReportBuilder (report/report_builder.py)
    ↓
    ├── Jinja2-Rendering (paper/sections/*.md.jinja)
    ├── Markdown-Export (paper/build/report.md)
    └── Pandoc PDF-Export (paper/build/report.pdf)
```

**Hauptdateien:**
- `run_report.py` - Hauptskript (Entry Point)
- `config/report_config.yaml` - Konfiguration
- `report/analysis_runner.py` - Analysen
- `report/report_builder.py` - Report-Generierung
- `paper/sections/*.md.jinja` - Jinja2-Templates
- `paper/templates/koma-article.tex` - LaTeX-Template

**Output:**
- `paper/build/report.md` - Markdown-Version
- `paper/build/report.pdf` - PDF-Version

### 3. Dubletten-Erkennung & UB-Vergleich

**Zweck:** Identifikation von Überschneidungen mit UB TUBAF

**Notebooks:**
- `notebooks/03_comparison/01_vdeh_ub_collection_check.ipynb`

**Code-Module:**
- `src/comparison/matcher.py` - ISBN-Matching, Fuzzy-Matching

**Output:**
- `data/comparison/vdeh_ub_comparison.parquet`

**Matching-Strategien:**
1. ISBN-Exact-Match
2. ISBN-Normalized-Match
3. Titel-Fuzzy-Match (≥85%)
4. Autor-Fuzzy-Match (≥90%)

## Verwendungs-Workflows

### Workflow 1: Vollständige VDEh-Pipeline

```bash
# 1. VDEh-Daten laden und parsen
cd notebooks/01_vdeh_preprocessing
jupyter nbconvert --execute --to notebook 01_vdeh_data_loading.ipynb

# 2. DNB-Anreicherung
jupyter nbconvert --execute --to notebook 04_vdeh_data_enrichment.ipynb

# 3. KI-Fusion
jupyter nbconvert --execute --to notebook 05_vdeh_data_fusion.ipynb

cd ../..
```

### Workflow 2: Report generieren

```bash
# Vollständige Pipeline (Analysen + Report)
python run_report.py

# Nur Report (Analysen aus Cache)
python run_report.py --skip-analysis
```

### Workflow 3: UB-Vergleich durchführen

```bash
# 1. UB-Daten laden
cd notebooks/02_ub_preprocessing
jupyter nbconvert --execute --to notebook 01_ub_data_loading.ipynb

# 2. VDEh vs. UB Vergleich
cd ../03_comparison
jupyter nbconvert --execute --to notebook 01_vdeh_ub_collection_check.ipynb

cd ../..
```

## Datenfluss

```
MARC21 XML (marcVDEH.xml)
    ↓
[01_vdeh_data_loading.ipynb]
    ↓
01_parsed_data.parquet
    ↓
[04_vdeh_data_enrichment.ipynb] ← DNB API
    ↓
04_dnb_enriched_data.parquet
    ↓
[05_vdeh_data_fusion.ipynb] ← Ollama LLM
    ↓
05_fused_data.parquet
    ↓
[run_report.py]
    ├── AnalysisRunner → report_analysis_results.json
    └── ReportBuilder → report.md + report.pdf
```

## Konfigurationsdateien

### `config.yaml` (Legacy - VDEh-Pipeline)
- DNB API Einstellungen
- Fusion-Parameter
- Vergleichs-Strategien

### `config/report_config.yaml` (NEU - Report-Generator)
- Report-Metadaten (Titel, Autoren)
- Daten-Pfade
- Aktivierte Analysen
- Output-Formate
- Forschungsfragen

## Dependencies

### Python-Pakete
- `pandas` - Datenverarbeitung
- `lxml` - XML-Parsing
- `requests` - API-Kommunikation
- `langdetect` - Spracherkennung
- `ollama` - KI-Fusion
- `jinja2` - Template-Rendering (Report-Generator)
- `pyyaml` - Konfiguration

### Externe Tools
- **Pandoc** - Markdown → PDF Konvertierung
- **XeLaTeX** - PDF-Generierung
- **Ollama** - LLM-Server für KI-Fusion

## Forschungsfragen (Report)

Der generierte Report beantwortet:

**RQ1: Dubletten zwischen VDEh und UB TUBAF**
- Anzahl Dubletten und Dublettenrate
- Matching-Strategien-Verteilung
- Einzigartige Records für Digitalisierung

**RQ2: Digitalisierungsaufwand (Seitenzahlen)**
- Seitenzahlen-Abdeckung (VDEh vs. DNB)
- Gesamtseitenzahl und Durchschnitt
- Hochrechnung für fehlende Werte
- Einsparungen durch Dubletten-Eliminierung

**RQ3: Datenqualität und Pipeline-Effektivität**
- Metadaten-Verbesserungen (ISBN, ISSN, Autoren, etc.)
- DNB-Strategie-Effektivität
- KI-Fusion Performance

## Versionsverwaltung

**Aktuelle Version:** v2.3.0 (2025-12-30)

**Major Releases:**
- **v2.3.0** (2025-12-30): Report-Generator integriert
- **v2.2.0** (2025-12-12): ISBN-Cleanup, Seitenzahlen-Extraktion
- **v2.1.0**: Titel/Jahr-DNB-Strategie
- **v2.0.0**: KI-gestützte Fusion, Triple-Strategy DNB

## Weiterführende Dokumentation

- **Report-Generator**: `docs/REPORT_GENERATOR.md`
- **Schnellstart**: `REPORT_QUICKSTART.md`
- **Projekt-README**: `README.md`
- **Konfiguration**: `config/report_config.yaml`

## Kontakt

**Data Analysis Team**
TU Bergakademie Freiberg

Email: sebastian.zug@informatik.tu-freiberg.de
