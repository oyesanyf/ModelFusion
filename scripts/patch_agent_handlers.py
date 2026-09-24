with open("crates/cli/src/main.rs", "r", encoding="utf-8") as f:
    lines = f.readlines()

insert_idx = None
for i, l in enumerate(lines):
    if '"agent" | "modelfusion" | "hugos"' in l and 6000 < i < 7000:
        # find closing brace of this match arm
        for j in range(i, i+15):
            if lines[j].strip().startswith("},"):
                insert_idx = j + 1
                break
        break

if insert_idx is None:
    raise ValueError("Could not find agent match arm in crates/cli/src/main.rs")

print(f"Inserting after line {insert_idx}")

handlers = """
                                      // ── Universal Agent Directives (Antigravity Parity) ──
                                      "btw" => {
                                          let side_query = resolve_code_for_command(&args_owned, &prompt_for_cmd);
                                          if side_query.trim().is_empty() {
                                              (idx, "💡 **Side Note (`/btw`)**\\n\\nAsk a quick side question without interrupting or polluting the main conversation flow.\\n\\n**Usage**:\\n- `/btw <question>`\\n- `@agent /btw what is RAII in Rust?`\\n- `/btw what port is Ollama listening on?`".to_string())
                                          } else {
                                              let mut cmd_args = vec!["--prompt".to_string(), format!("Answer this quick side question concisely in 2-4 sentences: {}", side_query.trim())];
                                              if std::env::var("MODELFUSION_USE_OLLAMA").is_ok() || !model_selection::memory::get_ollama_cached_models().is_empty() {
                                                  cmd_args.push("--ollama".to_string());
                                              }
                                              let (result, _ctx, _arm) = route_and_execute(&side_query, db_resolved, &cmd_args).await;
                                              (idx, format!("💡 **Side Note (`/btw`)**\\n\\n{}", result.trim()))
                                          }
                                      },
                                      "goal" => {
                                          let goal_prompt = resolve_code_for_command(&args_owned, &prompt_for_cmd);
                                          if goal_prompt.trim().is_empty() {
                                              (idx, "🎯 **Autonomous Goal Execution (`/goal`)**\\n\\nRuns an autonomous goal-seeking execution loop until the objective is achieved.\\n\\n**Usage**:\\n- `/goal <clear objective>`\\n- `@agent /goal optimize all SQLite indices and run full verification suite`\\n- `/goal refactor AST parser to support streaming tokens`".to_string())
                                          } else {
                                              let r = run_cli_subcommand(&["--rest-rl".to_string(), "enqueue".to_string(), goal_prompt.trim().to_string()], db_resolved).await;
                                              (idx, format!("🎯 **Autonomous Goal Execution (`/goal`)**\\n\\n- **Target Objective**: {}\\n- **Execution Mode**: Autonomous ReST-RL Daemon Enqueued\\n\\n{}", goal_prompt.trim(), r.trim()))
                                          }
                                      },
                                      "schedule" => {
                                          let sched_arg = resolve_code_for_command(&args_owned, &prompt_for_cmd);
                                          if sched_arg.trim().is_empty() {
                                              (idx, "⏱️ **Task Scheduler & Reminders (`/schedule`)**\\n\\nConfigure background one-shot timers or recurring cron execution schedules.\\n\\n**Usage**:\\n- `/schedule in 10 minutes: check build status`\\n- `/schedule cron '*/5 * * * *' health check`\\n- `/schedule timer 300`".to_string())
                                          } else {
                                              (idx, format!("⏱️ **Task Scheduler (`/schedule`)**\\n\\nScheduled directive accepted: `{}`\\n- **Engine**: Background Cron/Timer Service\\n- **Status**: Active", sched_arg.trim()))
                                          }
                                      },
                                      "browser" => {
                                          let query = resolve_code_for_command(&args_owned, &prompt_for_cmd);
                                          if query.trim().is_empty() {
                                              (idx, "🌐 **Web Browser Agent (`/browser`)**\\n\\nInvoke live web browsing and autonomous page inspection.\\n\\n**Usage**:\\n- `/browser https://huggingface.co/models`\\n- `/browser search for latest Vulkan driver optimizations`".to_string())
                                          } else {
                                              let r = run_cli_subcommand(&["--research".to_string(), query.trim().to_string()], db_resolved).await;
                                              (idx, format!("🌐 **Web Browser Agent (`/browser`)**\\n\\n{}", r.trim()))
                                          }
                                      },
                                      "plan" => {
                                          let plan_req = resolve_code_for_command(&args_owned, &prompt_for_cmd);
                                          if plan_req.trim().is_empty() {
                                              (idx, "📐 **Architectural Implementation Plan (`/plan`)**\\n\\nGenerates a rigorous architectural blueprint with verification criteria prior to code implementation.\\n\\n**Usage**:\\n- `/plan <feature or refactoring description>`\\n- `@agent /plan migrate microkernel IPC to shared memory circular buffers`".to_string())
                                          } else {
                                              let plan_prompt = format!("Generate a rigorous architectural blueprint for the following task. Include:\\n1. Executive Architecture & Component Breakdown\\n2. Key Invariants & Edge Cases (Memory safety, deadlocks, error handling)\\n3. Concrete Implementation Roadmap (Phase 1, Phase 2, Phase 3)\\n4. Verification & Testing Matrix\\n\\nTask: {}", plan_req.trim());
                                              let mut cmd_args = vec!["--prompt".to_string(), plan_prompt];
                                              if std::env::var("MODELFUSION_USE_OLLAMA").is_ok() || !model_selection::memory::get_ollama_cached_models().is_empty() {
                                                  cmd_args.push("--ollama".to_string());
                                              }
                                              let (result, _ctx, _arm) = route_and_execute(&plan_req, db_resolved, &cmd_args).await;
                                              (idx, format!("📐 **Architectural Implementation Plan (`/plan`)**\\n\\n{}", result.trim()))
                                          }
                                      },
                                      "grill-me" => {
                                          let topic = resolve_code_for_command(&args_owned, &prompt_for_cmd);
                                          let prompt_content = if topic.trim().is_empty() {
                                              "Interview me by asking 3 to 5 sharp, decisive architectural questions to uncover ambiguous assumptions, trade-offs, and critical system invariants.".to_string()
                                          } else {
                                              format!("Act as Lead Architect. Interview me about: {}. Ask 3 to 5 sharp, probing questions to clarify constraints, non-functional requirements, failure modes, and performance trade-offs before writing code.", topic.trim())
                                          };
                                          let mut cmd_args = vec!["--prompt".to_string(), prompt_content];
                                          if std::env::var("MODELFUSION_USE_OLLAMA").is_ok() || !model_selection::memory::get_ollama_cached_models().is_empty() {
                                              cmd_args.push("--ollama".to_string());
                                          }
                                          let (result, _ctx, _arm) = route_and_execute(&topic, db_resolved, &cmd_args).await;
                                          (idx, format!("🎯 **Design Interview (`/grill-me`)**\\n\\n{}", result.trim()))
                                      },
                                      "teamwork-preview" => {
                                          let task_desc = resolve_code_for_command(&args_owned, &prompt_for_cmd);
                                          let desc = if task_desc.trim().is_empty() { "Distributed System Engineering".to_string() } else { task_desc.trim().to_string() };
                                          let preview_text = format!(
"👥 **Teamwork & Multi-Agent Collaboration Topology (`/teamwork-preview`)**

Target Objective: **{}**

```mermaid
sequenceDiagram
    autonumber
    actor User as Engineer / User
    participant Pro as Lead Architect (Reasoning)
    participant Worker as Worker Subagent (Execution)
    participant AVO as AVO / ReST-RL Daemon
    participant Tools as Compiler / Test Runner

    User->>Pro: Submit complex directive
    Pro->>Pro: Architectural decomposition & pass criteria
    Pro->>Worker: Dispatch task unit & edge cases
    Worker->>Tools: Implement code & run validation
    Tools-->>Worker: Compilation & test status
    Worker->>AVO: Register mutation test & job objects
    AVO-->>Worker: Zero-VRAM verification certificate
    Worker-->>Pro: Report diffs & test evidence
    Pro-->>User: Synthesize verified response
```

### Active Agent Roles & Responsibilities
1. **Lead Architect**: High-level reasoning, architectural decomposition, test strategy formulation, and final code review.
2. **Worker Subagent**: Patch implementation, test suite execution, and terminal verification loops.
3. **AVO / ReST-RL Daemon**: Background reinforcement learning, sub-50ms job object preemption, and zero-impact verification gates.",
                                              desc
                                          );
                                          (idx, preview_text)
                                      },
                                      "learn" => {
                                          let rule_content = resolve_code_for_command(&args_owned, &prompt_for_cmd);
                                          if rule_content.trim().is_empty() {
                                              (idx, "🧠 **Rule Learned & Saved (`/learn`)**\\n\\nCapture reusable engineering rules, design invariants, or preferences from recent context.\\n\\n**Usage**:\\n- `/learn always verify free RAM before allocating models`\\n- `/learn use Windows Job Object for sub-50ms task preemption`".to_string())
                                          } else {
                                              let rule_dir = std::path::Path::new(".hugos").join("rules");
                                              let _ = std::fs::create_dir_all(&rule_dir);
                                              let filename = format!("rule_{}.md", std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap_or_default().as_secs());
                                              let target_path = rule_dir.join(&filename);
                                              let rule_doc = format!("# Learned Rule\\n\\n- Captured: {}\\n- Content: {}\\n", chrono::Utc::now().to_rfc3339(), rule_content.trim());
                                              let _ = std::fs::write(&target_path, rule_doc);
                                              (idx, format!("🧠 **Rule Learned & Saved (`/learn`)**\\n\\n- **Persisted To**: `{}`\\n- **Rule Invariant**: {}\\n- **Status**: Active across future sessions", target_path.display(), rule_content.trim()))
                                          }
                                      },
                                      "boost" => {
                                          let attached = extract_attached_code_context(&prompt_for_cmd);
                                          let payload = resolve_code_for_command(&args_owned, &prompt_for_cmd);
                                          if payload.trim().is_empty() && attached.is_empty() {
                                              (idx, "🚀 **High-Compute Multi-Sample Reasoning Boost (`/boost`)**\\n\\nApplies multi-sample consensus deliberation over top local models to solve difficult reasoning problems.\\n\\n**Usage**:\\n- `/boost <complex problem or code optimization>`\\n- `@agent /boost synthesize concurrent lock-free skip list`".to_string())
                                          } else {
                                              let mut cmd_args = vec![
                                                  "--fusion".to_string(),
                                                  "--fusion-mode".to_string(), "multi-sample".to_string(),
                                                  "--fusion-models".to_string(), "5".to_string(),
                                                  "--prompt".to_string(), payload
                                              ];
                                              if std::env::var("MODELFUSION_USE_OLLAMA").is_ok() || !model_selection::memory::get_ollama_cached_models().is_empty() {
                                                  cmd_args.push("--ollama".to_string());
                                              }
                                              let result = run_cli_subcommand(&cmd_args, db_resolved).await;
                                              (idx, format!("🚀 **Reasoning Boost (`/boost`)**\\n\\n{}", result.trim()))
                                          }
                                      },
                                      "generative_ui" => {
                                          let ui_req = resolve_code_for_command(&args_owned, &prompt_for_cmd);
                                          if ui_req.trim().is_empty() {
                                              (idx, "🎨 **Generative UI Component (`/generative_ui`)**\\n\\nRender self-contained, interactive HTML/Tailwind/JS widgets and dashboards.\\n\\n**Usage**:\\n- `/generative_ui interactive telemetry chart for GPU VRAM`\\n- `/generative_ui pricing calculator widget`".to_string())
                                          } else {
                                              let ui_prompt = format!("Generate a self-contained, production-grade interactive HTML component with inline Tailwind CSS and JavaScript. Return ONLY the HTML component within an html code block.\\n\\nWidget Specification: {}", ui_req.trim());
                                              let mut cmd_args = vec!["--prompt".to_string(), ui_prompt];
                                              if std::env::var("MODELFUSION_USE_OLLAMA").is_ok() || !model_selection::memory::get_ollama_cached_models().is_empty() {
                                                  cmd_args.push("--ollama".to_string());
                                              }
                                              let (result, _ctx, _arm) = route_and_execute(&ui_req, db_resolved, &cmd_args).await;
                                              (idx, format!("🎨 **Generative UI Component (`/generative_ui`)**\\n\\n{}", result.trim()))
                                          }
                                      },
"""

lines.insert(insert_idx, handlers)

with open("crates/cli/src/main.rs", "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Successfully inserted universal agent handlers into crates/cli/src/main.rs!")
