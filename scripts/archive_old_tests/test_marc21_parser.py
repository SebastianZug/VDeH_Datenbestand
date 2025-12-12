#!/usr/bin/env python3
"""
Test-Script für den MARC21 Parser
Testet die Extraktion von bibliographischen Daten aus marcVDEH.xml
"""

import sys
sys.path.insert(0, '/media/sz/Data/Bibo/analysis')

from src.parsers.marc21_parser import parse_bibliography, analyze_bibliography_data, get_sample_records
import logging
import pandas as pd

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("=" * 80)
print("MARC21 PARSER TEST")
print("=" * 80)

# Test mit ersten 100 Records
print("\n[1/3] Parsing erste 100 Records...")
df = parse_bibliography('/media/sz/Data/Bibo/data/marcVDEH.xml', max_records=100)

print(f"\n✓ Erfolgreich geparst: {len(df):,} Records")
print(f"✓ Spalten: {list(df.columns)}")

# Vollständigkeits-Check
print("\n[2/3] Vollständigkeits-Check...")
total = len(df)
titel_count = df['title'].notna().sum()
autor_count = df['num_authors'].gt(0).sum()
jahr_count = df['year'].notna().sum()
isbn_count = df['isbn'].notna().sum()
pages_count = df['pages'].notna().sum()

print(f"  Titel:      {titel_count:>3}/{total} ({titel_count/total*100:>5.1f}%)")
print(f"  Autoren:    {autor_count:>3}/{total} ({autor_count/total*100:>5.1f}%)")
print(f"  Jahr:       {jahr_count:>3}/{total} ({jahr_count/total*100:>5.1f}%)")
print(f"  ISBN:       {isbn_count:>3}/{total} ({isbn_count/total*100:>5.1f}%)")
print(f"  Seitenzahl: {pages_count:>3}/{total} ({pages_count/total*100:>5.1f}%)")

# Erwartete Werte prüfen
assert titel_count / total > 0.95, f"Titel-Vollständigkeit zu niedrig: {titel_count/total*100:.1f}%"
assert autor_count / total > 0.25, f"Autoren-Vollständigkeit zu niedrig: {autor_count/total*100:.1f}%"
print("\n✓ Vollständigkeits-Checks bestanden!")

# Beispiel-Records anzeigen
print("\n[3/3] Beispiel-Records:")
print("-" * 80)
samples = get_sample_records(df, n=3)
for idx, row in samples.iterrows():
    print(f"\nRecord {idx + 1}:")
    print(f"  ID:        {row['id']}")
    print(f"  Titel:     {row['title'][:80] if row['title'] else 'N/A'}...")
    print(f"  Autoren:   {row['authors_str'][:60] if row['authors_str'] else 'N/A'}")
    print(f"  Jahr:      {row['year'] if pd.notna(row['year']) else 'N/A'}")
    print(f"  Verlag:    {row['publisher'][:50] if row['publisher'] else 'N/A'}")
    print(f"  ISBN:      {row['isbn'] if row['isbn'] else 'N/A'}")
    if 'pages' in row and row['pages']:
        print(f"  Seiten:    {row['pages']}")

print("\n" + "=" * 80)
print("✅ MARC21 PARSER TEST ERFOLGREICH!")
print("=" * 80)

# Analyse ausführen
print("\n[BONUS] Vollständige Analyse:")
analyze_bibliography_data(df)
