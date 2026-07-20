# ModelFusion / HugOS IDE — Fix Memory

## Session: 2026-07-19 → 2026-07-20

### Fix 1: Title Bug — Chat Title Shows Model Answer Instead of User Question
- **Root Cause**: `ChatTitleProvider` in `title.ts` sent the user's question to the LLM and used the LLM's *answer* as the title (e.g. "ABUJA AS CAPITAL OF NIGERIA" instead of "CAPITAL OF NIGERIA").
- **Fix**: Replaced LLM-based title generation with direct extraction of the user's first prompt, truncated to 100 chars.
- **File**: `IDE/vscode/extensions/copilot/src/extension/prompt/node/title.ts`
- **Commit**: `11e78dd7`

### Fix 2: Accept/Reject (Keep/Undo) Buttons Not Showing on Code Blocks
- **Root Cause**: Multiple layers of safety filters in `_tryInlineApply()` (commentary detection, size check, overlap check, keyword guard) were rejecting valid code blocks.
- **Fix**: Removed the custom `_tryInlineApply()` call entirely. VS Code already provides native **Keep/Undo** buttons on every code block in chat responses via built-in code block actions (Apply to Editor, Insert at Cursor, Copy).
- **File**: `IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelFusionProvider.ts`
- **Commit**: `4124eee0`
- **Lesson**: Don't reinvent VS Code's built-in functionality.

### Fix 3: Token Null Guard
- **Root Cause**: `token.onCancellationRequested()` crashed when `token` was null/undefined on certain meta-requests (summary, title).
- **Fix**: Changed to `token?.onCancellationRequested()` (optional chaining).
- **File**: `modelFusionProvider.ts`

### Fix 4: /evolve Slash Command Not Detected
- **Root Cause**: `/evolve` was registered as a VS Code `chatParticipant` slash command in `package.json`. VS Code's chat framework consumed the `/evolve` prefix completely — stripped it from messages and did NOT pass it to the language model provider. No trace of `/evolve` appeared in messages or options.
- **Fix**: Removed `/evolve` (and 168 other custom slash commands) from `package.json`'s `chatParticipants.commands` registrations. Only kept VS Code built-ins (`explain`, `fix`, `tests`, `new`, `review`, `newNotebook`, `file`, `folder`). Custom commands now pass through as raw text and are detected by the model provider's regex.
- **File**: `IDE/vscode/extensions/copilot/package.json`
- **Debug Method**: Added comprehensive logging of ALL message roles, content, and options keys to trace exactly what VS Code sends.
- **Key Insight**: `options` keys are `["tools","modelOptions","configuration","modelConfiguration","requestInitiator","toolMode"]` — NO `command` or `slashCommand` field exists.

### Fix 5: /evolve LLM Generation Failed — "list index out of range"
- **Root Cause**: OpenEvolve uses the OpenAI Python SDK which calls `/v1/chat/completions`. The ModelFusion CLI at port 5000 did NOT have this endpoint — only `/orchestrate`. The SDK received `{"content":"Error: Unknown API path /v1/chat/completions"}` and crashed on `response.choices[0]`.
- **Fix**: Added `/v1/chat/completions` route to the Rust CLI (`crates/cli/src/main.rs`) that:
  1. Translates OpenAI `messages[]` format → single prompt string
  2. Routes through the existing `/orchestrate` pipeline (uses ALL backends: Ollama, OpenVINO, etc.)
  3. Wraps the response in OpenAI-compatible format (`choices[0].message.content`)
- **File**: `crates/cli/src/main.rs`
- **API Base**: Kept at `http://127.0.0.1:5000/v1` so /evolve uses ModelFusion's multi-backend routing.

### Fix 6: Rust Compile Error — rcedit branding type mismatch
- **Root Cause**: `.args([&exe_str, flag, key, value])` mixed `&String` with `&&str`.
- **Fix**: `.args([exe_str.as_str(), *flag, *key, *value])` — all `&str`.
- **File**: `crates/cli/src/main.rs` line ~4647

## Key Architecture Insights
- **VS Code strips registered slash commands** at the chat participant level BEFORE they reach the language model provider. Never register custom commands that you want the model provider to handle.
- **VS Code's built-in code block actions** (Keep/Undo, Apply to Editor, Insert at Cursor) work automatically on all fenced code blocks in chat responses. No custom inline apply needed.
- **OpenEvolve uses the OpenAI SDK** which requires a `/v1/chat/completions` endpoint with `choices[0].message.content` response format.
- **ModelFusion CLI roles**: `msg[0]` has role `3` (system), not `0`. Role mapping: 1=user, 2=assistant, 3=system.

## Git Commit History (recent)
- `11e78dd7` — fix: restore original inline apply (no guard), title uses user prompt, token null guard
- `4124eee0` — fix: remove custom _tryInlineApply, use VS Code native Keep/Undo code actions
- Pending — fix: remove 168 custom slash commands, add /v1/chat/completions to CLI
