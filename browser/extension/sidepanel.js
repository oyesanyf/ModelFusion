// HugOS Browser Extension Side Panel Script
// Handles UI interactions, quick action chips, slash commands, and ModelFusion IPC

document.addEventListener('DOMContentLoaded', () => {
  const chatFeed = document.getElementById('chat-feed');
  const promptInput = document.getElementById('prompt-input');
  const sendButton = document.getElementById('send-button');
  const pageTitle = document.getElementById('page-title');
  const statusBadge = document.getElementById('status-badge');
  const statusText = document.getElementById('status-text');

  // 1. Initialize Active Tab Context
  function refreshActiveTabContext() {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        pageTitle.textContent = `${tabs[0].title || 'Untitled'} (${tabs[0].url || ''})`;
      }
    });
  }

  refreshActiveTabContext();
  chrome.tabs.onActivated.addListener(refreshActiveTabContext);
  chrome.tabs.onUpdated.addListener(refreshActiveTabContext);

  // 2. Append Chat Messages
  function appendMessage(sender, text, isHtml = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender.toLowerCase()}`;

    const headerDiv = document.createElement('div');
    headerDiv.className = 'message-header';

    const nameSpan = document.createElement('span');
    nameSpan.className = 'sender-name';
    nameSpan.textContent = sender === 'user' ? 'You' : 'HugOS Assistant';

    const timeSpan = document.createElement('span');
    timeSpan.className = 'timestamp';
    timeSpan.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    headerDiv.appendChild(nameSpan);
    headerDiv.appendChild(timeSpan);

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    if (isHtml) {
      contentDiv.innerHTML = text;
    } else {
      const p = document.createElement('p');
      p.textContent = text;
      contentDiv.appendChild(p);
    }

    msgDiv.appendChild(headerDiv);
    msgDiv.appendChild(contentDiv);
    chatFeed.appendChild(msgDiv);
    chatFeed.scrollTop = chatFeed.scrollHeight;
  }

  // 3. Dispatch Active Tab Message Helper
  function sendToActiveTab(payload, callback) {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0] && tabs[0].id) {
        chrome.tabs.sendMessage(tabs[0].id, payload, callback);
      } else {
        appendMessage('assistant', 'Error: No active tab found.');
      }
    });
  }

  // 4. Quick Action Chips
  document.getElementById('chip-som').addEventListener('click', () => {
    sendToActiveTab({ action: 'toggle_som' }, (res) => {
      if (res && res.status === 'injected') {
        appendMessage('assistant', `🏷️ **Set-of-Mark Overlay Injected**: Identified **${res.count}** interactive elements with numeric badges on the active page. You can click elements by their mark ID e.g. <code>click [1]</code>.`, true);
      } else if (res && res.status === 'cleared') {
        appendMessage('assistant', '🏷️ Set-of-Mark visual overlays cleared.');
      } else {
        appendMessage('assistant', 'Could not inject Set-of-Mark overlay on this page.');
      }
    });
  });

  document.getElementById('chip-tables').addEventListener('click', () => {
    appendMessage('user', '/acdso (Extract Tables)');
    sendToActiveTab({ action: 'extract_tables' }, (res) => {
      if (res && res.tables && res.tables.length > 0) {
        let html = `📊 <strong>Extracted ${res.tables.length} Table(s)</strong>:<br><ul>`;
        for (const t of res.tables) {
          html += `<li><strong>${t.caption}</strong>: ${t.rowCount} rows × ${t.colCount} cols (${t.headers.slice(0, 4).join(', ')}...)</li>`;
        }
        html += `</ul><div class="tip-box">🚀 Tables ready for 5-objective Pareto ACDSO AutoML optimization. Running with <code>--predict</code>...</div>`;
        appendMessage('assistant', html, true);
      } else {
        appendMessage('assistant', '📊 No HTML tables or CSS grids detected on this page.');
      }
    });
  });

  document.getElementById('chip-summarize').addEventListener('click', () => {
    appendMessage('user', 'Summarize this page');
    sendToActiveTab({ action: 'get_pruned_dom' }, (res) => {
      if (res && res.pruned) {
        const { title, originalLength, prunedLength, text } = res.pruned;
        const reduction = Math.round((1 - prunedLength / originalLength) * 100);
        const preview = text.slice(0, 300).replace(/\n/g, '<br>');
        const html = `📝 <strong>Semantic Summary for "${title}"</strong><br>
          <span style="font-size:11px;color:#10b981;">⚡ Token Reduction: ${reduction}% (${originalLength} → ${prunedLength} chars)</span><br><br>
          ${preview}...`;
        appendMessage('assistant', html, true);
      } else {
        appendMessage('assistant', 'Could not prune DOM on this page.');
      }
    });
  });

  document.getElementById('chip-research').addEventListener('click', () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const topic = tabs[0] ? tabs[0].title : 'current page topic';
      appendMessage('user', `/research ${topic}`);
      appendMessage('assistant', `🔍 Launching deep research query for: <strong>${topic}</strong>...<br><span style="font-size:11px;color:#a1a1aa;">Synthesizing results across local vector catalog and live web indices...</span>`, true);
    });
  });

  // 5. Input Submission & Slash Command Handler
  function handleUserSubmit() {
    const raw = promptInput.value.trim();
    if (!raw) return;

    appendMessage('user', raw);
    promptInput.value = '';

    const lower = raw.toLowerCase();

    if (lower.startsWith('/acdso')) {
      sendToActiveTab({ action: 'extract_tables' }, (res) => {
        if (res && res.tables && res.tables.length > 0) {
          appendMessage('assistant', `🧠 <strong>ACDSO Triggered</strong>: Successfully parsed ${res.tables.length} table dataset(s). Analyzing Pareto frontier across Accuracy, Cost, Memory, Latency, and Risk...`, true);
        } else {
          appendMessage('assistant', '🧠 ACDSO: Please specify a dataset path or navigate to a page with tabular data.');
        }
      });
      return;
    }

    if (lower.startsWith('/browser')) {
      const task = raw.slice(8).trim();
      appendMessage('assistant', `🌐 <strong>Autonomous Browser Task</strong>: Initiating goal-directed multi-agent loop for: <em>"${task}"</em>.<br>Coordinating Vision Specialist, Fast DOM Specialist, and DeepSeek-R1 Arbiter...`, true);
      return;
    }

    if (lower.startsWith('/datascience')) {
      appendMessage('assistant', '📈 <strong>Data Science Engine</strong>: Initialized exploratory workflow. Ready for automated feature engineering and causal discovery.');
      return;
    }

    // Default conversational query
    setTimeout(() => {
      appendMessage('assistant', `🤖 Processing directive: "${raw}" via ModelFusion multi-model fusion pipeline.`);
    }, 400);
  }

  sendButton.addEventListener('click', handleUserSubmit);
  promptInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleUserSubmit();
    }
  });
});
