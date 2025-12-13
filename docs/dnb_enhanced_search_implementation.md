# DNB Enhanced Search Strategy - Implementation Documentation

**Version:** 2.2.0
**Datum:** 13. Dezember 2025
**Status:** ✅ Implementiert und getestet

## 📋 Übersicht

Diese Dokumentation beschreibt die erweiterte DNB-Abfragestrategie, die entwickelt wurde um die Erfolgsquote bei DNB-Queries trotz unvollständiger/fehlerhafter Daten zu erhöhen.

## 🎯 Zielsetzung

**Problem:** Viele DNB-Queries scheitern aufgrund von:
- Tippfehlern in Titeln
- Umlauten/Sonderzeichen-Unterschiede
- Sehr langen Titeln (DNB-API-Limits)
- Fehlende Validierung führt zu False Positives

**Lösung:** Mehrstufige tolerantere Suchstrategie mit:
1. **Text-Normalisierung** für Umlaute/Sonderzeichen
2. **Truncated Search** für lange Titel
3. **Erweiterte Validierung** gegen False Positives

## 🔧 Implementierung

### 1. Text-Normalisierung (`_normalize_for_search`)

**Location:** `src/dnb_api.py`

**Funktion:**
```python
def _normalize_for_search(text: str) -> str:
    """Normalisiert Text für tolerantere DNB-Suche."""
```

**Was wird normalisiert:**
- **Umlaute/Akzente:** "über" → "uber", "Müller" → "Muller"
- **Sonderzeichen:** "C++" → "C", "–" → " "
- **Mehrfache Leerzeichen:** "  " → " "

**Beispiele:**
| Original | Normalisiert |
|----------|-------------|
| Über die Prüfung von Stählen | Uber die Prufung von Stahlen |
| C++ Programmierung | C Programmierung |
| Stahlbau – Grundlagen | Stahlbau Grundlagen |
| Müller, Jürgen | Muller Jurgen |

**Technische Details:**
- Unicode NFKD-Normalisierung (zerlegt Zeichen mit Akzenten)
- ASCII-Encoding (entfernt Non-ASCII-Zeichen)
- Regex-basierte Sonderzeichen-Entfernung

### 2. Erweiterte Titel/Autor-Suche

**Location:** `src/dnb_api.py::query_dnb_by_title_author()`

**Suchstrategie (8 Stufen):**

#### Gruppe 1: Mit Autor (wenn vorhanden)
1. **Original Titel (Phrase) + Autor**
   - Query: `tit="Stahlbau Grundlagen" and per=Müller`
   - Höchste Präzision

2. **Original Titel (Wörter) + Autor**
   - Query: `tit=Stahlbau Grundlagen and per=Müller`
   - Toleranter bzgl. Wortstellung

3. **Normalisierter Titel + Autor** ✨ NEU
   - Query: `tit=Uber Stahlwerkstoffe and per=Muller`
   - Für Umlaute/Sonderzeichen-Probleme

4. **Truncated Titel + Autor** ✨ NEU
   - Query: `tit=Very long title about steel construction and and per=Schmidt`
   - Für Titel >60 Zeichen

#### Gruppe 2: Nur Titel (Fallback)
5-8. Gleiche Strategien wie 1-4, aber ohne Autor

**Code-Beispiel:**
```python
result = query_dnb_by_title_author(
    title="Über die Prüfung von Stählen",
    author="Müller, Hans"
)
# Versucht automatisch:
# 1. "Über die Prüfung von Stählen" + Müller
# 2. Über die Prüfung von Stählen + Müller
# 3. Uber die Prufung von Stahlen + Muller  ← Normalisiert!
# ... (insgesamt 8 Versuche)
```

### 3. Erweiterte Titel/Jahr-Suche

**Location:** `src/dnb_api.py::query_dnb_by_title_year()`

**Suchstrategie (8 Stufen):**

#### Gruppe 1: Exaktes Jahr
1-4. Wie bei Titel/Autor, aber mit exaktem Jahr
   - Query: `tit="..." and jhr=2010`

#### Gruppe 2: Jahr-Range ±1
5-8. Gleiche Strategien mit Jahr-Toleranz
   - Query: `tit="..." and jhr>=2009 and jhr<=2011`

**Logging:**
- Erfolgreiche Matches via Normalisierung/Truncation werden geloggt:
```
INFO: TY match via normalized title: 'Uber die Prufung...'
INFO: Match via truncated title: 'Very long title about steel...'
```

### 4. Match-Validierung

**Location:** `src/fusion/fusion_engine.py::validate_dnb_match()`

**Funktion:**
```python
def validate_dnb_match(
    vdeh_data: Dict,
    dnb_data: Dict,
    min_title_similarity: float = 0.5,
    max_year_diff: int = 2,
    max_pages_diff: float = 0.2
) -> Tuple[bool, str]:
    """Validiert DNB-Match gegen False Positives."""
```

**Validierungskriterien:**

| Kriterium | Schwellwert | Aktion bei Überschreitung |
|-----------|-------------|---------------------------|
| Titel-Similarity | < 50% | ❌ Reject |
| Jahr-Differenz | > 2 Jahre | ❌ Reject |
| Seiten-Differenz | > 20% | ❌ Reject |

**Validierungslogik:**
1. **Titel-Ähnlichkeit** (SequenceMatcher)
   - Vergleicht normalisierte Titel (lowercase, stripped)
   - 100% = identisch, 0% = komplett unterschiedlich

2. **Jahr-Validierung**
   - Erlaubt ±2 Jahre Abweichung
   - Berücksichtigt Neuauflagen/Reprints

3. **Seiten-Validierung**
   - Extrahiert Zahlen aus "350 S.", "XV, 250 p.", etc.
   - Berechnet prozentuale Differenz
   - Akzeptiert bis zu 20% Abweichung

**Beispiele:**

✅ **Akzeptiert:**
```python
VDEH: {'title': 'Stahlbau Grundlagen', 'year': 2010, 'pages': '350 S.'}
DNB:  {'title': 'Stahlbau: Grundlagen', 'year': 2010, 'pages': '352 S.'}
→ Similarity: 97.4%, Jahr gleich, Pages: 0.6% diff
```

❌ **Abgelehnt (Titel zu unterschiedlich):**
```python
VDEH: {'title': 'Korrosionsschutz', 'year': 2015, 'pages': '200 S.'}
DNB:  {'title': 'Werkstoffprüfung', 'year': 2015, 'pages': '205 S.'}
→ Similarity: 25.0% (< 50% Schwellwert)
```

❌ **Abgelehnt (Jahr zu weit weg):**
```python
VDEH: {'title': 'Stahlwerkstoffe', 'year': 2010, 'pages': '300 S.'}
DNB:  {'title': 'Stahlwerkstoffe', 'year': 2015, 'pages': '305 S.'}
→ Jahr-Differenz: 5 Jahre (> 2 Jahre)
```

❌ **Abgelehnt (Seitenzahl zu unterschiedlich):**
```python
VDEH: {'title': 'Werkstoffkunde', 'year': 2012, 'pages': '500 S.'}
DNB:  {'title': 'Werkstoffkunde', 'year': 2012, 'pages': '150 S.'}
→ Pages: 107.7% diff (> 20%)
```

## 📊 Erwartete Verbesserungen

### Vorher (v2.1.0):
| Methode | Erfolgsrate |
|---------|-------------|
| ISBN/ISSN | 54.1% |
| Titel/Autor | 23.8% |
| Titel/Jahr | ~15% (geschätzt) |

### Nachher (v2.2.0 - erwartet):
| Methode | Erfolgsrate | Verbesserung |
|---------|-------------|--------------|
| ISBN/ISSN | ~60% | +5-6% |
| Titel/Autor | **35-40%** | **+11-16%** ✨ |
| Titel/Jahr | **25-30%** | **+10-15%** ✨ |

**Gesamtabdeckung:**
- **Vorher:** ~40% der Records mit DNB-Daten
- **Nachher:** **50-55%** (+10-15 Prozentpunkte)

### Gründe für Verbesserung:

1. **Normalisierung** rettet ~5-10% der Queries
   - Umlaute-Probleme: "Über" vs "Uber"
   - Sonderzeichen: "C++" vs "C Plus Plus"

2. **Truncation** rettet ~3-5% der Queries
   - Lange Titel werden korrekt abgeschnitten
   - DNB-API-Limits umgangen

3. **Validierung** verhindert ~2-5% False Positives
   - Falsche Matches werden erkannt
   - Datenqualität steigt

## 🧪 Testing

**Test-Script:** `scripts/test_dnb_enhanced_search.py`

**Ausführen:**
```bash
poetry run python scripts/test_dnb_enhanced_search.py
```

**Test-Abdeckung:**
- ✅ Normalisierung (5 Tests)
- ✅ Titel/Autor-Suche (3 Beispiele)
- ✅ Match-Validierung (4 Tests)
- ✅ Titel-Ähnlichkeit (5 Tests)

**Letzter Test-Lauf:** 13.12.2025 - **Alle Tests bestanden** ✅

## 📝 Nutzung in der Pipeline

### In Notebooks:

```python
# In 04_vdeh_data_enrichment.ipynb
from dnb_api import query_dnb_by_title_author, query_dnb_by_title_year

# Queries nutzen automatisch erweiterte Suchstrategie
result = query_dnb_by_title_author(
    title="Über Stahlwerkstoffe",
    author="Müller"
)
# → Versucht automatisch 8 verschiedene Strategien
```

### In Fusion:

```python
# In 05_vdeh_data_fusion.ipynb
from fusion.fusion_engine import FusionEngine

# Validierung wird automatisch angewendet
engine = FusionEngine(ollama_client)
result = engine.merge_record(row)
# → AI-Auswahl + automatische Validierung
```

## ⚙️ Konfiguration

### Validierungs-Schwellwerte anpassen:

```python
# In fusion_engine.py
is_valid, reason = FusionEngine.validate_dnb_match(
    vdeh_data,
    dnb_data,
    min_title_similarity=0.5,   # 50% Minimum (anpassbar)
    max_year_diff=2,            # ±2 Jahre (anpassbar)
    max_pages_diff=0.2          # 20% Maximum (anpassbar)
)
```

### TY-Similarity-Threshold:

```python
# Für Titel/Jahr-Matches
engine = FusionEngine(
    ollama_client,
    ty_similarity_threshold=0.7  # 70% Minimum (default)
)
```

## 🔍 Monitoring & Debugging

### Logging aktivieren:

```python
import logging
logging.basicConfig(level=logging.INFO)

# Zeigt erfolgreiche Normalisierungs-/Truncation-Matches:
# INFO: Match via normalized title: 'Uber die Prufung...'
# INFO: TY match via truncated title: 'Very long title...'

# Zeigt abgelehnte Validierungen:
# WARNING: DNB id match rejected by validation: Titel zu unterschiedlich
```

### Statistiken tracken:

```python
# In Fusion-Prozess
rejected_count = (df_fused['dnb_match_rejected'] == True).sum()
rejection_reasons = df_fused[df_fused['dnb_match_rejected'] == True]['rejection_reason'].value_counts()

print(f"Abgelehnte Matches: {rejected_count}")
print(f"Gründe:\n{rejection_reasons}")
```

## 📌 Best Practices

### DO ✅:
- Normalisierung für alle Text-basierten Queries nutzen
- Validierung bei allen DNB-Matches anwenden
- Logging aktivieren um erfolgreiche Rettungen zu tracken
- Test-Script bei Änderungen ausführen

### DON'T ❌:
- Validierungs-Schwellwerte zu niedrig setzen (False Positives!)
- Truncation-Länge < 40 Zeichen (zu ungenau)
- Normalisierung überspringen (Umlaute-Probleme!)

## 🚀 Weiterführende Verbesserungen

Mögliche zukünftige Erweiterungen:

1. **Fuzzy String Matching** (Levenshtein Distance)
   - Für Tippfehler-Toleranz
   - Beispiel: "Korrosion" ≈ "Korossion"

2. **Machine Learning-basierte Validierung**
   - Trainiert auf bestätigten Matches
   - Erkennt komplexere Muster

3. **Caching-Layer**
   - Speichert erfolgreiche Queries
   - Vermeidet doppelte API-Calls

4. **A/B-Testing**
   - Vergleicht alte vs. neue Strategie
   - Misst echte Verbesserung

## 📚 Referenzen

- **DNB SRU API:** https://www.dnb.de/DE/Professionell/Metadatendienste/Datenbezug/SRU/sru_node.html
- **Unicode Normalization:** https://docs.python.org/3/library/unicodedata.html
- **SequenceMatcher:** https://docs.python.org/3/library/difflib.html#difflib.SequenceMatcher

## 📄 Changelog

### v2.2.0 (2025-12-13)
- ✨ Text-Normalisierung implementiert
- ✨ Truncated Search für lange Titel
- ✨ Erweiterte Match-Validierung
- ✅ Umfassende Test-Suite
- 📝 Vollständige Dokumentation

---

**Autor:** Sebastian Zug & Claude Sonnet 4.5
**Projekt:** Dual-Source Bibliothek Bestandsvergleich
**Lizenz:** MIT
