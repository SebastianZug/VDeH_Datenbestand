#!/usr/bin/env python3
"""Add pages field to DNB data storage in notebook 04."""

import json

# Read notebook
with open('notebooks/01_vdeh_preprocessing/04_vdeh_data_enrichment.ipynb', 'r') as f:
    nb = json.load(f)

print("=== ADDING PAGES FIELD TO NOTEBOOK 04 ===\n")

# Find and update DNB query cells
updates = []

for i, cell in enumerate(nb['cells']):
    source = ''.join(cell.get('source', []))

    # 1. Update ISBN/ISSN query cell - add pages to result_row
    if "'dnb_issn': dnb_result.get('issn') if dnb_result else None" in source and "'dnb_pages'" not in source:
        source = source.replace(
            "'dnb_issn': dnb_result.get('issn') if dnb_result else None",
            "'dnb_issn': dnb_result.get('issn') if dnb_result else None,\n            'dnb_pages': dnb_result.get('pages') if dnb_result else None"
        )
        cell['source'] = source.splitlines(keepends=True)
        updates.append(f"Cell {i}: Added dnb_pages to ISBN/ISSN query results")

    # 2. Update Title/Author query cell - add pages to result_row
    if "dnb_title_df = pd.DataFrame(columns=[" in source and "'dnb_pages'" not in source:
        source = source.replace(
            "'dnb_found', 'dnb_title', 'dnb_authors', 'dnb_year', 'dnb_publisher',\n        'dnb_isbn', 'dnb_issn'",
            "'dnb_found', 'dnb_title', 'dnb_authors', 'dnb_year', 'dnb_publisher',\n        'dnb_isbn', 'dnb_issn', 'dnb_pages'"
        )

        # Also update the result_row dictionary
        source = source.replace(
            "'dnb_issn': dnb_result.get('issn') if dnb_result else None\n        }",
            "'dnb_issn': dnb_result.get('issn') if dnb_result else None,\n            'dnb_pages': dnb_result.get('pages') if dnb_result else None\n        }"
        )

        cell['source'] = source.splitlines(keepends=True)
        updates.append(f"Cell {i}: Added dnb_pages to Title/Author query")

    # 3. Update Title/Year query cell - add pages to result_row
    if "dnb_ty_df = pd.DataFrame(columns=[" in source and "'dnb_pages'" not in source:
        source = source.replace(
            "'dnb_found', 'dnb_title', 'dnb_authors', 'dnb_year', 'dnb_publisher',\n        'dnb_isbn', 'dnb_issn'",
            "'dnb_found', 'dnb_title', 'dnb_authors', 'dnb_year', 'dnb_publisher',\n        'dnb_isbn', 'dnb_issn', 'dnb_pages'"
        )

        # Also update the result_row dictionary
        source = source.replace(
            "'dnb_issn': dnb_result.get('issn') if dnb_result else None\n        }",
            "'dnb_issn': dnb_result.get('issn') if dnb_result else None,\n            'dnb_pages': dnb_result.get('pages') if dnb_result else None\n        }"
        )

        cell['source'] = source.splitlines(keepends=True)
        updates.append(f"Cell {i}: Added dnb_pages to Title/Year query")

    # 4. Update merge cell - add pages columns
    if "rename_map = {" in source and "'dnb_publisher': 'dnb_publisher_ta'" in source and "'dnb_pages'" not in source:
        source = source.replace(
            "rename_map['dnb_issn'] = 'dnb_issn_ta'",
            "rename_map['dnb_issn'] = 'dnb_issn_ta'\n    if 'dnb_pages' in cols_to_merge_ta:\n        rename_map['dnb_pages'] = 'dnb_pages_ta'"
        )
        cell['source'] = source.splitlines(keepends=True)
        updates.append(f"Cell {i}: Added dnb_pages_ta to TA merge")

    # 5. Update TY merge logic
    if "'dnb_publisher_ty'" in source and "'dnb_pages': 'dnb_pages_ty'" not in source:
        source = source.replace(
            "rename_map['dnb_issn'] = 'dnb_issn_ty'",
            "rename_map['dnb_issn'] = 'dnb_issn_ty'\n    if 'dnb_pages' in cols_to_merge_ty:\n        rename_map['dnb_pages'] = 'dnb_pages_ty'"
        )
        cell['source'] = source.splitlines(keepends=True)
        updates.append(f"Cell {i}: Added dnb_pages_ty to TY merge")

# Write updated notebook
with open('notebooks/01_vdeh_preprocessing/04_vdeh_data_enrichment.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("Updates made:")
for update in updates:
    print(f"  ✓ {update}")

if not updates:
    print("  ⚠️ No updates needed - pages field might already be present")

print("\n✅ Notebook 04 updated with pages field!")
