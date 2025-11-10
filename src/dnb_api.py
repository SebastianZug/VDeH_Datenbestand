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
    try:
        # ISBN bereinigen
        isbn_clean = isbn.replace('-', '').replace(' ', '')
        
        # SRU Query erstellen
        query = f'isbn={isbn_clean}'
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
        
        # Namespace
        ns = {
            'srw': 'http://www.loc.gov/zing/srw/',
            'marc': 'http://www.loc.gov/MARC21/slim'
        }
        
        # Ersten Record extrahieren
        record = root.find('.//srw:recordData/marc:record', ns)
        if record is None:
            return None
        
        # Metadaten extrahieren
        metadata = {
            'title': None,
            'authors': [],
            'year': None,
            'publisher': None,
            'isbn': isbn_clean
        }
        
        # MARC21 Felder parsen
        for datafield in record.findall('marc:datafield', ns):
            tag = datafield.get('tag')
            
            # Titel (245)
            if tag == '245':
                subfields = datafield.findall('marc:subfield[@code="a"]', ns)
                if subfields:
                    metadata['title'] = subfields[0].text
            
            # Autoren (100, 700, 110, 710)
            # 100/700 = Personen, 110/710 = Körperschaften
            elif tag in ['100', '700', '110', '710']:
                subfields = datafield.findall('marc:subfield[@code="a"]', ns)
                for sf in subfields:
                    if sf.text:
                        author_name = sf.text.strip()
                        if author_name and author_name not in metadata['authors']:  # Duplikate vermeiden
                            metadata['authors'].append(author_name)
            
            # Jahr UND Verlag (264 oder 260)
            elif tag in ['264', '260']:
                # Jahr aus Subfield 'c'
                subfields_year = datafield.findall('marc:subfield[@code="c"]', ns)
                if subfields_year and subfields_year[0].text:
                    year_text = subfields_year[0].text
                    # Extrahiere 4-stellige Jahreszahl
                    year_match = re.search(r'\b(1[89]\d{2}|20\d{2})\b', year_text)
                    if year_match:
                        metadata['year'] = int(year_match.group(1))
                
                # Verlag aus Subfield 'b'
                subfields_publisher = datafield.findall('marc:subfield[@code="b"]', ns)
                if subfields_publisher and subfields_publisher[0].text:
                    metadata['publisher'] = subfields_publisher[0].text
        
        return metadata
        
    except Exception as e:
        print(f"   ⚠️ Fehler bei ISBN {isbn}: {str(e)}")
        return None


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
    try:
        # ISSN bereinigen
        issn_clean = issn.replace('-', '').replace(' ', '')
        
        # SRU Query
        query = f'issn={issn_clean}'
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
        
        # Parse (ähnlich wie bei ISBN)
        root = ET.fromstring(response.content)
        ns = {
            'srw': 'http://www.loc.gov/zing/srw/',
            'marc': 'http://www.loc.gov/MARC21/slim'
        }
        
        record = root.find('.//srw:recordData/marc:record', ns)
        if record is None:
            return None
        
        metadata = {
            'title': None,
            'authors': [],
            'year': None,
            'publisher': None,
            'issn': issn_clean
        }
        
        # MARC21 Felder parsen (wie bei ISBN)
        for datafield in record.findall('marc:datafield', ns):
            tag = datafield.get('tag')
            
            if tag == '245':
                subfields = datafield.findall('marc:subfield[@code="a"]', ns)
                if subfields:
                    metadata['title'] = subfields[0].text
            
            # Autoren (100, 700, 110, 710)
            # 100/700 = Personen, 110/710 = Körperschaften
            elif tag in ['100', '700', '110', '710']:
                subfields = datafield.findall('marc:subfield[@code="a"]', ns)
                for sf in subfields:
                    if sf.text:
                        author_name = sf.text.strip()
                        if author_name and author_name not in metadata['authors']:  # Duplikate vermeiden
                            metadata['authors'].append(author_name)
            
            # Jahr UND Verlag (264 oder 260)
            elif tag in ['264', '260']:
                # Jahr aus Subfield 'c'
                subfields_year = datafield.findall('marc:subfield[@code="c"]', ns)
                if subfields_year and subfields_year[0].text:
                    year_match = re.search(r'\b(1[89]\d{2}|20\d{2})\b', subfields_year[0].text)
                    if year_match:
                        metadata['year'] = int(year_match.group(1))
                
                # Verlag aus Subfield 'b'
                subfields_publisher = datafield.findall('marc:subfield[@code="b"]', ns)
                if subfields_publisher and subfields_publisher[0].text:
                    metadata['publisher'] = subfields_publisher[0].text
        
        return metadata
        
    except Exception as e:
        print(f"   ⚠️ Fehler bei ISSN {issn}: {str(e)}")
        return None


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
    try:
        # Query erstellen (CQL Syntax)
        if author:
            # Extrahiere nur ersten Autor (falls mehrere vorhanden)
            first_author = author.split(';')[0].split(',')[0].strip()
            query = f'tit={title} and per={first_author}'
        else:
            query = f'tit={title}'
        
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
        
        # Parse XML
        root = ET.fromstring(response.content)
        ns = {
            'srw': 'http://www.loc.gov/zing/srw/',
            'marc': 'http://www.loc.gov/MARC21/slim'
        }
        
        record = root.find('.//srw:recordData/marc:record', ns)
        if record is None:
            return None
        
        metadata = {
            'title': None,
            'authors': [],
            'year': None,
            'publisher': None
        }
        
        # MARC21 Felder parsen
        for datafield in record.findall('marc:datafield', ns):
            tag = datafield.get('tag')
            
            if tag == '245':
                subfields = datafield.findall('marc:subfield[@code="a"]', ns)
                if subfields:
                    metadata['title'] = subfields[0].text
            
            # Autoren (100, 700, 110, 710)
            # 100/700 = Personen, 110/710 = Körperschaften
            elif tag in ['100', '700', '110', '710']:
                subfields = datafield.findall('marc:subfield[@code="a"]', ns)
                for sf in subfields:
                    if sf.text:
                        author_name = sf.text.strip()
                        if author_name and author_name not in metadata['authors']:  # Duplikate vermeiden
                            metadata['authors'].append(author_name)
            
            # Jahr UND Verlag (264 oder 260)
            elif tag in ['264', '260']:
                # Jahr aus Subfield 'c'
                subfields_year = datafield.findall('marc:subfield[@code="c"]', ns)
                if subfields_year and subfields_year[0].text:
                    year_match = re.search(r'\b(1[89]\d{2}|20\d{2})\b', subfields_year[0].text)
                    if year_match:
                        metadata['year'] = int(year_match.group(1))
                
                # Verlag aus Subfield 'b'
                subfields_publisher = datafield.findall('marc:subfield[@code="b"]', ns)
                if subfields_publisher and subfields_publisher[0].text:
                    metadata['publisher'] = subfields_publisher[0].text
        
        return metadata
        
    except Exception as e:
        print(f"   ⚠️ Fehler bei Titel/Autor-Suche '{title}': {str(e)}")
        return None
