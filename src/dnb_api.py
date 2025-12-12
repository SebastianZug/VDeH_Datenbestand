"""
DNB API Client für bibliografische Metadaten-Abfragen.

Deutsche Nationalbibliothek SRU API Client mit ISBN/ISSN-basierter Suche.
Inkl. automatischer Retry-Logik mit Exponential Backoff.
"""

import requests
import xml.etree.ElementTree as ET
from typing import Dict, Optional, Callable
import re
import logging
import time

# Configure logger for this module
logger = logging.getLogger(__name__)


def _retry_with_backoff(func: Callable, max_retries: int = 3, base_delay: float = 2.0, query_desc: str = "query") -> Optional[Dict]:
    """
    Führt eine Funktion mit Exponential Backoff bei Fehlern aus.

    Args:
        func: Funktion, die ausgeführt werden soll (ohne Parameter)
        max_retries: Maximale Anzahl an Versuchen
        base_delay: Basis-Verzögerung in Sekunden für Backoff
        query_desc: Beschreibung der Query für Logging

    Returns:
        Ergebnis der Funktion oder None bei dauerhaftem Fehler
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            result = func()

            # Erfolg beim ersten Versuch
            if attempt == 0:
                return result

            # Erfolg nach Retry
            logger.info(f"Query '{query_desc}' erfolgreich nach {attempt + 1} Versuchen")
            return result

        except Exception as e:
            last_exception = e

            # Letzter Versuch fehlgeschlagen
            if attempt >= max_retries - 1:
                logger.error(f"Query '{query_desc}' fehlgeschlagen nach {max_retries} Versuchen: {str(e)}")
                return None

            # Exponential Backoff
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Query '{query_desc}' Versuch {attempt + 1}/{max_retries} fehlgeschlagen: {str(e)[:100]}. Retry in {delay}s...")
            time.sleep(delay)

    return None


# DNB SRU API Basis-URL
DNB_SRU_BASE = "https://services.dnb.de/sru/dnb"

# XML Namespaces for MARC21
MARC_NAMESPACES = {
    'srw': 'http://www.loc.gov/zing/srw/',
    'marc': 'http://www.loc.gov/MARC21/slim'
}


def _query_dnb_sru(query: str, max_records: int = 1, identifier_type: str = None, identifier_value: str = None) -> Optional[Dict]:
    """
    Internal helper to query DNB SRU API and parse MARC21 response.

    Args:
        query: SRU query string
        max_records: Maximum number of records to retrieve
        identifier_type: Type of identifier ('isbn', 'issn', or None)
        identifier_value: Value of identifier (cleaned)

    Returns:
        Dict with metadata or None on error/not found
    """
    try:
        params = {
            'version': '1.1',
            'operation': 'searchRetrieve',
            'query': query,
            'recordSchema': 'MARC21-xml',
            'maximumRecords': max_records
        }

        response = requests.get(DNB_SRU_BASE, params=params, timeout=10)

        if response.status_code != 200:
            return None

        # Parse XML Response
        root = ET.fromstring(response.content)

        # Extract first record
        record = root.find('.//srw:recordData/marc:record', MARC_NAMESPACES)
        if record is None:
            return None

        # Initialize metadata
        metadata = {
            'title': None,
            'authors': [],
            'year': None,
            'publisher': None,
            'isbn': None,
            'issn': None,
            'pages': None
        }

        # Add identifier if provided (from query parameter)
        if identifier_type and identifier_value:
            metadata[identifier_type] = identifier_value

        # Parse MARC21 fields
        for datafield in record.findall('marc:datafield', MARC_NAMESPACES):
            tag = datafield.get('tag')

            # ISBN (020)
            if tag == '020' and not metadata.get('isbn'):
                subfields = datafield.findall('marc:subfield[@code="a"]', MARC_NAMESPACES)
                if subfields and subfields[0].text:
                    # Extract ISBN (may contain additional text like binding info)
                    isbn_text = subfields[0].text.strip()
                    # Clean: remove everything after space or parenthesis
                    isbn_clean = re.split(r'[\s(]', isbn_text)[0]
                    # Remove hyphens for normalized storage
                    isbn_clean = isbn_clean.replace('-', '')
                    # Validate basic ISBN format (10 or 13 digits)
                    if re.match(r'^\d{10}(\d{3})?$', isbn_clean):
                        metadata['isbn'] = isbn_clean

            # ISSN (022)
            elif tag == '022' and not metadata.get('issn'):
                subfields = datafield.findall('marc:subfield[@code="a"]', MARC_NAMESPACES)
                if subfields and subfields[0].text:
                    issn_text = subfields[0].text.strip()
                    # Clean: remove everything after space
                    issn_clean = re.split(r'\s', issn_text)[0]
                    # Remove hyphens for normalized storage
                    issn_clean = issn_clean.replace('-', '')
                    # Validate basic ISSN format (8 digits)
                    if re.match(r'^\d{7}[\dXx]$', issn_clean):
                        metadata['issn'] = issn_clean.upper()

            # Title (245)
            elif tag == '245':
                subfields = datafield.findall('marc:subfield[@code="a"]', MARC_NAMESPACES)
                if subfields:
                    metadata['title'] = subfields[0].text

            # Authors (100, 700, 110, 710)
            # 100/700 = Persons, 110/710 = Corporate bodies
            elif tag in ['100', '700', '110', '710']:
                subfields = datafield.findall('marc:subfield[@code="a"]', MARC_NAMESPACES)
                for sf in subfields:
                    if sf.text:
                        author_name = sf.text.strip()
                        if author_name and author_name not in metadata['authors']:  # Avoid duplicates
                            metadata['authors'].append(author_name)

            # Year AND Publisher (264 or 260)
            elif tag in ['264', '260']:
                # Year from subfield 'c'
                subfields_year = datafield.findall('marc:subfield[@code="c"]', MARC_NAMESPACES)
                if subfields_year and subfields_year[0].text:
                    year_text = subfields_year[0].text
                    # Extract 4-digit year
                    year_match = re.search(r'\b(1[89]\d{2}|20\d{2})\b', year_text)
                    if year_match:
                        metadata['year'] = int(year_match.group(1))

                # Publisher from subfield 'b'
                subfields_publisher = datafield.findall('marc:subfield[@code="b"]', MARC_NAMESPACES)
                if subfields_publisher and subfields_publisher[0].text:
                    metadata['publisher'] = subfields_publisher[0].text

            # Pages (300 - Physical Description)
            elif tag == '300':
                # Pages from subfield 'a' (e.g., "188 S.", "XV, 250 p.")
                subfields_pages = datafield.findall('marc:subfield[@code="a"]', MARC_NAMESPACES)
                if subfields_pages and subfields_pages[0].text:
                    metadata['pages'] = subfields_pages[0].text.strip()

        return metadata

    except Exception as e:
        logger.warning(f"DNB query error for '{query}': {str(e)}")
        return None


def query_dnb_by_isbn(isbn: str, max_records: int = 1, max_retries: int = 3) -> Optional[Dict]:
    """
    Fragt DNB API mit ISBN ab (mit automatischer Retry-Logik).

    Args:
        isbn: ISBN-Nummer (mit oder ohne Bindestriche)
        max_records: Max. Anzahl Ergebnisse
        max_retries: Maximale Anzahl an Retry-Versuchen bei Fehlern (default: 3)

    Returns:
        Dict mit Metadaten oder None bei Fehler/Nicht-Gefunden

    Example:
        >>> data = query_dnb_by_isbn('978-3-16-148410-0')
        >>> if data:
        ...     print(data['title'])
    """
    # ISBN bereinigen
    isbn_clean = isbn.replace('-', '').replace(' ', '')

    # SRU Query erstellen
    query = f'isbn={isbn_clean}'

    # Query mit Retry-Logik ausführen
    return _retry_with_backoff(
        func=lambda: _query_dnb_sru(query, max_records, identifier_type='isbn', identifier_value=isbn_clean),
        max_retries=max_retries,
        query_desc=f"ISBN {isbn_clean}"
    )


def query_dnb_by_issn(issn: str, max_records: int = 1, max_retries: int = 3) -> Optional[Dict]:
    """
    Fragt DNB API mit ISSN ab (mit automatischer Retry-Logik).

    Args:
        issn: ISSN-Nummer (mit oder ohne Bindestriche)
        max_records: Max. Anzahl Ergebnisse
        max_retries: Maximale Anzahl an Retry-Versuchen bei Fehlern (default: 3)

    Returns:
        Dict mit Metadaten oder None bei Fehler/Nicht-Gefunden

    Example:
        >>> data = query_dnb_by_issn('0028-0836')
        >>> if data:
        ...     print(data['title'])
    """
    # ISSN bereinigen
    issn_clean = issn.replace('-', '').replace(' ', '')

    # SRU Query
    query = f'issn={issn_clean}'

    # Query mit Retry-Logik ausführen
    return _retry_with_backoff(
        func=lambda: _query_dnb_sru(query, max_records, identifier_type='issn', identifier_value=issn_clean),
        max_retries=max_retries,
        query_desc=f"ISSN {issn_clean}"
    )


def query_dnb_by_title_author(title: str, author: str = None, max_records: int = 1, max_retries: int = 3) -> Optional[Dict]:
    """
    Fragt DNB API mit Titel und optional Autor ab (mit automatischer Retry-Logik).

    Verwendet eine mehrstufige Suchstrategie:
    1. Titel + Autor (wenn Autor vorhanden)
    2. Nur Titel (Fallback)

    Args:
        title: Titel des Werks
        author: Autor (optional, verbessert die Präzision)
        max_records: Max. Anzahl Ergebnisse
        max_retries: Maximale Anzahl an Retry-Versuchen bei Fehlern (default: 3)

    Returns:
        Dict mit Metadaten oder None bei Fehler/Nicht-Gefunden

    Example:
        >>> data = query_dnb_by_title_author('Faust', 'Goethe')
        >>> if data:
        ...     print(data['title'])
    """
    # Bereinige Titel von Sonderzeichen
    title_clean = title.replace('¬', '').strip()

    # Erstelle eine Funktion, die alle Suchstrategien durchläuft
    def _try_all_strategies():
        # Strategie 1: Titel + Autor (wenn vorhanden)
        if author:
            # Extrahiere nur ersten Autor und nur Nachname
            # Format kann sein: "Nachname, Vorname" oder "Nachname"
            first_author = author.split('|')[0].split(';')[0].strip()
            # Nehme nur Text vor dem Komma (Nachname)
            author_lastname = first_author.split(',')[0].strip()

            # Versuche mit Autor
            query = f'tit="{title_clean}" and per={author_lastname}'
            result = _query_dnb_sru(query, max_records)

            if result:
                return result

            # Fallback: Titel ohne Anführungszeichen + Autor
            query = f'tit={title_clean} and per={author_lastname}'
            result = _query_dnb_sru(query, max_records)

            if result:
                return result

        # Strategie 2: Nur Titel (Fallback wenn Autor fehlschlägt oder nicht vorhanden)
        # Verwende Phrasensuche mit Anführungszeichen für bessere Präzision
        query = f'tit="{title_clean}"'
        result = _query_dnb_sru(query, max_records)

        if result:
            return result

        # Strategie 3: Titel ohne Anführungszeichen (größere Toleranz)
        query = f'tit={title_clean}'
        return _query_dnb_sru(query, max_records)

    # Query mit Retry-Logik ausführen
    query_desc = f"Title/Author '{title_clean[:50]}'"
    if author:
        query_desc += f" / {author.split('|')[0].split(';')[0].strip()[:30]}"

    return _retry_with_backoff(
        func=_try_all_strategies,
        max_retries=max_retries,
        query_desc=query_desc
    )


def query_dnb_by_title_year(title: str, year: int, max_records: int = 1, max_retries: int = 3) -> Optional[Dict]:
    """
    Fragt DNB API mit Titel und Jahr ab (mit automatischer Retry-Logik).

    Neue Suchmethode für Records ohne ISBN/ISSN aber mit Titel und Jahr.
    Verwendet eine mehrstufige Suchstrategie mit verschiedenen Jahr-Toleranzen.

    Args:
        title: Titel des Werks
        year: Erscheinungsjahr (4-stellig)
        max_records: Max. Anzahl Ergebnisse
        max_retries: Maximale Anzahl an Retry-Versuchen bei Fehlern

    Returns:
        Dict mit Metadaten oder None bei Fehler/Nicht-Gefunden

    Example:
        >>> data = query_dnb_by_title_year('Die Verwandlung', 1915)
        >>> if data:
        ...     print(data['title'])
    """
    # Titel bereinigen
    title_clean = title.replace('¬', '').strip()

    # Jahr validieren
    if not isinstance(year, (int, float)) or year < 1000 or year > 2100:
        return None

    year_int = int(year)

    # Erstelle eine Funktion, die alle Suchstrategien durchläuft
    def _try_all_strategies():
        # Strategie 1: Exakter Titel (mit Anführungszeichen) + exaktes Jahr
        query = f'tit="{title_clean}" and jhr={year_int}'
        result = _query_dnb_sru(query, max_records)
        if result:
            return result

        # Strategie 2: Titel ohne Anführungszeichen + exaktes Jahr (breitere Suche)
        query = f'tit={title_clean} and jhr={year_int}'
        result = _query_dnb_sru(query, max_records)
        if result:
            return result

        # Strategie 3: Exakter Titel + Jahr-Range ±1 (für Publikationsvarianten)
        # Beispiel: Erstauflage 1915, Neuauflage 1916
        query = f'tit="{title_clean}" and jhr>={year_int-1} and jhr<={year_int+1}'
        result = _query_dnb_sru(query, max_records)
        if result:
            return result

        # Strategie 4: Titel ohne Anführungszeichen + Jahr-Range ±1
        query = f'tit={title_clean} and jhr>={year_int-1} and jhr<={year_int+1}'
        return _query_dnb_sru(query, max_records)

    # Query mit Retry-Logik ausführen
    return _retry_with_backoff(
        func=_try_all_strategies,
        max_retries=max_retries,
        query_desc=f"Title/Year: '{title_clean[:40]}...' ({year_int})"
    )
