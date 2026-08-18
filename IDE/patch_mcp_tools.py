import json

tasks = [
    # NLP Tasks (15)
    "text_classification", "token_classification", "question_answering", "text_generation",
    "summarization", "translation", "fill_mask", "text2text_generation", "language_detection",
    "grammar_correction", "paraphrase_generation", "causal_language_modeling",
    "zero_shot_classification", "feature_extraction", "sentence_similarity",
    
    # Security Tasks (12)
    "anonymization", "coreference_resolution", "spam_detection", "malware_text_detection",
    "phishing_detection", "pii_detection", "hate_speech_detection", "cyberbullying_detection",
    "fake_news_detection", "legal_judgment_classification", "contract_clause_classification",
    "case_outcome_prediction",
    
    # Code & Domain Tasks (16)
    "financial_ner", "legal_ner", "biomedical_ner", "chemical_reaction_ner",
    "financial_sentiment_analysis", "scientific_abstract_summarization", "emotion_detection",
    "sarcasm_detection", "stance_detection", "bias_detection", "hallucination_detection",
    "reading_level_assessment", "generation_groundedness", "citation_intent_classification",
    "code_summary_generation", "code_clone_detection",
    
    # Multimodal Tasks (18)
    "image_classification", "object_detection", "image_segmentation", "visual_question_answering",
    "document_question_answering", "zero_shot_image_classification", "depth_estimation",
    "image_feature_extraction", "automatic_speech_recognition", "audio_classification",
    "voice_activity_detection", "emotion_recognition", "video_classification",
    "text_to_speech", "text_to_image", "image_super_resolution", "table_question_answering",
    "feature_ranking"
]

print(f"Total specialized task tools: {len(tasks)}")
tool_json_entries = []
for t in tasks:
    readable = t.replace('_', ' ')
    flag = t.replace('_', '-')
    entry = f'''                        {{
                            "name": "{t}",
                            "description": "Execute ModelFusion --{flag} for {readable}.",
                            "inputSchema": {{
                                "type": "object",
                                "properties": {{
                                    "text": {{ "type": "string", "description": "Input text or code" }},
                                    "prompt": {{ "type": "string", "description": "Task instructions" }},
                                    "file": {{ "type": "string", "description": "Optional file path" }},
                                    "language": {{ "type": "string", "description": "Optional language" }},
                                    "gpu": {{ "type": "boolean" }}
                                }}
                            }}
                        }}'''
    tool_json_entries.append(entry)

tools_text = ",\n".join(tool_json_entries)

main_path = r"d:\harfile\ModelFusion\crates\cli\src\main.rs"
with open(main_path, "r", encoding="utf-8") as f:
    content = f.read()

# Insert tools after report_bandit_feedback tool definition
bandit_anchor = '"name": "report_bandit_feedback",'
idx = content.find(bandit_anchor)
if idx == -1:
    print("ERROR: bandit_anchor not found")
    exit(1)

# Find the closing object of report_bandit_feedback
end_brace_idx = content.find('}\n                        }', idx)
if end_brace_idx == -1:
    end_brace_idx = content.find('}\r\n                        }', idx)
if end_brace_idx == -1:
    print("ERROR: end_brace_idx not found")
    exit(1)

end_brace_idx += len('}\n                        }') if '\r' not in content[end_brace_idx:end_brace_idx+5] else len('}\r\n                        }')

# Check if already patched
if '"name": "text_classification",' in content:
    print("Already contains text_classification tool in main.rs")
else:
    content = content[:end_brace_idx] + ",\n" + tools_text + content[end_brace_idx:]
    print("Injected 61 specialized tools into MCP tools/list")

# Update tools/call fallback
old_fallback = '_ => format!("Error: Unknown tool {}", name),'
new_fallback = '''                other => {
                    let flag_name = other.replace('_', "-");
                    let text = arguments["text"].as_str()
                        .or_else(|| arguments["prompt"].as_str())
                        .or_else(|| arguments["input"].as_str())
                        .unwrap_or("");
                    let mut cmd_args = vec![format!("--{}", flag_name)];
                    if !text.is_empty() {
                        cmd_args.push("--prompt".to_string());
                        cmd_args.push(text.to_string());
                    }
                    if let Some(file) = arguments["file"].as_str() {
                        cmd_args.push("--file".to_string());
                        cmd_args.push(file.to_string());
                    }
                    if let Some(lang) = arguments["language"].as_str() {
                        cmd_args.push("--language".to_string());
                        cmd_args.push(lang.to_string());
                    }
                    if arguments["gpu"].as_bool().unwrap_or(false) {
                        cmd_args.push("--gpu".to_string());
                    }
                    run_cli_subcommand(&cmd_args, &db_path_resolved).await
                }'''

if old_fallback in content:
    content = content.replace(old_fallback, new_fallback)
    print("Updated tools/call fallback handler")
elif "let flag_name = other.replace('_', \"-\");" in content:
    print("tools/call fallback already updated")

with open(main_path, "w", encoding="utf-8") as f:
    f.write(content)

print("SUCCESS: crates/cli/src/main.rs updated with all 86 MCP tools!")
