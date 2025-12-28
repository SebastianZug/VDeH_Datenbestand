"""
Library of Congress (LoC) API Client für bibliografische Metadaten-Abfragen.

LoC SRU API Client mit ISBN/ISSN-basierter Suche.
Inkl. automatischer Retry-Logik mit Exponential Backoff.
"""

import requests
import xml.etree.ElementTree as ET
from typing import Dict, Optional, Callable
import re
import logging
import time
import unicodedata

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
                logger.warning(f"Query '{query_desc}' fehlgeschlagen nach {max_retries} Versuchen")
                return None

            # Exponential Backoff
            delay = base_delay * (2 ** attempt)
            logger.debug(f"Query '{query_desc}' Versuch {attempt + 1}/{max_retries} fehlgeschlagen. Retry in {delay}s...")
            time.sleep(delay)

    return None


# Library of Congress SRU API Basis-URL
# Note: Using HTTP instead of HTTPS to avoid SSL issues with port 210
LOC_SRU_BASE = "http://lx2.loc.gov:210/lcdb"

# XML Namespaces for MARC21
MARC_NAMESPACES = {
    'srw': 'http://www.loc.gov/zing/srw/',
    'marc': 'http://www.loc.gov/MARC21/slim'
}


def _normalize_for_search(text: str) -> str:
    """
    Normalisiert Text für tolerantere LoC-Suche.

    Behandelt häufige Fehlerquellen:
    - Akzente/Umlaute: "über" → "uber"
    - Sonderzeichen: entfernt oder durch Leerzeichen ersetzt
    - Mehrfache Leerzeichen: reduziert

    Args:
        text: Zu normalisierender Text

    Returns:
        Normalisierter Text für LoC-Suche

    Examples:
        >>> _normalize_for_search("Über die Prüfung von Stählen")
        'Uber die Prufung von Stahlen'
        >>> _normalize_for_search("C++ Programmierung")
        'C Programmierung'
    """
    if not text:
        return ""

    # Unicode-Normalisierung: NFKD zerlegt Zeichen mit Akzenten
    text = unicodedata.normalize('NFKD', text)

    # Entferne alle Non-ASCII Zeichen (inkl. Akzente)
    text = text.encode('ASCII', 'ignore').decode('ASCII')

    # Sonderzeichen durch Leerzeichen ersetzen
    text = re.sub(r'[^\w\s]', ' ', text)

    # Mehrfache Leerzeichen reduzieren
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def _query_loc_sru(query: str, max_records: int = 1, identifier_type: str = None, identifier_value: str = None) -> Optional[Dict]:
    """
    Internal helper to query LoC SRU API and parse MARC21 response.

    Args:
        query: SRU query string (CQL format)
        max_records: Maximum number of records to retrieve
        identifier_type: Type of identifier ('isbn', 'issn', or None)
        identifier_value: Value of identifier (cleaned)

    Returns:
        Dict with metadata or None on error/not found
    """
    try:
        # Rate limiting: Wait before making the request
        # This ensures minimum delay between ALL requests (including retries)
        # Using 3 seconds to be more conservative with the LoC server
        time.sleep(3.0)  # Base delay between any API calls (increased from 2.0)

        params = {
            'version': '1.1',
            'operation': 'searchRetrieve',
            'query': query,
            'recordSchema': 'marcxml',
            'maximumRecords': max_records
        }

        # Use longer timeout and set connection close to avoid connection pool issues
        # HTTP connection (no SSL)
        # Add User-Agent to avoid being blocked
        headers = {
            'Connection': 'close',
            'User-Agent': 'Python-LoC-Client/1.0 (Research; mailto:research@example.com)'
        }
        response = requests.get(LOC_SRU_BASE, params=params, timeout=30, headers=headers)

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
            elif tag in ['100', '700', '110', '710']:
                subfields = datafield.findall('marc:subfield[@code="a"]', MARC_NAMESPACES)
                for sf in subfields:
                    if sf.text:
                        author_name = sf.text.strip()
                        if author_name and author_name not in metadata['authors']:
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
                subfields_pages = datafield.findall('marc:subfield[@code="a"]', MARC_NAMESPACES)
                if subfields_pages and subfields_pages[0].text:
                    metadata['pages'] = subfields_pages[0].text.strip()

        return metadata

    except Exception as e:
        # Only log at DEBUG level - retry logic will handle this
        logger.debug(f"LoC query error for '{query}': {str(e)}")
        return None


def query_loc_by_isbn(isbn: str, max_records: int = 1, max_retries: int = 3) -> Optional[Dict]:
    """
    Fragt LoC API mit ISBN ab (mit automatischer Retry-Logik).

    Args:
        isbn: ISBN-Nummer (mit oder ohne Bindestriche)
        max_records: Max. Anzahl Ergebnisse
        max_retries: Maximale Anzahl an Retry-Versuchen bei Fehlern

    Returns:
        Dict mit Metadaten oder None bei Fehler/Nicht-Gefunden

    Example:
        >>> data = query_loc_by_isbn('978-3-16-148410-0')
        >>> if data:
        ...     print(data['title'])
    """
    # ISBN bereinigen
    isbn_clean = isbn.replace('-', '').replace(' ', '')

    # SRU Query erstellen (CQL format for LoC)
    query = f'bath.isbn={isbn_clean}'

    # Query mit Retry-Logik ausführen
    return _retry_with_backoff(
        func=lambda: _query_loc_sru(query, max_records, identifier_type='isbn', identifier_value=isbn_clean),
        max_retries=max_retries,
        query_desc=f"ISBN {isbn_clean}"
    )


def query_loc_by_issn(issn: str, max_records: int = 1, max_retries: int = 3) -> Optional[Dict]:
    """
    Fragt LoC API mit ISSN ab (mit automatischer Retry-Logik).

    Args:
        issn: ISSN-Nummer (mit oder ohne Bindestriche)
        max_records: Max. Anzahl Ergebnisse
        max_retries: Maximale Anzahl an Retry-Versuchen bei Fehlern

    Returns:
        Dict mit Metadaten oder None bei Fehler/Nicht-Gefunden

    Example:
        >>> data = query_loc_by_issn('0028-0836')
        >>> if data:
        ...     print(data['title'])
    """
    # ISSN bereinigen
    issn_clean = issn.replace('-', '').replace(' ', '')

    # SRU Query (CQL format)
    query = f'bath.issn={issn_clean}'

    # Query mit Retry-Logik ausführen
    return _retry_with_backoff(
        func=lambda: _query_loc_sru(query, max_records, identifier_type='issn', identifier_value=issn_clean),
        max_retries=max_retries,
        query_desc=f"ISSN {issn_clean}"
    )


def query_loc_by_title_author(title: str, author: str = None, max_records: int = 1, max_retries: int = 3) -> Optional[Dict]:
    """
    Fragt LoC API mit Titel und optional Autor ab (mit automatischer Retry-Logik).

    Verwendet eine mehrstufige Suchstrategie mit Normalisierung:
    1. Titel + Autor (Phrase)
    2. Titel + Autor (Wörter, normalisiert)
    3. Nur Titel (Phrase)
    4. Nur Titel (Wörter, normalisiert)

    Args:
        title: Titel des Werks
        author: Autor (optional, verbessert die Präzision)
        max_records: Max. Anzahl Ergebnisse
        max_retries: Maximale Anzahl an Retry-Versuchen bei Fehlern

    Returns:
        Dict mit Metadaten oder None bei Fehler/Nicht-Gefunden

    Example:
        >>> data = query_loc_by_title_author('Moby Dick', 'Melville')
        >>> if data:
        ...     print(data['title'])
    """
    # Bereinige Titel
    title_clean = title.replace('¬', '').strip()
    title_normalized = _normalize_for_search(title_clean)

    # Truncated Version für lange Titel
    title_truncated = None
    if len(title_clean) > 60:
        title_truncated = title_clean[:60].rsplit(' ', 1)[0].strip()

    # Vereinfachte Suchstrategie mit nur 1-2 Versuchen pro Titel
    # Um Server-Überlastung zu vermeiden
    def _try_all_strategies():
        # Autor vorbereiten wenn vorhanden
        author_lastname = None
        if author:
            # Extrahiere nur ersten Autor und nur Nachname
            first_author = author.split('|')[0].split(';')[0].strip()
            author_lastname = first_author.split(',')[0].strip()

        # Strategie 1: Normalisierter Titel + Autor (wenn vorhanden)
        if author_lastname:
            query = f'dc.title={title_normalized} and dc.creator={author_lastname}'
            result = _query_loc_sru(query, max_records)
            if result:
                logger.info(f"Match via title+author: '{title_normalized[:40]}...'")
                return result

        # Strategie 2: Nur normalisierter Titel (Fallback)
        query = f'dc.title={title_normalized}'
        result = _query_loc_sru(query, max_records)
        if result:
            logger.info(f"Match via title only: '{title_normalized[:40]}...'")
            return result

        return None

    # Query mit Retry-Logik ausführen
    query_desc = f"Title/Author '{title_clean[:50]}'"
    if author:
        query_desc += f" / {author.split('|')[0].split(';')[0].strip()[:30]}"

    return _retry_with_backoff(
        func=_try_all_strategies,
        max_retries=max_retries,
        query_desc=query_desc
    )


def query_loc_by_title_year(title: str, year: int, max_records: int = 1, max_retries: int = 3) -> Optional[Dict]:
    """
    Fragt LoC API mit Titel und Jahr ab (mit automatischer Retry-Logik).

    Suchmethode für Records ohne ISBN/ISSN aber mit Titel und Jahr.
    Verwendet eine erweiterte Suchstrategie mit Normalisierung und Jahr-Toleranzen.

    Args:
        title: Titel des Werks
        year: Erscheinungsjahr (4-stellig)
        max_records: Max. Anzahl Ergebnisse
        max_retries: Maximale Anzahl an Retry-Versuchen bei Fehlern

    Returns:
        Dict mit Metadaten oder None bei Fehler/Nicht-Gefunden

    Example:
        >>> data = query_loc_by_title_year('The Great Gatsby', 1925)
        >>> if data:
        ...     print(data['title'])
    """
    # Titel bereinigen
    title_clean = title.replace('¬', '').strip()
    title_normalized = _normalize_for_search(title_clean)

    # Truncated Version für lange Titel
    title_truncated = None
    if len(title_clean) > 60:
        title_truncated = title_clean[:60].rsplit(' ', 1)[0].strip()

    # Jahr validieren
    if not isinstance(year, (int, float)) or year < 1000 or year > 2100:
        return None

    year_int = int(year)

    # Vereinfachte Suchstrategie - nur 1 Versuch pro Titel/Jahr
    # Um Server-Überlastung zu vermeiden
    def _try_all_strategies():
        # Nur normalisierter Titel + exaktes Jahr
        query = f'dc.title={title_normalized} and dc.date={year_int}'
        result = _query_loc_sru(query, max_records)
        if result:
            logger.info(f"TY match: '{title_normalized[:40]}...' ({year_int})")
            return result

        return None

    # Query mit Retry-Logik ausführen
    return _retry_with_backoff(
        func=_try_all_strategies,
        max_retries=max_retries,
        query_desc=f"Title/Year: '{title_clean[:40]}...' ({year_int})"
    )
