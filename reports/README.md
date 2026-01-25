# VDEh Report Generator

Generiert wissenschaftliche Reports zur VDEh-Bibliotheksanalyse mit Jinja2-Templates und Pandoc.

## Struktur

```
reports/
├── run_report_paper.py      # Hauptskript
├── src/
│   ├── __init__.py
│   └── report_builder.py    # Jinja2-Engine & PDF-Export
└── paper/
    ├── sections/            # Jinja2-Templates (.md.jinja)
    ├── templates/           # LaTeX-Template (koma-article.tex)
    └── filters/             # Pandoc Lua-Filter (mermaid.lua)
```

**Output** wird nach `docs/paper/` geschrieben (GitHub-sichtbar):
```
docs/paper/
├── VDEH_Bestandsanalyse.md  # Markdown-Report
├── VDEH_Bestandsanalyse.pdf # PDF-Report
└── figures/                  # Generierte Grafiken
```

## Report generieren

```bash
# Vom Projekt-Root
poetry run python reports/run_report_paper.py
```

**Voraussetzung:** Statistiken müssen vorher generiert werden:
```bash
poetry run python scripts/generate_paper_stats.py
```

## Optionen

```bash
# Mit Debug-Logging
poetry run python reports/run_report_paper.py --log-level DEBUG

# Nur PDF (kein Markdown)
poetry run python reports/run_report_paper.py --pdf-only

# Custom Output-Verzeichnis
poetry run python reports/run_report_paper.py --output custom/path
```

## Templates anpassen

Templates in `paper/sections/`:
- `00_motivation.md.jinja`
- `01_vdeh_bestand.md.jinja`
- `02_anreicherung.md.jinja`
- `03_abgleich.md.jinja`
- `04_forschungsfragen.md.jinja`

Nach Änderungen einfach erneut generieren.

## Abhängigkeiten

- Python 3.10+
- Pandoc
- XeLaTeX (für PDF-Export)
- Jinja2
