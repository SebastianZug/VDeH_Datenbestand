"""
Test der Pages-Validierung für TY-Matches.

Prüft:
1. extract_page_number() - Parsing verschiedener Seitenzahl-Formate
2. calculate_pages_match() - Pages-Match mit Toleranz
3. TY-Validierung - Borderline-Rescue durch Pages-Match
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.fusion.utils import extract_page_number, calculate_pages_match

print("=" * 70)
print("TEST 1: extract_page_number() - Verschiedene Seitenzahl-Formate")
print("=" * 70)
print()

test_cases_extract = [
    # (Input, Expected Output, Description)
    ("188 S.", 188, "Standard MARC21 deutsch"),
    ("XV, 250 p.", 250, "Mit römischen Zahlen + p."),
    ("192 pages", 192, "Englisch 'pages'"),
    ("250 Seiten", 250, "Deutsch 'Seiten'"),
    ("A35, B21 S.", 35, "Komplexe Pagination (größte Zahl)"),
    ("123", 123, "Nur Zahl"),
    ("50, 30 S.", 50, "Mehrere Zahlen (größte)"),
    ("", None, "Leerer String"),
    (None, None, "None"),
    ("keine Seitenzahl", None, "Keine Zahl enthalten"),
]

passed_extract = 0
failed_extract = 0

for pages_str, expected, description in test_cases_extract:
    result = extract_page_number(pages_str)
    status = "✓" if result == expected else "✗"

    if result == expected:
        passed_extract += 1
    else:
        failed_extract += 1

    print(f"{status} {description}")
    print(f"  Input:    '{pages_str}'")
    print(f"  Expected: {expected}")
    print(f"  Got:      {result}")

    if result != expected:
        print(f"  ❌ MISMATCH!")

    print()

print("=" * 70)
print(f"TEST 1 Ergebnis: {passed_extract}/{len(test_cases_extract)} Tests bestanden")
print("=" * 70)
print()

# ============================================================================
# TEST 2: calculate_pages_match()
# ============================================================================

print("=" * 70)
print("TEST 2: calculate_pages_match() - Pages-Match mit Toleranz")
print("=" * 70)
print()

test_cases_match = [
    # (pages1, pages2, expected_match, description)
    ("188 S.", "192 p.", True, "Ähnliche Seitenzahlen (188 vs 192, 2.1% diff)"),
    ("250 S.", "250 pages", True, "Identisch (250 vs 250)"),
    ("100 S.", "150 p.", False, "Zu unterschiedlich (100 vs 150, 40% diff)"),
    ("188 S.", "200 p.", True, "Grenzfall akzeptabel (188 vs 200, 6.2% diff)"),
    ("50 S.", "60 p.", False, "Kleine Zahlen, 18% diff (zu groß)"),
    ("", "188 p.", False, "Fehlende Seitenzahl VDEH"),
    ("188 S.", "", False, "Fehlende Seitenzahl DNB"),
    ("", "", False, "Beide fehlend"),
    ("188 S.", "189 p.", True, "Minimaler Unterschied (0.5%)"),
]

passed_match = 0
failed_match = 0

for pages1, pages2, expected_match, description in test_cases_match:
    match, diff = calculate_pages_match(pages1, pages2, tolerance=0.1)
    status = "✓" if match == expected_match else "✗"

    if match == expected_match:
        passed_match += 1
    else:
        failed_match += 1

    print(f"{status} {description}")
    print(f"  Pages 1:  '{pages1}'")
    print(f"  Pages 2:  '{pages2}'")
    print(f"  Expected: {expected_match}")
    diff_str = f"{diff:.1%}" if diff is not None else "N/A"
    print(f"  Got:      {match} (diff: {diff_str})")

    if match != expected_match:
        print(f"  ❌ MISMATCH!")

    print()

print("=" * 70)
print(f"TEST 2 Ergebnis: {passed_match}/{len(test_cases_match)} Tests bestanden")
print("=" * 70)
print()

# ============================================================================
# TEST 3: TY-Validierung Logik (simuliert)
# ============================================================================

print("=" * 70)
print("TEST 3: TY-Validierung - Borderline-Rescue durch Pages-Match")
print("=" * 70)
print()

def simulate_ty_validation(similarity, pages1, pages2, threshold=0.7):
    """Simuliert die TY-Validierungslogik."""
    pages_match, pages_diff = calculate_pages_match(pages1, pages2)

    if similarity >= threshold:
        return True, f"Similarity: {similarity:.1%}"
    elif similarity >= 0.5 and pages_match:
        return True, f"Similarity: {similarity:.1%}, Pages-Match bestätigt ({pages1} ≈ {pages2})"
    else:
        reason = f"Similarity: {similarity:.1%}"
        if pages_diff is not None:
            reason += f", Pages mismatch: {pages_diff:.1%} diff"
        return False, reason

test_cases_validation = [
    # (similarity, pages1, pages2, expected_accept, description)
    (0.85, "188 S.", "192 p.", True, "Hohe Similarity → Accept"),
    (0.65, "188 S.", "192 p.", True, "Borderline + Pages-Match → Rescue!"),
    (0.65, "100 S.", "200 p.", False, "Borderline + Pages-Mismatch → Reject"),
    (0.45, "188 S.", "192 p.", False, "Zu niedrige Similarity (< 50%)"),
    (0.55, "", "192 p.", False, "Borderline, aber Pages fehlen → Reject"),
    (0.72, "188 S.", "192 p.", True, "Über Threshold → Accept"),
    (0.68, "250 S.", "250 p.", True, "Borderline + Perfect Pages → Rescue!"),
]

passed_validation = 0
failed_validation = 0

for similarity, pages1, pages2, expected, description in test_cases_validation:
    accept, reason = simulate_ty_validation(similarity, pages1, pages2)
    status = "✓" if accept == expected else "✗"

    if accept == expected:
        passed_validation += 1
    else:
        failed_validation += 1

    print(f"{status} {description}")
    print(f"  Similarity: {similarity:.1%}")
    print(f"  Pages 1:    '{pages1}'")
    print(f"  Pages 2:    '{pages2}'")
    print(f"  Expected:   {'Accept' if expected else 'Reject'}")
    print(f"  Got:        {'Accept' if accept else 'Reject'}")
    print(f"  Reason:     {reason}")

    if accept != expected:
        print(f"  ❌ MISMATCH!")

    print()

print("=" * 70)
print(f"TEST 3 Ergebnis: {passed_validation}/{len(test_cases_validation)} Tests bestanden")
print("=" * 70)
print()

# ============================================================================
# GESAMTERGEBNIS
# ============================================================================

total_passed = passed_extract + passed_match + passed_validation
total_tests = len(test_cases_extract) + len(test_cases_match) + len(test_cases_validation)
total_failed = failed_extract + failed_match + failed_validation

print("=" * 70)
print("GESAMTERGEBNIS")
print("=" * 70)
print(f"Test 1 (extract_page_number):  {passed_extract}/{len(test_cases_extract)} bestanden")
print(f"Test 2 (calculate_pages_match): {passed_match}/{len(test_cases_match)} bestanden")
print(f"Test 3 (TY-Validierung):        {passed_validation}/{len(test_cases_validation)} bestanden")
print("-" * 70)
print(f"GESAMT: {total_passed}/{total_tests} Tests bestanden")
print("=" * 70)

if total_failed == 0:
    print("✅ Alle Tests erfolgreich!")
    sys.exit(0)
else:
    print(f"❌ {total_failed} Tests fehlgeschlagen!")
    sys.exit(1)
