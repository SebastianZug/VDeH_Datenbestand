# ISBN Corruption Fix

## Problem

Die DNB-Abfrage-Daten (`dnb_raw_data.parquet`) enthalten 2.407 korrupte ISBN-Einträge, bei denen ISBNs falsch konkateniert wurden.

**Beispiel:**
- Original: `3-514-00354-8`
- Korrupt: `35140035483540510400`

## Impact

- **DNB-Erfolgsrate**: Aktuell 82% für deutsche Werke, sollte ~90% sein
- **Betroffene Records**: 2.407 von 10.780 DNB-Abfragen
- **UB-Matching**: Potenziell ~81 fehlende Matches

## Lösung

Das Script `fix_isbn_corruption.py` behebt das Problem automatisch:

### Was macht das Script?

1. ✅ **Backup**: Erstellt Backups aller betroffenen Dateien
2. 🔍 **Identifikation**: Findet alle korrupten ISBN-Einträge
3. 🗑️ **Bereinigung**: Löscht korrupte Einträge aus `dnb_raw_data.parquet`
4. 🔄 **Re-Query**: Fragt DNB für 2.407 ISBNs neu ab (~40 Min)
5. 🔗 **Merge**: Führt DNB-Enrichment-Merge neu aus (~2 Min)
6. 🤖 **Fusion**: Führt KI-Fusion neu durch (~1 Min)
7. 📊 **Matching**: Führt UB-Matching neu durch (~5 Min)
8. 📈 **Statistiken**: Berechnet Paper-Statistiken neu (~1 Min)

### Geschätzte Dauer

**~50-60 Minuten** (hauptsächlich DNB-Abfrage mit Rate Limit)

## Ausführung

```bash
cd /media/sz/Data/Bibo/analysis
poetry run python scripts/fix_isbn_corruption.py
```

Das Script wird Sie um Bestätigung bitten, bevor es startet.

## Backups

Alle Backups werden gespeichert in:
```
data/vdeh/processed/backups/isbn_fix_YYYYMMDD_HHMMSS/
```

Enthält:
- `dnb_raw_data.parquet`
- `04_dnb_enriched_data.parquet`
- `04b_loc_enriched_data.parquet`
- `06_vdeh_dnb_loc_fused_data.parquet`

## Manuelle Alternative

Falls das automatische Script nicht funktioniert:

### 1. Backup erstellen
```bash
cd data/vdeh/processed
mkdir -p backups/manual_fix
cp dnb_raw_data.parquet backups/manual_fix/
cp 04_dnb_enriched_data.parquet backups/manual_fix/
cp 06_vdeh_dnb_loc_fused_data.parquet backups/manual_fix/
```

### 2. Notebooks manuell ausführen

1. **DNB Enrichment**: `notebooks/01_vdeh_preprocessing/04_vdeh_data_enrichment.ipynb`
   - Löschen Sie zuerst `dnb_raw_data.parquet`
   - Führen Sie das Notebook aus (wird nur korrupte ISBNs neu abfragen)

2. **Fusion**: `notebooks/01_vdeh_preprocessing/05_vdeh_dnb_loc_fusion.ipynb`

3. **UB Matching**: `notebooks/02_ub_comparision/data_matching.ipynb`

4. **Statistiken**: `python scripts/generate_paper_stats.py`

## Erwartete Ergebnisse

Nach dem Fix:

- ✅ DNB-Erfolgsrate für deutsche Werke: **~90%** (statt 82%)
- ✅ Saubere ISBN-Daten in allen Dateien
- ✅ Potenziell **+81 UB-Matches** (von 4.343 auf ~4.424)
- ✅ Verbesserte Datenqualität für Paper

## Verifikation

Nach dem Fix können Sie prüfen:

```python
import pandas as pd

# Check DNB raw data
dnb = pd.read_parquet('data/vdeh/processed/dnb_raw_data.parquet')
corrupted = dnb[dnb['query_value'].str.len() > 15]
print(f"Korrupte ISBNs: {len(corrupted)}")  # Sollte 0 sein

# Check success rate for German works
vdeh = pd.read_parquet('data/vdeh/processed/03_language_detected_data.parquet')
german = dnb.merge(vdeh[['id', 'language']], left_on='vdeh_id', right_on='id')
german = german[german['language'] == 'ger']
success_rate = (german['dnb_found'] == True).sum() / len(german) * 100
print(f"DNB Erfolgsrate (Deutsch): {success_rate:.1f}%")  # Sollte ~90% sein
```

## Rollback

Falls Sie zurück zum alten Stand wollen:

```bash
cd data/vdeh/processed/backups/isbn_fix_YYYYMMDD_HHMMSS/
cp * ../../
```

## Support

Bei Problemen:
1. Prüfen Sie die Log-Ausgabe des Scripts
2. Backups sind in `backups/` verfügbar
3. Der Code-Bug ist bereits behoben - aktuelle Notebooks sind korrekt
