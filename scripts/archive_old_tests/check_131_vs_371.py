#!/usr/bin/env python3
"""Check the discrepancy between 131 and 371 authors."""

import pandas as pd

df_01 = pd.read_parquet('data/vdeh/processed/01_loaded_data.parquet')
df_04 = pd.read_parquet('data/vdeh/processed/04_dnb_enriched_data.parquet')
df_05 = pd.read_parquet('data/vdeh/processed/05_fused_data.parquet')

# Method 1: Compare 01 → 05 (reported: 131)
had_no_authors_01 = (df_01['authors_str'].isna() | (df_01['authors_str'] == ''))
has_authors_05 = (df_05['authors_str'].notna() & (df_05['authors_str'] != ''))
newly_added_01_05 = had_no_authors_01 & has_authors_05

print(f'=== COMPARISON 01 → 05 (MARC21 → Final) ===')
print(f'Records with newly added authors: {newly_added_01_05.sum():,}')

# Method 2: Compare 04 → 05 (reported: 371)
had_no_authors_04 = (df_04['authors_str'].isna() | (df_04['authors_str'] == ''))
newly_added_04_05 = had_no_authors_04 & has_authors_05

print(f'\n=== COMPARISON 04 → 05 (DNB Enriched → Final) ===')
print(f'Records with newly added authors: {newly_added_04_05.sum():,}')

# The difference
print(f'\n=== DIFFERENCE ===')
print(f'371 - 131 = {371 - 131} records')

# Find records that are in 04→05 but NOT in 01→05
in_04_05_not_01_05 = newly_added_04_05 & ~newly_added_01_05

print(f'\nRecords added in 04→05 but NOT counted in 01→05: {in_04_05_not_01_05.sum():,}')

# These records must have had authors in stage 01 but lost them by stage 04
print('\n=== INVESTIGATING THE 240 MISSING RECORDS ===')

# Check if these had authors in 01
had_authors_01 = (df_01['authors_str'].notna() & (df_01['authors_str'] != ''))

for idx in df_05[in_04_05_not_01_05].head(10).index:
    row_01 = df_01.loc[idx]
    row_04 = df_04.loc[idx]
    row_05 = df_05.loc[idx]

    print(f'\nID: {row_05["id"]}')
    print(f'  Title: {row_05["title"][:60]}...')
    print(f'  Authors (Stage 01): {row_01["authors_str"]}')
    print(f'  Authors (Stage 04): {row_04["authors_str"]}')
    print(f'  Authors (Stage 05): {row_05["authors_str"]}')
    print(f'  DNB authors: {row_04.get("dnb_authors", "N/A")}')
