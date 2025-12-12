# Report Generator - Update Plan für MARC21 & Language

## Fehlende Inhalte

### 1. MARC21 Migration (Sektion 2.1 NEU)

**Ergänzen nach "2. Daten-Pipeline":**

```markdown
### 2.1 Datenquelle & Migration

**Aktuelle Datenquelle:** MARC21 XML (`marcVDEH.xml`)

| Metrik | MAB (Alt) | MARC21 (Neu) | Verbesserung |
|--------|-----------|--------------|--------------|
| Records | 58,760 | 58,305 | -455 (-0.8%) |
| Titel-Vollständigkeit | 69.5% | 99.9% | +17,412 Records |
| Seitenzahlen | 0% | 49.9% | +29,080 Records |
| Autoren | 28.9% | 32.1% | +1,724 Records |

**Migration:** 2025-12-09 - Umstellung von MAB auf internationales MARC21-Format

- Bessere Metadaten-Struktur
- Standardisierte Feldmappings
- Höhere Datenqualität für DNB-Abgleich
```

### 2. Language Analysis (Sektion 5.2 NEU)

**Ergänzen nach "5.1 Aktuelle Vollständigkeit":**

```markdown
### 5.2 Sprach-Abdeckung (Dual-Source)

Die Sprachinformation stammt aus zwei Quellen und wird intelligent kombiniert:

| Quelle | Abdeckung | Format | Genauigkeit |
|--------|-----------|--------|-------------|
| MARC21 Katalog | XX,XXX (XX.X%) | ISO 639-2 (ger, eng, fre) | 100% |
| langdetect (Titel) | XX,XXX (XX.X%) | ISO 639-1 (de, en, fr) | ~85% |
| **Final (kombiniert)** | **XX,XXX (XX.X%)** | **Gemischt** | **>95%** |

**Top 5 Sprachen:**

| Sprache | Anzahl | Anteil |
|---------|--------|--------|
| [aus Daten] | X,XXX | XX.X% |
| ... | ... | ... |

**Fusion-Strategie:**
1. MARC21-Sprache bevorzugt (wenn vorhanden)
2. Fallback zu langdetect (wenn MARC21 fehlt)
3. Beide verfügbar: XX,XXX Records (für Qualitätsprüfung)

![Language Coverage](figures/language_coverage.png)
```

### 3. Pipeline-Diagramm aktualisieren

**Alt:**
```
VDEH XML (58.760 Records)
```

**Neu:**
```
marcVDEH.xml (MARC21, 58,305 Records)
    |
    v
[01] MARC21 Parsing & Language Extraction
    |
    v
[02] Preprocessing & Validation
    |
    v
[03] Language Detection (Dual-Source: MARC21 + langdetect)
    |
    v
[04] DNB Enrichment (ISBN/ISSN + Titel/Autor)
    |
    v
[05] KI-Fusion (Ollama LLM) + Language Fusion
    |
    v
Finaler Datensatz (mit language_final)
```

### 4. Neue Visualisierungen

**Zu erstellen:**

1. **language_coverage.png**
   - Balkendiagramm: MARC21 vs langdetect vs Final
   - Zeigt Dual-Source Strategie visuell

2. **marc21_improvements.png**
   - Vorher/Nachher-Vergleich MAB vs MARC21
   - Titel, Autoren, Seitenzahlen

3. **data_source_quality.png**
   - Vergleich Vollständigkeit: MAB vs CSV vs MARC21

## Implementierung

### Schritt 1: Statistiken erweitern (Cell "calculate-stats")

```python
# Language-Statistiken hinzufügen
if 'language_final' in df_fused.columns:
    stats['language'] = {
        'marc21_count': (df_fused['language_source'] == 'marc21').sum(),
        'langdetect_count': (df_fused['language_source'] == 'langdetect').sum(),
        'total_with_lang': df_fused['language_final'].notna().sum(),
        'coverage_pct': df_fused['language_final'].notna().sum() / len(df_fused) * 100,
        'top_languages': df_fused['language_final'].value_counts().head(5).to_dict()
    }

# MARC21 Datenquelle aus Config/Metadata
stats['data_source'] = {
    'format': 'MARC21',
    'file': 'marcVDEH.xml',
    'records': len(df_fused)
}
```

### Schritt 2: Visualisierungen hinzufügen (Cell "create-visualizations")

```python
# Language Coverage Visualization
if 'language' in stats:
    fig, ax = plt.subplots(figsize=(10, 6))

    categories = ['MARC21\n(Katalog)', 'langdetect\n(Titel)', 'Final\n(kombiniert)']
    values = [
        stats['language']['marc21_count'],
        stats['language']['langdetect_count'],
        stats['language']['total_with_lang']
    ]
    percentages = [v / len(df_fused) * 100 for v in values]

    colors = ['#3498db', '#9b59b6', '#27ae60']
    bars = ax.bar(categories, values, color=colors, alpha=0.8)

    ax.set_ylabel('Anzahl Records')
    ax.set_title('Sprach-Abdeckung: Dual-Source Strategie')

    for bar, val, pct in zip(bars, values, percentages):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                f'{val:,}\n({pct:.1f}%)', ha='center', va='bottom', fontsize=10)

    plt.tight_layout()
    plt.savefig(figures_dir / 'language_coverage.png', dpi=150)
    plt.show()
    print(f"  Gespeichert: language_coverage.png")
```

### Schritt 3: Report-Text erweitern (Cell "generate-report")

Füge die oben genannten Markdown-Sektionen 2.1 und 5.2 ein.

## Priorität

**Hoch:**
- ✅ MARC21-Datenquelle erwähnen (schnelle Textänderung)
- ✅ Language-Statistiken hinzufügen (wenn Daten vorhanden)

**Mittel:**
- 📊 Language Coverage Visualisierung
- 📊 MARC21 Improvements Visualisierung

**Niedrig:**
- 📄 Detaillierte MARC21-Feldmapping-Tabelle
- 📊 Historischer Vergleich mit alten Reports

## Test-Checklist

Nach Update prüfen:

- [ ] Report läuft ohne Fehler durch
- [ ] Language-Statistiken korrekt (wenn `language_final` vorhanden)
- [ ] Graceful handling wenn Language-Spalten fehlen
- [ ] MARC21 wird als Datenquelle genannt
- [ ] Pipeline-Diagramm aktualisiert
- [ ] Neue Visualisierungen werden erstellt
- [ ] Export zu PDF funktioniert noch
