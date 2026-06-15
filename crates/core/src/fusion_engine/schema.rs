use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Provider {
    OpenAI,
    Anthropic,
    Google,
    Local,
    HuggingFace,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelConfig {
    pub name: String,
    pub provider: Provider,
    pub endpoint: String,
    pub api_key_env: Option<String>,
}

impl ModelConfig {
    pub fn openai(model_id: &str) -> Self {
        Self {
            name: format!("OpenAI: {}", model_id),
            provider: Provider::OpenAI,
            endpoint: model_id.to_string(),
            api_key_env: Some("OPENAI_API_KEY".to_string()),
        }
    }

    pub fn anthropic(model_id: &str) -> Self {
        Self {
            name: format!("Anthropic: {}", model_id),
            provider: Provider::Anthropic,
            endpoint: model_id.to_string(),
            api_key_env: Some("ANTHROPIC_API_KEY".to_string()),
        }
    }

    pub fn google(model_id: &str) -> Self {
        Self {
            name: format!("Google: {}", model_id),
            provider: Provider::Google,
            endpoint: model_id.to_string(),
            api_key_env: Some("GOOGLE_GEMINI_API_KEY".to_string()),
        }
    }

    pub fn local(model_id: &str) -> Self {
        Self {
            name: format!("Local: {}", model_id),
            provider: Provider::Local,
            endpoint: model_id.to_string(),
            api_key_env: None,
        }
    }

    pub fn huggingface(model_id: &str) -> Self {
        Self {
            name: format!("HuggingFace: {}", model_id),
            provider: Provider::HuggingFace,
            endpoint: model_id.to_string(),
            api_key_env: Some("HF_TOKEN".to_string()),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelAnswer {
    pub model_name: String,
    pub answer: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct JudgeAnalysis {
    pub consensus: Vec<String>,
    pub disagreements: Vec<String>,
    pub unique_insights: Vec<String>,
    pub blind_spots: Vec<String>,
    pub risk_flags: Vec<String>,
    pub recommended_final_position: String,
}
