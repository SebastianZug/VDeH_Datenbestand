#!/usr/bin/env python3
"""Analyze the author gap between stage 01 and stage 05."""

import pandas as pd

# Load stage 01 (MARC21 raw)
df_01 = pd.read_parquet('data/vdeh/processed/01_loaded_data.parquet')

# Load stage 05 (final fused)
df_05 = pd.read_parquet('data/vdeh/processed/05_fused_data.parquet')

print('=== STAGE 01 (MARC21 Raw) ===')
print(f'Total records: {len(df_01):,}')
has_authors_01 = (df_01['authors_str'].notna() & (df_01['authors_str'] != '')).sum()
missing_authors_01 = (df_01['authors_str'].isna() | (df_01['authors_str'] == '')).sum()
print(f'Records with authors: {has_authors_01:,}')
print(f'Records WITHOUT authors: {missing_authors_01:,}')

print('\n=== STAGE 05 (Final Fused) ===')
print(f'Total records: {len(df_05):,}')
has_authors_05 = (df_05['authors_str'].notna() & (df_05['authors_str'] != '')).sum()
missing_authors_05 = (df_05['authors_str'].isna() | (df_05['authors_str'] == '')).sum()
print(f'Records with authors: {has_authors_05:,}')
print(f'Records WITHOUT authors: {missing_authors_05:,}')

print('\n=== GAP ANALYSIS ===')
gap_filled = missing_authors_01 - missing_authors_05

print(f'Missing in stage 01: {missing_authors_01:,}')
print(f'Missing in stage 05: {missing_authors_05:,}')
print(f'Gap filled: {gap_filled:,} ({gap_filled/missing_authors_01*100:.2f}%)')

# Check metadata
print('\n=== METADATA CROSS-CHECK ===')
print('From 05_metadata.json:')
print(f'  Before (stage 04): 17,605 records with authors')
print(f'  After (stage 05): 17,667 records with authors')
print(f'  Improvement: +62 authors')

print('\nBut vdeh_completeness in metadata shows:')
print(f'  Stage 04 (before fusion): 17,536 authors')
print(f'  Difference: 17,605 - 17,536 = 69')

# Let's also check stage 03
df_03 = pd.read_parquet('data/vdeh/processed/03_language_detected_data.parquet')
has_authors_03 = (df_03['authors_str'].notna() & (df_03['authors_str'] != '')).sum()
missing_authors_03 = (df_03['authors_str'].isna() | (df_03['authors_str'] == '')).sum()

print('\n=== STAGE 03 (Language Detected) ===')
print(f'Records with authors: {has_authors_03:,}')
print(f'Records WITHOUT authors: {missing_authors_03:,}')
print(f'Difference from stage 01: {has_authors_03 - has_authors_01:,}')
