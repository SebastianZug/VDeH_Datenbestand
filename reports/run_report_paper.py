#!/usr/bin/env python3
"""
Paper Report Generator
Generiert Markdown und PDF aus Statistiken und Jinja2-Templates.

Output:
- docs/paper/VDEH_Bestandsanalyse.md (GitHub-sichtbar)
- docs/paper/VDEH_Bestandsanalyse.pdf
"""

import argparse
import logging
import sys
import json
import subprocess
from pathlib import Path

# Projekt-Root zum Path hinzufügen
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.report_builder import ReportBuilder


def setup_logging(log_level: str = "INFO"):
    """Konfiguriert Logging."""
    log_dir = project_root / 'logs'
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / 'paper_report.log')
        ]
    )


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='VDEh Paper Report Generator')
    parser.add_argument('--stats', default='data/processed/paper_statistics.json',
                       help='Pfad zur Statistik-Datei (relativ zum Projekt-Root)')
    parser.add_argument('--output', default='docs/paper',
                       help='Output-Verzeichnis (relativ zum Projekt-Root)')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging-Level')
    parser.add_argument('--pdf-only', action='store_true',
                       help='Nur PDF generieren, kein Markdown')

    args = parser.parse_args()

    # Logging einrichten
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    logger.info("="*70)
    logger.info("VDEh PAPER REPORT GENERATOR")
    logger.info("="*70)

    # Load statistics
    stats_path = project_root / args.stats
    if not stats_path.exists():
        logger.error(f"Statistik-Datei nicht gefunden: {stats_path}")
        logger.error("Führe zuerst aus: poetry run python scripts/generate_paper_stats.py")
        sys.exit(1)

    logger.info(f"\n1. Lade Statistiken: {stats_path}")
    with open(stats_path, 'r', encoding='utf-8') as f:
        analysis_results = json.load(f)

    logger.info(f"   ✓ Statistiken geladen")

    # Generate figures - output to docs/paper/figures/
    logger.info(f"\n2. Generiere Abbildungen...")
    figures_script = project_root / 'scripts' / 'generate_paper_figures.py'
    output_dir = project_root / args.output
    figures_dir = output_dir / 'figures'

    if figures_script.exists():
        result = subprocess.run(
            [sys.executable, str(figures_script), '--output', str(figures_dir)],
            capture_output=True,
            text=True,
            cwd=str(project_root)
        )
        if result.returncode == 0:
            logger.info(f"   ✓ Abbildungen generiert nach {figures_dir}")
        else:
            logger.warning(f"   ⚠ Fehler bei Figurengenerierung: {result.stderr}")
    else:
        logger.warning(f"   ⚠ Figuren-Script nicht gefunden: {figures_script}")

    # Minimal config for report builder
    config = {
        'report': {
            'title': 'Der VDEh-Bestand der UB Freiberg',
            'subtitle': 'Eine datengetriebene Analyse',
            'abstract': 'Dieser Bericht fasst die Analyse des Bestandskataloges der VDEh-Bibliothek zusammen und evaluiert die Überdeckung des Bestandes mit der UB Freiberg. Des weiteren erfolgt eine Abschätzung der Seitenzahlen, die bei einer vollständig digitalen Erfassung gescannt werden müssten. Dafür war es notwendig, den VDEh-Bestand mit externen Katalogen (Deutsche Nationalbibliothek, Library of Congress) abzugleichen und die Metadaten mit Hilfe von KI-gestützten Methoden anzureichern. Die Ergebnisse zeigen, dass durch die Anreicherung eine signifikante Verbesserung der Abdeckungsrate erreicht werden konnte. Abschließend werden die gewonnenen Erkenntnisse im Hinblick auf die Forschungsfragen diskutiert.\n\nDie zugehörige Implementierung ist als Open Source auf [Github](https://github.com/SebastianZug/VDeH_Datenbestand) verfügbar. Die Implementierung der Pipeline und des Berichtgenerators erfolgte unter Verwendung von Claude.ai.',
            'authors': [
                {
                    'name': 'Sebastian Zug (Fak. 1), Oliver Löwe (UB Freiberg)',
                    'affiliation': 'TU Bergakademie Freiberg'
                }
            ],
            'metadata': {
                'date': '2026-01-25',
                'keywords': ['Bibliotheksbestand', 'Datenanreicherung', 'DNB', 'LoC', 'KI-Fusion']
            },
            'output': {
                'format': ['markdown', 'pdf'],
                'language': 'de-DE',
                'include_toc': True,
                'toc_depth': 1,
                'template': 'koma-article'
            }
        }
    }

    # Initialize Report Builder
    logger.info("\n3. Initialisiere Report Builder...")
    reports_dir = Path(__file__).parent
    builder = ReportBuilder(
        template_dir=str(reports_dir / 'paper' / 'sections'),
        results=analysis_results,
        config=config
    )

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"\n4. Generiere Report...")

    # Section order for paper
    section_order = [
        '00_motivation',
        '01_vdeh_bestand',
        '02_anreicherung',
        '03_abgleich',
        '04_forschungsfragen'
    ]

    # Export - use descriptive filename for GitHub
    report_name = 'VDEH_Bestandsanalyse'

    # Markdown: GitHub-Format (ohne YAML-Frontmatter)
    if not args.pdf_only:
        md_path = output_dir / f'{report_name}.md'
        logger.info(f"   → Markdown (GitHub-Format): {md_path}")
        builder.export_markdown(str(md_path), section_order=section_order, github_format=True)

    # PDF: Pandoc/YAML-Format
    pdf_path = output_dir / f'{report_name}.pdf'
    logger.info(f"   → PDF: {pdf_path}")
    template = config['report']['output']['template']
    pdf_content = builder.build_full_report(section_order=section_order, github_format=False)
    builder.export_pdf(str(pdf_path), pdf_content, template=template)

    logger.info("\n" + "="*70)
    logger.info("✅ REPORT ERFOLGREICH GENERIERT")
    logger.info("="*70)

    logger.info(f"\nOutput (GitHub-sichtbar unter docs/paper/):")
    if not args.pdf_only:
        logger.info(f"  - Markdown: {md_path}")
    logger.info(f"  - PDF: {pdf_path}")
    logger.info(f"  - Figures: {figures_dir}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nUnterbrochen")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Fehler: {e}", exc_info=True)
        sys.exit(1)
