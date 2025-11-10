"""
DNB API Client für bibliografische Metadaten-Abfragen.

Deutsche Nationalbibliothek SRU API Client mit ISBN/ISSN-basierter Suche.
"""

import requests
import xml.etree.ElementTree as ET
from typing import Dict, Optional
import re


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
            'publisher': None
        }

        # Add identifier if provided
        if identifier_type and identifier_value:
            metadata[identifier_type] = identifier_value

        # Parse MARC21 fields
        for datafield in record.findall('marc:datafield', MARC_NAMESPACES):
            tag = datafield.get('tag')

            # Title (245)
            if tag == '245':
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

        return metadata

    except Exception as e:
        print(f"   ⚠️ DNB query error for '{query}': {str(e)}")
        return None


def query_dnb_by_isbn(isbn: str, max_records: int = 1) -> Optional[Dict]:
    """
    Fragt DNB API mit ISBN ab.

    Args:
        isbn: ISBN-Nummer (mit oder ohne Bindestriche)
        max_records: Max. Anzahl Ergebnisse

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

    return _query_dnb_sru(query, max_records, identifier_type='isbn', identifier_value=isbn_clean)


def query_dnb_by_issn(issn: str, max_records: int = 1) -> Optional[Dict]:
    """
    Fragt DNB API mit ISSN ab.

    Args:
        issn: ISSN-Nummer (mit oder ohne Bindestriche)
        max_records: Max. Anzahl Ergebnisse

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

    return _query_dnb_sru(query, max_records, identifier_type='issn', identifier_value=issn_clean)


def query_dnb_by_title_author(title: str, author: str = None, max_records: int = 1) -> Optional[Dict]:
    """
    Fragt DNB API mit Titel und optional Autor ab.

    Args:
        title: Titel des Werks
        author: Autor (optional, verbessert die Präzision)
        max_records: Max. Anzahl Ergebnisse

    Returns:
        Dict mit Metadaten oder None bei Fehler/Nicht-Gefunden

    Example:
        >>> data = query_dnb_by_title_author('Faust', 'Goethe')
        >>> if data:
        ...     print(data['title'])
    """
    # Query erstellen (CQL Syntax)
    if author:
        # Extrahiere nur ersten Autor (falls mehrere vorhanden)
        first_author = author.split(';')[0].split(',')[0].strip()
        query = f'tit={title} and per={first_author}'
    else:
        query = f'tit={title}'

    return _query_dnb_sru(query, max_records)
