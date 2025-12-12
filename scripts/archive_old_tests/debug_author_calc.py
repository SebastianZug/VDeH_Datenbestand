#!/usr/bin/env python3
import pandas as pd

df_01 = pd.read_parquet('data/vdeh/processed/01_loaded_data.parquet')
df_05 = pd.read_parquet('data/vdeh/processed/05_fused_data.parquet')

# Method 1: Notebook formula
missing_01 = (df_01['authors_str'].isna() | (df_01['authors_str'] == '')).sum()
missing_05 = (df_05['authors_str'].isna() | (df_05['authors_str'] == '')).sum()
gap_closed = missing_01 - missing_05

print(f'Notebook formula (gap closure): {gap_closed:,}')
print(f'  Missing in 01: {missing_01:,}')
print(f'  Missing in 05: {missing_05:,}')
print()

# Method 2: Direct count
had_no_authors_01 = (df_01['authors_str'].isna() | (df_01['authors_str'] == ''))
has_authors_05 = (df_05['authors_str'].notna() & (df_05['authors_str'] != ''))

newly_added = (had_no_authors_01 & has_authors_05).sum()

print(f'Direct count (newly added): {newly_added:,}')

# Are they the same?
print(f'\nAre they equal? {gap_closed == newly_added}')
