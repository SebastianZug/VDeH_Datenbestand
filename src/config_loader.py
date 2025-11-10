"""
VDEH Projekt Konfigurationsmodul
====================================

Zentrales Modul zum Laden und Verwalten der Projektkonfiguration.
Alle Notebooks und Skripte sollten diese Konfiguration verwenden.
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
import warnings
import logging

# Configure logger for this module
logger = logging.getLogger(__name__)

class VDEHConfig:
    """Zentrale Konfigurationsklasse für das VDEH-Projekt"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialisiert die Konfiguration
        
        Args:
            config_path: Pfad zur config.yaml (optional, sucht automatisch)
        """
        self.config_path = self._find_config_file(config_path)
        self.config = self._load_config()
        self._setup_paths()
    
    def _find_config_file(self, config_path: Optional[str]) -> Path:
        """Findet die config.yaml Datei automatisch"""
        if config_path:
            return Path(config_path)
        
        # Suche in verschiedenen möglichen Pfaden
        search_paths = [
            Path.cwd() / "config.yaml",  # Aktuelles Verzeichnis
            Path.cwd().parent / "config.yaml",  # Ein Verzeichnis höher
            Path.cwd().parent.parent / "config.yaml",  # Zwei Verzeichnisse höher
        ]
        
        for path in search_paths:
            if path.exists():
                return path
        
        raise FileNotFoundError(
            f"config.yaml nicht gefunden. Suchpfade: {[str(p) for p in search_paths]}"
        )
    
    def _load_config(self) -> Dict[str, Any]:
        """Lädt die YAML-Konfiguration"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            logger.info(f"Configuration loaded from {self.config_path}")
            return config
        except Exception as e:
            raise RuntimeError(f"Fehler beim Laden der Konfiguration: {e}")
    
    def _setup_paths(self):
        """Erstellt absolute Pfade basierend auf der Konfiguration"""
        self.project_root = self.config_path.parent
        
        # Alle relativen Pfade zu absoluten Pfaden konvertieren
        self.paths = {}
        for key, value in self.config['paths'].items():
            if isinstance(value, dict):
                # Verschachtelte Dictionaries rekursiv verarbeiten
                self.paths[key] = self._process_nested_paths(value)
            else:
                self.paths[key] = self.project_root / value
    
    def _process_nested_paths(self, path_dict):
        """Verarbeitet verschachtelte Pfad-Dictionaries rekursiv"""
        result = {}
        for k, v in path_dict.items():
            if isinstance(v, dict):
                # Weitere Verschachtelung
                result[k] = self._process_nested_paths(v)
            elif isinstance(v, str):
                # String-Pfad zu absolutem Pfad konvertieren
                result[k] = self.project_root / v
            else:
                # Anderen Wert unverändert übernehmen
                result[k] = v
        return result
    
    def get(self, key: str, default=None):
        """
        Holt einen Konfigurationswert mit Dot-Notation
        
        Beispiel: config.get('data_processing.xml_parser.max_records')
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def get_path(self, path_key: str) -> Path:
        """Holt einen absoluten Pfad mit Dot-Notation"""
        keys = path_key.split('.')
        value = self.paths
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                raise KeyError(f"Pfad '{path_key}' nicht in Konfiguration gefunden")
        
        if isinstance(value, Path):
            return value
        else:
            raise KeyError(f"'{path_key}' ist kein Pfad-Wert")
    
    def ensure_directories(self):
        """Erstellt alle konfigurierten Verzeichnisse falls sie nicht existieren"""
        dirs_to_create = [
            self.get_path('data.processed'),
            self.get_path('data.output'),
            self.get_path('results'),
            self.get_path('figures'),
            self.get_path('exports')
        ]
        
        created = []
        for dir_path in dirs_to_create:
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                created.append(str(dir_path))

        if created:
            logger.info(f"Created {len(created)} directories: {', '.join(created)}")
    
    def print_summary(self):
        """Gibt eine Übersicht der Konfiguration aus"""
        logger.info("=== VDEH PROJECT CONFIGURATION ===")
        logger.info(f"Project: {self.config['project']['name']} v{self.config['project']['version']}")
        logger.info(f"Root: {self.project_root}")
        logger.info(f"Config: {self.config_path}")
        logger.info(f"XML Source: {self.get_path('xml_source')}")
        logger.info(f"Parser: {self.get_path('parser_module')}")
        logger.info(f"Max Records: {self.get('data_processing.xml_parser.max_records') or 'All'}")

def load_config(config_path: Optional[str] = None) -> VDEHConfig:
    """
    Convenience-Funktion zum Laden der Konfiguration
    
    Usage:
        config = load_config()
        xml_file = config.get_path('xml_source')
    """
    return VDEHConfig(config_path)

# Global verfügbare Konfiguration (Singleton Pattern)
_global_config = None

def get_config() -> VDEHConfig:
    """Gibt die globale Konfiguration zurück (lädt sie beim ersten Aufruf)"""
    global _global_config
    if _global_config is None:
        _global_config = load_config()
    return _global_config