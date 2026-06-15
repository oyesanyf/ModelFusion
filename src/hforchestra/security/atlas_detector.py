"""
ATLAS Threat Detector for Enhanced Security.

This module provides threat detection capabilities based on the MITRE ATLAS framework
for identifying potential adversarial attacks against AI systems.
"""

import re
from typing import List, Dict, Optional


class ATLASThreatDetector:
    """Scans for patterns related to the MITRE ATLAS framework."""
    
    def __init__(self):
        # A subset of ATLAS techniques detectable via text patterns
        # See: https://atlas.mitre.org/matrices/ATLAS
        self.ttps = {
            "AML.T0049": {
                "name": "Evasion of AI-Assessed Policies",
                "keywords": [
                    "ignore previous instructions", "disregard safety", "jailbreak",
                    "DAN prompt", "act as if", "roleplay as", "without moral judgment"
                ]
            },
            "AML.T0052": {
                "name": "Abuse of Dual-Use Foundational Model",
                "keywords": [
                    "malware", "keylogger", "ransomware", "exploit code", "vulnerability",
                    "phishing email", "impersonate", "deepfake", "disinformation campaign",
                    "make a bomb", "synthesize a weapon", "create poison", "illegal substance"
                ]
            },
            "AML.T0040": {
                "name": "Reconnaissance of AI Systems",
                "keywords": [
                    "what are your safety guidelines", "how do you filter content",
                    "what is your system prompt", "reveal your instructions", "find security flaws"
                ]
            },
            "AML.T0043": {
                "name": "AI-Enabled Social Engineering",
                "keywords": [
                    "convince the user to", "trick the employee into", "create a pretext",
                    "write a persuasive script to", "generate a fraudulent message"
                ]
            }
        }

    def scan_thought(self, thought: str) -> Optional[List[Dict[str, str]]]:
        """Scans a thought for keywords associated with ATLAS TTPs."""
        detected_threats = []
        lower_thought = thought.lower()
        for ttp_id, details in self.ttps.items():
            for keyword in details["keywords"]:
                if re.search(r'\b' + re.escape(keyword) + r'\b', lower_thought):
                    detected_threats.append({"id": ttp_id, "name": details["name"]})
                    break
        return detected_threats if detected_threats else None 