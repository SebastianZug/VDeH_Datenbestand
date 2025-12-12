# Dual-Source Bibliothek Bestandsvergleich

**Version 2.1.0** | KI-gestützte bibliographische Datenanreicherung und -fusion

## 📋 Übersicht

Dieses Projekt führt einen systematischen Vergleich zwischen VDEH-Neuerwerbungen und dem UB TUBAF-Bestand durch. Der Fokus liegt auf der **intelligenten Datenanreicherung** über die Deutsche Nationalbibliothek (DNB) API und der **KI-gestützten Datenfusion** zur Qualitätsverbesserung bibliographischer Metadaten.

### Hauptmerkmale

- 🔍 **Triple-Strategy DNB-Anreicherung**: ISBN/ISSN + Titel/Autor + **Titel/Jahr (NEU!)**
- 🤖 **KI-gestützte Fusion**: Ollama LLM (llama3.3:70b) für intelligente Variantenauswahl
- 📊 **Datenqualitätsanalyse**: Umfassende Qualitätsmetriken und Konfliktdetektion
- 📚 **ISBN/ISSN/Pages-Extraktion**: Automatische Identifier- und Seitenzahlen-Anreicherung
- 🔄 **Inkrementelle Verarbeitung**: Progressive Speicherung und Wiederaufnahme
- 📖 **Seitenzahlen-Tracking**: Vollständige Pages-Erfassung aus MARC21 und DNB

---

## 🏗️ Projektstruktur

\`\`\`
analysis/
├── src/                          # Source Code Module
│   ├── parsers/                  # VDEH & MAB2 Parser
│   ├── fusion/                   # KI-Fusion Engine
│   │   ├── fusion_engine.py     # Haupt-Fusion-Logik
│   │   └── utils.py             # Normalisierung & Vergleich
│   ├── utils/                    # Utilities
│   │   └── notebook_utils.py    # Shared Notebook Setup
│   └── dnb_api.py               # DNB SRU API Client
│
├── notebooks/                    # Jupyter Notebooks
│   ├── 01_vdeh_preprocessing/   # VDEH Verarbeitungspipeline
│   └── 02_vdeh_analysis/        # Qualitätsanalysen
│
├── data/                        # Datenverzeichnisse
│   ├── vdeh/                    # VDEH Daten (OAI-PMH XML)
│   ├── ub_tubaf/                # UB TUBAF Daten (MAB2)
│   └── comparison/              # Vergleichsergebnisse
│
└── config.yaml                  # Zentrale Konfiguration
\`\`\`

---

## 🔄 Verarbeitungspipeline

### Gesamtübersicht

\`\`\`mermaid
flowchart TB
    Start([VDEH XML Rohdaten<br/>58,760 Records]) --> Parse

    subgraph "Phase 1: Preprocessing"
        Parse[01 XML Parsing<br/>MAB2 Feldextraktion] --> Valid
        Valid[02 ISBN/ISSN<br/>Validierung] --> Lang
        Lang[03 Sprach-<br/>erkennung]
    end

    subgraph "Phase 2: DNB Enrichment"
        Lang --> DNB_ID
        DNB_ID[04a DNB API<br/>ISBN/ISSN Suche] --> DNB_TA
        DNB_TA[04b DNB API<br/>Titel/Autor Suche<br/>4-stufige Strategie]

        DNB_ID -.->|Extrahiert| ISBN_Extract[ISBN/ISSN aus<br/>MARC21 Response]
        DNB_TA -.->|Extrahiert| ISBN_Extract
    end

    subgraph "Phase 3: KI-Fusion"
        DNB_TA --> Fusion
        ISBN_Extract --> Fusion
        Fusion[05 KI-Fusion<br/>Ollama LLM] --> Compare
        Compare{Varianten<br/>vergleichen} -->|ID-Variante| Accept1[✓ Akzeptieren]
        Compare -->|TA-Variante| Accept2[✓ Akzeptieren]
        Compare -->|Keine passend| Reject[✗ Verwerfen]

        Accept1 --> Normalize
        Accept2 --> Normalize
        Normalize[String-<br/>Normalisierung] --> Final
    end

    Final([Fusionierte Daten<br/>Angereichert + Validiert])

    style Start fill:#e1f5ff
    style Final fill:#c8e6c9
    style Fusion fill:#fff9c4
    style Compare fill:#ffe0b2
\`\`\`

---

## 📚 Detaillierte Verarbeitungsschritte

### 1. XML Parsing & Feldextraktion

**Notebook:** \`01_vdeh_xml_parsing.ipynb\`

\`\`\`mermaid
flowchart LR
    XML[VDEH XML<br/>OAI-PMH Format] --> Parser[MAB2 Parser]
    Parser --> Fields[Feldextraktion]

    Fields --> T[Titel<br/>MAB 331]
    Fields --> A[Autoren<br/>MAB 100/104]
    Fields --> Y[Jahr<br/>MAB 425]
    Fields --> P[Verlag<br/>MAB 412]
    Fields --> I[ISBN<br/>MAB 540]
    Fields --> S[ISSN<br/>MAB 542]

    T --> DF[DataFrame]
    A --> DF
    Y --> DF
    P --> DF
    I --> DF
    S --> DF
\`\`\`

**Input:** \`data/vdeh/raw/VDEH_mab_all.xml\`  
**Output:** \`data/vdeh/processed/01_parsed_data.parquet\`  
**Records:** 58,760

---

### 2. ISBN/ISSN Validierung

**Notebook:** \`02_vdeh_isbn_validation.ipynb\`

- Strukturvalidierung (10-/13-stellig für ISBN, 8-stellig für ISSN)
- Prüfziffernvalidierung
- Normalisierung (Entfernung von Bindestrichen)
- Status-Klassifikation: \`valid\`, \`invalid\`, \`missing\`

**Output:** \`data/vdeh/processed/02_isbn_validated_data.parquet\`

---

### 3. Spracherkennung

**Notebook:** \`03_vdeh_language_detection.ipynb\`

- Titelbasierte Spracherkennung (langdetect)
- Confidence Scores
- Support für 11 Sprachen (DE, EN, FR, ES, IT, NL, PT, RU, PL, CS, etc.)

**Output:** \`data/vdeh/processed/03_language_detected_data.parquet\`

---

### 4. DNB API Enrichment

**Notebook:** \`04_vdeh_data_enrichment.ipynb\`

#### 4a. ISBN/ISSN-basierte Suche

\`\`\`mermaid
flowchart TB
    Start[VDEH Record] --> HasID{Hat ISBN<br/>oder ISSN?}
    HasID -->|Ja| Query[DNB SRU API<br/>isbn=xxx ODER issn=xxx]
    HasID -->|Nein| SkipID[→ Titel/Autor-Suche]

    Query --> Parse[MARC21 Parsing]
    Parse --> Extract[Feldextraktion]

    Extract --> T[Titel 245\$a]
    Extract --> A[Autoren 100/700]
    Extract --> Y[Jahr 260/264\$c]
    Extract --> Pub[Verlag 260/264\$b]
    Extract --> ISBN[📚 ISBN 020\$a]
    Extract --> ISSN[📰 ISSN 022\$a]

    T --> Store[(DNB ID-Variante<br/>dnb_title<br/>dnb_authors<br/>dnb_year<br/>dnb_publisher<br/>dnb_isbn ✨<br/>dnb_issn ✨)]
    A --> Store
    Y --> Store
    Pub --> Store
    ISBN --> Store
    ISSN --> Store

    style ISBN fill:#fff59d
    style ISSN fill:#fff59d
    style Store fill:#c8e6c9
\`\`\`

**Erfolgsrate:** ~55% (6,232 von 11,383 Queries)

#### 4b. Titel/Autor-basierte Suche (4-stufige Strategie)

\`\`\`mermaid
flowchart TB
    Start[VDEH Record<br/>mit Titel + Autor] --> S1

    S1[Strategie 1:<br/>tit="Exact Title" AND per=Author]
    S1 -->|Gefunden| Extract
    S1 -->|Nicht gefunden| S2

    S2[Strategie 2:<br/>tit=Title Words AND per=Author]
    S2 -->|Gefunden| Extract
    S2 -->|Nicht gefunden| S3

    S3[Strategie 3:<br/>tit="Exact Title"]
    S3 -->|Gefunden| Extract
    S3 -->|Nicht gefunden| S4

    S4[Strategie 4:<br/>tit=Title Words]
    S4 -->|Gefunden| Extract
    S4 -->|Nicht gefunden| Fail[❌ Nicht gefunden]

    Extract[MARC21 Extraktion] --> Store[(DNB TA-Variante<br/>dnb_title_ta<br/>dnb_authors_ta<br/>dnb_year_ta<br/>dnb_publisher_ta<br/>dnb_isbn_ta ✨<br/>dnb_issn_ta ✨)]

    style S1 fill:#e3f2fd
    style S2 fill:#e3f2fd
    style S3 fill:#e3f2fd
    style S4 fill:#e3f2fd
    style Store fill:#c8e6c9
\`\`\`

**Erfolgsrate:** ~64% (5,730 von 8,901 Queries)

**Neu in v2.0:** ISBN/ISSN-Extraktion aus DNB-Antworten für **massiven Identifier-Gewinn**!

**Output:** \`data/vdeh/processed/04_dnb_enriched_data.parquet\`

---

### 5. KI-gestützte Datenfusion

**Notebook:** \`05_vdeh_data_fusion.ipynb\`  
**Engine:** \`src/fusion/fusion_engine.py\`

#### Fusionslogik

\`\`\`mermaid
flowchart TB
    Start[VDEH Record +<br/>2 DNB-Varianten] --> HasDNB{DNB-Daten<br/>vorhanden?}

    HasDNB -->|Nein| Keep[VDEH beibehalten]
    HasDNB -->|Ja| Prepare

    Prepare[Konflikte & Bestätigungen<br/>identifizieren] --> AI

    AI[🤖 Ollama LLM<br/>llama3.3:70b] --> Decision{KI-Entscheidung}

    Decision -->|ID-Variante| UseID[ID-Variante verwenden]
    Decision -->|TA-Variante| UseTA[TA-Variante verwenden]
    Decision -->|KEINE| Reject[❌ Match verwerfen<br/>VDEH beibehalten]

    UseID --> Norm[String-Normalisierung]
    UseTA --> Norm

    Norm --> Check[Konfliktprüfung<br/>nach Normalisierung]
    Check --> Resolve[Intelligente<br/>Konfliktauflösung]

    Resolve --> Final[(Fusioniertes Record<br/>+ Metadaten)]
    Reject --> Final
    Keep --> Final

    style AI fill:#fff9c4
    style Decision fill:#ffe0b2
    style Final fill:#c8e6c9
\`\`\`

#### KI-Prompt Struktur

Die KI erhält:
- VDEH Original-Daten
- DNB ID-Variante (falls vorhanden)
- DNB TA-Variante (falls vorhanden)
- **Konflikte:** Abweichende Felder
- **Bestätigungen:** Übereinstimmende Felder

**Entscheidungsregeln:**
1. Titel + Autoren dominieren (Jahr ±2 toleriert)
2. Bei beiden passend: ID-Variante bevorzugen
3. Bei nur einer passend: Diese wählen
4. Bei keiner passend: Verwerfen (nur bei klar unterschiedlichen Werken)

#### String-Normalisierung

\`\`\`python
# Bibliographische Normalisierung
- Entfernung von ¬ Marker-Zeichen
- Normalisierung von & → "und"
- Umlaut-Varianten: oe→ö, ae→ä, ue→ü
- Bindestriche → Leerzeichen
- Trailing Punctuation entfernen
- Publisher-Locations entfernen: ": Berlin (DE)" → ""
\`\`\`

**Ergebnis:** 50% Reduktion der Konflikt-Rate (58% → 29%)

**Output:** \`data/vdeh/processed/05_fused_data.parquet\`

---

## 📊 Qualitätsmetriken (1000-Record-Test)

### Fusion-Qualität

| Metrik | Wert | Bewertung |
|--------|------|-----------|
| **Fusionierte Records** | 1,850 | |
| **Akzeptierte Fusion** | 827 (44.7%) | ✅ Hohe Qualität |
| **Verworfene Matches** | 1,023 (55.3%) | |
| └─ Wegen leeren VDEH-Daten | 951 (93%) | ✅ Korrekt verworfen |
| └─ Andere Gründe | 72 (7%) | ⚠️ Zu prüfen |
| **Konflikt-Rate** | 29.2% | ✅ Nach Normalisierung |
| **ID-Variante bevorzugt** | 97.7% | ✅ Korrekte Priorisierung |

### Informationsgewinn

| Feld | Vorher (VDEH) | Nachher (Fusion) | Gewinn |
|------|---------------|------------------|--------|
| **Titel** | 827 (100%) | 827 (100%) | +0% |
| **Autoren** | 827 (100%) | 827 (100%) | +0% |
| **Jahr** | 827 (100%) | 827 (100%) | +0% |
| **Publisher** | 450 (54.4%) | 473 (57.2%) | **+2.8%** ⭐ |
| **ISBN** (erwartet) | ~380 (46%) | ~650 (79%) | **+33%** 🚀 |
| **ISSN** (erwartet) | ~40 (5%) | ~120 (15%) | **+10%** 🚀 |

**Hauptgewinn:**
- ✅ Verlags-Informationen (+5.1% relativ)
- ✅ **ISBN/ISSN-Identifier** (geschätzt +3,000-4,000 neue ISBNs!)

---

## 📊 VDEH Datenquellen - Vollständigkeitsvergleich

Das Projekt arbeitet mit mehreren Versionen der VDEH-Daten. Die folgende Tabelle zeigt die Vollständigkeit der wichtigsten Metadatenfelder:

| Feld | MAB (XML) | CSV (preprocessed) | MARC21 (XML) |
|------|-----------|-------------------|--------------|
| **TOTAL RECORDS** | 58,760 (100.0%) | 58,431 (100.0%) | **58,305 (100.0%)** |
| **Titel** | 40,830 (69.5%) | 58,043 (99.3%) | **58,252 (99.9%)** ✅ |
| **Autor** | 17,016 (29.0%) | 16,855 (28.8%) | **18,740 (32.1%)** ✅ |
| **ISBN** | **10,744 (18.3%)** ✅ | 10,576 (18.1%) | 10,586 (18.2%) |
| **ISSN** | 728 (1.2%) | 702 (1.2%) | **719 (1.2%)** |
| **Seitenzahl** | **29,396 (50.0%)** ✅ | 0 (0.0%) ❌ | 29,080 (49.9%) |

### Datenquellen im Detail

1. **VDEH_mab_all.xml (MAB Format)**
   - Pfad: `data/vdeh/raw/VDEH_mab_all.xml`
   - Format: MAB (Maschinelles Austauschformat für Bibliotheken)
   - Besonderheit: Nur 69.5% haben Hauptsachtitel (Feld 331)
   - Stärke: Beste ISBN-Abdeckung (18.3%)

2. **marcBIB-VDEH-xml2-tsv.csv (Preprocessed)**
   - Pfad: `/media/sz/Data/Bibo/data/marcBIB-VDEH-xml2-tsv.csv`
   - Format: CSV (Tab-separated)
   - Besonderheit: Kombiniert mehrere Titelfelder (331+335+340+655+750)
   - Stärke: Sehr gute Titel-Vollständigkeit (99.3%)
   - Schwäche: Keine Seitenzahl-Informationen

3. **marcVDEH.xml (MARC21 Format)** ⭐ **EMPFOHLEN**
   - Pfad: `/media/sz/Data/Bibo/data/marcVDEH.xml`
   - Format: MARC21 (international standard)
   - Stärke: Beste Titel-Vollständigkeit (99.9%), beste Autoren-Abdeckung (32.1%)
   - Besonderheit: Nur 53 Records ohne Titel (0.03%)

### Empfehlung

**Nutze marcVDEH.xml (MARC21)** als primäre Datenquelle:
- ✅ Beste Titel-Vollständigkeit (99.9%)
- ✅ Standardisiertes internationales Format
- ✅ Beste Autoren-Abdeckung (32.1%)
- ✅ Gute Seitenzahl-Informationen (50%)

**Herausforderung:** Alle Quellen haben niedrige ISBN/ISSN-Abdeckung (~18%), was DNB-Enrichment einschränkt.

**Analyseskript:** `scripts/compare_all_sources.py`

---

## 🔧 Technische Details

### Dependencies

\`\`\`toml
[tool.poetry.dependencies]
python = "^3.12"
pandas = "^2.1.0"
lxml = "^4.9.3"
requests = "^2.31.0"
langdetect = "^1.0.9"
tqdm = "^4.66.1"
jupyter = "^1.0.0"
matplotlib = "^3.8.0"
seaborn = "^0.13.0"
pyyaml = "^6.0.1"
ollama = "^0.1.0"
\`\`\`

### Konfiguration

Alle Parameter sind zentral in \`config.yaml\` konfigurierbar:

\`\`\`yaml
comparison:
  matching_strategies:
    - isbn_exact
    - isbn_normalized
    - title_fuzzy

  similarity_thresholds:
    title_fuzzy: 0.85
    author_fuzzy: 0.90

debug:
  fusion_limit: 1000  # Für Tests
\`\`\`

### Performance

- **Parallel Processing:** \`-1\` (alle CPU-Kerne)
- **Chunk Size:** 1,000 Records
- **Rate Limiting:** 0.5s zwischen DNB-Queries
- **Progressive Saving:** Alle 50 Records

---

## 📈 Verwendung

### 1. Setup

\`\`\`bash
# Repository klonen
git clone <repo-url>
cd analysis

# Dependencies installieren
poetry install

# Ollama starten (für Fusion)
ollama pull llama3.3:70b
ollama serve
\`\`\`

### 2. Pipeline ausführen

\`\`\`bash
# Gesamte Pipeline
poetry run jupyter notebook notebooks/01_vdeh_preprocessing/

# Einzelne Schritte
poetry run jupyter notebook notebooks/01_vdeh_preprocessing/01_vdeh_xml_parsing.ipynb
poetry run jupyter notebook notebooks/01_vdeh_preprocessing/04_vdeh_data_enrichment.ipynb
poetry run jupyter notebook notebooks/01_vdeh_preprocessing/05_vdeh_data_fusion.ipynb
\`\`\`

### 3. Qualitätsanalyse

\`\`\`bash
poetry run jupyter notebook notebooks/02_vdeh_analysis/04_fusion_quality_analysis.ipynb
\`\`\`

---

## 🤝 Mitwirkende

**Data Analysis Team**  
TU Bergakademie Freiberg

---

## 📄 Lizenz

Dieses Projekt ist für interne Verwendung bestimmt.

---

## 🔗 Referenzen

- **DNB SRU API:** https://www.dnb.de/DE/Professionell/Metadatendienste/Datenbezug/SRU/sru_node.html
- **OAI-PMH:** https://www.openarchives.org/pmh/
- **MARC21:** https://www.loc.gov/marc/bibliographic/
- **Ollama:** https://ollama.ai/

---

**Erstellt:** 2024-10-31
**Letzte Aktualisierung:** 2025-12-12
**Version:** 2.1.0

## 🆕 Was ist neu in v2.1.0?

### Title/Year Search (Dritte DNB-Strategie)
- **Neue Suchmethode**: Titel + Jahr für Records ohne ISBN/ISSN/Autoren
- **Reichweite**: 16,458 zusätzliche Records erreichbar
- **Erwarteter Gewinn**: 1,645-2,468 neue Autoren (5-8x Verbesserung!)
- **Fallback-Logik**: Automatische Nutzung wenn ID/TA nicht verfügbar

### Seitenzahlen-Extraktion
- **MARC21 Field 300**: Vollständige Pages-Erfassung (49.9% Abdeckung)
- **DNB Pages**: Extraktion aus allen drei DNB-Varianten (ID, TA, TY)
- **Fusion**: Intelligente Pages-Quelle-Tracking
- **Erwartete Gesamtabdeckung**: ~55-60% (nach DNB-Enrichment)

### Dokumentation
- [`docs/title_year_implementation.md`](docs/title_year_implementation.md) - Detaillierte Implementierung
- Vollständige API-Dokumentation für alle drei Suchmethoden
- Test-Scripts und Validierung

Siehe [CHANGELOG_MARC21.md](CHANGELOG_MARC21.md) für vollständige Release Notes.
