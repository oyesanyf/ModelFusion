//! Directory scaffolding, backup management, and file utilities.

use anyhow::{Context, Result};
use chrono::Local;
use serde::{Deserialize, Serialize};
use std::{
    fs,
    path::{Path, PathBuf},
    time::UNIX_EPOCH,
};
use walkdir::WalkDir;

/// Metadata about a single file or directory.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileInfo {
    pub name: String,
    pub size_bytes: u64,
    pub created: String,
    pub modified: String,
    pub is_file: bool,
    pub is_dir: bool,
    pub extension: String,
    pub parent: String,
}

/// Manages folder structure, backups, and file operations for ModelFusion.
pub struct FolderManager {
    base: PathBuf,
}

impl FolderManager {
    /// Create a new `FolderManager` rooted at `base_path`.
    ///
    /// Immediately ensures all required sub-directories exist.
    pub fn new(base_path: impl AsRef<Path>) -> Result<Self> {
        let base = base_path.as_ref().to_path_buf();
        let mgr = Self { base };
        mgr.ensure_directories()?;
        Ok(mgr)
    }

    /// Ensure all required runtime directories exist under the base path.
    pub fn ensure_directories(&self) -> Result<()> {
        for dir in &[
            "logs",
            "reports",
            "db",
            "config",
            "backups",
            "audio",
            "audio_processing",
        ] {
            let path = self.base.join(dir);
            fs::create_dir_all(&path)
                .with_context(|| format!("Failed to create directory: {}", path.display()))?;
        }
        Ok(())
    }

    /// Create a timestamped backup of the given source paths under `backups/`.
    ///
    /// Returns the path of the created backup directory.
    pub fn create_backup(
        &self,
        source_paths: &[impl AsRef<Path>],
        backup_name: Option<&str>,
    ) -> Result<PathBuf> {
        let name = backup_name.map(str::to_string).unwrap_or_else(|| {
            format!("backup_{}", Local::now().format("%Y%m%d_%H%M%S"))
        });
        let backup_dir = self.base.join("backups").join(&name);
        fs::create_dir_all(&backup_dir)
            .with_context(|| format!("Cannot create backup dir: {}", backup_dir.display()))?;

        for src in source_paths {
            let src = src.as_ref();
            if !src.exists() {
                log::warn!("Backup source does not exist, skipping: {}", src.display());
                continue;
            }
            let dest = backup_dir.join(src.file_name().unwrap_or_default());
            if src.is_file() {
                fs::copy(src, &dest)
                    .with_context(|| format!("Failed to copy {} → {}", src.display(), dest.display()))?;
            } else if src.is_dir() {
                Self::copy_dir_recursive(src, &dest)?;
            }
        }
        log::info!("Backup created at: {}", backup_dir.display());
        Ok(backup_dir)
    }

    /// Remove old backup directories, keeping only the `max_backups` most recent.
    pub fn cleanup_old_backups(&self, max_backups: usize) -> Result<()> {
        let backup_dir = self.base.join("backups");
        if !backup_dir.exists() {
            return Ok(());
        }
        let mut dirs: Vec<PathBuf> = fs::read_dir(&backup_dir)?
            .filter_map(|e| e.ok())
            .map(|e| e.path())
            .filter(|p| p.is_dir())
            .collect();

        // Sort by modification time descending (newest first)
        dirs.sort_by(|a, b| {
            let mt_a = a.metadata().and_then(|m| m.modified()).ok();
            let mt_b = b.metadata().and_then(|m| m.modified()).ok();
            mt_b.cmp(&mt_a)
        });

        for old in dirs.into_iter().skip(max_backups) {
            log::info!("Removing old backup: {}", old.display());
            fs::remove_dir_all(&old)
                .with_context(|| format!("Failed to remove old backup: {}", old.display()))?;
        }
        Ok(())
    }

    /// Get detailed metadata about a file or directory.
    pub fn get_file_info(&self, path: impl AsRef<Path>) -> Result<FileInfo> {
        let path = path.as_ref();
        let meta = fs::metadata(path)
            .with_context(|| format!("Cannot stat: {}", path.display()))?;

        let to_rfc = |st: std::time::SystemTime| -> String {
            st.duration_since(UNIX_EPOCH)
                .map(|d| {
                    let dt = chrono::DateTime::<Local>::from(
                        std::time::SystemTime::UNIX_EPOCH + d,
                    );
                    dt.to_rfc3339()
                })
                .unwrap_or_default()
        };

        Ok(FileInfo {
            name: path
                .file_name()
                .map(|n| n.to_string_lossy().to_string())
                .unwrap_or_default(),
            size_bytes: meta.len(),
            created: meta.created().map(to_rfc).unwrap_or_default(),
            modified: meta.modified().map(to_rfc).unwrap_or_default(),
            is_file: meta.is_file(),
            is_dir: meta.is_dir(),
            extension: path
                .extension()
                .map(|e| e.to_string_lossy().to_string())
                .unwrap_or_default(),
            parent: path
                .parent()
                .map(|p| p.to_string_lossy().to_string())
                .unwrap_or_default(),
        })
    }

    /// List files in `directory` matching a glob-like `pattern`.
    ///
    /// If `recursive` is `true`, all sub-directories are traversed.
    /// `pattern` is matched against the file name only (not the full path).
    pub fn list_files(
        &self,
        directory: impl AsRef<Path>,
        pattern: &str,
        recursive: bool,
    ) -> Vec<PathBuf> {
        let dir = directory.as_ref();
        if !dir.exists() {
            return vec![];
        }
        let walker: Box<dyn Iterator<Item = walkdir::DirEntry>> = if recursive {
            Box::new(WalkDir::new(dir).into_iter().filter_map(|e| e.ok()))
        } else {
            Box::new(
                WalkDir::new(dir)
                    .max_depth(1)
                    .into_iter()
                    .filter_map(|e| e.ok()),
            )
        };

        walker
            .filter(|e| e.path().is_file())
            .filter(|e| {
                if pattern == "*" {
                    return true;
                }
                e.file_name()
                    .to_string_lossy()
                    .contains(pattern.trim_start_matches('*').trim_end_matches('*'))
            })
            .map(|e| e.path().to_path_buf())
            .collect()
    }

    /// Safely delete a file (does nothing if it does not exist).
    pub fn safe_delete(&self, path: impl AsRef<Path>) -> Result<bool> {
        let path = path.as_ref();
        if !path.exists() {
            return Ok(false);
        }
        fs::remove_file(path)
            .with_context(|| format!("Failed to delete: {}", path.display()))?;
        Ok(true)
    }

    /// Recursively calculate the total size of a directory in bytes.
    pub fn directory_size(&self, directory: impl AsRef<Path>) -> u64 {
        WalkDir::new(directory.as_ref())
            .into_iter()
            .filter_map(|e| e.ok())
            .filter(|e| e.path().is_file())
            .map(|e| e.metadata().map(|m| m.len()).unwrap_or(0))
            .sum()
    }

    /// Format a byte count as a human-readable string (B, KB, MB, GB, TB).
    pub fn format_size(size_bytes: u64) -> String {
        const UNITS: &[&str] = &["B", "KB", "MB", "GB", "TB"];
        let mut value = size_bytes as f64;
        let mut unit_idx = 0;
        while value >= 1024.0 && unit_idx < UNITS.len() - 1 {
            value /= 1024.0;
            unit_idx += 1;
        }
        format!("{:.1} {}", value, UNITS[unit_idx])
    }

    // ── private helpers ────────────────────────────────────────────────────────

    fn copy_dir_recursive(src: &Path, dst: &Path) -> Result<()> {
        fs::create_dir_all(dst)?;
        for entry in fs::read_dir(src)? {
            let entry = entry?;
            let src_path = entry.path();
            let dst_path = dst.join(entry.file_name());
            if src_path.is_dir() {
                Self::copy_dir_recursive(&src_path, &dst_path)?;
            } else {
                fs::copy(&src_path, &dst_path)?;
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    #[test]
    fn format_size_units() {
        assert_eq!(FolderManager::format_size(0), "0.0 B");
        assert_eq!(FolderManager::format_size(1024), "1.0 KB");
        assert_eq!(FolderManager::format_size(1024 * 1024), "1.0 MB");
        assert_eq!(FolderManager::format_size(1024 * 1024 * 1024), "1.0 GB");
    }

    #[test]
    fn ensure_dirs_creates_structure() {
        let tmp = std::env::temp_dir().join("mf_test_utils");
        let _ = fs::remove_dir_all(&tmp);
        let mgr = FolderManager::new(&tmp).unwrap();
        assert!(tmp.join("logs").exists());
        assert!(tmp.join("db").exists());
        assert!(tmp.join("backups").exists());
        drop(mgr);
        let _ = fs::remove_dir_all(&tmp);
    }
}
