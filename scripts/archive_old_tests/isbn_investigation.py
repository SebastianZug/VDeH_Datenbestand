#!/usr/bin/env python3
"""Investigate where the 6,355 new ISBNs come from."""

import pandas as pd

df_01 = pd.read_parquet('data/vdeh/processed/01_loaded_data.parquet')
df_dnb_raw = pd.read_parquet('data/vdeh/processed/dnb_raw_data.parquet')
df_dnb_ta = pd.read_parquet('data/vdeh/processed/dnb_title_author_data.parquet')

print('=== ISBN DISCOVERY INVESTIGATION ===\n')

# Method 1: ISBN/ISSN search
has_dnb_isbn_raw = df_dnb_raw['dnb_isbn'].notna()
marc_had_isbn_raw = df_01['isbn'].notna()

new_from_raw = (has_dnb_isbn_raw & ~marc_had_isbn_raw).sum()

print(f'ISBN/ISSN method:')
print(f'  Total DNB ISBNs found: {has_dnb_isbn_raw.sum():,}')
print(f'  NEW (MARC21 had none): {new_from_raw:,}')

# Method 2: Title/Author search
has_dnb_isbn_ta = df_dnb_ta['dnb_isbn'].notna()

# Create a proper boolean index by reindexing
marc_isbn_series = df_01['isbn']
# Align the indices
new_from_ta_mask = pd.Series(False, index=df_dnb_ta.index)
for idx in df_dnb_ta[has_dnb_isbn_ta].index:
    if idx in marc_isbn_series.index:
        if pd.isna(marc_isbn_series.loc[idx]):
            new_from_ta_mask.loc[idx] = True

new_from_ta = new_from_ta_mask.sum()

print(f'\nTitle/Author method:')
print(f'  Total DNB ISBNs found: {has_dnb_isbn_ta.sum():,}')
print(f'  NEW (MARC21 had none): {new_from_ta:,}')

print(f'\n=== TOTAL ===')
print(f'Potential new ISBNs from DNB: {new_from_raw + new_from_ta:,}')

# But are they in the enriched dataset?
print(f'\n=== WHERE ARE THEY NOW? ===')

df_04 = pd.read_parquet('data/vdeh/processed/04_dnb_enriched_data.parquet')
df_05 = pd.read_parquet('data/vdeh/processed/05_fused_data.parquet')

# Check if dnb_isbn or dnb_isbn_ta columns exist
print(f'\nStage 04 columns with "isbn": {[col for col in df_04.columns if "isbn" in col.lower()]}')
print(f'Stage 05 columns with "isbn": {[col for col in df_05.columns if "isbn" in col.lower()]}')

# Check main isbn column
print(f'\nMain ISBN column:')
print(f'  Stage 01: {df_01["isbn"].notna().sum():,} records')
print(f'  Stage 04: {df_04["isbn"].notna().sum():,} records')
print(f'  Stage 05: {df_05["isbn"].notna().sum():,} records')

# The issue: DNB ISBNs are stored separately!
if 'dnb_isbn' in df_04.columns:
    print(f'\nDNB ISBN (separate column):')
    print(f'  Stage 04 dnb_isbn: {df_04["dnb_isbn"].notna().sum():,} records')

    # How many of these are NEW?
    marc_no_isbn = df_01['isbn'].isna()
    has_dnb_isbn_04 = df_04['dnb_isbn'].notna()

    could_be_new = (marc_no_isbn & has_dnb_isbn_04).sum()
    print(f'  Could be NEW (MARC21 empty, DNB filled): {could_be_new:,}')

if 'dnb_isbn_ta' in df_04.columns:
    print(f'\nDNB ISBN from Title/Author (separate column):')
    print(f'  Stage 04 dnb_isbn_ta: {df_04["dnb_isbn_ta"].notna().sum():,} records')

    # How many of these are NEW?
    marc_no_isbn = df_01['isbn'].isna()
    has_dnb_isbn_ta_04 = df_04['dnb_isbn_ta'].notna()

    could_be_new_ta = (marc_no_isbn & has_dnb_isbn_ta_04).sum()
    print(f'  Could be NEW (MARC21 empty, DNB filled): {could_be_new_ta:,}')

print('\n=== CONCLUSION ===')
print('The DNB ISBNs are stored in SEPARATE columns (dnb_isbn, dnb_isbn_ta)')
print('They were NEVER copied to the main "isbn" column!')
print('Therefore: +0 new ISBNs in the main column')
