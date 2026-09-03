use serde_json::Value;
use std::collections::{HashMap, HashSet};

/// Errors arising during JSON Schema validation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SchemaValidationError {
    TypeMismatch {
        expected: String,
        found: String,
        path: String,
    },
    MissingRequiredField {
        field: String,
        path: String,
    },
    AdditionalPropertyNotAllowed {
        property: String,
        path: String,
    },
    NotInEnum {
        path: String,
        allowed: Vec<String>,
        found: String,
    },
    NumberOutOfRange {
        path: String,
        message: String,
    },
    StringLengthOutOfRange {
        path: String,
        message: String,
    },
    InvalidSchema(String),
}

impl std::fmt::Display for SchemaValidationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SchemaValidationError::TypeMismatch { expected, found, path } => {
                write!(f, "Type mismatch at '{}': expected {}, found {}", path, expected, found)
            }
            SchemaValidationError::MissingRequiredField { field, path } => {
                write!(f, "Missing required field '{}' at '{}'", field, path)
            }
            SchemaValidationError::AdditionalPropertyNotAllowed { property, path } => {
                write!(f, "Additional property '{}' is not allowed at '{}'", property, path)
            }
            SchemaValidationError::NotInEnum { path, allowed, found } => {
                write!(f, "Value '{}' at '{}' is not in allowed enum [{}]", found, path, allowed.join(", "))
            }
            SchemaValidationError::NumberOutOfRange { path, message } => {
                write!(f, "Number out of range at '{}': {}", path, message)
            }
            SchemaValidationError::StringLengthOutOfRange { path, message } => {
                write!(f, "String length out of range at '{}': {}", path, message)
            }
            SchemaValidationError::InvalidSchema(msg) => {
                write!(f, "Invalid JSON Schema: {}", msg)
            }
        }
    }
}

impl std::error::Error for SchemaValidationError {}

/// Compiled representation of a JSON Schema for microsecond validation.
#[derive(Debug, Clone)]
pub struct CompiledSchema {
    expected_type: Option<SchemaType>,
    required: HashSet<String>,
    properties: HashMap<String, CompiledSchema>,
    items: Option<Box<CompiledSchema>>,
    enum_values: Option<Vec<Value>>,
    minimum: Option<f64>,
    maximum: Option<f64>,
    min_length: Option<usize>,
    max_length: Option<usize>,
    additional_properties_allowed: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SchemaType {
    Object,
    Array,
    String,
    Number,
    Integer,
    Boolean,
    Null,
}

impl SchemaType {
    fn matches(&self, val: &Value) -> bool {
        match self {
            SchemaType::Object => val.is_object(),
            SchemaType::Array => val.is_array(),
            SchemaType::String => val.is_string(),
            SchemaType::Number => val.is_number(),
            SchemaType::Integer => val.is_i64() || val.is_u64(),
            SchemaType::Boolean => val.is_boolean(),
            SchemaType::Null => val.is_null(),
        }
    }

    fn name(&self) -> &'static str {
        match self {
            SchemaType::Object => "object",
            SchemaType::Array => "array",
            SchemaType::String => "string",
            SchemaType::Number => "number",
            SchemaType::Integer => "integer",
            SchemaType::Boolean => "boolean",
            SchemaType::Null => "null",
        }
    }
}

fn value_type_name(val: &Value) -> &'static str {
    match val {
        Value::Null => "null",
        Value::Bool(_) => "boolean",
        Value::Number(n) if n.is_i64() || n.is_u64() => "integer",
        Value::Number(_) => "number",
        Value::String(_) => "string",
        Value::Array(_) => "array",
        Value::Object(_) => "object",
    }
}

impl CompiledSchema {
    /// Compiles a JSON Schema from a `serde_json::Value`.
    pub fn compile(schema: &Value) -> Result<Self, SchemaValidationError> {
        if !schema.is_object() {
            // Allow empty or true schemas
            if schema.as_bool() == Some(true) || schema.is_null() {
                return Ok(CompiledSchema {
                    expected_type: None,
                    required: HashSet::new(),
                    properties: HashMap::new(),
                    items: None,
                    enum_values: None,
                    minimum: None,
                    maximum: None,
                    min_length: None,
                    max_length: None,
                    additional_properties_allowed: true,
                });
            }
            return Err(SchemaValidationError::InvalidSchema(
                "Schema root must be an object".to_string(),
            ));
        }

        let obj = schema.as_object().unwrap();

        // Parse type
        let expected_type = if let Some(type_val) = obj.get("type") {
            if let Some(type_str) = type_val.as_str() {
                match type_str {
                    "object" => Some(SchemaType::Object),
                    "array" => Some(SchemaType::Array),
                    "string" => Some(SchemaType::String),
                    "number" => Some(SchemaType::Number),
                    "integer" => Some(SchemaType::Integer),
                    "boolean" => Some(SchemaType::Boolean),
                    "null" => Some(SchemaType::Null),
                    other => {
                        return Err(SchemaValidationError::InvalidSchema(format!(
                            "Unsupported schema type: {}",
                            other
                        )))
                    }
                }
            } else {
                None
            }
        } else {
            None
        };

        // Parse required fields
        let mut required = HashSet::new();
        if let Some(req_val) = obj.get("required") {
            if let Some(req_arr) = req_val.as_array() {
                for item in req_arr {
                    if let Some(s) = item.as_str() {
                        required.insert(s.to_string());
                    }
                }
            }
        }

        // Parse properties
        let mut properties = HashMap::new();
        if let Some(props_val) = obj.get("properties") {
            if let Some(props_obj) = props_val.as_object() {
                for (k, v) in props_obj {
                    let compiled_prop = CompiledSchema::compile(v)?;
                    properties.insert(k.clone(), compiled_prop);
                }
            }
        }

        // Parse items (for arrays)
        let items = if let Some(items_val) = obj.get("items") {
            Some(Box::new(CompiledSchema::compile(items_val)?))
        } else {
            None
        };

        // Parse enum
        let enum_values = if let Some(enum_val) = obj.get("enum") {
            enum_val.as_array().cloned()
        } else {
            None
        };

        // Parse numeric bounds
        let minimum = obj.get("minimum").and_then(|v| v.as_f64());
        let maximum = obj.get("maximum").and_then(|v| v.as_f64());

        // Parse string lengths
        let min_length = obj.get("minLength").and_then(|v| v.as_u64()).map(|v| v as usize);
        let max_length = obj.get("maxLength").and_then(|v| v.as_u64()).map(|v| v as usize);

        // Parse additionalProperties
        let additional_properties_allowed = obj
            .get("additionalProperties")
            .and_then(|v| v.as_bool())
            .unwrap_or(true);

        Ok(CompiledSchema {
            expected_type,
            required,
            properties,
            items,
            enum_values,
            minimum,
            maximum,
            min_length,
            max_length,
            additional_properties_allowed,
        })
    }

    /// Validates an input JSON `Value` against this compiled schema.
    pub fn validate(&self, val: &Value) -> Result<(), SchemaValidationError> {
        self.validate_internal(val, "$")
    }

    fn validate_internal(&self, val: &Value, path: &str) -> Result<(), SchemaValidationError> {
        // 1. Type validation
        if let Some(ref exp_type) = self.expected_type {
            if !exp_type.matches(val) {
                // If expected is Number, allow Integer as well
                if *exp_type == SchemaType::Number && val.is_number() {
                    // Valid
                } else {
                    return Err(SchemaValidationError::TypeMismatch {
                        expected: exp_type.name().to_string(),
                        found: value_type_name(val).to_string(),
                        path: path.to_string(),
                    });
                }
            }
        }

        // 2. Enum validation
        if let Some(ref allowed) = self.enum_values {
            if !allowed.contains(val) {
                return Err(SchemaValidationError::NotInEnum {
                    path: path.to_string(),
                    allowed: allowed.iter().map(|v| v.to_string()).collect(),
                    found: val.to_string(),
                });
            }
        }

        // 3. String bounds
        if let Some(s) = val.as_str() {
            let len = s.chars().count();
            if let Some(min) = self.min_length {
                if len < min {
                    return Err(SchemaValidationError::StringLengthOutOfRange {
                        path: path.to_string(),
                        message: format!("Length {} is less than minLength {}", len, min),
                    });
                }
            }
            if let Some(max) = self.max_length {
                if len > max {
                    return Err(SchemaValidationError::StringLengthOutOfRange {
                        path: path.to_string(),
                        message: format!("Length {} exceeds maxLength {}", len, max),
                    });
                }
            }
        }

        // 4. Number bounds
        if let Some(n) = val.as_f64() {
            if let Some(min) = self.minimum {
                if n < min {
                    return Err(SchemaValidationError::NumberOutOfRange {
                        path: path.to_string(),
                        message: format!("Value {} is less than minimum {}", n, min),
                    });
                }
            }
            if let Some(max) = self.maximum {
                if n > max {
                    return Err(SchemaValidationError::NumberOutOfRange {
                        path: path.to_string(),
                        message: format!("Value {} exceeds maximum {}", n, max),
                    });
                }
            }
        }

        // 5. Object properties & required fields
        if let Some(obj) = val.as_object() {
            for req in &self.required {
                if !obj.contains_key(req) {
                    return Err(SchemaValidationError::MissingRequiredField {
                        field: req.clone(),
                        path: path.to_string(),
                    });
                }
            }

            for (k, v) in obj {
                let child_path = if path == "$" {
                    format!("$.{}", k)
                } else {
                    format!("{}.{}", path, k)
                };

                if let Some(prop_schema) = self.properties.get(k) {
                    prop_schema.validate_internal(v, &child_path)?;
                } else if !self.additional_properties_allowed {
                    return Err(SchemaValidationError::AdditionalPropertyNotAllowed {
                        property: k.clone(),
                        path: path.to_string(),
                    });
                }
            }
        }

        // 6. Array items
        if let Some(arr) = val.as_array() {
            if let Some(ref item_schema) = self.items {
                for (idx, item) in arr.iter().enumerate() {
                    let child_path = format!("{}[{}]", path, idx);
                    item_schema.validate_internal(item, &child_path)?;
                }
            }
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_schema_object_validation() {
        let schema_val = json!({
            "type": "object",
            "properties": {
                "name": { "type": "string", "minLength": 2 },
                "age": { "type": "integer", "minimum": 0 },
                "tags": {
                    "type": "array",
                    "items": { "type": "string" }
                }
            },
            "required": ["name"]
        });

        let schema = CompiledSchema::compile(&schema_val).unwrap();

        // Valid
        let valid_val = json!({
            "name": "Alice",
            "age": 30,
            "tags": ["rust", "mcp"]
        });
        assert!(schema.validate(&valid_val).is_ok());

        // Missing required
        let missing_req = json!({ "age": 25 });
        assert!(schema.validate(&missing_req).is_err());

        // Type mismatch
        let wrong_type = json!({ "name": 123 });
        assert!(schema.validate(&wrong_type).is_err());

        // Sub-array item mismatch
        let wrong_array_item = json!({
            "name": "Bob",
            "tags": [1, 2, 3]
        });
        assert!(schema.validate(&wrong_array_item).is_err());
    }
}
