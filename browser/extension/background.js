// HugOS Browser Extension Background Service Worker
// Manages Side Panel, CDP connection bridging, and ModelFusion IPC

const MODELFUSION_IPC_ENDPOINT = 'http://127.0.0.1:5000';
const OLLAMA_ENDPOINT = 'http://127.0.0.1:11434';

// Open side panel on action button click
chrome.runtime.onInstalled.addListener(() => {
  if (chrome.sidePanel && chrome.sidePanel.setPanelBehavior) {
    chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});
  }
});

chrome.action.onClicked.addListener(async (tab) => {
  if (tab.id && chrome.sidePanel) {
    await chrome.sidePanel.open({ tabId: tab.id });
  }
});

// IPC Message Router
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'CHECK_MODELFUSION_STATUS') {
    checkModelFusionStatus().then(sendResponse);
    return true;
  }

  if (message.type === 'EXECUTE_CLI_COMMAND') {
    executeCliCommand(message.command).then(sendResponse);
    return true;
  }

  if (message.type === 'FORWARD_TO_ACTIVE_TAB') {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0] && tabs[0].id) {
        chrome.tabs.sendMessage(tabs[0].id, message.payload, sendResponse);
      } else {
        sendResponse({ error: 'No active tab found' });
      }
    });
    return true;
  }
});

async function checkModelFusionStatus() {
  try {
    const res = await fetch(`${OLLAMA_ENDPOINT}/api/tags`, { method: 'GET' });
    if (res.ok) {
      const data = await res.json();
      return { online: true, models: (data.models || []).map(m => m.name) };
    }
  } catch (e) {
    // Fallback probe
  }
  return { online: false, models: [] };
}

async function executeCliCommand(command) {
  try {
    const res = await fetch(`${MODELFUSION_IPC_ENDPOINT}/api/cli`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command })
    });
    if (res.ok) {
      return await res.json();
    }
    return { error: `Server returned ${res.status}` };
  } catch (e) {
    return { error: `ModelFusion IPC offline: ${e.message}` };
  }
}
