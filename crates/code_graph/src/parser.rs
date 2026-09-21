//! Multi-Language AST Extraction Engine using Tree-Sitter
//!
//! Supports Rust, TypeScript/JavaScript, and Python.
//! Extracts definitions (functions, structs, classes, traits, interfaces),
//! call hierarchy edges, implementations, and symbol references.

use anyhow::{anyhow, Result};
use tree_sitter::{Language, Node, Parser};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LanguageKind {
    Rust,
    TypeScript,
    Python,
}

impl LanguageKind {
    pub fn from_extension(ext: &str) -> Option<Self> {
        match ext.to_ascii_lowercase().as_str() {
            "rs" => Some(LanguageKind::Rust),
            "ts" | "tsx" | "js" | "jsx" | "mjs" | "cjs" => Some(LanguageKind::TypeScript),
            "py" => Some(LanguageKind::Python),
            _ => None,
        }
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            LanguageKind::Rust => "rust",
            LanguageKind::TypeScript => "typescript",
            LanguageKind::Python => "python",
        }
    }

    pub fn tree_sitter_language(&self, is_tsx: bool) -> Language {
        match self {
            LanguageKind::Rust => tree_sitter_rust::language(),
            LanguageKind::TypeScript => {
                if is_tsx {
                    tree_sitter_typescript::language_tsx()
                } else {
                    tree_sitter_typescript::language_typescript()
                }
            }
            LanguageKind::Python => tree_sitter_python::language(),
        }
    }
}

/// Extracted symbol definition.
#[derive(Debug, Clone, PartialEq)]
pub struct SymbolDef {
    pub name: String,
    pub qualified_name: String,
    pub kind: String, // "function", "method", "struct", "class", "interface", "trait", "enum", "type_alias"
    pub signature: Option<String>,
    pub docstring: Option<String>,
    pub start_line: usize,
    pub start_col: usize,
    pub end_line: usize,
    pub end_col: usize,
    pub parent_name: Option<String>,
    pub visibility: String,
}

/// Extracted call edge.
#[derive(Debug, Clone, PartialEq)]
pub struct CallEdge {
    pub caller_name: String,
    pub callee_name: String,
    pub line: usize,
    pub col: usize,
}

/// Extracted implementation edge (e.g. Trait implementation or Class interface).
#[derive(Debug, Clone, PartialEq)]
pub struct ImplEdge {
    pub symbol_name: String,
    pub interface_name: String,
    pub target_type: String,
}

/// Extracted symbol reference edge.
#[derive(Debug, Clone, PartialEq)]
pub struct RefEdge {
    pub symbol_name: String,
    pub line: usize,
    pub col: usize,
    pub ref_kind: String, // "call", "type_usage", "read", "write"
}

/// Complete AST parse result for a single source file.
#[derive(Debug, Default, Clone)]
pub struct ParsedFileEntities {
    pub symbols: Vec<SymbolDef>,
    pub calls: Vec<CallEdge>,
    pub implementations: Vec<ImplEdge>,
    pub references: Vec<RefEdge>,
}

pub struct AstExtractor {
    rust_parser: Parser,
    ts_parser: Parser,
    tsx_parser: Parser,
    py_parser: Parser,
}

impl AstExtractor {
    pub fn new() -> Result<Self> {
        let mut rust_parser = Parser::new();
        rust_parser
            .set_language(&tree_sitter_rust::language())
            .map_err(|e| anyhow!("Failed to set Rust grammar: {:?}", e))?;

        let mut ts_parser = Parser::new();
        ts_parser
            .set_language(&tree_sitter_typescript::language_typescript())
            .map_err(|e| anyhow!("Failed to set TypeScript grammar: {:?}", e))?;

        let mut tsx_parser = Parser::new();
        tsx_parser
            .set_language(&tree_sitter_typescript::language_tsx())
            .map_err(|e| anyhow!("Failed to set TSX grammar: {:?}", e))?;

        let mut py_parser = Parser::new();
        py_parser
            .set_language(&tree_sitter_python::language())
            .map_err(|e| anyhow!("Failed to set Python grammar: {:?}", e))?;

        Ok(Self {
            rust_parser,
            ts_parser,
            tsx_parser,
            py_parser,
        })
    }

    pub fn parse(
        &mut self,
        source: &str,
        language: LanguageKind,
        is_tsx: bool,
    ) -> Result<ParsedFileEntities> {
        let source_bytes = source.as_bytes();
        let tree = match language {
            LanguageKind::Rust => self.rust_parser.parse(source_bytes, None),
            LanguageKind::TypeScript => {
                if is_tsx {
                    self.tsx_parser.parse(source_bytes, None)
                } else {
                    self.ts_parser.parse(source_bytes, None)
                }
            }
            LanguageKind::Python => self.py_parser.parse(source_bytes, None),
        }
        .ok_or_else(|| anyhow!("Tree-sitter parse failed for language {:?}", language))?;

        let mut entities = ParsedFileEntities::default();
        let root = tree.root_node();

        match language {
            LanguageKind::Rust => {
                let mut ctx = RustParseContext {
                    source: source_bytes,
                    current_parent: None,
                    current_impl_trait: None,
                    current_impl_target: None,
                };
                self.extract_rust_node(root, &mut ctx, &mut entities);
            }
            LanguageKind::TypeScript => {
                let mut ctx = TsParseContext {
                    source: source_bytes,
                    current_parent: None,
                };
                self.extract_ts_node(root, &mut ctx, &mut entities);
            }
            LanguageKind::Python => {
                let mut ctx = PyParseContext {
                    source: source_bytes,
                    current_parent: None,
                };
                self.extract_py_node(root, &mut ctx, &mut entities);
            }
        }

        Ok(entities)
    }

    // -----------------------------------------------------------------------
    // Rust Extraction
    // -----------------------------------------------------------------------
    fn extract_rust_node<'a>(
        &self,
        node: Node<'a>,
        ctx: &mut RustParseContext<'a>,
        out: &mut ParsedFileEntities,
    ) {
        let kind = node.kind();
        match kind {
            "struct_item" => {
                if let Some(name_node) = node.child_by_field_name("name") {
                    let name = node_text(name_node, ctx.source);
                    let (start_line, start_col) = point_to_1indexed(node.start_position());
                    let (end_line, end_col) = point_to_1indexed(node.end_position());
                    let docstring = extract_preceding_docstrings(node, ctx.source);
                    let vis = extract_rust_visibility(node, ctx.source);
                    let qual_name = build_qualified_name(ctx.current_parent.as_deref(), &name);

                    out.symbols.push(SymbolDef {
                        name: name.clone(),
                        qualified_name: qual_name.clone(),
                        kind: "struct".to_string(),
                        signature: Some(format!("struct {}", name)),
                        docstring,
                        start_line,
                        start_col,
                        end_line,
                        end_col,
                        parent_name: ctx.current_parent.clone(),
                        visibility: vis,
                    });
                }
            }
            "enum_item" => {
                if let Some(name_node) = node.child_by_field_name("name") {
                    let name = node_text(name_node, ctx.source);
                    let (start_line, start_col) = point_to_1indexed(node.start_position());
                    let (end_line, end_col) = point_to_1indexed(node.end_position());
                    let docstring = extract_preceding_docstrings(node, ctx.source);
                    let vis = extract_rust_visibility(node, ctx.source);
                    let qual_name = build_qualified_name(ctx.current_parent.as_deref(), &name);

                    out.symbols.push(SymbolDef {
                        name: name.clone(),
                        qualified_name: qual_name,
                        kind: "enum".to_string(),
                        signature: Some(format!("enum {}", name)),
                        docstring,
                        start_line,
                        start_col,
                        end_line,
                        end_col,
                        parent_name: ctx.current_parent.clone(),
                        visibility: vis,
                    });
                }
            }
            "trait_item" => {
                if let Some(name_node) = node.child_by_field_name("name") {
                    let name = node_text(name_node, ctx.source);
                    let (start_line, start_col) = point_to_1indexed(node.start_position());
                    let (end_line, end_col) = point_to_1indexed(node.end_position());
                    let docstring = extract_preceding_docstrings(node, ctx.source);
                    let vis = extract_rust_visibility(node, ctx.source);
                    let qual_name = build_qualified_name(ctx.current_parent.as_deref(), &name);

                    out.symbols.push(SymbolDef {
                        name: name.clone(),
                        qualified_name: qual_name,
                        kind: "trait".to_string(),
                        signature: Some(format!("trait {}", name)),
                        docstring,
                        start_line,
                        start_col,
                        end_line,
                        end_col,
                        parent_name: ctx.current_parent.clone(),
                        visibility: vis,
                    });
                }
            }
            "type_item" => {
                if let Some(name_node) = node.child_by_field_name("name") {
                    let name = node_text(name_node, ctx.source);
                    let (start_line, start_col) = point_to_1indexed(node.start_position());
                    let (end_line, end_col) = point_to_1indexed(node.end_position());
                    let vis = extract_rust_visibility(node, ctx.source);
                    let qual_name = build_qualified_name(ctx.current_parent.as_deref(), &name);

                    out.symbols.push(SymbolDef {
                        name: name.clone(),
                        qualified_name: qual_name,
                        kind: "type_alias".to_string(),
                        signature: Some(format!("type {}", name)),
                        docstring: extract_preceding_docstrings(node, ctx.source),
                        start_line,
                        start_col,
                        end_line,
                        end_col,
                        parent_name: ctx.current_parent.clone(),
                        visibility: vis,
                    });
                }
            }
            "impl_item" => {
                let trait_node = node.child_by_field_name("trait");
                let type_node = node.child_by_field_name("type");

                let trait_name = trait_node.map(|n| node_text(n, ctx.source));
                let target_name = type_node.map(|n| node_text(n, ctx.source));

                let old_target = ctx.current_impl_target.clone();
                let old_trait = ctx.current_impl_trait.clone();
                let old_parent = ctx.current_parent.clone();

                if let Some(ref target) = target_name {
                    ctx.current_impl_target = Some(target.clone());
                    ctx.current_parent = Some(target.clone());
                }
                if let Some(ref tr) = trait_name {
                    ctx.current_impl_trait = Some(tr.clone());
                    if let Some(ref target) = target_name {
                        out.implementations.push(ImplEdge {
                            symbol_name: target.clone(),
                            interface_name: tr.clone(),
                            target_type: target.clone(),
                        });
                    }
                }

                // Recursively parse children inside impl block
                let mut cursor = node.walk();
                for child in node.children(&mut cursor) {
                    self.extract_rust_node(child, ctx, out);
                }

                ctx.current_impl_target = old_target;
                ctx.current_impl_trait = old_trait;
                ctx.current_parent = old_parent;
                return;
            }
            "function_item" => {
                if let Some(name_node) = node.child_by_field_name("name") {
                    let name = node_text(name_node, ctx.source);
                    let (start_line, start_col) = point_to_1indexed(node.start_position());
                    let (end_line, end_col) = point_to_1indexed(node.end_position());
                    let docstring = extract_preceding_docstrings(node, ctx.source);
                    let vis = extract_rust_visibility(node, ctx.source);

                    let is_method = ctx.current_parent.is_some();
                    let kind_str = if is_method { "method" } else { "function" };
                    let qual_name = build_qualified_name(ctx.current_parent.as_deref(), &name);

                    // Extract signature
                    let params = node
                        .child_by_field_name("parameters")
                        .map(|n| node_text(n, ctx.source))
                        .unwrap_or_else(|| "()".to_string());
                    let ret_type = node
                        .child_by_field_name("return_type")
                        .map(|n| format!(" -> {}", node_text(n, ctx.source).trim_start_matches("->").trim()))
                        .unwrap_or_default();
                    let sig = format!("fn {}{}{}", name, params, ret_type);

                    out.symbols.push(SymbolDef {
                        name: name.clone(),
                        qualified_name: qual_name.clone(),
                        kind: kind_str.to_string(),
                        signature: Some(sig),
                        docstring,
                        start_line,
                        start_col,
                        end_line,
                        end_col,
                        parent_name: ctx.current_parent.clone(),
                        visibility: vis,
                    });

                    // Parse calls inside function body
                    if let Some(body) = node.child_by_field_name("body") {
                        let old_parent = ctx.current_parent.clone();
                        ctx.current_parent = Some(qual_name);
                        self.extract_rust_calls(body, ctx, out);
                        ctx.current_parent = old_parent;
                    }
                    return;
                }
            }
            _ => {}
        }

        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            self.extract_rust_node(child, ctx, out);
        }
    }

    fn extract_rust_calls<'a>(
        &self,
        node: Node<'a>,
        ctx: &RustParseContext<'a>,
        out: &mut ParsedFileEntities,
    ) {
        if node.kind() == "call_expression" {
            if let Some(func_node) = node.child_by_field_name("function") {
                let callee_raw = node_text(func_node, ctx.source);
                let (line, col) = point_to_1indexed(node.start_position());
                let caller_name = ctx.current_parent.clone().unwrap_or_else(|| "global".to_string());

                // Normalize callee: strip Type:: or obj.
                let callee_name = extract_callee_leaf_name(&callee_raw);
                out.calls.push(CallEdge {
                    caller_name,
                    callee_name: callee_name.clone(),
                    line,
                    col,
                });

                out.references.push(RefEdge {
                    symbol_name: callee_name,
                    line,
                    col,
                    ref_kind: "call".to_string(),
                });
            }
        } else if node.kind() == "type_identifier" {
            let type_name = node_text(node, ctx.source);
            let (line, col) = point_to_1indexed(node.start_position());
            out.references.push(RefEdge {
                symbol_name: type_name,
                line,
                col,
                ref_kind: "type_usage".to_string(),
            });
        }

        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            self.extract_rust_calls(child, ctx, out);
        }
    }

    // -----------------------------------------------------------------------
    // TypeScript / JavaScript Extraction
    // -----------------------------------------------------------------------
    fn extract_ts_node<'a>(
        &self,
        node: Node<'a>,
        ctx: &mut TsParseContext<'a>,
        out: &mut ParsedFileEntities,
    ) {
        let kind = node.kind();
        match kind {
            "class_declaration" => {
                if let Some(name_node) = node.child_by_field_name("name") {
                    let name = node_text(name_node, ctx.source);
                    let (start_line, start_col) = point_to_1indexed(node.start_position());
                    let (end_line, end_col) = point_to_1indexed(node.end_position());
                    let docstring = extract_preceding_docstrings(node, ctx.source);
                    let qual_name = build_qualified_name(ctx.current_parent.as_deref(), &name);

                    out.symbols.push(SymbolDef {
                        name: name.clone(),
                        qualified_name: qual_name.clone(),
                        kind: "class".to_string(),
                        signature: Some(format!("class {}", name)),
                        docstring,
                        start_line,
                        start_col,
                        end_line,
                        end_col,
                        parent_name: ctx.current_parent.clone(),
                        visibility: "public".to_string(),
                    });

                    // Check for implements / extends
                    let mut ch_cursor = node.walk();
                    for child in node.children(&mut ch_cursor) {
                        if child.kind() == "class_heritage" {
                            let text = node_text(child, ctx.source);
                            if text.contains("implements") {
                                if let Some(after) = text.split("implements").nth(1) {
                                    for part in after.split('{').next().unwrap_or("").split(',') {
                                        let iface = part.trim();
                                        if !iface.is_empty() {
                                            out.implementations.push(ImplEdge {
                                                symbol_name: name.clone(),
                                                interface_name: iface.to_string(),
                                                target_type: name.clone(),
                                            });
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Traverse class body
                    if let Some(body) = node.child_by_field_name("body") {
                        let old_parent = ctx.current_parent.clone();
                        ctx.current_parent = Some(name.clone());
                        let mut cursor = body.walk();
                        for child in body.children(&mut cursor) {
                            self.extract_ts_node(child, ctx, out);
                        }
                        ctx.current_parent = old_parent;
                        return;
                    }
                }
            }
            "interface_declaration" => {
                if let Some(name_node) = node.child_by_field_name("name") {
                    let name = node_text(name_node, ctx.source);
                    let (start_line, start_col) = point_to_1indexed(node.start_position());
                    let (end_line, end_col) = point_to_1indexed(node.end_position());
                    let qual_name = build_qualified_name(ctx.current_parent.as_deref(), &name);

                    out.symbols.push(SymbolDef {
                        name: name.clone(),
                        qualified_name: qual_name,
                        kind: "interface".to_string(),
                        signature: Some(format!("interface {}", name)),
                        docstring: extract_preceding_docstrings(node, ctx.source),
                        start_line,
                        start_col,
                        end_line,
                        end_col,
                        parent_name: ctx.current_parent.clone(),
                        visibility: "public".to_string(),
                    });
                }
            }
            "type_alias_declaration" => {
                if let Some(name_node) = node.child_by_field_name("name") {
                    let name = node_text(name_node, ctx.source);
                    let (start_line, start_col) = point_to_1indexed(node.start_position());
                    let (end_line, end_col) = point_to_1indexed(node.end_position());
                    let qual_name = build_qualified_name(ctx.current_parent.as_deref(), &name);

                    out.symbols.push(SymbolDef {
                        name: name.clone(),
                        qualified_name: qual_name,
                        kind: "type_alias".to_string(),
                        signature: Some(format!("type {}", name)),
                        docstring: extract_preceding_docstrings(node, ctx.source),
                        start_line,
                        start_col,
                        end_line,
                        end_col,
                        parent_name: ctx.current_parent.clone(),
                        visibility: "public".to_string(),
                    });
                }
            }
            "function_declaration" | "method_definition" => {
                if let Some(name_node) = node.child_by_field_name("name") {
                    let name = node_text(name_node, ctx.source);
                    let (start_line, start_col) = point_to_1indexed(node.start_position());
                    let (end_line, end_col) = point_to_1indexed(node.end_position());
                    let docstring = extract_preceding_docstrings(node, ctx.source);

                    let is_method = ctx.current_parent.is_some();
                    let kind_str = if is_method { "method" } else { "function" };
                    let qual_name = build_qualified_name(ctx.current_parent.as_deref(), &name);

                    let params = node
                        .child_by_field_name("parameters")
                        .map(|n| node_text(n, ctx.source))
                        .unwrap_or_else(|| "()".to_string());
                    let sig = format!("function {}{}", name, params);

                    out.symbols.push(SymbolDef {
                        name: name.clone(),
                        qualified_name: qual_name.clone(),
                        kind: kind_str.to_string(),
                        signature: Some(sig),
                        docstring,
                        start_line,
                        start_col,
                        end_line,
                        end_col,
                        parent_name: ctx.current_parent.clone(),
                        visibility: "public".to_string(),
                    });

                    if let Some(body) = node.child_by_field_name("body") {
                        let old_parent = ctx.current_parent.clone();
                        ctx.current_parent = Some(qual_name);
                        self.extract_ts_calls(body, ctx, out);
                        ctx.current_parent = old_parent;
                    }
                    return;
                }
            }
            _ => {}
        }

        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            self.extract_ts_node(child, ctx, out);
        }
    }

    fn extract_ts_calls<'a>(
        &self,
        node: Node<'a>,
        ctx: &TsParseContext<'a>,
        out: &mut ParsedFileEntities,
    ) {
        if node.kind() == "call_expression" {
            if let Some(func_node) = node.child_by_field_name("function") {
                let callee_raw = node_text(func_node, ctx.source);
                let (line, col) = point_to_1indexed(node.start_position());
                let caller_name = ctx.current_parent.clone().unwrap_or_else(|| "global".to_string());
                let callee_name = extract_callee_leaf_name(&callee_raw);

                out.calls.push(CallEdge {
                    caller_name,
                    callee_name: callee_name.clone(),
                    line,
                    col,
                });

                out.references.push(RefEdge {
                    symbol_name: callee_name,
                    line,
                    col,
                    ref_kind: "call".to_string(),
                });
            }
        }

        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            self.extract_ts_calls(child, ctx, out);
        }
    }

    // -----------------------------------------------------------------------
    // Python Extraction
    // -----------------------------------------------------------------------
    fn extract_py_node<'a>(
        &self,
        node: Node<'a>,
        ctx: &mut PyParseContext<'a>,
        out: &mut ParsedFileEntities,
    ) {
        let kind = node.kind();
        match kind {
            "class_definition" => {
                if let Some(name_node) = node.child_by_field_name("name") {
                    let name = node_text(name_node, ctx.source);
                    let (start_line, start_col) = point_to_1indexed(node.start_position());
                    let (end_line, end_col) = point_to_1indexed(node.end_position());
                    let docstring = extract_python_docstring(node, ctx.source);
                    let qual_name = build_qualified_name(ctx.current_parent.as_deref(), &name);

                    // Check superclasses
                    if let Some(superclasses) = node.child_by_field_name("superclasses") {
                        let text = node_text(superclasses, ctx.source);
                        let clean = text.trim_matches(|c| c == '(' || c == ')');
                        for base in clean.split(',') {
                            let base_trimmed = base.trim();
                            if !base_trimmed.is_empty() {
                                out.implementations.push(ImplEdge {
                                    symbol_name: name.clone(),
                                    interface_name: base_trimmed.to_string(),
                                    target_type: name.clone(),
                                });
                            }
                        }
                    }

                    out.symbols.push(SymbolDef {
                        name: name.clone(),
                        qualified_name: qual_name.clone(),
                        kind: "class".to_string(),
                        signature: Some(format!("class {}:", name)),
                        docstring,
                        start_line,
                        start_col,
                        end_line,
                        end_col,
                        parent_name: ctx.current_parent.clone(),
                        visibility: if name.starts_with('_') { "private".to_string() } else { "public".to_string() },
                    });

                    // Recurse into class body
                    if let Some(body) = node.child_by_field_name("body") {
                        let old_parent = ctx.current_parent.clone();
                        ctx.current_parent = Some(name.clone());
                        let mut cursor = body.walk();
                        for child in body.children(&mut cursor) {
                            self.extract_py_node(child, ctx, out);
                        }
                        ctx.current_parent = old_parent;
                        return;
                    }
                }
            }
            "function_definition" => {
                if let Some(name_node) = node.child_by_field_name("name") {
                    let name = node_text(name_node, ctx.source);
                    let (start_line, start_col) = point_to_1indexed(node.start_position());
                    let (end_line, end_col) = point_to_1indexed(node.end_position());
                    let docstring = extract_python_docstring(node, ctx.source);

                    let is_method = ctx.current_parent.is_some();
                    let kind_str = if is_method { "method" } else { "function" };
                    let qual_name = build_qualified_name(ctx.current_parent.as_deref(), &name);

                    let params = node
                        .child_by_field_name("parameters")
                        .map(|n| node_text(n, ctx.source))
                        .unwrap_or_else(|| "()".to_string());
                    let sig = format!("def {}{}:", name, params);

                    out.symbols.push(SymbolDef {
                        name: name.clone(),
                        qualified_name: qual_name.clone(),
                        kind: kind_str.to_string(),
                        signature: Some(sig),
                        docstring,
                        start_line,
                        start_col,
                        end_line,
                        end_col,
                        parent_name: ctx.current_parent.clone(),
                        visibility: if name.starts_with('_') { "private".to_string() } else { "public".to_string() },
                    });

                    if let Some(body) = node.child_by_field_name("body") {
                        let old_parent = ctx.current_parent.clone();
                        ctx.current_parent = Some(qual_name);
                        self.extract_py_calls(body, ctx, out);
                        ctx.current_parent = old_parent;
                    }
                    return;
                }
            }
            _ => {}
        }

        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            self.extract_py_node(child, ctx, out);
        }
    }

    fn extract_py_calls<'a>(
        &self,
        node: Node<'a>,
        ctx: &PyParseContext<'a>,
        out: &mut ParsedFileEntities,
    ) {
        if node.kind() == "call" {
            if let Some(func_node) = node.child_by_field_name("function") {
                let callee_raw = node_text(func_node, ctx.source);
                let (line, col) = point_to_1indexed(node.start_position());
                let caller_name = ctx.current_parent.clone().unwrap_or_else(|| "global".to_string());
                let callee_name = extract_callee_leaf_name(&callee_raw);

                out.calls.push(CallEdge {
                    caller_name,
                    callee_name: callee_name.clone(),
                    line,
                    col,
                });

                out.references.push(RefEdge {
                    symbol_name: callee_name,
                    line,
                    col,
                    ref_kind: "call".to_string(),
                });
            }
        }

        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            self.extract_py_calls(child, ctx, out);
        }
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

struct RustParseContext<'a> {
    source: &'a [u8],
    current_parent: Option<String>,
    current_impl_trait: Option<String>,
    current_impl_target: Option<String>,
}

struct TsParseContext<'a> {
    source: &'a [u8],
    current_parent: Option<String>,
}

struct PyParseContext<'a> {
    source: &'a [u8],
    current_parent: Option<String>,
}

fn node_text<'a>(node: Node<'a>, source: &'a [u8]) -> String {
    node.utf8_text(source).unwrap_or("").trim().to_string()
}

fn point_to_1indexed(point: tree_sitter::Point) -> (usize, usize) {
    (point.row + 1, point.column + 1)
}

fn build_qualified_name(parent: Option<&str>, name: &str) -> String {
    match parent {
        Some(p) => format!("{}::{}", p, name),
        None => name.to_string(),
    }
}

fn extract_callee_leaf_name(raw: &str) -> String {
    // Strip self., this., Type::, obj.
    let s = raw.trim();
    if let Some(pos) = s.rfind("::") {
        s[pos + 2..].to_string()
    } else if let Some(pos) = s.rfind('.') {
        s[pos + 1..].to_string()
    } else {
        s.to_string()
    }
}

fn extract_rust_visibility(node: Node, source: &[u8]) -> String {
    if let Some(vis_node) = node.child_by_field_name("visibility") {
        node_text(vis_node, source)
    } else {
        "private".to_string()
    }
}

fn extract_preceding_docstrings(node: Node, source: &[u8]) -> Option<String> {
    let mut docs = Vec::new();
    let mut prev = node.prev_sibling();
    while let Some(p) = prev {
        if p.kind() == "line_comment" || p.kind() == "block_comment" || p.kind() == "comment" {
            let t = node_text(p, source);
            if t.starts_with("///") || t.starts_with("/**") || t.starts_with("//!") {
                docs.push(t);
            }
            prev = p.prev_sibling();
        } else {
            break;
        }
    }
    if docs.is_empty() {
        None
    } else {
        docs.reverse();
        Some(docs.join("\n"))
    }
}

fn extract_python_docstring(node: Node, source: &[u8]) -> Option<String> {
    if let Some(body) = node.child_by_field_name("body") {
        if let Some(first_stmt) = body.child(0) {
            if first_stmt.kind() == "expression_statement" {
                if let Some(str_node) = first_stmt.child(0) {
                    if str_node.kind() == "string" {
                        let raw = node_text(str_node, source);
                        let clean = raw.trim_matches(|c| c == '"' || c == '\'').trim();
                        return Some(clean.to_string());
                    }
                }
            }
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rust_extraction() {
        let mut extractor = AstExtractor::new().unwrap();
        let code = r#"
        /// Represents an arbiter.
        pub struct Arbiter {
            pub id: String,
        }

        impl Arbiter {
            /// Runs arbitration.
            pub fn run(&self) {
                self.helper();
            }

            fn helper(&self) {}
        }
        "#;
        let entities = extractor.parse(code, LanguageKind::Rust, false).unwrap();
        assert!(entities.symbols.iter().any(|s| s.name == "Arbiter" && s.kind == "struct"));
        assert!(entities.symbols.iter().any(|s| s.name == "run" && s.kind == "method"));
        assert!(entities.symbols.iter().any(|s| s.name == "helper" && s.kind == "method"));
        assert!(entities.calls.iter().any(|c| c.callee_name == "helper"));
    }

    #[test]
    fn test_typescript_extraction() {
        let mut extractor = AstExtractor::new().unwrap();
        let code = r#"
        export interface Worker {
            work(): void;
        }

        export class Service implements Worker {
            work(): void {
                this.executeTask();
            }
            private executeTask(): void {}
        }
        "#;
        let entities = extractor.parse(code, LanguageKind::TypeScript, false).unwrap();
        assert!(entities.symbols.iter().any(|s| s.name == "Worker" && s.kind == "interface"));
        assert!(entities.symbols.iter().any(|s| s.name == "Service" && s.kind == "class"));
        assert!(entities.implementations.iter().any(|i| i.symbol_name == "Service" && i.interface_name == "Worker"));
        assert!(entities.calls.iter().any(|c| c.callee_name == "executeTask"));
    }

    #[test]
    fn test_python_extraction() {
        let mut extractor = AstExtractor::new().unwrap();
        let code = r#"
class BaseHandler:
    """Base class for handlers."""
    def handle(self):
        self.process()

    def process(self):
        pass
        "#;
        let entities = extractor.parse(code, LanguageKind::Python, false).unwrap();
        assert!(entities.symbols.iter().any(|s| s.name == "BaseHandler" && s.kind == "class"));
        assert!(entities.symbols.iter().any(|s| s.name == "handle" && s.kind == "method"));
        assert!(entities.calls.iter().any(|c| c.callee_name == "process"));
    }
}
