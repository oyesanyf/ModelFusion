#!/usr/bin/env python3
"""
Enhanced PE Analyzer with AI Integration
Combines PE header extraction with Magika detection, langextract context analysis,
and database-driven model selection for malware analysis.
"""

import pefile
import os
import array
import math
import json
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class PEAnalysisResult:
    """Result of PE file analysis."""
    success: bool
    pe_info: Dict[str, Any]
    malware_analysis: Dict[str, Any]
    ai_context: Dict[str, Any]
    file_type_info: Dict[str, Any]
    error_message: Optional[str] = None

class EnhancedPEAnalyzer:
    """Enhanced PE analyzer with AI integration."""
    
    def __init__(self, db_path: str = "db/hf_models.db"):
        self.db_path = db_path
    
    def get_entropy(self, data):
        """Calculate Shannon entropy of data."""
        if len(data) == 0:
            return 0.0
        occurences = array.array('L', [0]*256)
        for x in data:
            occurences[x if isinstance(x, int) else ord(x)] += 1
        entropy = 0
        for x in occurences:
            if x:
                p_x = float(x) / len(data)
                entropy -= p_x*math.log(p_x, 2)
        return entropy

    def get_resources(self, pe):
        """Extract resources: [entropy, size]"""
        resources = []
        if hasattr(pe, 'DIRECTORY_ENTRY_RESOURCE'):
            try:
                for resource_type in pe.DIRECTORY_ENTRY_RESOURCE.entries:
                    if hasattr(resource_type, 'directory'):
                        for resource_id in resource_type.directory.entries:
                            if hasattr(resource_id, 'directory'):
                                for resource_lang in resource_id.directory.entries:
                                    data = pe.get_data(resource_lang.data.struct.OffsetToData, resource_lang.data.struct.Size)
                                    size = resource_lang.data.struct.Size
                                    entropy = self.get_entropy(data)
                                    resources.append([entropy, size])
            except Exception as e:
                logger.warning(f"Error extracting resources: {e}")
                return resources
        return resources

    def get_version_info(self, pe):
        """Return version infos"""
        res = {}
        try:
            for fileinfo in pe.FileInfo:
                if fileinfo.Key == 'StringFileInfo':
                    for st in fileinfo.StringTable:
                        for entry in st.entries.items():
                            res[entry[0]] = entry[1]
                if fileinfo.Key == 'VarFileInfo':
                    for var in fileinfo.Var:
                        res[var.entry.items()[0][0]] = var.entry.items()[0][1]
            if hasattr(pe, 'VS_FIXEDFILEINFO'):
                res['flags'] = pe.VS_FIXEDFILEINFO.FileFlags
                res['os'] = pe.VS_FIXEDFILEINFO.FileOS
                res['type'] = pe.VS_FIXEDFILEINFO.FileType
                res['file_version'] = pe.VS_FIXEDFILEINFO.FileVersionLS
                res['product_version'] = pe.VS_FIXEDFILEINFO.ProductVersionLS
                res['signature'] = pe.VS_FIXEDFILEINFO.Signature
                res['struct_version'] = pe.VS_FIXEDFILEINFO.StrucVersion
        except Exception as e:
            logger.warning(f"Error extracting version info: {e}")
        return res

    def extract_pe_info(self, fpath):
        """Extract comprehensive PE file information."""
        res = {}
        try:
            pe = pefile.PE(fpath)
            
            # Basic file info
            res['file_path'] = str(fpath)
            res['file_size'] = os.path.getsize(fpath)
            res['is_pe'] = True
            
            # File header
            res['Machine'] = pe.FILE_HEADER.Machine
            res['SizeOfOptionalHeader'] = pe.FILE_HEADER.SizeOfOptionalHeader
            res['Characteristics'] = pe.FILE_HEADER.Characteristics
            res['TimeDateStamp'] = pe.FILE_HEADER.TimeDateStamp
            res['NumberOfSections'] = pe.FILE_HEADER.NumberOfSections
            
            # Optional header
            res['MajorLinkerVersion'] = pe.OPTIONAL_HEADER.MajorLinkerVersion
            res['MinorLinkerVersion'] = pe.OPTIONAL_HEADER.MinorLinkerVersion
            res['SizeOfCode'] = pe.OPTIONAL_HEADER.SizeOfCode
            res['SizeOfInitializedData'] = pe.OPTIONAL_HEADER.SizeOfInitializedData
            res['SizeOfUninitializedData'] = pe.OPTIONAL_HEADER.SizeOfUninitializedData
            res['AddressOfEntryPoint'] = pe.OPTIONAL_HEADER.AddressOfEntryPoint
            res['BaseOfCode'] = pe.OPTIONAL_HEADER.BaseOfCode
            try:
                res['BaseOfData'] = pe.OPTIONAL_HEADER.BaseOfData
            except AttributeError:
                res['BaseOfData'] = 0
            res['ImageBase'] = pe.OPTIONAL_HEADER.ImageBase
            res['SectionAlignment'] = pe.OPTIONAL_HEADER.SectionAlignment
            res['FileAlignment'] = pe.OPTIONAL_HEADER.FileAlignment
            res['MajorOperatingSystemVersion'] = pe.OPTIONAL_HEADER.MajorOperatingSystemVersion
            res['MinorOperatingSystemVersion'] = pe.OPTIONAL_HEADER.MinorOperatingSystemVersion
            res['MajorImageVersion'] = pe.OPTIONAL_HEADER.MajorImageVersion
            res['MinorImageVersion'] = pe.OPTIONAL_HEADER.MinorImageVersion
            res['MajorSubsystemVersion'] = pe.OPTIONAL_HEADER.MajorSubsystemVersion
            res['MinorSubsystemVersion'] = pe.OPTIONAL_HEADER.MinorSubsystemVersion
            res['SizeOfImage'] = pe.OPTIONAL_HEADER.SizeOfImage
            res['SizeOfHeaders'] = pe.OPTIONAL_HEADER.SizeOfHeaders
            res['CheckSum'] = pe.OPTIONAL_HEADER.CheckSum
            res['Subsystem'] = pe.OPTIONAL_HEADER.Subsystem
            res['DllCharacteristics'] = pe.OPTIONAL_HEADER.DllCharacteristics
            res['SizeOfStackReserve'] = pe.OPTIONAL_HEADER.SizeOfStackReserve
            res['SizeOfStackCommit'] = pe.OPTIONAL_HEADER.SizeOfStackCommit
            res['SizeOfHeapReserve'] = pe.OPTIONAL_HEADER.SizeOfHeapReserve
            res['SizeOfHeapCommit'] = pe.OPTIONAL_HEADER.SizeOfHeapCommit
            res['LoaderFlags'] = pe.OPTIONAL_HEADER.LoaderFlags
            res['NumberOfRvaAndSizes'] = pe.OPTIONAL_HEADER.NumberOfRvaAndSizes

            # Sections analysis
            res['SectionsNb'] = len(pe.sections)
            entropy = list(map(lambda x:x.get_entropy(), pe.sections))
            res['SectionsMeanEntropy'] = sum(entropy)/float(len(entropy)) if entropy else 0
            res['SectionsMinEntropy'] = min(entropy) if entropy else 0
            res['SectionsMaxEntropy'] = max(entropy) if entropy else 0
            raw_sizes = list(map(lambda x:x.SizeOfRawData, pe.sections))
            res['SectionsMeanRawsize'] = sum(raw_sizes)/float(len(raw_sizes)) if raw_sizes else 0
            res['SectionsMinRawsize'] = min(raw_sizes) if raw_sizes else 0
            res['SectionsMaxRawsize'] = max(raw_sizes) if raw_sizes else 0
            virtual_sizes = list(map(lambda x:x.Misc_VirtualSize, pe.sections))
            res['SectionsMeanVirtualsize'] = sum(virtual_sizes)/float(len(virtual_sizes)) if virtual_sizes else 0
            res['SectionsMinVirtualsize'] = min(virtual_sizes) if virtual_sizes else 0
            res['SectionMaxVirtualsize'] = max(virtual_sizes) if virtual_sizes else 0

            # Section details
            res['sections'] = []
            for section in pe.sections:
                section_info = {
                    'name': section.Name.decode('utf-8', errors='ignore').strip('\x00'),
                    'virtual_address': section.VirtualAddress,
                    'virtual_size': section.Misc_VirtualSize,
                    'raw_size': section.SizeOfRawData,
                    'raw_address': section.PointerToRawData,
                    'characteristics': section.Characteristics,
                    'entropy': section.get_entropy()
                }
                res['sections'].append(section_info)

            # Imports analysis
            try:
                res['ImportsNbDLL'] = len(pe.DIRECTORY_ENTRY_IMPORT)
                imports = sum([x.imports for x in pe.DIRECTORY_ENTRY_IMPORT], [])
                res['ImportsNb'] = len(imports)
                res['ImportsNbOrdinal'] = len(list(filter(lambda x:x.name is None, imports)))
                
                # Get import details
                import_details = []
                for entry in pe.DIRECTORY_ENTRY_IMPORT:
                    dll_name = entry.dll.decode('utf-8', errors='ignore')
                    functions = []
                    for imp in entry.imports:
                        if imp.name:
                            functions.append(imp.name.decode('utf-8', errors='ignore'))
                        else:
                            functions.append(f"Ordinal_{imp.ordinal}")
                    import_details.append({
                        'dll': dll_name,
                        'functions': functions
                    })
                res['ImportDetails'] = import_details
            except AttributeError:
                res['ImportsNbDLL'] = 0
                res['ImportsNb'] = 0
                res['ImportsNbOrdinal'] = 0
                res['ImportDetails'] = []

            # Exports analysis
            try:
                res['ExportNb'] = len(pe.DIRECTORY_ENTRY_EXPORT.symbols)
                export_details = []
                for symbol in pe.DIRECTORY_ENTRY_EXPORT.symbols:
                    if symbol.name:
                        export_details.append(symbol.name.decode('utf-8', errors='ignore'))
                res['ExportDetails'] = export_details
            except AttributeError:
                res['ExportNb'] = 0
                res['ExportDetails'] = []

            # Resources analysis
            resources = self.get_resources(pe)
            res['ResourcesNb'] = len(resources)
            if len(resources) > 0:
                entropy = list(map(lambda x:x[0], resources))
                res['ResourcesMeanEntropy'] = sum(entropy)/float(len(entropy))
                res['ResourcesMinEntropy'] = min(entropy)
                res['ResourcesMaxEntropy'] = max(entropy)  
                sizes = list(map(lambda x:x[1], resources))
                res['ResourcesMeanSize'] = sum(sizes)/float(len(sizes))
                res['ResourcesMinSize'] = min(sizes)
                res['ResourcesMaxSize'] = max(sizes)
            else:
                res['ResourcesMeanEntropy'] = 0
                res['ResourcesMinEntropy'] = 0
                res['ResourcesMaxEntropy'] = 0
                res['ResourcesMeanSize'] = 0
                res['ResourcesMinSize'] = 0
                res['ResourcesMaxSize'] = 0

            # Load configuration
            try:
                res['LoadConfigurationSize'] = pe.DIRECTORY_ENTRY_LOAD_CONFIG.struct.Size
            except AttributeError:
                res['LoadConfigurationSize'] = 0

            # Version information
            try:
                version_infos = self.get_version_info(pe)
                res['VersionInformationSize'] = len(version_infos.keys())
                res['VersionInfo'] = version_infos
            except AttributeError:
                res['VersionInformationSize'] = 0
                res['VersionInfo'] = {}

            pe.close()
            
        except Exception as e:
            res['error'] = str(e)
            res['is_pe'] = False
            logger.error(f"Error extracting PE info: {e}")
        
        return res

    def analyze_malware_indicators(self, pe_info):
        """Analyze PE info for malware indicators."""
        indicators = {
            'suspicious_entropy': False,
            'suspicious_imports': False,
            'suspicious_sections': False,
            'suspicious_characteristics': False,
            'suspicious_subsystem': False,
            'suspicious_dll_characteristics': False,
            'risk_score': 0,
            'risk_level': 'LOW',
            'indicators_found': []
        }
        
        risk_score = 0
        indicators_found = []
        
        # Check entropy (high entropy can indicate packed/obfuscated code)
        if pe_info.get('SectionsMeanEntropy', 0) > 7.0:
            indicators['suspicious_entropy'] = True
            indicators_found.append("High entropy detected (possible packing/obfuscation)")
            risk_score += 20
        
        # Check for suspicious imports
        suspicious_apis = [
            'VirtualAlloc', 'VirtualProtect', 'CreateRemoteThread', 'WriteProcessMemory',
            'ReadProcessMemory', 'OpenProcess', 'CreateProcess', 'ShellExecute',
            'URLDownloadToFile', 'InternetOpen', 'RegCreateKey', 'RegSetValue',
            'CreateFile', 'WriteFile', 'ReadFile', 'DeleteFile', 'MoveFile',
            'GetProcAddress', 'LoadLibrary', 'GetModuleHandle', 'CreateMutex',
            'CreateThread', 'SuspendThread', 'ResumeThread', 'TerminateProcess'
        ]
        
        import_details = pe_info.get('ImportDetails', [])
        suspicious_imports_found = []
        for imp in import_details:
            for func in imp['functions']:
                if func in suspicious_apis:
                    suspicious_imports_found.append(f"{imp['dll']}:{func}")
        
        if len(suspicious_imports_found) > 5:
            indicators['suspicious_imports'] = True
            indicators_found.append(f"Multiple suspicious API calls detected ({len(suspicious_imports_found)})")
            risk_score += 25
            indicators['suspicious_imports_list'] = suspicious_imports_found
        
        # Check section characteristics
        sections_nb = pe_info.get('SectionsNb', 0)
        if sections_nb < 3 or sections_nb > 10:
            indicators['suspicious_sections'] = True
            indicators_found.append(f"Unusual number of sections ({sections_nb})")
            risk_score += 15
        
        # Check for executable sections with write permissions
        sections = pe_info.get('sections', [])
        for section in sections:
            characteristics = section.get('characteristics', 0)
            # IMAGE_SCN_MEM_EXECUTE (0x20000000) and IMAGE_SCN_MEM_WRITE (0x80000000)
            if (characteristics & 0x20000000) and (characteristics & 0x80000000):
                indicators_found.append(f"Section {section['name']} has execute and write permissions")
                risk_score += 10
        
        # Check file characteristics
        characteristics = pe_info.get('Characteristics', 0)
        if characteristics & 0x2000:  # DLL
            risk_score += 5
        
        # Check subsystem
        subsystem = pe_info.get('Subsystem', 0)
        if subsystem == 1:  # Native
            indicators_found.append("Native subsystem (unusual for user applications)")
            risk_score += 15
        
        # Check for packed indicators
        entry_point = pe_info.get('AddressOfEntryPoint', 0)
        if entry_point > 0:
            for section in sections:
                if (section['virtual_address'] <= entry_point < 
                    section['virtual_address'] + section['virtual_size']):
                    if section['entropy'] > 7.5:
                        indicators_found.append(f"Entry point in high-entropy section ({section['name']})")
                        risk_score += 20
                    break
        
        # Check for suspicious DLL characteristics
        dll_chars = pe_info.get('DllCharacteristics', 0)
        if not (dll_chars & 0x0040):  # No ASLR
            indicators_found.append("ASLR not enabled")
            risk_score += 10
        if not (dll_chars & 0x0100):  # No DEP
            indicators_found.append("DEP/NX not enabled")
            risk_score += 10
        
        # Check timestamps
        timestamp = pe_info.get('TimeDateStamp', 0)
        if timestamp == 0:
            indicators_found.append("Invalid/zero timestamp")
            risk_score += 10
        
        # Set risk level
        indicators['risk_score'] = min(risk_score, 100)
        indicators['indicators_found'] = indicators_found
        
        if indicators['risk_score'] >= 70:
            indicators['risk_level'] = 'HIGH'
        elif indicators['risk_score'] >= 40:
            indicators['risk_level'] = 'MEDIUM'
        else:
            indicators['risk_level'] = 'LOW'
        
        return indicators

    async def detect_file_type_with_magika(self, file_path: Path) -> Dict[str, Any]:
        """Use Magika for AI-powered file type detection."""
        try:
            from magika import Magika
            
            magika = Magika()
            result = magika.identify_path(file_path)
            
            return {
                'detected_type': result.output.ct_label,
                'mime_type': result.output.mime_type,
                'confidence': result.output.score,
                'is_binary': result.output.is_text is False,
                'description': f"{result.output.ct_label} file"
            }
        except ImportError:
            logger.warning("Magika not available, using basic detection")
            return {
                'detected_type': 'executable',
                'mime_type': 'application/x-executable',
                'confidence': 0.5,
                'is_binary': True,
                'description': 'Executable file (basic detection)'
            }
        except Exception as e:
            logger.error(f"Error with Magika detection: {e}")
            return {
                'detected_type': 'unknown',
                'mime_type': 'application/octet-stream',
                'confidence': 0.0,
                'is_binary': True,
                'description': f'Error: {e}'
            }

    async def analyze_context_with_langextract(self, prompt: str) -> Dict[str, Any]:
        """Use langextract to analyze the prompt context."""
        try:
            from core.task_detector import task_detector
            
            detection = task_detector.detect_task_type(prompt)
            
            return {
                'task_type': detection.task_type,
                'language': detection.language,
                'confidence': detection.confidence,
                'context': detection.context,
                'intent': self._determine_security_intent(prompt, detection.task_type)
            }
        except Exception as e:
            logger.error(f"Error with langextract: {e}")
            return {
                'task_type': 'malware-detection',
                'language': 'en',
                'confidence': 0.5,
                'context': prompt,
                'intent': self._determine_security_intent(prompt, 'malware-detection')
            }

    def _determine_security_intent(self, prompt: str, task_type: str) -> str:
        """Determine security analysis intent from prompt."""
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ['malicious', 'malware', 'virus', 'trojan', 'threat']):
            return 'malware_detection'
        elif any(word in prompt_lower for word in ['safe', 'clean', 'legitimate', 'benign']):
            return 'safety_verification'
        elif any(word in prompt_lower for word in ['analyze', 'examine', 'inspect', 'check']):
            return 'general_analysis'
        elif any(word in prompt_lower for word in ['suspicious', 'unknown', 'strange']):
            return 'suspicious_analysis'
        else:
            return 'comprehensive_analysis'

    async def get_best_malware_models(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get best malware detection models from database based on context."""
        try:
            import sqlite3
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Map intent to specific model types
                intent = context.get('intent', 'malware_detection')
                
                if intent == 'malware_detection':
                    pipeline_tags = ['text-classification', 'zero-shot-classification']
                    keywords = ['malware', 'virus', 'security', 'threat']
                elif intent == 'safety_verification':
                    pipeline_tags = ['text-classification', 'sentiment-analysis']
                    keywords = ['safety', 'clean', 'security']
                else:
                    pipeline_tags = ['text-classification', 'zero-shot-classification']
                    keywords = ['security', 'analysis', 'detection']
                
                # Query for relevant models
                placeholders = ','.join(['?' for _ in pipeline_tags])
                query = f"""
                    SELECT model_id, pipeline_tag, downloads, likes, decision_score, 
                           capability_score, efficiency_score, popularity_score, description
                    FROM models 
                    WHERE pipeline_tag IN ({placeholders})
                    AND downloads > 50
                    AND model_id NOT LIKE '%nsfw%'
                    AND model_id NOT LIKE '%adult%'
                    ORDER BY decision_score DESC, downloads DESC, likes DESC
                    LIMIT 5
                """
                
                cursor.execute(query, pipeline_tags)
                rows = cursor.fetchall()
                
                models = []
                for row in rows:
                    model = {
                        'model_id': row[0],
                        'pipeline_tag': row[1],
                        'downloads': row[2],
                        'likes': row[3],
                        'decision_score': row[4] or 0.0,
                        'capability_score': row[5] or 0.0,
                        'efficiency_score': row[6] or 0.0,
                        'popularity_score': row[7] or 0.0,
                        'description': row[8] or ''
                    }
                    models.append(model)
                
                return models
                
        except Exception as e:
            logger.error(f"Error querying database for models: {e}")
            return []

    async def run_ai_malware_analysis(self, pe_info: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Run AI-powered malware analysis using selected models."""
        try:
            # Get best models for this analysis
            models = await self.get_best_malware_models(context)
            
            if not models:
                return {
                    'ai_analysis_available': False,
                    'error': 'No suitable AI models found in database'
                }
            
            selected_model = models[0]
            
            # Prepare analysis text from PE info
            analysis_text = self._prepare_analysis_text(pe_info, context)
            
            # Try to run analysis with the selected model
            try:
                from core.orchestrator import HuggingFaceOrchestrator
                from core.providers import ModelConfig
                
                orchestrator = HuggingFaceOrchestrator(budget=5.0, verbose=False)
                
                model_config = ModelConfig(
                    name=f"malware_analysis_{selected_model['model_id']}",
                    api_provider="huggingface",
                    model_id=selected_model['model_id'],
                    max_tokens=500,
                    temperature=0.1
                )
                
                result = await orchestrator.process_task_with_model(
                    analysis_text, 
                    selected_model['model_id'], 
                    'malware-detection'
                )
                
                return {
                    'ai_analysis_available': True,
                    'model_used': selected_model['model_id'],
                    'model_score': selected_model['decision_score'],
                    'analysis_result': result.content if result.success else 'Analysis failed',
                    'success': result.success,
                    'alternative_models': [m['model_id'] for m in models[1:3]],
                    'context_intent': context.get('intent', 'unknown')
                }
                
            except Exception as e:
                logger.error(f"Error running AI analysis: {e}")
                return {
                    'ai_analysis_available': True,
                    'model_used': selected_model['model_id'],
                    'model_score': selected_model['decision_score'],
                    'analysis_result': f'AI analysis failed: {e}',
                    'success': False,
                    'fallback_used': True
                }
                
        except Exception as e:
            logger.error(f"Error in AI malware analysis: {e}")
            return {
                'ai_analysis_available': False,
                'error': str(e)
            }

    def _prepare_analysis_text(self, pe_info: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Prepare text for AI analysis based on PE info and context."""
        intent = context.get('intent', 'malware_detection')
        
        # Build analysis prompt based on intent
        if intent == 'malware_detection':
            prompt = "Analyze this PE file for malware indicators. "
        elif intent == 'safety_verification':
            prompt = "Verify if this PE file appears safe and legitimate. "
        else:
            prompt = "Perform a comprehensive security analysis of this PE file. "
        
        # Add key PE characteristics
        characteristics = []
        
        # File basic info
        characteristics.append(f"File size: {pe_info.get('file_size', 0)} bytes")
        characteristics.append(f"Sections: {pe_info.get('SectionsNb', 0)}")
        characteristics.append(f"Mean entropy: {pe_info.get('SectionsMeanEntropy', 0):.2f}")
        
        # Imports
        characteristics.append(f"Imported DLLs: {pe_info.get('ImportsNbDLL', 0)}")
        characteristics.append(f"Imported functions: {pe_info.get('ImportsNb', 0)}")
        
        # Resources
        characteristics.append(f"Resources: {pe_info.get('ResourcesNb', 0)}")
        
        # Add suspicious imports if any
        import_details = pe_info.get('ImportDetails', [])
        suspicious_dlls = []
        for imp in import_details[:5]:  # Top 5 DLLs
            suspicious_dlls.append(imp['dll'])
        
        if suspicious_dlls:
            characteristics.append(f"Key DLLs: {', '.join(suspicious_dlls)}")
        
        # Combine prompt with characteristics
        analysis_text = prompt + "File characteristics: " + "; ".join(characteristics)
        
        # Add specific question based on context
        if 'malicious' in context.get('context', '').lower():
            analysis_text += ". Is this file malicious or safe?"
        elif 'safe' in context.get('context', '').lower():
            analysis_text += ". Confirm if this file is safe to execute."
        else:
            analysis_text += ". Provide a security assessment."
        
        return analysis_text

    async def analyze_pe_file(self, file_path: Path, prompt: str = "") -> PEAnalysisResult:
        """Main method to analyze PE file with AI integration."""
        try:
            logger.info(f"🔍 Starting enhanced PE analysis for: {file_path}")
            
            # Step 1: Detect file type with Magika
            print("[MAGIKA] Detecting file type with AI...")
            file_type_info = await self.detect_file_type_with_magika(file_path)
            print(f"[MAGIKA] Detected: {file_type_info['detected_type']} "
                  f"(confidence: {file_type_info['confidence']:.2f})")
            
            # Step 2: Analyze prompt context with langextract
            ai_context = {}
            if prompt:
                print("[LANGEXTRACT] Analyzing prompt context...")
                ai_context = await self.analyze_context_with_langextract(prompt)
                print(f"[LANGEXTRACT] Intent: {ai_context['intent']} "
                      f"(task: {ai_context['task_type']})")
            
            # Step 3: Extract PE information
            print("[PE] Extracting PE headers and metadata...")
            pe_info = self.extract_pe_info(file_path)
            
            if not pe_info.get('is_pe', False):
                return PEAnalysisResult(
                    success=False,
                    pe_info=pe_info,
                    malware_analysis={},
                    ai_context=ai_context,
                    file_type_info=file_type_info,
                    error_message=pe_info.get('error', 'Not a valid PE file')
                )
            
            # Step 4: Static malware analysis
            print("[ANALYSIS] Performing static malware analysis...")
            malware_analysis = self.analyze_malware_indicators(pe_info)
            
            # Step 5: AI-powered analysis using database models
            if prompt and ai_context:
                print("[AI] Running database-driven AI analysis...")
                ai_analysis = await self.run_ai_malware_analysis(pe_info, ai_context)
                malware_analysis['ai_analysis'] = ai_analysis
            
            return PEAnalysisResult(
                success=True,
                pe_info=pe_info,
                malware_analysis=malware_analysis,
                ai_context=ai_context,
                file_type_info=file_type_info
            )
            
        except Exception as e:
            logger.error(f"Error in PE analysis: {e}")
            return PEAnalysisResult(
                success=False,
                pe_info={},
                malware_analysis={},
                ai_context={},
                file_type_info={},
                error_message=str(e)
            )

    def format_analysis_report(self, result: PEAnalysisResult) -> str:
        """Format comprehensive analysis report."""
        if not result.success:
            return f"❌ Analysis Error: {result.error_message}"
        
        pe_info = result.pe_info
        malware_analysis = result.malware_analysis
        ai_context = result.ai_context
        file_type_info = result.file_type_info
        
        output = []
        output.append("=" * 70)
        output.append("🔍 ENHANCED PE FILE ANALYSIS REPORT")
        output.append("=" * 70)
        
        # File detection info
        output.append("📁 FILE DETECTION (MAGIKA)")
        output.append(f"   Type: {file_type_info.get('detected_type', 'unknown')}")
        output.append(f"   MIME: {file_type_info.get('mime_type', 'unknown')}")
        output.append(f"   Confidence: {file_type_info.get('confidence', 0):.2f}")
        output.append(f"   Binary: {file_type_info.get('is_binary', 'unknown')}")
        
        # Context analysis
        if ai_context:
            output.append("\n🧠 CONTEXT ANALYSIS (LANGEXTRACT)")
            output.append(f"   Intent: {ai_context.get('intent', 'unknown')}")
            output.append(f"   Task Type: {ai_context.get('task_type', 'unknown')}")
            output.append(f"   Language: {ai_context.get('language', 'unknown')}")
            output.append(f"   Confidence: {ai_context.get('confidence', 0):.2f}")
        
        # Basic PE info
        output.append("\n📋 PE FILE INFORMATION")
        output.append(f"   File: {pe_info['file_path']}")
        output.append(f"   Size: {pe_info['file_size']:,} bytes")
        output.append(f"   Machine: 0x{pe_info['Machine']:04X}")
        output.append(f"   Timestamp: {pe_info['TimeDateStamp']}")
        output.append(f"   Subsystem: {pe_info['Subsystem']}")
        
        # Sections analysis
        output.append(f"\n📦 SECTIONS ANALYSIS")
        output.append(f"   Count: {pe_info['SectionsNb']}")
        output.append(f"   Mean Entropy: {pe_info['SectionsMeanEntropy']:.2f}")
        output.append(f"   Entropy Range: {pe_info['SectionsMinEntropy']:.2f} - {pe_info['SectionsMaxEntropy']:.2f}")
        
        # Show section details
        sections = pe_info.get('sections', [])
        if sections:
            output.append("   Section Details:")
            for section in sections[:5]:  # Show first 5
                output.append(f"     {section['name']}: "
                            f"VA=0x{section['virtual_address']:08X}, "
                            f"Size={section['raw_size']:,}, "
                            f"Entropy={section['entropy']:.2f}")
        
        # Imports analysis
        output.append(f"\n🔗 IMPORTS ANALYSIS")
        output.append(f"   DLLs: {pe_info['ImportsNbDLL']}")
        output.append(f"   Functions: {pe_info['ImportsNb']}")
        output.append(f"   Ordinal Imports: {pe_info['ImportsNbOrdinal']}")
        
        # Show top DLLs
        import_details = pe_info.get('ImportDetails', [])
        if import_details:
            output.append("   Top DLLs:")
            for imp in import_details[:5]:
                output.append(f"     {imp['dll']}: {len(imp['functions'])} functions")
        
        # Resources
        output.append(f"\n📚 RESOURCES")
        output.append(f"   Count: {pe_info['ResourcesNb']}")
        if pe_info['ResourcesNb'] > 0:
            output.append(f"   Mean Entropy: {pe_info['ResourcesMeanEntropy']:.2f}")
            output.append(f"   Mean Size: {pe_info['ResourcesMeanSize']:,} bytes")
        
        # Static malware analysis
        output.append(f"\n🔒 STATIC MALWARE ANALYSIS")
        output.append(f"   Risk Score: {malware_analysis['risk_score']}/100")
        output.append(f"   Risk Level: {malware_analysis['risk_level']}")
        
        indicators_found = malware_analysis.get('indicators_found', [])
        if indicators_found:
            output.append("   Indicators Found:")
            for indicator in indicators_found:
                output.append(f"     ⚠️  {indicator}")
        
        # Suspicious imports
        if malware_analysis.get('suspicious_imports_list'):
            output.append("   Suspicious APIs (first 10):")
            for api in malware_analysis['suspicious_imports_list'][:10]:
                output.append(f"     🚨 {api}")
        
        # AI Analysis results
        ai_analysis = malware_analysis.get('ai_analysis', {})
        if ai_analysis.get('ai_analysis_available'):
            output.append(f"\n🤖 AI ANALYSIS (DATABASE-DRIVEN)")
            output.append(f"   Model Used: {ai_analysis.get('model_used', 'unknown')}")
            output.append(f"   Model Score: {ai_analysis.get('model_score', 0):.2f}")
            output.append(f"   Success: {ai_analysis.get('success', False)}")
            
            if ai_analysis.get('alternative_models'):
                alt_models = ', '.join(ai_analysis['alternative_models'])
                output.append(f"   Alternative Models: {alt_models}")
            
            ai_result = ai_analysis.get('analysis_result', '')
            if ai_result:
                output.append("   AI Assessment:")
                # Split long AI responses into lines
                for line in ai_result.split('\n'):
                    if line.strip():
                        output.append(f"     {line.strip()}")
        
        # Final assessment (combining static analysis and AI results)
        output.append(f"\n🎯 FINAL ASSESSMENT")
        
        # Get AI assessment
        ai_analysis = malware_analysis.get('ai_analysis', {})
        ai_result = ai_analysis.get('analysis_result', '').lower()
        ai_indicates_malicious = any(word in ai_result for word in ['malicious', 'malware', 'threat', 'dangerous', 'suspicious'])
        ai_indicates_safe = any(word in ai_result for word in ['safe', 'clean', 'benign', 'legitimate'])
        
        # Combine static score with AI assessment
        final_risk_score = malware_analysis['risk_score']
        
        # Adjust risk based on AI analysis
        if ai_analysis.get('success') and ai_indicates_malicious:
            final_risk_score = max(final_risk_score, 70)  # AI detected malicious -> High risk
            output.append("   🤖 AI MODEL ALERT: Malicious behavior detected")
        elif ai_analysis.get('success') and ai_indicates_safe:
            final_risk_score = min(final_risk_score, 30)  # AI says safe -> Lower risk
            output.append("   🤖 AI MODEL: File appears safe")
        
        # Final risk determination
        if final_risk_score >= 70 or ai_indicates_malicious:
            output.append("   🚨 HIGH RISK - File appears potentially malicious")
            output.append("   Recommendation: DO NOT EXECUTE - Submit for detailed analysis")
            if ai_indicates_malicious:
                output.append("   ⚠️  AI model specifically flagged this file as malicious")
        elif final_risk_score >= 40:
            output.append("   ⚠️  MEDIUM RISK - File shows suspicious characteristics")
            output.append("   Recommendation: Exercise caution - Additional analysis recommended")
        else:
            output.append("   ✅ LOW RISK - File appears relatively benign")
            output.append("   Recommendation: Standard precautions apply")
            if ai_indicates_safe:
                output.append("   ✅ AI model confirms file appears safe")
        
        output.append("=" * 70)
        
        return "\n".join(output)

# Create global instance
enhanced_pe_analyzer = EnhancedPEAnalyzer()