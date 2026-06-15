# Complete PE Header Extractor

## Overview

This tool extracts **ALL PE headers** from binary files comprehensively for malware analysis and security research. It provides complete extraction of every PE header field, including DOS header, NT headers, sections, data directories, imports, exports, resources, and more.

## Features

### ✅ Complete PE Header Extraction
- **DOS Header**: All fields including magic bytes, file offsets, and reserved fields
- **File Header**: Machine type, sections count, timestamp, characteristics, and all flags
- **Optional Header**: All standard and extended fields for both 32-bit and 64-bit PE files
- **Data Directories**: All 16 data directories with virtual addresses and sizes
- **Sections**: Complete section information with entropy calculations
- **Imports**: All imported DLLs and functions with ordinal imports
- **Exports**: All exported functions and their addresses
- **Resources**: All resource types with entropy analysis
- **File Hashes**: MD5, SHA1, SHA256, and SHA512 hashes
- **Characteristic Flags**: Human-readable flag descriptions
- **Summary Statistics**: Comprehensive analysis statistics

### 🔍 Advanced Analysis
- **Entropy Calculation**: Shannon entropy for sections and resources
- **Machine Type Detection**: Support for all PE machine types (x86, x64, ARM, etc.)
- **Subsystem Identification**: Windows GUI/CUI, Native, EFI, etc.
- **Flag Decoding**: All characteristic flags converted to readable strings
- **Timestamp Conversion**: Human-readable timestamps
- **Hex Representations**: All values provided in both decimal and hexadecimal

## Installation

### Prerequisites
- Python 3.6 or higher
- pefile module

### Setup
```bash
# Install pefile module
pip install pefile

# Or install from requirements
pip install -r requirements.txt
```

## Usage

### Command Line
```bash
# Basic usage
python complete_pe_header_extractor.py malware.exe

# Specify output file
python complete_pe_header_extractor.py malware.exe analysis.json

# Help
python complete_pe_header_extractor.py
```

### Windows Batch Script
```cmd
# Basic usage
extract_all_pe_headers.bat malware.exe

# Specify output file
extract_all_pe_headers.bat malware.exe analysis.json

# Show help
extract_all_pe_headers.bat
```

### PowerShell Script
```powershell
# Basic usage
.\extract_all_pe_headers.ps1 malware.exe

# Specify output file
.\extract_all_pe_headers.ps1 malware.exe analysis.json

# Show help
Get-Help .\extract_all_pe_headers.ps1
```

## Output Format

The tool generates a comprehensive JSON file containing all PE header information:

```json
{
  "file_path": "malware.exe",
  "file_name": "malware.exe",
  "file_size": 174968,
  "file_size_hex": "0x2aaf8",
  "is_pe": true,
  "hashes": {
    "md5": "abc123...",
    "sha1": "def456...",
    "sha256": "ghi789...",
    "sha512": "jkl012..."
  },
  "dos_header": {
    "e_magic": 23117,
    "e_magic_hex": "0x5a4d",
    "e_magic_ascii": "MZ",
    "e_lfanew": 248,
    "e_lfanew_hex": "0xf8",
    // ... all DOS header fields
  },
  "file_header": {
    "Machine": 332,
    "Machine_hex": "0x14c",
    "Machine_name": "I386",
    "NumberOfSections": 4,
    "TimeDateStamp": 1155688419,
    "TimeDateStamp_iso": "2006-08-16T12:33:39",
    "Characteristics": 271,
    "Characteristics_hex": "0x10f",
    "Characteristics_flags": ["EXECUTABLE_IMAGE", "32BIT_MACHINE", "DLL"]
    // ... all file header fields
  },
  "optional_header": {
    "Magic": 267,
    "Magic_hex": "0x10b",
    "AddressOfEntryPoint": 31384,
    "AddressOfEntryPoint_hex": "0x7a98",
    "ImageBase": 4194304,
    "ImageBase_hex": "0x400000",
    "Subsystem": 2,
    "Subsystem_name": "WINDOWS_GUI",
    "DllCharacteristics_flags": ["DYNAMIC_BASE", "NX_COMPAT"]
    // ... all optional header fields
  },
  "data_directories": {
    "EXPORT": {
      "VirtualAddress": 0,
      "VirtualAddress_hex": "0x0",
      "Size": 0,
      "Size_hex": "0x0"
    },
    "IMPORT": {
      "VirtualAddress": 24576,
      "VirtualAddress_hex": "0x6000",
      "Size": 232,
      "Size_hex": "0xe8"
    }
    // ... all 16 data directories
  },
  "sections": [
    {
      "Name": ".text",
      "VirtualAddress": 4096,
      "VirtualAddress_hex": "0x1000",
      "VirtualSize": 28672,
      "VirtualSize_hex": "0x7000",
      "SizeOfRawData": 28672,
      "SizeOfRawData_hex": "0x7000",
      "PointerToRawData": 4096,
      "PointerToRawData_hex": "0x1000",
      "Characteristics": 1610612768,
      "Characteristics_hex": "0x60000020",
      "Characteristics_flags": ["CNT_CODE", "MEM_EXECUTE", "MEM_READ"],
      "Entropy": 6.1234,
      "Entropy_rounded": 6.1234
    }
    // ... all sections
  ],
  "imports": {
    "total_dlls": 12,
    "total_functions": 232,
    "total_ordinal_imports": 1,
    "import_details": [
      {
        "dll_name": "KERNEL32.dll",
        "functions": [
          "GetModuleHandleA",
          "GetStartupInfoA",
          "LocalAlloc"
          // ... all imported functions
        ],
        "ordinal_functions": ["Ordinal_123"]
      }
      // ... all imported DLLs
    ]
  },
  "exports": {
    "total_exports": 0,
    "export_details": []
  },
  "resources": {
    "total_resources": 30,
    "entropy_stats": {
      "min": 1.5715,
      "max": 4.8648,
      "mean": 2.7019
    },
    "resource_details": [
      {
        "type": "RT_ICON",
        "id": "1",
        "language": "1033",
        "size": 2216,
        "size_hex": "0x8a8",
        "offset": 163840,
        "offset_hex": "0x28000",
        "entropy": 4.8648,
        "entropy_rounded": 4.8648
      }
      // ... all resources
    ]
  },
  "summary_stats": {
    "sections": {
      "count": 4,
      "entropy": {
        "min": 4.1309,
        "max": 6.3375,
        "mean": 5.0170
      },
      "sizes": {
        "min": 12288,
        "max": 110592,
        "mean": 40960.0
      }
    },
    "imports": {
      "total_dlls": 12,
      "total_functions": 232,
      "total_ordinal_imports": 1
    },
    "exports": {
      "total_exports": 0
    },
    "resources": {
      "total_resources": 30,
      "entropy_stats": {
        "min": 1.5715,
        "max": 4.8648,
        "mean": 2.7019
      }
    }
  }
}
```

## PE Header Fields Extracted

### DOS Header (All Fields)
- `e_magic` - Magic number (MZ)
- `e_cblp` - Bytes on last page of file
- `e_cp` - Pages in file
- `e_crlc` - Relocations
- `e_cparhdr` - Size of header in paragraphs
- `e_minalloc` - Minimum extra paragraphs needed
- `e_maxalloc` - Maximum extra paragraphs needed
- `e_ss` - Initial (relative) SS value
- `e_sp` - Initial SP value
- `e_csum` - Checksum
- `e_ip` - Initial IP value
- `e_cs` - Initial (relative) CS value
- `e_lfarlc` - File address of relocation table
- `e_ovno` - Overlay number
- `e_res` - Reserved words
- `e_oemid` - OEM identifier
- `e_oeminfo` - OEM information
- `e_res2` - Reserved words
- `e_lfanew` - File address of new exe header

### File Header (All Fields)
- `Machine` - Target machine type
- `NumberOfSections` - Number of sections
- `TimeDateStamp` - Time and date stamp
- `PointerToSymbolTable` - File offset of symbol table
- `NumberOfSymbols` - Number of symbols
- `SizeOfOptionalHeader` - Size of optional header
- `Characteristics` - File characteristics flags

### Optional Header (All Fields)
- `Magic` - Magic number
- `MajorLinkerVersion` - Linker major version
- `MinorLinkerVersion` - Linker minor version
- `SizeOfCode` - Size of code section
- `SizeOfInitializedData` - Size of initialized data
- `SizeOfUninitializedData` - Size of uninitialized data
- `AddressOfEntryPoint` - Address of entry point
- `BaseOfCode` - Base address of code section
- `BaseOfData` - Base address of data section (32-bit only)
- `ImageBase` - Preferred load address
- `SectionAlignment` - Section alignment
- `FileAlignment` - File alignment
- `MajorOperatingSystemVersion` - OS major version
- `MinorOperatingSystemVersion` - OS minor version
- `MajorImageVersion` - Image major version
- `MinorImageVersion` - Image minor version
- `MajorSubsystemVersion` - Subsystem major version
- `MinorSubsystemVersion` - Subsystem minor version
- `Win32VersionValue` - Win32 version value
- `SizeOfImage` - Size of image
- `SizeOfHeaders` - Size of headers
- `CheckSum` - Checksum
- `Subsystem` - Subsystem
- `DllCharacteristics` - DLL characteristics
- `SizeOfStackReserve` - Size of stack reserve
- `SizeOfStackCommit` - Size of stack commit
- `SizeOfHeapReserve` - Size of heap reserve
- `SizeOfHeapCommit` - Size of heap commit
- `LoaderFlags` - Loader flags
- `NumberOfRvaAndSizes` - Number of data directories

### Data Directories (All 16)
1. **EXPORT** - Export directory
2. **IMPORT** - Import directory
3. **RESOURCE** - Resource directory
4. **EXCEPTION** - Exception directory
5. **SECURITY** - Security directory
6. **BASERELOC** - Base relocation table
7. **DEBUG** - Debug directory
8. **COPYRIGHT** - Copyright/architecture data
9. **GLOBALPTR** - Global pointer register
10. **TLS** - Thread local storage
11. **LOAD_CONFIG** - Load configuration directory
12. **BOUND_IMPORT** - Bound import directory
13. **IAT** - Import address table
14. **DELAY_IMPORT** - Delay import descriptor
15. **COM_DESCRIPTOR** - COM runtime descriptor
16. **RESERVED** - Reserved

### Sections (All Fields)
- `Name` - Section name
- `VirtualAddress` - Virtual address
- `VirtualSize` - Virtual size
- `SizeOfRawData` - Size of raw data
- `PointerToRawData` - Pointer to raw data
- `PointerToRelocations` - Pointer to relocations
- `PointerToLineNumbers` - Pointer to line numbers
- `NumberOfRelocations` - Number of relocations
- `NumberOfLineNumbers` - Number of line numbers
- `Characteristics` - Section characteristics
- `Entropy` - Shannon entropy of section data

### Imports (Complete)
- DLL names
- Function names
- Ordinal imports
- Import addresses
- Import hints

### Exports (Complete)
- Export names
- Export ordinals
- Export addresses
- Export hints

### Resources (Complete)
- Resource types
- Resource IDs
- Resource languages
- Resource sizes
- Resource offsets
- Resource entropy

## Machine Types Supported
- `0x0` - UNKNOWN
- `0x1d3` - AM33
- `0x8664` - AMD64
- `0x1c0` - ARM
- `0xaa64` - ARM64
- `0x1c4` - ARMNT
- `0xebc` - EFI_BYTE_CODE
- `0x14c` - I386
- `0x200` - IA64
- `0x9041` - M32R
- `0x266` - MIPS16
- `0x366` - MIPSFPU
- `0x466` - MIPSFPU16
- `0x1f0` - POWERPC
- `0x1f1` - POWERPCFP
- `0x166` - R4000
- `0x5032` - RISCV32
- `0x5064` - RISCV64
- `0x5128` - RISCV128
- `0x1a2` - SH3
- `0x1a3` - SH3DSP
- `0x1a6` - SH4
- `0x1a8` - SH5
- `0x1c2` - THUMB
- `0x169` - WCEMIPSV2

## Subsystem Types Supported
- `0` - UNKNOWN
- `1` - NATIVE
- `2` - WINDOWS_GUI
- `3` - WINDOWS_CUI
- `5` - OS2_CUI
- `7` - POSIX_CUI
- `8` - NATIVE_WINDOWS
- `9` - WINDOWS_CE_GUI
- `10` - EFI_APPLICATION
- `11` - EFI_BOOT_SERVICE_DRIVER
- `12` - EFI_RUNTIME_DRIVER
- `13` - EFI_ROM
- `14` - XBOX
- `16` - WINDOWS_BOOT_APPLICATION

## Examples

### Basic Analysis
```bash
python complete_pe_header_extractor.py malware.exe
```

### Custom Output
```bash
python complete_pe_header_extractor.py malware.exe detailed_analysis.json
```

### Batch Processing
```bash
# Windows
for %f in (*.exe) do python complete_pe_header_extractor.py "%f"

# PowerShell
Get-ChildItem *.exe | ForEach-Object { python complete_pe_header_extractor.py $_.Name }
```

## Error Handling

The tool handles various error conditions:
- Non-PE files
- Corrupted PE files
- Missing sections
- Invalid data directories
- Access permission issues
- Memory errors

## Performance

- **Small files (< 1MB)**: ~1-2 seconds
- **Medium files (1-10MB)**: ~2-5 seconds
- **Large files (10-100MB)**: ~5-15 seconds
- **Very large files (>100MB)**: ~15+ seconds

## Security Considerations

- Always run in a safe environment when analyzing unknown binaries
- The tool only reads files and does not execute them
- Consider using a sandbox or virtual machine for malware analysis
- Be cautious with files from untrusted sources

## Troubleshooting

### Common Issues

1. **"pefile module not found"**
   ```bash
   pip install pefile
   ```

2. **"Permission denied"**
   - Run as administrator or check file permissions

3. **"Invalid PE file"**
   - File may be corrupted or not a valid PE file

4. **"Memory error"**
   - File may be too large or corrupted

### Debug Mode
```bash
# Enable verbose output
python -v complete_pe_header_extractor.py malware.exe
```

## Contributing

Feel free to contribute improvements:
- Add support for additional PE features
- Improve error handling
- Add more analysis capabilities
- Optimize performance
- Add support for other file formats

## License

This tool is provided for educational and security research purposes. Use responsibly and in accordance with applicable laws and regulations.

## Disclaimer

This tool is for analysis purposes only. Always ensure you have proper authorization before analyzing files, especially in professional or legal contexts. 