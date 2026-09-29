use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::error::Error;

#[derive(Serialize, Deserialize, Debug, Clone)]
struct Message {
    role: String,
    content: String,
}

#[derive(Serialize, Debug)]
struct ChatCompletionRequest {
    model: String,
    messages: Vec<Message>,
    temperature: f32,
    top_p: f32,
    presence_penalty: f32,
    frequency_penalty: f32,
}

#[derive(Serialize, Debug)]
struct OllamaChatOptions {
    temperature: f32,
    top_p: f32,
    presence_penalty: f32,
    frequency_penalty: f32,
}

#[derive(Serialize, Debug)]
struct OllamaChatRequest {
    model: String,
    messages: Vec<Message>,
    stream: bool,
    options: OllamaChatOptions,
}

#[derive(Deserialize, Debug)]
struct ChatChoice {
    message: MessageContent,
}

#[derive(Deserialize, Debug)]
struct MessageContent {
    content: String,
}

#[derive(Deserialize, Debug)]
struct ChatCompletionResponse {
    #[serde(default)]
    choices: Vec<ChatChoice>,
    #[serde(default)]
    message: Option<MessageContent>,
}

pub struct ProseHumanizer {
    client: Client,
    endpoint: String,
    model: String,
    system_instruction: String,
}

impl ProseHumanizer {
    pub fn new(endpoint: &str, model: &str) -> Self {
        let ep = endpoint.trim().trim_end_matches('/');
        let final_endpoint = if ep.ends_with("/chat/completions") || ep.ends_with("/api/chat") {
            ep.to_string()
        } else {
            format!("{}/v1/chat/completions", ep)
        };

        let system_instruction = "You are an expert editor who rewrites stiff, synthetic, \
            or overly robotic text into natural, fluid human prose. Write in continuous, \
            organic paragraphs using conversational syntax. Vary your sentence lengths \
            deliberately to maintain rhythm. Avoid corporate buzzwords, formulaic transition \
            words, unnecessary bullet points, and decorative adjectives. Do not add meta \
            commentary, apologies, or introductory remarks. Return only the revised text."
            .to_string();

        Self {
            client: Client::builder()
                .no_proxy()
                .timeout(std::time::Duration::from_secs(120))
                .build()
                .unwrap_or_else(|_| Client::new()),
            endpoint: final_endpoint,
            model: model.to_string(),
            system_instruction,
        }
    }

    pub async fn humanize(&self, input_text: &str) -> Result<String, Box<dyn Error + Send + Sync>> {
        let messages = vec![
            Message {
                role: "system".to_string(),
                content: self.system_instruction.clone(),
            },
            Message {
                role: "user".to_string(),
                content: format!("Rewrite the following passage into natural human prose:\n\n{}", input_text),
            },
        ];

        // Slightly elevating temperature and penalties introduces burstiness and reduces repetition
        let request_payload = ChatCompletionRequest {
            model: self.model.clone(),
            messages: messages.clone(),
            temperature: 0.85,
            top_p: 0.95,
            presence_penalty: 0.3,
            frequency_penalty: 0.4,
        };

        let send_res = self
            .client
            .post(&self.endpoint)
            .json(&request_payload)
            .send()
            .await;

        match send_res {
            Ok(resp) if resp.status().is_success() => {
                let parsed: ChatCompletionResponse = resp.json().await?;
                if let Some(choice) = parsed.choices.into_iter().next() {
                    return Ok(choice.message.content.trim().to_string());
                } else if let Some(msg) = parsed.message {
                    return Ok(msg.content.trim().to_string());
                }
            }
            Ok(resp) if resp.status().as_u16() == 404 && self.endpoint.ends_with("/v1/chat/completions") => {
                // Fallback to Ollama native /api/chat endpoint if /v1/chat/completions is not mounted
                let alt_endpoint = self.endpoint.replace("/v1/chat/completions", "/api/chat");
                let alt_payload = OllamaChatRequest {
                    model: self.model.clone(),
                    messages,
                    stream: false,
                    options: OllamaChatOptions {
                        temperature: 0.85,
                        top_p: 0.95,
                        presence_penalty: 0.3,
                        frequency_penalty: 0.4,
                    },
                };
                let alt_resp = self.client.post(&alt_endpoint).json(&alt_payload).send().await?;
                if alt_resp.status().is_success() {
                    let parsed: ChatCompletionResponse = alt_resp.json().await?;
                    if let Some(choice) = parsed.choices.into_iter().next() {
                        return Ok(choice.message.content.trim().to_string());
                    } else if let Some(msg) = parsed.message {
                        return Ok(msg.content.trim().to_string());
                    }
                }
            }
            Err(e) => {
                return Err(Box::new(e));
            }
            _ => {}
        }

        Err("Model returned an empty or invalid response.".into())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_humanizer_construction() {
        let h1 = ProseHumanizer::new("http://127.0.0.1:11434", "qwen2.5:7b");
        assert_eq!(h1.endpoint, "http://127.0.0.1:11434/v1/chat/completions");
        assert_eq!(h1.model, "qwen2.5:7b");

        let h2 = ProseHumanizer::new("http://127.0.0.1:11434/api/chat", "qwen2.5:14b");
        assert_eq!(h2.endpoint, "http://127.0.0.1:11434/api/chat");
    }

    #[test]
    fn test_deserialization_openai_format() {
        let json_data = r#"{
            "choices": [
                {
                    "message": {
                        "content": "This is natural human prose with varied rhythm."
                    }
                }
            ]
        }"#;
        let res: ChatCompletionResponse = serde_json::from_str(json_data).unwrap();
        assert_eq!(res.choices.len(), 1);
        assert_eq!(res.choices[0].message.content, "This is natural human prose with varied rhythm.");
    }

    #[test]
    fn test_deserialization_ollama_format() {
        let json_data = r#"{
            "message": {
                "content": "Flowing organic human sentences."
            }
        }"#;
        let res: ChatCompletionResponse = serde_json::from_str(json_data).unwrap();
        assert_eq!(res.message.unwrap().content, "Flowing organic human sentences.");
    }
}
