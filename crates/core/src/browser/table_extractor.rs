//! Semantic table and CSS grid extractor for web datasets and AutoML pipelines.
//!
//! Extracts HTML `<table>` elements and CSS grid/flex table structures, converting them
//! into structured CSV datasets and JSON payloads ready for ACDSO (Auto-Causal Decision
//! & Strategic Optimization) and data science analysis.

use regex::Regex;
use serde::{Deserialize, Serialize};

/// A structured tabular dataset extracted from a web page.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ExtractedTable {
    /// 1-based index of the table on the page.
    pub id: usize,
    /// Optional caption, title, or nearest preceding heading.
    pub caption: Option<String>,
    /// Column header names.
    pub headers: Vec<String>,
    /// Rows of cell values.
    pub rows: Vec<Vec<String>>,
    /// Total number of rows extracted (excluding headers).
    pub row_count: usize,
    /// Total number of columns.
    pub col_count: usize,
}

impl ExtractedTable {
    /// Converts the tabular data into RFC-4180 compliant CSV format.
    pub fn to_csv(&self) -> String {
        let mut csv = String::new();

        // Write header row
        let escaped_headers: Vec<String> = self.headers.iter().map(|h| Self::escape_csv_field(h)).collect();
        csv.push_str(&escaped_headers.join(","));
        csv.push('\n');

        // Write data rows
        for row in &self.rows {
            let escaped_cells: Vec<String> = row.iter().map(|cell| Self::escape_csv_field(cell)).collect();
            csv.push_str(&escaped_cells.join(","));
            csv.push('\n');
        }

        csv
    }

    /// Converts the table into a JSON array of objects keyed by header names.
    pub fn to_json(&self) -> serde_json::Value {
        if self.headers.is_empty() {
            // Return array of rows
            return serde_json::json!(self.rows);
        }

        let mut items = Vec::with_capacity(self.rows.len());
        for row in &self.rows {
            let mut obj = serde_json::Map::new();
            for (i, header) in self.headers.iter().enumerate() {
                let val = row.get(i).map(|s| s.as_str()).unwrap_or("");
                // Try parsing numeric or boolean types
                if let Ok(int_val) = val.parse::<i64>() {
                    obj.insert(header.clone(), serde_json::json!(int_val));
                } else if let Ok(float_val) = val.parse::<f64>() {
                    obj.insert(header.clone(), serde_json::json!(float_val));
                } else if val.eq_ignore_ascii_case("true") {
                    obj.insert(header.clone(), serde_json::json!(true));
                } else if val.eq_ignore_ascii_case("false") {
                    obj.insert(header.clone(), serde_json::json!(false));
                } else {
                    obj.insert(header.clone(), serde_json::json!(val));
                }
            }
            items.push(serde_json::Value::Object(obj));
        }

        serde_json::Value::Array(items)
    }

    /// Formats the JSON dataset as a pretty-printed string.
    pub fn to_json_string(&self) -> String {
        serde_json::to_string_pretty(&self.to_json()).unwrap_or_else(|_| "[]".to_string())
    }

    /// Returns a human-readable summary of the table shape and columns.
    pub fn summary(&self) -> String {
        let title = self.caption.as_deref().unwrap_or("Untitled Table");
        format!(
            "Table #{} ({}): {} rows x {} columns. Columns: [{}]",
            self.id,
            title,
            self.row_count,
            self.col_count,
            self.headers.join(", ")
        )
    }

    /// Helper escaping CSV values containing commas, quotes, or newlines.
    fn escape_csv_field(field: &str) -> String {
        let trimmed = field.trim();
        if trimmed.contains(',') || trimmed.contains('"') || trimmed.contains('\n') || trimmed.contains('\r') {
            format!("\"{}\"", trimmed.replace('"', "\"\""))
        } else {
            trimmed.to_string()
        }
    }
}

/// Table and CSS grid extraction engine.
pub struct TableExtractor;

impl TableExtractor {
    /// Extracts all HTML tables and CSS grid tables from raw HTML.
    pub fn extract_from_html(html: &str) -> Vec<ExtractedTable> {
        let mut tables = Vec::new();
        let mut table_id = 1;

        // 1. Extract standard HTML <table> tags
        let re_table = Regex::new(r"(?si)<table\b[^>]*>(.*?)</table>").unwrap();
        for cap in re_table.captures_iter(html) {
            let table_html = cap.get(1).map(|m| m.as_str()).unwrap_or("");
            if let Some(table) = Self::parse_single_html_table(table_id, table_html) {
                if table.row_count > 0 || !table.headers.is_empty() {
                    tables.push(table);
                    table_id += 1;
                }
            }
        }

        // 2. If no standard tables found, extract role="table" or role="grid" or role="row" elements
        if tables.is_empty() && (html.contains("role=\"grid\"") || html.contains("role=\"table\"") || html.contains("role=\"row\"") || html.contains("role='grid'") || html.contains("role='table'") || html.contains("role='row'")) {
            if let Some(table) = Self::parse_role_grid_table(table_id, html) {
                if table.row_count > 0 {
                    tables.push(table);
                    table_id += 1;
                }
            }
        }

        // 3. If no HTML tables found, parse as raw CSV/TSV dataset
        if tables.is_empty() {
            let is_html_doc = html.contains("<html") || html.contains("<!DOCTYPE") || html.contains("<body") || html.contains("<div");
            if !is_html_doc {
                if let Some(table) = Self::parse_csv(table_id, html) {
                    if table.row_count > 0 && table.col_count > 1 {
                        tables.push(table);
                    }
                }
            }
        }

        tables
    }

    /// Parses a single HTML `<table>` inner body.
    fn parse_single_html_table(id: usize, table_body: &str) -> Option<ExtractedTable> {
        // Extract optional <caption>
        let re_caption = Regex::new(r"(?si)<caption\b[^>]*>(.*?)</caption>").unwrap();
        let caption = re_caption
            .captures(table_body)
            .and_then(|c| c.get(1))
            .map(|m| Self::clean_cell_text(m.as_str()));

        // Extract rows <tr>...</tr>
        let re_tr = Regex::new(r"(?si)<tr\b[^>]*>(.*?)</tr>").unwrap();
        let mut raw_rows: Vec<Vec<(bool, String)>> = Vec::new();

        for tr_cap in re_tr.captures_iter(table_body) {
            let tr_content = tr_cap.get(1).map(|m| m.as_str()).unwrap_or("");
            let cells = Self::extract_cells_from_row(tr_content);
            if !cells.is_empty() {
                raw_rows.push(cells);
            }
        }

        if raw_rows.is_empty() {
            return None;
        }

        // Detect headers
        let mut headers = Vec::new();
        let mut data_rows = Vec::new();

        let first_row = &raw_rows[0];
        let all_th = first_row.iter().all(|(is_th, _)| *is_th);
        let any_th = first_row.iter().any(|(is_th, _)| *is_th);

        let has_explicit_header_row = all_th || any_th;

        if has_explicit_header_row {
            headers = first_row.iter().map(|(_, text)| text.clone()).collect();
            for r in &raw_rows[1..] {
                data_rows.push(r.iter().map(|(_, text)| text.clone()).collect::<Vec<_>>());
            }
        } else {
            // Check if <thead> was explicitly defined
            let re_thead = Regex::new(r"(?si)<thead\b[^>]*>(.*?)</thead>").unwrap();
            if let Some(thead_match) = re_thead.captures(table_body) {
                let thead_content = thead_match.get(1).map(|m| m.as_str()).unwrap_or("");
                let thead_cells = Self::extract_cells_from_row(thead_content);
                if !thead_cells.is_empty() {
                    headers = thead_cells.into_iter().map(|(_, text)| text).collect();
                }
            }

            if headers.is_empty() {
                // Generate default column names Col_1, Col_2, ...
                let max_cols = raw_rows.iter().map(|r| r.len()).max().unwrap_or(0);
                for i in 1..=max_cols {
                    headers.push(format!("Col_{}", i));
                }
                for r in &raw_rows {
                    data_rows.push(r.iter().map(|(_, text)| text.clone()).collect());
                }
            } else {
                for r in &raw_rows {
                    data_rows.push(r.iter().map(|(_, text)| text.clone()).collect());
                }
            }
        }

        // Determine column count and normalize row widths
        let col_count = headers.len().max(data_rows.iter().map(|r| r.len()).max().unwrap_or(0));

        // Pad headers if needed
        while headers.len() < col_count {
            headers.push(format!("Col_{}", headers.len() + 1));
        }

        // Normalize each data row to col_count
        for row in &mut data_rows {
            while row.len() < col_count {
                row.push(String::new());
            }
            if row.len() > col_count {
                row.truncate(col_count);
            }
        }

        let row_count = data_rows.len();

        Some(ExtractedTable {
            id,
            caption,
            headers,
            rows: data_rows,
            row_count,
            col_count,
        })
    }

    /// Extracts `<th>` and `<td>` cells from a row string.
    fn extract_cells_from_row(row_str: &str) -> Vec<(bool, String)> {
        let mut cells = Vec::new();
        let re_cell = Regex::new(r"(?si)<th\b[^>]*>(.*?)</th>|<td\b[^>]*>(.*?)</td>").unwrap();

        for cap in re_cell.captures_iter(row_str) {
            let (is_th, content) = if let Some(m) = cap.get(1) {
                (true, m.as_str())
            } else if let Some(m) = cap.get(2) {
                (false, m.as_str())
            } else {
                continue;
            };
            let clean = Self::clean_cell_text(content);
            cells.push((is_th, clean));
        }

        cells
    }

    /// Parses ARIA/CSS role="grid" or role="table" structures.
    fn parse_role_grid_table(id: usize, grid_body: &str) -> Option<ExtractedTable> {
        let re_row_start = Regex::new(r#"(?si)<(?:div|tr|section)\b[^>]*role=["']row["'][^>]*>"#).unwrap();
        let re_cell = Regex::new(r#"(?si)<(?:div|td|th|span)\b[^>]*role=["'](columnheader|cell|gridcell)["'][^>]*>(.*?)</(?:div|td|th|span)>"#).unwrap();

        let mut raw_rows = Vec::new();
        let chunks: Vec<&str> = re_row_start.split(grid_body).collect();

        // Skip the pre-first-row chunk
        for chunk in chunks.into_iter().skip(1) {
            let mut cells = Vec::new();
            for cell_cap in re_cell.captures_iter(chunk) {
                let is_th = cell_cap.get(1).map(|m| m.as_str() == "columnheader").unwrap_or(false);
                let content = cell_cap.get(2).map(|m| m.as_str()).unwrap_or("");
                cells.push((is_th, Self::clean_cell_text(content)));
            }
            if !cells.is_empty() {
                raw_rows.push(cells);
            }
        }

        if raw_rows.is_empty() {
            return None;
        }

        let first_row = &raw_rows[0];
        let has_headers = first_row.iter().any(|(is_th, _)| *is_th);

        let (headers, data_rows): (Vec<String>, Vec<Vec<String>>) = if has_headers {
            let h: Vec<String> = first_row.iter().map(|(_, t)| t.clone()).collect();
            let d: Vec<Vec<String>> = raw_rows[1..].iter().map(|r| r.iter().map(|(_, t)| t.clone()).collect()).collect();
            (h, d)
        } else {
            let col_count = raw_rows[0].len();
            let h: Vec<String> = (1..=col_count).map(|i| format!("Col_{}", i)).collect();
            let d: Vec<Vec<String>> = raw_rows.iter().map(|r| r.iter().map(|(_, t)| t.clone()).collect()).collect();
            (h, d)
        };

        let col_count = headers.len();
        let row_count = data_rows.len();

        Some(ExtractedTable {
            id,
            caption: Some("CSS Grid Table".to_string()),
            headers,
            rows: data_rows,
            row_count,
            col_count,
        })
    }

    /// Parses raw CSV or TSV tabular data into an ExtractedTable.
    pub fn parse_csv(id: usize, raw: &str) -> Option<ExtractedTable> {
        let trimmed = raw.trim();
        if trimmed.is_empty() {
            return None;
        }

        // Determine delimiter (comma or tab)
        let first_line = trimmed.lines().next()?;
        let delimiter = if first_line.contains('\t') && !first_line.contains(',') {
            '\t'
        } else {
            ','
        };

        let mut lines = trimmed.lines();
        let header_line = lines.next()?;
        let headers: Vec<String> = Self::split_csv_line(header_line, delimiter);
        if headers.is_empty() {
            return None;
        }

        let col_count = headers.len();
        let mut data_rows = Vec::new();

        for line in lines {
            let line_trimmed = line.trim();
            if line_trimmed.is_empty() {
                continue;
            }
            let mut row = Self::split_csv_line(line_trimmed, delimiter);
            while row.len() < col_count {
                row.push(String::new());
            }
            if row.len() > col_count {
                row.truncate(col_count);
            }
            data_rows.push(row);
        }

        if data_rows.is_empty() {
            return None;
        }

        let row_count = data_rows.len();

        Some(ExtractedTable {
            id,
            caption: Some("Delimited Dataset".to_string()),
            headers,
            rows: data_rows,
            row_count,
            col_count,
        })
    }

    /// Splits a single CSV/TSV line respecting quotes.
    fn split_csv_line(line: &str, delimiter: char) -> Vec<String> {
        let mut fields = Vec::new();
        let mut current = String::new();
        let mut in_quotes = false;
        let mut chars = line.chars().peekable();

        while let Some(c) = chars.next() {
            match c {
                '"' => {
                    if in_quotes && chars.peek() == Some(&'"') {
                        // Escaped quote
                        chars.next();
                        current.push('"');
                    } else {
                        in_quotes = !in_quotes;
                    }
                }
                d if d == delimiter && !in_quotes => {
                    fields.push(current.trim().to_string());
                    current.clear();
                }
                _ => {
                    current.push(c);
                }
            }
        }
        fields.push(current.trim().to_string());
        fields
    }

    /// Strips nested tags and unescapes standard HTML entities.
    fn clean_cell_text(raw: &str) -> String {
        let re_tags = Regex::new(r"<[^>]*>").unwrap();
        let stripped = re_tags.replace_all(raw, " ").to_string();

        let s1 = stripped
            .replace("&nbsp;", " ")
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", "\"")
            .replace("&#39;", "'")
            .replace("&apos;", "'");

        let re_spaces = Regex::new(r"\s+").unwrap();
        re_spaces.replace_all(&s1, " ").trim().to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_standard_table() {
        let html = r#"
            <table>
                <caption>Model Performance Leaderboard</caption>
                <thead>
                    <tr>
                        <th>Model Name</th>
                        <th>Parameters</th>
                        <th>ARC Score</th>
                        <th>Downloads</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Qwen/Qwen2.5-32B-Instruct</td>
                        <td>32.5B</td>
                        <td>88.4</td>
                        <td>1,250,000</td>
                    </tr>
                    <tr>
                        <td>meta-llama/Llama-3.1-8B-Instruct</td>
                        <td>8.0B</td>
                        <td>79.6</td>
                        <td>4,800,000</td>
                    </tr>
                </tbody>
            </table>
        "#;

        let tables = TableExtractor::extract_from_html(html);
        assert_eq!(tables.len(), 1);

        let table = &tables[0];
        assert_eq!(table.caption.as_deref(), Some("Model Performance Leaderboard"));
        assert_eq!(table.headers, vec!["Model Name", "Parameters", "ARC Score", "Downloads"]);
        assert_eq!(table.row_count, 2);
        assert_eq!(table.col_count, 4);

        let csv = table.to_csv();
        assert!(csv.contains("Model Name,Parameters,ARC Score,Downloads"));
        assert!(csv.contains("\"1,250,000\"")); // escaped comma in downloads

        let json = table.to_json();
        assert_eq!(json.as_array().unwrap().len(), 2);
        let first_row = &json[0];
        assert_eq!(first_row["Model Name"], "Qwen/Qwen2.5-32B-Instruct");
        assert_eq!(first_row["ARC Score"], 88.4);
    }

    #[test]
    fn test_table_without_headers() {
        let html = r#"
            <table>
                <tr>
                    <td>Alpha</td>
                    <td>100</td>
                </tr>
                <tr>
                    <td>Beta</td>
                    <td>200</td>
                </tr>
            </table>
        "#;

        let tables = TableExtractor::extract_from_html(html);
        assert_eq!(tables.len(), 1);

        let table = &tables[0];
        assert_eq!(table.headers, vec!["Col_1", "Col_2"]);
        assert_eq!(table.row_count, 2);
        assert_eq!(table.rows[0], vec!["Alpha", "100"]);
    }

    #[test]
    fn test_role_grid_table() {
        let html = r#"
            <div role="grid">
                <div role="row">
                    <div role="columnheader">Metric</div>
                    <div role="columnheader">Value</div>
                </div>
                <div role="row">
                    <div role="cell">Latency</div>
                    <div role="cell">12ms</div>
                </div>
                <div role="row">
                    <div role="cell">Throughput</div>
                    <div role="cell">450 req/s</div>
                </div>
            </div>
        "#;

        let tables = TableExtractor::extract_from_html(html);
        assert_eq!(tables.len(), 1);

        let table = &tables[0];
        assert_eq!(table.headers, vec!["Metric", "Value"]);
        assert_eq!(table.row_count, 2);
        assert_eq!(table.rows[0], vec!["Latency", "12ms"]);
    }

    #[test]
    fn test_parse_raw_csv() {
        let csv = "total_bill,tip,sex,smoker,day,time,size\n16.99,1.01,Female,No,Sun,Dinner,2\n10.34,1.66,Male,No,Sun,Dinner,3";
        let tables = TableExtractor::extract_from_html(csv);
        assert_eq!(tables.len(), 1);

        let table = &tables[0];
        assert_eq!(table.headers, vec!["total_bill", "tip", "sex", "smoker", "day", "time", "size"]);
        assert_eq!(table.row_count, 2);
        assert_eq!(table.col_count, 7);
        assert_eq!(table.rows[0][0], "16.99");
    }
}
