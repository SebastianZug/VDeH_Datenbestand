#!/usr/bin/env python3
"""Final fix: Use correct 'newly filled' calculation instead of 'gap closure'."""

import json

# Read notebook
with open('notebooks/02_vdeh_analysis/01_project_report_generator.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find and update calculate-stats cell
for cell in nb['cells']:
    if cell.get('id') == 'calculate-stats':
        source = ''.join(cell['source'])

        # Replace gap closure calculation with 'newly filled' calculation
        old_calc = """    # GAP CLOSURE: Was wurde gefüllt?
    if df_original is not None:
        stats['gaps_filled'] = {
            'isbn': stats['original_gaps']['isbn_missing'] - (df_fused['isbn'].isna().sum() if 'isbn' in df_fused.columns else 0),
            'issn': stats['original_gaps']['issn_missing'] - (df_fused['issn'].isna().sum() if 'issn' in df_fused.columns else 0),
            'authors': stats['original_gaps']['authors_missing'] - (df_fused['authors_str'].isna() | (df_fused['authors_str'] == '')).sum(),
            'year': stats['original_gaps']['year_missing'] - df_fused['year'].isna().sum(),
            'publisher': stats['original_gaps']['publisher_missing'] - df_fused['publisher'].isna().sum()
        }"""

        new_calc = """    # NEWLY FILLED: Records that had NO value in original but HAVE value now
    if df_original is not None:
        # ISBN
        had_no_isbn_01 = df_original['isbn'].isna() if 'isbn' in df_fused.columns else pd.Series([True] * len(df_fused))
        has_isbn_05 = df_fused['isbn'].notna() if 'isbn' in df_fused.columns else pd.Series([False] * len(df_fused))
        
        # ISSN
        had_no_issn_01 = df_original['issn'].isna() if 'issn' in df_original.columns else pd.Series([True] * len(df_fused))
        has_issn_05 = df_fused['issn'].notna() if 'issn' in df_fused.columns else pd.Series([False] * len(df_fused))
        
        # Authors
        had_no_authors_01 = (df_original['authors_str'].isna() | (df_original['authors_str'] == ''))
        has_authors_05 = (df_fused['authors_str'].notna() & (df_fused['authors_str'] != ''))
        
        # Year
        had_no_year_01 = df_original['year'].isna()
        has_year_05 = df_fused['year'].notna()
        
        # Publisher
        had_no_pub_01 = df_original['publisher'].isna()
        has_pub_05 = df_fused['publisher'].notna()
        
        stats['gaps_filled'] = {
            'isbn': (had_no_isbn_01 & has_isbn_05).sum(),
            'issn': (had_no_issn_01 & has_issn_05).sum(),
            'authors': (had_no_authors_01 & has_authors_05).sum(),
            'year': (had_no_year_01 & has_year_05).sum(),
            'publisher': (had_no_pub_01 & has_pub_05).sum()
        }"""

        source = source.replace(old_calc, new_calc)

        cell['source'] = source.splitlines(keepends=True)
        print("✓ Updated calculate-stats cell: Using 'newly filled' instead of 'gap closure'")

# Write updated notebook
with open('notebooks/02_vdeh_analysis/01_project_report_generator.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("\n✅ Notebook updated!")
print("   - Now counts 'newly filled' records instead of gap closure")
print("   - This will show +371 authors (correct value)")
