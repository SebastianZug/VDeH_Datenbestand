"""
Core fusion engine for merging VDEH and DNB bibliographic data.

Author: Bibliographic Data Analysis
Date: November 2025
"""

import json
import logging
import pandas as pd
from typing import Dict, Optional, Tuple
from pathlib import Path

from .ollama_client import OllamaClient, OllamaUnavailableError
from .utils import compare_fields, format_record_for_display

logger = logging.getLogger(__name__)


class FusionResult:
    """Container for fusion result data."""

    def __init__(
        self,
        title: Optional[str] = None,
        authors: Optional[str] = None,
        year: Optional[int] = None,
        publisher: Optional[str] = None,
        title_source: Optional[str] = None,
        authors_source: Optional[str] = None,
        year_source: Optional[str] = None,
        publisher_source: Optional[str] = None,
        conflicts: Optional[str] = None,
        confirmations: Optional[str] = None,
        ai_reasoning: Optional[str] = None,
        dnb_variant_selected: Optional[str] = None,
        dnb_match_rejected: bool = False,
        rejection_reason: Optional[str] = None,
    ):
        self.title = title
        self.authors = authors
        self.year = year
        self.publisher = publisher
        self.title_source = title_source
        self.authors_source = authors_source
        self.year_source = year_source
        self.publisher_source = publisher_source
        self.conflicts = conflicts
        self.confirmations = confirmations
        self.ai_reasoning = ai_reasoning
        self.dnb_variant_selected = dnb_variant_selected
        self.dnb_match_rejected = dnb_match_rejected
        self.rejection_reason = rejection_reason

    def to_dict(self) -> Dict:
        """Convert to dictionary for DataFrame storage."""
        return {
            'title': self.title,
            'authors': self.authors,
            'year': self.year,
            'publisher': self.publisher,
            'title_source': self.title_source,
            'authors_source': self.authors_source,
            'year_source': self.year_source,
            'publisher_source': self.publisher_source,
            'conflicts': self.conflicts,
            'confirmations': self.confirmations,
            'ai_reasoning': self.ai_reasoning,
            'dnb_variant_selected': self.dnb_variant_selected,
            'dnb_match_rejected': self.dnb_match_rejected,
            'rejection_reason': self.rejection_reason,
        }


class FusionEngine:
    """Engine for fusing VDEH and DNB bibliographic records."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        variant_priority: list = None,
    ):
        """
        Initialize fusion engine.

        Args:
            ollama_client: Configured OllamaClient instance
            variant_priority: Priority order for DNB variants (default: ["id", "title_author"])
        """
        self.ollama = ollama_client
        self.variant_priority = variant_priority or ["id", "title_author"]

    def build_ai_prompt(
        self,
        vdeh: Dict,
        dnb_id: Optional[Dict],
        dnb_ta: Optional[Dict]
    ) -> str:
        """
        Build AI prompt for variant selection.

        Args:
            vdeh: VDEH record dictionary
            dnb_id: DNB ID-based variant dictionary (or None)
            dnb_ta: DNB title/author-based variant dictionary (or None)

        Returns:
            Formatted prompt string
        """
        return f"""Du bist ein erfahrener Bibliothekar. Prüfe welche DNB-Variante am besten zu VDEH passt oder ob keine passt.

REGELN:
1. ENTSCHEIDUNGSKRITERIEN: Titel + Autoren dominieren. Jahr ±2 oder fehlend ist OK. Verlag tolerant.
2. SCHREIBWEISEN: Ignoriere Groß-/Kleinschreibung, geringfügige Varianten, Abkürzungen.
3. WENN BEIDE passen: bevorzuge ID-basierte Variante (ISBN/ISSN) gegenüber Titel/Autor.
4. WENN NUR EINE passt: wähle diese.
5. WENN KEINE passt: entscheide NEIN.
6. EIN 'NEIN' nur bei klar unterschiedlichen Werken (Titel UND Autoren deutlich verschieden).
7. Fehlende Felder alleine NIE als Ablehnungsgrund.

DATENSATZ VDEH:
{format_record_for_display(vdeh)}

DNB-VARIANTE A (ID-basiert):
{format_record_for_display(dnb_id)}

DNB-VARIANTE B (Titel/Autor-basiert):
{format_record_for_display(dnb_ta)}

Antworte NUR mit einem dieser Formate:
A - [Begründung]
B - [Begründung]
KEINE - [Begründung warum keine passt]
A&B - [Begründung warum beide gleich gut sind, ID bevorzugt]"""

    def parse_ai_choice(self, response: Optional[str]) -> Tuple[str, str]:
        """
        Parse AI response to extract variant choice.

        Args:
            response: AI response string

        Returns:
            Tuple of (choice, reason) where choice is 'A', 'B', or 'KEINE'
        """
        if not response:
            return 'KEINE', 'KI keine Antwort'

        r = response.strip().upper()

        if r.startswith('A&B'):
            reason = response.split('-', 1)[1].strip() if '-' in response else ''
            return 'A', f"Beide passend, ID bevorzugt. {reason}"

        if r.startswith('A ') or r.startswith('A-') or r.startswith('A\n') or r == 'A':
            reason = response.split('-', 1)[1].strip() if '-' in response else ''
            return 'A', reason

        if r.startswith('B ') or r.startswith('B-') or r.startswith('B\n') or r == 'B':
            reason = response.split('-', 1)[1].strip() if '-' in response else ''
            return 'B', reason

        if r.startswith('KEINE') or r.startswith('KEIN'):
            reason = response.split('-', 1)[1].strip() if '-' in response else ''
            return 'KEINE', reason if reason else 'Keine Variante passt'

        # Fallback: unclear response
        return 'KEINE', f"Unklare KI-Antwort: {response}"

    def merge_record(self, row: pd.Series) -> FusionResult:
        """
        Merge a single record with AI-based variant selection.

        Args:
            row: Pandas Series containing record data

        Returns:
            FusionResult object

        Raises:
            OllamaUnavailableError: If Ollama is unavailable after retries
        """
        # Extract VDEH data
        vdeh_data = {
            'title': row.get('title'),
            'authors': row.get('authors_str'),
            'year': row.get('year'),
            'publisher': row.get('publisher')
        }

        # Extract DNB variants
        dnb_id = {
            'title': row.get('dnb_title'),
            'authors': row.get('dnb_authors'),
            'year': row.get('dnb_year'),
            'publisher': row.get('dnb_publisher')
        }

        dnb_ta = {
            'title': row.get('dnb_title_ta'),
            'authors': row.get('dnb_authors_ta'),
            'year': row.get('dnb_year_ta'),
            'publisher': row.get('dnb_publisher_ta')
        }

        # Check if variants are actually available
        id_available = any(pd.notna(dnb_id[f]) for f in dnb_id)
        ta_available = any(pd.notna(dnb_ta[f]) for f in dnb_ta)

        if not id_available:
            dnb_id = None
        if not ta_available:
            dnb_ta = None

        # Case 1: No DNB data available
        if dnb_id is None and dnb_ta is None:
            return FusionResult(
                title=vdeh_data['title'],
                authors=vdeh_data['authors'],
                year=vdeh_data['year'],
                publisher=vdeh_data['publisher'],
                title_source='vdeh',
                authors_source='vdeh',
                year_source='vdeh',
                publisher_source='vdeh',
            )

        # Case 2: DNB data available - use AI for selection
        ai_response = self.ollama.query(
            self.build_ai_prompt(vdeh_data, dnb_id, dnb_ta)
        )
        choice, reason = self.parse_ai_choice(ai_response)

        # Case 3: AI rejects both variants
        if choice == 'KEINE':
            return FusionResult(
                title=vdeh_data['title'],
                authors=vdeh_data['authors'],
                year=vdeh_data['year'],
                publisher=vdeh_data['publisher'],
                title_source='vdeh',
                authors_source='vdeh',
                year_source='vdeh',
                publisher_source='vdeh',
                ai_reasoning=f"KI: {reason}",
                dnb_match_rejected=True,
                rejection_reason=reason,
            )

        # Case 4: AI selected a variant
        selected_variant = 'id' if choice == 'A' else 'title_author'
        selected_data = dnb_id if selected_variant == 'id' else dnb_ta

        # Compare fields to find conflicts and confirmations
        conflicts, confirmations = compare_fields(vdeh_data, selected_data)

        # Build result
        result = FusionResult(
            conflicts=json.dumps(conflicts, ensure_ascii=False) if conflicts else None,
            confirmations=json.dumps(confirmations, ensure_ascii=False) if confirmations else None,
            ai_reasoning=f"KI Entscheidung: Variante {selected_variant} gewählt. {reason}",
            dnb_variant_selected=selected_variant,
        )

        # Assign values field by field
        for field in ['title', 'authors', 'year', 'publisher']:
            v_val = vdeh_data[field]
            d_val = selected_data.get(field) if selected_data else None

            if pd.notna(d_val):
                setattr(result, field, d_val)
                source = 'confirmed' if field in confirmations else f'dnb_{selected_variant}'
                setattr(result, f'{field}_source', source)
            elif pd.notna(v_val):
                setattr(result, field, v_val)
                setattr(result, f'{field}_source', 'vdeh')
            else:
                setattr(result, field, None)
                setattr(result, f'{field}_source', None)

        return result
