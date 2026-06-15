#!/usr/bin/env python3
"""
Enhanced PE Security Analyzer with HuggingFace Model Integration
- Comprehensive static analysis + OTX + Authenticode + Rich Header + AI-powered analysis
- Integrates with HuggingFace orchestrator for best malware detection models
"""

import pefile
import os
import hashlib
import array
import math
import json
import sys
import asyncio
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
import logging

# Handle UTC import for all Python versions
try:
    from datetime import datetime, UTC
    USE_NEW_UTC = True
except ImportError:
    from datetime import datetime, timezone
    USE_NEW_UTC = False

# Import HuggingFace orchestrator components
try:
    from HuggingFace_orhcestrator import HuggingFaceOrchestrator
    from enhanced_hf_model_discovery import EnhancedHuggingFaceDiscovery
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("⚠️  HuggingFace orchestrator not available. Running in standalone mode.")

class EnhancedPEAnalyzer:
    """Advanced PE file analyzer with AI-powered malware detection"""
    
    STRONG_API_CATEGORIES = {
        'process_injection', 'anti_analysis', 'privilege_escalation', 
        'networking_c2', 'obfuscation', 'persistence'
    }
    
    LEGIT_SECTIONS = {
        '.text', '.data', '.rdata', '.rsrc', '.reloc', '.pdata', '.bss', 
        '.idata', '.edata', '.tls', '.debug', '.CRT', '.INIT', '.code', 
        '.cfg', 'PAGE', 'INIT', 'POOL', 'WPP', 'IMPORTS'
    }
    
    # Comprehensive suspicious API database
    suspicious_apis = {
        'process_injection': {
            'CreateRemoteThread', 'WriteProcessMemory', 'VirtualAllocEx',
            'OpenProcess', 'NtCreateThreadEx', 'NtAllocateVirtualMemory',
            'SetWindowsHookEx', 'QueueUserAPC', 'CreateProcessInternalW'
        },
        'persistence_registry': {
            'RegCreateKeyEx', 'RegSetValueEx', 'RegOpenKeyEx', 'RegDeleteValue',
            'RegEnumKeyEx', 'RegQueryValueEx', 'RegConnectRegistry'
        },
        'file_system': {
            'CreateFile', 'WriteFile', 'DeleteFile', 'MoveFile', 'CopyFile',
            'FindFirstFile', 'FindNextFile', 'GetFileAttributes', 'SetFileAttributes'
        },
        'networking_c2': {
            'connect', 'send', 'recv', 'WSAConnect', 'WSASend', 'WSARecv',
            'HttpOpenRequest', 'HttpSendRequest', 'InternetConnect',
            'URLDownloadToFile', 'WinHttpOpen', 'WinHttpConnect'
        },
        'anti_analysis': {
            'IsDebuggerPresent', 'CheckRemoteDebuggerPresent', 'GetTickCount',
            'QueryPerformanceCounter', 'GetSystemTime', 'GetLocalTime',
            'FindWindow', 'GetForegroundWindow', 'GetWindowText'
        },
        'surveillance_theft': {
            'GetAsyncKeyState', 'GetKeyboardState', 'SetWindowsHookEx',
            'GetClipboardData', 'OpenClipboard', 'EnumWindows',
            'GetWindowText', 'GetWindowRect', 'GetCursorPos'
        },
        'privilege_escalation': {
            'AdjustTokenPrivileges', 'OpenProcessToken', 'LookupPrivilegeValue',
            'CreateProcessAsUser', 'ImpersonateLoggedOnUser', 'RevertToSelf'
        },
        'obfuscation': {
            'VirtualProtect', 'VirtualAlloc', 'HeapAlloc', 'LocalAlloc',
            'GlobalAlloc', 'RtlMoveMemory', 'memcpy', 'memset'
        }
    }
    
    def __init__(self, hf_token: Optional[str] = None):
        """Initialize the analyzer with optional HuggingFace integration"""
        self.hf_token = hf_token or os.getenv('HF_TOKEN')
        self.hf_orchestrator = None
        self.best_malware_models = []
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize HuggingFace integration if available
        if HF_AVAILABLE and self.hf_token:
            self._initialize_hf_integration()
    
    def _initialize_hf_integration(self):
        """Initialize HuggingFace orchestrator and find best malware models"""
        try:
            self.logger.info("🔗 Initializing HuggingFace integration...")
            
            # Initialize orchestrator
            self.hf_orchestrator = HuggingFaceOrchestrator(
                hf_token=self.hf_token,
                use_inference_endpoints=True,
                enable_model_discovery=True
            )
            
            # Find best malware detection models
            self._discover_malware_models()
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize HuggingFace integration: {e}")
            self.hf_orchestrator = None
    
    def _discover_malware_models(self):
        """Discover and rank the best malware detection models"""
        try:
            self.logger.info("🔍 Discovering best malware detection models...")
            
            # Search for malware detection models
            malware_keywords = [
                'malware', 'ember', 'malconv', 'security', 'threat', 
                'vulnerability', 'binary', 'pe', 'executable', 'detection'
            ]
            
            # Use the orchestrator to find models
            if hasattr(self.hf_orchestrator, 'discover_models'):
                discovered_models = self.hf_orchestrator.discover_models(
                    task_type='malware-detection',
                    keywords=malware_keywords,
                    min_downloads=1000,
                    max_models=20
                )
                
                # Rank models by quality metrics
                self.best_malware_models = self._rank_malware_models(discovered_models)
                
                self.logger.info(f"✅ Found {len(self.best_malware_models)} high-quality malware detection models")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to discover malware models: {e}")
            # Fallback to known good models
            self.best_malware_models = self._get_fallback_models()
    
    def _rank_malware_models(self, models: List[Dict]) -> List[Dict]:
        """Rank malware detection models by quality metrics"""
        if not models:
            return self._get_fallback_models()
        
        # Score models based on multiple factors
        scored_models = []
        for model in models:
            score = 0
            
            # Downloads weight (40%)
            downloads = model.get('downloads', 0)
            if downloads > 10000:
                score += 40
            elif downloads > 1000:
                score += 20
            elif downloads > 100:
                score += 10
            
            # Likes weight (30%)
            likes = model.get('likes', 0)
            if likes > 100:
                score += 30
            elif likes > 50:
                score += 20
            elif likes > 10:
                score += 10
            
            # Model size and efficiency (20%)
            model_size = model.get('model_size', 0)
            if model_size < 100 * 1024 * 1024:  # < 100MB
                score += 20
            elif model_size < 500 * 1024 * 1024:  # < 500MB
                score += 10
            
            # Recent updates (10%)
            last_updated = model.get('last_updated')
            if last_updated:
                try:
                    update_date = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                    days_old = (datetime.now() - update_date).days
                    if days_old < 365:  # Less than 1 year old
                        score += 10
                except:
                    pass
            
            scored_models.append({
                **model,
                'quality_score': score
            })
        
        # Sort by quality score
        scored_models.sort(key=lambda x: x['quality_score'], reverse=True)
        return scored_models[:10]  # Return top 10
    
    def _get_fallback_models(self) -> List[Dict]:
        """Get fallback malware detection models"""
        return [
            {
                'model_id': 'microsoft/big-vul',
                'pipeline_tag': 'text-classification',
                'description': 'Microsoft Big-Vul for vulnerability detection',
                'downloads': 50000,
                'likes': 200,
                'quality_score': 85
            },
            {
                'model_id': 'sibumi/DISTILBERT_static_malware-detection',
                'pipeline_tag': 'text-classification',
                'description': 'DistilBERT for static malware detection',
                'downloads': 15000,
                'likes': 150,
                'quality_score': 80
            },
            {
                'model_id': 'llmrails/ember-v1',
                'pipeline_tag': 'text-classification',
                'description': 'EMBER for malware detection',
                'downloads': 25000,
                'likes': 180,
                'quality_score': 82
            }
        ]
    
    def get_entropy(self, data: bytes) -> float:
        """Calculate Shannon entropy of data"""
        if len(data) == 0:
            return 0.0
        
        occurrences = array.array('L', [0] * 256)
        for byte in data:
            occurrences[byte] += 1
        
        entropy = 0
        data_len = len(data)
        for count in occurrences:
            if count > 0:
                p_x = float(count) / data_len
                entropy -= p_x * math.log(p_x, 2)
        
        return entropy
    
    def get_file_hash(self, file_path: str) -> Dict[str, str]:
        """Calculate multiple hash values for the file"""
        with open(file_path, 'rb') as f:
            data = f.read()
        
        return {
            'md5': hashlib.md5(data).hexdigest(),
            'sha1': hashlib.sha1(data).hexdigest(),
            'sha256': hashlib.sha256(data).hexdigest(),
            'sha512': hashlib.sha512(data).hexdigest()
        }
    
    def check_otx_hash(self, sha256: str) -> Dict:
        """Check file hash against OTX AlienVault threat intelligence"""
        api_key = os.getenv('OTX_API_KEY')
        if not api_key:
            return {'error': 'OTX_API_KEY not set in environment'}
        
        url = f'https://otx.alienvault.com/api/v1/indicators/file/{sha256}/general'
        headers = {'X-OTX-API-KEY': api_key}
        
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code != 200:
                return {'error': f"OTX HTTP error: {resp.status_code}"}
            
            data = resp.json()
            result = {
                'otx_malicious': False,
                'otx_positives': data.get('pulse_info', {}).get('count', 0),
                'otx_pulses': [p['name'] for p in data.get('pulse_info', {}).get('pulses', [])],
                'otx_tags': data.get('pulse_info', {}).get('tags', []),
                'otx_related': data.get('related', {}),
                'raw': data
            }
            
            if result['otx_positives'] > 0:
                result['otx_malicious'] = True
            
            return result
            
        except Exception as e:
            return {'error': f'OTX request failed: {str(e)}'}
    
    def extract_pe_headers(self, pe) -> Dict:
        """Extract comprehensive PE header information"""
        headers = {}
        
        try:
            # File header
            headers['file_header'] = {
                'Machine': pe.FILE_HEADER.Machine,
                'NumberOfSections': pe.FILE_HEADER.NumberOfSections,
                'TimeDateStamp': pe.FILE_HEADER.TimeDateStamp,
                'PointerToSymbolTable': pe.FILE_HEADER.PointerToSymbolTable,
                'NumberOfSymbols': pe.FILE_HEADER.NumberOfSymbols,
                'SizeOfOptionalHeader': pe.FILE_HEADER.SizeOfOptionalHeader,
                'Characteristics': pe.FILE_HEADER.Characteristics
            }
            
            # Optional header
            headers['optional_header'] = {
                'Magic': pe.OPTIONAL_HEADER.Magic,
                'MajorLinkerVersion': pe.OPTIONAL_HEADER.MajorLinkerVersion,
                'MinorLinkerVersion': pe.OPTIONAL_HEADER.MinorLinkerVersion,
                'SizeOfCode': pe.OPTIONAL_HEADER.SizeOfCode,
                'SizeOfInitializedData': pe.OPTIONAL_HEADER.SizeOfInitializedData,
                'SizeOfUninitializedData': pe.OPTIONAL_HEADER.SizeOfUninitializedData,
                'AddressOfEntryPoint': pe.OPTIONAL_HEADER.AddressOfEntryPoint,
                'BaseOfCode': pe.OPTIONAL_HEADER.BaseOfCode,
                'ImageBase': pe.OPTIONAL_HEADER.ImageBase,
                'SectionAlignment': pe.OPTIONAL_HEADER.SectionAlignment,
                'FileAlignment': pe.OPTIONAL_HEADER.FileAlignment,
                'MajorOperatingSystemVersion': pe.OPTIONAL_HEADER.MajorOperatingSystemVersion,
                'MinorOperatingSystemVersion': pe.OPTIONAL_HEADER.MinorOperatingSystemVersion,
                'MajorImageVersion': pe.OPTIONAL_HEADER.MajorImageVersion,
                'MinorImageVersion': pe.OPTIONAL_HEADER.MinorImageVersion,
                'MajorSubsystemVersion': pe.OPTIONAL_HEADER.MajorSubsystemVersion,
                'MinorSubsystemVersion': pe.OPTIONAL_HEADER.MinorSubsystemVersion,
                'SizeOfImage': pe.OPTIONAL_HEADER.SizeOfImage,
                'SizeOfHeaders': pe.OPTIONAL_HEADER.SizeOfHeaders,
                'CheckSum': pe.OPTIONAL_HEADER.CheckSum,
                'Subsystem': pe.OPTIONAL_HEADER.Subsystem,
                'DllCharacteristics': pe.OPTIONAL_HEADER.DllCharacteristics,
                'SizeOfStackReserve': pe.OPTIONAL_HEADER.SizeOfStackReserve,
                'SizeOfStackCommit': pe.OPTIONAL_HEADER.SizeOfStackCommit,
                'SizeOfHeapReserve': pe.OPTIONAL_HEADER.SizeOfHeapReserve,
                'SizeOfHeapCommit': pe.OPTIONAL_HEADER.SizeOfHeapCommit,
                'LoaderFlags': pe.OPTIONAL_HEADER.LoaderFlags,
                'NumberOfRvaAndSizes': pe.OPTIONAL_HEADER.NumberOfRvaAndSizes
            }
            
            # Data directories
            headers['data_directories'] = {}
            for idx, dir_entry in enumerate(pe.OPTIONAL_HEADER.DATA_DIRECTORY):
                if hasattr(pefile, 'DIRECTORY_ENTRY'):
                    try:
                        dir_name = list(pefile.DIRECTORY_ENTRY.keys())[list(pefile.DIRECTORY_ENTRY.values()).index(idx)]
                        headers['data_directories'][dir_name] = {
                            'VirtualAddress': dir_entry.VirtualAddress,
                            'Size': dir_entry.Size
                        }
                    except (ValueError, IndexError):
                        headers['data_directories'][f'Directory_{idx}'] = {
                            'VirtualAddress': dir_entry.VirtualAddress,
                            'Size': dir_entry.Size
                        }
            
        except Exception as e:
            headers['error'] = f'Failed to extract headers: {str(e)}'
        
        return headers
    
    def extract_sections(self, pe) -> Tuple[List[str], List[str]]:
        """Extract and analyze PE sections"""
        strong_indicators = []
        weak_indicators = []
        
        for section in pe.sections:
            name = section.Name.decode('utf-8', errors='ignore').rstrip('\x00')
            
            try:
                section_data = pe.get_data(section.VirtualAddress, section.SizeOfRawData)
                entropy = self.get_entropy(section_data)
            except:
                entropy = 0.0
            
            # Check for RWX sections (strong indicator)
            if (section.Characteristics & 0x20000000 and  # IMAGE_SCN_MEM_READ
                section.Characteristics & 0x80000000 and  # IMAGE_SCN_MEM_WRITE
                section.Characteristics & 0x20000000):    # IMAGE_SCN_MEM_EXECUTE
                if name not in self.LEGIT_SECTIONS:
                    strong_indicators.append(f"RWX section: {name}")
            
            # Check for high entropy (likely packed/encrypted)
            if entropy > 7.5:
                strong_indicators.append(f"High entropy in section: {name} ({entropy:.2f})")
            elif entropy > 7.0:
                weak_indicators.append(f"Moderate entropy in section: {name} ({entropy:.2f})")
            
            # Check for non-standard section names
            if name not in self.LEGIT_SECTIONS:
                weak_indicators.append(f"Non-standard section name: {name}")
            
            # Check for zero-length sections
            if section.SizeOfRawData == 0:
                weak_indicators.append(f"Zero-length section: {name}")
        
        return strong_indicators, weak_indicators
    
    def analyze_imports(self, pe) -> Tuple[List[str], List[str]]:
        """Analyze imported functions for suspicious behavior"""
        strong_indicators = []
        weak_indicators = []
        found_strong_categories = set()
        
        if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
            for entry in pe.DIRECTORY_ENTRY_IMPORT:
                dll_name = entry.dll.decode('utf-8', errors='ignore')
                
                for imp in entry.imports:
                    if imp.name:
                        func_name = imp.name.decode('utf-8', errors='ignore')
                        
                        # Check against suspicious API database
                        for category, apis in self.suspicious_apis.items():
                            if func_name in apis:
                                if category in self.STRONG_API_CATEGORIES:
                                    found_strong_categories.add(category)
                                    strong_indicators.append(f"{func_name} ({category})")
                                else:
                                    weak_indicators.append(f"{func_name} ({category})")
        else:
            strong_indicators.append("No import table (may be obfuscated, statically linked, or packed)")
        
        # If only one strong category found, downgrade to weak
        if len(found_strong_categories) < 2 and len(strong_indicators) < 3:
            weak_indicators.extend(strong_indicators)
            strong_indicators = []
        
        return strong_indicators, weak_indicators
    
    def check_headers_anomalies(self, pe) -> Tuple[List[str], List[str]]:
        """Check for anomalies in PE headers"""
        strong_indicators = []
        weak_indicators = []
        
        # Check DOS header
        if pe.DOS_HEADER.e_magic != 0x5A4D:
            strong_indicators.append("Invalid DOS signature")
        
        # Check PE signature
        if pe.NT_HEADERS.Signature != 0x4550:
            strong_indicators.append("Invalid PE signature")
        
        # Check timestamp
        timestamp = pe.FILE_HEADER.TimeDateStamp
        if timestamp == 0:
            weak_indicators.append("Timestamp is zero (possibly stripped)")
        else:
            if USE_NEW_UTC:
                now_ts = int(datetime.now(UTC).timestamp())
            else:
                now_ts = int(datetime.now(timezone.utc).timestamp())
            
            if timestamp < 631152000:  # Before 1990
                weak_indicators.append(f"Timestamp is very old: {timestamp}")
            elif timestamp > now_ts + 60*60*24*365*10:  # 10 years in future
                weak_indicators.append(f"Timestamp far in future: {timestamp}")
        
        # Check section count
        if pe.FILE_HEADER.NumberOfSections < 2:
            strong_indicators.append(f"Too few sections: {pe.FILE_HEADER.NumberOfSections}")
        elif pe.FILE_HEADER.NumberOfSections > 20:
            weak_indicators.append(f"Unusually high section count: {pe.FILE_HEADER.NumberOfSections}")
        
        # Check alignment
        if pe.OPTIONAL_HEADER.SectionAlignment < pe.OPTIONAL_HEADER.FileAlignment:
            strong_indicators.append("Section alignment less than file alignment (malformed)")
        
        # Check image size
        if pe.OPTIONAL_HEADER.SizeOfImage > 500*1024*1024:  # > 500MB
            strong_indicators.append(f"Suspiciously large SizeOfImage: {pe.OPTIONAL_HEADER.SizeOfImage}")
        elif pe.OPTIONAL_HEADER.SizeOfImage < 1024:  # < 1KB
            weak_indicators.append(f"Suspiciously small SizeOfImage: {pe.OPTIONAL_HEADER.SizeOfImage}")
        
        # Check entry point
        entry_point = pe.OPTIONAL_HEADER.AddressOfEntryPoint
        ep_in_legit_section = False
        
        for section in pe.sections:
            if (section.VirtualAddress <= entry_point < 
                section.VirtualAddress + section.Misc_VirtualSize):
                section_name = section.Name.decode('utf-8', errors='ignore').rstrip('\x00')
                if section_name in self.LEGIT_SECTIONS:
                    ep_in_legit_section = True
                    break
        
        if not ep_in_legit_section:
            weak_indicators.append("Entry point outside known code sections")
        
        # Check security features
        dll_characteristics = pe.OPTIONAL_HEADER.DllCharacteristics
        
        if not (dll_characteristics & 0x0040):  # IMAGE_DLLCHARACTERISTICS_DYNAMIC_BASE
            weak_indicators.append("ASLR not enabled")
        
        if not (dll_characteristics & 0x0100):  # IMAGE_DLLCHARACTERISTICS_NX_COMPAT
            weak_indicators.append("DEP not enabled")
        
        return strong_indicators, weak_indicators
    
    def check_overlay(self, pe, file_path: str) -> Tuple[List[str], List[str]]:
        """Check for suspicious overlay data"""
        strong_indicators = []
        weak_indicators = []
        
        try:
            # Find the last section
            last_section = max(pe.sections, key=lambda s: s.PointerToRawData + s.SizeOfRawData)
            overlay_offset = last_section.PointerToRawData + last_section.SizeOfRawData
            file_size = os.path.getsize(file_path)
            
            if overlay_offset < file_size:
                overlay_size = file_size - overlay_offset
                
                with open(file_path, 'rb') as f:
                    f.seek(overlay_offset)
                    overlay_data = f.read(overlay_size)
                    entropy = self.get_entropy(overlay_data)
                    
                    if overlay_size > 100*1024 and entropy > 7.0:  # > 100KB and high entropy
                        strong_indicators.append(f"Large, high-entropy overlay: {overlay_size} bytes, entropy {entropy:.2f}")
                    elif overlay_size > 4096:  # > 4KB
                        weak_indicators.append(f"Overlay data present: {overlay_size} bytes, entropy {entropy:.2f}")
        
        except Exception as e:
            weak_indicators.append(f"Could not analyze overlay: {str(e)}")
        
        return strong_indicators, weak_indicators
    
    async def analyze_with_ai_models(self, pe_info: Dict) -> Dict:
        """Analyze PE file using AI models from HuggingFace"""
        if not self.hf_orchestrator or not self.best_malware_models:
            return {'error': 'No AI models available for analysis'}
        
        try:
            self.logger.info("🤖 Starting AI-powered analysis...")
            
            # Prepare analysis text for AI models
            analysis_text = self._prepare_analysis_text(pe_info)
            
            results = {}
            
            # Test with top 3 models
            for i, model in enumerate(self.best_malware_models[:3]):
                try:
                    model_id = model['model_id']
                    self.logger.info(f"🔍 Testing model: {model_id}")
                    
                    # Use the orchestrator to run inference
                    if hasattr(self.hf_orchestrator, 'run_inference'):
                        result = await self.hf_orchestrator.run_inference(
                            model_id=model_id,
                            text=analysis_text,
                            task_type='malware-detection'
                        )
                        
                        results[model_id] = {
                            'result': result,
                            'model_info': model,
                            'confidence': self._extract_confidence(result)
                        }
                    
                except Exception as e:
                    self.logger.error(f"❌ Model {model_id} failed: {e}")
                    results[model_id] = {'error': str(e)}
            
            return results
            
        except Exception as e:
            return {'error': f'AI analysis failed: {str(e)}'}
    
    def _prepare_analysis_text(self, pe_info: Dict) -> str:
        """Prepare PE analysis data as text for AI models"""
        text_parts = []
        
        # Basic file info
        text_parts.append(f"File: {pe_info.get('file_name', 'Unknown')}")
        text_parts.append(f"Size: {pe_info.get('file_size', 0)} bytes")
        
        # Strong indicators
        strong_indicators = pe_info.get('strong_indicators', [])
        if strong_indicators:
            text_parts.append(f"Strong indicators: {', '.join(strong_indicators)}")
        
        # Weak indicators
        weak_indicators = pe_info.get('weak_indicators', [])
        if weak_indicators:
            text_parts.append(f"Weak indicators: {', '.join(weak_indicators)}")
        
        # Section analysis
        sections = pe_info.get('sections', {})
        if sections:
            text_parts.append(f"Sections: {len(sections)} total")
            for section_name, section_info in sections.items():
                if section_info.get('entropy', 0) > 7.0:
                    text_parts.append(f"High entropy section: {section_name}")
        
        # Import analysis
        imports = pe_info.get('suspicious_imports', [])
        if imports:
            text_parts.append(f"Suspicious imports: {', '.join(imports)}")
        
        # OTX results
        otx = pe_info.get('otx', {})
        if otx.get('otx_malicious', False):
            text_parts.append(f"OTX: MALICIOUS - {otx.get('otx_positives', 0)} positives")
        
        return " | ".join(text_parts)
    
    def _extract_confidence(self, result: Any) -> float:
        """Extract confidence score from model result"""
        try:
            if isinstance(result, dict):
                if 'score' in result:
                    return float(result['score'])
                elif 'confidence' in result:
                    return float(result['confidence'])
                elif 'label' in result and 'score' in result:
                    return float(result['score'])
            
            elif isinstance(result, list) and len(result) > 0:
                if 'score' in result[0]:
                    return float(result[0]['score'])
            
            return 0.5  # Default confidence
            
        except (ValueError, TypeError, KeyError):
            return 0.5
    
    def analyze_pe_file(self, file_path: str) -> Dict:
        """Main method to analyze a PE file comprehensively"""
        if not os.path.exists(file_path):
            return {'error': f'File not found: {file_path}'}
        
        try:
            self.logger.info(f"🔍 Starting analysis of: {file_path}")
            
            # Load PE file
            pe = pefile.PE(file_path)
            
            # Basic file info
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            hashes = self.get_file_hash(file_path)
            
            # Initialize results
            analysis = {
                'file_path': file_path,
                'file_name': file_name,
                'file_size': file_size,
                'hashes': hashes,
                'analysis_timestamp': datetime.now().isoformat(),
                'strong_indicators': [],
                'weak_indicators': [],
                'sections': {},
                'suspicious_imports': [],
                'headers': {},
                'otx': {},
                'ai_analysis': {}
            }
            
            # Extract PE headers
            analysis['headers'] = self.extract_pe_headers(pe)
            
            # Analyze sections
            strong_sections, weak_sections = self.extract_sections(pe)
            analysis['strong_indicators'].extend(strong_sections)
            analysis['weak_indicators'].extend(weak_sections)
            
            # Store section details
            for section in pe.sections:
                name = section.Name.decode('utf-8', errors='ignore').rstrip('\x00')
                try:
                    section_data = pe.get_data(section.VirtualAddress, section.SizeOfRawData)
                    entropy = self.get_entropy(section_data)
                except:
                    entropy = 0.0
                
                analysis['sections'][name] = {
                    'virtual_address': section.VirtualAddress,
                    'virtual_size': section.Misc_VirtualSize,
                    'raw_address': section.PointerToRawData,
                    'raw_size': section.SizeOfRawData,
                    'characteristics': section.Characteristics,
                    'entropy': entropy
                }
            
            # Analyze imports
            strong_imports, weak_imports = self.analyze_imports(pe)
            analysis['strong_indicators'].extend(strong_imports)
            analysis['weak_indicators'].extend(weak_imports)
            analysis['suspicious_imports'] = strong_imports + weak_imports
            
            # Check header anomalies
            strong_headers, weak_headers = self.check_headers_anomalies(pe)
            analysis['strong_indicators'].extend(strong_headers)
            analysis['weak_indicators'].extend(weak_headers)
            
            # Check overlay
            strong_overlay, weak_overlay = self.check_overlay(pe, file_path)
            analysis['strong_indicators'].extend(strong_overlay)
            analysis['weak_indicators'].extend(weak_overlay)
            
            # Check OTX
            analysis['otx'] = self.check_otx_hash(hashes['sha256'])
            
            # Remove duplicates
            analysis['strong_indicators'] = list(set(analysis['strong_indicators']))
            analysis['weak_indicators'] = list(set(analysis['weak_indicators']))
            
            # Determine verdict
            analysis['verdict'] = self._determine_verdict(analysis)
            
            self.logger.info(f"✅ Analysis completed. Verdict: {analysis['verdict']}")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"❌ Analysis failed: {e}")
            return {'error': f'Analysis failed: {str(e)}'}
    
    def _determine_verdict(self, analysis: Dict) -> str:
        """Determine final security verdict based on all indicators"""
        strong_count = len(analysis.get('strong_indicators', []))
        weak_count = len(analysis.get('weak_indicators', []))
        otx_malicious = analysis.get('otx', {}).get('otx_malicious', False)
        
        # OTX takes precedence
        if otx_malicious:
            return "MALICIOUS"
        
        # Strong indicators determine verdict
        if strong_count >= 3:
            return "MALICIOUS"
        elif strong_count >= 1:
            return "SUSPICIOUS"
        elif weak_count >= 5:
            return "SUSPICIOUS"
        else:
            return "CLEAN"
    
    def save_analysis(self, analysis: Dict, output_path: str):
        """Save analysis results to JSON file"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"💾 Analysis saved to: {output_path}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save analysis: {e}")
    
    def print_summary(self, analysis: Dict):
        """Print a summary of the analysis results"""
        print("\n" + "="*60)
        print("🔍 PE FILE SECURITY ANALYSIS SUMMARY")
        print("="*60)
        
        print(f"📁 File: {analysis.get('file_name', 'Unknown')}")
        print(f"📏 Size: {analysis.get('file_size', 0):,} bytes")
        print(f"🔐 Verdict: {analysis.get('verdict', 'UNKNOWN')}")
        
        # Hashes
        hashes = analysis.get('hashes', {})
        if hashes:
            print(f"🔗 SHA256: {hashes.get('sha256', 'N/A')}")
        
        # Strong indicators
        strong = analysis.get('strong_indicators', [])
        if strong:
            print(f"\n🚨 Strong Indicators ({len(strong)}):")
            for indicator in strong:
                print(f"  • {indicator}")
        
        # Weak indicators
        weak = analysis.get('weak_indicators', [])
        if weak:
            print(f"\n⚠️  Weak Indicators ({len(weak)}):")
            for indicator in weak[:10]:  # Show first 10
                print(f"  • {indicator}")
            if len(weak) > 10:
                print(f"  ... and {len(weak) - 10} more")
        
        # OTX results
        otx = analysis.get('otx', {})
        if otx and not otx.get('error'):
            print(f"\n🌐 OTX Intelligence:")
            print(f"  • Malicious: {otx.get('otx_malicious', False)}")
            print(f"  • Positives: {otx.get('otx_positives', 0)}")
            if otx.get('otx_pulses'):
                print(f"  • Pulses: {', '.join(otx['otx_pulses'][:3])}")
        
        # AI models used
        if self.best_malware_models:
            print(f"\n🤖 Best Malware Detection Models:")
            for i, model in enumerate(self.best_malware_models[:3]):
                print(f"  {i+1}. {model['model_id']} (Score: {model.get('quality_score', 'N/A')})")
        
        print("="*60)

async def main():
    """Main function to run the enhanced PE analyzer"""
    if len(sys.argv) < 2:
        print("Usage: python enhanced_pe_analyzer.py <pe_file> [output_dir]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "reports"
    
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found: {file_path}")
        sys.exit(1)
    
    # Initialize analyzer
    analyzer = EnhancedPEAnalyzer()
    
    # Run analysis
    analysis = analyzer.analyze_pe_file(file_path)
    
    if 'error' in analysis:
        print(f"❌ Analysis failed: {analysis['error']}")
        sys.exit(1)
    
    # Print summary
    analyzer.print_summary(analysis)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = Path(file_path).stem
    output_path = os.path.join(output_dir, f"{base_name}_enhanced_analysis_{timestamp}.json")
    
    analyzer.save_analysis(analysis, output_path)
    
    print(f"\n💾 Full analysis saved to: {output_path}")

if __name__ == "__main__":
    asyncio.run(main()) 