#!/usr/bin/env python3
"""
Wiederholt fehlgeschlagene Queries aus dem DNB-Enrichment.

Liest dnb_raw_data.parquet und dnb_title_author_data.parquet,
identifiziert alle dnb_found=False Einträge und versucht diese
erneut mit erhöhter Retry-Logik (5 Versuche statt 3).

Usage:
    poetry run python scripts/retry_failed_from_enrichment.py
"""

import sys
from pathlib import Path
import pandas as pd
import time
from tqdm.auto import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dnb_api import query_dnb_by_isbn, query_dnb_by_issn, query_dnb_by_title_author

def retry_failed_isbn_issn_queries():
    """Wiederholt fehlgeschlagene ISBN/ISSN-Queries."""

    data_file = Path('data/vdeh/processed/dnb_raw_data.parquet')

    if not data_file.exists():
        print(f"❌ Keine DNB-Daten gefunden: {data_file}")
        return 0, 0

    print("\n" + "="*80)
    print("📚 RETRY: ISBN/ISSN-QUERIES")
    print("="*80)

    # Lade Daten
    df = pd.read_parquet(data_file)

    # Filter fehlgeschlagene Queries
    failed = df[df['dnb_found'] == False].copy()

    if len(failed) == 0:
        print("✅ Keine fehlgeschlagenen ISBN/ISSN-Queries gefunden!")
        return 0, 0

    print(f"\n📋 Gefunden: {len(failed):,} fehlgeschlagene Queries")
    print(f"   ISBN: {(failed['query_type'] == 'ISBN').sum():,}")
    print(f"   ISSN: {(failed['query_type'] == 'ISSN').sum():,}")

    # Rate Limiting und Retry-Einstellungen
    RATE_LIMIT = 2.0  # 2 Sekunden zwischen Queries (erhöht für Stabilität)
    MAX_RETRIES = 5   # 5 Versuche statt 3

    print(f"\n⚙️  Konfiguration:")
    print(f"   Rate Limit: {RATE_LIMIT}s zwischen Queries")
    print(f"   Max Retries: {MAX_RETRIES} Versuche pro Query")
    print(f"   Exponential Backoff: 2s → 4s → 8s → 16s → 32s")

    input("\n▶️  Drücke ENTER zum Starten oder CTRL+C zum Abbrechen...")

    # Statistik
    stats = {'success': 0, 'still_failed': 0}
    updates = []

    print(f"\n🔄 Starte Retry für {len(failed):,} Queries...\n")

    for idx, row in tqdm(failed.iterrows(), total=len(failed), desc="🔍 Retry"):
        # Query ausführen
        result = None

        if row['query_type'] == 'ISBN':
            result = query_dnb_by_isbn(row['query_value'], max_retries=MAX_RETRIES)
        elif row['query_type'] == 'ISSN':
            result = query_dnb_by_issn(row['query_value'], max_retries=MAX_RETRIES)

        if result:
            # Erfolg! Update vorbereiten
            stats['success'] += 1

            updates.append({
                'index': idx,
                'dnb_found': True,
                'dnb_title': result.get('title'),
                'dnb_authors': ', '.join(result.get('authors', [])) if result.get('authors') else None,
                'dnb_year': result.get('year'),
                'dnb_publisher': result.get('publisher'),
                'dnb_isbn': result.get('isbn'),
                'dnb_issn': result.get('issn')
            })
        else:
            stats['still_failed'] += 1

        # Rate Limiting
        time.sleep(RATE_LIMIT)

    # Updates anwenden
    if updates:
        print(f"\n💾 Aktualisiere {len(updates):,} erfolgreiche Retries...")

        for update in updates:
            idx = update.pop('index')
            for col, val in update.items():
                df.at[idx, col] = val

        # Backup erstellen
        backup_file = data_file.with_suffix('.parquet.backup')
        if not backup_file.exists():
            df_original = pd.read_parquet(data_file)
            df_original.to_parquet(backup_file, index=False)
            print(f"   📦 Backup erstellt: {backup_file.name}")

        # Aktualisierte Daten speichern
        df.to_parquet(data_file, index=False)
        print(f"   ✅ Daten aktualisiert: {data_file.name}")

    # Zusammenfassung
    print(f"\n📊 === ERGEBNIS ===")
    print(f"   Versucht: {len(failed):,}")
    print(f"   ✅ Erfolgreich: {stats['success']:,} ({stats['success']/len(failed)*100:.1f}%)")
    print(f"   ❌ Weiterhin fehlgeschlagen: {stats['still_failed']:,} ({stats['still_failed']/len(failed)*100:.1f}%)")

    return stats['success'], stats['still_failed']


def retry_failed_title_author_queries():
    """Wiederholt fehlgeschlagene Titel/Autor-Queries."""

    data_file = Path('data/vdeh/processed/dnb_title_author_data.parquet')

    if not data_file.exists():
        print(f"\n⚠️  Keine Titel/Autor-Daten gefunden: {data_file}")
        return 0, 0

    print("\n" + "="*80)
    print("📖 RETRY: TITEL/AUTOR-QUERIES")
    print("="*80)

    # Lade Daten
    df = pd.read_parquet(data_file)

    # Filter fehlgeschlagene Queries
    failed = df[df['dnb_found'] == False].copy()

    if len(failed) == 0:
        print("✅ Keine fehlgeschlagenen Titel/Autor-Queries gefunden!")
        return 0, 0

    print(f"\n📋 Gefunden: {len(failed):,} fehlgeschlagene Titel/Autor-Queries")

    # Rate Limiting und Retry-Einstellungen
    RATE_LIMIT = 2.0
    MAX_RETRIES = 5

    print(f"\n⚙️  Konfiguration:")
    print(f"   Rate Limit: {RATE_LIMIT}s zwischen Queries")
    print(f"   Max Retries: {MAX_RETRIES} Versuche pro Query")

    input("\n▶️  Drücke ENTER zum Starten oder CTRL+C zum Abbrechen...")

    # Statistik
    stats = {'success': 0, 'still_failed': 0}
    updates = []

    print(f"\n🔄 Starte Retry für {len(failed):,} Queries...\n")

    for idx, row in tqdm(failed.iterrows(), total=len(failed), desc="🔍 Retry T/A"):
        # Query ausführen
        result = query_dnb_by_title_author(
            row['title'],
            row.get('author'),
            max_retries=MAX_RETRIES
        )

        if result:
            stats['success'] += 1

            updates.append({
                'index': idx,
                'dnb_found': True,
                'dnb_title': result.get('title'),
                'dnb_authors': ', '.join(result.get('authors', [])) if result.get('authors') else None,
                'dnb_year': result.get('year'),
                'dnb_publisher': result.get('publisher'),
                'dnb_isbn': result.get('isbn'),
                'dnb_issn': result.get('issn')
            })
        else:
            stats['still_failed'] += 1

        time.sleep(RATE_LIMIT)

    # Updates anwenden
    if updates:
        print(f"\n💾 Aktualisiere {len(updates):,} erfolgreiche Retries...")

        for update in updates:
            idx = update.pop('index')
            for col, val in update.items():
                df.at[idx, col] = val

        # Backup
        backup_file = data_file.with_suffix('.parquet.backup')
        if not backup_file.exists():
            df_original = pd.read_parquet(data_file)
            df_original.to_parquet(backup_file, index=False)
            print(f"   📦 Backup erstellt: {backup_file.name}")

        # Speichern
        df.to_parquet(data_file, index=False)
        print(f"   ✅ Daten aktualisiert: {data_file.name}")

    # Zusammenfassung
    print(f"\n📊 === ERGEBNIS ===")
    print(f"   Versucht: {len(failed):,}")
    print(f"   ✅ Erfolgreich: {stats['success']:,} ({stats['success']/len(failed)*100:.1f}%)")
    print(f"   ❌ Weiterhin fehlgeschlagen: {stats['still_failed']:,} ({stats['still_failed']/len(failed)*100:.1f}%)")

    return stats['success'], stats['still_failed']


def main():
    print("\n" + "="*80)
    print("🔄 DNB ENRICHMENT RETRY TOOL")
    print("="*80)
    print("\nWiederholt fehlgeschlagene Queries mit erhöhter Retry-Logik")
    print("(5 Versuche statt 3, 2s Rate Limit)")

    # ISBN/ISSN Retries
    isbn_success, isbn_failed = retry_failed_isbn_issn_queries()

    # Titel/Autor Retries
    ta_success, ta_failed = retry_failed_title_author_queries()

    # Gesamtzusammenfassung
    total_success = isbn_success + ta_success
    total_failed = isbn_failed + ta_failed

    print("\n" + "="*80)
    print("🎉 GESAMT-ERGEBNIS")
    print("="*80)
    print(f"   ✅ Erfolgreich nachgeholt: {total_success:,}")
    print(f"   ❌ Weiterhin fehlgeschlagen: {total_failed:,}")

    if total_success > 0:
        print(f"\n💡 Nächster Schritt:")
        print(f"   Führe das Enrichment-Notebook erneut aus (Zelle 13)")
        print(f"   um die aktualisierten DNB-Daten mit VDEH zu mergen:")
        print(f"   notebooks/01_vdeh_preprocessing/04_vdeh_data_enrichment.ipynb")

    print("\n" + "="*80)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Abgebrochen durch Benutzer")
        sys.exit(1)
