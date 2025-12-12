#!/usr/bin/env python3
"""Trace author changes through all pipeline stages."""

import pandas as pd

# Load all stages
df_01 = pd.read_parquet('data/vdeh/processed/01_loaded_data.parquet')
df_02 = pd.read_parquet('data/vdeh/processed/02_preprocessed_data.parquet')
df_03 = pd.read_parquet('data/vdeh/processed/03_language_detected_data.parquet')
df_04 = pd.read_parquet('data/vdeh/processed/04_dnb_enriched_data.parquet')
df_05 = pd.read_parquet('data/vdeh/processed/05_fused_data.parquet')

print('=== AUTHOR COUNT THROUGH ALL STAGES ===\n')

stages = [
    ('01 - MARC21 Raw', df_01),
    ('02 - Preprocessed', df_02),
    ('03 - Language Detected', df_03),
    ('04 - DNB Enriched', df_04),
    ('05 - Fused', df_05)
]

for stage_name, df in stages:
    has_authors = (df['authors_str'].notna() & (df['authors_str'] != '')).sum()
    missing_authors = (df['authors_str'].isna() | (df['authors_str'] == '')).sum()
    print(f'{stage_name}:')
    print(f'  With authors: {has_authors:,}')
    print(f'  Without authors: {missing_authors:,}')
    print()

# Calculate increments
print('=== INCREMENTAL CHANGES ===\n')

prev_count = (df_01['authors_str'].notna() & (df_01['authors_str'] != '')).sum()

for i, (stage_name, df) in enumerate(stages[1:], 1):
    curr_count = (df['authors_str'].notna() & (df['authors_str'] != '')).sum()
    delta = curr_count - prev_count

    print(f'Stage {i:02d} → {i+1:02d}: {delta:+,} authors')
    prev_count = curr_count

# Check specific ID to see what happened
print('\n=== EXAMPLE TRACE: Record 000000060 ===\n')

rec_id = '000000060'

for stage_name, df in stages:
    if rec_id in df['id'].values:
        row = df[df['id'] == rec_id].iloc[0]
        print(f'{stage_name}:')
        print(f'  authors_str: {row["authors_str"]}')
        if 'dnb_authors' in row:
            print(f'  dnb_authors: {row.get("dnb_authors", "N/A")}')
        if 'dnb_authors_ta' in row:
            print(f'  dnb_authors_ta: {row.get("dnb_authors_ta", "N/A")}')
        if 'fusion_authors_source' in row:
            print(f'  fusion_authors_source: {row.get("fusion_authors_source", "N/A")}')
        print()
