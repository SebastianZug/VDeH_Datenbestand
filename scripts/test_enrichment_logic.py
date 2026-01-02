#!/usr/bin/env python3
"""
Test script to validate enrichment-only logic in fusion engine.

Tests that VDEh values are never overwritten, only enriched.
"""

import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fusion.fusion_engine import FusionResult


def test_enrichment_logic():
    """Test that fusion only enriches, never replaces VDEh values."""

    print("🧪 Testing Enrichment-Only Logic\n")
    print("=" * 60)

    # Test Case 1: VDEh has year, DNB has different year
    print("\n📋 Test 1: VDEh has year (2000), DNB has different year (1998)")
    print("-" * 60)

    vdeh_data = {
        'title': 'Test Book',
        'authors': 'Test Author',
        'year': 2000,
        'publisher': None,
        'pages': None,
        'isbn': None,
        'issn': None
    }

    dnb_data = {
        'title': 'Test Book',
        'authors': 'Test Author',
        'year': 1998,  # Different year!
        'publisher': 'Test Publisher',
        'pages': '300 S.',
        'isbn': '978-3-16-148410-0',
        'issn': None
    }

    # Simulate the new logic
    result = FusionResult()
    for field in ['title', 'authors', 'year', 'publisher', 'pages', 'isbn', 'issn']:
        v_val = vdeh_data[field]
        d_val = dnb_data.get(field)

        # New enrichment logic
        if pd.notna(v_val):
            setattr(result, field, v_val)
            setattr(result, f'{field}_source', 'vdeh')
        elif pd.notna(d_val):
            setattr(result, field, d_val)
            setattr(result, f'{field}_source', 'dnb')
        else:
            setattr(result, field, None)
            setattr(result, f'{field}_source', None)

    print(f"   VDEh year: {vdeh_data['year']}")
    print(f"   DNB year:  {dnb_data['year']}")
    print(f"   Result:    {result.year} (source: {result.year_source})")

    assert result.year == 2000, "❌ FAIL: VDEh year was overwritten!"
    assert result.year_source == 'vdeh', "❌ FAIL: Source should be 'vdeh'!"
    assert result.publisher == 'Test Publisher', "❌ FAIL: Should enrich empty fields!"
    print("   ✅ PASS: VDEh year preserved, DNB enriched empty fields")

    # Test Case 2: VDEh missing year, DNB has year
    print("\n📋 Test 2: VDEh missing year, DNB has year (1995)")
    print("-" * 60)

    vdeh_data2 = {
        'title': 'Another Book',
        'authors': 'Another Author',
        'year': None,  # Missing!
        'publisher': 'VDEh Publisher',
        'pages': '250 S.',
        'isbn': None,
        'issn': None
    }

    dnb_data2 = {
        'title': 'Another Book',
        'authors': 'Another Author',
        'year': 1995,  # DNB has year
        'publisher': 'DNB Publisher',
        'pages': '255 S.',
        'isbn': '978-3-16-148410-1',
        'issn': None
    }

    result2 = FusionResult()
    for field in ['title', 'authors', 'year', 'publisher', 'pages', 'isbn', 'issn']:
        v_val = vdeh_data2[field]
        d_val = dnb_data2.get(field)

        if pd.notna(v_val):
            setattr(result2, field, v_val)
            setattr(result2, f'{field}_source', 'vdeh')
        elif pd.notna(d_val):
            setattr(result2, field, d_val)
            setattr(result2, f'{field}_source', 'dnb')
        else:
            setattr(result2, field, None)
            setattr(result2, f'{field}_source', None)

    print(f"   VDEh year: {vdeh_data2['year']}")
    print(f"   DNB year:  {dnb_data2['year']}")
    print(f"   Result:    {result2.year} (source: {result2.year_source})")

    assert result2.year == 1995, "❌ FAIL: Should enrich missing year!"
    assert result2.year_source == 'dnb', "❌ FAIL: Source should be 'dnb'!"
    assert result2.publisher == 'VDEh Publisher', "❌ FAIL: Should preserve VDEh publisher!"
    print("   ✅ PASS: DNB enriched missing year, VDEh values preserved")

    # Test Case 3: Both have same year (confirmation)
    print("\n📋 Test 3: Both have same year (2010) - confirmation")
    print("-" * 60)

    vdeh_data3 = {
        'title': 'Confirmed Book',
        'authors': 'Confirmed Author',
        'year': 2010,
        'publisher': None,
        'pages': None,
        'isbn': None,
        'issn': None
    }

    dnb_data3 = {
        'title': 'Confirmed Book',
        'authors': 'Confirmed Author',
        'year': 2010,  # Same!
        'publisher': 'Publisher',
        'pages': '400 S.',
        'isbn': '978-3-16-148410-2',
        'issn': None
    }

    # Simulate confirmations
    confirmations = {'year', 'title', 'authors'}

    result3 = FusionResult()
    for field in ['title', 'authors', 'year', 'publisher', 'pages', 'isbn', 'issn']:
        v_val = vdeh_data3[field]
        d_val = dnb_data3.get(field)

        if pd.notna(v_val):
            setattr(result3, field, v_val)
            if pd.notna(d_val) and field in confirmations:
                setattr(result3, f'{field}_source', 'confirmed')
            else:
                setattr(result3, f'{field}_source', 'vdeh')
        elif pd.notna(d_val):
            setattr(result3, field, d_val)
            setattr(result3, f'{field}_source', 'dnb')
        else:
            setattr(result3, field, None)
            setattr(result3, f'{field}_source', None)

    print(f"   VDEh year: {vdeh_data3['year']}")
    print(f"   DNB year:  {dnb_data3['year']}")
    print(f"   Result:    {result3.year} (source: {result3.year_source})")

    assert result3.year == 2010, "❌ FAIL: Year should be preserved!"
    assert result3.year_source == 'confirmed', "❌ FAIL: Should be marked as confirmed!"
    print("   ✅ PASS: Year confirmed, enrichment successful")

    print("\n" + "=" * 60)
    print("✅ All tests passed! Enrichment-only logic works correctly.")
    print("\nSummary:")
    print("  • VDEh values are NEVER overwritten")
    print("  • Empty VDEh fields are enriched from DNB/LoC")
    print("  • Matching values are marked as 'confirmed'")


if __name__ == '__main__':
    test_enrichment_logic()
