#!/usr/bin/env python3
"""Test the new Title/Year search method on sample records."""

import sys
sys.path.insert(0, '/media/sz/Data/Bibo/analysis')

import pandas as pd
from src.dnb_api import query_dnb_by_title_year

# Load data to find test candidates
df_01 = pd.read_parquet('data/vdeh/processed/01_loaded_data.parquet')

print("=== TESTING TITLE/YEAR SEARCH METHOD ===\n")

# Find records with:
# - No authors in MARC21
# - No ISBN/ISSN
# - But HAS title and year
no_authors = (df_01['authors_str'].isna() | (df_01['authors_str'] == ''))
no_isbn = df_01['isbn'].isna()
no_issn = df_01['issn'].isna() if 'issn' in df_01.columns else True
has_title = df_01['title'].notna()
has_year = df_01['year'].notna()

# Candidates for Title/Year search
candidates = df_01[no_authors & no_isbn & no_issn & has_title & has_year]

print(f"Found {len(candidates):,} candidates for Title/Year search")
print(f"(Records without authors, ISBN, ISSN but with title and year)\n")

# Test on first 10 records
test_sample = candidates.head(10)

print("Testing on 10 sample records:\n")

results = []

for idx, row in test_sample.iterrows():
    title = row['title']
    year = row['year']

    print(f"Record {idx}:")
    print(f"  Title: {title[:60]}...")
    print(f"  Year: {year}")

    # Query DNB
    result = query_dnb_by_title_year(title, year)

    if result:
        print(f"  ✓ FOUND:")
        print(f"    DNB Title: {result.get('title', 'N/A')[:60]}...")
        print(f"    DNB Authors: {result.get('authors', 'N/A')}")
        print(f"    DNB Year: {result.get('year', 'N/A')}")
        print(f"    DNB ISBN: {result.get('isbn', 'N/A')}")
        print(f"    DNB Publisher: {result.get('publisher', 'N/A')}")

        results.append({
            'vdeh_id': row['id'],
            'vdeh_title': title,
            'vdeh_year': year,
            'dnb_title': result.get('title'),
            'dnb_authors': result.get('authors'),
            'dnb_year': result.get('year'),
            'dnb_isbn': result.get('isbn'),
            'dnb_publisher': result.get('publisher')
        })
    else:
        print(f"  ✗ NOT FOUND")

    print()

# Summary
print(f"\n=== SUMMARY ===")
print(f"Tested: 10 records")
print(f"Found: {len(results)} matches ({len(results)/10*100:.0f}%)")

if results:
    print(f"\nMatches with authors: {sum(1 for r in results if r['dnb_authors']):}")
    print(f"Matches with ISBN: {sum(1 for r in results if r['dnb_isbn']):}")
    print(f"Matches with publisher: {sum(1 for r in results if r['dnb_publisher']):}")

print("\n✅ Test complete!")
