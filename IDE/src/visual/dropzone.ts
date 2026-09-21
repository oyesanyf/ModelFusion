/**
 * Native Multi-Modal Visual Canvas: Webview Dropzone & Clipboard Handler
 * 
 * Features:
 * - Drag-and-drop & clipboard paste (Win+Shift+S / PrtScn) listener
 * - Validates .png, .jpg, .jpeg, .webp, .svg formats
 * - Converts image buffers to Base64 data URLs via FileReader
 * - Thumbnail chips with remove/reorder actions
 * - Emits IPC message: { type: 'attachVisualAsset', asset: { id, filename, mimeType, base64Data, width, height } }
 * - Embedded CSS & client-side webview script generators for VSCode Webview panels
 */

export interface VisualAsset {
  id: string;
  filename: string;
  mimeType: string;
  base64Data: string; // Pure Base64 payload
  dataUrl?: string;   // data:image/png;base64,...
  width?: number;
  height?: number;
  sizeBytes: number;
  timestamp: number;
}

export interface DropzoneConfig {
  maxFileSizeMb?: number;
  maxAssets?: number;
  allowedMimeTypes?: string[];
  allowedExtensions?: string[];
}

export type VisualCanvasIpcMessage =
  | { type: 'attachVisualAsset'; asset: VisualAsset }
  | { type: 'removeVisualAsset'; assetId: string }
  | { type: 'reorderVisualAssets'; assetIds: string[] }
  | { type: 'requestSynthesis'; workflow: 'ui-synthesis' | 'layout-diagnosis'; assetId?: string; prompt?: string }
  | { type: 'visualSynthesisResult'; status: 'success' | 'error'; workflow: string; output: string; patch?: string }
  | { type: 'applyVisualPatch'; patch: string; targetFile?: string };

export const DEFAULT_ALLOWED_MIME_TYPES = [
  'image/png',
  'image/jpeg',
  'image/jpg',
  'image/webp',
  'image/svg+xml'
];

export const DEFAULT_ALLOWED_EXTENSIONS = [
  '.png',
  '.jpg',
  '.jpeg',
  '.webp',
  '.svg'
];

/**
 * Validates whether a file matches allowed multi-modal visual asset types.
 */
export function isAllowedVisualFile(filename: string, mimeType: string, config?: DropzoneConfig): boolean {
  const allowedMimes = config?.allowedMimeTypes || DEFAULT_ALLOWED_MIME_TYPES;
  const allowedExts = config?.allowedExtensions || DEFAULT_ALLOWED_EXTENSIONS;

  const lowerMime = (mimeType || '').toLowerCase();
  const lowerName = (filename || '').toLowerCase();

  const mimeMatch = allowedMimes.some(m => lowerMime.includes(m.toLowerCase()) || lowerMime === m.toLowerCase());
  const extMatch = allowedExts.some(ext => lowerName.endsWith(ext.toLowerCase()));

  return mimeMatch || extMatch;
}

/**
 * Converts a browser File object to a VisualAsset structure using FileReader.
 */
export async function fileToVisualAsset(file: File, idPrefix: string = 'vis'): Promise<VisualAsset> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error(`Failed to read file: ${file.name}`));
    reader.onload = () => {
      const dataUrl = reader.result as string;
      const commaIdx = dataUrl.indexOf(',');
      const base64Data = commaIdx >= 0 ? dataUrl.slice(commaIdx + 1) : dataUrl;

      // Extract image dimensions if DOM Image is available
      if (typeof Image !== 'undefined' && file.type.startsWith('image/')) {
        const img = new Image();
        img.onload = () => {
          resolve({
            id: `${idPrefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
            filename: file.name || `screenshot_${new Date().toISOString().replace(/[:.]/g, '-')}.png`,
            mimeType: file.type || 'image/png',
            base64Data,
            dataUrl,
            width: img.naturalWidth || img.width,
            height: img.naturalHeight || img.height,
            sizeBytes: file.size,
            timestamp: Date.now()
          });
        };
        img.onerror = () => {
          // Fallback if dimensions cannot be probed
          resolve({
            id: `${idPrefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
            filename: file.name || 'image.png',
            mimeType: file.type || 'image/png',
            base64Data,
            dataUrl,
            sizeBytes: file.size,
            timestamp: Date.now()
          });
        };
        img.src = dataUrl;
      } else {
        resolve({
          id: `${idPrefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          filename: file.name || 'image.png',
          mimeType: file.type || 'image/png',
          base64Data,
          dataUrl,
          sizeBytes: file.size,
          timestamp: Date.now()
        });
      }
    };
    reader.readAsDataURL(file);
  });
}

/**
 * Extracts image assets from a clipboard DataTransfer object (e.g. from Win+Shift+S paste).
 */
export async function extractClipboardImages(clipboardData: DataTransfer | null): Promise<VisualAsset[]> {
  if (!clipboardData) return [];
  const assets: VisualAsset[] = [];
  const items = clipboardData.items;

  if (items) {
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.type.startsWith('image/')) {
        const file = item.getAsFile();
        if (file) {
          const asset = await fileToVisualAsset(file, 'clipboard');
          assets.push(asset);
        }
      }
    }
  } else if (clipboardData.files && clipboardData.files.length > 0) {
    for (let i = 0; i < clipboardData.files.length; i++) {
      const file = clipboardData.files[i];
      if (file.type.startsWith('image/')) {
        const asset = await fileToVisualAsset(file, 'clipboard');
        assets.push(asset);
      }
    }
  }

  return assets;
}

/**
 * Generates the HTML template for the Visual Dropzone and Thumbnail Chips Strip.
 */
export function getDropzoneHtml(containerId: string = 'visual-canvas-container'): string {
  return `
<div id="${containerId}" class="visual-canvas-wrapper" role="region" aria-label="Visual Canvas Dropzone">
  <div id="visual-dropzone" class="visual-dropzone" tabindex="0" title="Drag & drop wireframes, screenshots, or paste from clipboard (Win+Shift+S)">
    <div class="visual-dropzone-icon">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
        <circle cx="8.5" cy="8.5" r="1.5"/>
        <polyline points="21 15 16 10 5 21"/>
      </svg>
    </div>
    <div class="visual-dropzone-label">
      <span class="visual-dropzone-prompt">Drop UI wireframe, layout screenshot, or <strong>paste clipboard</strong></span>
      <span class="visual-dropzone-subtext">Supports PNG, JPG, WebP, SVG &middot; Auto-routes to Qwen2-VL</span>
    </div>
    <input type="file" id="visual-file-input" class="visual-file-input" accept="image/png,image/jpeg,image/webp,image/svg+xml" multiple aria-hidden="true" />
  </div>

  <div id="visual-chips-container" class="visual-chips-container" style="display: none;">
    <div class="visual-chips-header">
      <span class="visual-chips-title">Attached Visual Assets (<span id="visual-chips-count">0</span>)</span>
      <button type="button" id="visual-chips-clear" class="visual-btn-secondary" title="Clear all attachments">Clear All</button>
    </div>
    <div id="visual-chips-list" class="visual-chips-list"></div>
  </div>

  <!-- Visual Workflow Quick Actions Bar -->
  <div id="visual-actions-bar" class="visual-actions-bar" style="display: none;">
    <button type="button" id="btn-synthesize-ui" class="visual-action-btn primary" title="Generate Tailwind + React JSX component from wireframe">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
      Synthesize UI Component
    </button>
    <button type="button" id="btn-diagnose-layout" class="visual-action-btn secondary" title="Diagnose CSS box model / flexbox misalignment">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
      Diagnose Layout Bug
    </button>
  </div>
</div>
`.trim();
}

/**
 * Generates theme-compatible CSS for the Visual Dropzone and interactive thumbnail chips.
 */
export function getDropzoneCss(): string {
  return `
/* Multi-Modal Visual Canvas Dropzone Styles */
.visual-canvas-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 8px 0;
  font-family: var(--vscode-font-family, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
}

.visual-dropzone {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border: 1.5px dashed var(--vscode-focusBorder, #007acc);
  border-radius: 6px;
  background: var(--vscode-editor-background, #1e1e1e);
  color: var(--vscode-foreground, #cccccc);
  cursor: pointer;
  transition: all 0.18s ease-in-out;
  user-select: none;
}

.visual-dropzone:hover,
.visual-dropzone:focus,
.visual-dropzone.drag-active {
  border-color: var(--vscode-button-background, #0e639c);
  background: var(--vscode-list-hoverBackground, #2a2d2e);
  box-shadow: 0 0 8px rgba(14, 99, 156, 0.25);
  outline: none;
}

.visual-dropzone.drag-active {
  border-style: solid;
  transform: scale(1.005);
}

.visual-dropzone-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--vscode-textLink-foreground, #3794ff);
  flex-shrink: 0;
}

.visual-dropzone-label {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.visual-dropzone-prompt {
  font-size: 12px;
  font-weight: 500;
  color: var(--vscode-foreground, #cccccc);
}

.visual-dropzone-prompt strong {
  color: var(--vscode-textLink-foreground, #3794ff);
}

.visual-dropzone-subtext {
  font-size: 10.5px;
  color: var(--vscode-descriptionForeground, #888888);
}

.visual-file-input {
  display: none;
}

/* Attached Visual Chips Strip */
.visual-chips-container {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px;
  background: var(--vscode-sideBar-background, #252526);
  border: 1px solid var(--vscode-widget-border, #333333);
  border-radius: 6px;
}

.visual-chips-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: var(--vscode-descriptionForeground, #888888);
}

.visual-chips-title {
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.visual-btn-secondary {
  background: transparent;
  border: none;
  color: var(--vscode-textLink-foreground, #3794ff);
  font-size: 11px;
  cursor: pointer;
  padding: 2px 4px;
}

.visual-btn-secondary:hover {
  text-decoration: underline;
}

.visual-chips-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-height: 180px;
  overflow-y: auto;
}

.visual-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  background: var(--vscode-editorWidget-background, #202020);
  border: 1px solid var(--vscode-widget-border, #3c3c3c);
  border-radius: 4px;
  position: relative;
  max-width: 220px;
  animation: visualChipFadeIn 0.2s ease-out;
}

@keyframes visualChipFadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.visual-chip-thumb {
  width: 32px;
  height: 32px;
  object-fit: cover;
  border-radius: 3px;
  border: 1px solid var(--vscode-widget-border, #444);
  background: #111;
  flex-shrink: 0;
}

.visual-chip-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.visual-chip-name {
  font-size: 11px;
  font-weight: 500;
  color: var(--vscode-foreground, #ddd);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.visual-chip-meta {
  font-size: 9.5px;
  color: var(--vscode-descriptionForeground, #777);
}

.visual-chip-remove {
  background: transparent;
  border: none;
  color: var(--vscode-descriptionForeground, #888);
  cursor: pointer;
  padding: 2px 4px;
  font-size: 13px;
  line-height: 1;
  border-radius: 3px;
}

.visual-chip-remove:hover {
  color: var(--vscode-errorForeground, #f48771);
  background: rgba(244, 135, 113, 0.15);
}

/* Quick Actions Bar */
.visual-actions-bar {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.visual-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  font-size: 11.5px;
  font-weight: 500;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s ease;
}

.visual-action-btn.primary {
  background: var(--vscode-button-background, #0e639c);
  color: var(--vscode-button-foreground, #ffffff);
}

.visual-action-btn.primary:hover {
  background: var(--vscode-button-hoverBackground, #1177bb);
}

.visual-action-btn.secondary {
  background: var(--vscode-button-secondaryBackground, #3a3d41);
  color: var(--vscode-button-secondaryForeground, #ffffff);
}

.visual-action-btn.secondary:hover {
  background: var(--vscode-button-secondaryHoverBackground, #45494e);
}
`.trim();
}

/**
 * Returns the client-side JavaScript initializing the visual dropzone and clipboard listeners inside a Webview.
 */
export function getDropzoneScript(config?: DropzoneConfig): string {
  const maxMb = config?.maxFileSizeMb || 20;
  const maxAssets = config?.maxAssets || 10;

  return `
(function() {
  const vscode = (typeof acquireVsCodeApi === 'function') ? acquireVsCodeApi() : null;
  const dropzone = document.getElementById('visual-dropzone');
  const fileInput = document.getElementById('visual-file-input');
  const chipsContainer = document.getElementById('visual-chips-container');
  const chipsList = document.getElementById('visual-chips-list');
  const chipsCount = document.getElementById('visual-chips-count');
  const clearBtn = document.getElementById('visual-chips-clear');
  const actionsBar = document.getElementById('visual-actions-bar');
  const btnSynthesize = document.getElementById('btn-synthesize-ui');
  const btnDiagnose = document.getElementById('btn-diagnose-layout');

  const MAX_FILE_SIZE = ${maxMb} * 1024 * 1024;
  const MAX_ASSETS = ${maxAssets};
  let attachedAssets = [];

  if (!dropzone) return;

  // Open file picker on click
  dropzone.addEventListener('click', () => {
    if (fileInput) fileInput.click();
  });

  // Keyboard accessibility
  dropzone.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      if (fileInput) fileInput.click();
    }
  });

  // Handle Drag & Drop
  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('drag-active');
    }, false);
  });

  ['dragleave', 'dragend'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('drag-active');
    }, false);
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.remove('drag-active');

    const dt = e.dataTransfer;
    if (dt && dt.files && dt.files.length > 0) {
      processFiles(Array.from(dt.files));
    }
  });

  // Handle Clipboard Paste (Win+Shift+S, Snipping Tool, PrtScn)
  window.addEventListener('paste', (e) => {
    const clipboardData = e.clipboardData;
    if (!clipboardData) return;

    const items = clipboardData.items;
    const files = [];
    if (items) {
      for (let i = 0; i < items.length; i++) {
        if (items[i].type.startsWith('image/')) {
          const file = items[i].getAsFile();
          if (file) files.push(file);
        }
      }
    }
    if (files.length > 0) {
      e.preventDefault();
      processFiles(files);
    }
  });

  // Handle File Input Change
  if (fileInput) {
    fileInput.addEventListener('change', (e) => {
      if (fileInput.files && fileInput.files.length > 0) {
        processFiles(Array.from(fileInput.files));
        fileInput.value = '';
      }
    });
  }

  // Clear button
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      attachedAssets = [];
      renderChips();
      if (vscode) {
        vscode.postMessage({ type: 'clearVisualAssets' });
      }
    });
  }

  // Synthesis action buttons
  if (btnSynthesize) {
    btnSynthesize.addEventListener('click', () => {
      if (attachedAssets.length === 0) return;
      if (vscode) {
        vscode.postMessage({
          type: 'requestSynthesis',
          workflow: 'ui-synthesis',
          assetId: attachedAssets[0].id
        });
      }
    });
  }

  if (btnDiagnose) {
    btnDiagnose.addEventListener('click', () => {
      if (attachedAssets.length === 0) return;
      if (vscode) {
        vscode.postMessage({
          type: 'requestSynthesis',
          workflow: 'layout-diagnosis',
          assetId: attachedAssets[0].id
        });
      }
    });
  }

  function processFiles(files) {
    const validFiles = files.filter(f => {
      const isImg = f.type.startsWith('image/') || /\\.(png|jpg|jpeg|webp|svg)$/i.test(f.name);
      if (!isImg) return false;
      if (f.size > MAX_FILE_SIZE) {
        console.warn('File exceeds limit: ' + f.name);
        return false;
      }
      return true;
    });

    if (attachedAssets.length + validFiles.length > MAX_ASSETS) {
      console.warn('Max assets limit reached');
      validFiles.splice(MAX_ASSETS - attachedAssets.length);
    }

    validFiles.forEach(file => {
      const reader = new FileReader();
      reader.onload = () => {
        const dataUrl = reader.result;
        const base64Data = (typeof dataUrl === 'string' && dataUrl.indexOf(',') >= 0)
          ? dataUrl.split(',')[1]
          : dataUrl;

        const asset = {
          id: 'vis-' + Date.now() + '-' + Math.random().toString(36).slice(2, 6),
          filename: file.name || 'clipboard_screenshot.png',
          mimeType: file.type || 'image/png',
          base64Data: base64Data,
          dataUrl: dataUrl,
          sizeBytes: file.size,
          timestamp: Date.now()
        };

        // Probe dimensions
        const img = new Image();
        img.onload = () => {
          asset.width = img.naturalWidth;
          asset.height = img.naturalHeight;
          addAsset(asset);
        };
        img.onerror = () => {
          addAsset(asset);
        };
        img.src = dataUrl;
      };
      reader.readAsDataURL(file);
    });
  }

  function addAsset(asset) {
    attachedAssets.push(asset);
    renderChips();

    // Dispatch IPC to VS Code Extension Host
    if (vscode) {
      vscode.postMessage({
        type: 'attachVisualAsset',
        asset: {
          id: asset.id,
          filename: asset.filename,
          mimeType: asset.mimeType,
          base64Data: asset.base64Data,
          width: asset.width,
          height: asset.height
        }
      });
    }
  }

  function removeAsset(id) {
    attachedAssets = attachedAssets.filter(a => a.id !== id);
    renderChips();
    if (vscode) {
      vscode.postMessage({
        type: 'removeVisualAsset',
        assetId: id
      });
    }
  }

  function renderChips() {
    if (!chipsContainer || !chipsList) return;

    chipsList.innerHTML = '';
    const count = attachedAssets.length;

    if (count === 0) {
      chipsContainer.style.display = 'none';
      if (actionsBar) actionsBar.style.display = 'none';
      return;
    }

    chipsContainer.style.display = 'flex';
    if (actionsBar) actionsBar.style.display = 'flex';
    if (chipsCount) chipsCount.textContent = count.toString();

    attachedAssets.forEach(asset => {
      const chip = document.createElement('div');
      chip.className = 'visual-chip';
      chip.dataset.id = asset.id;

      const thumb = document.createElement('img');
      thumb.className = 'visual-chip-thumb';
      thumb.src = asset.dataUrl || ('data:' + asset.mimeType + ';base64,' + asset.base64Data);
      thumb.alt = asset.filename;

      const info = document.createElement('div');
      info.className = 'visual-chip-info';

      const name = document.createElement('span');
      name.className = 'visual-chip-name';
      name.textContent = asset.filename;
      name.title = asset.filename;

      const meta = document.createElement('span');
      meta.className = 'visual-chip-meta';
      const dimStr = (asset.width && asset.height) ? (asset.width + 'x' + asset.height + ' &middot; ') : '';
      const kbStr = Math.round(asset.sizeBytes / 1024) + ' KB';
      meta.innerHTML = dimStr + kbStr;

      info.appendChild(name);
      info.appendChild(meta);

      const removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.className = 'visual-chip-remove';
      removeBtn.title = 'Remove visual asset';
      removeBtn.innerHTML = '&times;';
      removeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        removeAsset(asset.id);
      });

      chip.appendChild(thumb);
      chip.appendChild(info);
      chip.appendChild(removeBtn);
      chipsList.appendChild(chip);
    });
  }
})();
`.trim();
}
