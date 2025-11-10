"""
Parser Module für Multi-Source Bibliotheksdaten

Dieses Paket enthält Parser für verschiedene bibliographische Datenformate:
- VDEH Parser: OAI-PMH XML Format
- MAB2 Parser: Deutsche Bibliotheksdaten im MAB2-Format
"""

from .base_parser import BaseParser
from .vdeh_parser import parse_bibliography, analyze_bibliography_data, get_sample_records
from .mab2_parser import MAB2Parser, analyze_mab2_data, get_sample_records_mab2

__all__ = [
    'BaseParser',
    'MAB2Parser',
    'parse_bibliography',
    'analyze_bibliography_data', 
    'analyze_mab2_data',
    'get_sample_records',
    'get_sample_records_mab2'
]