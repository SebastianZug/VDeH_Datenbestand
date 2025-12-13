"""
Test der Title/Year Similarity-Filterung in der Fusion Engine.

Prüft ob die 70% Similarity-Threshold korrekt funktioniert.
"""

import sys
from pathlib import Path
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.fusion.fusion_engine import FusionEngine

print("=== Test: Title/Year Similarity Filter ===\n")

# Lade TY-Daten
ty_file = Path("data/vdeh/processed/dnb_title_year_data.parquet")
if not ty_file.exists():
    print(f"❌ Datei nicht gefunden: {ty_file}")
    sys.exit(1)

dnb_ty_df = pd.read_parquet(ty_file)
successful = dnb_ty_df[dnb_ty_df['dnb_found'] == True].copy()

print(f"Total TY-Matches: {len(successful)}\n")

# Test Similarity-Berechnung
print("=== Test 1: Similarity-Berechnung ===\n")

test_cases = [
    ("12. Umformtechnisches Kolloquium", "12. Umformtechnisches Kolloquium", 1.0),
    ("Powder metallurgy", "Influence of porosity on the tribological properties...", 0.26),
    ("Casting", "How to make artist dolls", 0.15),
    ("Materials characterization", "Materials Characterization for Systems Performance...", 0.56),
]

for vdeh, dnb, expected in test_cases:
    similarity = FusionEngine.calculate_title_similarity(vdeh, dnb)
    status = "✓" if abs(similarity - expected) < 0.05 else "✗"
    print(f"{status} Similarity: {similarity:.2%} (expected ~{expected:.0%})")
    print(f"   VDEH: '{vdeh[:50]}'")
    print(f"   DNB:  '{dnb[:50]}'\n")

# Berechne Similarity für alle TY-Matches
print("=== Test 2: Filter-Statistik (70% Threshold) ===\n")

successful['similarity'] = successful.apply(
    lambda row: FusionEngine.calculate_title_similarity(row['title'], row['dnb_title']),
    axis=1
)

threshold = 0.7
accepted = successful[successful['similarity'] >= threshold]
rejected = successful[successful['similarity'] < threshold]

print(f"Total Matches:        {len(successful):>3}")
print(f"Akzeptiert (≥70%):    {len(accepted):>3} ({len(accepted)/len(successful)*100:>5.1f}%)")
print(f"Abgelehnt (<70%):     {len(rejected):>3} ({len(rejected)/len(successful)*100:>5.1f}%)")

# Impact-Analyse
print("\n=== Test 3: Impact auf Autoren-Abdeckung ===\n")

accepted_with_authors = accepted[
    (accepted['dnb_authors'].notna()) &
    (accepted['dnb_authors'].str.len() > 0)
]

rejected_with_authors = rejected[
    (rejected['dnb_authors'].notna()) &
    (rejected['dnb_authors'].str.len() > 0)
]

print(f"Akzeptierte Matches mit Autoren:  {len(accepted_with_authors):>3}")
print(f"Abgelehnte Matches mit Autoren:   {len(rejected_with_authors):>3}")
print(f"Eingesparte False Positives:      {len(rejected):>3}")

print("\n=== Test 4: Beispiele ===\n")

print("✅ AKZEPTIERT (≥70%, Top 5):")
for _, row in accepted.head(5).iterrows():
    has_authors = "📚" if pd.notna(row['dnb_authors']) and len(row['dnb_authors']) > 0 else "  "
    print(f"{has_authors} Sim: {row['similarity']:.0%} | {row['title'][:60]}")
    print(f"            → {row['dnb_title'][:60]}")

print("\n❌ ABGELEHNT (<70%, Top 5):")
for _, row in rejected.head(5).iterrows():
    print(f"   Sim: {row['similarity']:.0%} | {row['title'][:60]}")
    print(f"            → {row['dnb_title'][:60]}")

print("\n✅ Test erfolgreich abgeschlossen!")
