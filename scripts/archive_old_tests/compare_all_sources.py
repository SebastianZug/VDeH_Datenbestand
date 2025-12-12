#!/usr/bin/env python3
"""
Vergleichende Analyse aller drei VDEH Datenquellen:
- VDEH_mab_all.xml (MAB Format)
- marcBIB-VDEH-xml2-tsv.csv (CSV, preprocessed)
- marcVDEH.xml (MARC21 Format)
"""

import xml.etree.ElementTree as ET
from collections import defaultdict
import csv

print("=" * 100)
print("VERGLEICHENDE VOLLSTÄNDIGKEITSANALYSE - VDEH Datenquellen")
print("=" * 100)

# ============================================================================
# 1. ANALYSE: VDEH_mab_all.xml (MAB Format)
# ============================================================================
print("\n[1/3] Analysiere VDEH_mab_all.xml (MAB Format)...")

mab_file = '/media/sz/Data/Bibo/analysis/data/vdeh/raw/VDEH_mab_all.xml'
tree_mab = ET.parse(mab_file)
root_mab = tree_mab.getroot()

ns = {'oai': 'http://www.openarchives.org/OAI/2.0/'}
documents_mab = root_mab.findall('.//oai:document', ns)
mab_total = len(documents_mab)

# MAB Felder zählen
mab_titel_331 = 0  # Hauptsachtitel
mab_autor_100 = 0  # Verfasser
mab_isbn_540 = 0   # ISBN
mab_issn_542 = 0   # ISSN
mab_seiten_433 = 0 # Seitenzahl

for doc in documents_mab:
    # Titel (Feld 331)
    if doc.find('.//oai:datafield[@tag="331"]', ns) is not None:
        mab_titel_331 += 1

    # Autor (Feld 100)
    if doc.find('.//oai:datafield[@tag="100"]', ns) is not None:
        mab_autor_100 += 1

    # ISBN (Feld 540)
    if doc.find('.//oai:datafield[@tag="540"]', ns) is not None:
        mab_isbn_540 += 1

    # ISSN (Feld 542)
    if doc.find('.//oai:datafield[@tag="542"]', ns) is not None:
        mab_issn_542 += 1

    # Seitenzahl (Feld 433)
    if doc.find('.//oai:datafield[@tag="433"]', ns) is not None:
        mab_seiten_433 += 1

print(f"   Total: {mab_total:,} Records")

# ============================================================================
# 2. ANALYSE: marcBIB-VDEH-xml2-tsv.csv
# ============================================================================
print("\n[2/3] Analysiere marcBIB-VDEH-xml2-tsv.csv...")

csv_file = '/media/sz/Data/Bibo/data/marcBIB-VDEH-xml2-tsv.csv'
csv_total = 0
csv_titel = 0
csv_autor = 0
csv_isbn = 0
csv_issn = 0
csv_seiten = 0

with open(csv_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        csv_total += 1

        # Titel
        if row.get('title') and row['title'].strip():
            csv_titel += 1

        # Autor (Spalte 'author' oder 'creator')
        if (row.get('author') and row['author'].strip()) or \
           (row.get('creator') and row['creator'].strip()):
            csv_autor += 1

        # ISBN
        if row.get('isbn') and row['isbn'].strip():
            csv_isbn += 1

        # ISSN
        if row.get('issn') and row['issn'].strip():
            csv_issn += 1

        # Seitenzahl (Spalte 'pages' oder 'extent')
        if (row.get('pages') and row['pages'].strip()) or \
           (row.get('extent') and row['extent'].strip()):
            csv_seiten += 1

print(f"   Total: {csv_total:,} Records")

# ============================================================================
# 3. ANALYSE: marcVDEH.xml (MARC21 Format)
# ============================================================================
print("\n[3/3] Analysiere marcVDEH.xml (MARC21 Format)...")

marc_file = '/media/sz/Data/Bibo/data/marcVDEH.xml'
tree_marc = ET.parse(marc_file)
root_marc = tree_marc.getroot()

documents_marc = root_marc.findall('document')
marc_total = len(documents_marc)

# MARC21 Felder zählen
marc_titel_245 = 0  # Title Statement
marc_autor_100 = 0  # Main Entry - Personal Name
marc_autor_700 = 0  # Added Entry - Personal Name
marc_autor_110 = 0  # Main Entry - Corporate Name
marc_isbn_020 = 0   # ISBN
marc_issn_022 = 0   # ISSN
marc_seiten_300 = 0 # Physical Description (enthält oft Seitenzahl)

for doc in documents_marc:
    # Titel (Feld 245)
    if doc.find('.//datafield[@tag="245"]') is not None:
        marc_titel_245 += 1

    # Autor (Felder 100, 110, 700)
    has_author = False
    if doc.find('.//datafield[@tag="100"]') is not None:
        marc_autor_100 += 1
        has_author = True
    if doc.find('.//datafield[@tag="110"]') is not None:
        marc_autor_110 += 1
        has_author = True
    if doc.find('.//datafield[@tag="700"]') is not None:
        marc_autor_700 += 1
        has_author = True

    # ISBN (Feld 020)
    if doc.find('.//datafield[@tag="020"]') is not None:
        marc_isbn_020 += 1

    # ISSN (Feld 022)
    if doc.find('.//datafield[@tag="022"]') is not None:
        marc_issn_022 += 1

    # Seitenzahl (Feld 300)
    field_300 = doc.find('.//datafield[@tag="300"]')
    if field_300 is not None:
        # Prüfe ob Subfield 'a' existiert (enthält meist Seitenzahlen)
        if field_300.find('.//subfield[@code="a"]') is not None:
            marc_seiten_300 += 1

# Autoren kombiniert (mindestens ein Autorenfeld)
marc_autor_gesamt = len(set(
    [doc.get('idn') for doc in documents_marc
     if doc.find('.//datafield[@tag="100"]') is not None or
        doc.find('.//datafield[@tag="110"]') is not None or
        doc.find('.//datafield[@tag="700"]') is not None]
))

print(f"   Total: {marc_total:,} Records")

# ============================================================================
# VERGLEICHSTABELLE
# ============================================================================
print("\n" + "=" * 100)
print("VERGLEICHSTABELLE - Vollständigkeit nach Datenquelle")
print("=" * 100)
print()

# Header
print(f"{'Feld':<25} | {'MAB (XML)':<20} | {'CSV (preprocessed)':<20} | {'MARC21 (XML)':<20}")
print("-" * 100)

# Zeile: Total Records
print(f"{'TOTAL RECORDS':<25} | {mab_total:>10,} (100.0%) | {csv_total:>10,} (100.0%) | {marc_total:>10,} (100.0%)")
print("-" * 100)

# Zeile: Titel
mab_titel_pct = (mab_titel_331 / mab_total * 100) if mab_total > 0 else 0
csv_titel_pct = (csv_titel / csv_total * 100) if csv_total > 0 else 0
marc_titel_pct = (marc_titel_245 / marc_total * 100) if marc_total > 0 else 0
print(f"{'Titel':<25} | {mab_titel_331:>10,} ({mab_titel_pct:>5.1f}%) | {csv_titel:>10,} ({csv_titel_pct:>5.1f}%) | {marc_titel_245:>10,} ({marc_titel_pct:>5.1f}%)")

# Zeile: Autor
mab_autor_pct = (mab_autor_100 / mab_total * 100) if mab_total > 0 else 0
csv_autor_pct = (csv_autor / csv_total * 100) if csv_total > 0 else 0
marc_autor_pct = (marc_autor_gesamt / marc_total * 100) if marc_total > 0 else 0
print(f"{'Autor':<25} | {mab_autor_100:>10,} ({mab_autor_pct:>5.1f}%) | {csv_autor:>10,} ({csv_autor_pct:>5.1f}%) | {marc_autor_gesamt:>10,} ({marc_autor_pct:>5.1f}%)")

# Zeile: ISBN
mab_isbn_pct = (mab_isbn_540 / mab_total * 100) if mab_total > 0 else 0
csv_isbn_pct = (csv_isbn / csv_total * 100) if csv_total > 0 else 0
marc_isbn_pct = (marc_isbn_020 / marc_total * 100) if marc_total > 0 else 0
print(f"{'ISBN':<25} | {mab_isbn_540:>10,} ({mab_isbn_pct:>5.1f}%) | {csv_isbn:>10,} ({csv_isbn_pct:>5.1f}%) | {marc_isbn_020:>10,} ({marc_isbn_pct:>5.1f}%)")

# Zeile: ISSN
mab_issn_pct = (mab_issn_542 / mab_total * 100) if mab_total > 0 else 0
csv_issn_pct = (csv_issn / csv_total * 100) if csv_total > 0 else 0
marc_issn_pct = (marc_issn_022 / marc_total * 100) if marc_total > 0 else 0
print(f"{'ISSN':<25} | {mab_issn_542:>10,} ({mab_issn_pct:>5.1f}%) | {csv_issn:>10,} ({csv_issn_pct:>5.1f}%) | {marc_issn_022:>10,} ({marc_issn_pct:>5.1f}%)")

# Zeile: Seitenzahl
mab_seiten_pct = (mab_seiten_433 / mab_total * 100) if mab_total > 0 else 0
csv_seiten_pct = (csv_seiten / csv_total * 100) if csv_total > 0 else 0
marc_seiten_pct = (marc_seiten_300 / marc_total * 100) if marc_total > 0 else 0
print(f"{'Seitenzahl':<25} | {mab_seiten_433:>10,} ({mab_seiten_pct:>5.1f}%) | {csv_seiten:>10,} ({csv_seiten_pct:>5.1f}%) | {marc_seiten_300:>10,} ({marc_seiten_pct:>5.1f}%)")

print("=" * 100)

# ============================================================================
# ZUSÄTZLICHE DETAILS
# ============================================================================
print("\nFELD-DETAILS:")
print("-" * 100)
print("\nMAB (VDEH_mab_all.xml):")
print(f"  - Feld 331 (Hauptsachtitel): {mab_titel_331:,}")
print(f"  - Feld 100 (Verfasser): {mab_autor_100:,}")
print(f"  - Feld 540 (ISBN): {mab_isbn_540:,}")
print(f"  - Feld 542 (ISSN): {mab_issn_542:,}")
print(f"  - Feld 433 (Seitenzahl): {mab_seiten_433:,}")

print("\nMARC21 (marcVDEH.xml):")
print(f"  - Feld 245 (Title): {marc_titel_245:,}")
print(f"  - Feld 100 (Personal Name): {marc_autor_100:,}")
print(f"  - Feld 110 (Corporate Name): {marc_autor_110:,}")
print(f"  - Feld 700 (Added Entry): {marc_autor_700:,}")
print(f"  - Gesamt Autoren (mind. 1 Feld): {marc_autor_gesamt:,}")
print(f"  - Feld 020 (ISBN): {marc_isbn_020:,}")
print(f"  - Feld 022 (ISSN): {marc_issn_022:,}")
print(f"  - Feld 300 (Physical Desc.): {marc_seiten_300:,}")

print("\n" + "=" * 100)
print("EMPFEHLUNG:")
print("-" * 100)
print("Die MARC21-Datei (marcVDEH.xml) hat die beste Titel-Vollständigkeit (99.97%).")
print("Für ISBN/ISSN-basiertes Enrichment sind alle Quellen unvollständig (~18-68% ISBN).")
print("Die CSV-Datei kombiniert mehrere Felder und ist für Datenqualitätsberichte optimal.")
print("=" * 100)
