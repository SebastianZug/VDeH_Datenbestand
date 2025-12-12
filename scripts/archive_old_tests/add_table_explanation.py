#!/usr/bin/env python3
"""Add explanation of table columns to the report."""

import json

# Read notebook
with open('notebooks/02_vdeh_analysis/01_project_report_generator.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Find generate-report cell and add explanation after the table
for cell in nb['cells']:
    if cell.get('id') == 'generate-report':
        source = ''.join(cell['source'])

        # Find the table and add explanation after it
        table_marker = """| Publisher | +{stats.get('corrections_confirmations', {}).get('publisher', {}).get('filled', gaps_filled.get('publisher', 0)):,} | {stats.get('corrections_confirmations', {}).get('publisher', {}).get('corrected', 0):,} | {stats.get('corrections_confirmations', {}).get('publisher', {}).get('confirmed', 0):,} | {stats.get('corrections_confirmations', {}).get('publisher', {}).get('filled', 0) + stats.get('corrections_confirmations', {}).get('publisher', {}).get('corrected', 0) + stats.get('corrections_confirmations', {}).get('publisher', {}).get('confirmed', 0):,} |

### Hauptmehrwert"""

        explanation = """| Publisher | +{stats.get('corrections_confirmations', {}).get('publisher', {}).get('filled', gaps_filled.get('publisher', 0)):,} | {stats.get('corrections_confirmations', {}).get('publisher', {}).get('corrected', 0):,} | {stats.get('corrections_confirmations', {}).get('publisher', {}).get('confirmed', 0):,} | {stats.get('corrections_confirmations', {}).get('publisher', {}).get('filled', 0) + stats.get('corrections_confirmations', {}).get('publisher', {}).get('corrected', 0) + stats.get('corrections_confirmations', {}).get('publisher', {}).get('confirmed', 0):,} |

**Erklärung der Spalten:**
- **Neu gefüllt**: MARC21 hatte keinen Wert → Pipeline füllte ihn
- **Korrigiert**: MARC21 hatte einen Wert → Pipeline ersetzte ihn mit DNB-Daten (weil DNB besser war)
- **Bestätigt**: MARC21 hatte einen Wert → Pipeline bestätigte ihn (gleich oder DNB-Match abgelehnt)
- **Gesamt bearbeitet**: Summe aller Pipeline-Aktivitäten für dieses Feld

### Hauptmehrwert"""

        if table_marker in source:
            source = source.replace(table_marker, explanation)
            cell['source'] = source.splitlines(keepends=True)
            print("✓ Added table explanation after the solution table")
        else:
            print("⚠ Could not find table marker to insert explanation")

# Write updated notebook
with open('notebooks/02_vdeh_analysis/01_project_report_generator.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("\n✅ Notebook updated with table explanation!")
