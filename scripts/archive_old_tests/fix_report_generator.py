#!/usr/bin/env python3
"""Fix the report generator to use Stage 01 as baseline and add Titel to first table."""

import json

# Read notebook
with open('notebooks/02_vdeh_analysis/01_project_report_generator.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find and update load-data cell
for cell in nb['cells']:
    if cell.get('id') == 'load-data':
        source = ''.join(cell['source'])
        # Replace Stage 03 with Stage 01
        source = source.replace(
            "# Original data\noriginal_path = processed_dir / '03_language_detected_data.parquet'",
            "# Original data (MARC21 raw - Stage 01 als Baseline!)\noriginal_path = processed_dir / '01_loaded_data.parquet'"
        )
        cell['source'] = source.splitlines(keepends=True)
        print("✓ Updated load-data cell: Using Stage 01 as baseline")

# Find and update generate-report cell to add "Titel" to first table
for cell in nb['cells']:
    if cell.get('id') == 'generate-report':
        source = ''.join(cell['source'])

        # Add title_missing to original_gaps calculation (in Problem table)
        old_table = """| Feld | Fehlend in MARC21 | Prozent |
|------|-------------------|---------|
| **ISBN** | **{original_gaps.get('isbn_missing', 0):,}** | **{original_gaps.get('isbn_missing', 0)/total*100:.1f}%** |
| **ISSN** | {original_gaps.get('issn_missing', 0):,} | {original_gaps.get('issn_missing', 0)/total*100:.1f}% |
| **Sprache** | {original_gaps.get('language_missing', 0):,} | {original_gaps.get('language_missing', 0)/total*100:.1f}% |
| Autoren | {original_gaps.get('authors_missing', 0):,} | {original_gaps.get('authors_missing', 0)/total*100:.1f}% |
| Jahr | {original_gaps.get('year_missing', 0):,} | {original_gaps.get('year_missing', 0)/total*100:.1f}% |
| Publisher | {original_gaps.get('publisher_missing', 0):,} | {original_gaps.get('publisher_missing', 0)/total*100:.1f}% |"""

        new_table = """| Feld | Fehlend in MARC21 | Prozent |
|------|-------------------|---------|
| Titel | {original_gaps.get('title_missing', 0):,} | {original_gaps.get('title_missing', 0)/total*100:.1f}% |
| **ISBN** | **{original_gaps.get('isbn_missing', 0):,}** | **{original_gaps.get('isbn_missing', 0)/total*100:.1f}%** |
| **ISSN** | {original_gaps.get('issn_missing', 0):,} | {original_gaps.get('issn_missing', 0)/total*100:.1f}% |
| **Sprache** | {original_gaps.get('language_missing', 0):,} | {original_gaps.get('language_missing', 0)/total*100:.1f}% |
| Autoren | {original_gaps.get('authors_missing', 0):,} | {original_gaps.get('authors_missing', 0)/total*100:.1f}% |
| Jahr | {original_gaps.get('year_missing', 0):,} | {original_gaps.get('year_missing', 0)/total*100:.1f}% |
| Publisher | {original_gaps.get('publisher_missing', 0):,} | {original_gaps.get('publisher_missing', 0)/total*100:.1f}% |"""

        source = source.replace(old_table, new_table)

        cell['source'] = source.splitlines(keepends=True)
        print("✓ Updated generate-report cell: Added 'Titel' to first table")

# Find and update calculate-stats cell to add title_missing calculation
for cell in nb['cells']:
    if cell.get('id') == 'calculate-stats':
        source = ''.join(cell['source'])

        # Add title_missing calculation
        old_gaps = """        stats['original_gaps'] = {
            'isbn_missing': (df_original['isbn'].isna()).sum(),
            'issn_missing': (df_original['issn'].isna()).sum() if 'issn' in df_original.columns else 0,
            'authors_missing': (df_original['authors_str'].isna() | (df_original['authors_str'] == '')).sum(),
            'year_missing': df_original['year'].isna().sum(),
            'publisher_missing': df_original['publisher'].isna().sum(),
            'language_missing': 0  # Wird gleich berechnet
        }"""

        new_gaps = """        stats['original_gaps'] = {
            'title_missing': (df_original['title'].isna()).sum(),
            'isbn_missing': (df_original['isbn'].isna()).sum(),
            'issn_missing': (df_original['issn'].isna()).sum() if 'issn' in df_original.columns else 0,
            'authors_missing': (df_original['authors_str'].isna() | (df_original['authors_str'] == '')).sum(),
            'year_missing': df_original['year'].isna().sum(),
            'publisher_missing': df_original['publisher'].isna().sum(),
            'language_missing': 0  # Wird gleich berechnet
        }"""

        source = source.replace(old_gaps, new_gaps)

        cell['source'] = source.splitlines(keepends=True)
        print("✓ Updated calculate-stats cell: Added title_missing calculation")

# Write updated notebook
with open('notebooks/02_vdeh_analysis/01_project_report_generator.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("\n✅ Notebook updated successfully!")
print("   - Stage 01 (MARC21 raw) is now used as baseline")
print("   - 'Titel' added to first table")
