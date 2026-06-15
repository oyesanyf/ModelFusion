"""
Complete PE Header Extractor for binary analysis.

This module provides comprehensive PE header extraction capabilities for
analyzing Windows executable files and detecting potential malware.
"""

import pefile
import os
import hashlib
import array
import math
import struct
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import sys


class CompletePEHeaderExtractor:
    """Extract ALL PE header fields comprehensively."""
    
    def __init__(self):
        self.suspicious_apis = {
            'VirtualAlloc', 'VirtualAllocEx', 'CreateRemoteThread', 'WriteProcessMemory',
            'ReadProcessMemory', 'OpenProcess', 'CreateProcess', 'ShellExecute',
            'WinExec', 'system', 'CreateFile', 'WriteFile', 'ReadFile',
            'RegCreateKey', 'RegSetValue', 'InternetOpen', 'HttpOpenRequest',
            'URLDownloadToFile', 'GetProcAddress', 'LoadLibrary', 'GetModuleHandle',
            'NtCreateThreadEx', 'NtAllocateVirtualMemory', 'NtWriteVirtualMemory'
        }
        
        # Machine types mapping
        self.machine_types = {
            0x0: 'UNKNOWN',
            0x1d3: 'AM33',
            0x8664: 'AMD64',
            0x1c0: 'ARM',
            0xaa64: 'ARM64',
            0x1c4: 'ARMNT',
            0xebc: 'EFI_BYTE_CODE',
            0x14c: 'I386',
            0x200: 'IA64',
            0x9041: 'M32R',
            0x266: 'MIPS16',
            0x366: 'MIPSFPU',
            0x466: 'MIPSFPU16',
            0x1f0: 'POWERPC',
            0x1f1: 'POWERPCFP',
            0x166: 'R4000',
            0x5032: 'RISCV32',
            0x5064: 'RISCV64',
            0x5128: 'RISCV128',
            0x1a2: 'SH3',
            0x1a3: 'SH3DSP',
            0x1a6: 'SH4',
            0x1a8: 'SH5',
            0x1c2: 'THUMB',
            0x169: 'WCEMIPSV2'
        }
        
        # Subsystem types
        self.subsystem_types = {
            0: 'UNKNOWN',
            1: 'NATIVE',
            2: 'WINDOWS_GUI',
            3: 'WINDOWS_CUI',
            5: 'OS2_CUI',
            7: 'POSIX_CUI',
            8: 'NATIVE_WINDOWS',
            9: 'WINDOWS_CE_GUI',
            10: 'EFI_APPLICATION',
            11: 'EFI_BOOT_SERVICE_DRIVER',
            12: 'EFI_RUNTIME_DRIVER',
            13: 'EFI_ROM',
            14: 'XBOX',
            16: 'WINDOWS_BOOT_APPLICATION'
        }
    
    def get_entropy(self, data: bytes) -> float:
        """Calculate Shannon entropy of data."""
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
        """Calculate multiple hash types."""
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
    
    def extract_dos_header_complete(self, pe) -> Dict[str, Any]:
        """Extract complete DOS header information."""
        dos_header = pe.DOS_HEADER
        return {
            'e_magic': hex(dos_header.e_magic),
            'e_cblp': dos_header.e_cblp,
            'e_cp': dos_header.e_cp,
            'e_crlc': dos_header.e_crlc,
            'e_cparhdr': dos_header.e_cparhdr,
            'e_minalloc': dos_header.e_minalloc,
            'e_maxalloc': dos_header.e_maxalloc,
            'e_ss': dos_header.e_ss,
            'e_sp': dos_header.e_sp,
            'e_csum': dos_header.e_csum,
            'e_ip': dos_header.e_ip,
            'e_cs': dos_header.e_cs,
            'e_lfarlc': dos_header.e_lfarlc,
            'e_ovno': dos_header.e_ovno,
            'e_res': list(dos_header.e_res),
            'e_oemid': dos_header.e_oemid,
            'e_oeminfo': dos_header.e_oeminfo,
            'e_res2': list(dos_header.e_res2),
            'e_lfanew': dos_header.e_lfanew
        }
    
    def extract_file_header_complete(self, pe) -> Dict[str, Any]:
        """Extract complete file header information."""
        file_header = pe.FILE_HEADER
        return {
            'Machine': hex(file_header.Machine),
            'MachineType': self.machine_types.get(file_header.Machine, 'UNKNOWN'),
            'NumberOfSections': file_header.NumberOfSections,
            'TimeDateStamp': file_header.TimeDateStamp,
            'TimeDateStampFormatted': datetime.fromtimestamp(file_header.TimeDateStamp).strftime('%Y-%m-%d %H:%M:%S'),
            'PointerToSymbolTable': file_header.PointerToSymbolTable,
            'NumberOfSymbols': file_header.NumberOfSymbols,
            'SizeOfOptionalHeader': file_header.SizeOfOptionalHeader,
            'Characteristics': hex(file_header.Characteristics),
            'CharacteristicsFlags': self.get_characteristics_flags(file_header.Characteristics)
        }
    
    def extract_optional_header_complete(self, pe) -> Dict[str, Any]:
        """Extract complete optional header information."""
        optional_header = pe.OPTIONAL_HEADER
        return {
            'Magic': hex(optional_header.Magic),
            'MajorLinkerVersion': optional_header.MajorLinkerVersion,
            'MinorLinkerVersion': optional_header.MinorLinkerVersion,
            'SizeOfCode': optional_header.SizeOfCode,
            'SizeOfInitializedData': optional_header.SizeOfInitializedData,
            'SizeOfUninitializedData': optional_header.SizeOfUninitializedData,
            'AddressOfEntryPoint': hex(optional_header.AddressOfEntryPoint),
            'BaseOfCode': hex(optional_header.BaseOfCode),
            'ImageBase': hex(optional_header.ImageBase),
            'SectionAlignment': optional_header.SectionAlignment,
            'FileAlignment': optional_header.FileAlignment,
            'MajorOperatingSystemVersion': optional_header.MajorOperatingSystemVersion,
            'MinorOperatingSystemVersion': optional_header.MinorOperatingSystemVersion,
            'MajorImageVersion': optional_header.MajorImageVersion,
            'MinorImageVersion': optional_header.MinorImageVersion,
            'MajorSubsystemVersion': optional_header.MajorSubsystemVersion,
            'MinorSubsystemVersion': optional_header.MinorSubsystemVersion,
            'Win32VersionValue': optional_header.Win32VersionValue,
            'SizeOfImage': optional_header.SizeOfImage,
            'SizeOfHeaders': optional_header.SizeOfHeaders,
            'CheckSum': optional_header.CheckSum,
            'Subsystem': hex(optional_header.Subsystem),
            'SubsystemType': self.subsystem_types.get(optional_header.Subsystem, 'UNKNOWN'),
            'DllCharacteristics': hex(optional_header.DllCharacteristics),
            'DllCharacteristicsFlags': self.get_dll_characteristics_flags(optional_header.DllCharacteristics),
            'SizeOfStackReserve': optional_header.SizeOfStackReserve,
            'SizeOfStackCommit': optional_header.SizeOfStackCommit,
            'SizeOfHeapReserve': optional_header.SizeOfHeapReserve,
            'SizeOfHeapCommit': optional_header.SizeOfHeapCommit,
            'LoaderFlags': optional_header.LoaderFlags,
            'NumberOfRvaAndSizes': optional_header.NumberOfRvaAndSizes
        }
    
    def extract_data_directories_complete(self, pe) -> Dict[str, Any]:
        """Extract complete data directories information."""
        data_directories = pe.OPTIONAL_HEADER.DATA_DIRECTORY
        directories = {}
        
        for i, directory in enumerate(data_directories):
            if directory.Size > 0:
                directories[f'Directory_{i}'] = {
                    'VirtualAddress': hex(directory.VirtualAddress),
                    'Size': directory.Size
                }
        
        return directories
    
    def extract_sections_complete(self, pe) -> List[Dict[str, Any]]:
        """Extract complete section information."""
        sections = []
        for section in pe.sections:
            section_data = {
                'Name': section.Name.decode('utf-8').rstrip('\x00'),
                'VirtualAddress': hex(section.VirtualAddress),
                'VirtualSize': section.Misc_VirtualSize,
                'SizeOfRawData': section.SizeOfRawData,
                'PointerToRawData': section.PointerToRawData,
                'PointerToRelocations': section.PointerToRelocations,
                'PointerToLineNumbers': section.PointerToLineNumbers,
                'NumberOfRelocations': section.NumberOfRelocations,
                'NumberOfLineNumbers': section.NumberOfLineNumbers,
                'Characteristics': hex(section.Characteristics),
                'CharacteristicsFlags': self.get_section_characteristics_flags(section.Characteristics),
                'Entropy': self.get_entropy(section.get_data())
            }
            sections.append(section_data)
        
        return sections
    
    def extract_imports_complete(self, pe) -> Dict[str, Any]:
        """Extract complete import information."""
        imports = {}
        if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
            for entry in pe.DIRECTORY_ENTRY_IMPORT:
                dll_name = entry.dll.decode('utf-8')
                imports[dll_name] = []
                
                for imp in entry.imports:
                    import_info = {
                        'Name': imp.name.decode('utf-8') if imp.name else f'Ordinal_{imp.ordinal}',
                        'Ordinal': imp.ordinal,
                        'Address': hex(imp.address)
                    }
                    imports[dll_name].append(import_info)
        
        return imports
    
    def extract_exports_complete(self, pe) -> Dict[str, Any]:
        """Extract complete export information."""
        exports = {}
        if hasattr(pe, 'DIRECTORY_ENTRY_EXPORT'):
            for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
                export_info = {
                    'Name': exp.name.decode('utf-8') if exp.name else f'Ordinal_{exp.ordinal}',
                    'Ordinal': exp.ordinal,
                    'Address': hex(exp.address)
                }
                exports[exp.name.decode('utf-8') if exp.name else f'Ordinal_{exp.ordinal}'] = export_info
        
        return exports
    
    def extract_resources_complete(self, pe) -> Dict[str, Any]:
        """Extract complete resource information."""
        resources = {}
        if hasattr(pe, 'DIRECTORY_ENTRY_RESOURCE'):
            for resource_type in pe.DIRECTORY_ENTRY_RESOURCE.entries:
                resource_type_name = resource_type.name if resource_type.name else str(resource_type.id)
                resources[resource_type_name] = []
                
                for resource_id in resource_type.directory.entries:
                    resource_id_name = resource_id.name if resource_id.name else str(resource_id.id)
                    resources[resource_type_name].append(resource_id_name)
        
        return resources
    
    def extract_complete_pe_headers(self, file_path: str) -> Dict[str, Any]:
        """Extract all PE header information comprehensively."""
        try:
            pe = pefile.PE(file_path)
            
            analysis = {
                'file_path': file_path,
                'file_size': os.path.getsize(file_path),
                'file_hashes': self.get_file_hash(file_path),
                'analysis_timestamp': datetime.now().isoformat(),
                'dos_header': self.extract_dos_header_complete(pe),
                'file_header': self.extract_file_header_complete(pe),
                'optional_header': self.extract_optional_header_complete(pe),
                'data_directories': self.extract_data_directories_complete(pe),
                'sections': self.extract_sections_complete(pe),
                'imports': self.extract_imports_complete(pe),
                'exports': self.extract_exports_complete(pe),
                'resources': self.extract_resources_complete(pe)
            }
            
            # Calculate summary statistics
            analysis['summary'] = self.calculate_summary_stats(analysis)
            
            pe.close()
            return analysis
            
        except Exception as e:
            return {
                'file_path': file_path,
                'error': str(e),
                'analysis_timestamp': datetime.now().isoformat()
            }
    
    def calculate_summary_stats(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate summary statistics from the analysis."""
        summary = {
            'total_sections': len(analysis['sections']),
            'total_imports': sum(len(imports) for imports in analysis['imports'].values()),
            'total_exports': len(analysis['exports']),
            'suspicious_apis': [],
            'high_entropy_sections': []
        }
        
        # Check for suspicious APIs
        for dll, imports in analysis['imports'].items():
            for imp in imports:
                if imp['Name'] in self.suspicious_apis:
                    summary['suspicious_apis'].append({
                        'dll': dll,
                        'api': imp['Name']
                    })
        
        # Check for high entropy sections (potential packed/encrypted content)
        for section in analysis['sections']:
            if section['Entropy'] > 7.0:  # High entropy threshold
                summary['high_entropy_sections'].append({
                    'name': section['Name'],
                    'entropy': section['Entropy']
                })
        
        return summary
    
    def get_characteristics_flags(self, characteristics: int) -> List[str]:
        """Get human-readable characteristics flags."""
        flags = []
        if characteristics & 0x0001:
            flags.append('RELOCS_STRIPPED')
        if characteristics & 0x0002:
            flags.append('EXECUTABLE_IMAGE')
        if characteristics & 0x0004:
            flags.append('LINE_NUMS_STRIPPED')
        if characteristics & 0x0008:
            flags.append('LOCAL_SYMS_STRIPPED')
        if characteristics & 0x0010:
            flags.append('AGGRESSIVE_WS_TRIM')
        if characteristics & 0x0020:
            flags.append('LARGE_ADDRESS_AWARE')
        if characteristics & 0x0080:
            flags.append('BYTES_REVERSED_LO')
        if characteristics & 0x0100:
            flags.append('32BIT_MACHINE')
        if characteristics & 0x0200:
            flags.append('DEBUG_STRIPPED')
        if characteristics & 0x0400:
            flags.append('REMOVABLE_RUN_FROM_SWAP')
        if characteristics & 0x0800:
            flags.append('NET_RUN_FROM_SWAP')
        if characteristics & 0x1000:
            flags.append('SYSTEM')
        if characteristics & 0x2000:
            flags.append('DLL')
        if characteristics & 0x4000:
            flags.append('UP_SYSTEM_ONLY')
        if characteristics & 0x8000:
            flags.append('BYTES_REVERSED_HI')
        return flags
    
    def get_dll_characteristics_flags(self, dll_characteristics: int) -> List[str]:
        """Get human-readable DLL characteristics flags."""
        flags = []
        if dll_characteristics & 0x0020:
            flags.append('HIGH_ENTROPY_VA')
        if dll_characteristics & 0x0040:
            flags.append('DYNAMIC_BASE')
        if dll_characteristics & 0x0080:
            flags.append('FORCE_INTEGRITY')
        if dll_characteristics & 0x0100:
            flags.append('NX_COMPAT')
        if dll_characteristics & 0x0200:
            flags.append('NO_ISOLATION')
        if dll_characteristics & 0x0400:
            flags.append('NO_SEH')
        if dll_characteristics & 0x0800:
            flags.append('NO_BIND')
        if dll_characteristics & 0x1000:
            flags.append('APPCONTAINER')
        if dll_characteristics & 0x2000:
            flags.append('WDM_DRIVER')
        if dll_characteristics & 0x4000:
            flags.append('GUARD_CF')
        if dll_characteristics & 0x8000:
            flags.append('TERMINAL_SERVER_AWARE')
        return flags
    
    def get_section_characteristics_flags(self, characteristics: int) -> List[str]:
        """Get human-readable section characteristics flags."""
        flags = []
        if characteristics & 0x00000020:
            flags.append('CODE')
        if characteristics & 0x00000040:
            flags.append('INITIALIZED_DATA')
        if characteristics & 0x00000080:
            flags.append('UNINITIALIZED_DATA')
        if characteristics & 0x00000200:
            flags.append('INFO')
        if characteristics & 0x00000800:
            flags.append('REMOVE')
        if characteristics & 0x00001000:
            flags.append('COM_DAT')
        if characteristics & 0x00008000:
            flags.append('GPREL')
        if characteristics & 0x00020000:
            flags.append('MEM_PURGEABLE')
        if characteristics & 0x00020000:
            flags.append('MEM_16BIT')
        if characteristics & 0x00040000:
            flags.append('MEM_LOCKED')
        if characteristics & 0x00080000:
            flags.append('MEM_PRELOAD')
        if characteristics & 0x00100000:
            flags.append('ALIGN_1BYTES')
        if characteristics & 0x00200000:
            flags.append('ALIGN_2BYTES')
        if characteristics & 0x00300000:
            flags.append('ALIGN_4BYTES')
        if characteristics & 0x00400000:
            flags.append('ALIGN_8BYTES')
        if characteristics & 0x00500000:
            flags.append('ALIGN_16BYTES')
        if characteristics & 0x00600000:
            flags.append('ALIGN_32BYTES')
        if characteristics & 0x00700000:
            flags.append('ALIGN_64BYTES')
        if characteristics & 0x00800000:
            flags.append('ALIGN_128BYTES')
        if characteristics & 0x00900000:
            flags.append('ALIGN_256BYTES')
        if characteristics & 0x00A00000:
            flags.append('ALIGN_512BYTES')
        if characteristics & 0x00B00000:
            flags.append('ALIGN_1024BYTES')
        if characteristics & 0x00C00000:
            flags.append('ALIGN_2048BYTES')
        if characteristics & 0x00D00000:
            flags.append('ALIGN_4096BYTES')
        if characteristics & 0x00E00000:
            flags.append('ALIGN_8192BYTES')
        if characteristics & 0x01000000:
            flags.append('LNK_NRELOC_OVFL')
        if characteristics & 0x02000000:
            flags.append('MEM_DISCARDABLE')
        if characteristics & 0x04000000:
            flags.append('MEM_NOT_CACHED')
        if characteristics & 0x08000000:
            flags.append('MEM_NOT_PAGED')
        if characteristics & 0x10000000:
            flags.append('MEM_SHARED')
        if characteristics & 0x20000000:
            flags.append('MEM_EXECUTE')
        if characteristics & 0x40000000:
            flags.append('MEM_READ')
        if characteristics & 0x80000000:
            flags.append('MEM_WRITE')
        return flags
    
    def save_analysis_to_json(self, analysis: Dict[str, Any], output_path: str):
        """Save analysis results to JSON file."""
        with open(output_path, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
    
    def print_summary(self, analysis: Dict[str, Any]):
        """Print a summary of the analysis."""
        if 'error' in analysis:
            print(f"Error analyzing {analysis['file_path']}: {analysis['error']}")
            return
        
        print(f"\n=== PE Header Analysis Summary ===")
        print(f"File: {analysis['file_path']}")
        print(f"Size: {analysis['file_size']:,} bytes")
        print(f"MD5: {analysis['file_hashes']['md5']}")
        print(f"SHA256: {analysis['file_hashes']['sha256']}")
        
        print(f"\nMachine Type: {analysis['file_header']['MachineType']}")
        print(f"Subsystem: {analysis['optional_header']['SubsystemType']}")
        print(f"Sections: {analysis['summary']['total_sections']}")
        print(f"Imports: {analysis['summary']['total_imports']}")
        print(f"Exports: {analysis['summary']['total_exports']}")
        
        if analysis['summary']['suspicious_apis']:
            print(f"\nSuspicious APIs ({len(analysis['summary']['suspicious_apis'])}):")
            for api in analysis['summary']['suspicious_apis'][:5]:  # Show first 5
                print(f"  {api['dll']}:{api['api']}")
        
        if analysis['summary']['high_entropy_sections']:
            print(f"\nHigh Entropy Sections ({len(analysis['summary']['high_entropy_sections'])}):")
            for section in analysis['summary']['high_entropy_sections']:
                print(f"  {section['name']}: {section['entropy']:.2f}")
        
        print(f"\nAnalysis completed at: {analysis['analysis_timestamp']}") 