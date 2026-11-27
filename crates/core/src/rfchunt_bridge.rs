//! Safe, process-scoped Rust bridge for invoking RFCHunt defensive auditing workflows
//! directly from ModelFusion / HugOS IDE using local abliterated models.
//!
//! Security & Environment Invariants:
//! - Strictly `shell = false` (explicit argv array, zero command-string interpolation).
//! - Allowlisted defensive RFCHunt subcommands only (fails closed on unknown commands).
//! - Process-scoped environment variables only (NEVER mutates Windows Registry or system PATH).

use anyhow::{bail, Result};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

/// Allowlisted RFCHunt CLI subcommands that ModelFusion can orchestrate safely.
pub const ALLOWED_RFCHUNT_SUBCOMMANDS: &[&str] = &[
    "fast-ooda",
    "ensemble-audit",
    "freshness-watch",
    "linux-poc",
    "eligibility-check",
    "h1-draft-stage",
    "check-drafts",
    "qa-drafts",
];

/// Configuration for running RFCHunt against ModelFusion's local abliterated fusion engine.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RfcHuntBridgeConfig {
    pub rfchunt_root: PathBuf,
    pub python_executable: String,
    pub modelfusion_endpoint: String,
    pub ollama_endpoint: String,
    pub hugos_cdp_url: String,
    pub preferred_abliterated_model: Option<String>,
    pub use_modelfusion_server: bool,
    pub dry_run: bool,
    pub timeout_secs: u64,
}

impl Default for RfcHuntBridgeConfig {
    fn default() -> Self {
        let rfchunt_root = std::env::var("RFCHUNT_ROOT")
            .map(PathBuf::from)
            .unwrap_or_else(|_| PathBuf::from(r"d:\harfile\rfchunt"));
        let modelfusion_endpoint = std::env::var("MODELFUSION_ENDPOINT")
            .unwrap_or_else(|_| "http://127.0.0.1:5000".to_string());
        let ollama_endpoint = std::env::var("LOCAL_OLLAMA_ENDPOINT")
            .or_else(|_| std::env::var("OLLAMA_ENDPOINT"))
            .unwrap_or_else(|_| "http://127.0.0.1:11434".to_string());
        let hugos_cdp_url = std::env::var("RFCHUNT_HUGOS_CDP_URL")
            .unwrap_or_else(|_| "http://127.0.0.1:9222".to_string());

        Self {
            rfchunt_root,
            python_executable: "python".to_string(),
            modelfusion_endpoint,
            ollama_endpoint,
            hugos_cdp_url,
            preferred_abliterated_model: None,
            use_modelfusion_server: true,
            dry_run: false,
            timeout_secs: 600,
        }
    }
}

/// Deterministic command specification returned by `build_rfchunt_command`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RfcHuntCommandSpec {
    pub program: String,
    pub args: Vec<String>,
    pub working_dir: PathBuf,
    pub env: BTreeMap<String, String>,
    pub selected_security_model: String,
    pub active_security_tier: String,
}

/// Execution output from running an allowlisted RFCHunt command.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RfcHuntRunOutput {
    pub exit_code: i32,
    pub success: bool,
    pub stdout: String,
    pub stderr: String,
    pub spec: RfcHuntCommandSpec,
}

/// Validates and builds a `shell = false` command specification for running an RFCHunt
/// defensive subcommand backed by ModelFusion + runtime-memory-fitted abliterated models.
pub fn build_rfchunt_command(
    cfg: &RfcHuntBridgeConfig,
    subcommand: &str,
    extra_args: &[String],
) -> Result<RfcHuntCommandSpec> {
    let sub = subcommand.trim();
    if !ALLOWED_RFCHUNT_SUBCOMMANDS.contains(&sub) {
        bail!(
            "Unsupported RFCHunt subcommand '{}'. Allowed: {:?}",
            sub,
            ALLOWED_RFCHUNT_SUBCOMMANDS
        );
    }

    // Reject shell metacharacters or control characters in extra_args
    for arg in extra_args {
        if arg.chars().any(|c| c.is_control()) {
            bail!("Refusing control character in RFCHunt argument");
        }
    }

    let script_path = cfg.rfchunt_root.join("revenue_cli.py");
    let mut args = vec![script_path.to_string_lossy().into_owned(), sub.to_string()];
    args.extend(extra_args.iter().cloned());
    if cfg.dry_run && !args.iter().any(|a| a == "--dry-run") {
        args.push("--dry-run".to_string());
    }

    // Select hardware-fitted abliterated security model using live free RAM/VRAM
    let mem = model_selection::memory::SystemMemory::detect_live();
    let sec_eval = mem.assess_security_abliterated_for_task();
    let chosen_model = cfg
        .preferred_abliterated_model
        .as_deref()
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
        .map(model_selection::memory::map_hf_to_ollama)
        .unwrap_or_else(|| sec_eval.recommended_primary.clone());

    let mut env = BTreeMap::new();
    env.insert("PYTHONIOENCODING".to_string(), "utf-8".to_string());
    env.insert(
        "RFCHUNT_USE_MODELFUSION".to_string(),
        if cfg.use_modelfusion_server { "1" } else { "0" }.to_string(),
    );
    env.insert(
        "MODELFUSION_ENDPOINT".to_string(),
        cfg.modelfusion_endpoint.trim_end_matches('/').to_string(),
    );
    env.insert(
        "OLLAMA_ENDPOINT".to_string(),
        cfg.ollama_endpoint.trim_end_matches('/').to_string(),
    );
    env.insert(
        "LOCAL_OLLAMA_ENDPOINT".to_string(),
        cfg.ollama_endpoint.trim_end_matches('/').to_string(),
    );
    env.insert(
        "RFCHUNT_HUGOS_CDP_URL".to_string(),
        cfg.hugos_cdp_url.trim_end_matches('/').to_string(),
    );
    env.insert("RFCHUNT_LLM_MODEL".to_string(), chosen_model.clone());
    env.insert("LOCAL_MODEL".to_string(), chosen_model.clone());
    env.insert("RFCHUNT_ENABLE_ANTI_JUNK_GUARD".to_string(), "1".to_string());

    Ok(RfcHuntCommandSpec {
        program: cfg.python_executable.clone(),
        args,
        working_dir: cfg.rfchunt_root.clone(),
        env,
        selected_security_model: chosen_model,
        active_security_tier: sec_eval.active_tier,
    })
}

/// Executes an allowlisted RFCHunt command asynchronously with a strict timeout and
/// `kill_on_drop(true)` deterministic process cleanup.
pub async fn execute_rfchunt_command(
    cfg: &RfcHuntBridgeConfig,
    subcommand: &str,
    extra_args: &[String],
) -> Result<RfcHuntRunOutput> {
    let spec = build_rfchunt_command(cfg, subcommand, extra_args)?;
    let script = Path::new(&spec.args[0]);
    if !script.is_file() {
        bail!(
            "RFCHunt entrypoint '{}' does not exist. Set RFCHUNT_ROOT to your rfchunt checkout.",
            script.display()
        );
    }

    let mut cmd = tokio::process::Command::new(&spec.program);
    #[cfg(windows)]
    {
        cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW
    }
    cmd.args(&spec.args)
        .current_dir(&spec.working_dir)
        .envs(&spec.env)
        .kill_on_drop(true);

    let timeout_dur = std::time::Duration::from_secs(cfg.timeout_secs.max(10));
    let out = tokio::time::timeout(timeout_dur, cmd.output())
        .await
        .map_err(|_| anyhow::anyhow!("RFCHunt '{}' timed out after {}s", subcommand, timeout_dur.as_secs()))??;

    let exit_code = out.status.code().unwrap_or(-1);
    Ok(RfcHuntRunOutput {
        exit_code,
        success: out.status.success(),
        stdout: String::from_utf8_lossy(&out.stdout).into_owned(),
        stderr: String::from_utf8_lossy(&out.stderr).into_owned(),
        spec,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_build_rfchunt_command_allowlist_and_env() {
        let cfg = RfcHuntBridgeConfig {
            rfchunt_root: PathBuf::from(r"d:\harfile\rfchunt"),
            preferred_abliterated_model: Some("OBLITERATUS/Gemma-4-12B-OBLITERATED".to_string()),
            dry_run: true,
            ..Default::default()
        };

        let spec = build_rfchunt_command(
            &cfg,
            "fast-ooda",
            &["--target".to_string(), r"d:\harfile\rfchunt".to_string()],
        )
        .expect("fast-ooda should be allowed");

        assert_eq!(spec.program, "python");
        assert!(spec.args[0].ends_with("revenue_cli.py"));
        assert_eq!(spec.args[1], "fast-ooda");
        assert!(spec.args.iter().any(|a| a == "--dry-run"));
        assert_eq!(
            spec.selected_security_model,
            "hf.co/OBLITERATUS/Gemma-4-12B-OBLITERATED:Q4_K_M"
        );
        assert_eq!(spec.env.get("RFCHUNT_USE_MODELFUSION").map(String::as_str), Some("1"));
        assert_eq!(spec.env.get("RFCHUNT_ENABLE_ANTI_JUNK_GUARD").map(String::as_str), Some("1"));
        assert_eq!(spec.env.get("PYTHONIOENCODING").map(String::as_str), Some("utf-8"));

        // Unknown subcommand MUST fail closed
        assert!(build_rfchunt_command(&cfg, "rm-rf", &[]).is_err());

        // Control characters in args MUST fail closed
        assert!(build_rfchunt_command(&cfg, "fast-ooda", &["bad\x07arg".to_string()]).is_err());
    }
}
