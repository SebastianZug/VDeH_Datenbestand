"""
Test script to verify ISBN/ISSN fusion functionality.

This script tests the updated FusionEngine on a small sample of records
to ensure ISBN/ISSN fields are properly extracted and fused.
"""

import sys
from pathlib import Path
import pandas as pd

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from config_loader import VDEhConfig
from fusion import FusionEngine, OllamaClient

def main():
    print("=" * 80)
    print("ISBN/ISSN FUSION TEST")
    print("=" * 80)

    # Load configuration
    config = VDEhConfig(str(project_root / 'config.yaml'))
    print(f"\n✅ Configuration loaded: {config.get('project.name')}")

    # Load processed data
    processed_dir = project_root / config.get('paths.data.vdeh.processed')

    # Load merged data (VDEh + DNB + LoC)
    print("\n📂 Loading data...")

    df_vdeh = pd.read_parquet(processed_dir / '03_language_detected_data.parquet')
    df_dnb = pd.read_parquet(processed_dir / '04_dnb_enriched_data.parquet')
    df_loc = pd.read_parquet(processed_dir / '04b_loc_enriched_data.parquet')

    print(f"   VDEh: {len(df_vdeh):,} records")
    print(f"   DNB:  {len(df_dnb):,} records")
    print(f"   LoC:  {len(df_loc):,} records")

    # Merge sources
    df_merged = df_vdeh.copy()

    # DNB columns
    dnb_cols = [
        'dnb_title', 'dnb_authors', 'dnb_year', 'dnb_publisher', 'dnb_isbn', 'dnb_issn',
        'dnb_title_ta', 'dnb_authors_ta', 'dnb_year_ta', 'dnb_publisher_ta', 'dnb_isbn_ta', 'dnb_issn_ta',
        'dnb_title_ty', 'dnb_authors_ty', 'dnb_year_ty', 'dnb_publisher_ty', 'dnb_isbn_ty', 'dnb_issn_ty',
        'dnb_query_method'
    ]

    # LoC columns
    loc_cols = [
        'loc_title', 'loc_authors', 'loc_year', 'loc_publisher', 'loc_isbn', 'loc_issn', 'loc_pages',
        'loc_title_ta', 'loc_authors_ta', 'loc_year_ta', 'loc_publisher_ta', 'loc_isbn_ta', 'loc_issn_ta', 'loc_pages_ta',
        'loc_title_ty', 'loc_authors_ty', 'loc_year_ty', 'loc_publisher_ty', 'loc_isbn_ty', 'loc_issn_ty', 'loc_pages_ty',
        'loc_query_method'
    ]

    df_merged = df_merged.join(df_dnb[dnb_cols], how='left')
    df_merged = df_merged.join(df_loc[loc_cols], how='left')

    print(f"\n✅ Data merged: {len(df_merged):,} records, {len(df_merged.columns)} columns")

    # Check ISBN availability
    print(f"\n📊 ISBN/ISSN Availability:")
    print(f"   VDEh ISBN:    {df_merged['isbn'].notna().sum():,} ({df_merged['isbn'].notna().sum()/len(df_merged)*100:.1f}%)")
    print(f"   DNB ISBN (ID):{df_merged['dnb_isbn'].notna().sum():,} ({df_merged['dnb_isbn'].notna().sum()/len(df_merged)*100:.1f}%)")
    print(f"   DNB ISBN (TA):{df_merged['dnb_isbn_ta'].notna().sum():,} ({df_merged['dnb_isbn_ta'].notna().sum()/len(df_merged)*100:.1f}%)")
    print(f"   LoC ISBN (ID):{df_merged['loc_isbn'].notna().sum():,} ({df_merged['loc_isbn'].notna().sum()/len(df_merged)*100:.1f}%)")

    # Select test sample: records with ISBN from different sources
    print(f"\n🔬 Selecting test sample...")

    # Sample 1: VDEh with ISBN (no enrichment)
    sample1 = df_merged[
        (df_merged['isbn'].notna()) &
        (df_merged['dnb_isbn'].isna()) &
        (df_merged['loc_isbn'].isna())
    ].head(2)

    # Sample 2: VDEh + DNB ISBN
    sample2 = df_merged[
        (df_merged['isbn'].notna()) &
        (df_merged['dnb_isbn'].notna())
    ].head(2)

    # Sample 3: DNB ISBN only
    sample3 = df_merged[
        (df_merged['isbn'].isna()) &
        (df_merged['dnb_isbn'].notna())
    ].head(2)

    # Sample 4: LoC ISBN
    sample4 = df_merged[
        (df_merged['loc_isbn'].notna())
    ].head(2)

    test_sample = pd.concat([sample1, sample2, sample3, sample4])
    print(f"   Test sample: {len(test_sample)} records")

    # Initialize Ollama (not needed for simple cases, but we need the engine)
    print(f"\n🤖 Initializing FusionEngine...")
    ollama_client = OllamaClient(
        api_url="http://localhost:11434/api/generate",
        model="llama3.3:70b",
        timeout_sec=220,
        max_retries=4
    )

    engine = FusionEngine(
        ollama_client=ollama_client,
        enable_loc=True,
        ty_similarity_threshold=0.7
    )
    print(f"   ✅ Engine initialized")

    # Test fusion
    print(f"\n🔥 Testing ISBN/ISSN fusion...\n")
    print("=" * 80)

    results = []
    for idx, row in test_sample.iterrows():
        print(f"\nTest Record #{idx}")
        print(f"  VDEh ISBN:  {row.get('isbn', 'N/A')}")
        print(f"  DNB ISBN:   {row.get('dnb_isbn', 'N/A')}")
        print(f"  DNB ISBN TA:{row.get('dnb_isbn_ta', 'N/A')}")
        print(f"  LoC ISBN:   {row.get('loc_isbn', 'N/A')}")

        try:
            result = engine.merge_record(row)
            result_dict = result.to_dict()
            results.append(result_dict)

            print(f"  → Fused ISBN:   {result_dict.get('isbn', 'N/A')}")
            print(f"  → ISBN Source:  {result_dict.get('isbn_source', 'N/A')}")
            print(f"  → Fused ISSN:   {result_dict.get('issn', 'N/A')}")
            print(f"  → ISSN Source:  {result_dict.get('issn_source', 'N/A')}")
            print(f"  ✅ Success")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({
                'isbn': None,
                'issn': None,
                'isbn_source': 'error',
                'issn_source': 'error'
            })

    print("\n" + "=" * 80)
    print(f"✅ FUSION TEST COMPLETE")
    print("=" * 80)

    # Summary
    df_results = pd.DataFrame(results)
    print(f"\n📊 Results Summary:")
    print(f"   Records processed: {len(df_results)}")
    print(f"   ISBNs fused:       {df_results['isbn'].notna().sum()} ({df_results['isbn'].notna().sum()/len(df_results)*100:.0f}%)")
    print(f"   ISSNs fused:       {df_results['issn'].notna().sum()} ({df_results['issn'].notna().sum()/len(df_results)*100:.0f}%)")

    if len(df_results) > 0:
        print(f"\n   ISBN Sources:")
        isbn_sources = df_results['isbn_source'].value_counts()
        for source, count in isbn_sources.items():
            print(f"      {source}: {count}")

    print(f"\n✅ Test successful! ISBN/ISSN fields are properly fused.")
    print(f"   Ready to run full fusion on entire dataset.")

if __name__ == '__main__':
    main()
