"""
Test der ISBN-Bereinigungsfunktion.

Prüft ob doppelte/konkatenierte ISBNs korrekt aufgespalten und bereinigt werden.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.marc21_parser import _format_isbn

print("=== Test: ISBN-Bereinigung ===\n")

test_cases = [
    # (Input, Expected Output, Description)
    ("35140035483540510400", "3-514-00354-8", "Double ISBN-10 (real example)"),
    ("35405159330387515933", "3-540-51593-3", "Double ISBN-10 (Springer)"),
    ("3540519432", "3-540-51943-2", "Single ISBN-10"),
    ("9783540519430", "978-3-540-51943-0", "Single ISBN-13"),
    ("97835405194309783540519430", "978-3-540-51943-0", "Double ISBN-13 (26 chars)"),
    ("35405194329783540519430", "3-540-51943-2", "Mixed ISBN-10+13 (23 chars)"),
    ("387011839", "387011839", "Too short - invalid (9 chars)"),
    ("3-540-51943-2", "3-540-51943-2", "Already formatted ISBN-10"),
]

print("Test-Fälle:\n")

passed = 0
failed = 0

for raw_isbn, expected, description in test_cases:
    result = _format_isbn(raw_isbn)
    status = "✓" if result == expected else "✗"

    if result == expected:
        passed += 1
    else:
        failed += 1

    print(f"{status} {description}")
    print(f"  Input:    {raw_isbn}")
    print(f"  Expected: {expected}")
    print(f"  Got:      {result}")

    if result != expected:
        print(f"  ❌ MISMATCH!")

    print()

print("=" * 60)
print(f"Ergebnis: {passed}/{len(test_cases)} Tests bestanden")

if failed == 0:
    print("✅ Alle Tests erfolgreich!")
else:
    print(f"❌ {failed} Tests fehlgeschlagen!")
    sys.exit(1)
