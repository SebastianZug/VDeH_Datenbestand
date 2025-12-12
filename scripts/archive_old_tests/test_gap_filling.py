#!/usr/bin/env python3
"""Test gap filling logic on existing fused data."""

import pandas as pd

# Load existing fused data
df_enriched = pd.read_parquet('data/vdeh/processed/05_fused_data.parquet')

print("📝 === GAP FILLING TEST ===\n")
print(f"Loaded {len(df_enriched):,} records\n")

# Statistics BEFORE gap filling
before_gap_filling = {
    'isbn': df_enriched['isbn'].notna().sum(),
    'issn': df_enriched['issn'].notna().sum() if 'issn' in df_enriched.columns else 0,
    'authors': (df_enriched['authors_str'].notna() & (df_enriched['authors_str'] != '')).sum(),
    'year': df_enriched['year'].notna().sum(),
    'publisher': df_enriched['publisher'].notna().sum(),
}

print("📊 BEFORE Gap Filling:")
for field, count in before_gap_filling.items():
    print(f"   {field}: {count:,} ({count/len(df_enriched)*100:.1f}%)")

filled_count = {
    'isbn': 0,
    'issn': 0,
    'authors': 0,
    'year': 0,
    'publisher': 0
}

# 1. ISBN Gap Filling
if 'dnb_isbn_ta' in df_enriched.columns:
    no_isbn = df_enriched['isbn'].isna()
    has_dnb_isbn_ta = df_enriched['dnb_isbn_ta'].notna()

    fill_isbn_mask = no_isbn & has_dnb_isbn_ta
    filled_count['isbn'] = fill_isbn_mask.sum()

    if filled_count['isbn'] > 0:
        df_enriched.loc[fill_isbn_mask, 'isbn'] = df_enriched.loc[fill_isbn_mask, 'dnb_isbn_ta']
        if 'isbn_source' not in df_enriched.columns:
            df_enriched['isbn_source'] = None
        df_enriched.loc[fill_isbn_mask, 'isbn_source'] = 'dnb_title_author'

        print(f"\n✓ ISBN: {filled_count['isbn']:,} neu gefüllt aus dnb_isbn_ta")

# 2. ISSN Gap Filling
if 'issn' in df_enriched.columns and 'dnb_issn_ta' in df_enriched.columns:
    no_issn = df_enriched['issn'].isna()
    has_dnb_issn_ta = df_enriched['dnb_issn_ta'].notna()

    fill_issn_mask = no_issn & has_dnb_issn_ta
    filled_count['issn'] = fill_issn_mask.sum()

    if filled_count['issn'] > 0:
        df_enriched.loc[fill_issn_mask, 'issn'] = df_enriched.loc[fill_issn_mask, 'dnb_issn_ta']
        if 'issn_source' not in df_enriched.columns:
            df_enriched['issn_source'] = None
        df_enriched.loc[fill_issn_mask, 'issn_source'] = 'dnb_title_author'

        print(f"✓ ISSN: {filled_count['issn']:,} neu gefüllt aus dnb_issn_ta")

# Statistics AFTER gap filling
after_gap_filling = {
    'isbn': df_enriched['isbn'].notna().sum(),
    'issn': df_enriched['issn'].notna().sum() if 'issn' in df_enriched.columns else 0,
    'authors': (df_enriched['authors_str'].notna() & (df_enriched['authors_str'] != '')).sum(),
    'year': df_enriched['year'].notna().sum(),
    'publisher': df_enriched['publisher'].notna().sum(),
}

print("\n📊 AFTER Gap Filling:")
for field, count in after_gap_filling.items():
    before = before_gap_filling[field]
    delta = count - before
    print(f"   {field}: {count:,} ({count/len(df_enriched)*100:.1f}%) [+{delta:,}]")

print("\n📊 Gap Filling Summary:")
total_filled = sum(filled_count.values())
print(f"   Total fields filled: {total_filled:,}")
for field, count in filled_count.items():
    if count > 0:
        print(f"   {field}: +{count:,}")

# Save updated data
output_path = 'data/vdeh/processed/05_fused_data.parquet'
df_enriched.to_parquet(output_path, index=True)
print(f"\n💾 Updated data saved to: {output_path}")
print("\n✅ Gap filling test complete!")
