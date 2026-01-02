#!/usr/bin/env python3
"""
ISBN Corruption Fix Script

Dieses Script behebt die ISBN-Korruption in dnb_raw_data.parquet und
führt einen automatischen Re-Run der gesamten Pipeline durch.

Schritte:
1. Backup aller betroffenen Dateien
2. Identifizierung und Löschung korrupter ISBN-Einträge
3. Neuabfrage der DNB für betroffene ISBNs
4. Re-Merge der DNB-Daten
5. Re-Run der Fusion
6. Re-Run des UB-Matchings
7. Neuberechnung der Statistiken

Geschätzte Dauer: ~50-60 Minuten
"""

import pandas as pd
import sys
from pathlib import Path
import shutil
import time
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from config_loader import VDEHConfig
from dnb_api import query_dnb_by_isbn, query_dnb_by_issn

def create_backup(file_path: Path, backup_dir: Path) -> Path:
    """Erstellt ein Backup einer Datei."""
    if not file_path.exists():
        return None

    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{file_path.stem}_BACKUP_{timestamp}{file_path.suffix}"

    shutil.copy2(file_path, backup_path)
    logger.info(f"✅ Backup erstellt: {backup_path.name}")
    return backup_path

def identify_corrupted_isbns(dnb_raw_df: pd.DataFrame) -> pd.DataFrame:
    """Identifiziert korrupte ISBN-Einträge."""
    # ISBNs mit Länge > 15 sind korrupt (normale ISBN-10 = 10, ISBN-13 = 13)
    corrupted = dnb_raw_df[
        (dnb_raw_df['query_type'] == 'ISBN') &
        (dnb_raw_df['query_value'].str.len() > 15)
    ].copy()

    logger.info(f"📊 Korrupte ISBN-Einträge gefunden: {len(corrupted):,}")
    return corrupted

def fix_dnb_raw_data(data_dir: Path, rate_limit: float = 1.0) -> tuple[pd.DataFrame, int]:
    """
    Behebt korrupte ISBNs in dnb_raw_data.parquet.

    Returns:
        Tuple aus (bereinigte DNB-Daten, Anzahl neu abgefragter ISBNs)
    """
    dnb_raw_path = data_dir / 'dnb_raw_data.parquet'

    logger.info("="*70)
    logger.info("SCHRITT 1: DNB Raw Data Fix")
    logger.info("="*70)

    # Load data
    dnb_raw = pd.read_parquet(dnb_raw_path)
    logger.info(f"📂 DNB Raw Data geladen: {len(dnb_raw):,} Einträge")

    # Identify corrupted entries
    corrupted = identify_corrupted_isbns(dnb_raw)

    if len(corrupted) == 0:
        logger.info("✅ Keine korrupten ISBNs gefunden!")
        return dnb_raw, 0

    # Get original ISBNs from VDEH data
    vdeh_data = pd.read_parquet(data_dir / '03_language_detected_data.parquet')

    # Remove corrupted entries
    logger.info(f"🗑️  Lösche {len(corrupted):,} korrupte Einträge...")
    dnb_raw_clean = dnb_raw[~dnb_raw.index.isin(corrupted.index)].copy()

    # Prepare re-queries
    logger.info(f"📋 Bereite Neuabfragen vor...")
    requery_list = []

    for _, corrupt_row in corrupted.iterrows():
        vdeh_id = corrupt_row['vdeh_id']

        # Get original ISBN from VDEH
        vdeh_row = vdeh_data[vdeh_data['id'] == vdeh_id]
        if len(vdeh_row) == 0:
            logger.warning(f"⚠️  VDEH ID {vdeh_id} nicht gefunden - überspringe")
            continue

        vdeh_row = vdeh_row.iloc[0]
        original_isbn = vdeh_row.get('isbn')

        if pd.notna(original_isbn):
            requery_list.append({
                'vdeh_id': vdeh_id,
                'isbn': original_isbn,
                'query_type': 'ISBN'
            })

    logger.info(f"🔄 {len(requery_list):,} ISBNs werden neu abgefragt...")
    logger.info(f"⏱️  Geschätzte Dauer: ~{len(requery_list) * rate_limit / 60:.0f} Minuten")

    # Re-query DNB
    from tqdm import tqdm
    new_results = []
    stats = {'found': 0, 'not_found': 0}

    for item in tqdm(requery_list, desc="🔍 DNB Re-Query", unit="queries"):
        # Query DNB
        dnb_result = query_dnb_by_isbn(item['isbn'])

        # Store result
        result_row = {
            'vdeh_id': item['vdeh_id'],
            'query_type': item['query_type'],
            'query_value': item['isbn'],
            'dnb_found': dnb_result is not None,
            'dnb_title': dnb_result.get('title') if dnb_result else None,
            'dnb_authors': ', '.join(dnb_result.get('authors', [])) if dnb_result else None,
            'dnb_year': dnb_result.get('year') if dnb_result else None,
            'dnb_publisher': dnb_result.get('publisher') if dnb_result else None,
            'dnb_isbn': dnb_result.get('isbn') if dnb_result else None,
            'dnb_issn': dnb_result.get('issn') if dnb_result else None,
            'dnb_pages': dnb_result.get('pages') if dnb_result else None
        }

        new_results.append(result_row)

        if dnb_result:
            stats['found'] += 1
        else:
            stats['not_found'] += 1

        # Rate limiting
        time.sleep(rate_limit)

    # Add new results to clean data
    new_results_df = pd.DataFrame(new_results)
    dnb_raw_fixed = pd.concat([dnb_raw_clean, new_results_df], ignore_index=True)

    # Save fixed data
    dnb_raw_fixed.to_parquet(dnb_raw_path, index=False)
    logger.info(f"💾 Bereinigte DNB-Daten gespeichert: {dnb_raw_path.name}")

    logger.info(f"\n📊 Neuabfrage-Ergebnisse:")
    logger.info(f"   ✅ Gefunden: {stats['found']:,} ({stats['found']/len(requery_list)*100:.1f}%)")
    logger.info(f"   ❌ Nicht gefunden: {stats['not_found']:,} ({stats['not_found']/len(requery_list)*100:.1f}%)")

    return dnb_raw_fixed, len(requery_list)

def run_enrichment_merge(data_dir: Path):
    """Führt den DNB Enrichment Merge neu aus."""
    logger.info("\n" + "="*70)
    logger.info("SCHRITT 2: DNB Enrichment Merge")
    logger.info("="*70)

    # Load data
    vdeh = pd.read_parquet(data_dir / '03_language_detected_data.parquet')
    dnb_raw = pd.read_parquet(data_dir / 'dnb_raw_data.parquet')
    dnb_ta = pd.read_parquet(data_dir / 'dnb_title_author_data.parquet')
    dnb_ty = pd.read_parquet(data_dir / 'dnb_title_year_data.parquet')

    logger.info(f"📂 Daten geladen:")
    logger.info(f"   VDEH: {len(vdeh):,}")
    logger.info(f"   DNB Raw: {len(dnb_raw):,}")
    logger.info(f"   DNB Title/Author: {len(dnb_ta):,}")
    logger.info(f"   DNB Title/Year: {len(dnb_ty):,}")

    # Start with VDEH data
    df_enriched = vdeh.copy()

    # Merge ISBN/ISSN-based DNB data
    cols_to_merge = ['vdeh_id', 'query_type', 'dnb_title', 'dnb_authors',
                     'dnb_year', 'dnb_publisher', 'dnb_isbn', 'dnb_issn', 'dnb_pages']

    dnb_isbn_issn = dnb_raw[dnb_raw['dnb_found'] == True][cols_to_merge].rename(
        columns={'query_type': 'dnb_query_method'}
    )

    df_enriched = df_enriched.merge(
        dnb_isbn_issn,
        left_on='id',
        right_on='vdeh_id',
        how='left',
        suffixes=('', '_dup')
    )

    # Drop duplicates
    if 'vdeh_id' in df_enriched.columns:
        df_enriched.drop(columns=['vdeh_id'], inplace=True)
    dup_cols = [c for c in df_enriched.columns if c.endswith('_dup')]
    if dup_cols:
        df_enriched.drop(columns=dup_cols, inplace=True)

    logger.info(f"✅ ISBN/ISSN DNB-Daten gemerged")

    # Merge Title/Author data
    cols_ta = ['vdeh_id', 'dnb_title', 'dnb_authors', 'dnb_year',
               'dnb_publisher', 'dnb_isbn', 'dnb_issn', 'dnb_pages']

    dnb_ta_matches = dnb_ta[dnb_ta['dnb_found'] == True][cols_ta].copy()
    dnb_ta_matches = dnb_ta_matches.rename(columns={
        'dnb_title': 'dnb_title_ta',
        'dnb_authors': 'dnb_authors_ta',
        'dnb_year': 'dnb_year_ta',
        'dnb_publisher': 'dnb_publisher_ta',
        'dnb_isbn': 'dnb_isbn_ta',
        'dnb_issn': 'dnb_issn_ta',
        'dnb_pages': 'dnb_pages_ta'
    })

    df_enriched = df_enriched.merge(
        dnb_ta_matches,
        left_on='id',
        right_on='vdeh_id',
        how='left'
    )
    if 'vdeh_id' in df_enriched.columns:
        df_enriched.drop(columns=['vdeh_id'], inplace=True)

    logger.info(f"✅ Title/Author DNB-Daten gemerged")

    # Merge Title/Year data
    dnb_ty_matches = dnb_ty[dnb_ty['dnb_found'] == True][cols_ta].copy()
    dnb_ty_matches = dnb_ty_matches.rename(columns={
        'dnb_title': 'dnb_title_ty',
        'dnb_authors': 'dnb_authors_ty',
        'dnb_year': 'dnb_year_ty',
        'dnb_publisher': 'dnb_publisher_ty',
        'dnb_isbn': 'dnb_isbn_ty',
        'dnb_issn': 'dnb_issn_ty',
        'dnb_pages': 'dnb_pages_ty'
    })

    df_enriched = df_enriched.merge(
        dnb_ty_matches,
        left_on='id',
        right_on='vdeh_id',
        how='left'
    )
    if 'vdeh_id' in df_enriched.columns:
        df_enriched.drop(columns=['vdeh_id'], inplace=True)

    logger.info(f"✅ Title/Year DNB-Daten gemerged")

    # Normalize year columns
    year_columns = ['year', 'dnb_year', 'dnb_year_ta', 'dnb_year_ty']
    for col in year_columns:
        if col in df_enriched.columns:
            df_enriched[col] = pd.to_numeric(df_enriched[col], errors='coerce').astype('Int64')

    # Save
    output_path = data_dir / '04_dnb_enriched_data.parquet'
    df_enriched.to_parquet(output_path, index=False)
    logger.info(f"💾 DNB-angereicherte Daten gespeichert: {output_path.name}")
    logger.info(f"   Records: {len(df_enriched):,}")

    return df_enriched

def run_fusion_pipeline(project_root: Path):
    """Führt die Fusion-Pipeline neu aus."""
    logger.info("\n" + "="*70)
    logger.info("SCHRITT 3: Fusion Pipeline")
    logger.info("="*70)

    # Run fusion notebook via papermill
    from papermill import execute_notebook

    fusion_notebook = project_root / 'notebooks' / '01_vdeh_preprocessing' / '05_vdeh_dnb_loc_fusion.ipynb'
    output_notebook = project_root / 'notebooks' / '01_vdeh_preprocessing' / '05_vdeh_dnb_loc_fusion_output.ipynb'

    logger.info(f"🚀 Starte Fusion-Notebook...")

    try:
        execute_notebook(
            str(fusion_notebook),
            str(output_notebook),
            kernel_name='python3'
        )
        logger.info(f"✅ Fusion erfolgreich abgeschlossen")
    except Exception as e:
        logger.error(f"❌ Fusion fehlgeschlagen: {e}")
        raise

def run_comparison_pipeline(project_root: Path):
    """Führt das UB-Matching neu aus."""
    logger.info("\n" + "="*70)
    logger.info("SCHRITT 4: UB Matching")
    logger.info("="*70)

    comparison_notebook = project_root / 'notebooks' / '02_ub_comparision' / 'data_matching.ipynb'
    output_notebook = project_root / 'notebooks' / '02_ub_comparision' / 'data_matching_output.ipynb'

    logger.info(f"🚀 Starte UB-Matching...")

    from papermill import execute_notebook

    try:
        execute_notebook(
            str(comparison_notebook),
            str(output_notebook),
            kernel_name='python3'
        )
        logger.info(f"✅ UB-Matching erfolgreich abgeschlossen")
    except Exception as e:
        logger.error(f"❌ UB-Matching fehlgeschlagen: {e}")
        raise

def regenerate_statistics(project_root: Path):
    """Regeneriert die Paper-Statistiken."""
    logger.info("\n" + "="*70)
    logger.info("SCHRITT 5: Statistiken neu berechnen")
    logger.info("="*70)

    stats_script = project_root / 'scripts' / 'generate_paper_stats.py'

    if not stats_script.exists():
        logger.warning(f"⚠️  Statistik-Script nicht gefunden: {stats_script}")
        return

    import subprocess
    result = subprocess.run(
        ['poetry', 'run', 'python', str(stats_script)],
        cwd=project_root,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        logger.info(f"✅ Statistiken erfolgreich neu berechnet")
    else:
        logger.error(f"❌ Statistik-Berechnung fehlgeschlagen:")
        logger.error(result.stderr)

def main():
    """Hauptfunktion für den kompletten Fix-Prozess."""
    logger.info("="*70)
    logger.info("ISBN CORRUPTION FIX - AUTOMATED PIPELINE")
    logger.info("="*70)
    logger.info("")
    logger.info("Dieser Prozess wird:")
    logger.info("  1. Backups aller Dateien erstellen")
    logger.info("  2. Korrupte ISBNs identifizieren und löschen")
    logger.info("  3. DNB neu abfragen (~40 Min)")
    logger.info("  4. DNB-Daten neu mergen (~2 Min)")
    logger.info("")
    logger.info("Geschätzte Gesamtdauer: ~43 Minuten")
    logger.info("")
    logger.info("HINWEIS: Fusion, UB-Matching und Statistiken müssen Sie")
    logger.info("         anschließend manuell durchführen.")
    logger.info("")

    # Confirm
    response = input("Möchten Sie fortfahren? (ja/nein): ")
    if response.lower() not in ['ja', 'j', 'yes', 'y']:
        logger.info("Abgebrochen.")
        return

    start_time = time.time()

    # Setup paths
    config = VDEHConfig()
    project_root = config.project_root
    data_dir = project_root / config.get('paths.data.vdeh.processed')
    backup_dir = data_dir / 'backups' / f"isbn_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Create backups
    logger.info("\n📦 Erstelle Backups...")
    backup_files = [
        'dnb_raw_data.parquet',
        '04_dnb_enriched_data.parquet',
        '04b_loc_enriched_data.parquet',
        '06_vdeh_dnb_loc_fused_data.parquet'
    ]

    for filename in backup_files:
        file_path = data_dir / filename
        create_backup(file_path, backup_dir)

    # Fix DNB raw data
    dnb_fixed, requery_count = fix_dnb_raw_data(data_dir, rate_limit=1.0)

    # Re-run enrichment merge
    df_enriched = run_enrichment_merge(data_dir)

    # Summary
    elapsed = time.time() - start_time
    logger.info("\n" + "="*70)
    logger.info("✅ ISBN CORRUPTION FIX ABGESCHLOSSEN")
    logger.info("="*70)
    logger.info(f"")
    logger.info(f"⏱️  Gesamtdauer: {elapsed/60:.1f} Minuten")
    logger.info(f"📊 {requery_count:,} ISBNs neu abgefragt")
    logger.info(f"💾 Backups gespeichert in: {backup_dir}")
    logger.info(f"")
    logger.info(f"✅ DNB-Daten erfolgreich bereinigt und neu abgefragt!")
    logger.info(f"")
    logger.info(f"⚠️  NÄCHSTE SCHRITTE (MANUELL DURCHFÜHREN):")
    logger.info(f"")
    logger.info(f"  1. Fusion-Pipeline:")
    logger.info(f"     notebooks/01_vdeh_preprocessing/05_vdeh_dnb_loc_fusion.ipynb")
    logger.info(f"")
    logger.info(f"  2. UB-Matching:")
    logger.info(f"     notebooks/02_ub_comparision/data_matching.ipynb")
    logger.info(f"")
    logger.info(f"  3. Statistiken neu berechnen:")
    logger.info(f"     poetry run python scripts/generate_paper_stats.py")
    logger.info(f"")
    logger.info(f"  Die Backups können bei Bedarf gelöscht werden.")

if __name__ == '__main__':
    main()
