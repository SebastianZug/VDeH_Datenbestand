# Title/Year Search Implementation

## Überblick

Die **Title/Year (TY)** Suchmethode ist die dritte DNB-Enrichment-Strategie, die Records ohne ISBN/ISSN und ohne Autoren erreichen kann.

## Motivation

**Problem:**
- 40,769 Records fehlen Autoren
- Nur 3,161 (7.8%) haben ISBN/ISSN → können via ID-Suche angereichert werden
- Nur ~1,200 (2.9%) haben Autoren → können via Title/Author-Suche angereichert werden
- **37,608 Records (92.2%) haben WEDER ISBN/ISSN NOCH Autoren**

**Lösung:**
- Title/Year Suche für Records mit Titel + Jahr (aber ohne ISBN/ISSN/Autoren)
- Potenzial: 16,458 Records
- Erwartete Ausbeute: 1,645-2,468 zusätzliche Autoren (20-30% DNB-Abdeckung)

## Implementierung

### 1. DNB API Extension ([src/dnb_api.py](../src/dnb_api.py))

Neue Funktion: `query_dnb_by_title_year(title, year, max_records=1, max_retries=3)`

**4-stufige Suchstrategie:**
1. Exakter Titel (mit Quotes) + exaktes Jahr
2. Titel ohne Quotes + exaktes Jahr
3. Exakter Titel + Jahr ±1 (für Publikationsvarianten)
4. Titel ohne Quotes + Jahr ±1

**SRU Query Format:**
```python
# Strategie 1
query = f'tit="{title_clean}" and jhr={year}'

# Strategie 3
query = f'tit="{title_clean}" and jhr>={year-1} and jhr<={year+1}'
```

**Features:**
- Automatische Retry-Logik mit exponentialem Backoff
- MARC21-XML Parsing
- Extraktion: title, authors, year, publisher, isbn, issn

### 2. Notebook 04 Extension ([notebooks/01_vdeh_preprocessing/04_vdeh_data_enrichment.ipynb](../notebooks/01_vdeh_preprocessing/04_vdeh_data_enrichment.ipynb))

**Neue Zelle:** Title/Year Enrichment (nach Title/Author)

**Kandidaten-Identifikation:**
```python
title_year_candidates = df_vdeh[
    (df_vdeh['isbn'].isna()) &
    (df_vdeh['issn'].isna()) &
    ((df_vdeh['authors_str'].isna()) | (df_vdeh['authors_str'] == '')) &
    (df_vdeh['title'].notna()) &
    (df_vdeh['year'].notna())
]
```

**Neue Spalten:**
- `dnb_title_ty`
- `dnb_authors_ty`
- `dnb_year_ty`
- `dnb_publisher_ty`
- `dnb_isbn_ty`
- `dnb_issn_ty`

**Persistierung:**
- `data/vdeh/processed/dnb_title_year_data.parquet`

### 3. Fusion Engine Extension ([src/fusion/fusion_engine.py](../src/fusion/fusion_engine.py))

**Strategie:** TY als **Fallback mit Similarity-Validierung**

**Logik:**
```python
# Fall 1: Nur TY verfügbar (kein ID, kein TA)
if dnb_id is None and dnb_ta is None and dnb_ty is not None:
    # Berechne Titel-Ähnlichkeit
    similarity = calculate_title_similarity(vdeh_title, dnb_ty_title)

    # Akzeptiere nur wenn Similarity ≥ 70%
    if similarity >= 0.7:
        # Nutze TY als Gap-Filling
        # VDEH-Werte haben Priorität, TY füllt nur leere Felder
    else:
        # Reject - zu unsicher
        return vdeh_data
```

**Similarity-Threshold: 70%**
- **Eliminiert False Positives:** Kurze generische Titel ("Casting", "Corrosion") werden abgelehnt
- **Akzeptiert hochwertige Matches:** Spezifische Titel mit >70% Übereinstimmung
- **Balance:** 57.6% der TY-Matches werden akzeptiert (193 von 335)
- **Vorteil:** Datenqualität > Datenquantität

**Warum Similarity statt AI?**
- TY-Records haben keine ISBN/ISSN/Autoren zum Abgleichen
- Titel-Vergleich ist ausreichend und schneller als AI
- AI-Validierung würde bei fehlenden Feldern nichts bringen
- ID/TA haben Priorität (werden via AI validiert)

**Fusion-Hierarchie:**
1. **ID-Variante** (ISBN/ISSN) - höchste Priorität (AI-validiert)
2. **TA-Variante** (Title/Author) - zweite Priorität (AI-validiert)
3. **TY-Variante** (Title/Year) - Fallback mit Similarity-Filter (≥70%)
4. **VDEH** - Original immer als Basis

### 4. Testing

**Test-Skripte:**
- `scripts/test_title_year_search.py` - Initiale Tests
- `scripts/test_title_year_with_known_books.py` - Validation mit bekannten Büchern
- `scripts/analyze_title_year_potential.py` - Potenzial-Analyse

**Test-Ergebnisse:**
- ✅ 6/7 bekannte deutsche Bücher gefunden (86% Erfolg)
- ⚠️ VDEH-Records (technische Berichte) nicht in DNB
- 📊 ~50% VDEH-Kandidaten sind technische Berichte (niedrige DNB-Abdeckung)
- 📊 ~50% VDEH-Kandidaten sind potenziell publizierte Bücher (20-30% DNB-Abdeckung)

## Tatsächliche Ergebnisse (mit 70% Similarity-Filter)

### Vorher (nur ID + TA):
- Autoren gefüllt: 371 von 40,769 (0.9%)
- ISBN gefüllt: 604
- ISSN gefüllt: 127

### Nachher (mit TY + Similarity-Filter):
- **Hochwertige TY-Matches:** 193 von 335 Raw-Matches (57.6% Akzeptanz)
- **Neue Autoren:** ~101 zusätzliche Records mit Autoren
- **Autoren gefüllt:** **~472** (371 + 101) von 40,769 (**1.2%**)
  - **Verbesserung:** +27% (nicht 5-8x wie initial erwartet)
- **ISBN gefüllt:** ~607 (+3, TY-Records haben selten ISBN)
- **ISSN gefüllt:** ~241 (+114, viele Zeitschriften)
- **Publisher gefüllt:** +190 zusätzliche Records

### Warum weniger als erwartet?

**Initial geschätzt:** 1,645-2,468 neue Autoren (10-15% DNB-Abdeckung)

**Tatsächlich:** ~101 neue Autoren (0.6% der 16,458 TY-Kandidaten)

**Gründe:**
1. **DNB-Abdeckung nur 2%** (statt 10-15%)
   - 95.2% der TY-Queries fanden kein DNB-Match
   - VDEH-Bestand enthält viele technische Berichte, Normen, Standards (nicht in DNB)

2. **Similarity-Filter eliminiert 42.4%**
   - Von 335 Raw-Matches → 193 akzeptiert, 142 abgelehnt
   - Notwendig um False Positives zu vermeiden

3. **Impact trotzdem wertvoll:**
   - **+27% mehr Autoren** (371 → 472)
   - **+90% mehr ISSN** (127 → 241)
   - **Hohe Datenqualität** durch Similarity-Validierung

### API-Kosten:
- ~16,458 neue Queries (vollständig durchgeführt)
- Bei 1 Query/sec: ~4.6 Stunden
- Rate-Limiting: 1s Pause pro Query
- **Tatsächlicher Ertrag:** 193 hochwertige Matches

## Datenfluss

```
01_loaded_data.parquet (MARC21)
    ↓
04_dnb_enriched_data.parquet
    ├── dnb_*        (ID-Variante: ISBN/ISSN)
    ├── dnb_*_ta     (TA-Variante: Title/Author)
    └── dnb_*_ty     (TY-Variante: Title/Year) ← NEU
    ↓
05_fused_data.parquet
    ├── fusion_*_source
    │   ├── 'vdeh'
    │   ├── 'dnb_id'
    │   ├── 'dnb_title_author'
    │   └── 'dnb_title_year' ← NEU
    └── dnb_variant_selected
        ├── 'id'
        ├── 'title_author'
        └── 'title_year' ← NEU
```

## Verwendung

### DNB API:
```python
from src.dnb_api import query_dnb_by_title_year

result = query_dnb_by_title_year('Die Verwandlung', 1915)
if result:
    print(result['title'])    # "Die Verwandlung"
    print(result['authors'])  # ['Kafka, Franz']
    print(result['year'])     # 1915
    print(result['isbn'])     # None (alte Ausgabe ohne ISBN)
```

### Fusion:
```python
# Automatisch in FusionEngine.merge_record()
# TY wird nur genutzt wenn ID und TA beide None sind
```

### Notebook 04 ausführen:
```bash
poetry run papermill \
    notebooks/01_vdeh_preprocessing/04_vdeh_data_enrichment.ipynb \
    output.ipynb
```

## Einschränkungen

1. **DNB-Abdeckung:** Technische Berichte nicht in DNB
   - ~50% VDEH-Kandidaten sind Conference Proceedings / Forschungsberichte
   - DNB fokussiert auf publizierte Bücher, Zeitschriften, Dissertationen

2. **Genauigkeit:** Titel+Jahr weniger präzise als ISBN
   - Mehrere Ausgaben desselben Werks möglich
   - ±1 Jahr-Toleranz kann zu falschen Matches führen
   - Daher nur als Fallback ohne AI-Validierung

3. **Performance:** ~4.6 Stunden für volle Abfrage
   - 16,458 Queries à 1 Sekunde
   - Kann parallelisiert werden (mit Vorsicht wegen Rate-Limiting)

## Nächste Schritte

1. ✅ API-Funktion implementiert
2. ✅ Notebook 04 erweitert
3. ✅ Fusion-Engine angepasst
4. ⏳ Pipeline komplett ausführen
5. ⏳ Ergebnisse analysieren
6. ⏳ Reports aktualisieren

## Änderungshistorie

- **2025-12-12:** Initiale Implementierung
  - DNB API Extension
  - Notebook 04 Title/Year Cell
  - Fusion Engine Fallback-Logik
  - Testing und Validation
  - Potenzial-Analyse
