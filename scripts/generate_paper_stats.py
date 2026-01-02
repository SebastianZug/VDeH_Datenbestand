#!/usr/bin/env python3
"""
Generiert alle Statistiken für das wissenschaftliche Paper.

Dieses Script berechnet:
1. VDEh Datenqualität
2. Erster UB-Abgleich (nur VDEh)
3. DNB/LoC Anreicherungsstatistiken
4. Verbesserter UB-Abgleich (mit Anreicherung)
5. Vergleichsstatistiken

Output: JSON-Datei mit allen Statistiken für Jinja2-Templates
"""

import sys
from pathlib import Path
import pandas as pd
import json
import re
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def extract_pages(page_str):
    """Extract numeric page count from MAB2 pages field."""
    if pd.isna(page_str):
        return None
    match = re.search(r'\b(\d+)\s*S\.', str(page_str))
    if match:
        return int(match.group(1))
    match = re.search(r'(\d+)', str(page_str))
    if match:
        return int(match.group(1))
    return None


def analyze_vdeh_quality(vdeh_df: pd.DataFrame) -> Dict[str, Any]:
    """Analysiert VDEh Datenqualität."""

    # Extract pages
    vdeh_df['pages_num'] = vdeh_df['pages'].apply(extract_pages)

    total = len(vdeh_df)

    # Basic completeness
    title_count = vdeh_df['title'].notna().sum()
    authors_count = vdeh_df['authors_str'].notna().sum()
    year_count = vdeh_df['year'].notna().sum()
    isbn_count = vdeh_df['isbn'].notna().sum()
    issn_count = vdeh_df['issn'].notna().sum()
    pages_count = vdeh_df['pages_num'].notna().sum()

    # Pages statistics
    total_pages = int(vdeh_df['pages_num'].sum(skipna=True))
    avg_pages = int(total_pages / pages_count) if pages_count > 0 else 0
    estimated_total_pages = total * avg_pages

    # Language distribution
    lang_names = {
        'de': 'Deutsch',
        'en': 'Englisch',
        'unknown': 'Unbekannt',
        'fr': 'Französisch',
        'it': 'Italienisch'
    }

    top_languages = []
    for lang, count in vdeh_df['detected_language'].value_counts().head(5).items():
        top_languages.append((
            lang,
            {
                'name': lang_names.get(lang, lang.upper()),
                'count': int(count),
                'percentage': float(count / total * 100)
            }
        ))

    return {
        'total_records': total,
        'title_count': int(title_count),
        'title_coverage_pct': float(title_count / total * 100),
        'authors_count': int(authors_count),
        'authors_coverage_pct': float(authors_count / total * 100),
        'year_count': int(year_count),
        'year_coverage_pct': float(year_count / total * 100),
        'isbn_count': int(isbn_count),
        'isbn_coverage_pct': float(isbn_count / total * 100),
        'issn_count': int(issn_count),
        'issn_coverage_pct': float(issn_count / total * 100),
        'pages_count': int(pages_count),
        'pages_coverage_pct': float(pages_count / total * 100),
        'total_pages': total_pages,
        'avg_pages': avg_pages,
        'estimated_total_pages': estimated_total_pages,
        'top_languages': top_languages,
        'isbn_issues': {
            'concatenated': 116,  # From previous analysis
            'invalid_checksum': 93
        }
    }


def analyze_ub_freiberg_quality(ub_df: pd.DataFrame) -> Dict[str, Any]:
    """Analysiert UB Freiberg Datenqualität."""

    total = len(ub_df)

    # Basic completeness
    isbn_count = ub_df['isbn'].notna().sum() if 'isbn' in ub_df.columns else 0

    return {
        'total_records': total,
        'isbn_count': int(isbn_count),
        'isbn_coverage_pct': float(isbn_count / total * 100) if total > 0 else 0
    }


def analyze_comparison_v1(vdeh_df: pd.DataFrame, matches_df: pd.DataFrame,
                          fused_df: pd.DataFrame, avg_pages: int) -> Dict[str, Any]:
    """Analysiert ersten UB-Abgleich (nur VDEh-Daten)."""

    # Filter to VDEh-only matches
    vdeh_indices_set = set(matches_df['vdeh_index'].values)
    matched_sources = fused_df.loc[list(vdeh_indices_set), 'title_source']
    vdeh_only_mask = matched_sources == 'vdeh'
    vdeh_only_indices = matched_sources[vdeh_only_mask].index.tolist()

    total_matches = len(vdeh_only_indices)
    total = len(vdeh_df)

    # Books to digitize
    books_to_digitize = total - total_matches
    pages_to_scan = books_to_digitize * avg_pages

    return {
        'total_matches': total_matches,
        'match_rate_pct': float(total_matches / total * 100),
        'books_to_digitize': books_to_digitize,
        'digitization_rate_pct': float(books_to_digitize / total * 100),
        'pages_to_scan': pages_to_scan
    }


def analyze_enrichment(vdeh_df: pd.DataFrame, dnb_df: pd.DataFrame,
                       loc_df: pd.DataFrame, fused_df: pd.DataFrame) -> Dict[str, Any]:
    """Analysiert DNB/LoC Anreicherung."""

    total = len(vdeh_df)

    # DNB counts
    dnb_id_count = dnb_df['dnb_title'].notna().sum()
    dnb_ta_count = dnb_df['dnb_title_ta'].notna().sum()
    dnb_ty_count = dnb_df['dnb_title_ty'].notna().sum()
    dnb_total = dnb_df[['dnb_title', 'dnb_title_ta', 'dnb_title_ty']].notna().any(axis=1).sum()

    # LoC counts
    loc_id_count = loc_df['loc_title'].notna().sum()
    loc_ta_count = loc_df['loc_title_ta'].notna().sum()
    loc_ty_count = loc_df['loc_title_ty'].notna().sum()
    loc_total = loc_df[['loc_title', 'loc_title_ta', 'loc_title_ty']].notna().any(axis=1).sum()

    # Combined
    has_dnb = dnb_df[['dnb_title', 'dnb_title_ta', 'dnb_title_ty']].notna().any(axis=1)
    has_loc = loc_df[['loc_title', 'loc_title_ta', 'loc_title_ty']].notna().any(axis=1)
    total_enriched = (has_dnb | has_loc).sum()
    both_sources = (has_dnb & has_loc).sum()

    # ISBN/ISSN gains
    isbn_before = vdeh_df['isbn'].notna().sum()
    isbn_after = fused_df['isbn'].notna().sum()
    isbn_gain = isbn_after - isbn_before

    issn_before = vdeh_df['issn'].notna().sum()
    issn_after = fused_df['issn'].notna().sum()
    issn_gain = issn_after - issn_before

    # Field-level enrichment gains
    def count_field_gain(vdeh_field: str, fused_field: str, dnb_search: str, loc_search: str,
                         dnb_df: pd.DataFrame, loc_df: pd.DataFrame,
                         fused_df: pd.DataFrame, vdeh_df: pd.DataFrame) -> Dict[str, int]:
        """Count how many records gained a specific field from DNB, LoC, or fusion."""

        # Records without the field in VDEh
        vdeh_missing = vdeh_df[vdeh_field].isna()

        # DNB variants for this field
        dnb_cols = [c for c in dnb_df.columns if c.startswith('dnb_') and dnb_search in c]
        has_dnb_field = dnb_df[dnb_cols].notna().any(axis=1) if dnb_cols else pd.Series(False, index=dnb_df.index)

        # LoC variants for this field
        loc_cols = [c for c in loc_df.columns if c.startswith('loc_') and loc_search in c]
        has_loc_field = loc_df[loc_cols].notna().any(axis=1) if loc_cols else pd.Series(False, index=loc_df.index)

        # Fused field is now filled
        fused_filled = fused_df[fused_field].notna()

        # Total gain: was missing in VDEh, now filled in fused
        total_gain = (vdeh_missing & fused_filled).sum()

        # DNB contribution: was missing, DNB has it, fused is filled
        dnb_gain = (vdeh_missing & has_dnb_field & fused_filled).sum()

        # LoC contribution: was missing, LoC has it, fused is filled
        loc_gain = (vdeh_missing & has_loc_field & fused_filled).sum()

        return {
            'dnb': int(dnb_gain),
            'loc': int(loc_gain),
            'total': int(total_gain)
        }

    # Extract pages for counting
    vdeh_df = vdeh_df.copy()
    dnb_df = dnb_df.copy()
    loc_df = loc_df.copy()
    fused_df = fused_df.copy()

    vdeh_df['pages_num'] = vdeh_df['pages'].apply(extract_pages)
    fused_df['pages_num'] = fused_df['pages'].apply(extract_pages)

    # For DNB, check all page variants
    for col in ['dnb_pages', 'dnb_pages_ta', 'dnb_pages_ty']:
        if col in dnb_df.columns:
            dnb_df[col + '_num'] = dnb_df[col].apply(extract_pages)

    # For LoC, check all page variants
    for col in ['loc_pages', 'loc_pages_ta', 'loc_pages_ty']:
        if col in loc_df.columns:
            loc_df[col + '_num'] = loc_df[col].apply(extract_pages)

    # Calculate gains for each field
    title_gain = count_field_gain('title', 'title', 'title', 'title', dnb_df, loc_df, fused_df, vdeh_df)
    authors_gain = count_field_gain('authors_str', 'authors', 'authors', 'authors', dnb_df, loc_df, fused_df, vdeh_df)
    year_gain = count_field_gain('year', 'year', 'year', 'year', dnb_df, loc_df, fused_df, vdeh_df)

    # ISBN/ISSN with source breakdown
    vdeh_missing_isbn = vdeh_df['isbn'].isna()
    has_dnb_isbn = dnb_df[['dnb_isbn', 'dnb_isbn_ta', 'dnb_isbn_ty']].notna().any(axis=1)
    has_loc_isbn = loc_df[['loc_isbn', 'loc_isbn_ta', 'loc_isbn_ty']].notna().any(axis=1)
    fused_has_isbn = fused_df['isbn'].notna()

    isbn_dnb_gain = (vdeh_missing_isbn & has_dnb_isbn & fused_has_isbn).sum()
    isbn_loc_gain = (vdeh_missing_isbn & has_loc_isbn & fused_has_isbn).sum()

    vdeh_missing_issn = vdeh_df['issn'].isna()
    has_dnb_issn = dnb_df[['dnb_issn', 'dnb_issn_ta', 'dnb_issn_ty']].notna().any(axis=1)
    has_loc_issn = loc_df[['loc_issn', 'loc_issn_ta', 'loc_issn_ty']].notna().any(axis=1)
    fused_has_issn = fused_df['issn'].notna()

    issn_dnb_gain = (vdeh_missing_issn & has_dnb_issn & fused_has_issn).sum()
    issn_loc_gain = (vdeh_missing_issn & has_loc_issn & fused_has_issn).sum()

    # Pages gain
    vdeh_missing_pages = vdeh_df['pages_num'].isna()
    dnb_page_cols = [c for c in dnb_df.columns if c.endswith('_num') and c.startswith('dnb_')]
    loc_page_cols = [c for c in loc_df.columns if c.endswith('_num') and c.startswith('loc_')]

    has_dnb_pages = dnb_df[dnb_page_cols].notna().any(axis=1) if dnb_page_cols else pd.Series(False, index=dnb_df.index)
    has_loc_pages = loc_df[loc_page_cols].notna().any(axis=1) if loc_page_cols else pd.Series(False, index=loc_df.index)
    fused_has_pages = fused_df['pages_num'].notna()

    pages_dnb_gain = (vdeh_missing_pages & has_dnb_pages & fused_has_pages).sum()
    pages_loc_gain = (vdeh_missing_pages & has_loc_pages & fused_has_pages).sum()
    pages_total_gain = (vdeh_missing_pages & fused_has_pages).sum()

    return {
        'dnb_id_count': int(dnb_id_count),
        'dnb_ta_count': int(dnb_ta_count),
        'dnb_ty_count': int(dnb_ty_count),
        'dnb_total': int(dnb_total),
        'dnb_coverage_pct': float(dnb_total / total * 100),
        'loc_id_count': int(loc_id_count),
        'loc_ta_count': int(loc_ta_count),
        'loc_ty_count': int(loc_ty_count),
        'loc_total': int(loc_total),
        'loc_coverage_pct': float(loc_total / total * 100),
        'total_enriched': int(total_enriched),
        'total_coverage_pct': float(total_enriched / total * 100),
        'both_sources': int(both_sources),
        'both_coverage_pct': float(both_sources / total * 100),
        'isbn_before': int(isbn_before),
        'isbn_before_pct': float(isbn_before / total * 100),
        'isbn_after': int(isbn_after),
        'isbn_after_pct': float(isbn_after / total * 100),
        'isbn_gain': int(isbn_gain),
        'isbn_gain_pct': float(isbn_gain / isbn_before * 100) if isbn_before > 0 else 0,
        'issn_before': int(issn_before),
        'issn_before_pct': float(issn_before / total * 100),
        'issn_after': int(issn_after),
        'issn_after_pct': float(issn_after / total * 100),
        'issn_gain': int(issn_gain),
        'issn_gain_pct': float(issn_gain / issn_before * 100) if issn_before > 0 else 0,
        'ai_decisions': 302,  # From fusion statistics
        # Field-level gains
        'field_gains': {
            'title': title_gain,
            'authors': authors_gain,
            'year': year_gain,
            'isbn': {
                'dnb': int(isbn_dnb_gain),
                'loc': int(isbn_loc_gain),
                'total': int(isbn_gain)
            },
            'issn': {
                'dnb': int(issn_dnb_gain),
                'loc': int(issn_loc_gain),
                'total': int(issn_gain)
            },
            'pages': {
                'dnb': int(pages_dnb_gain),
                'loc': int(pages_loc_gain),
                'total': int(pages_total_gain)
            }
        }
    }


def analyze_comparison_v2(matches_df: pd.DataFrame, fused_df: pd.DataFrame,
                          avg_pages: int, v1_results: Dict) -> Dict[str, Any]:
    """Analysiert verbesserten UB-Abgleich (mit DNB/LoC)."""

    total = len(fused_df)
    total_matches = len(matches_df)

    # Match methods
    isbn_matches = (matches_df['match_method'] == 'ISBN').sum()
    fuzzy_matches = (matches_df['match_method'] == 'Title+Author Fuzzy').sum()

    # Match sources
    vdeh_indices_set = set(matches_df['vdeh_index'].values)
    matched_sources = fused_df.loc[list(vdeh_indices_set), 'title_source']
    top_sources = [(source, int(count)) for source, count in matched_sources.value_counts().head(5).items()]

    # Enriched vs original
    vdeh_only_matches = (matched_sources == 'vdeh').sum()
    enriched_matches = total_matches - vdeh_only_matches

    # Digitization
    books_to_digitize = total - total_matches
    pages_to_scan = books_to_digitize * avg_pages
    pages_saved = v1_results['pages_to_scan'] - pages_to_scan

    # Gains
    gain_vs_v1 = total_matches - v1_results['total_matches']
    gain_pct = int(gain_vs_v1 / v1_results['total_matches'] * 100) if v1_results['total_matches'] > 0 else 0

    return {
        'total_matches': total_matches,
        'match_rate_pct': float(total_matches / total * 100),
        'isbn_matches': int(isbn_matches),
        'isbn_match_pct': float(isbn_matches / total_matches * 100),
        'fuzzy_matches': int(fuzzy_matches),
        'fuzzy_match_pct': float(fuzzy_matches / total_matches * 100),
        'top_sources': top_sources,
        'enriched_matches': int(enriched_matches),
        'enriched_match_pct': float(enriched_matches / total_matches * 100),
        'books_to_digitize': books_to_digitize,
        'digitization_rate_pct': float(books_to_digitize / total * 100),
        'pages_to_scan': pages_to_scan,
        'pages_saved': pages_saved,
        'pages_saved_pct': float(pages_saved / v1_results['pages_to_scan'] * 100),
        'gain_vs_v1': gain_vs_v1,
        'gain_pct': gain_pct
    }


def main():
    """Main function."""
    print("=" * 70)
    print("PAPER STATISTIKEN GENERIERUNG")
    print("=" * 70)

    # Paths
    data_dir = project_root / 'data' / 'vdeh' / 'processed'
    ub_data_dir = project_root / 'data' / 'ub_tubaf' / 'processed'
    comparison_dir = project_root / 'data' / 'comparison' / 'matches'

    print("\n1. Lade Daten...")

    # Load data
    vdeh_df = pd.read_parquet(data_dir / '03_language_detected_data.parquet')
    dnb_df = pd.read_parquet(data_dir / '04_dnb_enriched_data.parquet')
    loc_df = pd.read_parquet(data_dir / '04b_loc_enriched_data.parquet')
    fused_df = pd.read_parquet(data_dir / '06_vdeh_dnb_loc_fused_data.parquet')
    matches_df = pd.read_parquet(comparison_dir / 'vdeh_ub_matches_fused.parquet')
    ub_df = pd.read_parquet(ub_data_dir / '01_loaded_data.parquet')

    print(f"   VDEh: {len(vdeh_df):,} records")
    print(f"   UB Freiberg: {len(ub_df):,} records")
    print(f"   Fused: {len(fused_df):,} records")
    print(f"   Matches: {len(matches_df):,} records")

    print("\n2. Analysiere VDEh Datenqualität...")
    vdeh_quality = analyze_vdeh_quality(vdeh_df)
    print(f"   ✓ ISBN-Abdeckung: {vdeh_quality['isbn_coverage_pct']:.1f}%")
    print(f"   ✓ Pages-Abdeckung: {vdeh_quality['pages_coverage_pct']:.1f}%")
    print(f"   ✓ Durchschnitt: {vdeh_quality['avg_pages']} Seiten/Buch")

    print("\n3. Analysiere ersten UB-Abgleich (nur VDEh)...")
    comparison_v1 = analyze_comparison_v1(vdeh_df, matches_df, fused_df, vdeh_quality['avg_pages'])
    print(f"   ✓ Matches: {comparison_v1['total_matches']:,} ({comparison_v1['match_rate_pct']:.2f}%)")
    print(f"   ✓ Zu digitalisieren: {comparison_v1['pages_to_scan']:,} Seiten")

    print("\n4. Analysiere DNB/LoC Anreicherung...")
    enrichment = analyze_enrichment(vdeh_df, dnb_df, loc_df, fused_df)
    print(f"   ✓ DNB: {enrichment['dnb_total']:,} ({enrichment['dnb_coverage_pct']:.1f}%)")
    print(f"   ✓ LoC: {enrichment['loc_total']:,} ({enrichment['loc_coverage_pct']:.1f}%)")
    print(f"   ✓ ISBN-Gewinn: +{enrichment['isbn_gain']} (+{enrichment['isbn_gain_pct']:.1f}%)")

    print("\n5. Analysiere verbesserten UB-Abgleich (mit DNB/LoC)...")
    comparison_v2 = analyze_comparison_v2(matches_df, fused_df, vdeh_quality['avg_pages'], comparison_v1)
    print(f"   ✓ Matches: {comparison_v2['total_matches']:,} ({comparison_v2['match_rate_pct']:.2f}%)")
    print(f"   ✓ Gewinn: +{comparison_v2['gain_vs_v1']:,} (+{comparison_v2['gain_pct']}%)")
    print(f"   ✓ Seiteneinsparung: -{comparison_v2['pages_saved']:,} Seiten")

    print("\n6. Analysiere UB Freiberg Katalog...")
    ub_freiberg_quality = analyze_ub_freiberg_quality(ub_df)
    print(f"   ✓ Total Records: {ub_freiberg_quality['total_records']:,}")
    print(f"   ✓ ISBN-Abdeckung: {ub_freiberg_quality['isbn_coverage_pct']:.1f}%")

    # Combine all results
    results = {
        'vdeh_quality': vdeh_quality,
        'ub_freiberg_quality': ub_freiberg_quality,
        'comparison_v1': comparison_v1,
        'enrichment': enrichment,
        'comparison_v2': comparison_v2,
        'metadata': {
            'generated_at': pd.Timestamp.now().isoformat(),
            'script': 'generate_paper_stats.py'
        }
    }

    # Save to JSON
    output_file = project_root / 'data' / 'processed' / 'paper_statistics.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n7. Speichere Statistiken...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"   ✓ Gespeichert: {output_file}")

    print("\n" + "=" * 70)
    print("✅ STATISTIKEN ERFOLGREICH GENERIERT")
    print("=" * 70)
    print(f"\nNächster Schritt:")
    print(f"  python run_report.py --skip-analysis")
    print(f"\nOutput:")
    print(f"  paper/build/report.md")
    print(f"  paper/build/report.pdf")


if __name__ == '__main__':
    main()
