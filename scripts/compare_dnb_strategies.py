#!/usr/bin/env python3
"""
Vergleicht DNB-Abfrage-Strategien: v2.1.0 (Baseline) vs v2.2.0 (Enhanced)

Analysiert:
- Erfolgsraten pro Methode (ISBN/ISSN, Titel/Autor, Titel/Jahr)
- Neue Matches durch verbesserte Strategien
- Gerettete Queries durch Normalisierung/Truncation

Author: Bibliographic Data Analysis
Date: December 2025
"""

import sys
from pathlib import Path
import pandas as pd
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))


def load_baseline_data(processed_dir: Path):
    """Lädt Baseline-Daten (v2.1.0) aus Backup."""
    backup_dir = processed_dir / 'backup_v2.1.0_baseline'

    data = {}

    # ISBN/ISSN data
    isbn_file = backup_dir / 'dnb_raw_data.parquet'
    if isbn_file.exists():
        data['isbn_issn'] = pd.read_parquet(isbn_file)

    # Title/Author data
    ta_file = backup_dir / 'dnb_title_author_data.parquet'
    if ta_file.exists():
        data['title_author'] = pd.read_parquet(ta_file)

    # Title/Year data
    ty_file = backup_dir / 'dnb_title_year_data.parquet'
    if ty_file.exists():
        data['title_year'] = pd.read_parquet(ty_file)

    return data


def load_enhanced_data(processed_dir: Path):
    """Lädt Enhanced-Daten (v2.2.0) nach Re-Run."""
    data = {}

    # ISBN/ISSN data
    isbn_file = processed_dir / 'dnb_raw_data.parquet'
    if isbn_file.exists():
        data['isbn_issn'] = pd.read_parquet(isbn_file)

    # Title/Author data
    ta_file = processed_dir / 'dnb_title_author_data.parquet'
    if ta_file.exists():
        data['title_author'] = pd.read_parquet(ta_file)

    # Title/Year data
    ty_file = processed_dir / 'dnb_title_year_data.parquet'
    if ty_file.exists():
        data['title_year'] = pd.read_parquet(ty_file)

    return data


def calculate_success_rates(data: dict) -> dict:
    """Berechnet Erfolgsraten für alle Methoden."""
    rates = {}

    for method, df in data.items():
        if df is not None and len(df) > 0:
            total = len(df)
            found = (df['dnb_found'] == True).sum()
            rate = found / total * 100

            rates[method] = {
                'total': total,
                'found': found,
                'not_found': total - found,
                'success_rate': rate
            }

    return rates


def compare_strategies(baseline_data: dict, enhanced_data: dict) -> dict:
    """Vergleicht Baseline vs Enhanced Strategien."""
    comparison = {}

    for method in ['isbn_issn', 'title_author', 'title_year']:
        baseline_df = baseline_data.get(method)
        enhanced_df = enhanced_data.get(method)

        if baseline_df is None or enhanced_df is None:
            continue

        # Erfolgsraten
        baseline_found = (baseline_df['dnb_found'] == True).sum()
        enhanced_found = (enhanced_df['dnb_found'] == True).sum()

        baseline_rate = baseline_found / len(baseline_df) * 100
        enhanced_rate = enhanced_found / len(enhanced_df) * 100

        # Neue Matches
        new_matches = enhanced_found - baseline_found
        improvement = enhanced_rate - baseline_rate

        comparison[method] = {
            'baseline': {
                'total': len(baseline_df),
                'found': baseline_found,
                'rate': baseline_rate
            },
            'enhanced': {
                'total': len(enhanced_df),
                'found': enhanced_found,
                'rate': enhanced_rate
            },
            'delta': {
                'new_matches': new_matches,
                'improvement_pct': improvement,
                'improvement_abs': new_matches
            }
        }

    return comparison


def analyze_new_matches(baseline_data: dict, enhanced_data: dict) -> pd.DataFrame:
    """Analysiert welche Records neu gefunden wurden."""
    new_matches_list = []

    for method in ['isbn_issn', 'title_author', 'title_year']:
        baseline_df = baseline_data.get(method)
        enhanced_df = enhanced_data.get(method)

        if baseline_df is None or enhanced_df is None:
            continue

        # Merge um Unterschiede zu finden
        merged = enhanced_df.merge(
            baseline_df[['vdeh_id', 'dnb_found']],
            on='vdeh_id',
            how='left',
            suffixes=('_enhanced', '_baseline')
        )

        # Neue Matches: In Enhanced gefunden, aber nicht in Baseline
        new_in_enhanced = merged[
            (merged['dnb_found_enhanced'] == True) &
            ((merged['dnb_found_baseline'] == False) | (merged['dnb_found_baseline'].isna()))
        ]

        if len(new_in_enhanced) > 0:
            new_in_enhanced['method'] = method
            new_matches_list.append(new_in_enhanced)

    if new_matches_list:
        return pd.concat(new_matches_list, ignore_index=True)
    else:
        return pd.DataFrame()


def print_comparison_report(comparison: dict):
    """Gibt detaillierten Vergleichs-Report aus."""
    print("\n" + "=" * 80)
    print("DNB STRATEGY COMPARISON: v2.1.0 (Baseline) vs v2.2.0 (Enhanced)")
    print("=" * 80)

    print(f"\n📊 Generiert: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    for method, data in comparison.items():
        method_name = method.replace('_', '/').upper()

        print(f"\n{'─' * 80}")
        print(f"📚 {method_name}")
        print(f"{'─' * 80}")

        baseline = data['baseline']
        enhanced = data['enhanced']
        delta = data['delta']

        print(f"\n  Baseline (v2.1.0):")
        print(f"    Total Queries:   {baseline['total']:,}")
        print(f"    Gefunden:        {baseline['found']:,}")
        print(f"    Erfolgsrate:     {baseline['rate']:.2f}%")

        print(f"\n  Enhanced (v2.2.0):")
        print(f"    Total Queries:   {enhanced['total']:,}")
        print(f"    Gefunden:        {enhanced['found']:,}")
        print(f"    Erfolgsrate:     {enhanced['rate']:.2f}%")

        print(f"\n  Δ Verbesserung:")
        improvement_symbol = "✅" if delta['improvement_pct'] > 0 else "⚠️"
        print(f"    {improvement_symbol} Neue Matches:     {delta['new_matches']:+,}")
        print(f"    {improvement_symbol} Rate-Änderung:    {delta['improvement_pct']:+.2f} Prozentpunkte")

        if delta['improvement_pct'] > 0:
            relative_improvement = (delta['new_matches'] / baseline['found'] * 100) if baseline['found'] > 0 else 0
            print(f"    📈 Relative Steigerung: +{relative_improvement:.1f}% mehr Matches")

    # Gesamtübersicht
    print(f"\n{'=' * 80}")
    print("🎯 GESAMTBILANZ")
    print(f"{'=' * 80}")

    total_baseline_found = sum(data['baseline']['found'] for data in comparison.values())
    total_enhanced_found = sum(data['enhanced']['found'] for data in comparison.values())
    total_improvement = total_enhanced_found - total_baseline_found

    print(f"\n  Baseline Gesamt:  {total_baseline_found:,} Matches")
    print(f"  Enhanced Gesamt:  {total_enhanced_found:,} Matches")
    print(f"  Δ Verbesserung:   {total_improvement:+,} Matches")

    if total_baseline_found > 0:
        total_relative = total_improvement / total_baseline_found * 100
        print(f"  📈 Gesamt-Steigerung: +{total_relative:.1f}%")


def main():
    """Hauptfunktion."""
    # Konfiguration
    processed_dir = project_root / 'data' / 'vdeh' / 'processed'
    backup_dir = processed_dir / 'backup_v2.1.0_baseline'

    # Prüfe ob Backup existiert
    if not backup_dir.exists():
        print(f"❌ Fehler: Backup-Verzeichnis nicht gefunden: {backup_dir}")
        print(f"   Bitte zuerst Backup erstellen!")
        return 1

    print("🔍 Lade Baseline-Daten (v2.1.0)...")
    baseline_data = load_baseline_data(processed_dir)

    print("🔍 Lade Enhanced-Daten (v2.2.0)...")
    enhanced_data = load_enhanced_data(processed_dir)

    # Prüfe ob beide Datensätze vorhanden
    if not baseline_data or not enhanced_data:
        print("❌ Fehler: Daten nicht vollständig geladen!")
        return 1

    # Berechne Erfolgsraten
    print("\n📊 Berechne Erfolgsraten...")
    baseline_rates = calculate_success_rates(baseline_data)
    enhanced_rates = calculate_success_rates(enhanced_data)

    # Vergleiche Strategien
    print("📊 Vergleiche Strategien...")
    comparison = compare_strategies(baseline_data, enhanced_data)

    # Report ausgeben
    print_comparison_report(comparison)

    # Analysiere neue Matches (optional)
    print(f"\n{'=' * 80}")
    print("🔬 NEUE MATCHES ANALYSE")
    print(f"{'=' * 80}")

    new_matches = analyze_new_matches(baseline_data, enhanced_data)

    if len(new_matches) > 0:
        print(f"\n✨ Insgesamt {len(new_matches):,} neue Matches gefunden!")
        print(f"\n  Pro Methode:")
        method_counts = new_matches['method'].value_counts()
        for method, count in method_counts.items():
            print(f"    {method}: {count:,}")

        # Speichere neue Matches für detaillierte Analyse
        output_file = processed_dir / 'new_matches_v2.2.0.parquet'
        new_matches.to_parquet(output_file, index=False)
        print(f"\n💾 Neue Matches gespeichert: {output_file.name}")
    else:
        print("\nℹ️  Keine neuen Matches gefunden (oder Daten noch nicht mit v2.2.0 abgefragt)")

    print("\n" + "=" * 80)
    print("✅ Vergleich abgeschlossen!")
    print("=" * 80)

    return 0


if __name__ == '__main__':
    sys.exit(main())
