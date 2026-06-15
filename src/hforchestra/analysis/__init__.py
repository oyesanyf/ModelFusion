"""
Analysis module for HFOrchestra.

This module contains PE header analysis and malware detection components.
"""

from .pe_extractor import CompletePEHeaderExtractor
from .malware_detector import PEAnalyzer

__all__ = ['CompletePEHeaderExtractor', 'PEAnalyzer'] 