#!/usr/bin/env python3
"""Analyze how authors were filled during fusion."""

import pandas as pd

# Load stage 04 (before fusion)
df_04 = pd.read_parquet('data/vdeh/processed/04_dnb_enriched_data.parquet')

# Load stage 05 (after fusion)
df_05 = pd.read_parquet('data/vdeh/processed/05_fused_data.parquet')

print('=== AUTHOR ENRICHMENT DURING FUSION ===\n')

# Identify records where authors were added
had_no_authors_04 = (df_04['authors_str'].isna() | (df_04['authors_str'] == ''))
has_authors_05 = (df_05['authors_str'].notna() & (df_05['authors_str'] != ''))

newly_added = had_no_authors_04 & has_authors_05

print(f'Records with newly added authors: {newly_added.sum():,}')

# Sample some cases
print('\n=== SAMPLE CASES (First 10) ===\n')
sample_df = df_05[newly_added].head(10)

for idx in sample_df.index:
    row_04 = df_04.loc[idx]
    row_05 = df_05.loc[idx]

    print(f"ID: {row_05['id']}")
    print(f"  Title: {row_05['title'][:70]}...")
    print(f"  VDEH authors (stage 04): {row_04['authors_str']}")
    print(f"  DNB authors (ID method): {row_04.get('dnb_authors', 'N/A')}")
    print(f"  DNB authors (TA method): {row_04.get('dnb_authors_ta', 'N/A')}")
    print(f"  FINAL authors (stage 05): {row_05['authors_str']}")
    print()

# Check if there are fusion_decision or source columns
print('\n=== CHECKING FOR FUSION METADATA ===')
fusion_cols = [col for col in df_05.columns if 'fusion' in col.lower() or 'decision' in col.lower() or 'source' in col.lower()]
print(f'Fusion-related columns: {fusion_cols}')

if fusion_cols:
    for col in fusion_cols:
        print(f'\n{col}:')
        print(df_05[newly_added][col].value_counts().head())

# Check the reverse: How many DNB authors were available but NOT used?
print('\n=== MISSED OPPORTUNITIES ===')

# DNB ID method had authors, but VDEH didn't, yet final also doesn't
dnb_id_has_authors = (df_04['dnb_authors'].notna() & (df_04['dnb_authors'] != ''))
vdeh_no_authors = (df_04['authors_str'].isna() | (df_04['authors_str'] == ''))
final_no_authors = (df_05['authors_str'].isna() | (df_05['authors_str'] == ''))

missed_id = vdeh_no_authors & dnb_id_has_authors & final_no_authors
print(f'DNB ID method had authors but were NOT used: {missed_id.sum():,}')

# DNB TA method had authors, but VDEH didn't, yet final also doesn't
dnb_ta_has_authors = (df_04['dnb_authors_ta'].notna() & (df_04['dnb_authors_ta'] != ''))
missed_ta = vdeh_no_authors & dnb_ta_has_authors & final_no_authors

print(f'DNB TA method had authors but were NOT used: {missed_ta.sum():,}')

# Total potential
potential_from_dnb = vdeh_no_authors & (dnb_id_has_authors | dnb_ta_has_authors)
print(f'\nTotal records where DNB could have provided authors: {potential_from_dnb.sum():,}')
print(f'Actually filled: {newly_added.sum():,} ({newly_added.sum()/potential_from_dnb.sum()*100:.1f}%)')

# Sample missed opportunities
print('\n=== SAMPLE MISSED OPPORTUNITIES (First 5) ===\n')
sample_missed = df_05[missed_id | missed_ta].head(5)

for idx in sample_missed.index:
    row_04 = df_04.loc[idx]
    row_05 = df_05.loc[idx]

    print(f"ID: {row_05['id']}")
    print(f"  Title: {row_05['title'][:70] if pd.notna(row_05['title']) else 'N/A'}...")
    print(f"  VDEH authors: {row_04['authors_str']}")
    print(f"  DNB authors (ID): {row_04.get('dnb_authors', 'N/A')}")
    print(f"  DNB authors (TA): {row_04.get('dnb_authors_ta', 'N/A')}")
    print(f"  FINAL authors: {row_05['authors_str']}")

    if 'ai_decision' in df_05.columns:
        print(f"  AI Decision: {row_05.get('ai_decision', 'N/A')}")
    if 'fusion_variant' in df_05.columns:
        print(f"  Fusion Variant: {row_05.get('fusion_variant', 'N/A')}")

    print()
