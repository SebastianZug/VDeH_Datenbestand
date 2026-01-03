#!/usr/bin/env python3
"""
Generiert alle Abbildungen für das wissenschaftliche Paper.

Dieses Script erstellt:
1. Seitenzahlen-Histogramm

Output: PNG und PDF Dateien in reports/paper/figures/
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def extract_page_number(pages_str):
    """
    Extract numeric page count from various page string formats.

    Handles common formats:
    - "188 S." -> 188
    - "XV, 250 p." -> 250 (ignores Roman numerals)
    - "192 pages" -> 192
    """
    if pd.isna(pages_str) or not pages_str:
        return None

    pages_str = str(pages_str).strip()

    patterns = [
        r'(\d+)\s*(?:S\.|p\.|pages?|Seiten?)',
        r'(\d+)\s*$',
        r'(\d+)\s*[,:]',
    ]

    numbers = []
    for pattern in patterns:
        matches = re.findall(pattern, pages_str, re.IGNORECASE)
        numbers.extend([int(m) for m in matches])

    if not numbers:
        return None

    return max(numbers)


def generate_pages_histogram(fused_df: pd.DataFrame, output_dir: Path) -> dict:
    """
    Generiert Histogramm der Seitenzahlen.

    Returns:
        dict: Statistiken zu den Seitenzahlen
    """
    print("  Generiere Seitenzahlen-Histogramm...")

    # Extract numeric page counts
    fused_df = fused_df.copy()
    fused_df['pages_num'] = fused_df['pages'].apply(extract_page_number)

    # Filter valid page counts
    valid_pages = fused_df['pages_num'].dropna()

    stats = {
        'total_records': len(fused_df),
        'records_with_pages': len(valid_pages),
        'coverage_pct': len(valid_pages) / len(fused_df) * 100,
        'min': int(valid_pages.min()),
        'max': int(valid_pages.max()),
        'mean': float(valid_pages.mean()),
        'median': float(valid_pages.median()),
        'std': float(valid_pages.std()),
        'q25': float(valid_pages.quantile(0.25)),
        'q75': float(valid_pages.quantile(0.75)),
    }

    # Create figure - sized for 95% of A4 text width (~16cm -> 15.2cm = 6 inches)
    fig_width = 6.0  # inches (≈ 15.2 cm, 95% of typical A4 text width)
    fig_height = fig_width * 0.6  # aspect ratio for single histogram
    fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height))

    # Font sizes for compact figure
    label_fontsize = 9
    title_fontsize = 10
    legend_fontsize = 8
    tick_fontsize = 8

    # Full distribution (capped at 1000 for visibility)
    pages_capped = valid_pages[valid_pages <= 1000]
    ax.hist(pages_capped, bins=50, edgecolor='black', linewidth=0.3, alpha=0.7, color='steelblue')
    ax.set_xlabel('Seitenzahl', fontsize=label_fontsize)
    ax.set_ylabel('Anzahl Werke', fontsize=label_fontsize)
    ax.set_title(f'Verteilung der Seitenzahlen (n={len(pages_capped):,} Werke mit max. 1000 Seiten)', fontsize=title_fontsize)
    ax.axvline(valid_pages.median(), color='red', linestyle='--', linewidth=1.5,
               label=f'Median: {valid_pages.median():.0f}')
    ax.axvline(valid_pages.mean(), color='orange', linestyle='--', linewidth=1.5,
               label=f'Mittelwert: {valid_pages.mean():.0f}')
    ax.legend(fontsize=legend_fontsize, loc='upper right')
    ax.tick_params(axis='both', labelsize=tick_fontsize)
    ax.grid(axis='y', alpha=0.3, linewidth=0.5)

    plt.tight_layout()

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    png_path = output_dir / 'seitenzahlen_histogramm.png'
    pdf_path = output_dir / 'seitenzahlen_histogramm.pdf'

    plt.savefig(png_path, dpi=150, bbox_inches='tight')
    plt.savefig(pdf_path, bbox_inches='tight')
    plt.close()

    print(f"    ✓ {png_path}")
    print(f"    ✓ {pdf_path}")

    return stats


def main():
    """Main function."""
    print("=" * 70)
    print("PAPER ABBILDUNGEN GENERIERUNG")
    print("=" * 70)

    # Paths
    data_dir = project_root / 'data' / 'vdeh' / 'processed'
    output_dir = project_root / 'reports' / 'paper' / 'figures'

    print("\n1. Lade Daten...")
    fused_df = pd.read_parquet(data_dir / '06_vdeh_dnb_loc_fused_data.parquet')
    print(f"   ✓ Fused: {len(fused_df):,} records")

    print("\n2. Generiere Abbildungen...")

    # Generate pages histogram
    pages_stats = generate_pages_histogram(fused_df, output_dir)
    print(f"   Seitenzahlen-Statistik:")
    print(f"     - Abdeckung: {pages_stats['coverage_pct']:.1f}%")
    print(f"     - Median: {pages_stats['median']:.0f} Seiten")
    print(f"     - Mittelwert: {pages_stats['mean']:.0f} Seiten")

    print("\n" + "=" * 70)
    print("✅ ABBILDUNGEN ERFOLGREICH GENERIERT")
    print("=" * 70)


if __name__ == '__main__':
    main()
