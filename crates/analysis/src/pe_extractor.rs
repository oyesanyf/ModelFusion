//! Complete PE header extractor using goblin.

use anyhow::{Context, Result};
use chrono::Utc;
use goblin::pe::PE;
use md5::Md5;
use serde::{Deserialize, Serialize};
use sha1::Sha1;
use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};
use std::fs::File;
use std::io::Read;
use std::path::Path;

/// Section details in PE file.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SectionInfo {
    pub name: String,
    pub virtual_address: String,
    pub virtual_size: u32,
    pub raw_data_size: u32,
    pub entropy: f64,
    pub characteristics: String,
    pub flags: Vec<String>,
}

/// Summary statistics of the PE file.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SummaryStats {
    pub total_sections: usize,
    pub total_imports: usize,
    pub total_exports: usize,
    pub suspicious_apis: Vec<SuspiciousApiCall>,
    pub high_entropy_sections: Vec<HighEntropySection>,
}

/// Suspicious API call descriptor.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SuspiciousApiCall {
    pub dll: String,
    pub api: String,
}

/// High entropy section descriptor.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HighEntropySection {
    pub name: String,
    pub entropy: f64,
}

/// Comprehensive analysis result of a PE binary.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PeAnalysis {
    pub file_path: String,
    pub file_size: u64,
    pub file_hashes: HashMap<String, String>,
    pub analysis_timestamp: String,
    pub machine: String,
    pub machine_type: String,
    pub number_of_sections: u16,
    pub entry_point: String,
    pub image_base: String,
    pub size_of_image: u32,
    pub subsystem: String,
    pub subsystem_type: String,
    pub sections: Vec<SectionInfo>,
    pub imports: HashMap<String, Vec<String>>,
    pub exports: Vec<String>,
    pub summary: SummaryStats,
}

/// Extracts detailed information from a Windows Portable Executable.
pub struct CompletePEHeaderExtractor {
    suspicious_apis: HashSet<String>,
    machine_types: HashMap<u16, String>,
    subsystem_types: HashMap<u16, String>,
}

impl Default for CompletePEHeaderExtractor {
    fn default() -> Self {
        Self::new()
    }
}

impl CompletePEHeaderExtractor {
    /// Create a new extractor.
    pub fn new() -> Self {
        let suspicious_apis = vec![
            "VirtualAlloc", "VirtualAllocEx", "CreateRemoteThread", "WriteProcessMemory",
            "ReadProcessMemory", "OpenProcess", "CreateProcess", "ShellExecute",
            "WinExec", "system", "CreateFile", "WriteFile", "ReadFile",
            "RegCreateKey", "RegSetValue", "InternetOpen", "HttpOpenRequest",
            "URLDownloadToFile", "GetProcAddress", "LoadLibrary", "GetModuleHandle",
            "NtCreateThreadEx", "NtAllocateVirtualMemory", "NtWriteVirtualMemory",
        ]
        .into_iter()
        .map(|s| s.to_string())
        .collect();

        let mut machine_types = HashMap::new();
        machine_types.insert(0x0, "UNKNOWN".to_string());
        machine_types.insert(0x8664, "AMD64".to_string());
        machine_types.insert(0x1c0, "ARM".to_string());
        machine_types.insert(0xaa64, "ARM64".to_string());
        machine_types.insert(0x14c, "I386".to_string());
        machine_types.insert(0x200, "IA64".to_string());

        let mut subsystem_types = HashMap::new();
        subsystem_types.insert(0, "UNKNOWN".to_string());
        subsystem_types.insert(1, "NATIVE".to_string());
        subsystem_types.insert(2, "WINDOWS_GUI".to_string());
        subsystem_types.insert(3, "WINDOWS_CUI".to_string());
        subsystem_types.insert(8, "NATIVE_WINDOWS".to_string());
        subsystem_types.insert(10, "EFI_APPLICATION".to_string());

        Self {
            suspicious_apis,
            machine_types,
            subsystem_types,
        }
    }

    /// Calculate entropy of a slice of bytes.
    pub fn get_entropy(&self, data: &[u8]) -> f64 {
        if data.is_empty() {
            return 0.0;
        }
        let mut occurrences = [0usize; 256];
        for &byte in data {
            occurrences[byte as usize] += 1;
        }
        let mut entropy = 0.0;
        let data_len = data.len() as f64;
        for &count in &occurrences {
            if count > 0 {
                let p_x = count as f64 / data_len;
                entropy -= p_x * p_x.log2();
            }
        }
        entropy
    }

    /// Calculate file hashes.
    pub fn get_file_hashes(&self, file_path: &Path) -> Result<HashMap<String, String>> {
        let mut file = File::open(file_path)?;
        let mut data = Vec::new();
        file.read_to_end(&mut data)?;

        let mut md5 = Md5::new();
        md5.update(&data);
        let md5_hash = hex::encode(md5.finalize());

        let mut sha1 = Sha1::new();
        sha1.update(&data);
        let sha1_hash = hex::encode(sha1.finalize());

        let mut sha256 = Sha256::new();
        sha256.update(&data);
        let sha256_hash = hex::encode(sha256.finalize());

        let mut hashes = HashMap::new();
        hashes.insert("md5".to_string(), md5_hash);
        hashes.insert("sha1".to_string(), sha1_hash);
        hashes.insert("sha256".to_string(), sha256_hash);

        Ok(hashes)
    }

    /// Extract all PE headers and information.
    pub fn extract_complete_pe_headers(&self, file_path: impl AsRef<Path>) -> Result<PeAnalysis> {
        let path = file_path.as_ref();
        let mut file = File::open(path)?;
        let mut buffer = Vec::new();
        file.read_to_end(&mut buffer)?;

        let pe = PE::parse(&buffer).context("Failed to parse PE binary")?;

        let file_hashes = self.get_file_hashes(path).unwrap_or_default();
        let file_size = path.metadata()?.len();

        let coff = pe.header.coff_header;
        let machine = format!("0x{:X}", coff.machine);
        let machine_type = self.machine_types.get(&coff.machine).cloned().unwrap_or_else(|| "UNKNOWN".to_string());
        let number_of_sections = coff.number_of_sections;

        let mut entry_point = "0x0".to_string();
        let mut image_base = "0x0".to_string();
        let mut size_of_image = 0u32;
        let mut subsystem = "0x0".to_string();
        let mut subsystem_type = "UNKNOWN".to_string();

        if let Some(opt) = pe.header.optional_header {
            entry_point = format!("0x{:X}", opt.standard_fields.address_of_entry_point);
            image_base = format!("0x{:X}", opt.windows_fields.image_base);
            size_of_image = opt.windows_fields.size_of_image;
            let subsystem_val = opt.windows_fields.subsystem;
            subsystem = format!("0x{:X}", subsystem_val);
            subsystem_type = self.subsystem_types.get(&subsystem_val).cloned().unwrap_or_else(|| "UNKNOWN".to_string());
        }

        // Section analysis
        let mut sections = Vec::new();
        for sec in &pe.sections {
            // Safe section name conversion
            let name = String::from_utf8_lossy(&sec.name)
                .trim_end_matches('\0')
                .to_string();

            // Extract section data from buffer to calculate entropy
            let start = sec.pointer_to_raw_data as usize;
            let end = (sec.pointer_to_raw_data + sec.size_of_raw_data) as usize;
            let sec_data = if start < buffer.len() && end <= buffer.len() {
                &buffer[start..end]
            } else {
                &[]
            };

            let entropy = self.get_entropy(sec_data);
            let flags = self.get_section_flags(sec.characteristics);

            sections.push(SectionInfo {
                name,
                virtual_address: format!("0x{:X}", sec.virtual_address),
                virtual_size: sec.virtual_size,
                raw_data_size: sec.size_of_raw_data,
                entropy,
                characteristics: format!("0x{:X}", sec.characteristics),
                flags,
            });
        }

        // Import analysis
        let mut imports = HashMap::new();
        let mut total_imports = 0;
        for imp in &pe.imports {
            let dll = imp.dll.to_string();
            let name = imp.name.to_string();
            imports.entry(dll).or_insert_with(Vec::new).push(name);
            total_imports += 1;
        }

        // Export analysis
        let mut exports = Vec::new();
        for exp in &pe.exports {
            if let Some(name) = exp.name {
                exports.push(name.to_string());
            }
        }

        // Calculate summary
        let mut suspicious_apis = Vec::new();
        for (dll, apis) in &imports {
            for api in apis {
                if self.suspicious_apis.contains(api) {
                    suspicious_apis.push(SuspiciousApiCall {
                        dll: dll.clone(),
                        api: api.clone(),
                    });
                }
            }
        }

        let mut high_entropy_sections = Vec::new();
        for sec in &sections {
            if sec.entropy > 7.0 {
                high_entropy_sections.push(HighEntropySection {
                    name: sec.name.clone(),
                    entropy: sec.entropy,
                });
            }
        }

        let summary = SummaryStats {
            total_sections: sections.len(),
            total_imports,
            total_exports: exports.len(),
            suspicious_apis,
            high_entropy_sections,
        };

        Ok(PeAnalysis {
            file_path: path.to_string_lossy().to_string(),
            file_size,
            file_hashes,
            analysis_timestamp: Utc::now().to_rfc3339(),
            machine,
            machine_type,
            number_of_sections,
            entry_point,
            image_base,
            size_of_image,
            subsystem,
            subsystem_type,
            sections,
            imports,
            exports,
            summary,
        })
    }

    /// Helper to convert section characteristic flags into readable strings.
    fn get_section_flags(&self, char: u32) -> Vec<String> {
        let mut flags = Vec::new();
        if char & 0x00000020 != 0 {
            flags.push("CNT_CODE".to_string());
        }
        if char & 0x00000040 != 0 {
            flags.push("CNT_INITIALIZED_DATA".to_string());
        }
        if char & 0x00000080 != 0 {
            flags.push("CNT_UNINITIALIZED_DATA".to_string());
        }
        if char & 0x20000000 != 0 {
            flags.push("MEM_EXECUTE".to_string());
        }
        if char & 0x40000000 != 0 {
            flags.push("MEM_READ".to_string());
        }
        if char & 0x80000000 != 0 {
            flags.push("MEM_WRITE".to_string());
        }
        flags
    }
}
