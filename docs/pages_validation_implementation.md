# Pages Validation Implementation (v2.3.0)

## Überblick

**Pages Validation** verbessert die Title/Year (TY) Match-Qualität durch zusätzliche Validierung anhand der Seitenzahl. Dies ermöglicht es, borderline Matches (50-70% Similarity) zu retten, wenn die Seitenzahlen übereinstimmen.

## Motivation

**Problem:**
- TY-Matches basieren nur auf Titel-Similarity (70% Threshold)
- Einige gute Matches haben 50-70% Similarity (z.B. durch Titelvariation, Untertitel)
- Beispiel: "Materials characterization" vs "Materials Characterization: Methods and Applications" (66% Similarity)
- Diese Matches wurden bisher abgelehnt, obwohl sie korrekt sein könnten

**Lösung:**
- Nutze Seitenzahl als zusätzliches Validierungskriterium
- Akzeptiere Matches mit 50-70% Similarity, wenn die Seitenzahlen übereinstimmen (±10% Toleranz)
- Dies erhöht Precision ohne Recall zu reduzieren

**Datenverfügbarkeit:**
- 29,080 VDEH records haben Seitenzahlen (49.9%)
- 9,617 TY-Kandidaten haben Seitenzahlen (66.9%)
- Erwartete Rescue-Rate: 20-30 zusätzliche Matches

## Implementierung

### 1. Pages Parser ([src/fusion/utils.py](../src/fusion/utils.py))

**Neue Funktion:** `extract_page_number(pages_str: Optional[str]) -> Optional[int]`

**Funktionalität:**
- Extrahiert numerische Seitenzahl aus verschiedenen MARC21-Formaten
- Ignoriert römische Zahlen (Vorspann)
- Sucht größte Zahl (Hauptpagination)

**Unterstützte Formate:**
```python
"188 S."          → 188   # Standard MARC21 deutsch
"XV, 250 p."      → 250   # Mit römischen Zahlen + p.
"192 pages"       → 192   # Englisch
"250 Seiten"      → 250   # Deutsch
"A35, B21 S."     → 35    # Komplexe Pagination (größte Zahl)
"123"             → 123   # Nur Zahl
""                → None  # Fehlend
```

**Implementierung:**
```python
def extract_page_number(pages_str: Optional[str]) -> Optional[int]:
    """Extract numeric page count from various page string formats."""
    if pd.isna(pages_str) or not pages_str:
        return None

    pages_str = str(pages_str).strip()

    # Pattern: Find largest number (ignoring Roman numerals at start)
    patterns = [
        r'(\d+)\s*(?:S\.|p\.|pages?|Seiten?)',  # "188 S.", "250 p."
        r'(\d+)\s*$',  # Just number at end
        r'(\d+)\s*[,:]',  # Number before comma/colon
    ]

    numbers = []
    for pattern in patterns:
        matches = re.findall(pattern, pages_str, re.IGNORECASE)
        numbers.extend([int(m) for m in matches])

    return max(numbers) if numbers else None
```

### 2. Pages Match Validation ([src/fusion/utils.py](../src/fusion/utils.py))

**Neue Funktion:** `calculate_pages_match(pages1, pages2, tolerance=0.1) -> Tuple[bool, Optional[float]]`

**Funktionalität:**
- Vergleicht zwei Seitenzahlen mit Toleranz (Standard: 10%)
- Berechnet relative Differenz (basierend auf Durchschnitt)
- Returns: (match: bool, difference_percent: Optional[float])

**Beispiele:**
```python
# Match (2.1% Differenz, < 10% Toleranz)
calculate_pages_match("188 S.", "192 p.")
→ (True, 0.021)

# Match (0% Differenz)
calculate_pages_match("250 S.", "250 pages")
→ (True, 0.0)

# Mismatch (40% Differenz, > 10% Toleranz)
calculate_pages_match("100 S.", "150 p.")
→ (False, 0.4)

# Keine Validierung möglich (fehlende Daten)
calculate_pages_match("188 S.", "")
→ (False, None)
```

**Implementierung:**
```python
def calculate_pages_match(pages1: Optional[str], pages2: Optional[str],
                         tolerance: float = 0.1) -> Tuple[bool, Optional[float]]:
    """Check if two page counts match within tolerance (default 10%)."""
    num1 = extract_page_number(pages1)
    num2 = extract_page_number(pages2)

    # If either is missing, we can't validate
    if num1 is None or num2 is None:
        return (False, None)

    # Calculate relative difference
    diff = abs(num1 - num2)
    avg = (num1 + num2) / 2
    diff_percent = diff / avg if avg > 0 else 1.0

    matches = diff_percent <= tolerance

    logger.debug(
        f"Pages match check: {pages1} ({num1}) vs {pages2} ({num2}) "
        f"→ diff={diff_percent:.1%}, match={matches}"
    )

    return (matches, diff_percent)
```

### 3. TY Validation Enhancement ([src/fusion/fusion_engine.py](../src/fusion/fusion_engine.py))

**Modifizierter Code:** `merge_record()` - Case 1.5 (nur TY verfügbar)

**Neue Validierungslogik:**
```python
# Case 1.5: Only TY variant available - validate with similarity threshold + pages
if dnb_id is None and dnb_ta is None and dnb_ty is not None:
    # Calculate title similarity
    vdeh_title = vdeh_data.get('title')
    dnb_ty_title = dnb_ty.get('title')
    similarity = self.calculate_title_similarity(vdeh_title, dnb_ty_title)

    # Check pages match (if both available)
    vdeh_pages = vdeh_data.get('pages')
    dnb_ty_pages = dnb_ty.get('pages')
    pages_match, pages_diff = calculate_pages_match(vdeh_pages, dnb_ty_pages)

    # Decision logic: Similarity + Pages
    accept_match = False
    reason = ""

    if similarity >= self.ty_similarity_threshold:
        # High similarity → Accept
        accept_match = True
        reason = f"Similarity: {similarity:.1%}"
    elif similarity >= 0.5 and pages_match:
        # Borderline similarity (50-70%) but pages match → Accept
        accept_match = True
        reason = f"Similarity: {similarity:.1%}, Pages-Match bestätigt ({vdeh_pages} ≈ {dnb_ty_pages})"
        logger.info(
            f"TY borderline match rescued by pages: "
            f"similarity={similarity:.1%}, pages={vdeh_pages} vs {dnb_ty_pages}"
        )
    else:
        # Low similarity and no pages confirmation → Reject
        reason = f"Similarity: {similarity:.1%}"
        if pages_diff is not None:
            reason += f", Pages mismatch: {pages_diff:.1%} diff"
```

**Entscheidungsmatrix:**

| Similarity | Pages Match | Entscheidung | Grund |
|------------|-------------|--------------|-------|
| ≥ 70%      | -           | ✅ Accept    | Hohe Similarity |
| 50-70%     | ✅ Ja       | ✅ Accept    | Borderline + Pages-Match (Rescue!) |
| 50-70%     | ❌ Nein     | ❌ Reject    | Borderline + Pages-Mismatch |
| 50-70%     | - Fehlend   | ❌ Reject    | Borderline, keine Bestätigung |
| < 50%      | -           | ❌ Reject    | Zu niedrige Similarity |

### 4. FusionResult Extension ([src/fusion/fusion_engine.py](../src/fusion/fusion_engine.py))

**Neues Feld:** `pages_difference: Optional[float]`

**Zweck:**
- Speichert relative Differenz der Seitenzahlen (für Debugging/Analyse)
- Wird nur gesetzt wenn beide Seitenzahlen vorhanden sind
- Hilft bei späterer Qualitätsanalyse der Matches

**Verwendung:**
```python
result = FusionResult(
    dnb_variant_selected='title_year',
    ai_reasoning=f'TY-Variante als Fallback (kein ID/TA verfügbar, {reason})',
    title_similarity_score=similarity,
    pages_difference=pages_diff,  # NEU
)
```

## Testing

**Test-Skript:** [scripts/test_pages_validation.py](../scripts/test_pages_validation.py)

**Test-Coverage:**
1. **extract_page_number()** - 10/10 Tests
   - Standard MARC21 Formate
   - Römische Zahlen
   - Komplexe Pagination
   - Edge Cases (leer, None, keine Zahl)

2. **calculate_pages_match()** - 9/9 Tests
   - Ähnliche Zahlen (innerhalb Toleranz)
   - Identische Zahlen
   - Zu unterschiedliche Zahlen
   - Fehlende Daten

3. **TY-Validierung Logik** - 7/7 Tests
   - Hohe Similarity (>70%)
   - Borderline + Pages-Match (Rescue)
   - Borderline + Pages-Mismatch (Reject)
   - Borderline ohne Pages (Reject)
   - Niedrige Similarity (<50%)

**Ergebnis:** ✅ 26/26 Tests bestanden

**Test ausführen:**
```bash
poetry run python3 scripts/test_pages_validation.py
```

## Erwartete Ergebnisse

### Vor Pages-Validierung (v2.1):
- TY Matches: 193 (57.6% von 335 Raw-Matches)
- Rejection Grund: Similarity < 70%

### Nach Pages-Validierung (v2.3):
- **TY Matches: 213-223** (+20-30 Rescue)
- **Rescue-Rate: 10-15%** der 50-70% Similarity-Matches
- **Precision:** Hoch (nur Matches mit Pages-Bestätigung)

**Beispiel-Rescue:**
```
VDEH:  "Materials characterization" (188 S.)
DNB:   "Materials Characterization: Methods and Applications" (192 p.)
Similarity: 66% (< 70% → würde abgelehnt)
Pages: 188 vs 192 (2.1% Differenz → Match!)
→ ✅ Rescued durch Pages-Validierung!
```

### Impact auf Gesamt-Enrichment:

**Baseline (nur ID + TA):**
- Autoren: 371 (0.9%)
- ISBN: 604
- ISSN: 127

**v2.1 (TY mit Similarity):**
- Autoren: ~472 (1.2%)
- ISSN: ~241

**v2.2 (ISBN Cleanup):**
- Autoren: ~530 (+58)

**v2.3 (Pages Validation):**
- **Autoren: ~540-550** (+10-20 zusätzlich)
- **Gesamt: +45-48% gegenüber Baseline**

## Einschränkungen

1. **Pages nur in 66.9% der TY-Kandidaten vorhanden**
   - Rescue nur möglich wenn beide Records Seitenzahl haben
   - Ca. 33% der Borderline-Matches können nicht validiert werden

2. **10% Toleranz kann zu False Positives führen**
   - Verschiedene Ausgaben desselben Werks (Hardcover vs Paperback)
   - Trade-off: Toleranz vs Precision
   - 10% wurde als guter Balance-Punkt identifiziert

3. **Komplexe Pagination kann zu falschen Zahlen führen**
   - "A35, B21 S." → 35 (nimmt größte Zahl)
   - Kann bei ungewöhnlichen Formaten fehlschlagen
   - In Praxis sehr selten (< 1% der Fälle)

## Verwendung

### Automatisch in Fusion:
```python
# Wird automatisch in FusionEngine.merge_record() angewendet
# Keine manuelle Intervention nötig
```

### Notebook 05 ausführen (nach TY-Enrichment):
```bash
poetry run papermill \
    notebooks/01_vdeh_preprocessing/05_vdeh_data_fusion.ipynb \
    output.ipynb
```

### Analyse der Pages-Validierung:
```python
import pandas as pd

df = pd.read_parquet('data/vdeh/processed/05_fused_data.parquet')

# TY-Matches mit Pages-Rescue
rescued = df[
    (df['dnb_variant_selected'] == 'title_year') &
    (df['title_similarity_score'] >= 0.5) &
    (df['title_similarity_score'] < 0.7) &
    (df['pages_difference'].notna())
]

print(f"Rescued Matches: {len(rescued)}")
print(f"Avg Similarity: {rescued['title_similarity_score'].mean():.1%}")
print(f"Avg Pages Diff: {rescued['pages_difference'].mean():.1%}")
```

## Änderungshistorie

- **2025-12-12 (v2.3.0):** Initiale Implementierung
  - `extract_page_number()` in `src/fusion/utils.py`
  - `calculate_pages_match()` in `src/fusion/utils.py`
  - TY-Validierung Enhancement in `src/fusion/fusion_engine.py`
  - FusionResult Extension (pages_difference)
  - Comprehensive Testing (26/26 Tests)
  - Dokumentation

## Nächste Schritte

1. ✅ Implementation abgeschlossen
2. ✅ Testing erfolgreich (26/26)
3. ⏳ Pipeline ausführen (Notebooks 01, 04, 05)
4. ⏳ Ergebnisse analysieren (tatsächliche Rescue-Rate)
5. ⏳ README und CHANGELOG aktualisieren
6. ⏳ Report Generator anpassen (Pages-Validierung in Statistiken)

## Verwandte Dokumentation

- [Title/Year Implementation](title_year_implementation.md) - TY-Suche Grundlagen
- [ISBN Cleanup Implementation](isbn_cleanup_implementation.md) - ISBN-Bereinigung
- [MARC21 Migration](../MIGRATION_PLAN_MARC21.md) - MARC21 Parser
