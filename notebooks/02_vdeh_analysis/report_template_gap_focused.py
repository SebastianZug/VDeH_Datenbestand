# Gap-focused Report Template
# This will be integrated into the notebook

def generate_gap_focused_report(stats, config, report_date):
    """Generate a report focused on gaps in MARC21 and how the pipeline fills them."""

    total = stats.get('total_records', 0)
    data_source = stats.get('data_source', {})
    language_stats = stats.get('language', {})
    original_gaps = stats.get('original_gaps', {})
    gaps_filled = stats.get('gaps_filled', {})
    quality = stats.get('quality', {})
    improvements = stats.get('improvements', {})

    # Calculate gap closure rates
    isbn_gap_closure = (gaps_filled.get('isbn', 0) / original_gaps.get('isbn_missing', 1) * 100) if original_gaps.get('isbn_missing', 0) > 0 else 0
    language_gap_closure = (language_stats.get('gap_filled', 0) / original_gaps.get('language_missing', 1) * 100) if original_gaps.get('language_missing', 0) > 0 else 0

    report = f"""# VDEH Bibliothek Datenanreicherung - Projektbericht

**Fokus:** Lücken-Analyse und Pipeline-Mehrwert

**Erstellt:** {report_date}
**Projekt:** {config.get('project.name')}
**Version:** {config.get('project.version')}

---

## 1. Executive Summary: Was die Pipeline leistet

### Problem: Lücken im MARC21-Datensatz

Der MARC21-Datensatz ({data_source.get('file', 'N/A')}) enth\u00e4lt {total:,} Records, aber es fehlen kritische Metadaten:

| Feld | Fehlend in MARC21 | Prozent |
|------|-------------------|---------|
| **ISBN** | **{original_gaps.get('isbn_missing', 0):,}** | **{original_gaps.get('isbn_missing', 0)/total*100:.1f}%** |
| **ISSN** | {original_gaps.get('issn_missing', 0):,} | {original_gaps.get('issn_missing', 0)/total*100:.1f}% |
| **Sprache** | {original_gaps.get('language_missing', 0):,} | {original_gaps.get('language_missing', 0)/total*100:.1f}% |
| **Seitenzahlen** | {original_gaps.get('pages_missing', 0):,} | {original_gaps.get('pages_missing', 0)/total*100:.1f}% |
| Autoren | {original_gaps.get('authors_missing', 0):,} | {original_gaps.get('authors_missing', 0)/total*100:.1f}% |
| Jahr | {original_gaps.get('year_missing', 0):,} | {original_gaps.get('year_missing', 0)/total*100:.1f}% |
| Publisher | {original_gaps.get('publisher_missing', 0):,} | {original_gaps.get('publisher_missing', 0)/total*100:.1f}% |

### Lösung: Pipeline-Anreicherung

Die Pipeline f\u00fcllt diese L\u00fccken durch DNB-Abgleich und KI-Fusion:

| Feld | Neu gef\u00fcllt | Schlie\u00dfungsrate |
|------|------------|---------------------|
| **ISBN** | **+{gaps_filled.get('isbn', 0):,}** | **{isbn_gap_closure:.1f}%** |
| **ISSN** | **+{gaps_filled.get('issn', 0):,}** | {gaps_filled.get('issn', 0)/original_gaps.get('issn_missing', 1)*100 if original_gaps.get('issn_missing', 0) > 0 else 0:.1f}% |
| **Sprache** | **+{language_stats.get('gap_filled', 0):,}** | **{language_gap_closure:.1f}%** |
| **Seitenzahlen** | **+{gaps_filled.get('pages', 0):,}** | {gaps_filled.get('pages', 0)/original_gaps.get('pages_missing', 1)*100 if original_gaps.get('pages_missing', 0) > 0 else 0:.1f}% |
| Autoren | +{gaps_filled.get('authors', 0):,} | {gaps_filled.get('authors', 0)/original_gaps.get('authors_missing', 1)*100 if original_gaps.get('authors_missing', 0) > 0 else 0:.1f}% |
| Jahr | +{gaps_filled.get('year', 0):,} | {gaps_filled.get('year', 0)/original_gaps.get('year_missing', 1)*100 if original_gaps.get('year_missing', 0) > 0 else 0:.1f}% |
| Publisher | +{gaps_filled.get('publisher', 0):,} | {gaps_filled.get('publisher', 0)/original_gaps.get('publisher_missing', 1)*100 if original_gaps.get('publisher_missing', 0) > 0 else 0:.1f}% |

### Hauptmehrwert

1. **{gaps_filled.get('isbn', 0):,} neue ISBNs** ({isbn_gap_closure:.1f}% der fehlenden ISBNs) - essentiell f\u00fcr Katalogisierung
2. **{language_stats.get('gap_filled', 0):,} Sprachinformationen** ({language_gap_closure:.1f}% der fehlenden) - von {original_gaps.get('language_missing', 0)/total*100:.1f}% auf {language_stats.get('coverage_pct', 0):.1f}% Abdeckung
3. **{quality.get('rejected_matches', 0):,} falsche DNB-Matches erkannt** - verhindert Datenverschlechterung
4. **{quality.get('dnb_preferred', 0):,} Records verbessert** - h\u00f6here Datenqualit\u00e4t

---

## 2. Detaillierte Gap-Analyse

### 2.1 ISBN-L\u00fccke: {original_gaps.get('isbn_missing', 0):,} fehlende ISBNs

**Ausgangslage:**
- MARC21 enth\u00e4lt nur {total - original_gaps.get('isbn_missing', 0):,} ISBNs ({(total - original_gaps.get('isbn_missing', 0))/total*100:.1f}%)
- **{original_gaps.get('isbn_missing', 0):,} Records ohne ISBN** ({original_gaps.get('isbn_missing', 0)/total*100:.1f}%)

**Pipeline-L\u00f6sung:**
- DNB-Abfrage \u00fcber ISBN/ISSN: {stats.get('isbn_gain', 0):,} neue ISBNs
- DNB-Abfrage \u00fcber Titel/Autor: {stats.get('isbn_gain_ta', 0):,} neue ISBNs
- **Gesamt: +{gaps_filled.get('isbn', 0):,} ISBNs** ({isbn_gap_closure:.1f}% der L\u00fccke geschlossen)

**Detaillierung:**
- Komplett neue ISBNs: {stats.get('isbn_detailed', {}).get('new', 0):,}
- Alternative Ausgaben: {stats.get('isbn_detailed', {}).get('alternative', 0):,}

**Verbleibende L\u00fccke:** {original_gaps.get('isbn_missing', 0) - gaps_filled.get('isbn', 0):,} Records

![Identifier-Gewinn](figures/identifier_gain.png)

### 2.2 Sprach-L\u00fccke: {original_gaps.get('language_missing', 0):,} fehlende Sprachinformationen

**Ausgangslage:**
- MARC21 enth\u00e4lt nur {total - original_gaps.get('language_missing', 0):,} Sprachcodes ({(total - original_gaps.get('language_missing', 0))/total*100:.1f}%)
- **{original_gaps.get('language_missing', 0):,} Records ohne Sprache** ({original_gaps.get('language_missing', 0)/total*100:.1f}%)

**Pipeline-L\u00f6sung (Dual-Source):**
1. MARC21-Katalogdaten: {language_stats.get('marc21_count', 0):,} Records (100% genau)
2. langdetect (Titel-Analyse): {language_stats.get('langdetect_count', 0):,} zus\u00e4tzliche Records
3. **Kombiniert: {language_stats.get('total_with_lang', 0):,} Records** ({language_stats.get('coverage_pct', 0):.1f}% Abdeckung)

**L\u00fccken-Schlie\u00dfung:** +{language_stats.get('gap_filled', 0):,} Records ({language_gap_closure:.1f}%)

**Verbleibende L\u00fccke:** {total - language_stats.get('total_with_lang', 0):,} Records ({(total - language_stats.get('total_with_lang', 0))/total*100:.1f}%)

![Language Coverage](figures/language_coverage.png)

### 2.3 Seitenzahlen-L\u00fccke: {original_gaps.get('pages_missing', 0):,} fehlende Seitenzahlen

**Ausgangslage:**
- MARC21 enth\u00e4lt nur {total - original_gaps.get('pages_missing', 0):,} Seitenzahlen ({(total - original_gaps.get('pages_missing', 0))/total*100:.1f}%)
- **{original_gaps.get('pages_missing', 0):,} Records ohne Seitenzahl** ({original_gaps.get('pages_missing', 0)/total*100:.1f}%)

**Pipeline-L\u00f6sung:**
- MARC21 Field 300: {total - original_gaps.get('pages_missing', 0):,} Records (Original)
- DNB-Anreicherung (alle drei Varianten): +{gaps_filled.get('pages', 0):,} neue Seitenzahlen
- **Pages-Validierung**: Seitenzahlen als zus\u00e4tzliches Validierungskriterium (\u00b110% Toleranz)

**L\u00fccken-Schlie\u00dfung:** +{gaps_filled.get('pages', 0):,} Records ({gaps_filled.get('pages', 0)/original_gaps.get('pages_missing', 1)*100 if original_gaps.get('pages_missing', 0) > 0 else 0:.1f}%)

**Verbleibende L\u00fccke:** {original_gaps.get('pages_missing', 0) - gaps_filled.get('pages', 0):,} Records ({(original_gaps.get('pages_missing', 0) - gaps_filled.get('pages', 0))/total*100:.1f}%)

**Zusatzfunktion:** Pages werden auch zur **TY-Match-Validierung** verwendet - Borderline-Matches (50-70% Similarity) werden akzeptiert wenn Seitenzahlen \u00fcbereinstimmen.

### 2.4 Weitere L\u00fccken

| Feld | MARC21-L\u00fccke | Gef\u00fcllt | Verbleibend |
|------|------------|---------|-------------|
| ISSN | {original_gaps.get('issn_missing', 0):,} | +{gaps_filled.get('issn', 0):,} | {original_gaps.get('issn_missing', 0) - gaps_filled.get('issn', 0):,} |
| Seitenzahlen | {original_gaps.get('pages_missing', 0):,} | +{gaps_filled.get('pages', 0):,} | {original_gaps.get('pages_missing', 0) - gaps_filled.get('pages', 0):,} |
| Autoren | {original_gaps.get('authors_missing', 0):,} | +{gaps_filled.get('authors', 0):,} | {original_gaps.get('authors_missing', 0) - gaps_filled.get('authors', 0):,} |
| Jahr | {original_gaps.get('year_missing', 0):,} | +{gaps_filled.get('year', 0):,} | {original_gaps.get('year_missing', 0) - gaps_filled.get('year', 0):,} |
| Publisher | {original_gaps.get('publisher_missing', 0):,} | +{gaps_filled.get('publisher', 0):,} | {original_gaps.get('publisher_missing', 0) - gaps_filled.get('publisher', 0):,} |

---

## 3. Qualit\u00e4tssicherung: Warum KI-Fusion kritisch ist

### Das Problem: Falsche DNB-Matches

Von {stats.get('fusion_count', 0):,} DNB-Matches waren **{quality.get('rejected_matches', 0):,} falsch** ({quality.get('rejected_matches', 0)/stats.get('fusion_count', 1)*100:.1f}%).

**Ohne KI-Fusion w\u00fcrden Sie {quality.get('rejected_matches', 0):,} fehlerhafte Daten \u00fcbernehmen!**

### KI-Fusion Entscheidungen

| Entscheidung | Anzahl | Anteil | Bedeutung |
|--------------|--------|--------|-----------|
| **Validiert** | {quality.get('validated', 0):,} | {quality.get('validated', 0) / stats.get('fusion_count', 1) * 100:.1f}% | MARC21 war korrekt |
| **DNB gew\u00e4hlt** | {quality.get('dnb_preferred', 0):,} | {quality.get('dnb_preferred', 0) / stats.get('fusion_count', 1) * 100:.1f}% | DNB lieferte bessere Daten |
| **Abgelehnt** | {quality.get('rejected_matches', 0):,} | {quality.get('rejected_matches', 0) / stats.get('fusion_count', 1) * 100:.1f}% | Falscher Match verhindert |

![Qualit\u00e4tsentscheidungen](figures/quality_decisions.png)

---

## 4. ROI-Analyse: Lohnt sich die Pipeline?

### Aufwand
- Setup: **Bereits erledigt**
- Ausf\u00fchrung: ~10-12 Stunden (einmalig)
- Wartung: Minimal (bei Datenaktualisierung)

### Nutzen

| Kriterium | Wert | Kommentar |
|-----------|------|-----------|
| **ISBN-Gewinn** | +{gaps_filled.get('isbn', 0):,} | Unverzichtbar f\u00fcr Katalogisierung |
| **Sprach-Abdeckung** | {language_stats.get('coverage_pct', 0):.1f}% | Von {(total - original_gaps.get('language_missing', 0))/total*100:.1f}% auf {language_stats.get('coverage_pct', 0):.1f}% |
| **Fehler verhindert** | {quality.get('rejected_matches', 0):,} | Datenverschlechterung vermieden |
| **Records verbessert** | {quality.get('dnb_preferred', 0):,} | H\u00f6here Qualit\u00e4t |

### Empfehlung

**Die Pipeline lohnt sich**, weil:
1. **{isbn_gap_closure:.1f}% der ISBN-L\u00fccke** wird geschlossen
2. **{language_gap_closure:.1f}% der Sprach-L\u00fccke** wird geschlossen
3. **{quality.get('rejected_matches', 0):,} Fehler** werden verhindert
4. Setup ist fertig, nur Ausf\u00fchrung n\u00f6tig

---

## 5. Technische Details

### 5.1 Pipeline-Ablauf

```
marcVDEH.xml (MARC21, {total:,} Records)
    |
    v
[01] MARC21 Parsing & Language Extraction
    |
    v
[02] Preprocessing & Validation
    |
    v
[03] Language Detection (Dual-Source)
    |
    v
[04] DNB Enrichment (ISBN/ISSN + Titel/Autor)
    |
    v
[05] KI-Fusion (Ollama LLM) + L\u00fccken-F\u00fcllung
    |
    v
Finaler Datensatz (L\u00fccken geschlossen)
```

### 5.2 DNB Enrichment Erfolgsraten

| Methode | Erfolgsrate |
|---------|-------------|
| ISBN/ISSN-Suche | {stats.get('dnb_isbn_issn', {}).get('success_rate', 0):.1f}% |
| Titel/Autor-Suche | {stats.get('dnb_title_author', {}).get('success_rate', 0):.1f}% |

![DNB Erfolgsraten](figures/dnb_success_rates.png)

### 5.3 Konfiguration

- **Datenquelle:** {data_source.get('file', 'N/A')} ({data_source.get('format', 'N/A')})
- **DNB API Rate Limit:** 1.0s zwischen Anfragen
- **Fusion Model:** Ollama llama3.3:70b (lokal, kostenlos)
- **Fusion Timeout:** 220s

---

*Report generiert am {report_date} | Fokus: Gap-Analyse und Pipeline-Mehrwert*
"""

    return report
