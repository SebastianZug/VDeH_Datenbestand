"""
Core fusion engine for merging VDEh, DNB and LoC bibliographic data.

Author: Bibliographic Data Analysis
Date: December 2025
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
    """Container for fusion result data with enhanced tracking."""

    def __init__(
        self,
        title: Optional[str] = None,
        authors: Optional[str] = None,
        year: Optional[int] = None,
        publisher: Optional[str] = None,
        pages: Optional[str] = None,
        isbn: Optional[str] = None,
        issn: Optional[str] = None,
        title_source: Optional[str] = None,
        authors_source: Optional[str] = None,
        year_source: Optional[str] = None,
        publisher_source: Optional[str] = None,
        pages_source: Optional[str] = None,
        isbn_source: Optional[str] = None,
        issn_source: Optional[str] = None,
        conflicts: Optional[str] = None,
        confirmations: Optional[str] = None,
        ai_reasoning: Optional[str] = None,
        dnb_variant_selected: Optional[str] = None,
        dnb_match_rejected: bool = False,
        rejection_reason: Optional[str] = None,
        title_similarity_score: Optional[float] = None,
        pages_difference: Optional[float] = None,
        # New enhanced tracking fields
        fusion_trigger_reason: Optional[str] = None,
        fusion_variants_available: Optional[str] = None,
        fusion_conflicts_detected: Optional[str] = None,
        fusion_validation_metrics: Optional[str] = None,
        fusion_selected_variant: Optional[str] = None,
        loc_match_rejected: bool = False,
    ):
        self.title = title
        self.authors = authors
        self.year = year
        self.publisher = publisher
        self.pages = pages
        self.isbn = isbn
        self.issn = issn
        self.title_source = title_source
        self.authors_source = authors_source
        self.year_source = year_source
        self.publisher_source = publisher_source
        self.pages_source = pages_source
        self.isbn_source = isbn_source
        self.issn_source = issn_source
        self.conflicts = conflicts
        self.confirmations = confirmations
        self.ai_reasoning = ai_reasoning
        self.dnb_variant_selected = dnb_variant_selected
        self.dnb_match_rejected = dnb_match_rejected
        self.rejection_reason = rejection_reason
        self.title_similarity_score = title_similarity_score
        self.pages_difference = pages_difference
        # New enhanced tracking fields
        self.fusion_trigger_reason = fusion_trigger_reason
        self.fusion_variants_available = fusion_variants_available
        self.fusion_conflicts_detected = fusion_conflicts_detected
        self.fusion_validation_metrics = fusion_validation_metrics
        self.fusion_selected_variant = fusion_selected_variant
        self.loc_match_rejected = loc_match_rejected

    def to_dict(self) -> Dict:
        """Convert to dictionary for DataFrame storage."""
        return {
            'title': self.title,
            'authors': self.authors,
            'year': self.year,
            'publisher': self.publisher,
            'pages': self.pages,
            'isbn': self.isbn,
            'issn': self.issn,
            'title_source': self.title_source,
            'authors_source': self.authors_source,
            'year_source': self.year_source,
            'publisher_source': self.publisher_source,
            'pages_source': self.pages_source,
            'isbn_source': self.isbn_source,
            'issn_source': self.issn_source,
            'conflicts': self.conflicts,
            'confirmations': self.confirmations,
            'ai_reasoning': self.ai_reasoning,
            'dnb_variant_selected': self.dnb_variant_selected,
            'dnb_match_rejected': self.dnb_match_rejected,
            'rejection_reason': self.rejection_reason,
            'title_similarity_score': self.title_similarity_score,
            'pages_difference': self.pages_difference,
            # New enhanced tracking fields
            'fusion_trigger_reason': self.fusion_trigger_reason,
            'fusion_variants_available': self.fusion_variants_available,
            'fusion_conflicts_detected': self.fusion_conflicts_detected,
            'fusion_validation_metrics': self.fusion_validation_metrics,
            'fusion_selected_variant': self.fusion_selected_variant,
            'loc_match_rejected': self.loc_match_rejected,
        }


class FusionEngine:
    """Engine for fusing VDEh, DNB and LoC bibliographic records."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        variant_priority: list = None,
        ty_similarity_threshold: float = 0.7,
        enable_loc: bool = True,
    ):
        """
        Initialize fusion engine.

        Args:
            ollama_client: Configured OllamaClient instance
            variant_priority: Priority order for DNB variants (default: ["id", "title_author"])
            ty_similarity_threshold: Minimum title similarity for accepting TY matches (default: 0.7)
            enable_loc: Enable Library of Congress data fusion (default: True)
        """
        self.ollama = ollama_client
        self.variant_priority = variant_priority or ["id", "title_author"]
        self.ty_similarity_threshold = ty_similarity_threshold
        self.enable_loc = enable_loc

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
        Validiert ob ein DNB-Match wirklich zum VDEh-Record passt.

        Prüft mehrere Kriterien um False Positives zu vermeiden:
        - Titel-Ähnlichkeit (SequenceMatcher)
        - Jahr-Differenz (±2 Jahre OK)
        - Seitenzahl-Differenz (<20% OK)

        Args:
            vdeh_data: VDEh record dictionary
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

        if pd.notna(vdeh_year) and pd.notna(dnb_year):
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

        if pd.notna(vdeh_year) and pd.notna(dnb_year):
            reasons.append(f"Jahr: {vdeh_year} vs {dnb_year}")

        if pd.notna(vdeh_pages) and pd.notna(dnb_pages):
            if pages_diff is not None:
                reasons.append(f"Pages: {pages_diff:.1%} diff")

        return True, ", ".join(reasons)

    def build_ai_prompt(
        self,
        vdeh: Dict,
        dnb_id: Optional[Dict],
        dnb_ta: Optional[Dict],
        dnb_ty: Optional[Dict] = None,
        loc_id: Optional[Dict] = None,
        loc_ta: Optional[Dict] = None,
        loc_ty: Optional[Dict] = None,
        language: Optional[str] = None
    ) -> str:
        """
        Build AI prompt for 6-variant selection (DNB: ID/TA/TY, LoC: ID/TA/TY).

        Args:
            vdeh: VDEh record dictionary
            dnb_id: DNB ID-based variant dictionary (or None)
            dnb_ta: DNB title/author-based variant dictionary (or None)
            dnb_ty: DNB title/year-based variant dictionary (or None)
            loc_id: LoC ID-based variant dictionary (or None)
            loc_ta: LoC title/author-based variant dictionary (or None)
            loc_ty: LoC title/year-based variant dictionary (or None)
            language: Detected language for prioritization (or None)

        Returns:
            Formatted prompt string
        """
        # Build prompt based on available data sources
        has_loc = loc_id is not None or loc_ta is not None or loc_ty is not None
        has_ty = dnb_ty is not None or loc_ty is not None

        if not has_loc:
            # Original DNB-only prompt
            return f"""Du bist ein erfahrener Bibliothekar. Prüfe welche DNB-Variante am besten zu VDEh passt oder ob keine passt.

REGELN:
1. ENTSCHEIDUNGSKRITERIEN: Titel + Autoren dominieren. Jahr ±2 oder fehlend ist OK. Verlag tolerant.
2. SCHREIBWEISEN: Ignoriere Groß-/Kleinschreibung, geringfügige Varianten, Abkürzungen.
3. WENN BEIDE passen: bevorzuge ID-basierte Variante (ISBN/ISSN) gegenüber Titel/Autor.
4. WENN NUR EINE passt: wähle diese.
5. WENN KEINE passt: entscheide NEIN.
6. EIN 'NEIN' nur bei klar unterschiedlichen Werken (Titel UND Autoren deutlich verschieden).
7. Fehlende Felder alleine NIE als Ablehnungsgrund.

DATENSATZ VDEh:
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
        else:
            # Extended prompt with DNB + LoC (up to 6 variants: A-F)
            prompt = f"""Du bist ein erfahrener Bibliothekar. Prüfe welche Variante am besten zu VDEh passt oder ob keine passt.

REGELN:
1. ENTSCHEIDUNGSKRITERIEN: Titel + Autoren dominieren. Jahr ±2 oder fehlend ist OK. Verlag tolerant.
2. SCHREIBWEISEN: Ignoriere Groß-/Kleinschreibung, geringfügige Varianten, Abkürzungen.
3. PRIORITÄT: DNB für deutschsprachige Werke (de/ger), LoC für englischsprachige Werke (en/eng).
4. VARIANTEN-QUALITÄT: ID (ISBN/ISSN) > Titel/Autor > Titel/Jahr
5. WENN NUR EINE passt: wähle diese.
6. WENN KEINE passt: entscheide KEINE.
7. EIN 'KEINE' nur bei klar unterschiedlichen Werken (Titel UND Autoren deutlich verschieden).
8. Fehlende Felder alleine NIE als Ablehnungsgrund.
9. WICHTIG: Nenne in der Begründung KONKRET welche Felder übereinstimmen und welche abweichen.
10. Bei KEINE: Erkläre WARUM die Varianten nicht passen (z.B. "Titel komplett verschieden", "Jahr 30 Jahre Differenz").

DATENSATZ VDEh:
{format_record_for_display(vdeh)}
"""

            # Add available variants
            if dnb_id:
                prompt += f"\nDNB-VARIANTE A (ID-basiert, höchste Qualität):\n{format_record_for_display(dnb_id)}\n"
            if dnb_ta:
                prompt += f"\nDNB-VARIANTE B (Titel/Autor-basiert):\n{format_record_for_display(dnb_ta)}\n"
            if dnb_ty:
                prompt += f"\nDNB-VARIANTE C (Titel/Jahr-basiert, niedrigste Qualität):\n{format_record_for_display(dnb_ty)}\n"
            if loc_id:
                prompt += f"\nLOC-VARIANTE D (ID-basiert, höchste Qualität):\n{format_record_for_display(loc_id)}\n"
            if loc_ta:
                prompt += f"\nLOC-VARIANTE E (Titel/Autor-basiert):\n{format_record_for_display(loc_ta)}\n"
            if loc_ty:
                prompt += f"\nLOC-VARIANTE F (Titel/Jahr-basiert, niedrigste Qualität):\n{format_record_for_display(loc_ty)}\n"

            # Language context
            if language:
                prompt += f"\nSPRACHE: {language}\n"
                if language in ['de', 'ger', 'deu']:
                    prompt += "→ Bevorzuge DNB-Varianten (A > B > C)\n"
                elif language in ['en', 'eng']:
                    prompt += "→ Bevorzuge LoC-Varianten (D > E > F)\n"

            prompt += """
Antworte NUR mit einem dieser Formate:
A - [Begründung mit konkreten Feld-Übereinstimmungen]
B - [Begründung mit konkreten Feld-Übereinstimmungen]
C - [Begründung mit konkreten Feld-Übereinstimmungen]
D - [Begründung mit konkreten Feld-Übereinstimmungen]
E - [Begründung mit konkreten Feld-Übereinstimmungen]
F - [Begründung mit konkreten Feld-Übereinstimmungen]
KEINE - [Begründung: welche Felder weichen ab und warum]

BEISPIEL FÜR GUTE BEGRÜNDUNG:
"D - Titel und Autoren stimmen exakt überein, Jahr identisch (1991), nur Publisher unterscheidet sich (Springer vs. Verlag Stahleisen). LoC bevorzugt wegen englischer Sprache."

BEISPIEL FÜR KEINE:
"KEINE - Titel komplett verschieden (VDEh: 'Plasticity' vs DNB: 'Corporal Portal'), Jahr 29 Jahre Differenz (1993 vs 2022), Autoren passen nicht. Kein Match gefunden."

(bei mehreren passenden: bevorzuge ID > TA > TY, dann sprachbasierte Quelle)"""

            return prompt

    def parse_ai_choice(self, response: Optional[str]) -> Tuple[str, str]:
        """
        Parse AI response to extract variant choice (A-F or KEINE).

        Args:
            response: AI response string

        Returns:
            Tuple of (choice, reason) where choice is 'A', 'B', 'C', 'D', 'E', 'F', or 'KEINE'
        """
        if not response:
            return 'KEINE', 'KI keine Antwort'

        r = response.strip().upper()

        if r.startswith('A&B'):
            reason = response.split('-', 1)[1].strip() if '-' in response else ''
            return 'A', f"Beide passend, ID bevorzugt. {reason}"

        # Check all variants A-F
        for choice in ['A', 'B', 'C', 'D', 'E', 'F']:
            if r.startswith(f'{choice} ') or r.startswith(f'{choice}-') or r.startswith(f'{choice}\n') or r == choice:
                reason = response.split('-', 1)[1].strip() if '-' in response else ''
                return choice, reason

        if r.startswith('KEINE') or r.startswith('KEIN'):
            reason = response.split('-', 1)[1].strip() if '-' in response else ''
            return 'KEINE', reason if reason else 'Keine Variante passt'

        # Fallback: unclear response
        return 'KEINE', f"Unklare KI-Antwort: {response}"

    def build_tracking_data(
        self,
        vdeh_data: Dict,
        variants: Dict,
        trigger_reason: str
    ) -> Dict:
        """
        Build enhanced tracking data for fusion transparency.

        Args:
            vdeh_data: VDEh record dictionary
            variants: Dictionary of available variants (A-F)
            trigger_reason: Why was fusion triggered

        Returns:
            Dictionary with tracking information
        """
        # Track which variants are available
        variants_available = {
            choice: (data is not None and any(pd.notna(v) for v in data.values()))
            for choice, data in variants.items()
        }

        # Detect conflicts between all sources
        conflicts_detected = {}
        for field in ['title', 'authors', 'year', 'publisher']:
            vdeh_val = vdeh_data.get(field)
            # Convert pandas types to native Python types for JSON
            if pd.notna(vdeh_val):
                if pd.api.types.is_integer(vdeh_val):
                    vdeh_val = int(vdeh_val)
                elif pd.api.types.is_float(vdeh_val):
                    vdeh_val = float(vdeh_val)
            else:
                vdeh_val = None
            field_values = {'vdeh': vdeh_val}

            # Collect all variant values for this field
            for choice, data in variants.items():
                if data:
                    variant_name = {
                        'A': 'dnb_id', 'B': 'dnb_ta', 'C': 'dnb_ty',
                        'D': 'loc_id', 'E': 'loc_ta', 'F': 'loc_ty'
                    }.get(choice, choice)
                    val = data.get(field)
                    # Convert pandas types to native Python types
                    if pd.notna(val):
                        if pd.api.types.is_integer(val):
                            val = int(val)
                        elif pd.api.types.is_float(val):
                            val = float(val)
                    else:
                        val = None
                    field_values[variant_name] = val

            # Check if there are conflicts (different values)
            if len(field_values) > 1:
                unique_values = set(str(v).lower() if v else '' for v in field_values.values())
                unique_values.discard('')
                if len(unique_values) > 1:
                    conflicts_detected[field] = field_values

        # Calculate validation metrics for each variant
        validation_metrics = {}
        for choice, data in variants.items():
            if data and any(pd.notna(v) for v in data.values()):
                title_sim = self.calculate_title_similarity(
                    vdeh_data.get('title'),
                    data.get('title')
                )

                year_diff = None
                vdeh_year = vdeh_data.get('year')
                data_year = data.get('year')
                if pd.notna(vdeh_year) and pd.notna(data_year):
                    try:
                        year_diff = abs(int(vdeh_year) - int(data_year))
                    except (ValueError, TypeError):
                        pass

                is_valid, reason = self.validate_dnb_match(vdeh_data, data)

                variant_name = {
                    'A': 'dnb_id', 'B': 'dnb_ta', 'C': 'dnb_ty',
                    'D': 'loc_id', 'E': 'loc_ta', 'F': 'loc_ty'
                }.get(choice, choice)

                validation_metrics[variant_name] = {
                    'title_similarity': round(title_sim, 3) if title_sim else None,
                    'year_difference': int(year_diff) if year_diff is not None else None,
                    'valid': is_valid,
                    'validation_reason': reason
                }

        return {
            'trigger_reason': trigger_reason,
            'variants_available': json.dumps(variants_available, ensure_ascii=False),
            'conflicts_detected': json.dumps(conflicts_detected, ensure_ascii=False) if conflicts_detected else None,
            'validation_metrics': json.dumps(validation_metrics, ensure_ascii=False)
        }

    def merge_record(self, row: pd.Series) -> FusionResult:
        """
        Merge a single record with AI-based variant selection (DNB + LoC).

        Args:
            row: Pandas Series containing record data

        Returns:
            FusionResult object

        Raises:
            OllamaUnavailableError: If Ollama is unavailable after retries
        """
        # Extract VDEh data
        vdeh_data = {
            'title': row.get('title'),
            'authors': row.get('authors_str'),
            'year': row.get('year'),
            'publisher': row.get('publisher'),
            'pages': row.get('pages'),
            'isbn': row.get('isbn'),
            'issn': row.get('issn')
        }

        # Extract DNB variants (with pages if available)
        dnb_id = {
            'title': row.get('dnb_title'),
            'authors': row.get('dnb_authors'),
            'year': row.get('dnb_year'),
            'publisher': row.get('dnb_publisher'),
            'pages': row.get('dnb_pages'),
            'isbn': row.get('dnb_isbn'),
            'issn': row.get('dnb_issn')
        }

        dnb_ta = {
            'title': row.get('dnb_title_ta'),
            'authors': row.get('dnb_authors_ta'),
            'year': row.get('dnb_year_ta'),
            'publisher': row.get('dnb_publisher_ta'),
            'pages': row.get('dnb_pages_ta'),
            'isbn': row.get('dnb_isbn_ta'),
            'issn': row.get('dnb_issn_ta')
        }

        dnb_ty = {
            'title': row.get('dnb_title_ty'),
            'authors': row.get('dnb_authors_ty'),
            'year': row.get('dnb_year_ty'),
            'publisher': row.get('dnb_publisher_ty'),
            'pages': row.get('dnb_pages_ty'),
            'isbn': row.get('dnb_isbn_ty'),
            'issn': row.get('dnb_issn_ty')
        }

        # Extract LoC variants (if enabled)
        loc_id = None
        loc_ta = None
        loc_ty = None

        if self.enable_loc:
            loc_id = {
                'title': row.get('loc_title'),
                'authors': row.get('loc_authors'),
                'year': row.get('loc_year'),
                'publisher': row.get('loc_publisher'),
                'pages': row.get('loc_pages'),
                'isbn': row.get('loc_isbn'),
                'issn': row.get('loc_issn')
            }

            loc_ta = {
                'title': row.get('loc_title_ta'),
                'authors': row.get('loc_authors_ta'),
                'year': row.get('loc_year_ta'),
                'publisher': row.get('loc_publisher_ta'),
                'pages': row.get('loc_pages_ta'),
                'isbn': row.get('loc_isbn_ta'),
                'issn': row.get('loc_issn_ta')
            }

            loc_ty = {
                'title': row.get('loc_title_ty'),
                'authors': row.get('loc_authors_ty'),
                'year': row.get('loc_year_ty'),
                'publisher': row.get('loc_publisher_ty'),
                'pages': row.get('loc_pages_ty'),
                'isbn': row.get('loc_isbn_ty'),
                'issn': row.get('loc_issn_ty')
            }

        # Check if variants are actually available
        dnb_id_available = any(pd.notna(dnb_id[f]) for f in dnb_id)
        dnb_ta_available = any(pd.notna(dnb_ta[f]) for f in dnb_ta)
        dnb_ty_available = any(pd.notna(dnb_ty[f]) for f in dnb_ty)

        loc_id_available = self.enable_loc and loc_id and any(pd.notna(loc_id[f]) for f in loc_id)
        loc_ta_available = self.enable_loc and loc_ta and any(pd.notna(loc_ta[f]) for f in loc_ta)
        loc_ty_available = self.enable_loc and loc_ty and any(pd.notna(loc_ty[f]) for f in loc_ty)

        if not dnb_id_available:
            dnb_id = None
        if not dnb_ta_available:
            dnb_ta = None
        if not dnb_ty_available:
            dnb_ty = None
        if not loc_id_available:
            loc_id = None
        if not loc_ta_available:
            loc_ta = None
        if not loc_ty_available:
            loc_ty = None

        # Case 1: No external data available at all (neither DNB nor LoC)
        if dnb_id is None and dnb_ta is None and dnb_ty is None and loc_id is None and loc_ta is None and loc_ty is None:
            return FusionResult(
                title=vdeh_data['title'],
                authors=vdeh_data['authors'],
                year=vdeh_data['year'],
                publisher=vdeh_data['publisher'],
                pages=vdeh_data['pages'],
                isbn=vdeh_data['isbn'],
                issn=vdeh_data['issn'],
                title_source='vdeh',
                authors_source='vdeh',
                year_source='vdeh',
                publisher_source='vdeh',
                pages_source='vdeh',
                isbn_source='vdeh',
                issn_source='vdeh',
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
                    f"(VDEh: '{vdeh_title[:50] if vdeh_title else ''}...' vs DNB: '{dnb_ty_title[:50] if dnb_ty_title else ''}...')"
                )
                return FusionResult(
                    title=vdeh_data['title'],
                    authors=vdeh_data['authors'],
                    year=vdeh_data['year'],
                    publisher=vdeh_data['publisher'],
                    pages=vdeh_data['pages'],
                    isbn=vdeh_data['isbn'],
                    issn=vdeh_data['issn'],
                    title_source='vdeh',
                    authors_source='vdeh',
                    year_source='vdeh',
                    publisher_source='vdeh',
                    pages_source='vdeh',
                    isbn_source='vdeh',
                    issn_source='vdeh',
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

            # Fill missing fields from TY variant (ENRICHMENT only!)
            for field in ['title', 'authors', 'year', 'publisher', 'pages', 'isbn', 'issn']:
                v_val = vdeh_data[field]
                ty_val = dnb_ty.get(field) if dnb_ty else None

                # VDEh hat Wert → behalten (nur anreichern!)
                if pd.notna(v_val):
                    setattr(result, field, v_val)
                    setattr(result, f'{field}_source', 'vdeh')
                # VDEh leer, aber TY hat Wert → anreichern
                elif pd.notna(ty_val):
                    setattr(result, field, ty_val)
                    setattr(result, f'{field}_source', 'dnb_title_year')
                # Beide leer
                else:
                    setattr(result, field, None)
                    setattr(result, f'{field}_source', None)

            return result

        # Get language for prioritization
        language = row.get('detected_language')

        # Build variants dictionary for tracking
        variants_dict = {
            'A': dnb_id,
            'B': dnb_ta,
            'C': dnb_ty,
            'D': loc_id,
            'E': loc_ta,
            'F': loc_ty
        }

        # Build tracking data
        tracking_data = self.build_tracking_data(
            vdeh_data,
            variants_dict,
            'multiple_sources_available' if (dnb_id or dnb_ta or loc_id or loc_ta) else 'no_ai_needed'
        )

        # Case 2: ID or TA (DNB/LoC or both) available - use AI for selection
        ai_response = self.ollama.query(
            self.build_ai_prompt(vdeh_data, dnb_id, dnb_ta, dnb_ty, loc_id, loc_ta, loc_ty, language)
        )
        choice, reason = self.parse_ai_choice(ai_response)

        # Case 3: AI rejects all variants
        if choice == 'KEINE':
            return FusionResult(
                title=vdeh_data['title'],
                authors=vdeh_data['authors'],
                year=vdeh_data['year'],
                publisher=vdeh_data['publisher'],
                pages=vdeh_data['pages'],
                isbn=vdeh_data['isbn'],
                issn=vdeh_data['issn'],
                title_source='vdeh',
                authors_source='vdeh',
                year_source='vdeh',
                publisher_source='vdeh',
                pages_source='vdeh',
                isbn_source='vdeh',
                issn_source='vdeh',
                ai_reasoning=f"KI: {reason}",
                dnb_match_rejected=True,
                rejection_reason=reason,
                fusion_trigger_reason=tracking_data['trigger_reason'],
                fusion_variants_available=tracking_data['variants_available'],
                fusion_conflicts_detected=tracking_data['conflicts_detected'],
                fusion_validation_metrics=tracking_data['validation_metrics'],
                fusion_selected_variant='KEINE',
            )

        # Case 4: AI selected a variant (A-F)
        variant_mapping = {
            'A': ('dnb_id', dnb_id),
            'B': ('dnb_title_author', dnb_ta),
            'C': ('dnb_title_year', dnb_ty),
            'D': ('loc_id', loc_id),
            'E': ('loc_title_author', loc_ta),
            'F': ('loc_title_year', loc_ty),
        }

        selected_variant, selected_data = variant_mapping.get(choice, ('id', dnb_id))

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
                isbn=vdeh_data['isbn'],
                issn=vdeh_data['issn'],
                title_source='vdeh',
                authors_source='vdeh',
                year_source='vdeh',
                publisher_source='vdeh',
                pages_source='vdeh',
                isbn_source='vdeh',
                issn_source='vdeh',
                ai_reasoning=f"KI wählte {selected_variant}, aber Validierung fehlgeschlagen",
                dnb_match_rejected=True,
                rejection_reason=f"Validierung: {validation_reason}",
            )

        # Compare fields to find conflicts and confirmations
        conflicts, confirmations = compare_fields(vdeh_data, selected_data)

        # Build result with enhanced tracking
        result = FusionResult(
            conflicts=json.dumps(conflicts, ensure_ascii=False) if conflicts else None,
            confirmations=json.dumps(confirmations, ensure_ascii=False) if confirmations else None,
            ai_reasoning=f"KI Entscheidung: Variante {choice} ({selected_variant}) gewählt. {reason}. Validierung: {validation_reason}",
            dnb_variant_selected=selected_variant if choice in ['A', 'B', 'C'] else None,
            loc_match_rejected=False if choice in ['D', 'E', 'F'] else False,
            fusion_trigger_reason=tracking_data['trigger_reason'],
            fusion_variants_available=tracking_data['variants_available'],
            fusion_conflicts_detected=tracking_data['conflicts_detected'],
            fusion_validation_metrics=tracking_data['validation_metrics'],
            fusion_selected_variant=choice,
        )

        # Assign values field by field (ENRICHMENT, not replacement!)
        for field in ['title', 'authors', 'year', 'publisher', 'pages', 'isbn', 'issn']:
            v_val = vdeh_data[field]
            d_val = selected_data.get(field) if selected_data else None

            # VDEh hat Wert → behalten (nur anreichern, nicht ersetzen!)
            if pd.notna(v_val):
                setattr(result, field, v_val)
                # Wenn DNB/LoC denselben Wert hat → confirmed, sonst vdeh
                if pd.notna(d_val) and field in confirmations:
                    setattr(result, f'{field}_source', 'confirmed')
                else:
                    setattr(result, f'{field}_source', 'vdeh')
            # VDEh leer, aber DNB/LoC hat Wert → anreichern
            elif pd.notna(d_val):
                setattr(result, field, d_val)
                # Use correct source prefix based on variant
                if selected_variant.startswith('loc'):
                    setattr(result, f'{field}_source', selected_variant)
                else:
                    setattr(result, f'{field}_source', selected_variant)
            # Beide leer
            else:
                setattr(result, field, None)
                setattr(result, f'{field}_source', 'vdeh' if field != 'isbn' and field != 'issn' else None)

        return result
