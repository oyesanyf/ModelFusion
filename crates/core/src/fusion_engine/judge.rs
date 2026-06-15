use crate::fusion_engine::schema::{ModelAnswer, JudgeAnalysis, ModelConfig};
use crate::fusion_engine::models::call_model;

pub fn build_judge_prompt(user_prompt: &str, answers: &[ModelAnswer]) -> String {
    let mut prompt = String::new();

    prompt.push_str("You are an expert judge model evaluating and comparing multiple assistant responses.\n\n");

    prompt.push_str("### USER REQUEST:\n");
    prompt.push_str(user_prompt);
    prompt.push_str("\n\n");

    prompt.push_str("### ASSISTANT RESPONSES TO EVALUATE:\n");
    for answer in answers {
        prompt.push_str(&format!(
            "\n--- MODEL: {} ---\n{}\n",
            answer.model_name, answer.answer
        ));
    }
    prompt.push_str("\n");

    prompt.push_str("### INSTRUCTIONS FOR THE JUDGE:\n");
    prompt.push_str("Compare the assistant responses above. Identify consensus, disagreements, unique insights, blind spots, risk flags, and recommend a final synthesized position.\n");
    prompt.push_str("CRITICAL QUALITY RULE: Do not automatically select the majority consensus. If a minority response contains significantly more specific evidence, source code alignment, or detailed technical reasoning than the majority consensus, recommend the technically superior minority response.\n");
    prompt.push_str("You MUST return a valid JSON object ONLY. Do not write a markdown introduction or conversational text.\n\n");
    prompt.push_str("### REQUIRED JSON FORMAT:\n");
    prompt.push_str("{\n");
    prompt.push_str("  \"consensus\": [\"list of points of agreement\"],\n");
    prompt.push_str("  \"disagreements\": [\"list of points of disagreement\"],\n");
    prompt.push_str("  \"unique_insights\": [\"list of unique insights from specific models\"],\n");
    prompt.push_str("  \"blind_spots\": [\"list of potential omissions or errors across models\"],\n");
    prompt.push_str("  \"risk_flags\": [\"any risk factors or safety flags observed\"],\n");
    prompt.push_str("  \"recommended_final_position\": \"detailed summary of the recommended final position to answer the user request\"\n");
    prompt.push_str("}\n\n");
    prompt.push_str("JSON output:");

    prompt
}

pub async fn judge_panel(
    prompt: &str,
    answers: &[ModelAnswer],
    judge_model: &ModelConfig,
) -> anyhow::Result<JudgeAnalysis> {
    let judge_prompt = build_judge_prompt(prompt, answers);
    
    let response_text = match call_model(judge_model, &judge_prompt).await {
        Ok(text) => text,
        Err(e) => {
            log::warn!("Judge model call failed: {}. Falling back to local offline mock judge.", e);
            let mut summary = String::new();
            summary.push_str("[Offline Mock Judge Summary]\n");
            for ans in answers {
                summary.push_str(&format!("- {}: {}\n", ans.model_name, ans.answer));
            }
            return Ok(JudgeAnalysis {
                consensus: vec!["Offline mode: no active API keys found".to_string()],
                disagreements: vec![],
                unique_insights: vec![],
                blind_spots: vec![],
                risk_flags: vec![],
                recommended_final_position: summary,
            });
        }
    };
    
    // Strip <think>...</think> block if present
    let mut clean_json = if let Some(end_idx) = response_text.find("</think>") {
        response_text[end_idx + 8..].to_string()
    } else {
        response_text.clone()
    };

    // Trim and strip markdown code blocks
    clean_json = clean_json.trim().to_string();
    if clean_json.starts_with("```") {
        clean_json = clean_json
            .trim_start_matches("```json")
            .trim_start_matches("```")
            .trim_end_matches("```")
            .trim()
            .to_string();
    }

    // Extract content between first '{' and last '}' to handle any surrounding text
    if let Some(start) = clean_json.find('{') {
        if let Some(end) = clean_json.rfind('}') {
            if start < end {
                clean_json = clean_json[start..=end].to_string();
            }
        }
    }

    let analysis: JudgeAnalysis = serde_json::from_str(&clean_json)
        .unwrap_or_else(|e| {
            log::warn!("Failed to parse judge JSON: {}. Cleaned JSON was: {}. Using fallback model summary.", e, clean_json);
            JudgeAnalysis {
                consensus: vec!["Fallback: Parse error".to_string()],
                disagreements: vec![],
                unique_insights: vec![],
                blind_spots: vec![],
                risk_flags: vec![],
                recommended_final_position: response_text.clone(),
            }
        });

    Ok(analysis)
}

pub async fn write_final_answer(
    prompt: &str,
    judge_json: &JudgeAnalysis,
    writer_model: &ModelConfig,
) -> anyhow::Result<String> {
    let mut writer_prompt = String::new();
    writer_prompt.push_str("Use the judge analysis below to answer the user.\n");
    writer_prompt.push_str("Do not blindly prioritize consensus. If a minority response offers more specific evidence, code snippets, or deeper technical accuracy than the majority agreement, prioritize the technically superior minority view.\n");
    writer_prompt.push_str("Prioritize accuracy, technical depth, and specific evidence over simple consensus.\n");
    writer_prompt.push_str("Mention uncertainty where models disagreed.\n");
    writer_prompt.push_str("Do not pretend disagreement is resolved.\n\n");
    
    writer_prompt.push_str("USER REQUEST:\n");
    writer_prompt.push_str(prompt);
    writer_prompt.push_str("\n\nJUDGE ANALYSIS:\n");
    writer_prompt.push_str(&format!("Consensus: {:?}\n", judge_json.consensus));
    writer_prompt.push_str(&format!("Disagreements: {:?}\n", judge_json.disagreements));
    writer_prompt.push_str(&format!("Unique Insights: {:?}\n", judge_json.unique_insights));
    writer_prompt.push_str(&format!("Blind Spots: {:?}\n", judge_json.blind_spots));
    writer_prompt.push_str(&format!("Risk Flags: {:?}\n", judge_json.risk_flags));
    writer_prompt.push_str(&format!("Recommended Position: {}\n", judge_json.recommended_final_position));

    match call_model(writer_model, &writer_prompt).await {
        Ok(ans) => Ok(ans),
        Err(e) => {
            log::warn!("Writer model call failed: {}. Returning raw judge recommended position.", e);
            Ok(format!(
                "[Offline Synth Writer Fallback]\n\n{}\n\n(Note: Writer model failed with error: {})",
                judge_json.recommended_final_position, e
            ))
        }
    }
}
