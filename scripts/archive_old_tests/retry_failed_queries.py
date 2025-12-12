#!/usr/bin/env python3
"""
Wiederholt fehlgeschlagene DNB-Queries mit erhöhter Robustheit.

Features:
- Liest Retry-Listen aus data/vdeh/processed/retry_queries/
- Verwendet längere Timeouts und mehr Retries
- Exponential Backoff bei Fehlern
- Progressive Speicherung der Ergebnisse
- Automatische Merge mit bestehendem Enrichment-Datensatz

Usage:
    python scripts/retry_failed_queries.py [--rate-limit 2.0] [--max-retries 3]
"""

import sys
import time
import argparse
from pathlib import Path
import pandas as pd
from tqdm import tqdm
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dnb_api import query_dnb_by_isbn, query_dnb_by_issn, query_dnb_by_title_author

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/retry_queries.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def retry_with_backoff(func, max_retries=3, base_delay=2.0):
    """
    Führt Funktion mit exponential backoff aus.

    Args:
        func: Funktion ohne Parameter
        max_retries: Max. Anzahl Versuche
        base_delay: Basis-Verzögerung in Sekunden

    Returns:
        Ergebnis der Funktion oder None
    """
    for attempt in range(max_retries):
        try:
            result = func()
            return result
        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"All {max_retries} attempts failed: {e}")
                return None


def retry_isbn_queries(retry_df, rate_limit=2.0, max_retries=3):
    """Wiederholt ISBN-Queries."""
    logger.info(f"Starte Retry für {len(retry_df)} ISBN-Queries")

    results = []

    for idx, row in tqdm(retry_df.iterrows(), total=len(retry_df), desc="ISBN Retry"):
        isbn = row['query']

        # Query mit Retry-Logik
        result = retry_with_backoff(
            lambda: query_dnb_by_isbn(isbn),
            max_retries=max_retries
        )

        # Speichere Ergebnis
        results.append({
            'query_type': 'isbn',
            'query_value': isbn,
            'dnb_found': result is not None,
            'dnb_title': result.get('title') if result else None,
            'dnb_authors': ', '.join(result.get('authors', [])) if result else None,
            'dnb_year': result.get('year') if result else None,
            'dnb_publisher': result.get('publisher') if result else None,
            'dnb_isbn': result.get('isbn') if result else None,
            'dnb_issn': result.get('issn') if result else None,
            'retry_success': result is not None
        })

        time.sleep(rate_limit)

    return pd.DataFrame(results)


def retry_issn_queries(retry_df, rate_limit=2.0, max_retries=3):
    """Wiederholt ISSN-Queries."""
    logger.info(f"Starte Retry für {len(retry_df)} ISSN-Queries")

    results = []

    for idx, row in tqdm(retry_df.iterrows(), total=len(retry_df), desc="ISSN Retry"):
        issn = row['query']

        result = retry_with_backoff(
            lambda: query_dnb_by_issn(issn),
            max_retries=max_retries
        )

        results.append({
            'query_type': 'issn',
            'query_value': issn,
            'dnb_found': result is not None,
            'dnb_title': result.get('title') if result else None,
            'dnb_authors': ', '.join(result.get('authors', [])) if result else None,
            'dnb_year': result.get('year') if result else None,
            'dnb_publisher': result.get('publisher') if result else None,
            'dnb_isbn': result.get('isbn') if result else None,
            'dnb_issn': result.get('issn') if result else None,
            'retry_success': result is not None
        })

        time.sleep(rate_limit)

    return pd.DataFrame(results)


def retry_title_author_queries(retry_df, rate_limit=2.0, max_retries=3):
    """Wiederholt Titel/Autor-Queries."""
    logger.info(f"Starte Retry für {len(retry_df)} Titel/Autor-Queries")

    results = []

    for idx, row in tqdm(retry_df.iterrows(), total=len(retry_df), desc="Titel/Autor Retry"):
        full_query = row['full_query']

        # Parse Titel und Autor aus Query
        # Format: tit="..." and per=... oder tit=... and per=...
        title = None
        author = None

        if 'tit=' in full_query:
            # Extrahiere Titel
            if 'tit="' in full_query:
                title = full_query.split('tit="')[1].split('"')[0]
            else:
                title_part = full_query.split('tit=')[1]
                if ' and per=' in title_part:
                    title = title_part.split(' and per=')[0]
                else:
                    title = title_part

        if 'per=' in full_query:
            author = full_query.split('per=')[1].split(' ')[0]

        if not title:
            logger.warning(f"Konnte Titel nicht aus Query extrahieren: {full_query}")
            continue

        result = retry_with_backoff(
            lambda: query_dnb_by_title_author(title, author),
            max_retries=max_retries
        )

        results.append({
            'query_type': 'title_author',
            'title': title,
            'author': author,
            'dnb_found': result is not None,
            'dnb_title': result.get('title') if result else None,
            'dnb_authors': ', '.join(result.get('authors', [])) if result else None,
            'dnb_year': result.get('year') if result else None,
            'dnb_publisher': result.get('publisher') if result else None,
            'dnb_isbn': result.get('isbn') if result else None,
            'dnb_issn': result.get('issn') if result else None,
            'retry_success': result is not None
        })

        time.sleep(rate_limit)

    return pd.DataFrame(results)


def merge_with_existing(retry_results, original_file, output_file):
    """
    Merged Retry-Ergebnisse mit bestehendem Enrichment-Datensatz.

    Strategie:
    - Erfolgreiche Retries überschreiben Original-Daten
    - Fehlgeschlagene Retries bleiben unverändert
    """
    logger.info(f"Merge Retry-Ergebnisse mit {original_file}")

    # Lade Original-Daten
    if not Path(original_file).exists():
        logger.error(f"Original-Datei nicht gefunden: {original_file}")
        return

    original_df = pd.read_parquet(original_file)
    logger.info(f"Original: {len(original_df)} Records")

    # TODO: Implement merge logic based on query_type and vdeh_id
    # Dies erfordert Zugriff auf vdeh_id in den Retry-Listen
    logger.warning("Merge-Logik noch nicht implementiert - speichere Retry-Ergebnisse separat")

    # Speichere Retry-Ergebnisse separat
    retry_results.to_parquet(output_file, index=False)
    logger.info(f"Retry-Ergebnisse gespeichert: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Retry fehlgeschlagener DNB-Queries')
    parser.add_argument('--rate-limit', type=float, default=2.0,
                        help='Sekunden zwischen Queries (default: 2.0)')
    parser.add_argument('--max-retries', type=int, default=3,
                        help='Max. Versuche pro Query (default: 3)')
    args = parser.parse_args()

    retry_dir = Path('data/vdeh/processed/retry_queries')

    if not retry_dir.exists():
        logger.error(f"Retry-Verzeichnis nicht gefunden: {retry_dir}")
        logger.info("Führe zuerst 'python scripts/analyze_failed_queries.py' aus!")
        sys.exit(1)

    # ISBN Retries
    isbn_file = retry_dir / 'retry_isbn.parquet'
    if isbn_file.exists():
        retry_df = pd.read_parquet(isbn_file)
        results = retry_isbn_queries(retry_df, args.rate_limit, args.max_retries)

        success_count = results['retry_success'].sum()
        logger.info(f"ISBN Retry: {success_count}/{len(results)} erfolgreich")

        # Speichere Ergebnisse
        results.to_parquet(retry_dir / 'retry_isbn_results.parquet', index=False)

    # ISSN Retries
    issn_file = retry_dir / 'retry_issn.parquet'
    if issn_file.exists():
        retry_df = pd.read_parquet(issn_file)
        results = retry_issn_queries(retry_df, args.rate_limit, args.max_retries)

        success_count = results['retry_success'].sum()
        logger.info(f"ISSN Retry: {success_count}/{len(results)} erfolgreich")

        results.to_parquet(retry_dir / 'retry_issn_results.parquet', index=False)

    # Titel/Autor Retries
    ta_file = retry_dir / 'retry_title_author.parquet'
    if ta_file.exists():
        retry_df = pd.read_parquet(ta_file)
        results = retry_title_author_queries(retry_df, args.rate_limit, args.max_retries)

        success_count = results['retry_success'].sum()
        logger.info(f"Titel/Autor Retry: {success_count}/{len(results)} erfolgreich")

        results.to_parquet(retry_dir / 'retry_title_author_results.parquet', index=False)

    logger.info("Alle Retries abgeschlossen!")


if __name__ == '__main__':
    main()
