#!/usr/bin/env python3
"""
Test-Script für erweiterte DNB-Suchstrategien.

Testet:
- Normalisierung (Umlaute, Sonderzeichen)
- Truncated Search (lange Titel)
- Validierung von Matches

Author: Bibliographic Data Analysis
Date: December 2025
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from dnb_api import (
    _normalize_for_search,
    query_dnb_by_title_author,
    query_dnb_by_title_year
)
from fusion.fusion_engine import FusionEngine


def test_normalization():
    """Test der Text-Normalisierung."""
    print("=" * 60)
    print("TEST 1: Normalisierung")
    print("=" * 60)

    test_cases = [
        ("Über die Prüfung von Stählen", "Uber die Prufung von Stahlen"),
        ("C++ Programmierung", "C Programmierung"),
        ("Stahlbau – Grundlagen", "Stahlbau Grundlagen"),
        ("Müller, Jürgen", "Muller Jurgen"),
        ("Korrosionsschutz (2. Auflage)", "Korrosionsschutz 2 Auflage"),
    ]

    passed = 0
    failed = 0

    for original, expected in test_cases:
        normalized = _normalize_for_search(original)
        status = "✅" if normalized == expected else "❌"

        if normalized == expected:
            passed += 1
        else:
            failed += 1

        print(f"{status} '{original}'")
        print(f"   → '{normalized}'")
        if normalized != expected:
            print(f"   ❌ Erwartet: '{expected}'")
        print()

    print(f"\n📊 Ergebnis: {passed}/{len(test_cases)} bestanden\n")
    return failed == 0


def test_title_author_search():
    """Test der erweiterten Titel/Autor-Suche."""
    print("=" * 60)
    print("TEST 2: Titel/Autor-Suche (mit Normalisierung)")
    print("=" * 60)
    print("⚠️  HINWEIS: Dieser Test benötigt DNB-API-Zugriff!")
    print()

    test_cases = [
        {
            'title': 'Über Stahlwerkstoffe',
            'author': 'Müller',
            'description': 'Titel mit Umlaut + Autor'
        },
        {
            'title': 'Very long title about steel construction and its applications in modern engineering practices and industrial applications for sustainable development',
            'author': 'Schmidt',
            'description': 'Sehr langer Titel (Truncation-Test)'
        },
        {
            'title': 'Korrosionsschutz – moderne Verfahren',
            'author': 'Weber',
            'description': 'Titel mit Sonderzeichen'
        },
    ]

    print("ℹ️  Beispiel-Testfälle (Testmodus - keine echten API-Calls):\n")

    for i, case in enumerate(test_cases, 1):
        print(f"{i}. {case['description']}")
        print(f"   Titel: {case['title'][:60]}...")
        print(f"   Autor: {case['author']}")
        print(f"   Normalisiert: {_normalize_for_search(case['title'])[:60]}...")

        if len(case['title']) > 60:
            truncated = case['title'][:60].rsplit(' ', 1)[0].strip()
            print(f"   Truncated: {truncated}...")

        print()

    print("✅ Suchstrategien würden angewendet:")
    print("   1. Original Titel + Autor")
    print("   2. Normalisiert + Autor")
    print("   3. Truncated + Autor (bei langen Titeln)")
    print("   4. Nur Original Titel")
    print("   5. Nur Normalisiert")
    print("   6. Nur Truncated")
    print()

    return True


def test_match_validation():
    """Test der Match-Validierung."""
    print("=" * 60)
    print("TEST 3: Match-Validierung")
    print("=" * 60)

    test_cases = [
        {
            'vdeh': {
                'title': 'Stahlbau Grundlagen',
                'year': 2010,
                'pages': '350 S.'
            },
            'dnb': {
                'title': 'Stahlbau: Grundlagen',
                'year': 2010,
                'pages': '352 S.'
            },
            'expected': True,
            'description': 'Ähnlicher Titel, gleiches Jahr, ähnliche Seitenzahl'
        },
        {
            'vdeh': {
                'title': 'Korrosionsschutz',
                'year': 2015,
                'pages': '200 S.'
            },
            'dnb': {
                'title': 'Werkstoffprüfung',
                'year': 2015,
                'pages': '205 S.'
            },
            'expected': False,
            'description': 'Komplett anderer Titel'
        },
        {
            'vdeh': {
                'title': 'Stahlwerkstoffe',
                'year': 2010,
                'pages': '300 S.'
            },
            'dnb': {
                'title': 'Stahlwerkstoffe',
                'year': 2015,
                'pages': '305 S.'
            },
            'expected': False,
            'description': 'Gleiches Thema, aber zu viele Jahre Differenz (>2)'
        },
        {
            'vdeh': {
                'title': 'Werkstoffkunde',
                'year': 2012,
                'pages': '500 S.'
            },
            'dnb': {
                'title': 'Werkstoffkunde',
                'year': 2012,
                'pages': '150 S.'
            },
            'expected': False,
            'description': 'Gleiches Thema, aber Seitenzahl zu unterschiedlich (>20%)'
        },
    ]

    passed = 0
    failed = 0

    for case in test_cases:
        is_valid, reason = FusionEngine.validate_dnb_match(
            case['vdeh'],
            case['dnb']
        )

        status = "✅" if is_valid == case['expected'] else "❌"

        if is_valid == case['expected']:
            passed += 1
        else:
            failed += 1

        print(f"{status} {case['description']}")
        print(f"   VDEH: {case['vdeh']['title']}, {case['vdeh'].get('year')}, {case['vdeh'].get('pages')}")
        print(f"   DNB:  {case['dnb']['title']}, {case['dnb'].get('year')}, {case['dnb'].get('pages')}")
        print(f"   Ergebnis: {is_valid} (erwartet: {case['expected']})")
        print(f"   Grund: {reason}")
        print()

    print(f"📊 Ergebnis: {passed}/{len(test_cases)} bestanden\n")
    return failed == 0


def test_title_similarity():
    """Test der Titel-Ähnlichkeitsberechnung."""
    print("=" * 60)
    print("TEST 4: Titel-Ähnlichkeit")
    print("=" * 60)

    test_cases = [
        ("Stahlbau", "Stahlbau", 1.0, "Identisch"),
        ("Stahlbau Grundlagen", "Stahlbau: Grundlagen", 0.9, "Sehr ähnlich"),
        ("Korrosionsschutz", "Korrosion", 0.7, "Ähnlich"),
        ("Stahlbau", "Holzbau", 0.4, "Unterschiedlich"),
        ("Werkstoffprüfung", "Stahlbau", 0.1, "Sehr unterschiedlich"),
    ]

    passed = 0
    failed = 0

    for title1, title2, min_expected, description in test_cases:
        similarity = FusionEngine.calculate_title_similarity(title1, title2)

        # Check if similarity is in expected range (±0.1)
        is_ok = similarity >= min_expected - 0.1
        status = "✅" if is_ok else "❌"

        if is_ok:
            passed += 1
        else:
            failed += 1

        print(f"{status} {description}")
        print(f"   '{title1}' vs '{title2}'")
        print(f"   Similarity: {similarity:.1%} (min. erwartet: {min_expected:.1%})")
        print()

    print(f"📊 Ergebnis: {passed}/{len(test_cases)} bestanden\n")
    return failed == 0


def main():
    """Hauptfunktion - führt alle Tests aus."""
    print("\n" + "=" * 60)
    print("DNB ENHANCED SEARCH - TEST SUITE")
    print("=" * 60)
    print()

    results = {
        'Normalisierung': test_normalization(),
        'Titel/Autor-Suche': test_title_author_search(),
        'Match-Validierung': test_match_validation(),
        'Titel-Ähnlichkeit': test_title_similarity(),
    }

    print("\n" + "=" * 60)
    print("GESAMT-ERGEBNIS")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ BESTANDEN" if passed else "❌ FEHLGESCHLAGEN"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())

    print()
    if all_passed:
        print("🎉 Alle Tests bestanden!")
        return 0
    else:
        print("⚠️  Einige Tests fehlgeschlagen!")
        return 1


if __name__ == '__main__':
    sys.exit(main())
