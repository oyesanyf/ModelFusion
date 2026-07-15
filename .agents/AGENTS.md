# Project Rules & User Preferences

## Git Push Preferences
- **Do Not Push to Microsoft**: Never run `git push` inside the `IDE/vscode` directory or any remote pointing to Microsoft's repositories. Only push to the main `ModelFusion` repository at `https://github.com/oyesanyf/ModelFusion.git`.

## Model Slowdown & Verification Blueprints
- **Conditional Trigger**: If your underlying model environment is running a Flash variant (e.g., Gemini 3.5 Flash or Gemini 1.5 Flash), you are strictly required to drop back into a "Reasoning Sandbox" before generating output. You must use the corresponding blueprint below based on the task type to mitigate speed-driven logic slips.
- If running a full-scale reasoning model, process standard prompt requests normally unless a structured breakdown is explicitly requested.

### 1. The "Sandbox & Verify" Blueprint (Coding Tasks)
When generating new code architectures, scripts, or components under Flash constraints, split your response into three strict phases. Keep the reasoning sections concise to minimize latency:
1. **SANDBOX**: Lay out the logical implementation plan, specify your targeted libraries/crates, and identify three potential edge cases (specifically look for: memory allocation/OOM in Rust, resource leaks/unhandled disposables in TS, or asynchronous boundary conditions).
2. **VERIFY**: Review the plan against those exact edge cases, explicitly stating how your code avoids failure.
3. **OUTPUT**: Write the clean, finalized code. Ensure variable types, error handling, and safety boundaries are strictly verified.

### 2. The "Deconstruct & Solve" Blueprint (Math & Logic Tasks)
For complex calculations or logic evaluations under Flash constraints:
- Do not provide a final answer or conclusion in your first sentence.
- First, explicitly list every piece of raw data or variable provided in the prompt.
- Second, state the core mathematical or logical rule required to solve it.
- Third, show your work step-by-step, detailing the transformation at each stage.
- Finally, output the definitive answer based strictly on the work shown above.

### 3. The "Self-Correction" Blueprint (Debugging & Errors)
When processing error logs or broken code under Flash constraints:
1. **TRACE**: Trace the execution path or compilation flow line-by-line until you find the exact point of failure.
2. **ISOLATE**: Explain why that specific line, syntax, or logic caused the mistake.
3. **REFACTOR**: Provide the corrected solution, specifically highlighting the fix introduced to solve the isolation phase.

### 4. The "Retrieve & Struct" Blueprint (Research & Q&A Tasks)
For informational queries, research, or Q&A that do not involve modifying code:
1. **RETRIEVE**: List the exact files, git logs, or web sources consulted.
2. **CONTEXT**: Briefly state the key verified facts and any remaining ambiguities.
3. **ANSWER**: Present the structured, concise response (using bullet points or tables where appropriate).