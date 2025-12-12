#!/usr/bin/env python3
"""Analyze where the 131 new authors came from."""

import pandas as pd

# Load relevant stages
df_01 = pd.read_parquet('data/vdeh/processed/01_loaded_data.parquet')
df_04 = pd.read_parquet('data/vdeh/processed/04_dnb_enriched_data.parquet')
df_05 = pd.read_parquet('data/vdeh/processed/05_fused_data.parquet')

print('=== AUTHOR ENRICHMENT SOURCE ANALYSIS ===\n')

# Stage 01 → 04: DNB Enrichment adds authors
has_authors_01 = (df_01['authors_str'].notna() & (df_01['authors_str'] != '')).sum()
has_authors_04 = (df_04['authors_str'].notna() & (df_04['authors_str'] != '')).sum()
has_authors_05 = (df_05['authors_str'].notna() & (df_05['authors_str'] != '')).sum()

print(f'Stage 01 (MARC21 raw): {has_authors_01:,} records with authors')
print(f'Stage 04 (DNB enriched): {has_authors_04:,} records with authors')
print(f'Stage 05 (Fused): {has_authors_05:,} records with authors')
print()
print(f'Stage 01 → 04: +{has_authors_04 - has_authors_01:,} authors (DNB enrichment)')
print(f'Stage 04 → 05: +{has_authors_05 - has_authors_04:,} authors (KI fusion)')
print(f'Total improvement: +{has_authors_05 - has_authors_01:,} authors')

# Check DNB sources
print('\n=== DNB ENRICHMENT DETAILS ===')

# DNB ISBN/ISSN method
dnb_id_has_authors = (df_04['dnb_authors'].notna() & (df_04['dnb_authors'] != '')).sum()
print(f'DNB ISBN/ISSN method provided authors: {dnb_id_has_authors:,} records')

# DNB Title/Author method
dnb_ta_has_authors = (df_04['dnb_authors_ta'].notna() & (df_04['dnb_authors_ta'] != '')).sum()
print(f'DNB Title/Author method provided authors: {dnb_ta_has_authors:,} records')

# How many records had NO authors in MARC21 but got them from DNB?
marc_no_authors = (df_01['authors_str'].isna() | (df_01['authors_str'] == ''))
dnb_provided_any = ((df_04['dnb_authors'].notna() & (df_04['dnb_authors'] != '')) |
                    (df_04['dnb_authors_ta'].notna() & (df_04['dnb_authors_ta'] != '')))

gap_filled_by_dnb = (marc_no_authors & dnb_provided_any).sum()
print(f'\nRecords with NO MARC21 authors but DNB provided authors: {gap_filled_by_dnb:,}')

# But how many of those made it to the final dataset?
# Check if stage 04 has these filled
marc_no_authors_04 = (df_01['authors_str'].isna() | (df_01['authors_str'] == ''))
stage_04_has_authors = (df_04['authors_str'].notna() & (df_04['authors_str'] != ''))
newly_filled_04 = (marc_no_authors_04 & stage_04_has_authors).sum()

print(f'Records actually filled in stage 04: {newly_filled_04:,}')

# Check fusion impact
marc_no_authors_05 = (df_01['authors_str'].isna() | (df_01['authors_str'] == ''))
stage_05_has_authors = (df_05['authors_str'].notna() & (df_05['authors_str'] != ''))
newly_filled_05 = (marc_no_authors_05 & stage_05_has_authors).sum()

print(f'Records actually filled in stage 05 (final): {newly_filled_05:,}')

# Sample some cases
print('\n=== SAMPLE CASES WHERE AUTHORS WERE ADDED ===')
newly_filled_mask = marc_no_authors_05 & stage_05_has_authors
sample_filled = df_05[newly_filled_mask].head(5)

for idx, row in sample_filled.iterrows():
    print(f"\nID: {row['id']}")
    print(f"  Title: {row['title'][:80]}...")
    print(f"  Authors (final): {row['authors_str']}")

# Check if these came from DNB
if 'dnb_authors' in df_04.columns:
    dnb_row = df_04.loc[idx]
    if pd.notna(dnb_row['dnb_authors']) and dnb_row['dnb_authors'] != '':
        print(f"  DNB authors (ID method): {dnb_row['dnb_authors']}")
    if pd.notna(dnb_row['dnb_authors_ta']) and dnb_row['dnb_authors_ta'] != '':
        print(f"  DNB authors (TA method): {dnb_row['dnb_authors_ta']}")
