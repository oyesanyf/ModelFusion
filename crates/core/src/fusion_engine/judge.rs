use crate::fusion_engine::schema::{ModelAnswer, JudgeAnalysis, ModelConfig};
use crate::fusion_engine::models::call_model;

pub fn build_judge_prompt(user_prompt: &str, answers: &[ModelAnswer]) -> String {
    let mut prompt = String::new();

    prompt.push_str("You are a judge model. Compare the model responses. Do not write the final answer.\n");
    prompt.push_str("Return strict JSON with these fields:\n");
    prompt.push_str("consensus, disagreements, unique_insights, blind_spots, risk_flags, recommended_final_position.\n");
    prompt.push_str("All fields except 'recommended_final_position' must be arrays of strings.\n");
    prompt.push_str("Ensure response is valid raw JSON ONLY (no markdown formatting code blocks).\n\n");

    prompt.push_str("USER REQUEST:\n");
    prompt.push_str(user_prompt);
    prompt.push_str("\n\nMODEL RESPONSES:\n");

    for answer in answers {
        prompt.push_str(&format!(
            "\n--- MODEL: {} ---\n{}\n",
            answer.model_name, answer.answer
        ));
    }

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
    
    // Strip markdown formatting if any
    let clean_json = response_text
        .trim()
        .trim_start_matches("```json")
        .trim_start_matches("```")
        .trim_end_matches("```")
        .trim()
        .to_string();

    let analysis: JudgeAnalysis = serde_json::from_str(&clean_json)
        .unwrap_or_else(|e| {
            log::warn!("Failed to parse judge JSON: {}. Using fallback model summary.", e);
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
    writer_prompt.push_str("Prioritize consensus.\n");
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
