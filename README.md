# VDEh-Bestandsanalyse

**KI-gestützte bibliographische Datenanreicherung und Bestandsvergleich**

## Übersicht

Dieses Projekt führt einen systematischen Vergleich zwischen den VDEh-Neuerwerbungen (58.305 MARC21-Datensätze) und dem UB TUBAF-Bestand (MAB2) durch. Zur Überwindung der lückenhaften Metadaten (nur 18% ISBN-Abdeckung) werden die Daten über die Deutsche Nationalbibliothek (DNB) und Library of Congress (LoC) angereichert und mittels KI-gestützter Fusion (Ollama llama3.3:70b) zusammengeführt.

Die vollständige Analyse mit Ergebnissen und Diskussion ist im Bericht dokumentiert:
**[VDEH_Bestandsanalyse.pdf](docs/paper/VDEH_Bestandsanalyse.pdf)**

Das methodische Vorgehen und die Verarbeitungspipeline sind separat beschrieben:
**[docs/METHODIK.md](docs/METHODIK.md)**

## Projektstruktur

```
analysis/
├── src/                          # Source Code Module
│   ├── parsers/                  # MARC21 & MAB2 Parser
│   ├── fusion/                   # KI-Fusion Engine (Ollama)
│   ├── comparison/               # Bestandsvergleich (Matching)
│   ├── dnb_api.py                # DNB SRU API Client
│   └── loc_api.py                # Library of Congress API Client
│
├── notebooks/                    # Jupyter Notebooks
│   ├── 01_vdeh_preprocessing/    # VDEh Verarbeitungspipeline (6 Notebooks)
│   └── 02_ub_comparision/        # UB TUBAF Laden & Vergleich (2 Notebooks)
│
├── data/                         # Roh- und Ergebnisdaten
│   ├── vdeh/                     # VDEh (MARC21 XML)
│   ├── ub_tubaf/                 # UB TUBAF (MAB2)
│   └── comparison/               # Vergleichsergebnisse
│
├── scripts/                      # Test- und Analyse-Scripts
├── docs/                         # Dokumentation & Paper
└── config.yaml                   # Zentrale Konfiguration
```

## Setup & Installation

### Voraussetzungen

- Python 3.10+
- Poetry
- Ollama (für KI-Fusion)

### Installation

```bash
poetry install

# Ollama-Modell für Fusion laden
ollama pull llama3.3:70b
ollama serve
```

### Konfiguration

Zentrale Einstellungen in [config.yaml](config.yaml) (Datenpfade, API-Limits, Fusion-Parameter).

## Verwendung

```bash
# VDEh Pipeline (Schritt für Schritt)
cd notebooks/01_vdeh_preprocessing
poetry run jupyter notebook 01_vdeh_data_loading.ipynb
# ... bis 05_vdeh_dnb_loc_fusion.ipynb

# UB TUBAF & Vergleich
cd notebooks/02_ub_comparision
poetry run jupyter notebook 01_ub_data_loading.ipynb
poetry run jupyter notebook 02_vdeh_ub_collection_check.ipynb
```

## Weiterführende Dokumentation

- **Analysebericht:** [docs/paper/VDEH_Bestandsanalyse.pdf](docs/paper/VDEH_Bestandsanalyse.pdf)
- **Methodik & Pipeline:** [docs/METHODIK.md](docs/METHODIK.md)
- **Fusion-Planung:** [docs/multi_source_fusion_plan.md](docs/multi_source_fusion_plan.md)

## Autoren

Sebastian Zug, Oliver Löwe
TU Bergakademie Freiberg

Kontakt: sebastian.zug@informatik.tu-freiberg.de

---

**Lizenz:** Internes Forschungsprojekt
