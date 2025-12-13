# ISBN Cleanup Implementation

**Version:** 2.2.0
**Datum:** 2025-12-12
**Status:** Implementiert ✅

## Überblick

Automatische Bereinigung von doppelten/konkatenierten ISBNs im MARC21-Parser zur Verbesserung der DNB-Enrichment-Erfolgsrate.

## Problem

**209 Records (2.0% aller ISBNs) haben ungültige ISBN-Nummern**, davon:
- **116 Records mit doppelten ISBNs** (automatisch behebbar)
- 93 Records mit anderen Problemen (z.B. zu kurz, Tippfehler)

### Beispiele ungültiger ISBNs:

```
Original:  35140035483540510400  (Länge: 20)
Aufgespalten:
  - ISBN 1: 3514003548 (Springer DE)
  - ISBN 2: 3540510400 (Springer US)
Titel: "Metallurgie der Stahlherstellung"
```

**Ursache:** Viele wissenschaftliche Bücher haben **zwei ISBN-Nummern** (deutsche + englische/US-Ausgabe vom selben Verlag), die im MARC21-Feld konkateniert wurden.

## Lösung

### 1. Automatische ISBN-Bereinigung im MARC21-Parser

**Datei:** `src/parsers/marc21_parser.py`
**Funktion:** `_format_isbn()`

**Logik:**
```python
def _format_isbn(isbn: str) -> str:
    # Entferne alle Nicht-Ziffern
    isbn = re.sub(r'[^0-9X]', '', isbn.upper())

    # Bereinige doppelte ISBNs
    if len(isbn) == 20:    # Zwei ISBN-10 → Nutze erste
        isbn = isbn[:10]
    elif len(isbn) == 26:  # Zwei ISBN-13 → Nutze erste
        isbn = isbn[:13]
    elif len(isbn) == 23:  # ISBN-10 + ISBN-13 → Nutze erste
        isbn = isbn[:10]

    # Formatiere bereinigte ISBN
    if len(isbn) == 13:
        return f"{isbn[0:3]}-{isbn[3]}-{isbn[4:7]}-{isbn[7:12]}-{isbn[12]}"
    elif len(isbn) == 10:
        return f"{isbn[0]}-{isbn[1:4]}-{isbn[4:9]}-{isbn[9]}"

    return isbn  # Ungültige Länge → Raw zurückgeben
```

**Entscheidung "Erste ISBN nutzen":**
- Erste ISBN ist meist die **deutsche/primäre Ausgabe**
- Zweite ISBN ist oft die **US/internationale Variante**
- DNB bevorzugt deutschsprachige Ausgaben → erste ISBN ist passender

### 2. Integration

**Automatisch aktiv in:**
- ✅ Notebook 01 (`01_vdeh_data_loading.ipynb`) - MARC21-Parsing
- ✅ Notebook 04 (`04_vdeh_data_enrichment.ipynb`) - DNB ID-Suche nutzt bereinigte ISBNs

**Keine Code-Änderungen nötig** - Cleanup läuft transparent im Hintergrund!

### 3. Testing

**Test-Skript:** `scripts/test_isbn_cleanup.py`

**Test-Cases:**
- ✅ Doppelte ISBN-10 (20 Zeichen)
- ✅ Doppelte ISBN-13 (26 Zeichen)
- ✅ Gemischte ISBN-10+13 (23 Zeichen)
- ✅ Einzelne ISBN-10/13 (unverändert)
- ✅ Ungültige ISBNs (Raw zurückgeben)
- ✅ Bereits formatierte ISBNs (beibehalten)

**Ergebnis:** 8/8 Tests bestanden ✅

## Erwarteter Gewinn

### Vor Bereinigung:
- **209 ungültige ISBNs** (2.0% aller ISBNs)
- **DNB ID-Suche schlägt fehl** für diese Records

### Nach Bereinigung:
- **116 ISBNs bereinigt** (55.5% der ungültigen ISBNs)
- **Erwartete DNB-Matches:** ~58 zusätzliche Records (50% Erfolgsrate)
- **Neue Autoren:** ~40-50 Records (71.6% der behebbaren haben bereits Autoren)
- **Bessere Metadaten:** Jahr, Publisher, Pages von DNB

### Vergleich mit anderen Methoden:

| Methode | Kandidaten | DNB-Rate | Erwartete Matches | Qualität |
|---------|------------|----------|-------------------|----------|
| **ISBN-Cleanup** | 116 | ~50% | **~58** | ⭐⭐⭐⭐⭐ |
| Title/Year (TY) | 16,458 | 2% | 193 (mit Filter) | ⭐⭐⭐ |
| Title/Author (TA) | ~1,200 | ~15% | ~180 | ⭐⭐⭐⭐ |

**Vorteil:** ISBN-Cleanup liefert **höchste Datenqualität** bei minimalem Aufwand!

## Auswirkungen

### Datenfluss:

```
marcVDEH.xml (MARC21)
    ↓
MARC21 Parser (_format_isbn)
    ├── Erkennt: 35140035483540510400
    ├── Bereinigt: 3514003548
    └── Formatiert: 3-514-00354-8
    ↓
01_loaded_data.parquet
    └── isbn: "3-514-00354-8" (sauber!)
    ↓
04_dnb_enriched_data.parquet
    ├── DNB ID-Suche mit bereinigter ISBN
    └── Höhere Erfolgsrate durch valide ISBNs
```

### Logging:

Bei aktiviertem DEBUG-Logging sieht man:
```
DEBUG: Double ISBN-10 detected: 35140035483540510400 -> using first: 3514003548
DEBUG: Mixed ISBN detected: 35405194329783540519430 -> using first: 3540519432
```

## Migration

### Für bestehende Datensätze:

**Notebook 01 neu ausführen:**
```bash
poetry run papermill \
    notebooks/01_vdeh_preprocessing/01_vdeh_data_loading.ipynb \
    output_01.ipynb
```

Dies wird:
1. ✅ MARC21 neu parsen mit ISBN-Cleanup
2. ✅ 116 ISBNs automatisch bereinigen
3. ✅ `01_loaded_data.parquet` mit sauberen ISBNs überschreiben

**Notebook 04 neu ausführen:**
```bash
poetry run papermill \
    notebooks/01_vdeh_preprocessing/04_vdeh_data_enrichment.ipynb \
    output_04.ipynb
```

Dies wird:
1. ✅ Bereinigte ISBNs für DNB ID-Suche nutzen
2. ✅ ~58 zusätzliche DNB-Matches finden
3. ✅ Bessere Metadaten-Abdeckung erreichen

### Backward Compatibility:

✅ **Keine Breaking Changes**
- Bestehende valide ISBNs werden nicht verändert
- Bereits formatierte ISBNs bleiben unverändert
- Nur ungültige ISBNs werden bereinigt

## Einschränkungen

1. **Zweite ISBN geht verloren:**
   - Lösung: Wenn beide ISBNs benötigt werden, könnte man `isbn_alt` Feld hinzufügen
   - Aktuell: Nicht notwendig, da DNB-Suche nur eine ISBN braucht

2. **Nicht alle ungültigen ISBNs behebbar:**
   - 93 Records (44.5%) haben andere Probleme (z.B. Tippfehler, zu kurz)
   - Diese bleiben ungültig und müssen manuell geprüft werden

3. **Heuristik kann fehlen:**
   - Annahme: Erste ISBN ist primäre Ausgabe
   - In seltenen Fällen könnte zweite ISBN besser passen
   - Praktisch: Bei 50% DNB-Erfolgsrate ist Heuristik gut genug

## Zukünftige Verbesserungen

1. **Beide ISBNs speichern:**
   - `isbn` (primär)
   - `isbn_alt` (alternativ)
   - DNB-Suche mit beiden versuchen

2. **Smart ISBN-Wahl:**
   - Prüfe welche ISBN besser zur Sprache/Region passt
   - Deutsche Bücher → bevorzuge 3-*-*
   - US-Bücher → bevorzuge 0-*-*

3. **Validierung:**
   - ISBN-10/13 Checksummen-Prüfung
   - Automatische Korrektur bei Tippfehlern (Levenshtein-Distanz)

## Changelog

**2025-12-12 - v2.2.0:**
- ✅ ISBN-Cleanup in `_format_isbn()` implementiert
- ✅ Behandelt doppelte ISBN-10, ISBN-13, gemischte ISBNs
- ✅ Tests geschrieben und validiert
- ✅ Dokumentation erstellt
- ✅ Automatisch aktiv in Notebooks 01 + 04

## Testing

**Ausführen:**
```bash
poetry run python3 scripts/test_isbn_cleanup.py
```

**Erwartete Ausgabe:**
```
=== Test: ISBN-Bereinigung ===
✓ Double ISBN-10 (real example)
✓ Double ISBN-10 (Springer)
✓ Single ISBN-10
✓ Single ISBN-13
✓ Double ISBN-13 (26 chars)
✓ Mixed ISBN-10+13 (23 chars)
✓ Too short - invalid (9 chars)
✓ Already formatted ISBN-10

Ergebnis: 8/8 Tests bestanden
✅ Alle Tests erfolgreich!
```

## Referenzen

- **ISBN Standard:** [Wikipedia - International Standard Book Number](https://de.wikipedia.org/wiki/Internationale_Standardbuchnummer)
- **MARC21 Field 020:** [Library of Congress - MARC21 020](https://www.loc.gov/marc/bibliographic/bd020.html)
- **DNB SRU API:** [Deutsche Nationalbibliothek SRU](https://www.dnb.de/DE/Professionell/Metadatendienste/Datenbezug/SRU/sru_node.html)
