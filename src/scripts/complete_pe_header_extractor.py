#!/usr/bin/env python3
"""
Complete PE Header Extractor - Extracts ALL PE Headers from Binary Files
Comprehensive extraction of every PE header field for complete binary analysis
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
                'sha256': hashlib.sha256(data).hexdigest(),
                'sha512': hashlib.sha512(data).hexdigest()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def extract_dos_header_complete(self, pe) -> Dict[str, Any]:
        """Extract complete DOS header with all fields."""
        dos = pe.DOS_HEADER
        return {
            'e_magic': dos.e_magic,
            'e_magic_hex': hex(dos.e_magic),
            'e_magic_ascii': dos.e_magic.to_bytes(2, 'little').decode('ascii', errors='ignore'),
            'e_cblp': dos.e_cblp,
            'e_cp': dos.e_cp,
            'e_crlc': dos.e_crlc,
            'e_cparhdr': dos.e_cparhdr,
            'e_minalloc': dos.e_minalloc,
            'e_maxalloc': dos.e_maxalloc,
            'e_ss': dos.e_ss,
            'e_sp': dos.e_sp,
            'e_csum': dos.e_csum,
            'e_ip': dos.e_ip,
            'e_cs': dos.e_cs,
            'e_lfarlc': dos.e_lfarlc,
            'e_ovno': dos.e_ovno,
            'e_res': list(dos.e_res),
            'e_oemid': dos.e_oemid,
            'e_oeminfo': dos.e_oeminfo,
            'e_res2': list(dos.e_res2),
            'e_lfanew': dos.e_lfanew,
            'e_lfanew_hex': hex(dos.e_lfanew)
        }
    
    def extract_file_header_complete(self, pe) -> Dict[str, Any]:
        """Extract complete File Header with all fields."""
        fh = pe.FILE_HEADER
        return {
            'Machine': fh.Machine,
            'Machine_hex': hex(fh.Machine),
            'Machine_name': self.machine_types.get(fh.Machine, 'UNKNOWN'),
            'NumberOfSections': fh.NumberOfSections,
            'TimeDateStamp': fh.TimeDateStamp,
            'TimeDateStamp_hex': hex(fh.TimeDateStamp),
            'TimeDateStamp_iso': datetime.fromtimestamp(fh.TimeDateStamp).isoformat() if fh.TimeDateStamp > 0 else None,
            'PointerToSymbolTable': fh.PointerToSymbolTable,
            'PointerToSymbolTable_hex': hex(fh.PointerToSymbolTable),
            'NumberOfSymbols': fh.NumberOfSymbols,
            'SizeOfOptionalHeader': fh.SizeOfOptionalHeader,
            'SizeOfOptionalHeader_hex': hex(fh.SizeOfOptionalHeader),
            'Characteristics': fh.Characteristics,
            'Characteristics_hex': hex(fh.Characteristics),
            'Characteristics_flags': self.get_characteristics_flags(fh.Characteristics)
        }
    
    def extract_optional_header_complete(self, pe) -> Dict[str, Any]:
        """Extract complete Optional Header with all fields."""
        oh = pe.OPTIONAL_HEADER
        
        # Standard fields
        optional_header = {
            'Magic': oh.Magic,
            'Magic_hex': hex(oh.Magic),
            'MajorLinkerVersion': oh.MajorLinkerVersion,
            'MinorLinkerVersion': oh.MinorLinkerVersion,
            'SizeOfCode': oh.SizeOfCode,
            'SizeOfCode_hex': hex(oh.SizeOfCode),
            'SizeOfInitializedData': oh.SizeOfInitializedData,
            'SizeOfInitializedData_hex': hex(oh.SizeOfInitializedData),
            'SizeOfUninitializedData': oh.SizeOfUninitializedData,
            'SizeOfUninitializedData_hex': hex(oh.SizeOfUninitializedData),
            'AddressOfEntryPoint': oh.AddressOfEntryPoint,
            'AddressOfEntryPoint_hex': hex(oh.AddressOfEntryPoint),
            'BaseOfCode': oh.BaseOfCode,
            'BaseOfCode_hex': hex(oh.BaseOfCode),
            'ImageBase': oh.ImageBase,
            'ImageBase_hex': hex(oh.ImageBase),
            'SectionAlignment': oh.SectionAlignment,
            'SectionAlignment_hex': hex(oh.SectionAlignment),
            'FileAlignment': oh.FileAlignment,
            'FileAlignment_hex': hex(oh.FileAlignment),
            'MajorOperatingSystemVersion': oh.MajorOperatingSystemVersion,
            'MinorOperatingSystemVersion': oh.MinorOperatingSystemVersion,
            'MajorImageVersion': oh.MajorImageVersion,
            'MinorImageVersion': oh.MinorImageVersion,
            'MajorSubsystemVersion': oh.MajorSubsystemVersion,
            'MinorSubsystemVersion': oh.MinorSubsystemVersion,
            'Win32VersionValue': getattr(oh, 'Win32VersionValue', 0),
            'Win32VersionValue_hex': hex(getattr(oh, 'Win32VersionValue', 0)),
            'SizeOfImage': oh.SizeOfImage,
            'SizeOfImage_hex': hex(oh.SizeOfImage),
            'SizeOfHeaders': oh.SizeOfHeaders,
            'SizeOfHeaders_hex': hex(oh.SizeOfHeaders),
            'CheckSum': oh.CheckSum,
            'CheckSum_hex': hex(oh.CheckSum),
            'Subsystem': oh.Subsystem,
            'Subsystem_hex': hex(oh.Subsystem),
            'Subsystem_name': self.subsystem_types.get(oh.Subsystem, 'UNKNOWN'),
            'DllCharacteristics': oh.DllCharacteristics,
            'DllCharacteristics_hex': hex(oh.DllCharacteristics),
            'DllCharacteristics_flags': self.get_dll_characteristics_flags(oh.DllCharacteristics),
            'SizeOfStackReserve': oh.SizeOfStackReserve,
            'SizeOfStackReserve_hex': hex(oh.SizeOfStackReserve),
            'SizeOfStackCommit': oh.SizeOfStackCommit,
            'SizeOfStackCommit_hex': hex(oh.SizeOfStackCommit),
            'SizeOfHeapReserve': oh.SizeOfHeapReserve,
            'SizeOfHeapReserve_hex': hex(oh.SizeOfHeapReserve),
            'SizeOfHeapCommit': oh.SizeOfHeapCommit,
            'SizeOfHeapCommit_hex': hex(oh.SizeOfHeapCommit),
            'LoaderFlags': oh.LoaderFlags,
            'LoaderFlags_hex': hex(oh.LoaderFlags),
            'NumberOfRvaAndSizes': oh.NumberOfRvaAndSizes
        }
        
        # Add 64-bit specific fields if present
        if hasattr(oh, 'BaseOfData'):
            optional_header['BaseOfData'] = oh.BaseOfData
            optional_header['BaseOfData_hex'] = hex(oh.BaseOfData)
        
        return optional_header
    
    def extract_data_directories_complete(self, pe) -> Dict[str, Any]:
        """Extract all data directories."""
        directories = {}
        
        # Standard data directories
        dir_names = [
            'EXPORT', 'IMPORT', 'RESOURCE', 'EXCEPTION', 'SECURITY',
            'BASERELOC', 'DEBUG', 'COPYRIGHT', 'GLOBALPTR', 'TLS',
            'LOAD_CONFIG', 'BOUND_IMPORT', 'IAT', 'DELAY_IMPORT',
            'COM_DESCRIPTOR', 'RESERVED'
        ]
        
        for i, name in enumerate(dir_names):
            if i < len(pe.OPTIONAL_HEADER.DATA_DIRECTORY):
                directory = pe.OPTIONAL_HEADER.DATA_DIRECTORY[i]
                directories[name] = {
                    'VirtualAddress': directory.VirtualAddress,
                    'VirtualAddress_hex': hex(directory.VirtualAddress),
                    'Size': directory.Size,
                    'Size_hex': hex(directory.Size)
                }
        
        return directories
    
    def extract_sections_complete(self, pe) -> List[Dict[str, Any]]:
        """Extract complete section information."""
        sections = []
        
        for section in pe.sections:
            try:
                section_data = pe.get_data(section.VirtualAddress, section.SizeOfRawData)
                entropy = self.get_entropy(section_data)
                
                section_info = {
                    'Name': section.Name.decode('utf-8', errors='ignore').rstrip('\x00'),
                    'VirtualAddress': section.VirtualAddress,
                    'VirtualAddress_hex': hex(section.VirtualAddress),
                    'VirtualSize': section.Misc_VirtualSize,
                    'VirtualSize_hex': hex(section.Misc_VirtualSize),
                    'SizeOfRawData': section.SizeOfRawData,
                    'SizeOfRawData_hex': hex(section.SizeOfRawData),
                    'PointerToRawData': section.PointerToRawData,
                    'PointerToRawData_hex': hex(section.PointerToRawData),
                    'PointerToRelocations': getattr(section, 'PointerToRelocations', 0),
                    'PointerToRelocations_hex': hex(getattr(section, 'PointerToRelocations', 0)),
                    'PointerToLineNumbers': getattr(section, 'PointerToLineNumbers', 0),
                    'PointerToLineNumbers_hex': hex(getattr(section, 'PointerToLineNumbers', 0)),
                    'NumberOfRelocations': getattr(section, 'NumberOfRelocations', 0),
                    'NumberOfLineNumbers': getattr(section, 'NumberOfLineNumbers', 0),
                    'Characteristics': section.Characteristics,
                    'Characteristics_hex': hex(section.Characteristics),
                    'Characteristics_flags': self.get_section_characteristics_flags(section.Characteristics),
                    'Entropy': entropy,
                    'Entropy_rounded': round(entropy, 4)
                }
                sections.append(section_info)
            except Exception as e:
                sections.append({
                    'Name': section.Name.decode('utf-8', errors='ignore').rstrip('\x00'),
                    'VirtualAddress': section.VirtualAddress,
                    'VirtualAddress_hex': hex(section.VirtualAddress),
                    'VirtualSize': section.Misc_VirtualSize,
                    'VirtualSize_hex': hex(section.Misc_VirtualSize),
                    'SizeOfRawData': section.SizeOfRawData,
                    'SizeOfRawData_hex': hex(section.SizeOfRawData),
                    'PointerToRawData': section.PointerToRawData,
                    'PointerToRawData_hex': hex(section.PointerToRawData),
                    'Characteristics': section.Characteristics,
                    'Characteristics_hex': hex(section.Characteristics),
                    'Error': str(e)
                })
        
        return sections
    
    def extract_imports_complete(self, pe) -> Dict[str, Any]:
        """Extract complete import information."""
        imports_info = {
            'total_dlls': 0,
            'total_functions': 0,
            'total_ordinal_imports': 0,
            'import_details': []
        }
        
        if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
            for entry in pe.DIRECTORY_ENTRY_IMPORT:
                dll_info = {
                    'dll_name': entry.dll.decode('utf-8', errors='ignore'),
                    'functions': [],
                    'ordinal_functions': []
                }
                
                for imp in entry.imports:
                    if imp.name:
                        dll_info['functions'].append(imp.name.decode('utf-8', errors='ignore'))
                    elif imp.ordinal:
                        dll_info['ordinal_functions'].append(f"Ordinal_{imp.ordinal}")
                
                imports_info['import_details'].append(dll_info)
                imports_info['total_dlls'] += 1
                imports_info['total_functions'] += len(dll_info['functions'])
                imports_info['total_ordinal_imports'] += len(dll_info['ordinal_functions'])
        
        return imports_info
    
    def extract_exports_complete(self, pe) -> Dict[str, Any]:
        """Extract complete export information."""
        exports_info = {
            'total_exports': 0,
            'export_details': []
        }
        
        if hasattr(pe, 'DIRECTORY_ENTRY_EXPORT'):
            for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
                export_info = {
                    'name': exp.name.decode('utf-8', errors='ignore') if exp.name else None,
                    'ordinal': exp.ordinal,
                    'address': exp.address,
                    'address_hex': hex(exp.address)
                }
                exports_info['export_details'].append(export_info)
                exports_info['total_exports'] += 1
        
        return exports_info
    
    def extract_resources_complete(self, pe) -> Dict[str, Any]:
        """Extract complete resource information."""
        resources_info = {
            'total_resources': 0,
            'resource_details': [],
            'entropy_stats': {'min': 0, 'max': 0, 'mean': 0}
        }
        
        if hasattr(pe, 'DIRECTORY_ENTRY_RESOURCE'):
            entropies = []
            
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
                                    entropy = self.get_entropy(data)
                                    entropies.append(entropy)
                                    
                                    resource_info = {
                                        'type': str(resource_type.name) if resource_type.name else str(resource_type.id),
                                        'id': str(resource_id.name) if resource_id.name else str(resource_id.id),
                                        'language': str(resource_lang.name) if resource_lang.name else str(resource_lang.id),
                                        'size': resource_lang.data.struct.Size,
                                        'size_hex': hex(resource_lang.data.struct.Size),
                                        'offset': resource_lang.data.struct.OffsetToData,
                                        'offset_hex': hex(resource_lang.data.struct.OffsetToData),
                                        'entropy': entropy,
                                        'entropy_rounded': round(entropy, 4)
                                    }
                                    resources_info['resource_details'].append(resource_info)
                                    resources_info['total_resources'] += 1
                                except Exception as e:
                                    pass
            
            if entropies:
                resources_info['entropy_stats'] = {
                    'min': min(entropies),
                    'max': max(entropies),
                    'mean': sum(entropies) / len(entropies)
                }
        
        return resources_info
    
    def extract_complete_pe_headers(self, file_path: str) -> Dict[str, Any]:
        """Extract ALL PE headers comprehensively."""
        try:
            pe = pefile.PE(file_path)
            
            # Get file information
            file_info = {
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'file_size': os.path.getsize(file_path),
                'file_size_hex': hex(os.path.getsize(file_path)),
                'is_pe': True,
                'hashes': self.get_file_hash(file_path)
            }
            
            # Extract all headers
            complete_analysis = {
                **file_info,
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
            complete_analysis['summary_stats'] = self.calculate_summary_stats(complete_analysis)
            
            pe.close()
            return complete_analysis
            
        except Exception as e:
            return {
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'is_pe': False,
                'error': str(e)
            }
    
    def calculate_summary_stats(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive summary statistics."""
        stats = {}
        
        # Section statistics
        if 'sections' in analysis and analysis['sections']:
            sections = analysis['sections']
            entropies = [s.get('Entropy', 0) for s in sections if 'Entropy' in s]
            sizes = [s.get('SizeOfRawData', 0) for s in sections if 'SizeOfRawData' in s]
            
            stats['sections'] = {
                'count': len(sections),
                'entropy': {
                    'min': min(entropies) if entropies else 0,
                    'max': max(entropies) if entropies else 0,
                    'mean': sum(entropies) / len(entropies) if entropies else 0
                },
                'sizes': {
                    'min': min(sizes) if sizes else 0,
                    'max': max(sizes) if sizes else 0,
                    'mean': sum(sizes) / len(sizes) if sizes else 0
                }
            }
        
        # Import statistics
        if 'imports' in analysis:
            stats['imports'] = {
                'total_dlls': analysis['imports'].get('total_dlls', 0),
                'total_functions': analysis['imports'].get('total_functions', 0),
                'total_ordinal_imports': analysis['imports'].get('total_ordinal_imports', 0)
            }
        
        # Export statistics
        if 'exports' in analysis:
            stats['exports'] = {
                'total_exports': analysis['exports'].get('total_exports', 0)
            }
        
        # Resource statistics
        if 'resources' in analysis:
            stats['resources'] = {
                'total_resources': analysis['resources'].get('total_resources', 0),
                'entropy_stats': analysis['resources'].get('entropy_stats', {})
            }
        
        return stats
    
    def get_characteristics_flags(self, characteristics: int) -> List[str]:
        """Get characteristics flags as strings."""
        flags = []
        if characteristics & 0x0001: flags.append('RELOCS_STRIPPED')
        if characteristics & 0x0002: flags.append('EXECUTABLE_IMAGE')
        if characteristics & 0x0004: flags.append('LINE_NUMS_STRIPPED')
        if characteristics & 0x0008: flags.append('LOCAL_SYMS_STRIPPED')
        if characteristics & 0x0010: flags.append('AGGRESSIVE_WS_TRIM')
        if characteristics & 0x0020: flags.append('LARGE_ADDRESS_AWARE')
        if characteristics & 0x0080: flags.append('BYTES_REVERSED_LO')
        if characteristics & 0x0100: flags.append('32BIT_MACHINE')
        if characteristics & 0x0200: flags.append('DEBUG_STRIPPED')
        if characteristics & 0x0400: flags.append('REMOVABLE_RUN_FROM_SWAP')
        if characteristics & 0x0800: flags.append('NET_RUN_FROM_SWAP')
        if characteristics & 0x1000: flags.append('SYSTEM')
        if characteristics & 0x2000: flags.append('DLL')
        if characteristics & 0x4000: flags.append('UP_SYSTEM_ONLY')
        if characteristics & 0x8000: flags.append('BYTES_REVERSED_HI')
        return flags
    
    def get_dll_characteristics_flags(self, dll_characteristics: int) -> List[str]:
        """Get DLL characteristics flags as strings."""
        flags = []
        if dll_characteristics & 0x0020: flags.append('HIGH_ENTROPY_VA')
        if dll_characteristics & 0x0040: flags.append('DYNAMIC_BASE')
        if dll_characteristics & 0x0080: flags.append('FORCE_INTEGRITY')
        if dll_characteristics & 0x0100: flags.append('NX_COMPAT')
        if dll_characteristics & 0x0200: flags.append('NO_ISOLATION')
        if dll_characteristics & 0x0400: flags.append('NO_SEH')
        if dll_characteristics & 0x0800: flags.append('NO_BIND')
        if dll_characteristics & 0x1000: flags.append('APPCONTAINER')
        if dll_characteristics & 0x2000: flags.append('WDM_DRIVER')
        if dll_characteristics & 0x4000: flags.append('GUARD_CF')
        if dll_characteristics & 0x8000: flags.append('TERMINAL_SERVER_AWARE')
        return flags
    
    def get_section_characteristics_flags(self, characteristics: int) -> List[str]:
        """Get section characteristics flags as strings."""
        flags = []
        if characteristics & 0x00000008: flags.append('TYPE_NO_PAD')
        if characteristics & 0x00000020: flags.append('CNT_CODE')
        if characteristics & 0x00000040: flags.append('CNT_INITIALIZED_DATA')
        if characteristics & 0x00000080: flags.append('CNT_UNINITIALIZED_DATA')
        if characteristics & 0x00000200: flags.append('LNK_INFO')
        if characteristics & 0x00000800: flags.append('LNK_REMOVE')
        if characteristics & 0x00001000: flags.append('LNK_COMDAT')
        if characteristics & 0x00008000: flags.append('GPREL')
        if characteristics & 0x00020000: flags.append('MEM_PURGEABLE')
        if characteristics & 0x00020000: flags.append('MEM_16BIT')
        if characteristics & 0x00040000: flags.append('MEM_LOCKED')
        if characteristics & 0x00080000: flags.append('MEM_PRELOAD')
        if characteristics & 0x00100000: flags.append('ALIGN_1BYTES')
        if characteristics & 0x00200000: flags.append('ALIGN_2BYTES')
        if characteristics & 0x00300000: flags.append('ALIGN_4BYTES')
        if characteristics & 0x00400000: flags.append('ALIGN_8BYTES')
        if characteristics & 0x00500000: flags.append('ALIGN_16BYTES')
        if characteristics & 0x00600000: flags.append('ALIGN_32BYTES')
        if characteristics & 0x00700000: flags.append('ALIGN_64BYTES')
        if characteristics & 0x00800000: flags.append('ALIGN_128BYTES')
        if characteristics & 0x00900000: flags.append('ALIGN_256BYTES')
        if characteristics & 0x00A00000: flags.append('ALIGN_512BYTES')
        if characteristics & 0x00B00000: flags.append('ALIGN_1024BYTES')
        if characteristics & 0x00C00000: flags.append('ALIGN_2048BYTES')
        if characteristics & 0x00D00000: flags.append('ALIGN_4096BYTES')
        if characteristics & 0x00E00000: flags.append('ALIGN_8192BYTES')
        if characteristics & 0x01000000: flags.append('LNK_NRELOC_OVFL')
        if characteristics & 0x02000000: flags.append('MEM_DISCARDABLE')
        if characteristics & 0x04000000: flags.append('MEM_NOT_CACHED')
        if characteristics & 0x08000000: flags.append('MEM_NOT_PAGED')
        if characteristics & 0x10000000: flags.append('MEM_SHARED')
        if characteristics & 0x20000000: flags.append('MEM_EXECUTE')
        if characteristics & 0x40000000: flags.append('MEM_READ')
        if characteristics & 0x80000000: flags.append('MEM_WRITE')
        return flags
    
    def save_analysis_to_json(self, analysis: Dict[str, Any], output_path: str):
        """Save complete analysis to JSON file."""
        try:
            # Ensure we start with a clean file
            with open(output_path, 'w', encoding='utf-8', newline='\n') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)
            print(f"Complete PE analysis saved to: {output_path}")
        except Exception as e:
            print(f"Error saving analysis: {e}")
    
    def print_summary(self, analysis: Dict[str, Any]):
        """Print a summary of the PE analysis."""
        if not analysis.get('is_pe', False):
            print(f"Error: {analysis.get('error', 'Unknown error')}")
            return
        
        print(f"\n=== COMPLETE PE HEADER ANALYSIS ===")
        print(f"File: {analysis['file_name']}")
        print(f"Size: {analysis['file_size']} bytes ({analysis['file_size_hex']})")
        print(f"MD5: {analysis['hashes'].get('md5', 'N/A')}")
        print(f"SHA256: {analysis['hashes'].get('sha256', 'N/A')}")
        
        # File Header info
        fh = analysis['file_header']
        print(f"\n--- File Header ---")
        print(f"Machine: {fh['Machine_name']} ({fh['Machine_hex']})")
        print(f"Sections: {fh['NumberOfSections']}")
        print(f"Timestamp: {fh['TimeDateStamp_iso']}")
        print(f"Characteristics: {', '.join(fh['Characteristics_flags'])}")
        
        # Optional Header info
        oh = analysis['optional_header']
        print(f"\n--- Optional Header ---")
        print(f"Subsystem: {oh['Subsystem_name']}")
        print(f"Entry Point: {oh['AddressOfEntryPoint_hex']}")
        print(f"Image Base: {oh['ImageBase_hex']}")
        print(f"Stack Reserve: {oh['SizeOfStackReserve_hex']}")
        print(f"Heap Reserve: {oh['SizeOfHeapReserve_hex']}")
        
        # Sections info
        sections = analysis['sections']
        print(f"\n--- Sections ({len(sections)}) ---")
        for section in sections:
            entropy_info = f"Entropy={section.get('Entropy_rounded', 'N/A')}" if 'Entropy_rounded' in section else "Entropy=N/A"
            print(f"  {section['Name']}: VA={section['VirtualAddress_hex']}, "
                  f"Size={section['SizeOfRawData_hex']}, {entropy_info}")
        
        # Imports info
        imports = analysis['imports']
        print(f"\n--- Imports ---")
        print(f"Total DLLs: {imports['total_dlls']}")
        print(f"Total Functions: {imports['total_functions']}")
        print(f"Ordinal Imports: {imports['total_ordinal_imports']}")
        
        # Summary stats
        stats = analysis['summary_stats']
        if 'sections' in stats:
            print(f"\n--- Section Statistics ---")
            print(f"Mean Entropy: {stats['sections']['entropy']['mean']:.4f}")
            print(f"Entropy Range: {stats['sections']['entropy']['min']:.4f} - {stats['sections']['entropy']['max']:.4f}")

def main():
    """Main function to run the complete PE header extractor."""
    if len(sys.argv) < 2:
        print("Usage: python complete_pe_header_extractor.py <binary_file> [output_json]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    output_json = sys.argv[2] if len(sys.argv) > 2 else f"{Path(file_path).stem}_complete_pe_analysis.json"
    
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)
    
    extractor = CompletePEHeaderExtractor()
    
    print(f"Extracting ALL PE headers from: {file_path}")
    analysis = extractor.extract_complete_pe_headers(file_path)
    
    # Print summary
    extractor.print_summary(analysis)
    
    # Save to JSON
    extractor.save_analysis_to_json(analysis, output_json)
    
    print(f"\nComplete PE header extraction finished!")
    print(f"All PE headers have been extracted and saved to: {output_json}")

if __name__ == "__main__":
    main() 