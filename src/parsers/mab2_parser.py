"""
MAB2 Parser für deutsche Bibliotheksdaten

Dieses Modul parsed MAB2 (Maschinelles Austauschformat für Bibliotheken Version 2) 
Dateien und extrahiert bibliographische Informationen.

MAB2 Format:
- Records beginnen mit "### " (0x23 0x23 0x23 0x20)  
- Felder haben numerische Codes (001, 310, 331, etc.)
- Trennung durch CR LF (\r\n)
- Encoding typischerweise Latin1/CP1252

Features:
- Robuste Behandlung von Sonderzeichen und Formatierungen
- Erweiterte Datenvalidierung und -bereinigung
- Flexible Verarbeitung von String- und Dateiinput
- Detaillierte Parsing-Statistiken

Autor: Data Analysis Team
Erstellt: 2024-10-31
Aktualisiert: 2025-11-02
"""

import logging
import re
import pandas as pd
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Any

@dataclass
class MAB2Record:
    """
    Datenklasse für einen MAB2-Record
    
    Attributes:
        record_id: Eindeutige ID des Records
        fields: Dictionary mit den MAB2-Feldern und ihren Werten
        raw_data: Original MAB2-Daten als String
        errors: Liste von aufgetretenen Fehlern bei der Verarbeitung
    """
    record_id: str
    fields: Dict[str, Union[str, List[str]]]
    raw_data: str
    errors: List[str] = None
    
    def __post_init__(self):
        # Initialisiere errors falls nicht gesetzt
        if self.errors is None:
            self.errors = []

class MAB2Parser:
    """
    Parser für MAB2-Dateien (Deutsche Bibliotheksdaten)
    
    Wichtige MAB-Felder:
    - 001: Identifikationsnummer
    - 310/331: Titel  
    - 100: Autor/Herausgeber
    - 425: Erscheinungsjahr
    - 540: ISBN
    """
    
    def __init__(self, debug_mode: bool = False, debug_first_n: int = 5, 
                 encoding: str = 'latin1', logger: Optional[logging.Logger] = None):
        """
        Initialisiert den MAB2-Parser.
        
        Args:
            debug_mode: Aktiviert detailliertes Logging wenn True
            debug_first_n: Anzahl der ersten n Records für Debug-Ausgaben
            encoding: Encoding der MAB2-Dateien
            logger: Logger-Instanz (optional)
        """
        self.encoding = encoding
        self.logger = logger or logging.getLogger(__name__)
        
        if debug_mode:
            self.logger.setLevel(logging.DEBUG)
        
        # Debugging-Parameter
        self.debug_first_n = debug_first_n
        self.debug_mode = debug_mode
        
        # MAB-Feldmapping für bibliographische Daten
        self.field_mapping = {
            # Identifikation
            '001': 'id',
            '010': 'isbn', 
            '013': 'isbn_additional',
            '540': 'isbn_main',
            '542': 'issn',
            '552': 'doi',
            
            # Titel & Autoren
            '310': 'title_main',
            '331': 'title_alt',
            '335': 'subtitle',
            '359': 'title_subtitle',
            '100': 'author_primary',
            '104': 'author_other',
            '200': 'author_secondary',
            
            # Publikationsinfos
            '410': 'publisher_place',
            '412': 'publisher_name',
            '425': 'pub_year',
            '403': 'edition',
            '037': 'language',
            
            # Physische Beschreibung
            '433': 'pages',
            '435': 'format',
            
            # Klassifikation
            '700': 'ddc',
            '740': 'subjects'
        }
        
        # Stats initialisieren
        self.stats = {
            'total_records': 0,
            'parsed_records': 0,
            'error_records': 0,
            'field_counts': {}
        }
    
    def parse_content(self, content: str, max_records: Optional[int] = None) -> pd.DataFrame:
        """
        Parsed MAB2-Content direkt aus einem String

        Args:
            content: MAB2-formatierter String
            max_records: Maximale Anzahl Records (None = alle)

        Returns:
            DataFrame mit bibliographischen Daten
        """
        records = []
        
        # Setze Stats zurück
        self.stats['total_records'] = 0
        self.stats['parsed_records'] = 0
        self.stats['error_records'] = 0
        
        raw_records = self._split_records(content)
        if max_records:
            raw_records = raw_records[:max_records]
        
        self.stats['total_records'] = len(raw_records)
        self.logger.info(f"📋 Gefundene Records: {len(raw_records):,}")
        
        # Parse jeden Record
        for i, raw_record in enumerate(raw_records):
            # Aktiviere Debug für erste Records
            self.debug_mode = i < self.debug_first_n
            
            try:
                if self.debug_mode:
                    self.logger.debug(f"\n=== VERARBEITE RECORD {i+1} ===")
                    self.logger.debug(f"RAW RECORD:\n{raw_record[:200]}...")
                
                record = self._parse_record(raw_record)
                if record:
                    if self.debug_mode:
                        self.logger.debug(f"PARSED FIELDS: {list(record.fields.keys())}")
                    # Extrahiere bibliographische Daten
                    bib_data = self._extract_bibliographic_data(record)
                    if bib_data:
                        # Zeige erste erfolgreichen Records komplett
                        if self.debug_mode:
                            self.logger.info(f"\n✅ ERFOLGREICH GEPARST (Record {i+1}):")
                            for key, value in bib_data.items():
                                if key != 'original_fields':
                                    self.logger.info(f"   {key}: {value}")
                        records.append(bib_data)
                        self.stats['parsed_records'] += 1
                    else:
                        if self.debug_mode:
                            self.logger.warning(f"⚠️  Keine bibliographischen Daten extrahiert")
                else:
                    if self.debug_mode:
                        self.logger.warning(f"⚠️  Record konnte nicht geparst werden")
                    
            except Exception as e:
                self.stats['error_records'] += 1
                if self.debug_mode:
                    self.logger.error(f"❌ Fehler beim Parsen von Record {i+1}:")
                    self.logger.error(f"   {str(e)}")
                    self.logger.error(f"   Record-Start: {raw_record[:100]}...")
                
            # Progress-Info alle 1000 Records
            if (i + 1) % 1000 == 0:
                success_rate = (self.stats['parsed_records'] / (i + 1)) * 100
                self.logger.info(f"📊 Verarbeitet: {i+1:,} Records (Erfolgsrate: {success_rate:.1f}%)")
        
        # Erstelle DataFrame
        df = pd.DataFrame(records)
        
        # Log Statistiken
        self.logger.info(f"\n✅ MAB2-Parsing abgeschlossen:")
        self.logger.info(f"   📋 Total Records: {self.stats['total_records']:,}")
        self.logger.info(f"   ✅ Erfolgreich geparst: {self.stats['parsed_records']:,}")
        self.logger.info(f"   ❌ Fehler: {self.stats['error_records']:,}")
        
        if not df.empty:
            self.logger.info(f"   📊 DataFrame: {len(df):,} Zeilen, {len(df.columns)} Spalten")
        
        return df

    def parse_file(self, file_path: Union[str, Path], max_records: Optional[int] = None) -> pd.DataFrame:
        """
        Parsed eine MAB2-Datei und gibt einen DataFrame zurück
        
        Args:
            file_path: Pfad zur MAB2-Datei
            max_records: Maximale Anzahl Records (None = alle)
            
        Returns:
            DataFrame mit bibliographischen Daten
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"MAB2-Datei nicht gefunden: {file_path}")
        
        self.logger.info(f"🔄 Lade MAB2-Datei: {file_path}")
        self.logger.info(f"📊 Encoding: {self.encoding}")
        
        try:
            with open(file_path, 'r', encoding=self.encoding, errors='replace') as file:
                content = file.read()
            
            return self.parse_content(content, max_records)
            
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Lesen der Datei: {str(e)}")
            raise
    
    def _split_records(self, content: str) -> List[str]:
        """
        Teilt den MAB2-Content in einzelne Records auf.
        
        Unterstützt beide MAB2-Formate:
        - Records mit "### " am Anfang
        - Records mit "^" am Zeilenanfang
        
        Args:
            content: MAB2-formatierter String
            
        Returns:
            Liste der einzelnen Records als Strings
        """
        try:
            # Normalisiere Zeilenumbrüche
            content = content.replace('\r\n', '\n').replace('\r', '\n')
            
            # Prüfe Format anhand der ersten nicht-leeren Zeile
            first_line = next((line for line in content.split('\n') if line.strip()), '')
            
            if first_line.startswith('### '):
                # Format mit "### " als Record-Beginn
                records = []
                current_record = []
                
                for line in content.split('\n'):
                    if line.startswith('### '):
                        if current_record:
                            record_content = '\n'.join(current_record)
                            if record_content.strip():
                                records.append(record_content)
                        current_record = [line]
                    elif current_record:
                        current_record.append(line)
                    elif line.strip():
                        if self.debug_mode:
                            self.logger.warning(f"⚠️  Ungültige Zeile ignoriert: {line[:50]}...")
                
                # Letzten Record hinzufügen
                if current_record:
                    record_content = '\n'.join(current_record)
                    if record_content.strip():
                        records.append(record_content)
                        
            else:
                # Format mit "^" als Record-Beginn
                records = [r.strip() for r in content.split('\n^') if r.strip()]
                # Füge ^ wieder an Records an (außer beim ersten)
                records = [records[0]] + ['^' + r for r in records[1:]]
                        
            if self.debug_mode:
                self.logger.info(f"📊 Records gefunden: {len(records):,}")
                if records:
                    self.logger.debug(f"📝 Beispiel-Record:\n{records[0][:200]}...")
            
            return records
            
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Aufteilen der Records: {str(e)}")
            return []
    
    def _parse_record(self, raw_record: str) -> Optional[MAB2Record]:
        """
        Parsed einen einzelnen MAB2-Record.
        
        Unterstützt:
        - Numerische Felder (001, 100, etc.)
        - Unterfelder (a, b, etc.)
        - Mehrfachfelder (gleiche Nummer mehrfach)
        - Fortsetzungszeilen
        
        Args:
            raw_record: String mit einem MAB2-Record
            
        Returns:
            MAB2Record Objekt oder None bei Fehler
        """
        try:
            # Record vorbereiten
            raw_record = raw_record.replace('\r\n', '\n').replace('\r', '\n')
            lines = raw_record.split('\n')
            
            if not lines:
                if self.debug_mode:
                    self.logger.warning("⚠️  Leerer Record gefunden")
                return None
                
            # Record erstellen
            record = MAB2Record(
                record_id="",  # Wird später gesetzt
                fields={},
                raw_data=raw_record
            )
            
            # Erste Zeile verarbeiten (enthält Record-ID)
            first_line = lines[0].strip()
            
            if first_line.startswith('### '):
                first_line = first_line[4:].strip()
            elif first_line.startswith('^'):
                first_line = first_line[1:].strip()
                
            # Record-ID extrahieren
            id_match = re.search(r'(\d+)', first_line)
            record.record_id = id_match.group(1) if id_match else first_line.strip()
            
            # Parse Felder
            current_field = None
            current_content = []
            
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # Neue Feldzeile?
                    is_new_field = False
                    
                    # Prüfe auf Feldanfang (^ oder Leerzeichen + 3 Ziffern)
                    if line.startswith('^'):
                        line = line[1:]
                        is_new_field = True
                    elif len(line) >= 3 and line[:3].isdigit():
                        is_new_field = True
                        
                    if is_new_field:
                        # Speichere vorheriges Feld wenn vorhanden
                        if current_field and current_content:
                            content = ' '.join(c for c in current_content if c)
                            if current_field in record.fields:
                                # Bei Mehrfachfeld: Liste erstellen
                                if isinstance(record.fields[current_field], list):
                                    record.fields[current_field].append(content)
                                else:
                                    record.fields[current_field] = [record.fields[current_field], content]
                            else:
                                record.fields[current_field] = content
                        
                        # Neues Feld beginnt
                        field_code = line[:3]  # Basis-Feldcode
                        field_content = line[3:].strip()
                        
                        # Handle Subfeldkennungen (z.B. 331a)
                        if len(line) > 3 and line[3].isalpha():
                            field_content = line[4:].strip()
                            
                        current_field = field_code
                        current_content = [field_content] if field_content else []
                        
                        # Statistik
                        if field_code not in self.stats['field_counts']:
                            self.stats['field_counts'][field_code] = 0
                        self.stats['field_counts'][field_code] += 1
                        
                    else:
                        # Fortsetzungszeile
                        if current_field:
                            current_content.append(line)
                            
                except Exception as e:
                    msg = f"Fehler beim Parsen der Zeile: {str(e)}"
                    if self.debug_mode:
                        self.logger.warning(f"⚠️  {msg}")
                    record.errors.append(msg)
                    
            # Letztes Feld speichern
            if current_field and current_content:
                content = ' '.join(c for c in current_content if c)
                if current_field in record.fields:
                    if isinstance(record.fields[current_field], list):
                        record.fields[current_field].append(content)
                    else:
                        record.fields[current_field] = [record.fields[current_field], content]
                else:
                    record.fields[current_field] = content
            
            # Validiere Record
            if not record.fields:
                if self.debug_mode:
                    self.logger.warning(f"⚠️  Keine Felder gefunden in Record {record.record_id}")
                return None
                
            return record
            
        except Exception as e:
            msg = f"Kritischer Fehler beim Record-Parsing: {str(e)}"
            if self.debug_mode:
                self.logger.error(f"❌ {msg}")
            return None
    
    def _extract_bibliographic_data(self, record: MAB2Record) -> Optional[Dict]:
        """Extrahiert standardisierte bibliographische Daten aus einem MAB2-Record"""
        
        # Basis-Daten
        bib_data = {
            'id': record.record_id,
            'source': 'ub_tubaf_mab2',
            'title': None,
            'authors': [],
            'authors_str': None,
            'year': None,
            'isbn': None,
            'place': None,
            'physical_desc': None,
            'original_fields': {}  # Debug-Info
        }
        
        # Speichere Original-Felder für Debug
        bib_data['original_fields'] = record.fields.copy()
        
        # Titel extrahieren (310 ist Haupttitel, 331 Alternative)
        title_candidates = []
        for field_code in ['310', '331', '359']:  # Haupt-, Alt-Titel, Untertitel
            if field_code in record.fields:
                title_text = record.fields[field_code].strip()
                if title_text:
                    # Bereinige spezielle Formatierungen
                    title_text = re.sub(r'\$[a-z]', ' ', title_text)  # Entferne $a, $b etc.
                    title_text = re.sub(r'¬\[.*?\]¬', '', title_text)  # Entferne [Brackets]
                    title_text = re.sub(r'\s+', ' ', title_text).strip()  # Normalisiere Whitespace
                    title_candidates.append(title_text)
                    
        if title_candidates:
            # Für Debug: Speichere alle Kandidaten
            bib_data['title_candidates'] = title_candidates
            # Haupttitel + evtl. Untertitel
            bib_data['title'] = ' : '.join(title_candidates[:2])
        
        # Autoren sammeln
        authors = []
        for field_code in ['100', '200']:  # Haupt- und Nebenautoren
            if field_code in record.fields:
                author_text = record.fields[field_code].strip()
                if author_text:
                    # Bereinige Autorennamen
                    author_text = re.sub(r'\$[a-z]', ' ', author_text)
                    author_text = re.sub(r'¬\[.*?\]¬', '', author_text)
                    author_text = re.sub(r'\[.*?\]', '', author_text)
                    author_text = re.sub(r'\s+', ' ', author_text).strip()
                    if author_text:
                        authors.append(author_text)
        
        if authors:
            bib_data['authors'] = authors
            bib_data['authors_str'] = ' ; '.join(authors)
        
        # Jahr extrahieren
        if '425' in record.fields:
            year_str = record.fields['425']
            # Extrahiere 4-stellige Jahreszahl, auch mit möglichen Präfixen/Suffixen
            year_match = re.search(r'(?:^|[^\d])([12][0-9]{3})(?:[^\d]|$)', year_str)
            if year_match:
                try:
                    year = int(year_match.group(1))
                    if 1400 <= year <= 2100:  # Validiere Jahresbereich
                        bib_data['year'] = year
                except ValueError:
                    pass
            
            # Für Debug: Speichere Original
            bib_data['year_original'] = year_str
        
        # ISBN extrahieren und validieren
        isbn_candidates = []
        for field_code in ['010', '540', '013k']:
            if field_code in record.fields:
                isbn_text = record.fields[field_code].strip()
                if isbn_text:
                    # Extrahiere ISBN mit oder ohne Präfix
                    isbn_match = re.search(r'(?:ISBN[- ]*)?([\dX\-]+)', isbn_text)
                    if isbn_match:
                        isbn = re.sub(r'[^\dX]', '', isbn_match.group(1))
                        if len(isbn) in [10, 13]:  # Validiere Länge
                            isbn_candidates.append(isbn)
                    
        if isbn_candidates:
            bib_data['isbn'] = isbn_candidates[0]  # Nimm die erste valide ISBN
            # Für Debug: Speichere alle Kandidaten
            bib_data['isbn_candidates'] = isbn_candidates
        
        # Erscheinungsort
        if '410' in record.fields:
            place_text = record.fields['410'].strip()
            if place_text:
                bib_data['place'] = place_text
        
        # Physische Beschreibung
        if '433' in record.fields:
            phys_text = record.fields['433'].strip()
            if phys_text:
                bib_data['physical_desc'] = phys_text
        
        # Gebe Record zurück wenn mindestens ein wichtiges Feld vorhanden ist
        if (bib_data['title'] or bib_data['authors'] or 
            bib_data['isbn'] or bib_data['year']):
            return bib_data
            
        # Für Debug-Zwecke
        self.logger.warning(f"⚠️  Record ohne Kernfelder: ID={record.record_id}")
        return None
    
    def get_field_statistics(self) -> Dict:
        """Gibt Statistiken über die gefundenen MAB-Felder zurück"""
        return {
            'parsing_stats': {
                'total_records': self.stats['total_records'],
                'parsed_records': self.stats['parsed_records'],
                'error_records': self.stats['error_records'],
                'success_rate': self.stats['parsed_records'] / max(self.stats['total_records'], 1)
            },
            'field_frequencies': dict(sorted(
                self.stats['field_counts'].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:20])  # Top 20 Felder
        }

def analyze_mab2_data(df: pd.DataFrame, logger: Optional[logging.Logger] = None) -> None:
    """
    Analysiert die geparsten MAB2-Daten und gibt eine Übersicht aus
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info(f"\n📊 === MAB2 DATENANALYSE ===")
    logger.info(f"📋 Datensatz: {len(df):,} Records")
    
    if df.empty:
        logger.warning("⚠️  Leerer Datensatz!")
        return
    
    # Vollständigkeit-Analyse
    logger.info(f"\n🔍 === VOLLSTÄNDIGKEITS-ANALYSE ===")
    
    title_count = df['title'].notna().sum()
    author_count = df['authors_str'].notna().sum()
    year_count = df['year'].notna().sum()
    isbn_count = df['isbn'].notna().sum()
    
    logger.info(f"📖 Records mit Titel: {title_count:,} ({title_count/len(df)*100:.1f}%)")
    logger.info(f"✍️  Records mit Autor: {author_count:,} ({author_count/len(df)*100:.1f}%)")
    logger.info(f"📅 Records mit Jahr: {year_count:,} ({year_count/len(df)*100:.1f}%)")
    logger.info(f"📚 Records mit ISBN: {isbn_count:,} ({isbn_count/len(df)*100:.1f}%)")
    
    # Jahres-Verteilung
    if year_count > 0:
        year_stats = df['year'].describe()
        logger.info(f"\n📅 === JAHRES-VERTEILUNG ===")
        logger.info(f"Ältestes Jahr: {year_stats['min']}")
        logger.info(f"Neuestes Jahr: {year_stats['max']}")
        logger.info(f"Durchschnitt: {year_stats['mean']:.1f}")
        
    # Top Autoren
    if author_count > 0:
        logger.info(f"\n✍️  === TOP 5 AUTOREN ===")
        author_counts = df[df['authors_str'].notna()]['authors_str'].value_counts().head(5)
        for author, count in author_counts.items():
            logger.info(f"   {author}: {count:,} Records")

def get_sample_records_mab2(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Gibt eine Stichprobe von MAB2-Records für Anzeigezwecke zurück"""
    if df.empty:
        return df
        
    sample = df.head(n).copy()
    
    # Kürze lange Felder für bessere Darstellung
    display_columns = ['id', 'title', 'authors_str', 'year', 'isbn', 'place']
    sample_display = sample[display_columns].copy()
    
    # Titel kürzen falls zu lang
    if 'title' in sample_display.columns:
        sample_display['title'] = sample_display['title'].apply(
            lambda x: x[:50] + "..." if pd.notna(x) and len(str(x)) > 50 else x
        )
    
    return sample_display