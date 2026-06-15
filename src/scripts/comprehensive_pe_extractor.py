#!/usr/bin/env python3
"""
Comprehensive PE Header Extractor for Malware Analysis
Extracts ALL PE header fields including DOS header, NT headers, sections, and data directories
"""

import pefile
import os
import hashlib
import array
import math
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
from datetime import datetime

class ComprehensivePEExtractor:
    """Extract ALL PE header fields for comprehensive malware analysis."""
    
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
    
    def extract_dos_header(self, pe) -> Dict[str, Any]:
        """Extract DOS header information."""
        dos_header = pe.DOS_HEADER
        return {
            'e_magic': dos_header.e_magic,
            'e_magic_hex': hex(dos_header.e_magic),
            'e_magic_ascii': dos_header.e_magic.to_bytes(2, 'little').decode('ascii', errors='ignore'),
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
    
    def extract_file_header(self, pe) -> Dict[str, Any]:
        """Extract File Header information."""
        file_header = pe.FILE_HEADER
        return {
            'Machine': file_header.Machine,
            'Machine_hex': hex(file_header.Machine),
            'Machine_name': self.get_machine_name(file_header.Machine),
            'NumberOfSections': file_header.NumberOfSections,
            'TimeDateStamp': file_header.TimeDateStamp,
            'TimeDateStamp_iso': datetime.fromtimestamp(file_header.TimeDateStamp).isoformat() if file_header.TimeDateStamp > 0 else None,
            'PointerToSymbolTable': file_header.PointerToSymbolTable,
            'NumberOfSymbols': file_header.NumberOfSymbols,
            'SizeOfOptionalHeader': file_header.SizeOfOptionalHeader,
            'Characteristics': file_header.Characteristics,
            'Characteristics_hex': hex(file_header.Characteristics),
            'Characteristics_flags': self.get_characteristics_flags(file_header.Characteristics)
        }
    
    def extract_optional_header(self, pe) -> Dict[str, Any]:
        """Extract Optional Header information."""
        opt_header = pe.OPTIONAL_HEADER
        
        # Standard fields
        optional_header = {
            'Magic': opt_header.Magic,
            'Magic_hex': hex(opt_header.Magic),
            'Magic_name': 'PE32' if opt_header.Magic == 0x10B else 'PE32+' if opt_header.Magic == 0x20B else 'Unknown',
            'MajorLinkerVersion': opt_header.MajorLinkerVersion,
            'MinorLinkerVersion': opt_header.MinorLinkerVersion,
            'SizeOfCode': opt_header.SizeOfCode,
            'SizeOfInitializedData': opt_header.SizeOfInitializedData,
            'SizeOfUninitializedData': opt_header.SizeOfUninitializedData,
            'AddressOfEntryPoint': opt_header.AddressOfEntryPoint,
            'AddressOfEntryPoint_hex': hex(opt_header.AddressOfEntryPoint),
            'BaseOfCode': opt_header.BaseOfCode,
            'BaseOfCode_hex': hex(opt_header.BaseOfCode),
            'ImageBase': opt_header.ImageBase,
            'ImageBase_hex': hex(opt_header.ImageBase),
            'SectionAlignment': opt_header.SectionAlignment,
            'FileAlignment': opt_header.FileAlignment,
            'MajorOperatingSystemVersion': opt_header.MajorOperatingSystemVersion,
            'MinorOperatingSystemVersion': opt_header.MinorOperatingSystemVersion,
            'MajorImageVersion': opt_header.MajorImageVersion,
            'MinorImageVersion': opt_header.MinorImageVersion,
            'MajorSubsystemVersion': opt_header.MajorSubsystemVersion,
            'MinorSubsystemVersion': opt_header.MinorSubsystemVersion,
            'Win32VersionValue': opt_header.Win32VersionValue,
            'SizeOfImage': opt_header.SizeOfImage,
            'SizeOfHeaders': opt_header.SizeOfHeaders,
            'CheckSum': opt_header.CheckSum,
            'Subsystem': opt_header.Subsystem,
            'Subsystem_name': self.get_subsystem_name(opt_header.Subsystem),
            'DllCharacteristics': opt_header.DllCharacteristics,
            'DllCharacteristics_hex': hex(opt_header.DllCharacteristics),
            'DllCharacteristics_flags': self.get_dll_characteristics_flags(opt_header.DllCharacteristics),
            'SizeOfStackReserve': opt_header.SizeOfStackReserve,
            'SizeOfStackCommit': opt_header.SizeOfStackCommit,
            'SizeOfHeapReserve': opt_header.SizeOfHeapReserve,
            'SizeOfHeapCommit': opt_header.SizeOfHeapCommit,
            'LoaderFlags': opt_header.LoaderFlags,
            'NumberOfRvaAndSizes': opt_header.NumberOfRvaAndSizes
        }
        
        # Handle BaseOfData (32-bit only)
        try:
            optional_header['BaseOfData'] = opt_header.BaseOfData
            optional_header['BaseOfData_hex'] = hex(opt_header.BaseOfData)
        except AttributeError:
            optional_header['BaseOfData'] = None
            optional_header['BaseOfData_hex'] = None
        
        return optional_header
    
    def extract_data_directories(self, pe) -> Dict[str, Any]:
        """Extract Data Directory information."""
        data_dirs = {}
        directory_names = [
            'Export Table', 'Import Table', 'Resource Table', 'Exception Table',
            'Certificate Table', 'Base Relocation Table', 'Debug Directory',
            'Architecture', 'Global Pointer', 'TLS Table', 'Load Config Table',
            'Bound Import Table', 'Import Address Table', 'Delay Import Descriptor',
            'COM+ Runtime Header', 'Reserved'
        ]
        
        for i, name in enumerate(directory_names):
            if i < len(pe.OPTIONAL_HEADER.DATA_DIRECTORY):
                directory = pe.OPTIONAL_HEADER.DATA_DIRECTORY[i]
                data_dirs[name] = {
                    'VirtualAddress': directory.VirtualAddress,
                    'VirtualAddress_hex': hex(directory.VirtualAddress),
                    'Size': directory.Size,
                    'Size_hex': hex(directory.Size)
                }
            else:
                data_dirs[name] = {'VirtualAddress': 0, 'Size': 0}
        
        return data_dirs
    
    def extract_sections(self, pe) -> List[Dict[str, Any]]:
        """Extract detailed section information."""
        sections = []
        
        for section in pe.sections:
            section_info = {
                'Name': section.Name.decode('utf-8', errors='ignore').rstrip('\x00'),
                'VirtualAddress': section.VirtualAddress,
                'VirtualAddress_hex': hex(section.VirtualAddress),
                'Misc_VirtualSize': section.Misc_VirtualSize,
                'SizeOfRawData': section.SizeOfRawData,
                'PointerToRawData': section.PointerToRawData,
                'PointerToRawData_hex': hex(section.PointerToRawData),
                'PointerToRelocations': section.PointerToRelocations,
                'PointerToLinenumbers': section.PointerToLinenumbers,
                'NumberOfRelocations': section.NumberOfRelocations,
                'NumberOfLinenumbers': section.NumberOfLinenumbers,
                'Characteristics': section.Characteristics,
                'Characteristics_hex': hex(section.Characteristics),
                'Characteristics_flags': self.get_section_characteristics_flags(section.Characteristics),
                'Entropy': section.get_entropy(),
                'IsExecutable': bool(section.Characteristics & 0x20000000),  # IMAGE_SCN_MEM_EXECUTE
                'IsWritable': bool(section.Characteristics & 0x80000000),    # IMAGE_SCN_MEM_WRITE
                'IsReadable': bool(section.Characteristics & 0x40000000),    # IMAGE_SCN_MEM_READ
            }
            
            # Try to get section data for additional analysis
            try:
                section_data = section.get_data()
                section_info['DataSize'] = len(section_data)
                section_info['DataEntropy'] = self.get_entropy(section_data)
            except:
                section_info['DataSize'] = 0
                section_info['DataEntropy'] = 0
            
            sections.append(section_info)
        
        return sections
    
    def extract_imports(self, pe) -> Dict[str, Any]:
        """Extract detailed import information."""
        imports_info = {
            'DLLs': [],
            'TotalImports': 0,
            'TotalDLLs': 0,
            'SuspiciousAPIs': []
        }
        
        try:
            for entry in pe.DIRECTORY_ENTRY_IMPORT:
                dll_info = {
                    'Name': entry.dll.decode('utf-8', errors='ignore'),
                    'Functions': [],
                    'SuspiciousFunctions': []
                }
                
                for imp in entry.imports:
                    func_info = {
                        'Name': imp.name.decode('utf-8', errors='ignore') if imp.name else f'Ordinal_{imp.ordinal}',
                        'Ordinal': imp.ordinal,
                        'Address': imp.address,
                        'Address_hex': hex(imp.address)
                    }
                    
                    dll_info['Functions'].append(func_info)
                    
                    # Check for suspicious APIs
                    if imp.name and imp.name.decode('utf-8', errors='ignore') in self.suspicious_apis:
                        dll_info['SuspiciousFunctions'].append(func_info)
                        imports_info['SuspiciousAPIs'].append(func_info)
                
                imports_info['DLLs'].append(dll_info)
                imports_info['TotalImports'] += len(dll_info['Functions'])
            
            imports_info['TotalDLLs'] = len(imports_info['DLLs'])
            
        except AttributeError:
            pass
        
        return imports_info
    
    def extract_exports(self, pe) -> Dict[str, Any]:
        """Extract export information."""
        exports_info = {
            'Functions': [],
            'TotalExports': 0
        }
        
        try:
            for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
                exp_info = {
                    'Name': exp.name.decode('utf-8', errors='ignore') if exp.name else f'Ordinal_{exp.ordinal}',
                    'Ordinal': exp.ordinal,
                    'Address': exp.address,
                    'Address_hex': hex(exp.address)
                }
                exports_info['Functions'].append(exp_info)
            
            exports_info['TotalExports'] = len(exports_info['Functions'])
            
        except AttributeError:
            pass
        
        return exports_info
    
    def extract_resources(self, pe) -> Dict[str, Any]:
        """Extract resource information."""
        resources_info = {
            'Resources': [],
            'TotalResources': 0,
            'ResourceTypes': {}
        }
        
        try:
            for resource_type in pe.DIRECTORY_ENTRY_RESOURCE.entries:
                type_name = resource_type.name.decode('utf-8', errors='ignore') if resource_type.name else f'Type_{resource_type.id}'
                
                if type_name not in resources_info['ResourceTypes']:
                    resources_info['ResourceTypes'][type_name] = []
                
                for resource_id in resource_type.directory.entries:
                    id_name = resource_id.name.decode('utf-8', errors='ignore') if resource_id.name else f'ID_{resource_id.id}'
                    
                    for resource_lang in resource_id.directory.entries:
                        try:
                            data = pe.get_data(resource_lang.data.struct.OffsetToData, resource_lang.data.struct.Size)
                            resource_info = {
                                'Type': type_name,
                                'ID': id_name,
                                'Language': resource_lang.id,
                                'Size': resource_lang.data.struct.Size,
                                'Offset': resource_lang.data.struct.OffsetToData,
                                'Offset_hex': hex(resource_lang.data.struct.OffsetToData),
                                'Entropy': self.get_entropy(data)
                            }
                            
                            resources_info['Resources'].append(resource_info)
                            resources_info['ResourceTypes'][type_name].append(resource_info)
                            
                        except Exception as e:
                            pass
            
            resources_info['TotalResources'] = len(resources_info['Resources'])
            
        except AttributeError:
            pass
        
        return resources_info
    
    def extract_comprehensive_pe_headers(self, file_path: str) -> Dict[str, Any]:
        """Extract ALL PE header information."""
        try:
            pe = pefile.PE(file_path)
            
            # Get file hashes
            file_hashes = self.get_file_hash(file_path)
            
            # Comprehensive PE analysis
            pe_analysis = {
                'file_info': {
                    'id': os.path.basename(file_path),
                    'path': file_path,
                    'size': os.path.getsize(file_path),
                    'md5': file_hashes['md5'],
                    'sha1': file_hashes['sha1'],
                    'sha256': file_hashes['sha256'],
                    'analysis_timestamp': datetime.now().isoformat()
                },
                'dos_header': self.extract_dos_header(pe),
                'file_header': self.extract_file_header(pe),
                'optional_header': self.extract_optional_header(pe),
                'data_directories': self.extract_data_directories(pe),
                'sections': self.extract_sections(pe),
                'imports': self.extract_imports(pe),
                'exports': self.extract_exports(pe),
                'resources': self.extract_resources(pe)
            }
            
            # Calculate summary statistics
            pe_analysis['summary'] = self.calculate_summary_stats(pe_analysis)
            
            pe.close()
            return pe_analysis
            
        except Exception as e:
            return {
                'file_info': {
                    'id': os.path.basename(file_path),
                    'error': str(e)
                },
                'md5': self.get_file_hash(file_path)['md5']
            }
    
    def calculate_summary_stats(self, pe_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate summary statistics from PE analysis."""
        sections = pe_analysis.get('sections', [])
        imports = pe_analysis.get('imports', {})
        exports = pe_analysis.get('exports', {})
        resources = pe_analysis.get('resources', {})
        
        # Section statistics
        if sections:
            entropies = [s['Entropy'] for s in sections]
            sizes = [s['SizeOfRawData'] for s in sections]
            exec_sections = [s for s in sections if s['IsExecutable']]
            writable_sections = [s for s in sections if s['IsWritable']]
            
            section_stats = {
                'total_sections': len(sections),
                'executable_sections': len(exec_sections),
                'writable_sections': len(writable_sections),
                'mean_entropy': sum(entropies) / len(entropies),
                'min_entropy': min(entropies),
                'max_entropy': max(entropies),
                'total_size': sum(sizes),
                'mean_size': sum(sizes) / len(sizes)
            }
        else:
            section_stats = {
                'total_sections': 0,
                'executable_sections': 0,
                'writable_sections': 0,
                'mean_entropy': 0,
                'min_entropy': 0,
                'max_entropy': 0,
                'total_size': 0,
                'mean_size': 0
            }
        
        # Import/Export statistics
        import_stats = {
            'total_dlls': imports.get('TotalDLLs', 0),
            'total_imports': imports.get('TotalImports', 0),
            'suspicious_apis': len(imports.get('SuspiciousAPIs', []))
        }
        
        export_stats = {
            'total_exports': exports.get('TotalExports', 0)
        }
        
        # Resource statistics
        resource_stats = {
            'total_resources': resources.get('TotalResources', 0),
            'resource_types': len(resources.get('ResourceTypes', {}))
        }
        
        return {
            'sections': section_stats,
            'imports': import_stats,
            'exports': export_stats,
            'resources': resource_stats
        }
    
    def get_machine_name(self, machine: int) -> str:
        """Get machine architecture name."""
        machine_names = {
            0x0: 'Unknown',
            0x1d3: 'AM33',
            0x8664: 'AMD64',
            0x1c0: 'ARM',
            0xaa64: 'ARM64',
            0x1c4: 'ARMNT',
            0xebc: 'EFI Byte Code',
            0x14c: 'Intel 386',
            0x200: 'Intel Itanium',
            0x9041: 'M32R',
            0x266: 'MIPS16',
            0x366: 'MIPS with FPU',
            0x466: 'MIPS16 with FPU',
            0x1f0: 'PowerPC',
            0x1f1: 'PowerPC with FPU',
            0x166: 'R4000',
            0x5032: 'RISCV32',
            0x5064: 'RISCV64',
            0x5128: 'RISCV128',
            0x1a2: 'SH3',
            0x1a3: 'SH3DSP',
            0x1a6: 'SH4',
            0x1a8: 'SH5',
            0x1c2: 'Thumb',
            0x169: 'WCEMIPSV2'
        }
        return machine_names.get(machine, f'Unknown ({hex(machine)})')
    
    def get_characteristics_flags(self, characteristics: int) -> List[str]:
        """Get file characteristics flags."""
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
        """Get DLL characteristics flags."""
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
        """Get section characteristics flags."""
        flags = []
        if characteristics & 0x00000020: flags.append('CODE')
        if characteristics & 0x00000040: flags.append('INITIALIZED_DATA')
        if characteristics & 0x00000080: flags.append('UNINITIALIZED_DATA')
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
        if characteristics & 0x00F00000: flags.append('ALIGN_MASK')
        if characteristics & 0x01000000: flags.append('LNK_NRELOC_OVFL')
        if characteristics & 0x02000000: flags.append('MEM_DISCARDABLE')
        if characteristics & 0x04000000: flags.append('MEM_NOT_CACHED')
        if characteristics & 0x08000000: flags.append('MEM_NOT_PAGED')
        if characteristics & 0x10000000: flags.append('MEM_SHARED')
        if characteristics & 0x20000000: flags.append('MEM_EXECUTE')
        if characteristics & 0x40000000: flags.append('MEM_READ')
        if characteristics & 0x80000000: flags.append('MEM_WRITE')
        return flags
    
    def get_subsystem_name(self, subsystem: int) -> str:
        """Get subsystem name."""
        subsystem_names = {
            0: 'Unknown',
            1: 'Native',
            2: 'Windows GUI',
            3: 'Windows CUI',
            5: 'OS/2 CUI',
            7: 'POSIX CUI',
            8: 'Native Windows',
            9: 'Windows CE GUI',
            10: 'EFI Application',
            11: 'EFI Boot Service Driver',
            12: 'EFI Runtime Driver',
            13: 'EFI ROM',
            14: 'XBOX',
            16: 'Windows Boot Application'
        }
        return subsystem_names.get(subsystem, f'Unknown ({subsystem})')
    
    def format_comprehensive_pe_headers(self, pe_analysis: Dict[str, Any]) -> str:
        """Format comprehensive PE headers as a detailed report."""
        if 'error' in pe_analysis.get('file_info', {}):
            return f"❌ PE Analysis Error: {pe_analysis['file_info']['error']}"
        
        output = "🔍 COMPREHENSIVE PE HEADER ANALYSIS\n"
        output += "=" * 60 + "\n"
        
        # File info
        file_info = pe_analysis['file_info']
        output += f"📁 File: {file_info['id']}\n"
        output += f"📏 Size: {file_info['size']:,} bytes\n"
        output += f"🔐 MD5: {file_info['md5']}\n"
        output += f"🔐 SHA1: {file_info['sha1']}\n"
        output += f"🔐 SHA256: {file_info['sha256']}\n"
        output += f"⏰ Analysis: {file_info['analysis_timestamp']}\n\n"
        
        # DOS Header
        dos_header = pe_analysis['dos_header']
        output += "📋 DOS HEADER:\n"
        output += f"  Magic: {dos_header['e_magic_ascii']} ({dos_header['e_magic_hex']})\n"
        output += f"  File Address of NT Headers: {dos_header['e_lfanew']} ({hex(dos_header['e_lfanew'])})\n\n"
        
        # File Header
        file_header = pe_analysis['file_header']
        output += "📋 FILE HEADER:\n"
        output += f"  Machine: {file_header['Machine_name']} ({file_header['Machine_hex']})\n"
        output += f"  Number of Sections: {file_header['NumberOfSections']}\n"
        output += f"  Time Date Stamp: {file_header['TimeDateStamp_iso']}\n"
        output += f"  Characteristics: {', '.join(file_header['Characteristics_flags'])}\n\n"
        
        # Optional Header
        opt_header = pe_analysis['optional_header']
        output += "📋 OPTIONAL HEADER:\n"
        output += f"  Magic: {opt_header['Magic_name']} ({opt_header['Magic_hex']})\n"
        output += f"  Address of Entry Point: {opt_header['AddressOfEntryPoint_hex']}\n"
        output += f"  Image Base: {opt_header['ImageBase_hex']}\n"
        output += f"  Subsystem: {opt_header['Subsystem_name']}\n"
        output += f"  DLL Characteristics: {', '.join(opt_header['DllCharacteristics_flags'])}\n\n"
        
        # Sections
        sections = pe_analysis['sections']
        output += f"📦 SECTIONS ({len(sections)} total):\n"
        for i, section in enumerate(sections[:5]):  # Show first 5 sections
            output += f"  {i+1}. {section['Name']}:\n"
            output += f"     Virtual Address: {section['VirtualAddress_hex']}\n"
            output += f"     Size: {section['SizeOfRawData']:,} bytes\n"
            output += f"     Entropy: {section['Entropy']:.2f}\n"
            output += f"     Characteristics: {', '.join(section['Characteristics_flags'][:3])}\n"
        if len(sections) > 5:
            output += f"  ... and {len(sections) - 5} more sections\n"
        output += "\n"
        
        # Imports
        imports = pe_analysis['imports']
        output += f"🔗 IMPORTS:\n"
        output += f"  Total DLLs: {imports['TotalDLLs']}\n"
        output += f"  Total Functions: {imports['TotalImports']}\n"
        output += f"  Suspicious APIs: {len(imports['SuspiciousAPIs'])}\n"
        if imports['SuspiciousAPIs']:
            output += f"  Suspicious Functions: {', '.join([api['Name'] for api in imports['SuspiciousAPIs'][:5]])}\n"
        output += "\n"
        
        # Exports
        exports = pe_analysis['exports']
        output += f"📤 EXPORTS:\n"
        output += f"  Total Functions: {exports['TotalExports']}\n\n"
        
        # Resources
        resources = pe_analysis['resources']
        output += f"📚 RESOURCES:\n"
        output += f"  Total Resources: {resources['TotalResources']}\n"
        output += f"  Resource Types: {', '.join(list(resources['ResourceTypes'].keys())[:5])}\n\n"
        
        # Summary
        summary = pe_analysis['summary']
        output += "📊 SUMMARY STATISTICS:\n"
        output += f"  Sections: {summary['sections']['total_sections']} total, {summary['sections']['executable_sections']} executable\n"
        output += f"  Mean Section Entropy: {summary['sections']['mean_entropy']:.2f}\n"
        output += f"  Suspicious APIs: {summary['imports']['suspicious_apis']}\n"
        
        return output

def main():
    """Test the comprehensive PE header extractor."""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python comprehensive_pe_extractor.py <pe_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found")
        sys.exit(1)
    
    extractor = ComprehensivePEExtractor()
    pe_analysis = extractor.extract_comprehensive_pe_headers(file_path)
    
    print(extractor.format_comprehensive_pe_headers(pe_analysis))
    
    # Save as JSON
    output_file = f"{os.path.splitext(file_path)[0]}_comprehensive_pe_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(pe_analysis, f, indent=2, default=str)
    print(f"\n💾 Comprehensive PE analysis saved to: {output_file}")

if __name__ == "__main__":
    main() 