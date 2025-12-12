#!/usr/bin/env python3
"""Extend report generator to show 'filled', 'corrected', and 'confirmed' columns."""

import pandas as pd

# Load data to calculate corrections and confirmations
df_original = pd.read_parquet('data/vdeh/processed/01_loaded_data.parquet')
df_fused = pd.read_parquet('data/vdeh/processed/05_fused_data.parquet')

print("=== CALCULATING CORRECTIONS AND CONFIRMATIONS ===\n")

# For each field, calculate:
# - Filled: MARC21 empty → Pipeline filled
# - Corrected: MARC21 had value → Pipeline changed it (DNB was chosen)
# - Confirmed: MARC21 had value → Pipeline kept it (confirmed or no DNB match)

results = {}

# Helper: Check if fusion source indicates DNB was chosen
def is_dnb_source(source):
    """Check if source indicates DNB data was used."""
    if pd.isna(source):
        return False
    return 'dnb' in str(source).lower() and 'gap_fill' not in str(source).lower()

# 1. ISBN
had_isbn_01 = df_original['isbn'].notna()
has_isbn_05 = df_fused['isbn'].notna()
isbn_changed = (had_isbn_01 & has_isbn_05 & (df_original['isbn'] != df_fused['isbn']))

# Check if change was from DNB
isbn_source_is_dnb = df_fused['isbn_source'].apply(is_dnb_source) if 'isbn_source' in df_fused.columns else pd.Series([False] * len(df_fused))

results['isbn'] = {
    'filled': (~had_isbn_01 & has_isbn_05).sum(),
    'corrected': (isbn_changed & isbn_source_is_dnb).sum(),
    'confirmed': (had_isbn_01 & has_isbn_05 & (df_original['isbn'] == df_fused['isbn'])).sum()
}

print(f"ISBN:")
print(f"  Filled: {results['isbn']['filled']:,}")
print(f"  Corrected: {results['isbn']['corrected']:,}")
print(f"  Confirmed: {results['isbn']['confirmed']:,}")

# 2. ISSN
if 'issn' in df_original.columns and 'issn' in df_fused.columns:
    had_issn_01 = df_original['issn'].notna()
    has_issn_05 = df_fused['issn'].notna()
    issn_changed = (had_issn_01 & has_issn_05 & (df_original['issn'] != df_fused['issn']))

    issn_source_is_dnb = df_fused['issn_source'].apply(is_dnb_source) if 'issn_source' in df_fused.columns else pd.Series([False] * len(df_fused))

    results['issn'] = {
        'filled': (~had_issn_01 & has_issn_05).sum(),
        'corrected': (issn_changed & issn_source_is_dnb).sum(),
        'confirmed': (had_issn_01 & has_issn_05 & (df_original['issn'] == df_fused['issn'])).sum()
    }

    print(f"\nISSN:")
    print(f"  Filled: {results['issn']['filled']:,}")
    print(f"  Corrected: {results['issn']['corrected']:,}")
    print(f"  Confirmed: {results['issn']['confirmed']:,}")

# 3. Authors
had_authors_01 = (df_original['authors_str'].notna() & (df_original['authors_str'] != ''))
has_authors_05 = (df_fused['authors_str'].notna() & (df_fused['authors_str'] != ''))

# Corrected: fusion source is DNB (not gap_fill, not vdeh, not confirmed)
authors_source_is_dnb = df_fused['fusion_authors_source'].apply(
    lambda x: is_dnb_source(x) if pd.notna(x) else False
) if 'fusion_authors_source' in df_fused.columns else pd.Series([False] * len(df_fused))

# Confirmed: fusion source is 'confirmed'
authors_confirmed = (df_fused['fusion_authors_source'] == 'confirmed') if 'fusion_authors_source' in df_fused.columns else pd.Series([False] * len(df_fused))

results['authors'] = {
    'filled': (~had_authors_01 & has_authors_05).sum(),
    'corrected': (had_authors_01 & authors_source_is_dnb).sum(),
    'confirmed': (had_authors_01 & authors_confirmed).sum()
}

print(f"\nAuthors:")
print(f"  Filled: {results['authors']['filled']:,}")
print(f"  Corrected: {results['authors']['corrected']:,}")
print(f"  Confirmed: {results['authors']['confirmed']:,}")

# 4. Year
had_year_01 = df_original['year'].notna()
has_year_05 = df_fused['year'].notna()

year_source_is_dnb = df_fused['fusion_year_source'].apply(is_dnb_source) if 'fusion_year_source' in df_fused.columns else pd.Series([False] * len(df_fused))
year_confirmed = (df_fused['fusion_year_source'] == 'confirmed') if 'fusion_year_source' in df_fused.columns else pd.Series([False] * len(df_fused))

results['year'] = {
    'filled': (~had_year_01 & has_year_05).sum(),
    'corrected': (had_year_01 & year_source_is_dnb).sum(),
    'confirmed': (had_year_01 & year_confirmed).sum()
}

print(f"\nYear:")
print(f"  Filled: {results['year']['filled']:,}")
print(f"  Corrected: {results['year']['corrected']:,}")
print(f"  Confirmed: {results['year']['confirmed']:,}")

# 5. Publisher
had_pub_01 = df_original['publisher'].notna()
has_pub_05 = df_fused['publisher'].notna()

pub_source_is_dnb = df_fused['fusion_publisher_source'].apply(is_dnb_source) if 'fusion_publisher_source' in df_fused.columns else pd.Series([False] * len(df_fused))
pub_confirmed = (df_fused['fusion_publisher_source'] == 'confirmed') if 'fusion_publisher_source' in df_fused.columns else pd.Series([False] * len(df_fused))

results['publisher'] = {
    'filled': (~had_pub_01 & has_pub_05).sum(),
    'corrected': (had_pub_01 & pub_source_is_dnb).sum(),
    'confirmed': (had_pub_01 & pub_confirmed).sum()
}

print(f"\nPublisher:")
print(f"  Filled: {results['publisher']['filled']:,}")
print(f"  Corrected: {results['publisher']['corrected']:,}")
print(f"  Confirmed: {results['publisher']['confirmed']:,}")

# 6. Language (special case - dual source)
had_lang_01 = df_original['language'].notna() if 'language' in df_original.columns else pd.Series([False] * len(df_original))
has_lang_05 = df_fused['language_final'].notna() if 'language_final' in df_fused.columns else pd.Series([False] * len(df_fused))

# Language confirmed = from MARC21
lang_confirmed = (df_fused['language_source'] == 'marc21') if 'language_source' in df_fused.columns else pd.Series([False] * len(df_fused))

results['language'] = {
    'filled': (~had_lang_01 & has_lang_05).sum(),
    'corrected': 0,  # Language is never "corrected", only filled or confirmed
    'confirmed': (had_lang_01 & lang_confirmed).sum()
}

print(f"\nLanguage:")
print(f"  Filled: {results['language']['filled']:,}")
print(f"  Corrected: {results['language']['corrected']:,} (N/A for language)")
print(f"  Confirmed: {results['language']['confirmed']:,}")

# Save results to JSON for use in notebook
import json
with open('data/vdeh/processed/corrections_confirmations_stats.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\n✅ Statistics saved to corrections_confirmations_stats.json")

# Print summary table
print("\n=== SUMMARY TABLE ===\n")
print("| Feld      | Gefüllt | Korrigiert | Bestätigt |")
print("|-----------|---------|------------|-----------|")
for field in ['isbn', 'issn', 'language', 'authors', 'year', 'publisher']:
    if field in results:
        filled = results[field]['filled']
        corrected = results[field]['corrected']
        confirmed = results[field]['confirmed']
        print(f"| {field:9} | {filled:7,} | {corrected:10,} | {confirmed:9,} |")
