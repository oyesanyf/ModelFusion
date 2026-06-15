#!/usr/bin/env python3
"""
Focused PE Header Extractor for Malware Analysis
Extracts specific PE header fields for malware detection
"""

import pefile
import os
import hashlib
import array
import math
from pathlib import Path
from typing import Dict, Any, Optional
import json

class FocusedPEExtractor:
    """Extract specific PE header fields for malware analysis."""
    
    def __init__(self):
        self.suspicious_apis = {
            'VirtualAlloc', 'VirtualAllocEx', 'CreateRemoteThread', 'WriteProcessMemory',
            'ReadProcessMemory', 'OpenProcess', 'CreateProcess', 'ShellExecute',
            'WinExec', 'system', 'CreateFile', 'WriteFile', 'ReadFile',
            'RegCreateKey', 'RegSetValue', 'InternetOpen', 'HttpOpenRequest',
            'URLDownloadToFile', 'GetProcAddress', 'LoadLibrary', 'GetModuleHandle'
        }
    
    def get_entropy(self, data: bytes) -> float:
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
                entropy -= p_x * math.log(p_x, 2)
        
        return entropy
    
    def get_file_hash(self, file_path: str) -> Dict[str, str]:
        """Calculate MD5, SHA1, and SHA256 hashes of file."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            return {
                'md5': hashlib.md5(data).hexdigest(),
                'sha1': hashlib.sha1(data).hexdigest(),
                'sha256': hashlib.sha256(data).hexdigest()
            }
        except Exception as e:
            return {'md5': '', 'sha1': '', 'sha256': str(e)}
    
    def extract_pe_headers(self, file_path: str) -> Dict[str, Any]:
        """Extract focused PE header information."""
        try:
            pe = pefile.PE(file_path)
            
            # Get file hashes
            file_hashes = self.get_file_hash(file_path)
            
            # Basic PE information
            pe_info = {
                'id': os.path.basename(file_path),
                'md5': file_hashes['md5'],
                'Machine': pe.FILE_HEADER.Machine,
                'SizeOfOptionalHeader': pe.FILE_HEADER.SizeOfOptionalHeader,
                'Characteristics': pe.FILE_HEADER.Characteristics,
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
            
            # Handle BaseOfData (32-bit only)
            try:
                pe_info['BaseOfData'] = pe.OPTIONAL_HEADER.BaseOfData
            except AttributeError:
                pe_info['BaseOfData'] = 0
            
            # Section analysis
            sections = pe.sections
            pe_info['SectionsNb'] = len(sections)
            
            if sections:
                entropy_values = [section.get_entropy() for section in sections]
                raw_sizes = [section.SizeOfRawData for section in sections]
                virtual_sizes = [section.Misc_VirtualSize for section in sections]
                
                pe_info['SectionsMeanEntropy'] = sum(entropy_values) / len(entropy_values)
                pe_info['SectionsMinEntropy'] = min(entropy_values)
                pe_info['SectionsMaxEntropy'] = max(entropy_values)
                pe_info['SectionsMeanRawsize'] = sum(raw_sizes) / len(raw_sizes)
                pe_info['SectionsMinRawsize'] = min(raw_sizes)
                pe_info['SectionMaxRawsize'] = max(raw_sizes)
                pe_info['SectionsMeanVirtualsize'] = sum(virtual_sizes) / len(virtual_sizes)
                pe_info['SectionsMinVirtualsize'] = min(virtual_sizes)
                pe_info['SectionMaxVirtualsize'] = max(virtual_sizes)
            else:
                pe_info['SectionsMeanEntropy'] = 0
                pe_info['SectionsMinEntropy'] = 0
                pe_info['SectionsMaxEntropy'] = 0
                pe_info['SectionsMeanRawsize'] = 0
                pe_info['SectionsMinRawsize'] = 0
                pe_info['SectionMaxRawsize'] = 0
                pe_info['SectionsMeanVirtualsize'] = 0
                pe_info['SectionsMinVirtualsize'] = 0
                pe_info['SectionMaxVirtualsize'] = 0
            
            # Import analysis
            try:
                pe_info['ImportsNbDLL'] = len(pe.DIRECTORY_ENTRY_IMPORT)
                imports = sum([x.imports for x in pe.DIRECTORY_ENTRY_IMPORT], [])
                pe_info['ImportsNb'] = len(imports)
                pe_info['ImportsNbOrdinal'] = len([x for x in imports if x.name is None])
            except AttributeError:
                pe_info['ImportsNbDLL'] = 0
                pe_info['ImportsNb'] = 0
                pe_info['ImportsNbOrdinal'] = 0
            
            # Export analysis
            try:
                pe_info['ExportNb'] = len(pe.DIRECTORY_ENTRY_EXPORT.symbols)
            except AttributeError:
                pe_info['ExportNb'] = 0
            
            # Resource analysis
            resources = self.get_resources(pe)
            pe_info['ResourcesNb'] = len(resources)
            
            if resources:
                entropy_values = [r[0] for r in resources]
                sizes = [r[1] for r in resources]
                pe_info['ResourcesMeanEntropy'] = sum(entropy_values) / len(entropy_values)
                pe_info['ResourcesMinEntropy'] = min(entropy_values)
                pe_info['ResourcesMaxEntropy'] = max(entropy_values)
                pe_info['ResourcesMeanSize'] = sum(sizes) / len(sizes)
                pe_info['ResourcesMinSize'] = min(sizes)
                pe_info['ResourcesMaxSize'] = max(sizes)
            else:
                pe_info['ResourcesMeanEntropy'] = 0
                pe_info['ResourcesMinEntropy'] = 0
                pe_info['ResourcesMaxEntropy'] = 0
                pe_info['ResourcesMeanSize'] = 0
                pe_info['ResourcesMinSize'] = 0
                pe_info['ResourcesMaxSize'] = 0
            
            # Load configuration size
            try:
                pe_info['LoadConfigurationSize'] = pe.DIRECTORY_ENTRY_LOAD_CONFIG.struct.Size
            except AttributeError:
                pe_info['LoadConfigurationSize'] = 0
            
            # Version information size
            try:
                version_infos = self.get_version_info(pe)
                pe_info['VersionInformationSize'] = len(version_infos.keys())
            except AttributeError:
                pe_info['VersionInformationSize'] = 0
            
            pe.close()
            return pe_info
            
        except Exception as e:
            return {
                'id': os.path.basename(file_path),
                'error': str(e),
                'md5': self.get_file_hash(file_path)['md5']
            }
    
    def get_resources(self, pe) -> list:
        """Extract resources with entropy and size."""
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
            except Exception:
                pass
        return resources
    
    def get_version_info(self, pe) -> dict:
        """Extract version information."""
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
        except Exception:
            pass
        return res
    
    def format_pe_headers(self, pe_info: Dict[str, Any]) -> str:
        """Format PE headers as a table."""
        if 'error' in pe_info:
            return f"❌ PE Analysis Error: {pe_info['error']}"
        
        output = "🔍 PE HEADER ANALYSIS\n"
        output += "=" * 50 + "\n"
        output += f"File: {pe_info['id']}\n"
        output += f"MD5: {pe_info['md5']}\n\n"
        
        # Basic info
        output += "📋 BASIC INFORMATION:\n"
        output += f"  Machine: {pe_info['Machine']}\n"
        output += f"  Characteristics: {pe_info['Characteristics']}\n"
        output += f"  Subsystem: {pe_info['Subsystem']}\n"
        output += f"  DllCharacteristics: {pe_info['DllCharacteristics']}\n\n"
        
        # Sizes
        output += "📏 SIZE INFORMATION:\n"
        output += f"  SizeOfCode: {pe_info['SizeOfCode']:,}\n"
        output += f"  SizeOfInitializedData: {pe_info['SizeOfInitializedData']:,}\n"
        output += f"  SizeOfUninitializedData: {pe_info['SizeOfUninitializedData']:,}\n"
        output += f"  SizeOfImage: {pe_info['SizeOfImage']:,}\n"
        output += f"  SizeOfHeaders: {pe_info['SizeOfHeaders']:,}\n\n"
        
        # Sections
        output += "📦 SECTION ANALYSIS:\n"
        output += f"  Number of Sections: {pe_info['SectionsNb']}\n"
        output += f"  Mean Entropy: {pe_info['SectionsMeanEntropy']:.2f}\n"
        output += f"  Min Entropy: {pe_info['SectionsMinEntropy']:.2f}\n"
        output += f"  Max Entropy: {pe_info['SectionsMaxEntropy']:.2f}\n\n"
        
        # Imports/Exports
        output += "🔗 IMPORTS/EXPORTS:\n"
        output += f"  Import DLLs: {pe_info['ImportsNbDLL']}\n"
        output += f"  Import Functions: {pe_info['ImportsNb']}\n"
        output += f"  Export Functions: {pe_info['ExportNb']}\n\n"
        
        # Resources
        output += "📚 RESOURCES:\n"
        output += f"  Number of Resources: {pe_info['ResourcesNb']}\n"
        if pe_info['ResourcesNb'] > 0:
            output += f"  Mean Resource Entropy: {pe_info['ResourcesMeanEntropy']:.2f}\n"
            output += f"  Mean Resource Size: {pe_info['ResourcesMeanSize']:,}\n\n"
        
        return output

def main():
    """Test the PE header extractor."""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python focused_pe_extractor.py <pe_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found")
        sys.exit(1)
    
    extractor = FocusedPEExtractor()
    pe_info = extractor.extract_pe_headers(file_path)
    
    print(extractor.format_pe_headers(pe_info))
    
    # Also save as JSON
    output_file = f"{os.path.splitext(file_path)[0]}_pe_headers.json"
    with open(output_file, 'w') as f:
        json.dump(pe_info, f, indent=2)
    print(f"\n💾 PE headers saved to: {output_file}")

if __name__ == "__main__":
    main() 