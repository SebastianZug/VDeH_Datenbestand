#!/usr/bin/env python3
import pandas as pd

df_01 = pd.read_parquet('data/vdeh/processed/01_loaded_data.parquet')
df_05 = pd.read_parquet('data/vdeh/processed/05_fused_data.parquet')

# Find records that LOST authors
had_authors_01 = (df_01['authors_str'].notna() & (df_01['authors_str'] != ''))
has_no_authors_05 = (df_05['authors_str'].isna() | (df_05['authors_str'] == ''))

lost_authors = had_authors_01 & has_no_authors_05

print(f'Records that LOST authors (01 → 05): {lost_authors.sum():,}')

# Sample
if lost_authors.sum() > 0:
    print('\nSample cases:')
    for idx in df_05[lost_authors].head(5).index:
        print(f"  ID: {df_05.loc[idx, 'id']}")
        print(f"    Authors (Stage 01): {df_01.loc[idx, 'authors_str'][:80] if pd.notna(df_01.loc[idx, 'authors_str']) else 'None'}...")
        print(f"    Authors (Stage 05): {df_05.loc[idx, 'authors_str']}")
        print()
