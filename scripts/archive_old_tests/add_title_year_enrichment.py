#!/usr/bin/env python3
"""Add Title/Year enrichment cell to notebook 04."""

import json
import uuid

# Read notebook
with open('notebooks/01_vdeh_preprocessing/04_vdeh_data_enrichment.ipynb', 'r') as f:
    nb = json.load(f)

# Find title/author cell index
ta_index = None
for i, cell in enumerate(nb['cells']):
    if cell.get('id') == '97aaf6e1':  # Title/Author cell
        ta_index = i
        break

if ta_index is None:
    print("❌ Title/Author cell not found!")
    exit(1)

# Create new Title/Year enrichment cell
title_year_cell = {
    "cell_type": "code",
    "id": str(uuid.uuid4())[:8],
    "metadata": {},
    "source": [
        "# 🔍 DNB TITEL/JAHR-SUCHE (Neue Methode für Records ohne ISBN/ISSN!)\n",
        "print(\"🔍 === DNB TITEL/JAHR-SUCHE ===\\n\")\n",
        "\n",
        "# Import new function\n",
        "from dnb_api import query_dnb_by_title_year\n",
        "\n",
        "# Konfiguration\n",
        "DNB_TITLE_YEAR_DATA_FILE = processed_dir / 'dnb_title_year_data.parquet'\n",
        "RESET_TY_SEARCH = False  # Set to True to reset and re-run\n",
        "\n",
        "print(f\"⚙️  Konfiguration:\")\n",
        "print(f\"   Rate Limit: {RATE_LIMIT_DELAY}s pro Anfrage\")\n",
        "print(f\"   Save Interval: Alle {SAVE_INTERVAL} Queries\")\n",
        "print(f\"   Output: {DNB_TITLE_YEAR_DATA_FILE.name}\")\n",
        "print(f\"   🆕 Neue Suchmethode: Titel + Jahr (für Records ohne ISBN/ISSN/Autoren)\")\n",
        "\n",
        "# Reset wenn gewünscht\n",
        "if RESET_TY_SEARCH and DNB_TITLE_YEAR_DATA_FILE.exists():\n",
        "    backup_file = processed_dir / f'dnb_title_year_data_OLD_{pd.Timestamp.now().strftime(\"%Y%m%d_%H%M%S\")}.parquet'\n",
        "    DNB_TITLE_YEAR_DATA_FILE.rename(backup_file)\n",
        "    print(f\"\\n🔄 TY-Suche wird zurückgesetzt - alte Datei gesichert: {backup_file.name}\")\n",
        "\n",
        "# Lade vorhandene Titel/Jahr-Suchdaten (falls vorhanden)\n",
        "if DNB_TITLE_YEAR_DATA_FILE.exists():\n",
        "    print(f\"\\n📂 Lade vorhandene Titel/Jahr-Suchdaten...\")\n",
        "    dnb_ty_df = pd.read_parquet(DNB_TITLE_YEAR_DATA_FILE)\n",
        "    print(f\"   Bereits abgefragt: {len(dnb_ty_df):,}\")\n",
        "    print(f\"   Davon erfolgreich: {(dnb_ty_df['dnb_found'] == True).sum():,}\")\n",
        "else:\n",
        "    print(f\"\\n📂 Keine vorhandenen Titel/Jahr-Suchdaten gefunden - starte neue Abfrage\")\n",
        "    dnb_ty_df = pd.DataFrame(columns=[\n",
        "        'vdeh_id', 'query_type', 'title', 'year',\n",
        "        'dnb_found', 'dnb_title', 'dnb_authors', 'dnb_year', 'dnb_publisher',\n",
        "        'dnb_isbn', 'dnb_issn'\n",
        "    ])\n",
        "\n",
        "# Identifiziere Kandidaten für Titel/Jahr-Suche\n",
        "# Nur Records OHNE ISBN/ISSN UND OHNE Autoren, aber MIT Titel und Jahr\n",
        "title_year_candidates = df_vdeh[\n",
        "    (df_vdeh['isbn'].isna()) &\n",
        "    (df_vdeh['issn'].isna()) &\n",
        "    ((df_vdeh['authors_str'].isna()) | (df_vdeh['authors_str'] == '')) &\n",
        "    (df_vdeh['title'].notna()) &\n",
        "    (df_vdeh['year'].notna())\n",
        "].copy()\n",
        "\n",
        "print(f\"\\n📋 Titel/Jahr-Kandidaten: {len(title_year_candidates):,}\")\n",
        "print(f\"   Ohne ISBN/ISSN: {(title_year_candidates['isbn'].isna() & title_year_candidates['issn'].isna()).sum():,}\")\n",
        "print(f\"   Ohne Autoren: {((title_year_candidates['authors_str'].isna()) | (title_year_candidates['authors_str'] == '')).sum():,}\")\n",
        "print(f\"   Mit Titel: {title_year_candidates['title'].notna().sum():,}\")\n",
        "print(f\"   Mit Jahr: {title_year_candidates['year'].notna().sum():,}\")\n",
        "\n",
        "# Erstelle Query-Liste\n",
        "ty_queries = title_year_candidates[['id', 'title', 'year']].copy()\n",
        "ty_queries.columns = ['vdeh_id', 'title', 'year']\n",
        "ty_queries['query_type'] = 'TITLE_YEAR'\n",
        "\n",
        "print(f\"   Gesamt Titel/Jahr-Queries: {len(ty_queries):,}\")\n",
        "\n",
        "# Filtere bereits abgefragte Titel/Jahr-Kombinationen\n",
        "if len(dnb_ty_df) > 0:\n",
        "    already_queried = set(dnb_ty_df['vdeh_id'])\n",
        "    new_ty_queries = ty_queries[~ty_queries['vdeh_id'].isin(already_queried)].copy()\n",
        "    \n",
        "    print(f\"\\n🔍 Abgleich mit vorhandenen Daten:\")\n",
        "    print(f\"   Bereits vorhanden: {len(ty_queries) - len(new_ty_queries):,}\")\n",
        "    print(f\"   Neu abzufragen: {len(new_ty_queries):,}\")\n",
        "else:\n",
        "    new_ty_queries = ty_queries\n",
        "    print(f\"\\n🔍 Alle {len(new_ty_queries):,} Titel/Jahr-Queries sind neu\")\n",
        "\n",
        "# Nur abfragen wenn neue Queries vorhanden\n",
        "if len(new_ty_queries) > 0:\n",
        "    print(f\"\\n🔄 Starte DNB Titel/Jahr-Abfrage für {len(new_ty_queries):,} neue Queries...\")\n",
        "    print(f\"   📚 4-stufige Suchstrategie:\\n\")\n",
        "    print(f\"      1. Titel (Phrase) + exaktes Jahr\")\n",
        "    print(f\"      2. Titel (Wörter) + exaktes Jahr\")\n",
        "    print(f\"      3. Titel (Phrase) + Jahr ±1\")\n",
        "    print(f\"      4. Titel (Wörter) + Jahr ±1\\n\")\n",
        "    \n",
        "    from tqdm.auto import tqdm\n",
        "    \n",
        "    results = []\n",
        "    stats = {'found': 0, 'not_found': 0}\n",
        "    query_count = 0\n",
        "    \n",
        "    for _, row in tqdm(new_ty_queries.iterrows(), total=len(new_ty_queries), desc=\"🔍 DNB Titel/Jahr\", unit=\"queries\"):\n",
        "        # API-Abfrage\n",
        "        dnb_result = query_dnb_by_title_year(row['title'], int(row['year']))\n",
        "        \n",
        "        # Ergebnis speichern\n",
        "        result_row = {\n",
        "            'vdeh_id': row['vdeh_id'],\n",
        "            'query_type': row['query_type'],\n",
        "            'title': row['title'],\n",
        "            'year': row['year'],\n",
        "            'dnb_found': dnb_result is not None,\n",
        "            'dnb_title': dnb_result.get('title') if dnb_result else None,\n",
        "            'dnb_authors': ', '.join(dnb_result.get('authors', [])) if dnb_result else None,\n",
        "            'dnb_year': dnb_result.get('year') if dnb_result else None,\n",
        "            'dnb_publisher': dnb_result.get('publisher') if dnb_result else None,\n",
        "            'dnb_isbn': dnb_result.get('isbn') if dnb_result else None,\n",
        "            'dnb_issn': dnb_result.get('issn') if dnb_result else None\n",
        "        }\n",
        "        \n",
        "        results.append(result_row)\n",
        "        \n",
        "        if dnb_result:\n",
        "            stats['found'] += 1\n",
        "        else:\n",
        "            stats['not_found'] += 1\n",
        "        \n",
        "        query_count += 1\n",
        "        \n",
        "        # Regelmäßiges Speichern\n",
        "        if query_count % SAVE_INTERVAL == 0:\n",
        "            new_results_df = pd.DataFrame(results)\n",
        "            dnb_ty_df = pd.concat([dnb_ty_df, new_results_df], ignore_index=True)\n",
        "            dnb_ty_df.to_parquet(DNB_TITLE_YEAR_DATA_FILE, index=False)\n",
        "            results = []\n",
        "            \n",
        "            current_rate = stats['found'] / query_count * 100\n",
        "            print(f\"💾 Zwischenstand: {query_count}/{len(new_ty_queries)} | Erfolgsrate: {current_rate:.1f}%\")\n",
        "        \n",
        "        # Rate Limiting\n",
        "        time.sleep(RATE_LIMIT_DELAY)\n",
        "    \n",
        "    # Finale Speicherung\n",
        "    if len(results) > 0:\n",
        "        new_results_df = pd.DataFrame(results)\n",
        "        dnb_ty_df = pd.concat([dnb_ty_df, new_results_df], ignore_index=True)\n",
        "        dnb_ty_df.to_parquet(DNB_TITLE_YEAR_DATA_FILE, index=False)\n",
        "    \n",
        "    print(f\"\\n💾 DNB Titel/Jahr-Daten gespeichert: {DNB_TITLE_YEAR_DATA_FILE.name}\")\n",
        "    \n",
        "    # Zusammenfassung\n",
        "    print(f\"\\n📊 === NEUE TITEL/JAHR-ABFRAGEN ===\" )\n",
        "    print(f\"   Neue Queries: {len(new_ty_queries):,}\")\n",
        "    print(f\"   ✅ Gefunden: {stats['found']:,} ({stats['found']/len(new_ty_queries)*100:.1f}%)\")\n",
        "    print(f\"   ❌ Nicht gefunden: {stats['not_found']:,} ({stats['not_found']/len(new_ty_queries)*100:.1f}%)\")\n",
        "    print(f\"   💾 Zwischenspeicherungen: {len(new_ty_queries)//SAVE_INTERVAL}\")\n",
        "\n",
        "else:\n",
        "    print(f\"\\n✅ Alle Titel/Jahr-Kombinationen bereits abgefragt - keine neuen Abfragen nötig\")\n",
        "\n",
        "# Gesamtstatistik\n",
        "print(f\"\\n📊 === GESAMT TITEL/JAHR-DATEN ===\" )\n",
        "print(f\"   Total Records: {len(dnb_ty_df):,}\")\n",
        "print(f\"   Erfolgreich: {(dnb_ty_df['dnb_found'] == True).sum():,}\")\n",
        "print(f\"   Nicht gefunden: {(dnb_ty_df['dnb_found'] == False).sum():,}\")\n",
        "if len(dnb_ty_df) > 0:\n",
        "    print(f\"   📈 Erfolgsrate: {(dnb_ty_df['dnb_found'] == True).sum()/len(dnb_ty_df)*100:.1f}%\")\n",
        "\n",
        "# ISBN/ISSN-Gewinn via TY-Suche\n",
        "if 'dnb_isbn' in dnb_ty_df.columns and len(dnb_ty_df) > 0:\n",
        "    isbn_from_ty = (dnb_ty_df['dnb_found'] == True) & dnb_ty_df['dnb_isbn'].notna()\n",
        "    issn_from_ty = (dnb_ty_df['dnb_found'] == True) & dnb_ty_df['dnb_issn'].notna()\n",
        "    authors_from_ty = (dnb_ty_df['dnb_found'] == True) & dnb_ty_df['dnb_authors'].notna()\n",
        "    print(f\"   📚 Mit DNB-ISBN (via TY): {isbn_from_ty.sum():,}\")\n",
        "    print(f\"   📰 Mit DNB-ISSN (via TY): {issn_from_ty.sum():,}\")\n",
        "    print(f\"   ✍️  Mit DNB-Autoren (via TY): {authors_from_ty.sum():,}\")\n",
        "\n",
        "print(f\"\\n✅ Titel/Jahr-Daten verfügbar als: dnb_ty_df\")\n",
        "print(f\"   Shape: {dnb_ty_df.shape}\")"
    ],
    "outputs": [],
    "execution_count": None
}

# Insert after title/author cell
nb['cells'].insert(ta_index + 1, title_year_cell)

print(f"✓ Created Title/Year enrichment cell (ID: {title_year_cell['id']})")

# Now update the merge cell to include Title/Year data
merge_cell_index = None
for i, cell in enumerate(nb['cells']):
    if cell.get('id') == '13f121c3':  # Merge cell
        merge_cell_index = i
        break

if merge_cell_index:
    print(f"✓ Found merge cell at index {merge_cell_index}")

    # Read current source
    source = ''.join(nb['cells'][merge_cell_index]['source'])

    # Add Title/Year merge logic before the summary
    insert_marker = "# Zusammenfassung\nprint(f\"\\n📊 === MERGE ZUSAMMENFASSUNG ===\")"

    ty_merge_code = """# 3. Merge Titel/Jahr-basierte DNB-Daten als separate Variante (_ty)
if len(dnb_ty_df) > 0:
    # Prüfe ob ISBN/ISSN-Spalten existieren
    cols_to_merge_ty = ['vdeh_id', 'dnb_title', 'dnb_authors', 'dnb_year', 'dnb_publisher']
    if 'dnb_isbn' in dnb_ty_df.columns:
        cols_to_merge_ty.append('dnb_isbn')
    if 'dnb_issn' in dnb_ty_df.columns:
        cols_to_merge_ty.append('dnb_issn')

    dnb_ty_matches = dnb_ty_df[dnb_ty_df['dnb_found'] == True][cols_to_merge_ty].copy()

    # Rename mit _ty Suffix
    rename_map = {
        'dnb_title': 'dnb_title_ty',
        'dnb_authors': 'dnb_authors_ty',
        'dnb_year': 'dnb_year_ty',
        'dnb_publisher': 'dnb_publisher_ty'
    }
    if 'dnb_isbn' in cols_to_merge_ty:
        rename_map['dnb_isbn'] = 'dnb_isbn_ty'
    if 'dnb_issn' in cols_to_merge_ty:
        rename_map['dnb_issn'] = 'dnb_issn_ty'

    dnb_ty_matches = dnb_ty_matches.rename(columns=rename_map)

    df_enriched = df_enriched.merge(
        dnb_ty_matches,
        left_on='id',
        right_on='vdeh_id',
        how='left'
    )
    if 'vdeh_id' in df_enriched.columns:
        df_enriched.drop(columns=['vdeh_id'], inplace=True)

    print(f"✅ Titel/Jahr-basierte DNB-Daten (TY) gemerged → Spalten: dnb_*_ty")
    if 'dnb_isbn_ty' in df_enriched.columns:
        print(f"   + dnb_isbn_ty, dnb_issn_ty")
    print(f"   TY-Matches: {df_enriched[['dnb_title_ty','dnb_authors_ty','dnb_year_ty','dnb_publisher_ty']].notna().any(axis=1).sum():,}")

# 4. Rückwärtskompatibilität
#    dnb_query_method zeigt nur noch ID-Quelle; Fusion vergleicht alle drei Varianten (ID, TA, TY)

# """

    if insert_marker in source:
        source = source.replace(insert_marker, ty_merge_code + insert_marker)

        # Also update the summary section to include TY stats
        source = source.replace(
            "print(f\"   Mit TA-DNB: {df_enriched[['dnb_title_ta','dnb_authors_ta','dnb_year_ta','dnb_publisher_ta']].notna().any(axis=1).sum():,}\")",
            "print(f\"   Mit TA-DNB: {df_enriched[['dnb_title_ta','dnb_authors_ta','dnb_year_ta','dnb_publisher_ta']].notna().any(axis=1).sum():,}\")\n    print(f\"   Mit TY-DNB: {df_enriched[['dnb_title_ty','dnb_authors_ty','dnb_year_ty','dnb_publisher_ty']].notna().any(axis=1).sum() if 'dnb_title_ty' in df_enriched.columns else 0:,}\")"
        )

        # Add TY stats to ISBN/ISSN summary
        source = source.replace(
            "    print(f\"   Mit DNB-ISSN (TA): {issn_ta_count:,}\")",
            "    print(f\"   Mit DNB-ISSN (TA): {issn_ta_count:,}\")\n\nif 'dnb_isbn_ty' in df_enriched.columns:\n    isbn_ty_count = df_enriched['dnb_isbn_ty'].notna().sum()\n    issn_ty_count = df_enriched.get('dnb_issn_ty', pd.Series()).notna().sum() if 'dnb_issn_ty' in df_enriched.columns else 0\n    authors_ty_count = df_enriched['dnb_authors_ty'].notna().sum() if 'dnb_authors_ty' in df_enriched.columns else 0\n    print(f\"   Mit DNB-ISBN (TY): {isbn_ty_count:,}\")\n    print(f\"   Mit DNB-ISSN (TY): {issn_ty_count:,}\")\n    print(f\"   Mit DNB-Autoren (TY): {authors_ty_count:,}\")"
        )

        nb['cells'][merge_cell_index]['source'] = source.splitlines(keepends=True)
        print(f"✓ Updated merge cell to include Title/Year data")
    else:
        print(f"⚠️  Could not find insertion marker in merge cell")

# Update metadata cell to include TY stats
metadata_cell_index = None
for i, cell in enumerate(nb['cells']):
    if cell.get('id') == '8de03a8f':  # Metadata/save cell
        metadata_cell_index = i
        break

if metadata_cell_index:
    source = ''.join(nb['cells'][metadata_cell_index]['source'])

    # Update dnb_queries to include title_year
    source = source.replace(
        "'title_author': {\n            'total_queries': len(dnb_title_df) if len(dnb_title_df) > 0 else 0,\n            'successful': int((dnb_title_df['dnb_found'] == True).sum()) if len(dnb_title_df) > 0 else 0,\n            'failed': int((dnb_title_df['dnb_found'] == False).sum()) if len(dnb_title_df) > 0 else 0\n        }",
        "'title_author': {\n            'total_queries': len(dnb_title_df) if len(dnb_title_df) > 0 else 0,\n            'successful': int((dnb_title_df['dnb_found'] == True).sum()) if len(dnb_title_df) > 0 else 0,\n            'failed': int((dnb_title_df['dnb_found'] == False).sum()) if len(dnb_title_df) > 0 else 0\n        },\n        'title_year': {\n            'total_queries': len(dnb_ty_df) if 'dnb_ty_df' in locals() and len(dnb_ty_df) > 0 else 0,\n            'successful': int((dnb_ty_df['dnb_found'] == True).sum()) if 'dnb_ty_df' in locals() and len(dnb_ty_df) > 0 else 0,\n            'failed': int((dnb_ty_df['dnb_found'] == False).sum()) if 'dnb_ty_df' in locals() and len(dnb_ty_df) > 0 else 0\n        }"
    )

    # Update dnb_variants
    source = source.replace(
        "'ta_available': int(df_enriched[['dnb_title_ta','dnb_authors_ta','dnb_year_ta','dnb_publisher_ta']].notna().any(axis=1).sum())",
        "'ta_available': int(df_enriched[['dnb_title_ta','dnb_authors_ta','dnb_year_ta','dnb_publisher_ta']].notna().any(axis=1).sum()),\n        'ty_available': int(df_enriched[['dnb_title_ty','dnb_authors_ty','dnb_year_ty','dnb_publisher_ty']].notna().any(axis=1).sum()) if 'dnb_title_ty' in df_enriched.columns else 0"
    )

    # Update dnb_field_availability
    source = source.replace(
        "'title_author': {\n            'title': int(df_enriched['dnb_title_ta'].notna().sum()) if 'dnb_title_ta' in df_enriched.columns else 0,\n            'authors': int(df_enriched['dnb_authors_ta'].notna().sum()) if 'dnb_authors_ta' in df_enriched.columns else 0,\n            'year': int(df_enriched['dnb_year_ta'].notna().sum()) if 'dnb_year_ta' in df_enriched.columns else 0,\n            'publisher': int(df_enriched['dnb_publisher_ta'].notna().sum()) if 'dnb_publisher_ta' in df_enriched.columns else 0\n        }",
        "'title_author': {\n            'title': int(df_enriched['dnb_title_ta'].notna().sum()) if 'dnb_title_ta' in df_enriched.columns else 0,\n            'authors': int(df_enriched['dnb_authors_ta'].notna().sum()) if 'dnb_authors_ta' in df_enriched.columns else 0,\n            'year': int(df_enriched['dnb_year_ta'].notna().sum()) if 'dnb_year_ta' in df_enriched.columns else 0,\n            'publisher': int(df_enriched['dnb_publisher_ta'].notna().sum()) if 'dnb_publisher_ta' in df_enriched.columns else 0\n        },\n        'title_year': {\n            'title': int(df_enriched['dnb_title_ty'].notna().sum()) if 'dnb_title_ty' in df_enriched.columns else 0,\n            'authors': int(df_enriched['dnb_authors_ty'].notna().sum()) if 'dnb_authors_ty' in df_enriched.columns else 0,\n            'year': int(df_enriched['dnb_year_ty'].notna().sum()) if 'dnb_year_ty' in df_enriched.columns else 0,\n            'publisher': int(df_enriched['dnb_publisher_ty'].notna().sum()) if 'dnb_publisher_ty' in df_enriched.columns else 0\n        }"
    )

    # Update summary text
    source = source.replace(
        "print(f\"   TA-Variante verfügbar: {metadata['dnb_variants']['ta_available']:,}\")",
        "print(f\"   TA-Variante verfügbar: {metadata['dnb_variants']['ta_available']:,}\")\n    print(f\"   TY-Variante verfügbar: {metadata['dnb_variants']['ty_available']:,}\")"
    )

    source = source.replace(
        "print(f\"   KI-gestützte Fusion von VDEH und DNB Daten (beide Varianten)\")",
        "print(f\"   KI-gestützte Fusion von VDEH und DNB Daten (alle drei Varianten: ID, TA, TY)\")"
    )

    nb['cells'][metadata_cell_index]['source'] = source.splitlines(keepends=True)
    print(f"✓ Updated metadata cell to include Title/Year stats")

# Update DNB API STATUS cell to mention new function
api_status_index = None
for i, cell in enumerate(nb['cells']):
    if cell.get('id') == 'd57f67b9':
        api_status_index = i
        break

if api_status_index:
    source = ''.join(nb['cells'][api_status_index]['source'])
    source = source.replace(
        "print(f\"     - query_dnb_by_title_author(title, author=None, max_records=1)\")",
        "print(f\"     - query_dnb_by_title_author(title, author=None, max_records=1)\")\nprint(f\"     - query_dnb_by_title_year(title, year, max_records=1)\")"
    )
    nb['cells'][api_status_index]['source'] = source.splitlines(keepends=True)
    print(f"✓ Updated API status cell")

# Write updated notebook
with open('notebooks/01_vdeh_preprocessing/04_vdeh_data_enrichment.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("\n✅ Notebook updated with Title/Year enrichment!")
print("   - Added new Title/Year enrichment cell")
print("   - Updated merge logic to include _ty columns")
print("   - Updated metadata tracking")
print("   - Updated API status documentation")
