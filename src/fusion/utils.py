"""
Utility functions for data fusion operations.

Author: Bibliographic Data Analysis
Date: November 2025
"""

import re
import unicodedata
import pandas as pd
from typing import Optional, Dict, Tuple


def normalize_string(val) -> Optional[str]:
    """
    Normalize strings for robust comparison.

    Args:
        val: Value to normalize (can be None, str, or other)

    Returns:
        Normalized lowercase string with collapsed whitespace, or None
    """
    if pd.isna(val):
        return None
    s = str(val).strip()
    s = re.sub(r'\s+', ' ', s)
    s = unicodedata.normalize('NFKC', s)
    return s.lower()


def compare_fields(base: Dict, other: Optional[Dict]) -> Tuple[Dict, Dict]:
    """
    Compare fields between two records and identify conflicts and confirmations.

    Args:
        base: Base record dictionary with keys: title, authors, year, publisher
        other: Other record dictionary (or None)

    Returns:
        Tuple of (conflicts_dict, confirmations_dict)
        - conflicts: {field: {base: value, other: value}}
        - confirmations: {field: value}
    """
    conflicts = {}
    confirmations = {}

    for field in ['title', 'authors', 'year', 'publisher']:
        b = base.get(field)
        o = other.get(field) if other else None

        if pd.notna(b) and pd.notna(o):
            bn = normalize_string(b)
            on = normalize_string(o)

            if bn == on:
                confirmations[field] = str(b)
            else:
                conflicts[field] = {'vdeh': str(b), 'dnb': str(o)}

    return conflicts, confirmations


def format_record_for_display(entry: Optional[Dict]) -> str:
    """
    Format a record dictionary for display in prompts or logs.

    Args:
        entry: Record dictionary or None

    Returns:
        Formatted multi-line string
    """
    if entry is None:
        entry = {'title': None, 'authors': None, 'year': None, 'publisher': None}

    return (
        f"- Titel: {entry['title'] if pd.notna(entry['title']) else 'nicht vorhanden'}\n"
        f"- Autoren: {entry['authors'] if pd.notna(entry['authors']) else 'nicht vorhanden'}\n"
        f"- Jahr: {entry['year'] if pd.notna(entry['year']) else 'nicht vorhanden'}\n"
        f"- Verlag: {entry['publisher'] if pd.notna(entry['publisher']) else 'nicht vorhanden'}"
    )
