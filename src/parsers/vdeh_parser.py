"""
Optimierter OAI-PMH Parser für bibliographische Grunddaten
==========================================================

Dieses Modul stellt einen effizienten Parser für OAI-PMH XML-Dateien bereit,
der sich auf die wichtigsten bibliographischen Daten konzentriert:
- Titel
- Autoren
- Erscheinungsjahr
- Verlag
- ISBN

Autor: Bibliographische Datenanalyse
Datum: November 2025
"""

import pandas as pd
import xml.etree.ElementTree as ET
import re
import os
from typing import Optional, List, Dict, Any


def parse_bibliography(file_path: str, max_records: Optional[int] = None) -> pd.DataFrame:
    """
    Parst eine OAI-PMH XML-Datei und extrahiert bibliographische Grunddaten.
    
    Dieser robuste Parser verwendet xml.etree.ElementTree und extrahiert:
    - Titel (mit Zusätzen)
    - Autoren (alle gefundenen)
    - Erscheinungsjahr
    - Verlag (Name + Ort)
    - ISBN
    - ISSN
    
    Args:
        file_path (str): Pfad zur OAI-PMH XML-Datei
        max_records (Optional[int]): Maximale Anzahl zu verarbeitender Records (None = alle)
        
    Returns:
        pd.DataFrame: DataFrame mit Spalten ['id', 'title', 'authors', 'year', 'publisher', 'isbn', 'issn', 'authors_str', 'num_authors']
        
    Raises:
        FileNotFoundError: Wenn die XML-Datei nicht gefunden wird
        Exception: Bei XML-Parsing-Fehlern
    """
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"XML-Datei nicht gefunden: {file_path}")
    
    print("🚀 Starte robusten Parser für bibliographische Grunddaten...")
    print(f"📁 Datei: {file_path}")
    print(f"📊 Dateigröße: {os.path.getsize(file_path) / (1024*1024):.1f} MB")
    
    # OAI-PMH Namespace
    ns = {"oai": "http://www.openarchives.org/OAI/2.0/"}
    
    records = []
    record_count = 0
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Alle <record> im OAI-namespace finden
        oai_records = root.findall(".//oai:record", ns)
        total_records = len(oai_records)
        print(f"📚 Gefunden: {total_records:,} OAI-Records")
        
        for idx, record_elem in enumerate(oai_records):
            if max_records and record_count >= max_records:
                break
            
            record = _extract_basic_record_data(record_elem, ns, record_count)
            records.append(record)
            record_count += 1
            
            if record_count % 5000 == 0:
                print(f"📝 Verarbeitet: {record_count:,} Records")
        
        print(f"✅ {record_count:,} Records verarbeitet")
        
    except Exception as e:
        raise Exception(f"Fehler beim Parsen der XML-Datei: {str(e)}")
    
    # DataFrame erstellen
    df = pd.DataFrame(records)
    
    # Autoren-Strings für einfache Anzeige
    df['authors_str'] = df['authors'].apply(lambda x: ' | '.join(x) if x else '')
    df['num_authors'] = df['authors'].apply(len)
    
    # Affiliations-Strings (Institutionen/Herausgeber)
    df['authors_affiliation_str'] = df['authors_affiliation'].apply(lambda x: ' | '.join(x) if x else '')
    df['num_authors_affiliation'] = df['authors_affiliation'].apply(len)
    
    print(f"🎯 DataFrame erstellt:")
    print(f"   📊 {len(df):,} Zeilen")
    print(f"   📋 {len(df.columns):,} Spalten")
    print(f"   💾 {df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")
    
    return df


def _extract_basic_record_data(elem: ET.Element, ns: Dict[str, str], record_count: int) -> Dict[str, Any]:
    """
    Extrahiert die grundlegenden bibliographischen Daten aus einem Record.
    
    Args:
        elem: XML-Element des Records
        ns: OAI-PMH Namespace Dictionary
        record_count: Laufende Nummer des Records
        
    Returns:
        Dict mit den extrahierten Grunddaten
    """
    record = {
        'id': None,
        'title': None,
        'authors': [],
        'authors_affiliation': [],  # Institutionen/Herausgeber (z.B. "Europäische Kommission")
        'year': None,
        'publisher': None,
        'isbn': None,
        'issn': None
    }
    
    # OAI Identifier extrahieren
    header = elem.find('.//oai:header', ns)
    if header is not None:
        identifier = header.find('.//oai:identifier', ns)
        if identifier is not None:
            record['id'] = identifier.text
    
    # Fallback: Record-Nummer als ID
    if not record['id']:
        record['id'] = f"record_{record_count}"
    
    # Metadata und Document-Daten extrahieren
    metadata = elem.find('oai:metadata', ns)
    if metadata is None:
        return record
        
    document = metadata.find('oai:document', ns)
    if document is not None:
        record['title'] = _extract_title(document, ns)
        record['authors'] = _extract_authors(document, ns, include_corporate=False)  # Nur Personen
        record['authors_affiliation'] = _extract_authors_affiliation(document, ns)  # Institutionen separat
        record['year'] = _extract_year(document, ns)
        record['publisher'] = _extract_publisher(document, ns)
        record['isbn'], record['issn'] = _find_standard_numbers(document, ns)
    
    return record


def _extract_title(document: ET.Element, ns: Dict[str, str]) -> Optional[str]:
    """
    Extrahiert den Titel aus verschiedenen möglichen Feldern.
    
    Args:
        document: Document XML-Element
        ns: OAI-PMH Namespace Dictionary
        
    Returns:
        Titel als String oder None
    """
    def get_field(tag: str, code: Optional[str] = None) -> Optional[str]:
        """Hilfsfunktion zum Extrahieren von Feldern"""
        elems = document.findall(f".//oai:datafield[@tag='{tag}']", ns)
        if not elems:
            return None
        if code:
            subs = [s.text for e in elems for s in e.findall(f"oai:subfield[@code='{code}']", ns) if s.text]
            return "; ".join(subs) if subs else None
        else:
            texts = [e.text for e in elems if e.text]
            return "; ".join(texts) if texts else None
    
    # Haupttitel (Tag 331)
    titel = get_field("331")
    titel_zusatz = get_field("335")
    
    if titel and titel_zusatz:
        return f"{titel} : {titel_zusatz}"
    return titel


def _extract_authors(document: ET.Element, ns: Dict[str, str], include_corporate: bool = False) -> List[str]:
    """
    Extrahiert alle Autoren aus verschiedenen Autorenfeldern.
    
    MAB2 Autoren-Tags:
    - 100, 104, 108: Personennamen (echte Autoren)
    - 200, 204, 208: Körperschaften/Institutionen (z.B. "Europäische Kommission")
    
    Args:
        document: Document XML-Element
        ns: OAI-PMH Namespace Dictionary
        include_corporate: Wenn True, werden auch Körperschaften als Autoren eingeschlossen
        
    Returns:
        Liste der Autoren
    """
    def get_field(tag: str, code: Optional[str] = None) -> Optional[str]:
        """Hilfsfunktion zum Extrahieren von Feldern"""
        elems = document.findall(f".//oai:datafield[@tag='{tag}']", ns)
        if not elems:
            return None
        if code:
            subs = [s.text for e in elems for s in e.findall(f"oai:subfield[@code='{code}']", ns) if s.text]
            return "; ".join(subs) if subs else None
        else:
            texts = [e.text for e in elems if e.text]
            return "; ".join(texts) if texts else None
    
    authors = []
    
    # Personennamen (echte Autoren) - IMMER einschließen
    person_tags = ["100", "104", "108"]
    for tag in person_tags:
        autor = get_field(tag, "a")
        if autor:
            authors.extend(autor.split("; "))
    
    # Körperschaften/Institutionen - NUR wenn gewünscht
    if include_corporate:
        corporate_tags = ["200", "204", "208"]
        for tag in corporate_tags:
            autor = get_field(tag, "a")
            if autor:
                authors.extend(autor.split("; "))
    
    return authors


def _extract_corporate_authors(document: ET.Element, ns: Dict[str, str]) -> List[str]:
    """
    Extrahiert institutionelle Zugehörigkeiten/Herausgeber (z.B. "Europäische Kommission").
    
    DEPRECATED: Diese Funktion wurde in _extract_authors_affiliation umbenannt.
    Wird für Backward-Kompatibilität beibehalten.
    """
    return _extract_authors_affiliation(document, ns)


def _extract_authors_affiliation(document: ET.Element, ns: Dict[str, str]) -> List[str]:
    """
    Extrahiert institutionelle Zugehörigkeiten/Herausgeber (z.B. "Europäische Kommission", "OECD").
    
    MAB2 Körperschafts-Tags:
    - 200, 204, 208: Körperschaften/Institutionen
    
    Args:
        document: Document XML-Element
        ns: OAI-PMH Namespace Dictionary
        
    Returns:
        Liste der institutionellen Affiliationen
    """
    def get_field(tag: str, code: Optional[str] = None) -> Optional[str]:
        """Hilfsfunktion zum Extrahieren von Feldern"""
        elems = document.findall(f".//oai:datafield[@tag='{tag}']", ns)
        if not elems:
            return None
        if code:
            subs = [s.text for e in elems for s in e.findall(f"oai:subfield[@code='{code}']", ns) if s.text]
            return "; ".join(subs) if subs else None
        else:
            texts = [e.text for e in elems if e.text]
            return "; ".join(texts) if texts else None
    
    affiliations = []
    affiliation_tags = ["200", "204", "208"]
    for tag in affiliation_tags:
        aff = get_field(tag, "a")
        if aff:
            affiliations.extend(aff.split("; "))
    
    return affiliations


def _extract_year(document: ET.Element, ns: Dict[str, str]) -> Optional[int]:
    """
    Extrahiert das Erscheinungsjahr aus verschiedenen Jahresfeldern.
    
    Args:
        document: Document XML-Element
        ns: OAI-PMH Namespace Dictionary
        
    Returns:
        Jahr als Integer oder None
    """
    def get_field(tag: str, code: Optional[str] = None) -> Optional[str]:
        """Hilfsfunktion zum Extrahieren von Feldern"""
        elems = document.findall(f".//oai:datafield[@tag='{tag}']", ns)
        if not elems:
            return None
        if code:
            subs = [s.text for e in elems for s in e.findall(f"oai:subfield[@code='{code}']", ns) if s.text]
            return "; ".join(subs) if subs else None
        else:
            texts = [e.text for e in elems if e.text]
            return "; ".join(texts) if texts else None
    
    # Erscheinungsjahr (Tag 425)
    jahr_text = get_field("425")
    if jahr_text:
        return _parse_year_from_text(jahr_text)
    
    return None


def _extract_publisher(document: ET.Element, ns: Dict[str, str]) -> Optional[str]:
    """
    Extrahiert Verlagsinformationen.
    
    Args:
        document: Document XML-Element
        ns: OAI-PMH Namespace Dictionary
        
    Returns:
        Verlag als String oder None
    """
    def get_field(tag: str, code: Optional[str] = None) -> Optional[str]:
        """Hilfsfunktion zum Extrahieren von Feldern"""
        elems = document.findall(f".//oai:datafield[@tag='{tag}']", ns)
        if not elems:
            return None
        if code:
            subs = [s.text for e in elems for s in e.findall(f"oai:subfield[@code='{code}']", ns) if s.text]
            return "; ".join(subs) if subs else None
        else:
            texts = [e.text for e in elems if e.text]
            return "; ".join(texts) if texts else None
    
    # Verlag: 412 = Verlagsort, 410 = Verlagsname
    verlag_name = get_field("410")
    verlag_ort = get_field("412")
    
    if verlag_name and verlag_ort:
        return f"{verlag_ort} : {verlag_name}"
    elif verlag_name:
        return verlag_name
    elif verlag_ort:
        return verlag_ort
    
    return None


def _parse_year_from_text(text: str) -> Optional[int]:
    """
    Extrahiert eine 4-stellige Jahreszahl aus einem Text.
    
    Args:
        text: Text der nach einer Jahreszahl durchsucht werden soll
        
    Returns:
        Jahr als Integer oder None
    """
    year_match = re.search(r'\b(19|20)\d{2}\b', text)
    if year_match:
        year = int(year_match.group())
        # Plausibilitätsprüfung: Jahr zwischen 1800 und 2030
        if 1800 <= year <= 2030:
            return year
    return None


def _find_standard_numbers(document: ET.Element, ns: Dict[str, str]) -> tuple[Optional[str], Optional[str]]:
    """
    Extrahiert ISBN und ISSN Nummern aus dem Dokument.
    
    Sucht nach:
    - ISBN-13: 13-stellige Nummer (meist mit 978 oder 979 beginnend)
    - ISBN-10: 10-stellige Nummer (kann X als letzte Stelle haben)
    - ISSN: 8-stellige Nummer (XXXX-XXXX Format, letzte Stelle kann X sein)
    
    Args:
        document: Document XML-Element
        ns: OAI-PMH Namespace Dictionary
        
    Returns:
        Tuple mit (ISBN, ISSN), beide können None sein
    """
    def get_field(tag: str, code: Optional[str] = None) -> Optional[str]:
        """Hilfsfunktion zum Extrahieren von Feldern"""
        elems = document.findall(f".//oai:datafield[@tag='{tag}']", ns)
        if not elems:
            return None
        if code:
            subs = [s.text for e in elems for s in e.findall(f"oai:subfield[@code='{code}']", ns) if s.text]
            return "; ".join(subs) if subs else None
        else:
            texts = [e.text for e in elems if e.text]
            return "; ".join(texts) if texts else None
    
    # ISBN: MAB2 Tags 540/542
    isbn = get_field("540", "a") or get_field("542", "a")
    
    # ISSN: Suche in verschiedenen Feldern
    issn = None
    for tag in ["542", "540"]:  # Häufige ISSN-Felder
        issn_candidate = get_field(tag, "a")
        if issn_candidate and _is_issn(issn_candidate):
            issn = _format_issn(issn_candidate)
            break
    
    # Format ISBN wenn vorhanden
    if isbn:
        isbn = _format_isbn(isbn)
    
    return isbn, issn


def _is_issn(text: str) -> bool:
    """Prüft ob ein Text eine ISSN ist (8 Ziffern, optional mit Bindestrich)"""
    cleaned = re.sub(r'[^0-9X]', '', text.upper())
    return len(cleaned) == 8


def _format_isbn(isbn: str) -> str:
    """Formatiert ISBN mit Bindestrichen"""
    isbn = re.sub(r'[^0-9X]', '', isbn.upper())
    if len(isbn) == 13:  # ISBN-13
        return f"{isbn[0:3]}-{isbn[3]}-{isbn[4:7]}-{isbn[7:12]}-{isbn[12]}"
    elif len(isbn) == 10:  # ISBN-10
        return f"{isbn[0]}-{isbn[1:4]}-{isbn[4:9]}-{isbn[9]}"
    return isbn


def _format_issn(issn: str) -> str:
    """Formatiert ISSN mit Bindestrich"""
    issn = re.sub(r'[^0-9X]', '', issn.upper())
    if len(issn) == 8:
        return f"{issn[0:4]}-{issn[4:8]}"
    return issn


def analyze_bibliography_data(df: pd.DataFrame) -> None:
    """
    Führt eine Analyse der bibliographischen Daten durch.
    
    Args:
        df: DataFrame mit bibliographischen Daten
    """
    print("\n📊 === BIBLIOGRAPHISCHE DATEN ANALYSE ===")
    
    total = len(df)
    with_title = df['title'].notna().sum()
    with_authors = df['num_authors'].gt(0).sum()
    with_year = df['year'].notna().sum()
    with_publisher = df['publisher'].notna().sum() if 'publisher' in df.columns else 0
    with_isbn = df['isbn'].notna().sum()
    with_issn = df['issn'].notna().sum() if 'issn' in df.columns else 0
    complete = df[(df['title'].notna()) & (df['year'].notna()) & (df['num_authors'] > 0)].shape[0]
    
    print(f"📚 Gesamt Records: {total:,}")
    print(f"📋 Mit Titel: {with_title:,} ({with_title/total*100:.1f}%)")
    print(f"👤 Mit Autoren: {with_authors:,} ({with_authors/total*100:.1f}%)")
    print(f"📅 Mit Jahr: {with_year:,} ({with_year/total*100:.1f}%)")
    if with_publisher > 0:
        print(f"🏢 Mit Verlag: {with_publisher:,} ({with_publisher/total*100:.1f}%)")
    print(f"📖 Mit ISBN: {with_isbn:,} ({with_isbn/total*100:.1f}%)")
    if with_issn > 0:
        print(f"📰 Mit ISSN: {with_issn:,} ({with_issn/total*100:.1f}%)")
    print(f"✅ Vollständig: {complete:,} ({complete/total*100:.1f}%)")
    
    # Zeitspanne
    years = df['year'].dropna()
    if len(years) > 0:
        print(f"📅 Zeitspanne: {int(years.min())} - {int(years.max())}")
        print(f"📊 Median-Jahr: {int(years.median())}")
    
    # Autoren-Statistik
    all_authors = []
    for authors_list in df['authors']:
        if authors_list:
            all_authors.extend(authors_list)
    
    if all_authors:
        unique_authors = len(set(all_authors))
        print(f"👥 Einzigartige Autoren: {unique_authors:,}")


def get_sample_records(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """
    Gibt Beispiel-Records zurück.
    
    Args:
        df: DataFrame mit bibliographischen Daten
        n: Anzahl der Beispiele
        
    Returns:
        DataFrame mit Beispieldaten
    """
    sample_cols = ['id', 'title', 'authors_str', 'year', 'publisher', 'num_authors', 'isbn', 'issn']
    available_cols = [col for col in sample_cols if col in df.columns]
    return df[available_cols].head(n)


if __name__ == "__main__":
    # Beispiel-Verwendung
    print("Robuster OAI-PMH Parser für bibliographische Grunddaten")
    print("Verwendung: df = parse_bibliography('pfad/zur/datei.xml')")
    print("\nExtrahiert:")
    print("  - Titel (mit Zusätzen)")
    print("  - Autoren (alle)")
    print("  - Erscheinungsjahr")
    print("  - Verlag (Name + Ort)")
    print("  - ISBN")
    print("  - ISSN")