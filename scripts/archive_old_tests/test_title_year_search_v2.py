#!/usr/bin/env python3
"""Test Title/Year search with better candidate selection."""

import sys
sys.path.insert(0, '/media/sz/Data/Bibo/analysis')

import pandas as pd
from src.dnb_api import query_dnb_by_title_year

# Load data
df_01 = pd.read_parquet('data/vdeh/processed/01_loaded_data.parquet')

print("=== TESTING TITLE/YEAR SEARCH - IMPROVED CANDIDATE SELECTION ===\n")

# Find records with:
# - No authors in MARC21
# - No ISBN/ISSN
# - Has title and year
# - Title length > 20 chars (to filter out abbreviations/codes)
# - Year > 1950 (more likely to be in DNB)
# - Exclude "Bericht" and technical report keywords
no_authors = (df_01['authors_str'].isna() | (df_01['authors_str'] == ''))
no_isbn = df_01['isbn'].isna()
no_issn = df_01['issn'].isna() if 'issn' in df_01.columns else True
has_title = df_01['title'].notna()
has_year = (df_01['year'].notna()) & (df_01['year'] > 1950)

# Filter out technical reports
title_ok = df_01['title'].apply(lambda t:
    len(str(t)) > 20 and
    'Bericht' not in str(t) and
    'Abschlussbericht' not in str(t) and
    'rapport' not in str(t).lower() and
    'report' not in str(t).lower() and
    'investigation' not in str(t).lower()
) if has_title.any() else pd.Series([False] * len(df_01))

candidates = df_01[no_authors & no_isbn & no_issn & has_title & has_year & title_ok]

print(f"Found {len(candidates):,} better candidates for Title/Year search\n")

# Test on first 15 records
test_sample = candidates.head(15)

print("Testing on 15 sample records:\n")

results = []

for idx, row in test_sample.iterrows():
    title = row['title']
    year = int(row['year'])

    print(f"Record {idx}:")
    print(f"  Title: {title[:70]}...")
    print(f"  Year: {year}")

    # Query DNB
    result = query_dnb_by_title_year(title, year)

    if result:
        print(f"  ✓ FOUND:")
        print(f"    DNB Title: {result.get('title', 'N/A')[:60]}...")

        dnb_authors = result.get('authors', 'N/A')
        print(f"    DNB Authors: {dnb_authors if dnb_authors else 'N/A'}")
        print(f"    DNB Year: {result.get('year', 'N/A')}")
        print(f"    DNB ISBN: {result.get('isbn', 'N/A')}")

        results.append({
            'vdeh_id': row['id'],
            'vdeh_title': title,
            'vdeh_year': year,
            'dnb_title': result.get('title'),
            'dnb_authors': result.get('authors'),
            'dnb_year': result.get('year'),
            'dnb_isbn': result.get('isbn'),
        })
    else:
        print(f"  ✗ NOT FOUND")

    print()

# Summary
print(f"\n=== SUMMARY ===")
print(f"Tested: 15 records")
print(f"Found: {len(results)} matches ({len(results)/15*100:.0f}%)")

if results:
    with_authors = sum(1 for r in results if r['dnb_authors'])
    with_isbn = sum(1 for r in results if r['dnb_isbn'])

    print(f"\nMatches with authors: {with_authors} ({with_authors/len(results)*100:.0f}%)")
    print(f"Matches with ISBN: {with_isbn} ({with_isbn/len(results)*100:.0f}%)")

    # Show some successful matches
    if with_authors > 0:
        print(f"\n📚 Sample successful matches:")
        for i, r in enumerate([r for r in results if r['dnb_authors']][:3], 1):
            print(f"\n{i}. VDEH: {r['vdeh_title'][:60]}...")
            print(f"   DNB:  {r['dnb_title'][:60]}...")
            print(f"   Authors found: {r['dnb_authors']}")

print("\n✅ Test complete!")
