# Library of Congress (LoC) Integration - Changelog

## Version 2.2.1 - December 2025

### 🎯 Neue Features

#### 1. **Library of Congress API Client** (`src/loc_api.py`)
- Vollständige SRU API Integration für LoC
- Vier Suchstrategien:
  - `query_loc_by_isbn()` - ISBN-basierte Suche
  - `query_loc_by_issn()` - ISSN-basierte Suche
  - `query_loc_by_title_author()` - Titel/Autor-Suche mit 4-stufiger Fallback-Strategie
  - `query_loc_by_title_year()` - Titel/Jahr-Suche mit Jahr-Toleranzen (±1 Jahr)
- MARC21 XML Parsing (analog zu DNB)
- Exponential Backoff Retry-Logik (max. 3 Versuche)
- Text-Normalisierung für tolerantere Suche

#### 2. **LoC Enrichment Notebook** (`notebooks/01_vdeh_preprocessing/04b_vdeh_loc_enrichment.ipynb`)
- **Fokus auf englischsprachige Literatur** (`detected_language == 'en'`)
- Parallele Verarbeitung zu DNB (04_vdeh_data_enrichment.ipynb)
- Drei Datenvarianten:
  - `loc_*` - ID-Variante (aus ISBN/ISSN-Suche)
  - `loc_*_ta` - Titel/Autor-Variante
  - `loc_*_ty` - Titel/Jahr-Variante
- Inkrementelle Verarbeitung mit automatischer Zwischenspeicherung
- Rate Limiting: 1.5s zwischen Anfragen

#### 3. **Erweiterte Fusion-Engine** (`src/fusion/fusion_engine.py`)
- Integration von DNB + LoC Daten
- AI-basierte Variantenauswahl mit 4 Optionen:
  - A: DNB-ID (ISBN/ISSN-basiert)
  - B: DNB-TA (Titel/Autor-basiert)
  - C: LoC-ID (ISBN/ISSN-basiert)
  - D: LoC-TA (Titel/Autor-basiert)
- Intelligente Priorisierung:
  - DNB für deutschsprachige Werke (`de`, `ger`)
  - LoC für englischsprachige Werke (`en`, `eng`)
  - ID-Varianten bevorzugt gegenüber TA-Varianten
- Backward-kompatibel: `enable_loc=False` für reine DNB-Fusion

### 📊 Erwartete Verbesserungen

- **Englischsprachige Literatur**: Deutlich bessere Metadaten-Abdeckung
- **Internationale Publikationen**: Ergänzung zu DNB-Daten
- **ISBN/ISSN-Gewinn**: Zusätzliche Identifier für Records ohne ISBN

### 🔧 API-Details

**LoC SRU Endpoint:**
- URL: `http://lx2.loc.gov:210/lcdb`
- Protocol: SRU (Search/Retrieve via URL)
- Format: MARC21-xml
- Query Language: CQL (Contextual Query Language)

### 📁 Neue Dateien

```
src/
└── loc_api.py                              # LoC API Client

notebooks/01_vdeh_preprocessing/
└── 04b_vdeh_loc_enrichment.ipynb           # LoC Enrichment

data/vdeh/processed/
├── 04b_loc_enriched_data.parquet           # Output: Angereicherte Daten
├── 04b_metadata.json                       # Metadaten
├── loc_raw_data.parquet                    # ISBN/ISSN Query-Cache
├── loc_title_author_data.parquet           # Titel/Autor Query-Cache
└── loc_title_year_data.parquet             # Titel/Jahr Query-Cache
```

### 🔄 Aktualisierte Dateien

- `src/fusion/fusion_engine.py` - Erweitert für DNB + LoC
- `notebooks/01_vdeh_preprocessing/05_vdeh_data_fusion.ipynb` - TODO: Aktualisierung für LoC-Integration

### 🚀 Nutzung

1. **LoC Enrichment ausführen:**
   ```bash
   cd notebooks/01_vdeh_preprocessing
   jupyter notebook 04b_vdeh_loc_enrichment.ipynb
   ```

2. **Fusion mit LoC-Daten (TODO):**
   - Notebook 05 muss noch aktualisiert werden, um LoC-Daten zu laden
   - Fusion-Engine ist bereits vorbereitet (`enable_loc=True`)

### 🎓 Hintergrund

Die Library of Congress ist die größte Bibliothek der Welt und hat besonders umfangreiche Metadaten für:
- Englischsprachige Literatur
- US-Publikationen
- Internationale wissenschaftliche Werke

Die Integration ergänzt die DNB-Daten perfekt für einen bi-nationalen Bestandsabgleich.

### ⚠️ Bekannte Einschränkungen

- LoC SRU API ist teilweise langsamer als DNB (daher 1.5s Rate Limit)
- Einige Query-Formate werden unterschiedlich interpretiert
- HTTP statt HTTPS auf Port 210 (SSL-Probleme vermeiden)

### 📝 TODO

- [ ] Notebook 05 aktualisieren für LoC-Daten Integration
- [ ] Gap-Filling-Logik in Notebook 05 erweitern
- [ ] Statistiken über DNB vs. LoC Erfolgsraten
- [ ] Dokumentation vervollständigen
