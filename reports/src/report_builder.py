"""
Report Builder Module für VDEh-Bibliotheksanalyse
Generiert Report-Dokumente aus Templates und Analyseergebnissen mit Jinja2.

Angepasst von LiaScript_Paper/pipeline/paper_builder.py
"""

import logging
from pathlib import Path
from typing import Dict, Any, List
from jinja2 import Environment, FileSystemLoader, Template
import subprocess

logger = logging.getLogger(__name__)


class ReportBuilder:
    """Generiert Report-Dokumente aus Templates und Analyseergebnissen."""

    def __init__(self, template_dir: str, results: Dict[str, Any], config: Dict[str, Any]):
        """
        Initialisiert den Report Builder.

        Args:
            template_dir: Verzeichnis mit Jinja2-Templates
            results: Analyseergebnisse-Dictionary
            config: Konfigurations-Dictionary
        """
        self.template_dir = Path(template_dir)
        self.results = results
        self.config = config

        # Jinja2 Environment einrichten
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )

        # Custom Filters hinzufügen
        self._add_custom_filters()

        logger.info(f"ReportBuilder initialisiert mit Templates aus {self.template_dir}")

    def _add_custom_filters(self):
        """Fügt custom Jinja2-Filter für Formatierung hinzu."""

        def format_number(value, decimals=2):
            """Formatiert Zahl mit angegebener Dezimalstellen-Anzahl."""
            try:
                return f"{float(value):.{decimals}f}"
            except (ValueError, TypeError):
                return value

        def format_percent(value, decimals=1):
            """Formatiert als Prozentsatz."""
            try:
                return f"{float(value) * 100:.{decimals}f}%"
            except (ValueError, TypeError):
                return value

        def format_large_number(value):
            """Formatiert große Zahlen mit Tausender-Trennzeichen."""
            try:
                # Deutsche Formatierung: Punkt als Tausender-Trenner
                return f"{int(value):,.0f}".replace(",", ".")
            except (ValueError, TypeError):
                return value

        def format_decimal_german(value, decimals=2):
            """Formatiert Dezimalzahl im deutschen Format (Komma statt Punkt)."""
            try:
                formatted = f"{float(value):.{decimals}f}"
                return formatted.replace(".", ",")
            except (ValueError, TypeError):
                return value

        # Filter registrieren
        self.env.filters['num'] = format_number
        self.env.filters['pct'] = format_percent
        self.env.filters['large'] = format_large_number
        self.env.filters['de_num'] = format_decimal_german

    def build_section(self, section_name: str) -> str:
        """
        Rendert eine einzelne Sektion mit Jinja2.

        Args:
            section_name: Name des Sektions-Templates (ohne Extension)

        Returns:
            Gerenderte Sektions-Inhalte
        """
        template_file = f"{section_name}.md.jinja"
        logger.info(f"Rendere Sektion: {section_name}")

        try:
            template = self.env.get_template(template_file)
            content = template.render(
                results=self.results,
                config=self.config,
                report=self.config.get('report', {}),
                rq=self.config.get('research_questions', {})
            )
            return content
        except Exception as e:
            logger.error(f"Fehler beim Rendern von {section_name}: {e}", exc_info=True)
            return f"\n<!-- Fehler beim Rendern von {section_name}: {e} -->\n"

    def build_full_report(self, section_order: List[str] = None, github_format: bool = False) -> str:
        """
        Assembliert alle Sektionen zu einem vollständigen Report.

        Args:
            section_order: Liste der Sektionsnamen in Reihenfolge
            github_format: Wenn True, wird GitHub-kompatibles Markdown generiert

        Returns:
            Vollständiger Report-Inhalt
        """
        if section_order is None:
            # Standard-Reihenfolge für VDEh-Report (Paper Structure)
            section_order = [
                '00_motivation',
                '01_vdeh_bestand',
                '02_erster_abgleich',
                '03_anreicherung',
                '04_verbesserter_abgleich',
                '05_forschungsfragen',
                '02_einleitung',
                '03_datenaufbereitung',
                '04_ergebnisse',
                '05_diskussion',
                '06_fazit',
                '07_literatur'
            ]

        logger.info("Baue vollständigen Report...")

        # Frontmatter hinzufügen
        report_parts = [self._build_frontmatter(github_format=github_format)]

        # Abstract hinzufügen (falls vorhanden)
        abstract_template = self.template_dir / '01_abstract.md.jinja'
        if abstract_template.exists():
            try:
                # Abstract wird im Frontmatter eingebunden, hier nicht nochmal
                pass
            except Exception as e:
                logger.warning(f"Abstract-Rendering fehlgeschlagen: {e}")

        # Jede Sektion hinzufügen
        for section in section_order:
            try:
                content = self.build_section(section)
                report_parts.append(content)
            except Exception as e:
                logger.warning(f"Sektion {section} fehlgeschlagen: {e}")

        # Appendix hinzufügen (falls konfiguriert)
        if self.config.get('report', {}).get('output', {}).get('include_appendix', False):
            appendix_template = self.template_dir / '08_appendix.md.jinja'
            if appendix_template.exists():
                try:
                    appendix = self.build_section('08_appendix')
                    report_parts.append(appendix)
                except Exception as e:
                    logger.warning(f"Appendix-Rendering fehlgeschlagen: {e}")

        full_report = '\n\n'.join(report_parts)
        logger.info(f"Report gebaut: {len(full_report)} Zeichen")

        return full_report

    def _build_frontmatter(self, github_format: bool = False) -> str:
        """
        Generiert Report-Frontmatter (Titel, Autoren, etc.).

        Args:
            github_format: Wenn True, wird GitHub-kompatibles Markdown generiert,
                          sonst YAML-Format für Pandoc.

        Returns:
            Frontmatter-Markdown
        """
        report_config = self.config.get('report', {})
        title = report_config.get('title', 'Untitled Report')
        subtitle = report_config.get('subtitle', '')
        authors = report_config.get('authors', [])
        metadata = report_config.get('metadata', {})

        if github_format:
            return self._build_github_header(title, subtitle, authors, metadata, report_config)

        # YAML Frontmatter für Pandoc erstellen
        yaml_lines = [
            "---",
            f"title: \"{title}\""
        ]

        if subtitle:
            yaml_lines.append(f"subtitle: \"{subtitle}\"")

        # Autoren im Pandoc-Format
        if authors:
            yaml_lines.append("author:")
            for author in authors:
                name = author.get('name', '')
                yaml_lines.append(f"  - {name}")

            # Institut-Informationen
            yaml_lines.append("institute:")
            for author in authors:
                if 'affiliation' in author:
                    yaml_lines.append(f"  - {author['affiliation']}")

        # Datum
        date = metadata.get('date', '')
        if date:
            yaml_lines.append(f"date: \"{date}\"")

        # Abstract direkt aus Config holen
        abstract_text = report_config.get('abstract', None)

        if abstract_text:
            abstract_text = abstract_text.replace('"', '\\"')
            yaml_lines.append("abstract: |")
            for line in abstract_text.split('\n'):
                yaml_lines.append(f"  {line}")

        # Keywords
        if 'keywords' in metadata:
            keywords = metadata['keywords']
            yaml_lines.append("keywords:")
            for keyword in keywords:
                yaml_lines.append(f"  - \"{keyword}\"")

        # Sprache
        language = report_config.get('output', {}).get('language', 'de-DE')
        yaml_lines.append(f"lang: {language}")

        # YAML-Block schließen
        yaml_lines.append("---")
        yaml_lines.append("")

        return "\n".join(yaml_lines)

    def _build_github_header(self, title: str, subtitle: str, authors: list,
                              metadata: dict, report_config: dict) -> str:
        """
        Generiert GitHub-kompatiblen Markdown-Header statt YAML-Frontmatter.

        Returns:
            Markdown-Header für GitHub-Rendering
        """
        lines = []

        # Titel und Untertitel
        lines.append(f"# {title}")
        if subtitle:
            lines.append(f"### {subtitle}")
        lines.append("")

        # Autoren und Datum
        author_names = [a.get('name', '') for a in authors]
        affiliations = [a.get('affiliation', '') for a in authors if a.get('affiliation')]

        if author_names:
            lines.append(f"**Autoren:** {', '.join(author_names)}")
        if affiliations:
            lines.append(f"**Institution:** {', '.join(set(affiliations))}")

        date = metadata.get('date', '')
        if date:
            lines.append(f"**Datum:** {date}")

        lines.append("")

        # Abstract als Blockquote
        abstract_text = report_config.get('abstract', None)
        if abstract_text:
            lines.append("---")
            lines.append("")
            lines.append("**Abstract:**")
            lines.append("")
            for para in abstract_text.strip().split('\n\n'):
                lines.append(f"> {para.strip()}")
            lines.append("")

        # Keywords
        if 'keywords' in metadata:
            keywords = metadata['keywords']
            lines.append(f"**Schlagwörter:** {', '.join(keywords)}")
            lines.append("")

        lines.append("---")
        lines.append("")

        return "\n".join(lines)

    def export_markdown(self, output_path: str, content: str = None,
                         section_order: List[str] = None, github_format: bool = True):
        """
        Exportiert Report als Markdown-Datei.

        Args:
            output_path: Pfad zur Output-Datei
            content: Report-Inhalt (falls None, wird vollständiger Report gebaut)
            section_order: Liste der Sektionsnamen in Reihenfolge
            github_format: Wenn True, wird GitHub-kompatibles Markdown generiert (Standard: True)
        """
        if content is None:
            content = self.build_full_report(section_order=section_order, github_format=github_format)

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Schreibe Markdown nach {output_file}")
        output_file.write_text(content, encoding='utf-8')
        logger.info("Markdown-Export abgeschlossen")

    def export_pdf(self, output_path: str, content: str = None, template: str = None):
        """
        Exportiert Report als PDF mit Pandoc und LaTeX.

        Args:
            output_path: Pfad zur Output-PDF-Datei
            content: Report-Inhalt (falls None, wird vollständiger Report gebaut)
            template: LaTeX-Template-Name
        """
        import re

        if content is None:
            content = self.build_full_report()

        project_root = Path(__file__).parent.parent.parent

        # Temporäre Markdown-Datei im Build-Verzeichnis speichern
        output_file = Path(output_path).resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)

        build_dir = output_file.parent
        temp_md = build_dir / 'temp_report.md'
        temp_md.write_text(content, encoding='utf-8')

        logger.info(f"Konvertiere zu PDF: {output_file}")

        # Resource-Path: Output-Dir (für figures/) und reports/paper (für Templates)
        resource_paths = [
            str(build_dir),              # docs/paper/ (für figures/)
            str(project_root / 'reports' / 'paper'),
        ]

        # Pandoc-Befehl erstellen
        pandoc_cmd = [
            'pandoc',
            str(temp_md.resolve()),
            '-o', str(output_file),
            '--from', 'markdown-smart',
            '--to', 'pdf',
            '--pdf-engine', 'xelatex',
            '--lua-filter', str(project_root / 'reports' / 'paper' / 'filters' / 'mermaid.lua'),
            '--resource-path', ':'.join(resource_paths)
        ]

        # Inhaltsverzeichnis hinzufügen (falls konfiguriert)
        if self.config.get('report', {}).get('output', {}).get('include_toc', False):
            pandoc_cmd.append('--toc')
            toc_depth = self.config.get('report', {}).get('output', {}).get('toc_depth', 3)
            pandoc_cmd.extend(['--toc-depth', str(toc_depth)])

        # Template hinzufügen (falls angegeben)
        if template:
            template_path = Path(self.template_dir).parent / 'templates' / f'{template}.tex'
            # Absoluten Pfad verwenden, damit Pandoc das Template findet
            template_path_abs = (project_root / 'reports' / template_path).resolve()
            logger.info(f"Template-Pfad: {template_path_abs} (exists: {template_path_abs.exists()})")
            if template_path_abs.exists():
                pandoc_cmd.extend(['--template', str(template_path_abs)])
                logger.info(f"Template wird verwendet: {template_path_abs}")
            else:
                logger.warning(f"LaTeX-Template nicht gefunden: {template_path_abs}")

        try:
            # Vom Projekt-Root ausführen, damit relative Pfade funktionieren
            logger.info(f"Pandoc-Befehl: {' '.join(pandoc_cmd)}")
            subprocess.run(pandoc_cmd, check=True, cwd=str(project_root))
            logger.info("PDF-Export abgeschlossen")
        except subprocess.CalledProcessError as e:
            logger.error(f"Pandoc PDF-Konvertierung fehlgeschlagen: {e}")
            logger.error("Stelle sicher, dass xelatex installiert ist")
        except FileNotFoundError:
            logger.error("Pandoc nicht gefunden. Bitte installieren: sudo apt install pandoc texlive-xetex")
        finally:
            # Temporäre Datei NICHT aufräumen für Debugging
            # if temp_md.exists():
            #     temp_md.unlink()
            pass

    def export_all(self, output_dir: str):
        """
        Exportiert Report in allen konfigurierten Formaten.

        Args:
            output_dir: Verzeichnis für Output-Dateien
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Report einmal bauen
        content = self.build_full_report()

        output_config = self.config.get('report', {}).get('output', {})
        formats = output_config.get('format', ['markdown'])
        template = output_config.get('template', 'koma-article')

        logger.info(f"Exportiere Report in Formaten: {formats}")

        if 'markdown' in formats:
            self.export_markdown(output_path / 'report.md', content)

        if 'pdf' in formats:
            self.export_pdf(output_path / 'report.pdf', content, template)

        logger.info("Alle Exports abgeschlossen")
