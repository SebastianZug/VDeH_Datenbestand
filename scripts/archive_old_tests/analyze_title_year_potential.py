#!/usr/bin/env python3
"""Analyze how many VDEH records might benefit from Title/Year search."""

import sys
sys.path.insert(0, '/media/sz/Data/Bibo/analysis')

import pandas as pd

# Load data
df_01 = pd.read_parquet('data/vdeh/processed/01_loaded_data.parquet')
df_04 = pd.read_parquet('data/vdeh/processed/04_dnb_enriched_data.parquet')

print("=== ANALYSIS: TITLE/YEAR SEARCH POTENTIAL ===\n")

# Records missing authors
no_authors = (df_01['authors_str'].isna() | (df_01['authors_str'] == ''))
print(f"Records without authors: {no_authors.sum():,}")

# Already covered by existing methods
has_isbn = df_01['isbn'].notna()
has_issn = df_01['issn'].notna() if 'issn' in df_01.columns else pd.Series([False] * len(df_01))

dnb_id_found = (df_04['dnb_authors'].notna() & (df_04['dnb_authors'] != ''))
dnb_ta_found = (df_04['dnb_authors_ta'].notna() & (df_04['dnb_authors_ta'] != ''))

already_found = dnb_id_found | dnb_ta_found

print(f"Already found via ISBN/ISSN: {(no_authors & (has_isbn | has_issn) & already_found).sum():,}")
print(f"Already found via Title/Author: {(no_authors & ~(has_isbn | has_issn) & already_found).sum():,}")

# Potential for Title/Year
has_title = df_01['title'].notna()
has_year = df_01['year'].notna()

potential_ty = no_authors & ~already_found & has_title & has_year

print(f"\nPotential for Title/Year search: {potential_ty.sum():,}")

# Analyze content type
print(f"\n=== CONTENT TYPE ANALYSIS ===\n")

sample = df_01[potential_ty].head(100)

# Check for technical report keywords
technical_keywords = [
    'Bericht', 'Abschlussbericht', 'rapport', 'report',
    'investigation', 'proceedings', 'conference', 'symposium',
    'Kongress', 'Tagung', 'Seminar'
]

is_technical = sample['title'].apply(lambda t:
    any(kw.lower() in str(t).lower() for kw in technical_keywords)
)

print(f"Sample of 100 potential Title/Year records:")
print(f"  Technical reports/proceedings: {is_technical.sum()} ({is_technical.sum()/100*100:.0f}%)")
print(f"  Potentially published books: {(~is_technical).sum()} ({(~is_technical).sum()/100*100:.0f}%)")

# Extrapolate
total_potential = potential_ty.sum()
estimated_books = int(total_potential * (~is_technical).sum() / 100)
estimated_technical = int(total_potential * is_technical.sum() / 100)

print(f"\nExtrapolated to all {total_potential:,} records:")
print(f"  Technical reports (unlikely in DNB): ~{estimated_technical:,} ({estimated_technical/total_potential*100:.0f}%)")
print(f"  Published books (might be in DNB): ~{estimated_books:,} ({estimated_books/total_potential*100:.0f}%)")

# Expected yield
# DNB coverage for published books: assume ~20-30% (conservative)
expected_yield_low = int(estimated_books * 0.20)
expected_yield_high = int(estimated_books * 0.30)

print(f"\n=== EXPECTED YIELD ===")
print(f"Expected authors found via Title/Year: {expected_yield_low:,} - {expected_yield_high:,}")
print(f"(Assuming 20-30% DNB coverage for non-technical books)")

# Cost-benefit
print(f"\n=== COST-BENEFIT ===")
print(f"Current author enrichment: 371 (from 40,769 missing)")
print(f"Additional via Title/Year: {expected_yield_low:,} - {expected_yield_high:,}")
print(f"Total improvement: {371 + expected_yield_low:,} - {371 + expected_yield_high:,}")
print(f"Success rate improvement: {(371 + expected_yield_low) / 40769 * 100:.1f}% - {(371 + expected_yield_high) / 40769 * 100:.1f}%")

# API load
print(f"\nAPI queries required: ~{total_potential:,}")
print(f"At 1 query/sec with retries: ~{total_potential / 3600:.1f} hours")

print("\n=== RECOMMENDATION ===")
if expected_yield_high > 100:
    print("✓ IMPLEMENT - Expected yield justifies the effort")
else:
    print("⚠️  LOW YIELD - Most VDEH records are technical reports not in DNB")
    print("   Consider implementing but with realistic expectations")

print("\n✅ Analysis complete!")
