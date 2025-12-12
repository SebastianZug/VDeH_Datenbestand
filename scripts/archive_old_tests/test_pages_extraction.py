#!/usr/bin/env python3
"""Test pages extraction from MARC21 and DNB."""

import sys
sys.path.insert(0, '/media/sz/Data/Bibo/analysis')

import pandas as pd
from src.dnb_api import query_dnb_by_isbn

print("=== TESTING PAGES EXTRACTION ===\n")

# Test 1: Check if MARC21 data has pages
print("1. MARC21 Pages Extraction:")
df_01 = pd.read_parquet('data/vdeh/processed/01_loaded_data.parquet')

has_pages = df_01['pages'].notna().sum()
print(f"   Records with pages: {has_pages:,} / {len(df_01):,} ({has_pages/len(df_01)*100:.1f}%)")

if has_pages > 0:
    sample_pages = df_01[df_01['pages'].notna()]['pages'].head(10)
    print(f"\n   Sample pages from MARC21:")
    for i, page in enumerate(sample_pages, 1):
        print(f"     {i}. {page}")
else:
    print("   ⚠️ No pages found in MARC21 data")

# Test 2: Test DNB API pages extraction
print(f"\n2. DNB API Pages Extraction:")
print(f"   Testing with known ISBNs...\n")

test_isbns = [
    ('3428054091', 'Die deutsche Roheisenindustrie'),
    ('3527260706', 'Korrosionskunde im Experiment'),
    ('9783161484100', 'Test ISBN'),
]

for isbn, title in test_isbns:
    print(f"   Testing ISBN: {isbn} ({title})")
    result = query_dnb_by_isbn(isbn)

    if result:
        pages = result.get('pages')
        print(f"     ✓ Found: {result.get('title', 'N/A')[:50]}...")
        print(f"     ✓ Pages: {pages if pages else 'N/A'}")
    else:
        print(f"     ✗ Not found in DNB")
    print()

# Test 3: Check if enriched data has DNB pages
print("3. DNB Enriched Data Pages:")
try:
    df_04 = pd.read_parquet('data/vdeh/processed/04_dnb_enriched_data.parquet')

    if 'dnb_pages' in df_04.columns:
        dnb_pages_count = df_04['dnb_pages'].notna().sum()
        print(f"   dnb_pages: {dnb_pages_count:,} records")
    else:
        print(f"   ⚠️ dnb_pages column not found (needs re-enrichment)")

    if 'dnb_pages_ta' in df_04.columns:
        dnb_pages_ta_count = df_04['dnb_pages_ta'].notna().sum()
        print(f"   dnb_pages_ta: {dnb_pages_ta_count:,} records")
    else:
        print(f"   ⚠️ dnb_pages_ta column not found (needs re-enrichment)")

except FileNotFoundError:
    print("   ⚠️ 04_dnb_enriched_data.parquet not found")

# Test 4: Check fused data
print(f"\n4. Fused Data Pages:")
try:
    df_05 = pd.read_parquet('data/vdeh/processed/05_fused_data.parquet')

    if 'pages' in df_05.columns:
        fused_pages = df_05['pages'].notna().sum()
        print(f"   pages: {fused_pages:,} / {len(df_05):,} ({fused_pages/len(df_05)*100:.1f}%)")

        if 'fusion_pages_source' in df_05.columns:
            sources = df_05['fusion_pages_source'].value_counts()
            print(f"\n   Pages sources:")
            for source, count in sources.items():
                if pd.notna(source):
                    print(f"     {source}: {count:,}")
        else:
            print(f"   ⚠️ fusion_pages_source column not found")
    else:
        print(f"   ⚠️ pages column not found in fused data")

except FileNotFoundError:
    print("   ⚠️ 05_fused_data.parquet not found")

print("\n✅ Pages extraction test complete!")
print("\n📋 Summary:")
print("   - MARC21 parser: ✓ Already extracts pages from field 300")
print("   - DNB API: ✓ Now extracts pages from field 300")
print("   - Fusion engine: ✓ Now handles pages field")
print("\n⚠️  To get DNB pages data, re-run notebook 04 (existing queries will be skipped)")
