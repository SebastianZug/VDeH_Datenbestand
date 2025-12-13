"""
Utility functions for data fusion operations.

Author: Bibliographic Data Analysis
Date: November 2025
"""

import re
import unicodedata
import pandas as pd
import logging
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)


def normalize_string(val) -> Optional[str]:
    """
    Normalize strings for robust bibliographic comparison.

    Handles common variations in bibliographic data:
    - Removes special marker characters (¬)
    - Normalizes separators (& vs und, - vs spaces)
    - Handles umlaut variants (oe/ö, ae/ä, ue/ü)
    - Collapses whitespace
    - Lowercase normalization

    Args:
        val: Value to normalize (can be None, str, or other)

    Returns:
        Normalized lowercase string, or None
    """
    if pd.isna(val):
        return None

    s = str(val).strip()

    # Remove special bibliographic marker characters
    s = s.replace('¬', '')

    # Normalize Unicode to composed form (NFC)
    s = unicodedata.normalize('NFC', s)

    # Convert to lowercase first for easier handling
    s = s.lower()

    # Normalize common separator variations
    s = s.replace(' & ', ' und ')
    s = s.replace('&', ' und ')

    # Normalize hyphens and dashes to spaces for year ranges
    s = re.sub(r'\s*[-–—]\s*', ' ', s)

    # Normalize umlaut variants (after lowercase)
    s = s.replace('oe', 'ö').replace('ae', 'ä').replace('ue', 'ü')
    s = s.replace('ss', 'ß')

    # Collapse multiple spaces
    s = re.sub(r'\s+', ' ', s).strip()

    # Remove trailing punctuation that doesn't affect meaning
    s = s.rstrip('.,:;')

    return s


def _normalize_publisher(val: str) -> str:
    """
    Normalize publisher names, removing location info and extra formatting.

    Examples:
        "Duncker & Humblot : Berlin (DE)" -> "duncker und humblot"
        "Springer-Verlag, Heidelberg" -> "springer verlag, heidelberg"
    """
    # Remove everything after colon (location separator)
    if ':' in val:
        val = val.split(':')[0]

    # Remove content in parentheses (country codes, etc.)
    val = re.sub(r'\([^)]*\)', '', val)

    return val.strip()


def compare_fields(base: Dict, other: Optional[Dict]) -> Tuple[Dict, Dict]:
    """
    Compare fields between two records and identify conflicts and confirmations.

    Uses intelligent field-specific normalization:
    - Publisher: Ignores location/country information
    - Title/Authors: Full bibliographic normalization
    - Year: Numeric comparison

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
            # Special handling for publisher field
            if field == 'publisher':
                bn = normalize_string(_normalize_publisher(str(b)))
                on = normalize_string(_normalize_publisher(str(o)))
            else:
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


def extract_page_number(pages_str: Optional[str]) -> Optional[int]:
    """
    Extract numeric page count from various page string formats.

    Handles common formats:
    - "188 S." → 188
    - "XV, 250 p." → 250 (ignores Roman numerals)
    - "192 pages" → 192
    - "A35, B21 S." → None (complex pagination)

    Args:
        pages_str: Page string from MARC21 field 300

    Returns:
        Integer page count or None if not parseable
    """
    if pd.isna(pages_str) or not pages_str:
        return None

    # Convert to string and normalize
    pages_str = str(pages_str).strip()

    # Pattern: Find largest number (ignoring Roman numerals at start)
    # Looks for digits followed by optional space and page indicator
    patterns = [
        r'(\d+)\s*(?:S\.|p\.|pages?|Seiten?)',  # "188 S.", "250 p."
        r'(\d+)\s*$',  # Just number at end
        r'(\d+)\s*[,:]',  # Number before comma/colon
    ]

    numbers = []
    for pattern in patterns:
        matches = re.findall(pattern, pages_str, re.IGNORECASE)
        numbers.extend([int(m) for m in matches])

    if not numbers:
        return None

    # Return largest number found (main pagination)
    return max(numbers)


def calculate_pages_match(pages1: Optional[str], pages2: Optional[str], tolerance: float = 0.1) -> Tuple[bool, Optional[float]]:
    """
    Check if two page counts match within tolerance.

    Args:
        pages1: First page string
        pages2: Second page string
        tolerance: Allowed relative difference (default: 0.1 = 10%)

    Returns:
        Tuple of (matches: bool, difference_percent: Optional[float])
    """
    num1 = extract_page_number(pages1)
    num2 = extract_page_number(pages2)

    # If either is missing, we can't validate
    if num1 is None or num2 is None:
        return (False, None)

    # Calculate relative difference
    diff = abs(num1 - num2)
    avg = (num1 + num2) / 2
    diff_percent = diff / avg if avg > 0 else 1.0

    matches = diff_percent <= tolerance

    logger.debug(
        f"Pages match check: {pages1} ({num1}) vs {pages2} ({num2}) "
        f"→ diff={diff_percent:.1%}, match={matches}"
    )

    return (matches, diff_percent)
