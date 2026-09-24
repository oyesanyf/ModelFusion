#!/usr/bin/env python3
"""
Update ModelFusion_Interactive_Docs.html so its interactive search table includes all 161 flags.
"""

import json
import os
import re
import sys

def update_interactive_docs():
    target_path = r"C:/Users/oyesanyf/.gemini/antigravity/brain/b6ef927a-8ffc-4ecd-b7ed-90b470e8fc34/ModelFusion_Interactive_Docs.html"
    
    if not os.path.exists(target_path):
        raise FileNotFoundError(f"Target HTML not found at: {target_path}")

    with open(target_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # Load 161 flags from scripts/all_parsed_flags.json
    with open('scripts/all_parsed_flags.json', 'r', encoding='utf-8') as f:
        all_flags = json.load(f)

    sys.path.insert(0, '.')
    from scripts.generate_docs import APPENDIX_FLAGS, FLAG_DETAILS
    excluded = set(APPENDIX_FLAGS.keys())
    agent_directives = {'btw', 'goal', 'schedule', 'browser', 'grill-me', 'teamwork-preview', 'learn', 'boost', 'generative-ui', 'no-fusion'}
    primary_161 = [f for f in all_flags if f['long_name'] not in excluded and f['long_name'] not in agent_directives]

    assert len(primary_161) == 161, f"Expected 161 flags, got {len(primary_161)}"

    # Category mapping for interactive UI
    cat_ui_map = {
        "Global Execution & Resource Flags": "global",
        "Machine Learning Model Selection": "ml",
        "SINQ Quantization Engine": "ml",
        "Innovation & Cognitive Systems": "innov",
        "HyDE Search & Web Retrieval": "hyde",
        "System & Orchestration Commands": "sys",
        "Data Science & Tabular Workflows": "data",
        "Response Evaluation & Planning": "data",
        "Binary & PE Executable Analysis": "data",
        "Multi-Modal Task Routing Flags": "tasks",
        "Server & Database Commands": "server"
    }

    commands_js = []
    for idx, f in enumerate(primary_161, 1):
        long_name = f['long_name']
        detail = FLAG_DETAILS.get(long_name, {})
        desc = detail.get('desc', f['help_text'] or f"Executes {long_name} capability.")
        syntax = detail.get('example', f"cli.exe --{long_name}")
        t_clean = f['field_type'].replace('Option<', '').replace('>', '')
        def_val = str(f['default_val']) if f['default_val'] is not None else ("false" if f['field_type'] == 'bool' else "None")
        ui_cat = cat_ui_map.get(f['clean_category'], "sys")

        alias_str = ""
        if f['aliases']:
            alias_str = " (aliases: " + ", ".join(f['aliases']) + ")"

        commands_js.append({
            "idx": idx,
            "name": f['flag'] + alias_str,
            "flag": f['flag'],
            "category": ui_cat,
            "category_name": f['clean_category'],
            "type": t_clean,
            "default": def_val,
            "desc": desc,
            "syntax": syntax
        })

    # Prepare replacement markup for the Interactive Command Explorer section
    new_section_markup = """  <!-- Interactive Command Explorer (All 161 Master CLI Flags) -->
  <section class="glass-card rounded-3xl p-8 mb-8 shadow-2xl">
    <div class="flex flex-col md:flex-row items-start md:items-center justify-between pb-6 mb-6 border-b border-[var(--border)] gap-4">
      <div>
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-500 text-xs font-bold uppercase tracking-wider mb-2">
          <span>Authoritative CLI Master Table</span>
        </div>
        <h2 class="text-2xl font-black tracking-tight text-[var(--foreground)]">Interactive Command & Flag Explorer (All 161 Flags)</h2>
        <p class="text-sm text-[var(--muted-foreground)]">Instant search across all 161 production flags, multi-modal routing pipelines, and system execution directives.</p>
      </div>
      <div class="flex flex-col sm:flex-row items-start sm:items-center gap-3 w-full md:w-auto">
        <div class="relative w-full sm:w-72">
          <input type="text" id="flagSearch" oninput="filterFlags()" placeholder="Search 161 flags, tasks, syntax..." 
                 class="w-full px-4 py-2 text-xs rounded-xl glass-card border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] focus:outline-none focus:border-amber-500" />
        </div>
        <span id="flagCounter" class="text-xs font-mono text-amber-500 font-bold whitespace-nowrap">Showing 161 of 161</span>
      </div>
    </div>

    <!-- Filter Buttons -->
    <div class="flex flex-wrap gap-2 mb-6" id="filterButtons">
      <button onclick="setCategory('all')" id="btn-all" class="cat-btn px-3 py-1 rounded-xl text-xs font-semibold bg-amber-500 text-white">All Flags (161)</button>
      <button onclick="setCategory('global')" id="btn-global" class="cat-btn px-3 py-1 rounded-xl text-xs font-semibold glass-card text-[var(--muted-foreground)] hover:text-[var(--foreground)]">Global & Hardware (19)</button>
      <button onclick="setCategory('ml')" id="btn-ml" class="cat-btn px-3 py-1 rounded-xl text-xs font-semibold glass-card text-[var(--muted-foreground)] hover:text-[var(--foreground)]">ML & Quantization (12)</button>
      <button onclick="setCategory('innov')" id="btn-innov" class="cat-btn px-3 py-1 rounded-xl text-xs font-semibold glass-card text-[var(--muted-foreground)] hover:text-[var(--foreground)]">Innovation (6)</button>
      <button onclick="setCategory('hyde')" id="btn-hyde" class="cat-btn px-3 py-1 rounded-xl text-xs font-semibold glass-card text-[var(--muted-foreground)] hover:text-[var(--foreground)]">HyDE & Search (9)</button>
      <button onclick="setCategory('sys')" id="btn-sys" class="cat-btn px-3 py-1 rounded-xl text-xs font-semibold glass-card text-[var(--muted-foreground)] hover:text-[var(--foreground)]">System & Backends (41)</button>
      <button onclick="setCategory('data')" id="btn-data" class="cat-btn px-3 py-1 rounded-xl text-xs font-semibold glass-card text-[var(--muted-foreground)] hover:text-[var(--foreground)]">Data & Eval (7)</button>
      <button onclick="setCategory('tasks')" id="btn-tasks" class="cat-btn px-3 py-1 rounded-xl text-xs font-semibold glass-card text-[var(--muted-foreground)] hover:text-[var(--foreground)]">Multi-Modal Tasks (62)</button>
      <button onclick="setCategory('server')" id="btn-server" class="cat-btn px-3 py-1 rounded-xl text-xs font-semibold glass-card text-[var(--muted-foreground)] hover:text-[var(--foreground)]">Server & MCP (5)</button>
    </div>

    <!-- Flag Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-h-[750px] overflow-y-auto pr-1" id="cmdGrid">
      <!-- Generated via JS -->
    </div>
  </section>"""

    idx = html.find('Interactive Command Explorer')
    if idx == -1:
        idx = html.find('Interactive Command & Flag Explorer')
    if idx == -1:
        raise ValueError("Could not find Command Explorer in HTML")

    sec_start = html.rfind('<section', 0, idx)
    sec_end = html.find('</section>', idx) + len('</section>')

    html = html[:sec_start] + new_section_markup + html[sec_end:]

    # Now replace the JavaScript commands and rendering logic
    js_blob = json.dumps(commands_js, indent=4)
    new_js_logic = f"""
    // Master CLI Commands (All 161 Flags)
    const allFlags = {js_blob};

    let activeCategory = 'all';

    function renderFlags(list) {{
      const grid = document.getElementById('cmdGrid');
      const counter = document.getElementById('flagCounter');
      counter.textContent = `Showing ${{list.length}} of 161`;

      if (list.length === 0) {{
        grid.innerHTML = `<div class="col-span-full p-8 text-center text-sm text-[var(--muted-foreground)]">No matching flags found. Try searching for a different keyword or task.</div>`;
        return;
      }}

      grid.innerHTML = list.map(c => `
        <div class="p-4 rounded-2xl glass-card flex flex-col justify-between hover:border-amber-500/50 transition-all border border-[var(--border)] bg-[var(--card)]">
          <div>
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs font-mono font-bold text-amber-500">#${{c.idx}}</span>
              <span class="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 border border-amber-500/20">${{c.category_name}}</span>
            </div>
            <div class="font-mono text-sm font-bold text-[var(--foreground)] mb-1 break-all">${{c.name}}</div>
            <div class="flex items-center gap-2 mb-2 text-[11px] text-[var(--muted-foreground)]">
              <span>Type: <code class="text-[var(--foreground)]">${{c.type}}</code></span>
              <span>•</span>
              <span>Default: <code class="text-[var(--foreground)]">${{c.default}}</code></span>
            </div>
            <p class="text-xs text-[var(--muted-foreground)] mb-3 leading-relaxed">${{c.desc}}</p>
          </div>
          <div class="text-[11px] font-mono bg-[var(--background)] p-2 rounded-lg border border-[var(--border)] text-emerald-400 break-all select-all">
            ${{c.syntax}}
          </div>
        </div>
      `).join('');
    }}

    function setCategory(cat) {{
      activeCategory = cat;
      document.querySelectorAll('.cat-btn').forEach(b => {{
        b.className = 'cat-btn px-3 py-1 rounded-xl text-xs font-semibold glass-card text-[var(--muted-foreground)] hover:text-[var(--foreground)]';
      }});
      const activeBtn = document.getElementById(`btn-${{cat}}`);
      if (activeBtn) {{
        activeBtn.className = 'cat-btn px-3 py-1 rounded-xl text-xs font-semibold bg-amber-500 text-white';
      }}
      filterFlags();
    }}

    function filterFlags() {{
      const query = (document.getElementById('flagSearch').value || '').toLowerCase().trim();
      const filtered = allFlags.filter(c => {{
        const matchesCat = activeCategory === 'all' || c.category === activeCategory;
        const matchesQuery = !query || 
          c.name.toLowerCase().includes(query) ||
          c.flag.toLowerCase().includes(query) ||
          c.desc.toLowerCase().includes(query) ||
          c.syntax.toLowerCase().includes(query) ||
          c.category_name.toLowerCase().includes(query);
        return matchesCat && matchesQuery;
      }});
      renderFlags(filtered);
    }}

    // Initial render
    renderFlags(allFlags);
"""

    # Replace old script logic
    # Find `const commands =` to end of renderCommands call
    old_js_start = html.find('const commands =')
    if old_js_start == -1:
        # maybe already replaced
        old_js_start = html.find('const allFlags =')
    
    old_js_end = html.find('renderCommands(commands);')
    if old_js_end != -1:
        old_js_end += len('renderCommands(commands);')
    else:
        old_js_end = html.find('renderFlags(allFlags);')
        if old_js_end != -1:
            old_js_end += len('renderFlags(allFlags);')

    if old_js_start != -1 and old_js_end != -1:
        html = html[:old_js_start] + new_js_logic.strip() + html[old_js_end:]
    else:
        # Insert before </body>
        html = html.replace('</body>', f'<script>{new_js_logic}</script></body>')

    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Successfully updated {target_path} with all 161 CLI flags!")

if __name__ == '__main__':
    update_interactive_docs()
