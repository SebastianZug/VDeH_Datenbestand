#!/usr/bin/env python3
"""Extend fusion engine to support Title/Year (TY) as third DNB variant."""

# This is a summary of changes needed - we'll implement them manually

print("=== FUSION ENGINE EXTENSION PLAN ===\n")

print("📋 Changes needed to support Title/Year variant:\n")

print("1. fusion_engine.py:")
print("   - Update variant_priority default: ['id', 'title_author'] → ['id', 'title_author', 'title_year']")
print("   - Update build_ai_prompt() to accept dnb_ty parameter")
print("   - Update AI prompt to mention 3 variants (A=ID, B=TA, C=TY)")
print("   - Update parse_ai_choice() to handle 'C' responses")
print("   - Update merge_record() to extract dnb_ty data")
print("   - Update variant selection logic to handle 3-way choice\n")

print("2. Since fusion engine is complex, we should:")
print("   a) Keep it as 2-variant for now (ID vs TA)")
print("   b) TY variant acts as FALLBACK - only used when ID and TA both empty")
print("   c) This avoids needing to update AI prompts and 3-way logic\n")

print("3. Simplified approach:")
print("   - In merge_record(), check if ID and TA are both None")
print("   - If both None but TY exists, use TY directly (no AI needed)")
print("   - Mark source as 'dnb_title_year'")
print("   - This gives us TY enrichment without complex AI changes\n")

print("✅ This is the pragmatic solution:")
print("   - Minimal code changes")
print("   - TY fills gaps that ID/TA can't reach")
print("   - No need to train AI on 3-way choices")
print("   - Can be enhanced later if needed\n")

print("Proceeding with minimal implementation...")
