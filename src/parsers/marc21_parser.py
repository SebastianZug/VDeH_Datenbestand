"""
MARC21 XML Parser für bibliographische Grunddaten
==================================================

Dieses Modul stellt einen effizienten Parser für MARC21 XML-Dateien bereit,
der sich auf die wichtigsten bibliographischen Daten konzentriert:
- Titel
- Autoren
- Erscheinungsjahr
- Verlag
- ISBN/ISSN
- Seitenzahl

MARC21 Feldübersicht:
- 020: ISBN
- 022: ISSN
- 100: Haupteintrag Personenname (Autor)
- 110: Haupteintrag Körperschaftsname
- 245: Titel (Title Statement)
- 246: Nebentitel
- 260: Publikationsangaben (alt)
- 264: Produktion/Publikation/Vertrieb (neu)
- 300: Physische Beschreibung
- 520: Zusammenfassung/Abstract
- 650: Schlagwort
- 700: Nebeneintrag Personenname
- 710: Nebeneintrag Körperschaftsname

Autor: Data Analysis Team
Datum: Dezember 2025
"""

import pandas as pd
import xml.etree.ElementTree as ET
import re
import os
import logging
from typing import Optional, List, Dict, Any

# Configure logger for this module
logger = logging.getLogger(__name__)


def _get_field(document: ET.Element, tag: str, code: Optional[str] = None) -> Optional[str]:
    """
    Helper function to extract fields from MARC21 XML document.

    Args:
        document: Document XML-Element
        tag: MARC21 tag to search for
        code: Optional subfield code

    Returns:
        Extracted field value(s) as string or None
    """
    elems = document.findall(f".//datafield[@tag='{tag}']")
    if not elems:
        return None

    if code:
        subs = [s.text for e in elems for s in e.findall(f"subfield[@code='{code}']") if s.text]
        return "; ".join(subs) if subs else None
    else:
        # Wenn kein code angegeben, alle Subfields konkatenieren
        texts = []
        for e in elems:
            subfields = [s.text for s in e.findall("subfield") if s.text]
            if subfields:
                texts.append(" ".join(subfields))
        return "; ".join(texts) if texts else None


def parse_bibliography(file_path: str, max_records: Optional[int] = None) -> pd.DataFrame:
    """
    Parst eine MARC21 XML-Datei und extrahiert bibliographische Grunddaten.

    Dieser robuste Parser verwendet xml.etree.ElementTree und extrahiert:
    - Titel (mit Zusätzen)
    - Autoren (alle gefundenen)
    - Erscheinungsjahr
    - Verlag (Name + Ort)
    - ISBN
    - ISSN
    - Seitenzahl

    Args:
        file_path (str): Pfad zur MARC21 XML-Datei
        max_records (Optional[int]): Maximale Anzahl zu verarbeitender Records (None = alle)

    Returns:
        pd.DataFrame: DataFrame mit Spalten ['id', 'title', 'authors', 'year', 'publisher',
                      'isbn', 'issn', 'pages', 'authors_str', 'num_authors',
                      'authors_affiliation_str', 'num_authors_affiliation']

    Raises:
        FileNotFoundError: Wenn die XML-Datei nicht gefunden wird
        Exception: Bei XML-Parsing-Fehlern
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"XML-Datei nicht gefunden: {file_path}")

    file_size_mb = os.path.getsize(file_path) / (1024*1024)
    logger.info(f"Starting MARC21 parser for bibliographic data from {file_path} ({file_size_mb:.1f} MB)")

    records = []
    record_count = 0

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Alle <document> Elemente finden
        documents = root.findall('document')
        total_records = len(documents)
        logger.info(f"Found {total_records:,} MARC21 documents")

        for idx, document in enumerate(documents):
            if max_records and record_count >= max_records:
                break

            record = _extract_basic_record_data(document, record_count)
            records.append(record)
            record_count += 1

            if record_count % 5000 == 0:
                logger.info(f"Processed {record_count:,} records")

        logger.info(f"Successfully processed {record_count:,} records")

    except Exception as e:
        raise Exception(f"Fehler beim Parsen der MARC21 XML-Datei: {str(e)}")

    # DataFrame erstellen
    df = pd.DataFrame(records)

    # Autoren-Strings für einfache Anzeige
    df['authors_str'] = df['authors'].apply(lambda x: ' | '.join(x) if x else '')
    df['num_authors'] = df['authors'].apply(len)

    # Affiliations-Strings (Institutionen/Herausgeber)
    df['authors_affiliation_str'] = df['authors_affiliation'].apply(lambda x: ' | '.join(x) if x else '')
    df['num_authors_affiliation'] = df['authors_affiliation'].apply(len)

    memory_mb = df.memory_usage(deep=True).sum() / 1024**2
    logger.info(f"DataFrame created: {len(df):,} rows, {len(df.columns)} columns, {memory_mb:.1f} MB")

    return df


def _extract_basic_record_data(document: ET.Element, record_count: int) -> Dict[str, Any]:
    """
    Extrahiert die grundlegenden bibliographischen Daten aus einem MARC21 Record.

    Args:
        document: XML-Element des MARC21 Documents
        record_count: Laufende Nummer des Records

    Returns:
        Dict mit den extrahierten Grunddaten
    """
    record = {
        'id': None,
        'title': None,
        'authors': [],
        'authors_affiliation': [],  # Institutionen/Herausgeber
        'year': None,
        'publisher': None,
        'isbn': None,
        'issn': None,
        'pages': None,  # Seitenzahl aus Feld 300
        'language': None  # Sprache aus Feld 041 oder controlfield 008
    }

    # IDN aus Attribut extrahieren
    record['id'] = document.get('idn')

    # Fallback: controlfield 001
    if not record['id']:
        controlfield = document.find(".//controlfield[@tag='001']")
        if controlfield is not None and controlfield.text:
            record['id'] = controlfield.text

    # Fallback: Record-Nummer als ID
    if not record['id']:
        record['id'] = f"record_{record_count}"

    # Daten extrahieren
    record['title'] = _extract_title(document)
    record['authors'] = _extract_authors(document, include_corporate=False)  # Nur Personen
    record['authors_affiliation'] = _extract_authors_affiliation(document)  # Institutionen separat
    record['year'] = _extract_year(document)
    record['publisher'] = _extract_publisher(document)
    record['isbn'], record['issn'] = _find_standard_numbers(document)
    record['pages'] = _extract_pages(document)
    record['language'] = _extract_language(document)

    return record


def _extract_title(document: ET.Element) -> Optional[str]:
    """
    Extrahiert den Titel aus MARC21 Feld 245.

    MARC21 Feld 245 (Title Statement):
    - $a: Haupttitel
    - $b: Untertitel/Zusatz

    Args:
        document: Document XML-Element

    Returns:
        Titel als String oder None
    """
    # Haupttitel (245$a)
    titel = _get_field(document, "245", "a")
    titel_zusatz = _get_field(document, "245", "b")

    if titel and titel_zusatz:
        return f"{titel} : {titel_zusatz}"
    return titel


def _extract_authors(document: ET.Element, include_corporate: bool = False) -> List[str]:
    """
    Extrahiert alle Autoren aus MARC21 Feldern.

    MARC21 Autoren-Tags:
    - 100: Haupteintrag Personenname (Hauptautor)
    - 700: Nebeneintrag Personenname (weitere Autoren)
    - 110: Haupteintrag Körperschaftsname (nur wenn include_corporate=True)
    - 710: Nebeneintrag Körperschaftsname (nur wenn include_corporate=True)

    Args:
        document: Document XML-Element
        include_corporate: Wenn True, werden auch Körperschaften als Autoren eingeschlossen

    Returns:
        Liste der Autoren
    """
    authors = []

    # Personennamen (echte Autoren) - IMMER einschließen
    person_tags = ["100", "700"]
    for tag in person_tags:
        autor = _get_field(document, tag, "a")
        if autor:
            authors.extend(autor.split("; "))

    # Körperschaften/Institutionen - NUR wenn gewünscht
    if include_corporate:
        corporate_tags = ["110", "710"]
        for tag in corporate_tags:
            autor = _get_field(document, tag, "a")
            if autor:
                authors.extend(autor.split("; "))

    return authors


def _extract_authors_affiliation(document: ET.Element) -> List[str]:
    """
    Extrahiert institutionelle Zugehörigkeiten/Herausgeber (z.B. "Europäische Kommission", "OECD").

    MARC21 Körperschafts-Tags:
    - 110: Haupteintrag Körperschaftsname
    - 710: Nebeneintrag Körperschaftsname

    Args:
        document: Document XML-Element

    Returns:
        Liste der institutionellen Affiliationen
    """
    affiliations = []
    affiliation_tags = ["110", "710"]
    for tag in affiliation_tags:
        aff = _get_field(document, tag, "a")
        if aff:
            affiliations.extend(aff.split("; "))

    return affiliations


def _extract_year(document: ET.Element) -> Optional[int]:
    """
    Extrahiert das Erscheinungsjahr aus MARC21 Feldern.

    MARC21 Jahres-Felder:
    - controlfield 008 (Positionen 7-10): Publikationsjahr (bevorzugt)
    - 260$c: Publikationsdatum (alt)
    - 264$c: Produktions-/Publikationsdatum (neu)

    Args:
        document: Document XML-Element

    Returns:
        Jahr als Integer oder None
    """
    # Bevorzugt: controlfield 008, Positionen 7-10
    controlfield_008 = document.find(".//controlfield[@tag='008']")
    if controlfield_008 is not None and controlfield_008.text:
        text = controlfield_008.text
        # Format: "961111|1983||||   |||||r|||||||||||ger|u"
        # Jahr steht nach dem ersten "|" an Position 7-10
        if '|' in text:
            parts = text.split('|')
            if len(parts) > 1:
                year_text = parts[1][:4]  # Erste 4 Zeichen nach "|"
                year = _parse_year_from_text(year_text)
                if year:
                    return year

    # Fallback: 264$c (neueres Feld)
    jahr_text = _get_field(document, "264", "c")
    if jahr_text:
        return _parse_year_from_text(jahr_text)

    # Fallback: 260$c (älteres Feld)
    jahr_text = _get_field(document, "260", "c")
    if jahr_text:
        return _parse_year_from_text(jahr_text)

    return None


def _extract_publisher(document: ET.Element) -> Optional[str]:
    """
    Extrahiert Verlagsinformationen aus MARC21 Feldern.

    MARC21 Verlags-Felder:
    - 264$a: Ort (neu)
    - 264$b: Verlag (neu)
    - 260$a: Ort (alt)
    - 260$b: Verlag (alt)

    Args:
        document: Document XML-Element

    Returns:
        Verlag als String oder None
    """
    # Bevorzugt: 264 (neueres Feld)
    verlag_name = _get_field(document, "264", "b")
    verlag_ort = _get_field(document, "264", "a")

    # Fallback: 260 (älteres Feld)
    if not verlag_name:
        verlag_name = _get_field(document, "260", "b")
    if not verlag_ort:
        verlag_ort = _get_field(document, "260", "a")

    if verlag_name and verlag_ort:
        return f"{verlag_ort} : {verlag_name}"
    elif verlag_name:
        return verlag_name
    elif verlag_ort:
        return verlag_ort

    return None


def _extract_pages(document: ET.Element) -> Optional[str]:
    """
    Extrahiert Seitenzahl-Informationen aus MARC21 Feld 300.

    MARC21 Feld 300 (Physical Description):
    - $a: Umfang (z.B. "188 S.", "XV, 250 p.")

    Args:
        document: Document XML-Element

    Returns:
        Seitenzahl-Information als String oder None
    """
    pages = _get_field(document, "300", "a")
    return pages


def _extract_language(document: ET.Element) -> Optional[str]:
    """
    Extrahiert die Sprache aus MARC21 Feldern.

    MARC21 Sprach-Felder:
    - 041$a: Language Code (bevorzugt)
    - controlfield 008 (Positionen 35-37): Language Code

    Args:
        document: Document XML-Element

    Returns:
        Sprachcode als String (z.B. "ger", "eng") oder None
    """
    # Bevorzugt: Feld 041$a
    language = _get_field(document, "041", "a")
    if language:
        # Nur ersten Code nehmen, falls mehrere
        return language.split(";")[0].strip() if ";" in language else language.strip()

    # Fallback: controlfield 008, Positionen 35-37
    controlfield_008 = document.find(".//controlfield[@tag='008']")
    if controlfield_008 is not None and controlfield_008.text:
        text = controlfield_008.text
        # Format: "961111|1983||||   |||||r|||||||||||ger|u"
        # Sprache steht zwischen den letzten beiden "|"
        if '|' in text:
            parts = text.split('|')
            if len(parts) >= 3:
                # Vorletztes Teil enthält die Sprache
                lang_part = parts[-2]
                if len(lang_part) >= 3:
                    return lang_part[:3]  # Erste 3 Zeichen = Sprachcode

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


def _find_standard_numbers(document: ET.Element) -> tuple[Optional[str], Optional[str]]:
    """
    Extrahiert ISBN und ISSN Nummern aus MARC21 Feldern.

    MARC21 Standard-Nummern:
    - 020$a: ISBN
    - 022$a: ISSN

    Args:
        document: Document XML-Element

    Returns:
        Tuple mit (ISBN, ISSN), beide können None sein
    """
    # ISBN: MARC21 Feld 020$a
    isbn = _get_field(document, "020", "a")

    # ISSN: MARC21 Feld 022$a
    issn = _get_field(document, "022", "a")

    # Format ISBN wenn vorhanden
    if isbn:
        isbn = _format_isbn(isbn)

    # Format ISSN wenn vorhanden
    if issn:
        issn = _format_issn(issn)

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
    logger.info("=== BIBLIOGRAPHIC DATA ANALYSIS (MARC21) ===")

    total = len(df)
    with_title = df['title'].notna().sum()
    with_authors = df['num_authors'].gt(0).sum()
    with_year = df['year'].notna().sum()
    with_publisher = df['publisher'].notna().sum() if 'publisher' in df.columns else 0
    with_isbn = df['isbn'].notna().sum()
    with_issn = df['issn'].notna().sum() if 'issn' in df.columns else 0
    with_pages = df['pages'].notna().sum() if 'pages' in df.columns else 0
    with_language = df['language'].notna().sum() if 'language' in df.columns else 0
    complete = df[(df['title'].notna()) & (df['year'].notna()) & (df['num_authors'] > 0)].shape[0]

    logger.info(f"Total records: {total:,}")
    logger.info(f"With title: {with_title:,} ({with_title/total*100:.1f}%)")
    logger.info(f"With authors: {with_authors:,} ({with_authors/total*100:.1f}%)")
    logger.info(f"With year: {with_year:,} ({with_year/total*100:.1f}%)")
    if with_publisher > 0:
        logger.info(f"With publisher: {with_publisher:,} ({with_publisher/total*100:.1f}%)")
    logger.info(f"With ISBN: {with_isbn:,} ({with_isbn/total*100:.1f}%)")
    if with_issn > 0:
        logger.info(f"With ISSN: {with_issn:,} ({with_issn/total*100:.1f}%)")
    if with_pages > 0:
        logger.info(f"With pages: {with_pages:,} ({with_pages/total*100:.1f}%)")
    if with_language > 0:
        logger.info(f"With language: {with_language:,} ({with_language/total*100:.1f}%)")
    logger.info(f"Complete records: {complete:,} ({complete/total*100:.1f}%)")

    # Zeitspanne
    years = df['year'].dropna()
    if len(years) > 0:
        logger.info(f"Year range: {int(years.min())} - {int(years.max())}")
        logger.info(f"Median year: {int(years.median())}")

    # Autoren-Statistik
    all_authors = []
    for authors_list in df['authors']:
        if authors_list:
            all_authors.extend(authors_list)

    if all_authors:
        unique_authors = len(set(all_authors))
        logger.info(f"Unique authors: {unique_authors:,}")


def get_sample_records(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """
    Gibt Beispiel-Records zurück.

    Args:
        df: DataFrame mit bibliographischen Daten
        n: Anzahl der Beispiele

    Returns:
        DataFrame mit Beispieldaten
    """
    sample_cols = ['id', 'title', 'authors_str', 'year', 'publisher', 'num_authors', 'isbn', 'issn', 'pages']
    available_cols = [col for col in sample_cols if col in df.columns]
    return df[available_cols].head(n)


if __name__ == "__main__":
    # Beispiel-Verwendung
    print("MARC21 XML Parser für bibliographische Grunddaten")
    print("Verwendung: df = parse_bibliography('pfad/zur/datei.xml')")
    print("\nExtrahiert:")
    print("  - Titel (Feld 245)")
    print("  - Autoren (Felder 100, 700)")
    print("  - Erscheinungsjahr (Felder 260/264)")
    print("  - Verlag (Felder 260/264)")
    print("  - ISBN (Feld 020)")
    print("  - ISSN (Feld 022)")
    print("  - Seitenzahl (Feld 300)")
