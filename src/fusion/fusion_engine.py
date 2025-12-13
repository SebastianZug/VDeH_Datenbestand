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
from difflib import SequenceMatcher

from .ollama_client import OllamaClient, OllamaUnavailableError
from .utils import compare_fields, format_record_for_display, calculate_pages_match

logger = logging.getLogger(__name__)


class FusionResult:
    """Container for fusion result data."""

    def __init__(
        self,
        title: Optional[str] = None,
        authors: Optional[str] = None,
        year: Optional[int] = None,
        publisher: Optional[str] = None,
        pages: Optional[str] = None,
        title_source: Optional[str] = None,
        authors_source: Optional[str] = None,
        year_source: Optional[str] = None,
        publisher_source: Optional[str] = None,
        pages_source: Optional[str] = None,
        conflicts: Optional[str] = None,
        confirmations: Optional[str] = None,
        ai_reasoning: Optional[str] = None,
        dnb_variant_selected: Optional[str] = None,
        dnb_match_rejected: bool = False,
        rejection_reason: Optional[str] = None,
        title_similarity_score: Optional[float] = None,
        pages_difference: Optional[float] = None,
    ):
        self.title = title
        self.authors = authors
        self.year = year
        self.publisher = publisher
        self.pages = pages
        self.title_source = title_source
        self.authors_source = authors_source
        self.year_source = year_source
        self.publisher_source = publisher_source
        self.pages_source = pages_source
        self.conflicts = conflicts
        self.confirmations = confirmations
        self.ai_reasoning = ai_reasoning
        self.dnb_variant_selected = dnb_variant_selected
        self.dnb_match_rejected = dnb_match_rejected
        self.rejection_reason = rejection_reason
        self.title_similarity_score = title_similarity_score
        self.pages_difference = pages_difference

    def to_dict(self) -> Dict:
        """Convert to dictionary for DataFrame storage."""
        return {
            'title': self.title,
            'authors': self.authors,
            'year': self.year,
            'publisher': self.publisher,
            'pages': self.pages,
            'title_source': self.title_source,
            'authors_source': self.authors_source,
            'year_source': self.year_source,
            'publisher_source': self.publisher_source,
            'pages_source': self.pages_source,
            'conflicts': self.conflicts,
            'confirmations': self.confirmations,
            'ai_reasoning': self.ai_reasoning,
            'dnb_variant_selected': self.dnb_variant_selected,
            'dnb_match_rejected': self.dnb_match_rejected,
            'rejection_reason': self.rejection_reason,
            'title_similarity_score': self.title_similarity_score,
            'pages_difference': self.pages_difference,
        }


class FusionEngine:
    """Engine for fusing VDEH and DNB bibliographic records."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        variant_priority: list = None,
        ty_similarity_threshold: float = 0.7,
    ):
        """
        Initialize fusion engine.

        Args:
            ollama_client: Configured OllamaClient instance
            variant_priority: Priority order for DNB variants (default: ["id", "title_author"])
            ty_similarity_threshold: Minimum title similarity for accepting TY matches (default: 0.7)
        """
        self.ollama = ollama_client
        self.variant_priority = variant_priority or ["id", "title_author"]
        self.ty_similarity_threshold = ty_similarity_threshold

    @staticmethod
    def calculate_title_similarity(title1: str, title2: str) -> float:
        """
        Calculate similarity between two titles using SequenceMatcher.

        Args:
            title1: First title string
            title2: Second title string

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not title1 or not title2:
            return 0.0

        # Normalize: lowercase and strip
        t1 = str(title1).lower().strip()
        t2 = str(title2).lower().strip()

        return SequenceMatcher(None, t1, t2).ratio()

    @staticmethod
    def validate_dnb_match(
        vdeh_data: Dict,
        dnb_data: Dict,
        min_title_similarity: float = 0.5,
        max_year_diff: int = 2,
        max_pages_diff: float = 0.2
    ) -> Tuple[bool, str]:
        """
        Validiert ob ein DNB-Match wirklich zum VDEH-Record passt.

        Prüft mehrere Kriterien um False Positives zu vermeiden:
        - Titel-Ähnlichkeit (SequenceMatcher)
        - Jahr-Differenz (±2 Jahre OK)
        - Seitenzahl-Differenz (<20% OK)

        Args:
            vdeh_data: VDEH record dictionary
            dnb_data: DNB record dictionary
            min_title_similarity: Minimum title similarity (0.0-1.0)
            max_year_diff: Maximum year difference in years
            max_pages_diff: Maximum pages difference (percentage)

        Returns:
            Tuple of (is_valid, reason)

        Example:
            >>> vdeh = {'title': 'Faust', 'year': 1808, 'pages': '368 S.'}
            >>> dnb = {'title': 'Faust I', 'year': 1808, 'pages': '370 S.'}
            >>> valid, reason = FusionEngine.validate_dnb_match(vdeh, dnb)
            >>> valid
            True
        """
        # Titel-Ähnlichkeit prüfen
        vdeh_title = vdeh_data.get('title')
        dnb_title = dnb_data.get('title')

        if not vdeh_title or not dnb_title:
            # Wenn Titel fehlt, kann nicht validiert werden → Akzeptieren
            return True, "Titel fehlt - keine Validierung möglich"

        title_sim = FusionEngine.calculate_title_similarity(vdeh_title, dnb_title)

        if title_sim < min_title_similarity:
            return False, f"Titel zu unterschiedlich (Similarity: {title_sim:.1%})"

        # Jahr prüfen (±max_year_diff Jahre OK)
        vdeh_year = vdeh_data.get('year')
        dnb_year = dnb_data.get('year')

        if vdeh_year and dnb_year:
            try:
                year_diff = abs(int(vdeh_year) - int(dnb_year))
                if year_diff > max_year_diff:
                    return False, f"Jahr zu weit weg ({year_diff} Jahre Differenz)"
            except (ValueError, TypeError):
                # Jahr nicht konvertierbar → Ignorieren
                pass

        # Seitenzahl prüfen (wenn beide vorhanden)
        vdeh_pages = vdeh_data.get('pages')
        dnb_pages = dnb_data.get('pages')

        if vdeh_pages and dnb_pages:
            pages_match, pages_diff = calculate_pages_match(vdeh_pages, dnb_pages)

            if pages_diff is not None and pages_diff > max_pages_diff:
                return False, f"Seitenzahl zu unterschiedlich ({pages_diff:.1%} Differenz)"

        # Alle Checks bestanden
        reasons = [f"Titel: {title_sim:.1%}"]

        if vdeh_year and dnb_year:
            reasons.append(f"Jahr: {vdeh_year} vs {dnb_year}")

        if vdeh_pages and dnb_pages:
            if pages_diff is not None:
                reasons.append(f"Pages: {pages_diff:.1%} diff")

        return True, ", ".join(reasons)

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
            'publisher': row.get('publisher'),
            'pages': row.get('pages')
        }

        # Extract DNB variants
        dnb_id = {
            'title': row.get('dnb_title'),
            'authors': row.get('dnb_authors'),
            'year': row.get('dnb_year'),
            'publisher': row.get('dnb_publisher'),
            'pages': row.get('dnb_pages')
        }

        dnb_ta = {
            'title': row.get('dnb_title_ta'),
            'authors': row.get('dnb_authors_ta'),
            'year': row.get('dnb_year_ta'),
            'publisher': row.get('dnb_publisher_ta'),
            'pages': row.get('dnb_pages_ta')
        }

        # Extract DNB Title/Year variant (NEW - Fallback for records without ISBN/ISSN/Authors)
        dnb_ty = {
            'title': row.get('dnb_title_ty'),
            'authors': row.get('dnb_authors_ty'),
            'year': row.get('dnb_year_ty'),
            'publisher': row.get('dnb_publisher_ty'),
            'pages': row.get('dnb_pages_ty')
        }

        # Check if variants are actually available
        id_available = any(pd.notna(dnb_id[f]) for f in dnb_id)
        ta_available = any(pd.notna(dnb_ta[f]) for f in dnb_ta)
        ty_available = any(pd.notna(dnb_ty[f]) for f in dnb_ty)

        if not id_available:
            dnb_id = None
        if not ta_available:
            dnb_ta = None
        if not ty_available:
            dnb_ty = None

        # Case 1: No DNB data available at all
        if dnb_id is None and dnb_ta is None and dnb_ty is None:
            return FusionResult(
                title=vdeh_data['title'],
                authors=vdeh_data['authors'],
                year=vdeh_data['year'],
                publisher=vdeh_data['publisher'],
                pages=vdeh_data['pages'],
                title_source='vdeh',
                authors_source='vdeh',
                year_source='vdeh',
                publisher_source='vdeh',
                pages_source='vdeh',
            )

        # Case 1.5: Only TY variant available - validate with similarity threshold + pages
        if dnb_id is None and dnb_ta is None and dnb_ty is not None:
            # Calculate title similarity
            vdeh_title = vdeh_data.get('title')
            dnb_ty_title = dnb_ty.get('title')
            similarity = self.calculate_title_similarity(vdeh_title, dnb_ty_title)

            # Check pages match (if both available)
            vdeh_pages = vdeh_data.get('pages')
            dnb_ty_pages = dnb_ty.get('pages')
            pages_match, pages_diff = calculate_pages_match(vdeh_pages, dnb_ty_pages)

            # Decision logic: Similarity + Pages
            accept_match = False
            reason = ""

            if similarity >= self.ty_similarity_threshold:
                # High similarity → Accept
                accept_match = True
                reason = f"Similarity: {similarity:.1%}"
            elif similarity >= 0.5 and pages_match:
                # Borderline similarity (50-70%) but pages match → Accept
                accept_match = True
                reason = f"Similarity: {similarity:.1%}, Pages-Match bestätigt ({vdeh_pages} ≈ {dnb_ty_pages})"
                logger.info(
                    f"TY borderline match rescued by pages: "
                    f"similarity={similarity:.1%}, pages={vdeh_pages} vs {dnb_ty_pages}"
                )
            else:
                # Low similarity and no pages confirmation → Reject
                reason = f"Similarity: {similarity:.1%}"
                if pages_diff is not None:
                    reason += f", Pages mismatch: {pages_diff:.1%} diff"

            # Reject if not accepted
            if not accept_match:
                logger.info(
                    f"TY match rejected: {reason} "
                    f"(VDEH: '{vdeh_title[:50] if vdeh_title else ''}...' vs DNB: '{dnb_ty_title[:50] if dnb_ty_title else ''}...')"
                )
                return FusionResult(
                    title=vdeh_data['title'],
                    authors=vdeh_data['authors'],
                    year=vdeh_data['year'],
                    publisher=vdeh_data['publisher'],
                    pages=vdeh_data['pages'],
                    title_source='vdeh',
                    authors_source='vdeh',
                    year_source='vdeh',
                    publisher_source='vdeh',
                    pages_source='vdeh',
                    dnb_match_rejected=True,
                    rejection_reason=f'TY-Match zu unsicher ({reason})',
                    title_similarity_score=similarity,
                    pages_difference=pages_diff,
                )

            # Accept TY match - use as gap-filling fallback
            logger.info(
                f"TY match accepted: {reason}"
            )

            result = FusionResult(
                dnb_variant_selected='title_year',
                ai_reasoning=f'TY-Variante als Fallback (kein ID/TA verfügbar, {reason})',
                title_similarity_score=similarity,
                pages_difference=pages_diff,
            )

            # Fill missing fields from TY variant
            for field in ['title', 'authors', 'year', 'publisher', 'pages']:
                v_val = vdeh_data[field]
                ty_val = dnb_ty.get(field) if dnb_ty else None

                if pd.notna(v_val):
                    # VDEH has value - keep it
                    setattr(result, field, v_val)
                    setattr(result, f'{field}_source', 'vdeh')
                elif pd.notna(ty_val):
                    # VDEH empty, TY has value - use TY
                    setattr(result, field, ty_val)
                    setattr(result, f'{field}_source', 'dnb_title_year')
                else:
                    # Both empty
                    setattr(result, field, None)
                    setattr(result, f'{field}_source', None)

            return result

        # Case 2: ID or TA (or both) available - use AI for selection
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
                pages=vdeh_data['pages'],
                title_source='vdeh',
                authors_source='vdeh',
                year_source='vdeh',
                publisher_source='vdeh',
                pages_source='vdeh',
                ai_reasoning=f"KI: {reason}",
                dnb_match_rejected=True,
                rejection_reason=reason,
            )

        # Case 4: AI selected a variant
        selected_variant = 'id' if choice == 'A' else 'title_author'
        selected_data = dnb_id if selected_variant == 'id' else dnb_ta

        # Validate DNB match (zusätzliche Sicherheit gegen False Positives)
        is_valid, validation_reason = self.validate_dnb_match(vdeh_data, selected_data)

        if not is_valid:
            # Match rejected by validation
            logger.warning(
                f"DNB {selected_variant} match rejected by validation: {validation_reason}"
            )
            return FusionResult(
                title=vdeh_data['title'],
                authors=vdeh_data['authors'],
                year=vdeh_data['year'],
                publisher=vdeh_data['publisher'],
                pages=vdeh_data['pages'],
                title_source='vdeh',
                authors_source='vdeh',
                year_source='vdeh',
                publisher_source='vdeh',
                pages_source='vdeh',
                ai_reasoning=f"KI wählte {selected_variant}, aber Validierung fehlgeschlagen",
                dnb_match_rejected=True,
                rejection_reason=f"Validierung: {validation_reason}",
            )

        # Compare fields to find conflicts and confirmations
        conflicts, confirmations = compare_fields(vdeh_data, selected_data)

        # Build result
        result = FusionResult(
            conflicts=json.dumps(conflicts, ensure_ascii=False) if conflicts else None,
            confirmations=json.dumps(confirmations, ensure_ascii=False) if confirmations else None,
            ai_reasoning=f"KI Entscheidung: Variante {selected_variant} gewählt. {reason}. Validierung: {validation_reason}",
            dnb_variant_selected=selected_variant,
        )

        # Assign values field by field
        for field in ['title', 'authors', 'year', 'publisher', 'pages']:
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
