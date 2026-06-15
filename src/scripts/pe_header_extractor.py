#!/usr/bin/env python3
"""
PE File Header Extractor for Malware Analysis
Extracts comprehensive PE header information from executable files for security analysis
"""

import pefile
import os
import array
import math
import sys
import argparse
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import hashlib
from datetime import datetime

class PEHeaderExtractor:
    """Extract and analyze PE file headers for malware detection."""
    
    def __init__(self):
        self.suspicious_apis = {
            'VirtualAlloc', 'VirtualAllocEx', 'CreateRemoteThread', 'WriteProcessMemory',
            'ReadProcessMemory', 'OpenProcess', 'CreateProcess', 'ShellExecute',
            'WinExec', 'system', 'CreateFile', 'WriteFile', 'ReadFile',
            'RegCreateKey', 'RegSetValue', 'InternetOpen', 'HttpOpenRequest',
            'URLDownloadToFile', 'GetProcAddress', 'LoadLibrary', 'GetModuleHandle'
        }
        
        self.suspicious_sections = {
            '.text', '.data', '.rdata', '.idata', '.edata', '.pdata', '.reloc',
            '.rsrc', '.bss', '.crt', '.tls', '.debug', '.drectve', '.sdata',
            '.sdata2', '.srdata', '.xdata', '.pdata', '.idata$2', '.idata$3',
            '.idata$4', '.idata$5', '.idata$6', '.idata$7', '.edata', '.didat',
            '.00cfg', '.00cfg$01', '.00cfg$02', '.00cfg$03', '.00cfg$04',
            '.00cfg$05', '.00cfg$06', '.00cfg$07', '.00cfg$08', '.00cfg$09'
        }
    
    def get_entropy(self, data: bytes) -> float:
        """Calculate Shannon entropy of data."""
        if len(data) == 0:
            return 0.0
        
        # Count byte frequencies
        occurrences = array.array('L', [0] * 256)
        for byte in data:
            occurrences[byte] += 1
        
        # Calculate entropy
        entropy = 0
        data_len = len(data)
        for count in occurrences:
            if count > 0:
                p_x = float(count) / data_len
                entropy -= p_x * math.log(p_x, 2)
        
        return entropy
    
    def get_file_hash(self, file_path: str) -> Dict[str, str]:
        """Calculate various hashes of the file."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            return {
                'md5': hashlib.md5(data).hexdigest(),
                'sha1': hashlib.sha1(data).hexdigest(),
                'sha256': hashlib.sha256(data).hexdigest()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_resources(self, pe) -> List[Dict[str, Any]]:
        """Extract resource information."""
        resources = []
        if hasattr(pe, 'DIRECTORY_ENTRY_RESOURCE'):
            try:
                for resource_type in pe.DIRECTORY_ENTRY_RESOURCE.entries:
                    if hasattr(resource_type, 'directory'):
                        for resource_id in resource_type.directory.entries:
                            if hasattr(resource_id, 'directory'):
                                for resource_lang in resource_id.directory.entries:
                                    try:
                                        data = pe.get_data(
                                            resource_lang.data.struct.OffsetToData,
                                            resource_lang.data.struct.Size
                                        )
                                        size = resource_lang.data.struct.Size
                                        entropy = self.get_entropy(data)
                                        
                                        resources.append({
                                            'type': str(resource_type.name) if resource_type.name else str(resource_type.id),
                                            'id': str(resource_id.name) if resource_id.name else str(resource_id.id),
                                            'language': str(resource_lang.name) if resource_lang.name else str(resource_lang.id),
                                            'size': size,
                                            'entropy': entropy,
                                            'offset': resource_lang.data.struct.OffsetToData
                                        })
                                    except Exception as e:
                                        continue
            except Exception as e:
                pass
        return resources
    
    def get_version_info(self, pe) -> Dict[str, Any]:
        """Extract version information."""
        version_info = {}
        
        try:
            if hasattr(pe, 'FileInfo'):
                for fileinfo in pe.FileInfo:
                    if fileinfo.Key == 'StringFileInfo':
                        for st in fileinfo.StringTable:
                            for entry in st.entries.items():
                                version_info[entry[0]] = entry[1]
                    elif fileinfo.Key == 'VarFileInfo':
                        for var in fileinfo.Var:
                            for entry in var.entry.items():
                                version_info[entry[0]] = entry[1]
            
            if hasattr(pe, 'VS_FIXEDFILEINFO'):
                version_info.update({
                    'flags': pe.VS_FIXEDFILEINFO.FileFlags,
                    'os': pe.VS_FIXEDFILEINFO.FileOS,
                    'type': pe.VS_FIXEDFILEINFO.FileType,
                    'file_version': pe.VS_FIXEDFILEINFO.FileVersionLS,
                    'product_version': pe.VS_FIXEDFILEINFO.ProductVersionLS,
                    'signature': pe.VS_FIXEDFILEINFO.Signature,
                    'struct_version': pe.VS_FIXEDFILEINFO.StrucVersion
                })
        except Exception as e:
            version_info['error'] = str(e)
        
        return version_info
    
    def analyze_sections(self, pe) -> Dict[str, Any]:
        """Analyze PE sections for suspicious characteristics."""
        sections_info = {
            'count': len(pe.sections),
            'sections': [],
            'total_size': 0,
            'high_entropy_sections': 0,
            'suspicious_sections': 0
        }
        
        for section in pe.sections:
            try:
                section_data = section.get_data()
                entropy = self.get_entropy(section_data)
                size = section.SizeOfRawData
                
                section_info = {
                    'name': section.Name.decode('utf-8', errors='ignore').rstrip('\x00'),
                    'virtual_address': section.VirtualAddress,
                    'virtual_size': section.Misc_VirtualSize,
                    'raw_size': size,
                    'entropy': entropy,
                    'characteristics': section.Characteristics,
                    'is_executable': bool(section.Characteristics & 0x20000000),  # IMAGE_SCN_MEM_EXECUTE
                    'is_writable': bool(section.Characteristics & 0x80000000),    # IMAGE_SCN_MEM_WRITE
                    'is_readable': bool(section.Characteristics & 0x40000000),   # IMAGE_SCN_MEM_READ
                }
                
                # Check for suspicious characteristics
                if entropy > 7.0:  # High entropy often indicates packed/encrypted code
                    section_info['high_entropy'] = True
                    sections_info['high_entropy_sections'] += 1
                
                if section_info['name'] in self.suspicious_sections:
                    section_info['suspicious_name'] = True
                    sections_info['suspicious_sections'] += 1
                
                sections_info['sections'].append(section_info)
                sections_info['total_size'] += size
                
            except Exception as e:
                section_info = {
                    'name': 'ERROR',
                    'error': str(e)
                }
                sections_info['sections'].append(section_info)
        
        return sections_info
    
    def analyze_imports(self, pe) -> Dict[str, Any]:
        """Analyze imported functions for suspicious APIs."""
        imports_info = {
            'dlls': [],
            'total_imports': 0,
            'suspicious_imports': [],
            'suspicious_dlls': []
        }
        
        try:
            if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
                for dll_entry in pe.DIRECTORY_ENTRY_IMPORT:
                    dll_name = dll_entry.dll.decode('utf-8', errors='ignore')
                    dll_imports = []
                    suspicious_count = 0
                    
                    for import_entry in dll_entry.imports:
                        if import_entry.name:
                            func_name = import_entry.name.decode('utf-8', errors='ignore')
                            dll_imports.append(func_name)
                            imports_info['total_imports'] += 1
                            
                            if func_name in self.suspicious_apis:
                                imports_info['suspicious_imports'].append({
                                    'dll': dll_name,
                                    'function': func_name
                                })
                                suspicious_count += 1
                    
                    dll_info = {
                        'name': dll_name,
                        'imports': dll_imports,
                        'import_count': len(dll_imports),
                        'suspicious_count': suspicious_count
                    }
                    
                    imports_info['dlls'].append(dll_info)
                    
                    # Check for suspicious DLLs
                    suspicious_dlls = ['kernel32.dll', 'user32.dll', 'advapi32.dll', 
                                     'ws2_32.dll', 'wininet.dll', 'urlmon.dll']
                    if dll_name.lower() in suspicious_dlls and suspicious_count > 0:
                        imports_info['suspicious_dlls'].append(dll_name)
                        
        except Exception as e:
            imports_info['error'] = str(e)
        
        return imports_info
    
    def analyze_exports(self, pe) -> Dict[str, Any]:
        """Analyze exported functions."""
        exports_info = {
            'count': 0,
            'functions': [],
            'ordinals': []
        }
        
        try:
            if hasattr(pe, 'DIRECTORY_ENTRY_EXPORT'):
                for export in pe.DIRECTORY_ENTRY_EXPORT.symbols:
                    if export.name:
                        func_name = export.name.decode('utf-8', errors='ignore')
                        exports_info['functions'].append(func_name)
                    else:
                        exports_info['ordinals'].append(export.ordinal)
                    
                    exports_info['count'] += 1
        except Exception as e:
            exports_info['error'] = str(e)
        
        return exports_info
    
    def calculate_malware_indicators(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate malware risk indicators based on PE analysis."""
        indicators = {
            'risk_score': 0,
            'high_risk_factors': [],
            'medium_risk_factors': [],
            'low_risk_factors': [],
            'overall_assessment': 'Unknown'
        }
        
        # High entropy sections (packed/encrypted code)
        if analysis['sections']['high_entropy_sections'] > 0:
            indicators['risk_score'] += 30
            indicators['high_risk_factors'].append(
                f"High entropy sections detected: {analysis['sections']['high_entropy_sections']}"
            )
        
        # Suspicious API imports
        suspicious_imports = len(analysis['imports']['suspicious_imports'])
        if suspicious_imports > 5:
            indicators['risk_score'] += 25
            indicators['high_risk_factors'].append(
                f"Many suspicious API imports: {suspicious_imports}"
            )
        elif suspicious_imports > 2:
            indicators['risk_score'] += 15
            indicators['medium_risk_factors'].append(
                f"Some suspicious API imports: {suspicious_imports}"
            )
        
        # Suspicious DLLs
        if len(analysis['imports']['suspicious_dlls']) > 2:
            indicators['risk_score'] += 20
            indicators['high_risk_factors'].append(
                f"Suspicious DLLs imported: {', '.join(analysis['imports']['suspicious_dlls'])}"
            )
        
        # Executable sections with write permissions
        writable_executable = sum(
            1 for section in analysis['sections']['sections']
            if section.get('is_executable', False) and section.get('is_writable', False)
        )
        if writable_executable > 0:
            indicators['risk_score'] += 25
            indicators['high_risk_factors'].append(
                f"Writable executable sections: {writable_executable}"
            )
        
        # Unusual section count
        section_count = analysis['sections']['count']
        if section_count < 3 or section_count > 15:
            indicators['risk_score'] += 10
            indicators['medium_risk_factors'].append(
                f"Unusual number of sections: {section_count}"
            )
        
        # No exports (common in malware)
        if analysis['exports']['count'] == 0:
            indicators['risk_score'] += 5
            indicators['low_risk_factors'].append("No exported functions")
        
        # Determine overall assessment
        if indicators['risk_score'] >= 70:
            indicators['overall_assessment'] = 'High Risk - Likely Malicious'
        elif indicators['risk_score'] >= 40:
            indicators['overall_assessment'] = 'Medium Risk - Suspicious'
        elif indicators['risk_score'] >= 20:
            indicators['overall_assessment'] = 'Low Risk - Some Concerns'
        else:
            indicators['overall_assessment'] = 'Low Risk - Appears Benign'
        
        return indicators
    
    def extract_pe_info(self, file_path: str) -> Dict[str, Any]:
        """Extract comprehensive PE information from file."""
        try:
            pe = pefile.PE(file_path)
            
            # Basic file information
            file_info = {
                'file_path': file_path,
                'file_size': os.path.getsize(file_path),
                'file_hashes': self.get_file_hash(file_path),
                'analysis_timestamp': datetime.now().isoformat(),
                'pe_info': {
                    'machine': pe.FILE_HEADER.Machine,
                    'characteristics': pe.FILE_HEADER.Characteristics,
                    'timestamp': pe.FILE_HEADER.TimeDateStamp,
                    'number_of_sections': pe.FILE_HEADER.NumberOfSections,
                    'size_of_optional_header': pe.FILE_HEADER.SizeOfOptionalHeader,
                    'magic': pe.OPTIONAL_HEADER.Magic,
                    'major_linker_version': pe.OPTIONAL_HEADER.MajorLinkerVersion,
                    'minor_linker_version': pe.OPTIONAL_HEADER.MinorLinkerVersion,
                    'size_of_code': pe.OPTIONAL_HEADER.SizeOfCode,
                    'size_of_initialized_data': pe.OPTIONAL_HEADER.SizeOfInitializedData,
                    'size_of_uninitialized_data': pe.OPTIONAL_HEADER.SizeOfUninitializedData,
                    'address_of_entry_point': pe.OPTIONAL_HEADER.AddressOfEntryPoint,
                    'base_of_code': pe.OPTIONAL_HEADER.BaseOfCode,
                    'image_base': pe.OPTIONAL_HEADER.ImageBase,
                    'section_alignment': pe.OPTIONAL_HEADER.SectionAlignment,
                    'file_alignment': pe.OPTIONAL_HEADER.FileAlignment,
                    'major_operating_system_version': pe.OPTIONAL_HEADER.MajorOperatingSystemVersion,
                    'minor_operating_system_version': pe.OPTIONAL_HEADER.MinorOperatingSystemVersion,
                    'major_image_version': pe.OPTIONAL_HEADER.MajorImageVersion,
                    'minor_image_version': pe.OPTIONAL_HEADER.MinorImageVersion,
                    'major_subsystem_version': pe.OPTIONAL_HEADER.MajorSubsystemVersion,
                    'minor_subsystem_version': pe.OPTIONAL_HEADER.MinorSubsystemVersion,
                    'size_of_image': pe.OPTIONAL_HEADER.SizeOfImage,
                    'size_of_headers': pe.OPTIONAL_HEADER.SizeOfHeaders,
                    'checksum': pe.OPTIONAL_HEADER.CheckSum,
                    'subsystem': pe.OPTIONAL_HEADER.Subsystem,
                    'dll_characteristics': pe.OPTIONAL_HEADER.DllCharacteristics,
                    'size_of_stack_reserve': pe.OPTIONAL_HEADER.SizeOfStackReserve,
                    'size_of_stack_commit': pe.OPTIONAL_HEADER.SizeOfStackCommit,
                    'size_of_heap_reserve': pe.OPTIONAL_HEADER.SizeOfHeapReserve,
                    'size_of_heap_commit': pe.OPTIONAL_HEADER.SizeOfHeapCommit,
                    'loader_flags': pe.OPTIONAL_HEADER.LoaderFlags,
                    'number_of_rva_and_sizes': pe.OPTIONAL_HEADER.NumberOfRvaAndSizes
                }
            }
            
            # Analyze sections
            file_info['sections'] = self.analyze_sections(pe)
            
            # Analyze imports
            file_info['imports'] = self.analyze_imports(pe)
            
            # Analyze exports
            file_info['exports'] = self.analyze_exports(pe)
            
            # Extract resources
            file_info['resources'] = self.get_resources(pe)
            
            # Extract version information
            file_info['version_info'] = self.get_version_info(pe)
            
            # Calculate malware indicators
            file_info['malware_indicators'] = self.calculate_malware_indicators(file_info)
            
            pe.close()
            return file_info
            
        except Exception as e:
            return {
                'file_path': file_path,
                'error': str(e),
                'analysis_timestamp': datetime.now().isoformat()
            }
    
    def format_analysis_output(self, analysis: Dict[str, Any], output_format: str = 'text') -> str:
        """Format analysis results for output."""
        if output_format == 'json':
            return json.dumps(analysis, indent=2, ensure_ascii=False)
        
        # Text format
        output = []
        output.append("=" * 80)
        output.append("PE FILE HEADER ANALYSIS")
        output.append("=" * 80)
        output.append(f"File: {analysis.get('file_path', 'Unknown')}")
        output.append(f"Analysis Time: {analysis.get('analysis_timestamp', 'Unknown')}")
        
        if 'error' in analysis:
            output.append(f"\n❌ ERROR: {analysis['error']}")
            return '\n'.join(output)
        
        # File hashes
        hashes = analysis.get('file_hashes', {})
        if 'error' not in hashes:
            output.append(f"\n📄 FILE HASHES:")
            output.append(f"  MD5:    {hashes.get('md5', 'N/A')}")
            output.append(f"  SHA1:   {hashes.get('sha1', 'N/A')}")
            output.append(f"  SHA256: {hashes.get('sha256', 'N/A')}")
        
        # Malware assessment
        indicators = analysis.get('malware_indicators', {})
        output.append(f"\n🔍 MALWARE ASSESSMENT:")
        output.append(f"  Risk Score: {indicators.get('risk_score', 0)}/100")
        output.append(f"  Assessment: {indicators.get('overall_assessment', 'Unknown')}")
        
        # High risk factors
        if indicators.get('high_risk_factors'):
            output.append(f"\n⚠️  HIGH RISK FACTORS:")
            for factor in indicators['high_risk_factors']:
                output.append(f"  • {factor}")
        
        # Medium risk factors
        if indicators.get('medium_risk_factors'):
            output.append(f"\n⚠️  MEDIUM RISK FACTORS:")
            for factor in indicators['medium_risk_factors']:
                output.append(f"  • {factor}")
        
        # Low risk factors
        if indicators.get('low_risk_factors'):
            output.append(f"\nℹ️  LOW RISK FACTORS:")
            for factor in indicators['low_risk_factors']:
                output.append(f"  • {factor}")
        
        # Sections analysis
        sections = analysis.get('sections', {})
        output.append(f"\n📦 SECTIONS ANALYSIS:")
        output.append(f"  Total Sections: {sections.get('count', 0)}")
        output.append(f"  High Entropy Sections: {sections.get('high_entropy_sections', 0)}")
        output.append(f"  Suspicious Sections: {sections.get('suspicious_sections', 0)}")
        
        # Show high entropy sections
        high_entropy_sections = [
            s for s in sections.get('sections', [])
            if s.get('high_entropy', False)
        ]
        if high_entropy_sections:
            output.append(f"\n🔒 HIGH ENTROPY SECTIONS:")
            for section in high_entropy_sections:
                output.append(f"  • {section['name']}: entropy={section['entropy']:.2f}")
        
        # Imports analysis
        imports = analysis.get('imports', {})
        output.append(f"\n📥 IMPORTS ANALYSIS:")
        output.append(f"  Total Imports: {imports.get('total_imports', 0)}")
        output.append(f"  Suspicious Imports: {len(imports.get('suspicious_imports', []))}")
        
        # Show suspicious imports
        suspicious_imports = imports.get('suspicious_imports', [])
        if suspicious_imports:
            output.append(f"\n⚠️  SUSPICIOUS IMPORTS:")
            for imp in suspicious_imports[:10]:  # Show first 10
                output.append(f"  • {imp['dll']}:{imp['function']}")
            if len(suspicious_imports) > 10:
                output.append(f"  ... and {len(suspicious_imports) - 10} more")
        
        # Exports analysis
        exports = analysis.get('exports', {})
        output.append(f"\n📤 EXPORTS ANALYSIS:")
        output.append(f"  Total Exports: {exports.get('count', 0)}")
        
        # Resources analysis
        resources = analysis.get('resources', [])
        output.append(f"\n📋 RESOURCES ANALYSIS:")
        output.append(f"  Total Resources: {len(resources)}")
        
        # High entropy resources
        high_entropy_resources = [
            r for r in resources if r.get('entropy', 0) > 7.0
        ]
        if high_entropy_resources:
            output.append(f"  High Entropy Resources: {len(high_entropy_resources)}")
        
        output.append("\n" + "=" * 80)
        return '\n'.join(output)

def main():
    """Main function for PE header extraction."""
    parser = argparse.ArgumentParser(
        description='Extract PE file headers for malware analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pe_header_extractor.py "c:\\tools\\AccessEnum.exe"
  python pe_header_extractor.py "malware.exe" --format json
  python pe_header_extractor.py "suspicious.dll" --output analysis.json
        """
    )
    
    parser.add_argument('file_path', help='Path to the PE file to analyze')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                       help='Output format (default: text)')
    parser.add_argument('--output', help='Output file path (optional)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Check if file exists
    if not os.path.exists(args.file_path):
        print(f"❌ Error: File '{args.file_path}' not found")
        return 1
    
    # Check if it's a PE file
    try:
        with open(args.file_path, 'rb') as f:
            magic = f.read(2)
        if magic != b'MZ':
            print(f"❌ Error: File '{args.file_path}' is not a valid PE file (missing MZ header)")
            return 1
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return 1
    
    # Extract PE information
    extractor = PEHeaderExtractor()
    analysis = extractor.extract_pe_info(args.file_path)
    
    # Format output
    if args.format == 'json':
        output = json.dumps(analysis, indent=2, ensure_ascii=False)
    else:
        output = extractor.format_analysis_output(analysis, 'text')
    
    # Output results
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"✅ Analysis saved to: {args.output}")
        except Exception as e:
            print(f"❌ Error saving output: {e}")
            print(output)
    else:
        print(output)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 