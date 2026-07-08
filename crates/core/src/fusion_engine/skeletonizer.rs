use std::path::{Path, PathBuf};
use std::fs;

/// Simple regex-based skeletonizer to extract code structure (signatures, classes, imports)
/// and strip function bodies to compress the context size by 90%+.
pub struct WorkspaceSkeletonizer {
    max_file_size_bytes: usize,
}

impl WorkspaceSkeletonizer {
    pub fn new() -> Self {
        Self {
            max_file_size_bytes: 256 * 1024, // 256 KB limit per file to avoid locking
        }
    }

    /// Recursively scan a folder and build a compact structure map of all source code files.
    pub fn build_skeleton_map(&self, root_dir: &Path, max_total_chars: usize) -> String {
        let mut map = String::new();
        map.push_str("=== WORKSPACE SKELETON MAP ===\n");
        map.push_str("Below is the structural signature of the workspace files. Code bodies have been omitted to save context tokens:\n\n");

        let mut files_scanned = 0;
        let mut total_chars = map.len();

        let extensions = vec!["rs", "ts", "js", "py", "go", "java", "cpp", "cs", "h", "json"];
        let mut walk_stack = vec![root_dir.to_path_buf()];

        while let Some(current_path) = walk_stack.pop() {
            if total_chars >= max_total_chars {
                break;
            }

            if let Ok(entries) = fs::read_dir(&current_path) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    let metadata = match entry.metadata() {
                        Ok(m) => m,
                        Err(_) => continue,
                    };

                    if metadata.is_dir() {
                        let dir_name = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
                        if dir_name == "node_modules"
                            || dir_name == ".git"
                            || dir_name == "target"
                            || dir_name == "dist"
                            || dir_name == "build"
                            || dir_name == ".agents"
                        {
                            continue;
                        }
                        walk_stack.push(path);
                    } else if metadata.is_file() {
                        if let Some(ext) = path.extension().and_then(|s| s.to_str()) {
                            if extensions.contains(&ext) && metadata.len() < self.max_file_size_bytes as u64 {
                                if let Ok(relative) = path.strip_prefix(root_dir) {
                                    if let Ok(content) = fs::read_to_string(&path) {
                                        let skeleton = self.skeletonize_file(&content, ext);
                                        let file_header = format!("--- File: {} ---\n{}\n\n", relative.display(), skeleton);
                                        if total_chars + file_header.len() < max_total_chars {
                                            map.push_str(&file_header);
                                            total_chars += file_header.len();
                                            files_scanned += 1;
                                        } else {
                                            break;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        map.push_str(&format!("=== End of Map (Scanned {} files) ===\n", files_scanned));
        map
    }

    /// Extract definitions (struct, class, fn, impl, import) and omit method bodies.
    fn skeletonize_file(&self, content: &str, ext: &str) -> String {
        let mut result = String::new();
        let lines: Vec<&str> = content.lines().collect();
        let mut in_long_comment = false;

        for line in lines {
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }

            // Skip comment blocks
            if ext == "rs" || ext == "ts" || ext == "js" || ext == "go" || ext == "cpp" || ext == "java" || ext == "cs" {
                if trimmed.starts_with("/*") {
                    in_long_comment = !trimmed.contains("*/");
                    continue;
                }
                if in_long_comment {
                    if trimmed.contains("*/") {
                        in_long_comment = false;
                    }
                    continue;
                }
                if trimmed.starts_with("//") {
                    continue;
                }
            } else if ext == "py" {
                if trimmed.starts_with("#") {
                    continue;
                }
                if trimmed.starts_with("\"\"\"") || trimmed.starts_with("'''") {
                    in_long_comment = !trimmed.ends_with("\"\"\"") && !trimmed.ends_with("'''");
                    continue;
                }
                if in_long_comment {
                    if trimmed.ends_with("\"\"\"") || trimmed.ends_with("'''") {
                        in_long_comment = false;
                    }
                    continue;
                }
            }

            // Detect signature keywords
            let is_signature = match ext {
                "rs" => {
                    trimmed.starts_with("pub ")
                        || trimmed.starts_with("fn ")
                        || trimmed.starts_with("impl ")
                        || trimmed.starts_with("struct ")
                        || trimmed.starts_with("enum ")
                        || trimmed.starts_with("trait ")
                        || trimmed.starts_with("mod ")
                        || trimmed.starts_with("use ")
                }
                "ts" | "js" => {
                    trimmed.starts_with("export ")
                        || trimmed.starts_with("import ")
                        || trimmed.starts_with("class ")
                        || trimmed.starts_with("interface ")
                        || trimmed.starts_with("function ")
                        || trimmed.starts_with("const ") && (trimmed.contains("=>") || trimmed.contains("function"))
                }
                "py" => {
                    trimmed.starts_with("def ")
                        || trimmed.starts_with("class ")
                        || trimmed.starts_with("import ")
                        || trimmed.starts_with("from ")
                }
                _ => {
                    trimmed.starts_with("class ")
                        || trimmed.starts_with("struct ")
                        || trimmed.starts_with("public ")
                        || trimmed.starts_with("private ")
                        || trimmed.starts_with("protected ")
                        || trimmed.contains("fn ")
                        || trimmed.starts_with("#import")
                        || trimmed.starts_with("using ")
                }
            };

            if is_signature {
                // If the signature ends with opening brace, close it right away to summarize
                let cleaned = if trimmed.ends_with('{') {
                    format!("{} {{ ... }}", &trimmed[..trimmed.len() - 1].trim())
                } else if trimmed.ends_with(':') && ext == "py" {
                    format!("{} ...", &trimmed[..trimmed.len() - 1].trim())
                } else {
                    trimmed.to_string()
                };

                // Maintain basic indent levels (up to 4 spaces for legibility)
                let leading_spaces = line.len() - line.trim_start().len();
                let indent = " ".repeat(leading_spaces.min(4));
                result.push_str(&format!("{}{}\n", indent, cleaned));
            }
        }

        result
    }
}
