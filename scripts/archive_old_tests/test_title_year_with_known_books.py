#!/usr/bin/env python3
"""Test Title/Year search with known German books to verify the method works."""

import sys
sys.path.insert(0, '/media/sz/Data/Bibo/analysis')

from src.dnb_api import query_dnb_by_title_year

print("=== TESTING TITLE/YEAR WITH KNOWN GERMAN BOOKS ===\n")
print("Testing with well-known German books that should be in DNB:\n")

# Test with known German literature
test_cases = [
    ("Die Verwandlung", 1915),
    ("Der Prozess", 1925),
    ("Steppenwolf", 1927),
    ("Berlin Alexanderplatz", 1929),
    ("Tschick", 2010),
    ("Im Westen nichts Neues", 1929),
    ("Die Leiden des jungen Werther", 1774),
]

results = []

for title, year in test_cases:
    print(f"Searching: '{title}' ({year})")

    result = query_dnb_by_title_year(title, year)

    if result:
        print(f"  ✓ FOUND:")
        print(f"    Title: {result.get('title', 'N/A')}")
        print(f"    Authors: {result.get('authors', 'N/A')}")
        print(f"    Year: {result.get('year', 'N/A')}")
        print(f"    ISBN: {result.get('isbn', 'N/A')}")
        results.append(title)
    else:
        print(f"  ✗ NOT FOUND")

    print()

print(f"\n=== SUMMARY ===")
print(f"Tested: {len(test_cases)} known books")
print(f"Found: {len(results)} matches ({len(results)/len(test_cases)*100:.0f}%)")

if len(results) > 0:
    print(f"\n✅ Title/Year search method is working correctly!")
else:
    print(f"\n⚠️  No matches found - DNB API may be down or SRU query syntax incorrect")

print("\n=== NOW TESTING WITH ACTUAL VDEH DATA ===\n")

import pandas as pd

# Load VDEH data with authors (to verify against DNB)
df_01 = pd.read_parquet('data/vdeh/processed/01_loaded_data.parquet')

# Find records that HAVE authors (so we can check if DNB finds same authors)
has_authors = (df_01['authors_str'].notna() & (df_01['authors_str'] != ''))
has_title = df_01['title'].notna()
has_year = df_01['year'].notna()

# German titles (more likely to be in DNB)
is_german = df_01['language'].isin(['ger', 'de']) if 'language' in df_01.columns else True

test_records = df_01[has_authors & has_title & has_year & is_german].head(5)

print(f"Testing with 5 VDEH records that have authors:\n")

for idx, row in test_records.iterrows():
    title = row['title']
    year = int(row['year']) if pd.notna(row['year']) else 0
    vdeh_authors = row['authors_str']

    print(f"VDEH Record {idx}:")
    print(f"  Title: {title[:60]}...")
    print(f"  Year: {year}")
    print(f"  VDEH Authors: {vdeh_authors}")

    result = query_dnb_by_title_year(title, year)

    if result:
        dnb_authors = result.get('authors', 'N/A')
        print(f"  ✓ DNB Match:")
        print(f"    DNB Authors: {dnb_authors}")

        # Check if authors match
        if str(vdeh_authors).lower() in str(dnb_authors).lower() or str(dnb_authors).lower() in str(vdeh_authors).lower():
            print(f"    → Authors MATCH ✓")
        else:
            print(f"    → Authors DIFFERENT (might be variant spellings)")
    else:
        print(f"  ✗ NOT FOUND in DNB")

    print()

print("✅ Test complete!")
