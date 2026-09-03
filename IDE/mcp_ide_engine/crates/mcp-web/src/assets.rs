//! Embedded Web Dashboard assets (HTML, CSS, JavaScript)

pub const INDEX_HTML: &str = r#"<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP IDE Engine — Web Dashboard</title>
    <style>
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-tertiary: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.2);
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --border: #334155;
            --radius: 8px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, monospace;
        }

        body {
            background-color: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        header {
            background-color: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
            padding: 0.75rem 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-weight: 700;
            font-size: 1.25rem;
            color: var(--accent);
        }

        .badge {
            font-size: 0.75rem;
            padding: 0.2rem 0.5rem;
            border-radius: 9999px;
            background: var(--accent-glow);
            color: var(--accent);
            border: 1px solid var(--accent);
        }

        nav {
            display: flex;
            gap: 0.5rem;
        }

        .nav-btn {
            background: transparent;
            border: 1px solid transparent;
            color: var(--text-secondary);
            padding: 0.5rem 1rem;
            border-radius: var(--radius);
            cursor: pointer;
            font-weight: 500;
            transition: all 0.2s;
        }

        .nav-btn:hover {
            color: var(--text-primary);
            background: var(--bg-tertiary);
        }

        .nav-btn.active {
            background: var(--accent);
            color: #0f172a;
            font-weight: 600;
        }

        main {
            flex: 1;
            padding: 1.5rem;
            max-width: 1400px;
            margin: 0 auto;
            width: 100%;
        }

        .tab-pane {
            display: none;
            flex-direction: column;
            gap: 1.5rem;
        }

        .tab-pane.active {
            display: flex;
        }

        .grid-3 {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1.5rem;
        }

        .card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: 600;
            color: var(--accent);
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.5rem;
        }

        .progress-bar-bg {
            background: var(--bg-tertiary);
            border-radius: 4px;
            height: 12px;
            overflow: hidden;
            width: 100%;
        }

        .progress-bar-fill {
            height: 100%;
            background: var(--accent);
            transition: width 0.3s ease;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.875rem;
        }

        th, td {
            padding: 0.6rem 0.8rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }

        th {
            color: var(--text-secondary);
            font-weight: 600;
        }

        pre {
            background: var(--bg-primary);
            padding: 0.75rem;
            border-radius: var(--radius);
            font-size: 0.85rem;
            overflow-x: auto;
            color: var(--accent);
            border: 1px solid var(--border);
        }

        button.btn-action {
            background: var(--accent);
            color: #0f172a;
            border: none;
            padding: 0.4rem 0.8rem;
            border-radius: var(--radius);
            cursor: pointer;
            font-weight: 600;
            transition: opacity 0.2s;
        }

        button.btn-action:hover {
            opacity: 0.9;
        }

        button.btn-danger {
            background: var(--danger);
            color: white;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }

        input, select, textarea {
            background: var(--bg-primary);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 0.5rem;
            border-radius: var(--radius);
            font-size: 0.9rem;
        }

        input:focus, select:focus, textarea:focus {
            outline: 1px solid var(--accent);
        }

        .log-container {
            background: var(--bg-primary);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 0.75rem;
            height: 400px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 0.85rem;
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }

        .log-line {
            display: flex;
            gap: 0.5rem;
        }

        .log-time { color: var(--text-secondary); }
        .log-level-INFO { color: var(--success); font-weight: bold; }
        .log-level-WARN { color: var(--warning); font-weight: bold; }
        .log-level-ERROR { color: var(--danger); font-weight: bold; }
        .log-level-DEBUG { color: var(--accent); font-weight: bold; }
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <span>⚡ MCP IDE Engine</span>
            <span class="badge">v0.1.0</span>
            <span id="conn-status" class="badge" style="background: rgba(16, 185, 129, 0.2); color: #10b981; border-color: #10b981;">Connected</span>
        </div>
        <nav>
            <button class="nav-btn active" onclick="switchTab('tab-dashboard')">Dashboard</button>
            <button class="nav-btn" onclick="switchTab('tab-tasks')">Tasks</button>
            <button class="nav-btn" onclick="switchTab('tab-telemetry')">Telemetry</button>
            <button class="nav-btn" onclick="switchTab('tab-mcp')">MCP Tools</button>
            <button class="nav-btn" onclick="switchTab('tab-logs')">Logs</button>
        </nav>
    </header>

    <main>
        <!-- DASHBOARD TAB -->
        <div id="tab-dashboard" class="tab-pane active">
            <div class="grid-3">
                <div class="card">
                    <div class="card-header">
                        <span>CPU Utilization</span>
                        <span id="cpu-pct">0%</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div id="cpu-bar" class="progress-bar-fill" style="width: 0%;"></div>
                    </div>
                    <small id="cpu-cores" style="color: var(--text-secondary);">Logical Cores: --</small>
                </div>

                <div class="card">
                    <div class="card-header">
                        <span>System RAM</span>
                        <span id="ram-summary">0 / 0 GB</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div id="ram-bar" class="progress-bar-fill" style="width: 0%; background: #c084fc;"></div>
                    </div>
                    <small id="ram-avail" style="color: var(--text-secondary);">Available: -- GB</small>
                </div>

                <div class="card">
                    <div class="card-header">
                        <span>GPU VRAM</span>
                        <span id="gpu-name">Probing...</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div id="vram-bar" class="progress-bar-fill" style="width: 0%; background: #facc15;"></div>
                    </div>
                    <small id="vram-summary" style="color: var(--text-secondary);">VRAM: -- / -- GB</small>
                </div>
            </div>

            <div class="card">
                <div class="card-header">Quick Task Dispatch</div>
                <div style="display: flex; gap: 1rem; align-items: flex-end;">
                    <div class="form-group" style="flex: 2;">
                        <label>Command Name</label>
                        <input type="text" id="quick-cmd" placeholder="e.g. echo, compute_hash">
                    </div>
                    <div class="form-group" style="flex: 1;">
                        <label>Priority</label>
                        <select id="quick-priority">
                            <option value="Normal">Normal</option>
                            <option value="High">High</option>
                            <option value="Critical">Critical</option>
                            <option value="Low">Low</option>
                            <option value="Background">Background</option>
                        </select>
                    </div>
                    <button class="btn-action" onclick="dispatchQuickTask()">Dispatch</button>
                </div>
            </div>
        </div>

        <!-- TASKS TAB -->
        <div id="tab-tasks" class="tab-pane">
            <div class="card">
                <div class="card-header">
                    <span>Active Task Registry</span>
                    <button class="btn-action" onclick="fetchTasks()">Refresh</button>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Task ID</th>
                            <th>Command</th>
                            <th>Priority</th>
                            <th>State</th>
                            <th>Worker</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody id="task-table-body">
                        <tr><td colspan="6" style="text-align: center; color: var(--text-secondary);">No tasks currently active</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- TELEMETRY TAB -->
        <div id="tab-telemetry" class="tab-pane">
            <div class="card">
                <div class="card-header">Dynamic Hardware Telemetry & Sizing Model</div>
                <pre id="telemetry-json">Loading hardware snapshot...</pre>
            </div>
        </div>

        <!-- MCP TOOLS TAB -->
        <div id="tab-mcp" class="tab-pane">
            <div class="card">
                <div class="card-header">Registered MCP Tools & Execution Playground</div>
                <div style="display: flex; gap: 1.5rem;">
                    <div style="flex: 1;">
                        <label style="font-weight: 600; color: var(--text-secondary);">Select Tool</label>
                        <select id="tool-select" size="8" style="width: 100%; height: 200px; margin-top: 0.5rem;" onchange="inspectSelectedTool()"></select>
                    </div>
                    <div style="flex: 2; display: flex; flex-direction: column; gap: 0.75rem;">
                        <label style="font-weight: 600; color: var(--text-secondary);">Input Arguments (JSON)</label>
                        <textarea id="tool-args" style="height: 140px; font-family: monospace;" placeholder='{ "param": "value" }'></textarea>
                        <button class="btn-action" onclick="callSelectedTool()">Execute Tool</button>
                    </div>
                </div>
                <div class="form-group" style="margin-top: 1rem;">
                    <label style="font-weight: 600; color: var(--text-secondary);">Execution Result</label>
                    <pre id="tool-result">Ready.</pre>
                </div>
            </div>
        </div>

        <!-- LOGS TAB -->
        <div id="tab-logs" class="tab-pane">
            <div class="card">
                <div class="card-header">
                    <span>Real-Time Engine Log Stream</span>
                    <button class="btn-action" onclick="document.getElementById('logs-box').innerHTML = ''">Clear</button>
                </div>
                <div id="logs-box" class="log-container"></div>
            </div>
        </div>
    </main>

    <script>
        function switchTab(tabId) {
            document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            event.target.classList.add('active');
        }

        async function fetchTelemetry() {
            try {
                const res = await fetch('/api/telemetry');
                if (res.ok) {
                    const data = await res.json();
                    document.getElementById('cpu-pct').innerText = `${data.cpu.global_cpu_usage.toFixed(1)}%`;
                    document.getElementById('cpu-bar').style.width = `${Math.min(100, data.cpu.global_cpu_usage)}%`;
                    document.getElementById('cpu-cores').innerText = `Logical Cores: ${data.cpu.logical_core_count}`;

                    const usedGb = (data.memory.used_ram_bytes / 1073741824).toFixed(1);
                    const totalGb = (data.memory.total_ram_bytes / 1073741824).toFixed(1);
                    const availGb = (data.memory.available_ram_bytes / 1073741824).toFixed(1);
                    document.getElementById('ram-summary').innerText = `${usedGb} / ${totalGb} GB`;
                    document.getElementById('ram-avail').innerText = `Available: ${availGb} GB`;
                    document.getElementById('ram-bar').style.width = `${(data.memory.used_ram_bytes / data.memory.total_ram_bytes * 100).toFixed(1)}%`;

                    if (data.gpu.gpus && data.gpu.gpus.length > 0) {
                        const g = data.gpu.gpus[0];
                        document.getElementById('gpu-name').innerText = g.name;
                        const vUsed = (g.vram_used_bytes / 1073741824).toFixed(1);
                        const vTot = (g.vram_total_bytes / 1073741824).toFixed(1);
                        document.getElementById('vram-summary').innerText = `VRAM: ${vUsed} / ${vTot} GB`;
                        document.getElementById('vram-bar').style.width = `${(g.vram_used_bytes / g.vram_total_bytes * 100).toFixed(1)}%`;
                    } else {
                        document.getElementById('gpu-name').innerText = "CPU Mode";
                    }

                    document.getElementById('telemetry-json').innerText = JSON.stringify(data, null, 2);
                }
            } catch (e) {
                console.error("Telemetry fetch error:", e);
            }
        }

        async function fetchTasks() {
            try {
                const res = await fetch('/api/tasks');
                if (res.ok) {
                    const tasks = await res.json();
                    const tbody = document.getElementById('task-table-body');
                    if (tasks.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-secondary);">No tasks currently active</td></tr>';
                        return;
                    }
                    tbody.innerHTML = tasks.map(t => `
                        <tr>
                            <td><code>${t.id}</code></td>
                            <td><strong>${t.name}</strong></td>
                            <td><span class="badge">${t.priority}</span></td>
                            <td>${t.state}</td>
                            <td>${t.assigned_worker !== null ? '#' + t.assigned_worker : '-'}</td>
                            <td><button class="btn-action btn-danger" onclick="cancelTask('${t.id}')">Cancel</button></td>
                        </tr>
                    `).join('');
                }
            } catch (e) {
                console.error("Task fetch error:", e);
            }
        }

        async function cancelTask(id) {
            await fetch(`/api/tasks/${id}/cancel`, { method: 'POST' });
            fetchTasks();
        }

        async function dispatchQuickTask() {
            const name = document.getElementById('quick-cmd').value.trim();
            const priority = document.getElementById('quick-priority').value;
            if (!name) return;

            const res = await fetch('/api/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: name, payload: {}, priority: priority })
            });

            if (res.ok) {
                document.getElementById('quick-cmd').value = '';
                fetchTasks();
            }
        }

        async function fetchTools() {
            try {
                const res = await fetch('/api/tools');
                if (res.ok) {
                    const tools = await res.json();
                    const sel = document.getElementById('tool-select');
                    sel.innerHTML = tools.map(t => `<option value="${t.name}">${t.name}</option>`).join('');
                    if (tools.length > 0) inspectSelectedTool();
                }
            } catch (e) {
                console.error("Tools fetch error:", e);
            }
        }

        async function callSelectedTool() {
            const tool = document.getElementById('tool-select').value;
            const argsText = document.getElementById('tool-args').value;
            let args = {};
            try {
                if (argsText.trim()) args = JSON.parse(argsText);
            } catch (e) {
                alert("Invalid JSON arguments");
                return;
            }

            const out = document.getElementById('tool-result');
            out.innerText = "Executing...";

            const res = await fetch('/api/tools/call', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: tool, arguments: args })
            });

            const result = await res.json();
            out.innerText = JSON.stringify(result, null, 2);
        }

        // Live SSE Log Stream
        function initSse() {
            const es = new EventSource('/api/events');
            es.onmessage = (e) => {
                const data = JSON.parse(e.data);
                const box = document.getElementById('logs-box');
                const line = document.createElement('div');
                line.className = 'log-line';
                line.innerHTML = `<span class="log-time">[${new Date().toLocaleTimeString()}]</span> <span class="log-level-INFO">[EVENT]</span> <span>${JSON.stringify(data)}</span>`;
                box.appendChild(line);
                box.scrollTop = box.scrollHeight;
            };
        }

        // Initialization
        setInterval(fetchTelemetry, 2000);
        setInterval(fetchTasks, 2000);
        fetchTelemetry();
        fetchTasks();
        fetchTools();
        initSse();
    </script>
</body>
</html>
"#;
