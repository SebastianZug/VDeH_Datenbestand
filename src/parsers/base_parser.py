"""
Base Parser Klasse für alle Bibliotheksdaten-Parser

Definiert ein einheitliches Interface für verschiedene Parser-Implementierungen.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
from pathlib import Path
import pandas as pd
import logging

class BaseParser(ABC):
    """
    Abstrakte Basisklasse für alle Bibliotheksdaten-Parser
    
    Implementiert gemeinsame Funktionalität und definiert das Interface
    für spezifische Parser-Implementierungen.
    """
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """
        Initialisiert den Parser
        
        Args:
            config: Konfigurationsdictionary für den Parser
            logger: Logger-Instanz (optional)
        """
        self.config = config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.stats = {}
        
    @abstractmethod
    def parse_file(self, file_path: Union[str, Path], **kwargs) -> pd.DataFrame:
        """
        Parsed eine Datei und gibt ein standardisiertes DataFrame zurück
        
        Args:
            file_path: Pfad zur zu parsenden Datei
            **kwargs: Parser-spezifische Optionen
            
        Returns:
            DataFrame mit standardisierten bibliographischen Daten
        """
        pass
    
    @abstractmethod
    def analyze_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analysiert die geparsten Daten und gibt Statistiken zurück
        
        Args:
            df: DataFrame mit bibliographischen Daten
            
        Returns:
            Dictionary mit Analyse-Statistiken
        """
        pass
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Gibt Parser-Statistiken zurück
        
        Returns:
            Dictionary mit Parser-Statistiken
        """
        return self.stats.copy()
    
    def validate_file(self, file_path: Union[str, Path]) -> bool:
        """
        Validiert, ob eine Datei vom Parser verarbeitet werden kann
        
        Args:
            file_path: Pfad zur zu validierenden Datei
            
        Returns:
            True wenn die Datei verarbeitet werden kann
        """
        file_path = Path(file_path)
        return file_path.exists() and file_path.is_file()
    
    def standardize_output(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardisiert die Ausgabe-Datenstruktur für alle Parser
        
        Args:
            raw_data: Parser-spezifische Rohdaten
            
        Returns:
            Standardisierte Datenstruktur
        """
        standard_fields = {
            'id': raw_data.get('id'),
            'source': raw_data.get('source'),
            'title': raw_data.get('title'),
            'authors': raw_data.get('authors', []),
            'authors_str': raw_data.get('authors_str'),
            'year': raw_data.get('year'),
            'isbn': raw_data.get('isbn'),
            'publisher': raw_data.get('publisher'),
            'place': raw_data.get('place'),
            'language': raw_data.get('language'),
            'subject': raw_data.get('subject'),
            'format': raw_data.get('format'),
            'url': raw_data.get('url')
        }
        
        # Entferne None-Werte
        return {k: v for k, v in standard_fields.items() if v is not None}
    
    def log_parsing_progress(self, current: int, total: int, step: int = 1000):
        """
        Loggt den Parsing-Fortschritt
        
        Args:
            current: Aktuelle Anzahl verarbeiteter Records
            total: Gesamtanzahl Records
            step: Schrittweite für Logging
        """
        if current % step == 0 or current == total:
            percentage = (current / total * 100) if total > 0 else 0
            self.logger.info(f"📊 Progress: {current:,}/{total:,} ({percentage:.1f}%)")
    
    def handle_parsing_error(self, error: Exception, context: str = ""):
        """
        Behandelt Parsing-Fehler einheitlich
        
        Args:
            error: Aufgetretener Fehler
            context: Kontext-Information
        """
        error_msg = f"Parsing Error"
        if context:
            error_msg += f" in {context}"
        error_msg += f": {str(error)}"
        
        self.logger.warning(error_msg)
        
        # Aktualisiere Fehler-Statistiken
        if 'errors' not in self.stats:
            self.stats['errors'] = []
        self.stats['errors'].append({
            'error': str(error),
            'context': context,
            'type': type(error).__name__
        })