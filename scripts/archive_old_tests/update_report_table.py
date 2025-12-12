#!/usr/bin/env python3
"""Update report generator to include filled, corrected, and confirmed columns."""

import json

# Read notebook
with open('notebooks/02_vdeh_analysis/01_project_report_generator.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find calculate-stats cell and add loading of corrections/confirmations stats
for cell in nb['cells']:
    if cell.get('id') == 'calculate-stats':
        source = ''.join(cell['source'])

        # Add loading of corrections/confirmations stats at the end
        if 'corrections_confirmations_stats.json' not in source:
            insert_pos = source.rfind('print("Statistiken berechnet!")')
            if insert_pos > 0:
                new_code = """

# CORRECTIONS AND CONFIRMATIONS (NEU)
corrections_path = processed_dir / 'corrections_confirmations_stats.json'
if corrections_path.exists():
    with open(corrections_path, 'r') as f:
        stats['corrections_confirmations'] = json.load(f)
    print("  Corrections/Confirmations geladen")

"""
                source = source[:insert_pos] + new_code + source[insert_pos:]
                cell['source'] = source.splitlines(keepends=True)
                print("✓ Updated calculate-stats cell: Added corrections/confirmations loading")

# Find generate-report cell and update the second table
for cell in nb['cells']:
    if cell.get('id') == 'generate-report':
        source = ''.join(cell['source'])

        # Find and replace the solution table
        old_table = """| Feld | Neu gefüllt | Schließungsrate |
|------|------------|---------------------|
| **ISBN** | **+{gaps_filled.get('isbn', 0):,}** | **{isbn_gap_closure:.1f}%** |
| **ISSN** | **+{gaps_filled.get('issn', 0):,}** | {gaps_filled.get('issn', 0)/original_gaps.get('issn_missing', 1)*100 if original_gaps.get('issn_missing', 0) > 0 else 0:.1f}% |
| **Sprache** | **+{language_stats.get('gap_filled', 0):,}** | **{language_gap_closure:.1f}%** |
| Autoren | +{gaps_filled.get('authors', 0):,} | {gaps_filled.get('authors', 0)/original_gaps.get('authors_missing', 1)*100 if original_gaps.get('authors_missing', 0) > 0 else 0:.1f}% |
| Jahr | +{gaps_filled.get('year', 0):,} | {gaps_filled.get('year', 0)/original_gaps.get('year_missing', 1)*100 if original_gaps.get('year_missing', 0) > 0 else 0:.1f}% |
| Publisher | +{gaps_filled.get('publisher', 0):,} | {gaps_filled.get('publisher', 0)/original_gaps.get('publisher_missing', 1)*100 if original_gaps.get('publisher_missing', 0) > 0 else 0:.1f}% |"""

        new_table = """| Feld | Neu gefüllt | Korrigiert | Bestätigt | Gesamt bearbeitet |
|------|------------|------------|-----------|-------------------|
| **ISBN** | **+{stats.get('corrections_confirmations', {}).get('isbn', {}).get('filled', gaps_filled.get('isbn', 0)):,}** | {stats.get('corrections_confirmations', {}).get('isbn', {}).get('corrected', 0):,} | {stats.get('corrections_confirmations', {}).get('isbn', {}).get('confirmed', 0):,} | **{stats.get('corrections_confirmations', {}).get('isbn', {}).get('filled', 0) + stats.get('corrections_confirmations', {}).get('isbn', {}).get('corrected', 0) + stats.get('corrections_confirmations', {}).get('isbn', {}).get('confirmed', 0):,}** |
| **ISSN** | **+{stats.get('corrections_confirmations', {}).get('issn', {}).get('filled', gaps_filled.get('issn', 0)):,}** | {stats.get('corrections_confirmations', {}).get('issn', {}).get('corrected', 0):,} | {stats.get('corrections_confirmations', {}).get('issn', {}).get('confirmed', 0):,} | **{stats.get('corrections_confirmations', {}).get('issn', {}).get('filled', 0) + stats.get('corrections_confirmations', {}).get('issn', {}).get('corrected', 0) + stats.get('corrections_confirmations', {}).get('issn', {}).get('confirmed', 0):,}** |
| **Sprache** | **+{stats.get('corrections_confirmations', {}).get('language', {}).get('filled', language_stats.get('gap_filled', 0)):,}** | {stats.get('corrections_confirmations', {}).get('language', {}).get('corrected', 0):,} | {stats.get('corrections_confirmations', {}).get('language', {}).get('confirmed', 0):,} | **{stats.get('corrections_confirmations', {}).get('language', {}).get('filled', 0) + stats.get('corrections_confirmations', {}).get('language', {}).get('corrected', 0) + stats.get('corrections_confirmations', {}).get('language', {}).get('confirmed', 0):,}** |
| Autoren | +{stats.get('corrections_confirmations', {}).get('authors', {}).get('filled', gaps_filled.get('authors', 0)):,} | {stats.get('corrections_confirmations', {}).get('authors', {}).get('corrected', 0):,} | {stats.get('corrections_confirmations', {}).get('authors', {}).get('confirmed', 0):,} | {stats.get('corrections_confirmations', {}).get('authors', {}).get('filled', 0) + stats.get('corrections_confirmations', {}).get('authors', {}).get('corrected', 0) + stats.get('corrections_confirmations', {}).get('authors', {}).get('confirmed', 0):,} |
| Jahr | +{stats.get('corrections_confirmations', {}).get('year', {}).get('filled', gaps_filled.get('year', 0)):,} | {stats.get('corrections_confirmations', {}).get('year', {}).get('corrected', 0):,} | {stats.get('corrections_confirmations', {}).get('year', {}).get('confirmed', 0):,} | {stats.get('corrections_confirmations', {}).get('year', {}).get('filled', 0) + stats.get('corrections_confirmations', {}).get('year', {}).get('corrected', 0) + stats.get('corrections_confirmations', {}).get('year', {}).get('confirmed', 0):,} |
| Publisher | +{stats.get('corrections_confirmations', {}).get('publisher', {}).get('filled', gaps_filled.get('publisher', 0)):,} | {stats.get('corrections_confirmations', {}).get('publisher', {}).get('corrected', 0):,} | {stats.get('corrections_confirmations', {}).get('publisher', {}).get('confirmed', 0):,} | {stats.get('corrections_confirmations', {}).get('publisher', {}).get('filled', 0) + stats.get('corrections_confirmations', {}).get('publisher', {}).get('corrected', 0) + stats.get('corrections_confirmations', {}).get('publisher', {}).get('confirmed', 0):,} |"""

        if old_table in source:
            source = source.replace(old_table, new_table)
            cell['source'] = source.splitlines(keepends=True)
            print("✓ Updated generate-report cell: Expanded table with corrected/confirmed columns")
        else:
            print("⚠ Could not find table to replace in generate-report cell")

# Write updated notebook
with open('notebooks/02_vdeh_analysis/01_project_report_generator.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("\n✅ Notebook updated!")
print("   - Added corrections/confirmations loading")
print("   - Expanded solution table with 'Korrigiert', 'Bestätigt', and 'Gesamt bearbeitet' columns")
