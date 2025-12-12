#!/usr/bin/env python3
"""Deep analysis of author enrichment - why only 371 filled?"""

import pandas as pd

# Load data
df_01 = pd.read_parquet('data/vdeh/processed/01_loaded_data.parquet')
df_04 = pd.read_parquet('data/vdeh/processed/04_dnb_enriched_data.parquet')
df_05 = pd.read_parquet('data/vdeh/processed/05_fused_data.parquet')

print("=== DEEP ANALYSIS: AUTHOR ENRICHMENT ===\n")

# Basic stats
total = len(df_01)
had_no_authors_01 = (df_01['authors_str'].isna() | (df_01['authors_str'] == '')).sum()
has_authors_05 = (df_05['authors_str'].notna() & (df_05['authors_str'] != '')).sum()

print(f"Total records: {total:,}")
print(f"Records WITHOUT authors in MARC21: {had_no_authors_01:,} ({had_no_authors_01/total*100:.1f}%)")
print(f"Records WITH authors after pipeline: {has_authors_05:,} ({has_authors_05/total*100:.1f}%)")
print(f"Filled: {has_authors_05 - (total - had_no_authors_01):,}")

# Where could authors come from?
print(f"\n=== DNB AUTHOR AVAILABILITY ===\n")

# DNB ID method
dnb_id_has_authors = (df_04['dnb_authors'].notna() & (df_04['dnb_authors'] != '')).sum()
print(f"DNB ID method has authors: {dnb_id_has_authors:,}")

# DNB Title/Author method
dnb_ta_has_authors = (df_04['dnb_authors_ta'].notna() & (df_04['dnb_authors_ta'] != '')).sum()
print(f"DNB Title/Author method has authors: {dnb_ta_has_authors:,}")

print(f"Total DNB authors available: {dnb_id_has_authors + dnb_ta_has_authors:,}")

# How many of these are for records WITHOUT MARC21 authors?
marc_no_authors = (df_01['authors_str'].isna() | (df_01['authors_str'] == ''))

dnb_id_for_empty = (marc_no_authors & (df_04['dnb_authors'].notna()) & (df_04['dnb_authors'] != '')).sum()
dnb_ta_for_empty = (marc_no_authors & (df_04['dnb_authors_ta'].notna()) & (df_04['dnb_authors_ta'] != '')).sum()

print(f"\n=== DNB AUTHORS FOR RECORDS WITHOUT MARC21 AUTHORS ===\n")
print(f"DNB ID method (for empty MARC21): {dnb_id_for_empty:,}")
print(f"DNB Title/Author method (for empty MARC21): {dnb_ta_for_empty:,}")
print(f"Total potential: {dnb_id_for_empty + dnb_ta_for_empty:,}")

# How many were actually used?
actually_filled = (marc_no_authors & (df_05['authors_str'].notna()) & (df_05['authors_str'] != '')).sum()
print(f"\nActually filled in final dataset: {actually_filled:,}")
print(f"Utilization rate: {actually_filled / (dnb_id_for_empty + dnb_ta_for_empty) * 100:.1f}%" if (dnb_id_for_empty + dnb_ta_for_empty) > 0 else "N/A")

# Why weren't they used?
print(f"\n=== WHY WEREN'T DNB AUTHORS USED? ===\n")

# Records with DNB authors but still empty
has_dnb_authors = ((df_04['dnb_authors'].notna() & (df_04['dnb_authors'] != '')) |
                   (df_04['dnb_authors_ta'].notna() & (df_04['dnb_authors_ta'] != '')))
still_empty = (df_05['authors_str'].isna() | (df_05['authors_str'] == ''))

dnb_available_but_not_used = (marc_no_authors & has_dnb_authors & still_empty).sum()

print(f"DNB had authors, but NOT used: {dnb_available_but_not_used:,}")

# Check fusion decisions
if 'fusion_authors_source' in df_05.columns:
    print(f"\n=== FUSION AUTHORS SOURCE ANALYSIS ===\n")

    # For records that were filled
    filled_records = marc_no_authors & (df_05['authors_str'].notna()) & (df_05['authors_str'] != '')

    sources = df_05.loc[filled_records, 'fusion_authors_source'].value_counts()
    print(f"Sources for {filled_records.sum():,} filled records:")
    for source, count in sources.items():
        if pd.notna(source):
            print(f"  {source}: {count:,}")

    # For records that COULD have been filled but weren't
    not_filled = marc_no_authors & has_dnb_authors & still_empty

    if not_filled.sum() > 0:
        print(f"\n=== RECORDS WITH DNB AUTHORS BUT NOT FILLED ({not_filled.sum():,}) ===\n")

        # Check if fusion was attempted
        fusion_sources_for_not_filled = df_05.loc[not_filled, 'fusion_authors_source'].notna().sum()
        print(f"Have fusion_authors_source: {fusion_sources_for_not_filled:,}")

        # Sample some cases
        print(f"\nSample cases (first 10):")
        sample = df_05[not_filled].head(10)

        for idx in sample.index:
            print(f"\nID: {df_05.loc[idx, 'id']}")
            print(f"  Title: {df_05.loc[idx, 'title'][:60] if pd.notna(df_05.loc[idx, 'title']) else 'N/A'}...")
            print(f"  MARC21 authors: {df_01.loc[idx, 'authors_str']}")
            print(f"  DNB authors (ID): {df_04.loc[idx, 'dnb_authors']}")
            print(f"  DNB authors (TA): {df_04.loc[idx, 'dnb_authors_ta']}")
            print(f"  Final authors: {df_05.loc[idx, 'authors_str']}")
            print(f"  Fusion source: {df_05.loc[idx, 'fusion_authors_source']}")

            # Check if DNB match was rejected
            if 'fusion_dnb_match_rejected' in df_05.columns:
                print(f"  DNB match rejected: {df_05.loc[idx, 'fusion_dnb_match_rejected']}")

print("\n=== SUMMARY ===")
print(f"MARC21 missing authors: {had_no_authors_01:,}")
print(f"DNB could provide: {dnb_id_for_empty + dnb_ta_for_empty:,}")
print(f"Actually filled: {actually_filled:,}")
print(f"Not filled despite DNB data: {dnb_available_but_not_used:,}")
print(f"\nSuccess rate: {actually_filled / had_no_authors_01 * 100:.2f}%")
print(f"DNB utilization rate: {actually_filled / (dnb_id_for_empty + dnb_ta_for_empty) * 100:.2f}%" if (dnb_id_for_empty + dnb_ta_for_empty) > 0 else "N/A")
