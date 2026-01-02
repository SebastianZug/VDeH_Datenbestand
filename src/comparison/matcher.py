"""
Comparison Module für Bibliotheksbestandsvergleich

Dieses Modul implementiert verschiedene Matching-Strategien um
VDEh-Neuerwerbungen mit dem UB TUBAF-Bestand zu vergleichen.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Set
import re
from difflib import SequenceMatcher
import logging
from dataclasses import dataclass

@dataclass
class MatchResult:
    """Datenklasse für Match-Ergebnisse"""
    vdeh_id: str
    ub_id: str
    match_type: str
    confidence: float
    details: Dict

class BookMatcher:
    """
    Haupt-Klasse für den Bestandsvergleich zwischen VDEh und UB TUBAF
    
    Implementiert verschiedene Matching-Strategien:
    - ISBN-basiertes Matching (exakt und normalisiert)
    - Titel-basiertes Fuzzy Matching  
    - Autor+Titel Kombinationsmatching
    """
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        self.config = config.get('comparison', {})
        self.logger = logger or logging.getLogger(__name__)
        
        # Konfigurationen laden
        self.strategies = self.config.get('matching_strategies', [
            'isbn_exact', 'title_fuzzy', 'author_title_combo'
        ])
        self.thresholds = self.config.get('similarity_thresholds', {
            'title_fuzzy': 0.85,
            'author_fuzzy': 0.90,
            'combined_threshold': 0.80
        })
        self.text_config = self.config.get('text_normalization', {})
        
        # Statistiken
        self.match_stats = {
            'total_vdeh': 0,
            'total_ub': 0,
            'matches_found': 0,
            'match_breakdown': {}
        }
    
    def compare_collections(self, vdeh_df: pd.DataFrame, ub_df: pd.DataFrame) -> pd.DataFrame:
        """
        Führt einen vollständigen Vergleich zwischen VDEh und UB TUBAF durch

        Args:
            vdeh_df: VDEh Neuerwerbungen DataFrame
            ub_df: UB TUBAF Bestand DataFrame
            
        Returns:
            DataFrame mit Match-Ergebnissen
        """
        self.logger.info(f"🔍 === BESTANDSVERGLEICH GESTARTET ===")
        self.logger.info(f"📚 VDEh Records: {len(vdeh_df):,}")
        self.logger.info(f"🏛️  UB TUBAF Records: {len(ub_df):,}")
        
        self.match_stats['total_vdeh'] = len(vdeh_df)
        self.match_stats['total_ub'] = len(ub_df)
        
        all_matches = []
        
        # Führe alle konfigurierten Matching-Strategien durch
        for strategy in self.strategies:
            self.logger.info(f"\n🎯 Führe {strategy} Matching durch...")
            
            try:
                if strategy == 'isbn_exact':
                    matches = self._match_isbn_exact(vdeh_df, ub_df)
                elif strategy == 'isbn_normalized':
                    matches = self._match_isbn_normalized(vdeh_df, ub_df)
                elif strategy == 'title_exact':
                    matches = self._match_title_exact(vdeh_df, ub_df)
                elif strategy == 'title_fuzzy':
                    matches = self._match_title_fuzzy(vdeh_df, ub_df)
                elif strategy == 'author_title_combo':
                    matches = self._match_author_title_combo(vdeh_df, ub_df)
                else:
                    self.logger.warning(f"⚠️  Unbekannte Strategie: {strategy}")
                    continue
                
                if matches:
                    self.logger.info(f"✅ {strategy}: {len(matches)} Matches gefunden")
                    all_matches.extend(matches)
                    self.match_stats['match_breakdown'][strategy] = len(matches)
                else:
                    self.logger.info(f"❌ {strategy}: Keine Matches")
                    self.match_stats['match_breakdown'][strategy] = 0
                    
            except Exception as e:
                self.logger.error(f"❌ Fehler bei {strategy}: {e}")
                self.match_stats['match_breakdown'][strategy] = 0
        
        # Erstelle Ergebnis-DataFrame
        if all_matches:
            # Entferne Duplikate (basierend auf vdeh_id + ub_id)
            unique_matches = self._deduplicate_matches(all_matches)
            
            matches_df = pd.DataFrame([{
                'vdeh_id': m.vdeh_id,
                'ub_id': m.ub_id,
                'match_type': m.match_type,
                'confidence': m.confidence,
                'vdeh_title': m.details.get('vdeh_title'),
                'ub_title': m.details.get('ub_title'),
                'vdeh_authors': m.details.get('vdeh_authors'),
                'ub_authors': m.details.get('ub_authors'),
                'isbn_match': m.details.get('isbn_match'),
                'title_similarity': m.details.get('title_similarity')
            } for m in unique_matches])
            
            self.match_stats['matches_found'] = len(matches_df)
            
            self.logger.info(f"\n✅ === VERGLEICH ABGESCHLOSSEN ===")
            self.logger.info(f"📊 Gefundene Matches: {len(matches_df):,}")
            self.logger.info(f"📈 Match-Rate: {len(matches_df)/len(vdeh_df)*100:.1f}% der VDEh Records")
            
        else:
            matches_df = pd.DataFrame()
            self.logger.warning("❌ Keine Matches gefunden!")
        
        return matches_df
    
    def _match_isbn_exact(self, vdeh_df: pd.DataFrame, ub_df: pd.DataFrame) -> List[MatchResult]:
        """ISBN Exakt-Matching"""
        matches = []
        
        # Filter DataFrames für Records mit ISBN
        vdeh_isbn = vdeh_df[vdeh_df['isbn'].notna()].copy()
        ub_isbn = ub_df[ub_df['isbn'].notna()].copy()
        
        if vdeh_isbn.empty or ub_isbn.empty:
            return matches
        
        # Erstelle ISBN-Lookup für UB
        ub_lookup = dict(zip(ub_isbn['isbn'], ub_isbn.index))
        
        for _, vdeh_row in vdeh_isbn.iterrows():
            vdeh_isbn_val = str(vdeh_row['isbn']).strip()
            
            if vdeh_isbn_val in ub_lookup:
                ub_idx = ub_lookup[vdeh_isbn_val]
                ub_row = ub_df.loc[ub_idx]
                
                match = MatchResult(
                    vdeh_id=str(vdeh_row['id']),
                    ub_id=str(ub_row['id']),
                    match_type='isbn_exact',
                    confidence=1.0,
                    details={
                        'vdeh_title': vdeh_row.get('title'),
                        'ub_title': ub_row.get('title'),
                        'vdeh_authors': vdeh_row.get('authors_str'),
                        'ub_authors': ub_row.get('authors_str'),
                        'isbn_match': vdeh_isbn_val
                    }
                )
                matches.append(match)
        
        return matches
    
    def _match_isbn_normalized(self, vdeh_df: pd.DataFrame, ub_df: pd.DataFrame) -> List[MatchResult]:
        """ISBN Normalisiertes Matching (entfernt Bindestriche, etc.)"""
        matches = []
        
        def normalize_isbn(isbn_str):
            if pd.isna(isbn_str):
                return None
            return re.sub(r'[-\s]', '', str(isbn_str).strip())
        
        # Filter und normalisiere ISBNs
        vdeh_isbn = vdeh_df[vdeh_df['isbn'].notna()].copy()
        vdeh_isbn['isbn_norm'] = vdeh_isbn['isbn'].apply(normalize_isbn)
        
        ub_isbn = ub_df[ub_df['isbn'].notna()].copy()
        ub_isbn['isbn_norm'] = ub_isbn['isbn'].apply(normalize_isbn)
        
        if vdeh_isbn.empty or ub_isbn.empty:
            return matches
        
        # Lookup für normalisierte ISBNs
        ub_lookup = dict(zip(ub_isbn['isbn_norm'], ub_isbn.index))
        
        for _, vdeh_row in vdeh_isbn.iterrows():
            isbn_norm = vdeh_row['isbn_norm']
            
            if isbn_norm and isbn_norm in ub_lookup:
                ub_idx = ub_lookup[isbn_norm]
                ub_row = ub_df.loc[ub_idx]
                
                match = MatchResult(
                    vdeh_id=str(vdeh_row['id']),
                    ub_id=str(ub_row['id']),
                    match_type='isbn_normalized',
                    confidence=0.95,
                    details={
                        'vdeh_title': vdeh_row.get('title'),
                        'ub_title': ub_row.get('title'),
                        'vdeh_authors': vdeh_row.get('authors_str'),
                        'ub_authors': ub_row.get('authors_str'),
                        'isbn_match': isbn_norm
                    }
                )
                matches.append(match)
        
        return matches
    
    def _match_title_exact(self, vdeh_df: pd.DataFrame, ub_df: pd.DataFrame) -> List[MatchResult]:
        """Exakter Titel-Match (nach Normalisierung)"""
        matches = []
        
        # Filter für Records mit Titel
        vdeh_titles = vdeh_df[vdeh_df['title'].notna()].copy()
        ub_titles = ub_df[ub_df['title'].notna()].copy()
        
        if vdeh_titles.empty or ub_titles.empty:
            return matches
        
        # Normalisiere Titel
        vdeh_titles['title_norm'] = vdeh_titles['title'].apply(self._normalize_text)
        ub_titles['title_norm'] = ub_titles['title'].apply(self._normalize_text)
        
        # Lookup für normalisierte Titel
        ub_lookup = dict(zip(ub_titles['title_norm'], ub_titles.index))
        
        for _, vdeh_row in vdeh_titles.iterrows():
            title_norm = vdeh_row['title_norm']
            
            if title_norm and title_norm in ub_lookup:
                ub_idx = ub_lookup[title_norm]
                ub_row = ub_df.loc[ub_idx]
                
                match = MatchResult(
                    vdeh_id=str(vdeh_row['id']),
                    ub_id=str(ub_row['id']),
                    match_type='title_exact',
                    confidence=0.90,
                    details={
                        'vdeh_title': vdeh_row.get('title'),
                        'ub_title': ub_row.get('title'),
                        'vdeh_authors': vdeh_row.get('authors_str'),
                        'ub_authors': ub_row.get('authors_str'),
                        'title_similarity': 1.0
                    }
                )
                matches.append(match)
        
        return matches
    
    def _match_title_fuzzy(self, vdeh_df: pd.DataFrame, ub_df: pd.DataFrame) -> List[MatchResult]:
        """Fuzzy Titel-Matching mit konfigurierbarem Schwellenwert"""
        matches = []
        threshold = self.thresholds.get('title_fuzzy', 0.85)
        
        # Filter für Records mit Titel
        vdeh_titles = vdeh_df[vdeh_df['title'].notna()].copy()
        ub_titles = ub_df[ub_df['title'].notna()].copy()
        
        if vdeh_titles.empty or ub_titles.empty:
            return matches
        
        # Normalisiere Titel
        vdeh_titles['title_norm'] = vdeh_titles['title'].apply(self._normalize_text)
        ub_titles['title_norm'] = ub_titles['title'].apply(self._normalize_text)
        
        # Für Performance: Begrenze auf Sample falls zu groß
        if len(vdeh_titles) > 1000 or len(ub_titles) > 1000:
            self.logger.info(f"⚠️  Große Datenmenge - verwende Sample für Fuzzy Matching")
            vdeh_sample = vdeh_titles.head(500)
            ub_sample = ub_titles.head(500)
        else:
            vdeh_sample = vdeh_titles
            ub_sample = ub_titles
        
        for _, vdeh_row in vdeh_sample.iterrows():
            vdeh_title = vdeh_row['title_norm']
            if not vdeh_title:
                continue
                
            best_match = None
            best_similarity = 0
            
            for _, ub_row in ub_sample.iterrows():
                ub_title = ub_row['title_norm']
                if not ub_title:
                    continue
                
                similarity = self._calculate_similarity(vdeh_title, ub_title)
                
                if similarity >= threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_match = ub_row
            
            if best_match is not None:
                match = MatchResult(
                    vdeh_id=str(vdeh_row['id']),
                    ub_id=str(best_match['id']),
                    match_type='title_fuzzy',
                    confidence=best_similarity,
                    details={
                        'vdeh_title': vdeh_row.get('title'),
                        'ub_title': best_match.get('title'),
                        'vdeh_authors': vdeh_row.get('authors_str'),
                        'ub_authors': best_match.get('authors_str'),
                        'title_similarity': best_similarity
                    }
                )
                matches.append(match)
        
        return matches
    
    def _match_author_title_combo(self, vdeh_df: pd.DataFrame, ub_df: pd.DataFrame) -> List[MatchResult]:
        """Kombiniertes Autor+Titel Matching"""
        matches = []
        
        # Filter für Records mit Autor UND Titel
        vdeh_combo = vdeh_df[
            vdeh_df['title'].notna() & vdeh_df['authors_str'].notna()
        ].copy()
        ub_combo = ub_df[
            ub_df['title'].notna() & ub_df['authors_str'].notna()
        ].copy()
        
        if vdeh_combo.empty or ub_combo.empty:
            return matches
        
        # Begrenze für Performance
        if len(vdeh_combo) > 200 or len(ub_combo) > 200:
            vdeh_combo = vdeh_combo.head(100)
            ub_combo = ub_combo.head(100)
        
        for _, vdeh_row in vdeh_combo.iterrows():
            vdeh_title_norm = self._normalize_text(vdeh_row['title'])
            vdeh_author_norm = self._normalize_text(vdeh_row['authors_str'])
            
            if not vdeh_title_norm or not vdeh_author_norm:
                continue
            
            best_match = None
            best_score = 0
            
            for _, ub_row in ub_combo.iterrows():
                ub_title_norm = self._normalize_text(ub_row['title'])
                ub_author_norm = self._normalize_text(ub_row['authors_str'])
                
                if not ub_title_norm or not ub_author_norm:
                    continue
                
                # Berechne kombinierte Ähnlichkeit
                title_sim = self._calculate_similarity(vdeh_title_norm, ub_title_norm)
                author_sim = self._calculate_similarity(vdeh_author_norm, ub_author_norm)
                
                # Gewichtete Kombination (Titel 60%, Autor 40%)
                combined_score = (title_sim * 0.6) + (author_sim * 0.4)
                
                threshold = self.thresholds.get('combined_threshold', 0.80)
                if combined_score >= threshold and combined_score > best_score:
                    best_score = combined_score
                    best_match = ub_row
            
            if best_match is not None:
                match = MatchResult(
                    vdeh_id=str(vdeh_row['id']),
                    ub_id=str(best_match['id']),
                    match_type='author_title_combo',
                    confidence=best_score,
                    details={
                        'vdeh_title': vdeh_row.get('title'),
                        'ub_title': best_match.get('title'),
                        'vdeh_authors': vdeh_row.get('authors_str'),
                        'ub_authors': best_match.get('authors_str'),
                        'title_similarity': title_sim,
                        'author_similarity': author_sim
                    }
                )
                matches.append(match)
        
        return matches
    
    def _normalize_text(self, text: str) -> str:
        """Normalisiert Text für bessere Matching-Ergebnisse"""
        if pd.isna(text) or not text:
            return ""
        
        text = str(text).strip()
        
        # Konfigurationsbasierte Normalisierung
        if self.text_config.get('lowercase', True):
            text = text.lower()
        
        if self.text_config.get('remove_punctuation', True):
            text = re.sub(r'[^\w\s]', ' ', text)
        
        if self.text_config.get('remove_articles', True):
            # Deutsche und englische Artikel entfernen
            articles = r'\b(der|die|das|ein|eine|the|a|an)\b'
            text = re.sub(articles, ' ', text, flags=re.IGNORECASE)
        
        # Mehrfache Leerzeichen entfernen
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Berechnet Ähnlichkeit zwischen zwei Texten"""
        if not text1 or not text2:
            return 0.0
            
        return SequenceMatcher(None, text1, text2).ratio()
    
    def _deduplicate_matches(self, matches: List[MatchResult]) -> List[MatchResult]:
        """Entfernt Duplikate aus Match-Liste, behält besten Match pro VDEh-Record"""
        match_dict = {}
        
        for match in matches:
            key = match.vdeh_id
            
            if key not in match_dict or match.confidence > match_dict[key].confidence:
                match_dict[key] = match
        
        return list(match_dict.values())
    
    def get_statistics(self) -> Dict:
        """Gibt Match-Statistiken zurück"""
        return self.match_stats.copy()
    
    def analyze_gaps(self, vdeh_df: pd.DataFrame, matches_df: pd.DataFrame) -> Dict:
        """
        Analysiert Erwerbungslücken (VDEh Records ohne Match im UB-Bestand)
        """
        if matches_df.empty:
            gaps_df = vdeh_df.copy()
        else:
            matched_vdeh_ids = set(matches_df['vdeh_id'].astype(str))
            vdeh_ids = vdeh_df['id'].astype(str)
            gaps_df = vdeh_df[~vdeh_ids.isin(matched_vdeh_ids)]
        
        gap_analysis = {
            'total_vdeh_records': len(vdeh_df),
            'matched_records': len(matches_df),
            'gap_records': len(gaps_df),
            'gap_percentage': len(gaps_df) / len(vdeh_df) * 100 if len(vdeh_df) > 0 else 0,
            'gaps_by_year': {},
            'gaps_by_language': {}
        }
        
        # Analyse nach Jahr
        if 'year' in gaps_df.columns and not gaps_df['year'].isna().all():
            year_counts = gaps_df['year'].value_counts().head(10)
            gap_analysis['gaps_by_year'] = year_counts.to_dict()
        
        # Analyse nach Sprache
        if 'lang_name' in gaps_df.columns and not gaps_df['lang_name'].isna().all():
            lang_counts = gaps_df['lang_name'].value_counts().head(5)
            gap_analysis['gaps_by_language'] = lang_counts.to_dict()
        
        return gap_analysis