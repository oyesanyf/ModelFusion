"""
Security module for HFOrchestra.

This module contains security-related components including ATLAS threat detection
and other security monitoring capabilities.
"""

from .atlas_detector import ATLASThreatDetector

__all__ = ['ATLASThreatDetector'] 