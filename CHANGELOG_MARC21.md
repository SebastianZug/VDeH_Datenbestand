# Changelog - MARC21 Migration

## [2.1.0] - 2025-12-12

### 🚀 New Features

#### Title/Year DNB Search (Third Strategy)
- **New search method**: `query_dnb_by_title_year(title, year)` in `src/dnb_api.py`
- **Target audience**: 16,458 records without ISBN/ISSN/Authors but with Title+Year
- **Search strategies**: 4-stage approach (exact/fuzzy title, exact/±1 year)
- **Expected yield**: 1,645-2,468 additional authors (5-8x improvement!)
- **Integration**: Notebook 04 extended with Title/Year enrichment cell
- **Fusion**: Automatic TY fallback when ID/TA unavailable (no AI needed)

#### Pages (Seitenzahlen) Tracking
- **DNB API**: Extended to extract pages from MARC21 field 300
- **MARC21 Parser**: Already extracted pages (49.9% coverage)
- **DNB pages columns**: `dnb_pages`, `dnb_pages_ta`, `dnb_pages_ty`
- **Fusion**: Pages field integrated into all fusion paths
- **Expected coverage**: ~55-60% after DNB enrichment

### ✨ Improvements

#### DNB Enrichment
- **Three DNB variants**: ID (ISBN/ISSN), TA (Title/Author), TY (Title/Year)
- **Hierarchical fallback**: ID → TA → TY
- **Gap filling**: TY fills gaps unreachable by ID/TA

#### Documentation
- **New**: `docs/title_year_implementation.md` - Complete TY implementation guide
- **Updated**: README.md with v2.1.0 features
- **Scripts**: Archived 29 test scripts to `scripts/archive_old_tests/`

### 📝 Modified Files

#### Core
- `src/dnb_api.py` - Added `query_dnb_by_title_year()` and pages extraction
- `src/fusion/fusion_engine.py` - Added TY fallback logic and pages field
- `notebooks/01_vdeh_preprocessing/04_vdeh_data_enrichment.ipynb` - Added TY cell
- `notebooks/01_vdeh_preprocessing/05_vdeh_data_fusion.ipynb` - Extended for TY variant

#### Documentation
- `README.md` - Updated to v2.1.0, added TY and pages features
- `CHANGELOG_MARC21.md` - This file
- `docs/title_year_implementation.md` - New implementation guide
- `scripts/README.md` - New scripts directory documentation

### 🗑️ Cleaned Up

#### Archived Scripts
- Moved 29 test/development scripts to `scripts/archive_old_tests/`:
  - `add_gap_filling_to_fusion.py`
  - `add_table_explanation.py`
  - `analyze_author_gap.py`
  - `deep_analysis_authors.py`
  - `test_title_year_*.py`
  - ...and 24 more

### 📊 Expected Impact

| Metric | Before | After (Expected) | Improvement |
|--------|--------|------------------|-------------|
| **Authors filled** | 371 (0.9%) | 2,016-2,839 (4.9-7.0%) | **+5-8x** |
| **Pages coverage** | 29,080 (49.9%) | ~32,000-35,000 (55-60%) | **+5-10pp** |
| **DNB strategies** | 2 (ID, TA) | 3 (ID, TA, TY) | **+50%** |

### 🔄 Migration Guide

#### No Breaking Changes
- ✅ Existing notebooks work without modification
- ✅ Title/Year enrichment is optional (fallback only)
- ✅ Pages field is backward compatible

#### To Use New Features
```bash
# Re-run enrichment (existing queries skipped, only TY added)
poetry run papermill notebooks/01_vdeh_preprocessing/04_vdeh_data_enrichment.ipynb output_04.ipynb

# Re-run fusion (only TY records re-fused, ~5-10 min)
poetry run papermill notebooks/01_vdeh_preprocessing/05_vdeh_data_fusion.ipynb output_05.ipynb
```

---

## [3.0.0-marc21] - 2025-12-09

### 🎯 Major Changes

#### Neue MARC21-Datenquelle
- **Primäre Datenquelle**: `marcVDEH.xml` (MARC21 Format)
- **Format-Wechsel**: Von MAB (Deutsch) zu MARC21 (International)
- **Records**: 58,305 (vorher: 58,760 MAB)

### ✨ Verbesserungen

#### Datenqualität
- **Titel-Vollständigkeit**: 99.9% (vorher: 69.5%) → **+17,412 Records**
- **Seitenzahl-Informationen**: 49.9% (vorher: 0%) → **+29,000 Records**
- **Autoren-Abdeckung**: 30.1% (vorher: 28.9%) → +525 Records

#### Neue Features
- MARC21 Parser mit vollem Feldmapping
- Jahr-Extraktion aus `controlfield 008`
- Seitenzahl-Extraktion aus Feld 300
- **Sprach-Extraktion aus MARC21** (Feld 041 / controlfield 008) - 51.8% Abdeckung
- **Dual-Source Language Strategy**: MARC21 Sprache + langdetect kombiniert
- Standardisiertes internationales Format

### 📝 Neue Dateien

#### Parser & Tools
- `src/parsers/marc21_parser.py` - MARC21 Parser
- `scripts/test_marc21_parser.py` - Parser-Tests
- `scripts/compare_all_sources.py` - Datenquellen-Vergleich

#### Notebooks
- `notebooks/01_vdeh_preprocessing/01_vdeh_data_loading.ipynb` - MARC21 Data Loading (umbenannt von `_marc21`)
- `notebooks/01_vdeh_preprocessing/03_vdeh_language_detection.ipynb` - Erweitert für Dual-Source Language
- `notebooks/01_vdeh_preprocessing/05_vdeh_data_fusion.ipynb` - Erweitert für Language Fusion

#### Dokumentation
- `MIGRATION_PLAN_MARC21.md` - Migrations-Plan
- `reports/MIGRATION_REPORT_MARC21.md` - Abschlussbericht
- `reports/LANGUAGE_ANALYSIS_MARC21.md` - Sprach-Analyse und Dual-Source Strategie
- `CHANGELOG_MARC21.md` - Dieses Dokument

### 🗑️ Entfernte Dateien

#### Reports (veraltet)
- `reports/titel_analyse_vergleich.md/pdf`
- `reports/missing_titles_investigation.md`
- `reports/vdeh_enrichment_report.md`
- `reports/Leistungsangebot.md`

#### Scripts (ersetzt)
- `scripts/analyze_failed_queries.py`
- `scripts/analyze_marc_vdeh.py` (ersetzt durch `compare_all_sources.py`)

#### Notebooks (gelöscht/archiviert)
- `notebooks/02_vdeh_analysis/01_vdeh_quality_analysis.ipynb`
- `notebooks/02_vdeh_analysis/02_vdeh_enrichment_conflicts.ipynb`
- `notebooks/template_new.ipynb`
- `notebooks/02_vdeh_analysis/Mikromobile in Mittelsachsen.md`
- `notebooks/01_vdeh_preprocessing/01_vdeh_data_loading.ipynb` (MAB) → archiviert

### 📦 Archivierte Dateien

#### MAB-Daten
- Alle `.parquet` Dateien → `data/vdeh/archive/mab_format/`
- Legacy-Config in `config.yaml` unter `vdeh_mab_legacy` (archived: true)

### ⚙️ Konfigurationsänderungen

#### config.yaml
```yaml
data_sources:
  vdeh:
    type: "marc21_xml"  # GEÄNDERT
    path: "data/vdeh/raw/marcVDEH.xml"  # GEÄNDERT
    parser_module: "src/parsers/marc21_parser.py"  # GEÄNDERT
    estimated_records: 58305  # GEÄNDERT

data_processing:
  marc21_parser:  # NEU
    max_records: null
    encoding: "utf-8"
```

### 🔄 Kompatibilität

#### Abwärtskompatibel
- ✅ Output-Schema identisch zu MAB
- ✅ Notebooks 02-05 sollten ohne Änderungen funktionieren
- ✅ DNB-Enrichment profitiert von besserer Datenqualität

#### Breaking Changes
- ⚠️ Notebook 01 verwendet jetzt `marc21_parser` statt `vdeh_parser`
- ⚠️ 455 weniger Records (0.8%) in MARC21-Daten

### 📊 Erwartete Auswirkungen

#### DNB-Enrichment
- **Match-Rate**: +10-15% erwartet (von ~65% auf ~75-80%)
- **Grund**: 17,412 zusätzliche Records mit Titeln

#### Datenqualität
- Bessere Metadaten für alle downstream-Prozesse
- Mehr Seitenzahl-Informationen für Analysen
- **Sprach-Abdeckung**: ~97% durch Dual-Source Strategie (MARC21 + langdetect)
- Standardisiertes Format erleichtert zukünftige Integrationen

### 🌍 Dual-Source Language Strategy

**Implementation:** 2025-12-09

#### Strategie
1. **MARC21 Language** (`language` Spalte)
   - Quelle: MARC21 Feld 041$a oder controlfield 008
   - Format: ISO 639-2 Codes (ger, eng, fre)
   - Abdeckung: 30,173 Records (51.8%)
   - Genauigkeit: 100% (Katalogmetadaten)

2. **langdetect** (`detected_language` Spalte)
   - Quelle: Titel-basierte Erkennung
   - Format: ISO 639-1 Codes (de, en, fr)
   - Abdeckung: 56,859 Records (97.5%)
   - Genauigkeit: ~80-90% (abhängig von Textqualität)

3. **Fusion** (`language_final` Spalte)
   - Priorität: MARC21 > langdetect
   - Gesamt-Abdeckung: ~97% aller Records
   - Beide verfügbar: 29,929 Records (für Qualitätsprüfung)

#### Pipeline-Integration
- **Notebook 01**: MARC21 Sprache extrahieren → `language`
- **Notebook 03**: langdetect ausführen → `detected_language`, `detected_language_confidence`
- **Notebook 05**: Fusion-Logik → `language_final`, `language_source`, `language_confidence`

### 🧪 Tests

#### Parser-Tests
- ✅ 100 Records: 100% Titel, 100% Jahr, 78% Autoren
- ✅ Pipeline: 58,305 Records erfolgreich verarbeitet

#### Validierung
- ✅ Feldmapping korrekt
- ✅ Datenqualität überprüft
- ✅ Notebook 01 läuft fehlerfrei
- ✅ Dual-Source Language: 56,859 Records (97.5% Abdeckung)

### 📚 Weitere Dokumentation

- [README.md](README.md) - Aktualisiert mit Datenquellen-Vergleich
- [MIGRATION_PLAN_MARC21.md](MIGRATION_PLAN_MARC21.md) - Detaillierter Plan
- [reports/MIGRATION_REPORT_MARC21.md](reports/MIGRATION_REPORT_MARC21.md) - Technischer Bericht

---

## Legacy-Versionen

### [2.0.0] - 2024-11-19
- KI-gestützte Datenfusion mit Ollama
- Multi-Strategy DNB-Anreicherung
- MAB-Format als primäre Datenquelle

### [1.0.0] - 2024-10-31
- Initiales Release
- Dual-Source Bestandsvergleich
- Basic DNB-Enrichment
