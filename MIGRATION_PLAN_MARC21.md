# Migration von MAB zu MARC21 - Detaillierter Plan

**Datum:** 2025-12-09
**Version:** 1.0
**Status:** In Planung

---

## 🎯 Ziel

Umstellung der gesamten VDEH-Pipeline von MAB-Format (`VDEH_mab_all.xml`) auf MARC21-Format (`marcVDEH.xml`) als primäre Datenquelle.

## 📊 Ausgangslage

### Datenquellen-Vergleich

| Aspekt | MAB (alt) | MARC21 (neu) |
|--------|-----------|--------------|
| Datei | `VDEH_mab_all.xml` | `marcVDEH.xml` |
| Records | 58,760 | 58,305 (-455) |
| Format | MAB (Deutsch) | MARC21 (International) |
| Titel-Vollständigkeit | 69.5% | **99.9%** ✅ |
| Autoren-Vollständigkeit | 29.0% | **32.1%** ✅ |
| ISBN-Vollständigkeit | 18.3% | 18.2% |
| Seitenzahlen | 50.0% | 49.9% |

### Vorteile der Migration

1. ✅ **Drastisch bessere Titel-Vollständigkeit** (99.9% vs 69.5%)
2. ✅ **Standardisiertes Format** (MARC21 ist internationaler Standard)
3. ✅ **Bessere Autoren-Abdeckung** (32.1% vs 29.0%)
4. ✅ **Konsistenz mit DNB** (DNB liefert MARC21-Daten zurück)

### Herausforderungen

1. ⚠️ 455 weniger Records (58,305 vs 58,760)
2. ⚠️ Feldnummern ändern sich (331→245, 540→020, etc.)
3. ⚠️ Unterschiedliche XML-Struktur (keine OAI-PMH Wrapper)

---

## 🗺️ Feldmapping: MAB → MARC21

| Datenfeld | MAB Tag | MARC21 Tag | Subfield | Bemerkung |
|-----------|---------|------------|----------|-----------|
| **Titel** | 331 | 245 | $a | Haupttitel |
| Titelzusatz | 335 | 245 | $b | Untertitel |
| **Autor (Person)** | 100 | 100 | $a | Haupteintrag |
| Weitere Autoren | 104 | 700 | $a | Nebeneintrag |
| **Körperschaft** | 200 | 110 | $a | Haupteintrag |
| Weitere Körperschaften | 204 | 710 | $a | Nebeneintrag |
| **Jahr** | 425 | 260/264 | $c | Publikationsjahr |
| **Verlag (Name)** | 410 | 260/264 | $b | Publisher |
| Verlag (Ort) | 412 | 260/264 | $a | Place |
| **ISBN** | 540 | 020 | $a | ISBN |
| **ISSN** | 542 | 022 | $a | ISSN |
| **Seitenzahl** | 433 | 300 | $a | Physical description |
| Abstract | 750 | 520 | $a | Summary |
| Schlagwörter | 902 | 650 | $a | Subject |

---

## 📁 Betroffene Komponenten

### 1. Parser-Module

- ✅ **Neu:** `src/parsers/marc21_parser.py` (zu erstellen)
- 📝 **Ändern:** `src/parsers/__init__.py` (Import hinzufügen)
- 🔄 **Beibehalten:** `src/parsers/vdeh_parser.py` (für Referenz/Fallback)

### 2. Konfiguration

- 📝 **Ändern:** `config.yaml`
  - Pfad: `data/vdeh/raw/VDEH_mab_all.xml` → `/media/sz/Data/Bibo/data/marcVDEH.xml`
  - Parser: `vdeh_parser` → `marc21_parser`
  - Type: `oai_pmh_xml` → `marc21_xml`

### 3. Notebooks

Alle Notebooks in `notebooks/01_vdeh_preprocessing/`:

- 📝 **01_vdeh_data_loading.ipynb** - Parser-Import ändern
- 📝 **02_vdeh_data_preprocessing.ipynb** - Validierung anpassen (gleiche Felder)
- 📝 **03_vdeh_language_detection.ipynb** - Keine Änderung nötig
- 📝 **04_vdeh_data_enrichment.ipynb** - Keine Änderung nötig (DNB API)
- 📝 **05_vdeh_data_fusion.ipynb** - Keine Änderung nötig

### 4. Datenverzeichnisse

- 📁 **Neu:** Kopiere `marcVDEH.xml` → `data/vdeh/raw/marcVDEH.xml`
- 📁 **Archiv:** Verschiebe alte Outputs → `data/vdeh/archive/mab_format/`

---

## 🔧 Implementierungsschritte

### Phase 1: Parser-Entwicklung ✅

**Datei:** `src/parsers/marc21_parser.py`

**Funktionen:**
```python
def parse_bibliography(file_path: str, max_records: Optional[int] = None) -> pd.DataFrame:
    """Hauptfunktion - parst MARC21 XML"""

def _extract_title(document: ET.Element) -> Optional[str]:
    """Feld 245$a + $b"""

def _extract_authors(document: ET.Element) -> List[str]:
    """Felder 100$a + 700$a (Personen)"""

def _extract_authors_affiliation(document: ET.Element) -> List[str]:
    """Felder 110$a + 710$a (Körperschaften)"""

def _extract_year(document: ET.Element) -> Optional[int]:
    """Felder 260$c oder 264$c"""

def _extract_publisher(document: ET.Element) -> Optional[str]:
    """Felder 260$a + $b oder 264$a + $b"""

def _find_standard_numbers(document: ET.Element) -> tuple[Optional[str], Optional[str]]:
    """Felder 020$a (ISBN) + 022$a (ISSN)"""
```

**Output-Schema (identisch zu MAB):**
```python
{
    'id': str,
    'title': str,
    'authors': List[str],
    'authors_affiliation': List[str],
    'year': int,
    'publisher': str,
    'isbn': str,
    'issn': str,
    'authors_str': str,  # Joined string
    'num_authors': int,
    'authors_affiliation_str': str,
    'num_authors_affiliation': int
}
```

### Phase 2: Konfiguration ⚙️

**Datei:** `config.yaml`

```yaml
data_sources:
  vdeh:
    type: "marc21_xml"  # GEÄNDERT
    description: "Neuerwerbungen der VDEH Bibliotheken (MARC21 Format)"
    path: "data/vdeh/raw/marcVDEH.xml"  # GEÄNDERT
    parser_module: "src/parsers/marc21_parser.py"  # GEÄNDERT
    parser_class: "MARC21Parser"  # GEÄNDERT
    encoding: "utf-8"
    estimated_records: 58305  # GEÄNDERT

data_processing:
  marc21_parser:  # NEU
    max_records: null
    encoding: "utf-8"
```

### Phase 3: Notebook-Updates 📓

#### Notebook 01: Data Loading

**Änderungen:**
```python
# ALT:
from src.parsers.vdeh_parser import parse_bibliography

# NEU:
from src.parsers.marc21_parser import parse_bibliography

# Pfad anpassen:
input_file = config['data_sources']['vdeh']['path']
# → "data/vdeh/raw/marcVDEH.xml"
```

#### Notebooks 02-05

**Keine Änderungen nötig!**
- ISBN-Validierung arbeitet auf DataFrame-Ebene
- Language Detection arbeitet auf `title`-Spalte
- DNB Enrichment nutzt ISBN/Titel/Autoren
- Fusion nutzt allgemeine Felder

### Phase 4: Tests & Validation ✅

**Test-Script:** `scripts/test_marc21_migration.py`

```python
# 1. Parser-Test
df = parse_bibliography('data/vdeh/raw/marcVDEH.xml', max_records=100)
assert len(df) == 100
assert df['title'].notna().sum() > 95  # >95% mit Titel

# 2. Vollständigkeits-Check
total = len(df)
assert df['title'].notna().sum() / total > 0.99  # >99% Titel
assert df['num_authors'].gt(0).sum() / total > 0.30  # >30% Autoren

# 3. Feldtyp-Validierung
assert df['year'].dtype == 'Int64'
assert df['authors'].apply(type).eq(list).all()

# 4. Vergleich mit MAB-Output
df_mab = pd.read_parquet('data/vdeh/archive/mab_format/01_parsed_data.parquet')
df_marc21 = pd.read_parquet('data/vdeh/processed/01_parsed_data.parquet')

print(f"MAB Records: {len(df_mab):,}")
print(f"MARC21 Records: {len(df_marc21):,}")
print(f"Differenz: {len(df_mab) - len(df_marc21):,}")
```

### Phase 5: Pipeline-Ausführung 🚀

```bash
# 1. Alte Daten archivieren
mkdir -p data/vdeh/archive/mab_format
mv data/vdeh/processed/*.parquet data/vdeh/archive/mab_format/

# 2. MARC21-Datei kopieren
cp /media/sz/Data/Bibo/data/marcVDEH.xml data/vdeh/raw/

# 3. Pipeline ausführen
poetry run jupyter nbconvert --execute \
    notebooks/01_vdeh_preprocessing/01_vdeh_data_loading.ipynb

poetry run jupyter nbconvert --execute \
    notebooks/01_vdeh_preprocessing/02_vdeh_data_preprocessing.ipynb

# ... weitere Notebooks
```

---

## 📋 Checkliste

### Vor der Migration

- [ ] Backup aller bestehenden Daten erstellen
- [ ] MARC21-Datei verfügbar (`/media/sz/Data/Bibo/data/marcVDEH.xml`)
- [ ] Git-Commit aller aktuellen Änderungen
- [ ] Branch erstellen: `git checkout -b feature/marc21-migration`

### Implementierung

- [ ] MARC21 Parser implementiert (`src/parsers/marc21_parser.py`)
- [ ] Parser-Tests geschrieben und erfolgreich
- [ ] `config.yaml` aktualisiert
- [ ] Notebook 01 angepasst
- [ ] Alle Notebooks getestet

### Validierung

- [ ] Vollständigkeits-Vergleich durchgeführt (MAB vs MARC21)
- [ ] Stichproben-Prüfung (mindestens 100 Records manuell)
- [ ] DNB-Enrichment funktioniert
- [ ] Fusion funktioniert
- [ ] README aktualisiert

### Deployment

- [ ] Alte Daten archiviert
- [ ] Pipeline komplett durchgelaufen
- [ ] Qualitätsmetriken dokumentiert
- [ ] Git-Commit & Merge zu `main`
- [ ] Tag erstellen: `v3.0.0-marc21`

---

## 🔄 Rollback-Plan

Falls Probleme auftreten:

```bash
# 1. Git zurücksetzen
git checkout main
git branch -D feature/marc21-migration

# 2. Alte Daten wiederherstellen
cp data/vdeh/archive/mab_format/*.parquet data/vdeh/processed/

# 3. config.yaml zurücksetzen
git checkout config.yaml
```

---

## 📈 Erwartete Verbesserungen

| Metrik | MAB (alt) | MARC21 (neu) | Differenz |
|--------|-----------|--------------|-----------|
| Records gesamt | 58,760 | 58,305 | -455 (-0.8%) |
| Records mit Titel | 40,830 (69.5%) | 58,252 (99.9%) | **+17,422 (+30.4%)** 🚀 |
| Records mit Autor | 17,016 (29.0%) | 18,740 (32.1%) | +1,724 (+3.1%) ✅ |
| Records mit ISBN | 10,744 (18.3%) | 10,586 (18.2%) | -158 (-0.1%) |
| DNB-Match-Rate (geschätzt) | ~65% | ~75% | +10% 📈 |

**Hauptgewinn:** +17,422 Records mit vollständigen Titeln für DNB-Enrichment!

---

## 📝 Notizen

- Der Verlust von 455 Records ist akzeptabel angesichts der massiven Qualitätsverbesserung
- MARC21 ist konsistent mit DNB-Response-Format → bessere Integration
- Alle downstream-Prozesse (Validation, Language Detection, Enrichment, Fusion) bleiben unverändert
- Migration ist weitgehend rückwärtskompatibel (gleiches DataFrame-Schema)

---

**Nächster Schritt:** Implementierung des MARC21 Parsers
