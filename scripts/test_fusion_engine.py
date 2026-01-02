#!/usr/bin/env python3
"""
Test the extended FusionEngine with 3-source fusion (VDEh + DNB + LoC).
"""

import sys
from pathlib import Path
import pandas as pd
import json

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from fusion import FusionEngine, OllamaClient

def main():

    # Load test data
    test_data_path = project_root / 'data' / 'vdeh' / 'test' / 'test_sample.pkl'
    test_data = pd.read_pickle(test_data_path)
    df_test = test_data['df_test']

    print(f"Loaded {len(df_test)} test records\n")

    # Initialize Ollama client
    ollama_client = OllamaClient(
        api_url="http://localhost:11434/api/generate",
        model="llama3.3:70b",
        timeout_sec=220
    )

    # Initialize FusionEngine
    engine = FusionEngine(
        ollama_client=ollama_client,
        enable_loc=True
    )

    # Test with 5 records
    test_records = [6652, 26374, 38578, 1590, 2086]

    results = []
    for idx in test_records:
        print(f"\n{'='*80}")
        print(f"Testing record {idx}")
        print(f"{'='*80}")

        row = df_test.loc[idx]

        # Show VDEh data
        print(f"\nVDEh: {row.get('title', 'N/A')[:60]}... ({row.get('year', 'N/A')}) | Lang: {row.get('detected_language', 'N/A')}")

        # Merge record
        try:
            result = engine.merge_record(row)

            print(f"\n✅ SUCCESS")
            print(f"   Title source: {result.title_source}")
            print(f"   DNB variant: {result.dnb_variant_selected}")
            if result.fusion_trigger_reason:
                print(f"   Trigger: {result.fusion_trigger_reason}")
            if result.fusion_selected_variant:
                print(f"   Selected: {result.fusion_selected_variant}")
            if result.fusion_conflicts_detected:
                conflicts = json.loads(result.fusion_conflicts_detected)
                print(f"   Conflicts: {list(conflicts.keys())}")
            if result.ai_reasoning:
                print(f"   AI reasoning: {result.ai_reasoning[:80]}...")

            results.append({
                'index': idx,
                'vdeh_title': row.get('title', 'N/A')[:60],
                'language': row.get('detected_language'),
                'title_source': result.title_source,
                'dnb_variant': result.dnb_variant_selected,
                'trigger_reason': result.fusion_trigger_reason,
                'selected_variant': result.fusion_selected_variant,
                'ai_reasoning': result.ai_reasoning[:100] if result.ai_reasoning else None,
                'success': True
            })

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

            results.append({
                'index': idx,
                'vdeh_title': row.get('title', 'N/A')[:60],
                'language': row.get('detected_language'),
                'error': str(e),
                'success': False
            })

    # Summary
    print(f"\n\n{'='*80}")
    print(f"TEST SUMMARY")
    print(f"{'='*80}\n")

    success_count = sum(1 for r in results if r.get('success', False))
    print(f"Passed: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")

    if success_count < len(results):
        print(f"\nFailed tests:")
        for r in results:
            if not r.get('success', False):
                print(f"   - Record {r['index']}: {r.get('error', 'Unknown error')}")

    # Save results
    output_path = project_root / 'data' / 'vdeh' / 'test' / 'fusion_engine_test_results.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Results saved to: {output_path}")

    return 0 if success_count == len(results) else 1

if __name__ == '__main__':
    sys.exit(main())
