#!/usr/bin/env python3
"""Understand why 187 DNB authors were rejected."""

import pandas as pd

# Load stage 04 and 05
df_04 = pd.read_parquet('data/vdeh/processed/04_dnb_enriched_data.parquet')
df_05 = pd.read_parquet('data/vdeh/processed/05_fused_data.parquet')

# Find rejected authors
vdeh_no_authors = (df_04['authors_str'].isna() | (df_04['authors_str'] == ''))
dnb_has_authors = (df_04['dnb_authors'].notna() & (df_04['dnb_authors'] != ''))
final_no_authors = (df_05['authors_str'].isna() | (df_05['authors_str'] == ''))

rejected = vdeh_no_authors & dnb_has_authors & final_no_authors

print(f'=== REJECTED DNB AUTHORS: {rejected.sum():,} cases ===\n')

# Check fusion metadata for rejected cases
print('Fusion rejection reasons:\n')

if 'fusion_dnb_match_rejected' in df_05.columns:
    rejected_df = df_05[rejected]

    # Count rejections
    if rejected_df['fusion_dnb_match_rejected'].notna().any():
        print(f'  Marked as rejected: {rejected_df["fusion_dnb_match_rejected"].sum():,}')

    # Check rejection reasons
    if 'fusion_rejection_reason' in df_05.columns:
        reasons = rejected_df['fusion_rejection_reason'].value_counts()
        print(f'\n  Rejection reasons:')
        for reason, count in reasons.head(10).items():
            if pd.notna(reason):
                print(f'    {count:,}: {reason[:100]}...' if len(str(reason)) > 100 else f'    {count:,}: {reason}')

# Sample rejected cases
print('\n=== SAMPLE REJECTED CASES (First 10) ===\n')

sample_rejected = df_05[rejected].head(10)

for idx in sample_rejected.index:
    row_04 = df_04.loc[idx]
    row_05 = df_05.loc[idx]

    print(f"ID: {row_05['id']}")
    print(f"  Title: {row_05['title'][:70] if pd.notna(row_05['title']) else 'N/A'}...")
    print(f"  DNB authors (available): {row_04['dnb_authors']}")

    if 'fusion_dnb_match_rejected' in row_05:
        print(f"  Match rejected: {row_05['fusion_dnb_match_rejected']}")

    if 'fusion_rejection_reason' in row_05 and pd.notna(row_05['fusion_rejection_reason']):
        print(f"  Reason: {row_05['fusion_rejection_reason']}")

    if 'fusion_ai_reasoning' in row_05 and pd.notna(row_05['fusion_ai_reasoning']):
        print(f"  AI reasoning: {row_05['fusion_ai_reasoning'][:200]}...")

    print()

# Check if these records were even processed by fusion
print('\n=== FUSION PROCESSING CHECK ===\n')

rejected_df = df_05[rejected]

# Check if fusion columns exist
fusion_source_cols = [col for col in df_05.columns if 'fusion_' in col and '_source' in col]

if fusion_source_cols:
    print(f'Checking {len(fusion_source_cols)} fusion source columns:')

    for col in fusion_source_cols:
        has_value = rejected_df[col].notna().sum()
        print(f'  {col}: {has_value:,} / {len(rejected_df):,} have values')

# Most importantly: check if these records had DNB matches AT ALL
print(f'\n=== DNB MATCH STATUS ===\n')

print(f'Records with rejected authors that had DNB ID match: {(rejected & df_04["dnb_query_method"].notna()).sum():,}')
print(f'Records with rejected authors that had DNB TA match: {(rejected & df_04["dnb_title_ta"].notna()).sum():,}')

# Check if fusion was attempted
fusion_attempted = rejected_df['fusion_conflicts'].notna() | rejected_df['fusion_confirmations'].notna()
print(f'\nFusion was attempted for: {fusion_attempted.sum():,} / {len(rejected_df):,} rejected cases')
print(f'Fusion was NOT attempted for: {(~fusion_attempted).sum():,} / {len(rejected_df):,} rejected cases')

# For cases where fusion was NOT attempted, why?
no_fusion_df = rejected_df[~fusion_attempted]

if len(no_fusion_df) > 0:
    print(f'\n=== CASES WHERE FUSION WAS NOT ATTEMPTED ({len(no_fusion_df):,}) ===\n')

    # Check if they had DNB matches
    print(f'  Had DNB ID match: {no_fusion_df["dnb_query_method"].notna().sum():,}')
    print(f'  Had DNB TA match: {no_fusion_df["dnb_title_ta"].notna().sum():,}')

    # Sample
    print(f'\n  Sample cases:')
    for idx in no_fusion_df.head(3).index:
        row_04 = df_04.loc[idx]
        row_05 = df_05.loc[idx]

        print(f'\n  ID: {row_05["id"]}')
        print(f'    Title (VDEH): {row_05["title"][:60] if pd.notna(row_05["title"]) else "N/A"}...')
        print(f'    Authors (VDEH): {row_04["authors_str"]}')
        print(f'    Authors (DNB ID): {row_04.get("dnb_authors", "N/A")}')
        print(f'    Authors (DNB TA): {row_04.get("dnb_authors_ta", "N/A")}')
        print(f'    DNB method: {row_04.get("dnb_query_method", "N/A")}')
        print(f'    DNB title: {row_04.get("dnb_title", "N/A")}')
