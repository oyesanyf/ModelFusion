/**
 * Multi-Modal Visual Canvas Dashboard Tab Integration
 * 
 * Provides HTML, CSS, and client-side JavaScript for embedding the Native Multi-Modal
 * Visual Canvas into the HugOS Studio Webview dashboard.
 */

import { getDropzoneCss } from './dropzone';

export function getVisualTabNavHtml(): string {
  return `
		<button class="tab-btn" data-tab="visualTab" id="visualTabBtn">
			<span>🎨 Visual Canvas & UI</span>
			<span class="tab-counter" id="visualAssetsBadge">0</span>
		</button>
  `.trim();
}

export function getVisualTabPaneHtml(): string {
  return `
	<!-- TAB 4: Native Multi-Modal Visual Canvas & UI Synthesis -->
	<section class="tab-pane" id="visualTab" role="tabpanel" aria-label="Visual Canvas & UI Synthesis">
		<!-- Dropzone & Quick Capture Card -->
		<div class="card" style="margin-bottom: 12px;">
			<div class="card-header">
				<div class="card-title">🎨 Visual Input Canvas (Dropzone & Clipboard)</div>
				<div style="display: flex; gap: 6px;">
					<button class="btn btn-secondary" id="visualClearBtn" style="padding: 3px 8px; font-size: 11px;">Clear Assets</button>
				</div>
			</div>

			<!-- Dropzone Area -->
			<div id="visualDropzoneArea" class="visual-dropzone-box" tabindex="0">
				<div class="visual-dropzone-inner">
					<div class="visual-dropzone-icon">
						<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
							<rect x="3" y="3" width="18" height="18" rx="3" ry="3"/>
							<circle cx="8.5" cy="8.5" r="1.5"/>
							<polyline points="21 15 16 10 5 21"/>
						</svg>
					</div>
					<div class="visual-dropzone-text">
						<strong>Drag & drop UI wireframes, mockups, or screenshots here</strong>
						<span style="font-size: 11px; color: var(--text-dim);">Or capture with <code>Win+Shift+S</code> / <code>PrtScn</code> and <strong>Ctrl+V</strong> to paste</span>
						<span style="font-size: 10px; color: var(--text-dim); margin-top: 2px;">Supported: PNG, JPEG, WebP, SVG &middot; Automatic local VLM routing</span>
					</div>
				</div>
				<input type="file" id="visualFileInputHidden" accept="image/png,image/jpeg,image/webp,image/svg+xml" multiple style="display: none;" />
			</div>

			<!-- Attached Assets Strip -->
			<div id="visualChipsContainer" style="display: none; margin-top: 10px;">
				<div style="font-size: 11px; font-weight: 600; color: var(--text-muted); margin-bottom: 6px;">
					ATTACHED ASSETS (<span id="visualChipsCount">0</span>)
				</div>
				<div id="visualChipsList" class="visual-chips-list"></div>
			</div>

			<!-- Workflow Selector & Action Buttons -->
			<div class="visual-controls-bar" style="margin-top: 12px; display: flex; flex-wrap: wrap; gap: 10px; align-items: center; justify-content: space-between;">
				<div style="display: flex; gap: 8px; align-items: center;">
					<label class="input-label" style="margin: 0;">Inference Target:</label>
					<select class="styled-select" id="visualModelTargetSelect">
						<option value="auto">Auto-Select (OpenVINO / Ollama)</option>
						<option value="qwen2-vl">Qwen2-VL 7B (OpenVINO INT4)</option>
						<option value="ollama-vision">Ollama Local VLM</option>
					</select>
				</div>
				<div style="display: flex; gap: 8px;">
					<button class="btn btn-primary" id="btnSynthesizeUiAction" disabled>
						<span>✨ Synthesize React + Tailwind UI</span>
					</button>
					<button class="btn btn-secondary" id="btnDiagnoseLayoutAction" disabled>
						<span>🔍 Diagnose CSS Layout Bug</span>
					</button>
				</div>
			</div>
		</div>

		<!-- Real-Time Synthesis / Diagnosis Output Card -->
		<div class="card" id="visualResultCard" style="display: none;">
			<div class="card-header">
				<div class="card-title" id="visualResultTitle">✨ Synthesized Component Output</div>
				<div style="display: flex; gap: 6px; align-items: center;">
					<span id="visualLatencyBadge" class="status-badge" style="font-size: 10px;">0ms</span>
					<button class="btn btn-primary" id="btnApplyToEditor" style="padding: 4px 10px; font-size: 11px;">
						📥 Apply in Active Editor
					</button>
					<button class="btn btn-secondary" id="btnCopyVisualCode" style="padding: 4px 8px; font-size: 11px;">
						📋 Copy Code
					</button>
				</div>
			</div>

			<!-- Synthesis Summary & Design Tokens -->
			<div id="visualResultMeta" style="margin-bottom: 8px; font-size: 12px; color: var(--text-muted);"></div>

			<!-- Code Output Viewport -->
			<div class="code-viewport" style="background: rgba(0,0,0,0.4); border: 1px solid var(--border-glass); border-radius: var(--radius-md); padding: 12px; max-height: 420px; overflow: auto; font-family: monospace; font-size: 12px; white-space: pre-wrap; word-break: break-word;" id="visualCodeOutput">
			</div>
		</div>
	</section>
  `.trim();
}

export function getVisualTabCss(): string {
  return `
/* Visual Canvas Tab Specific Styles */
.visual-dropzone-box {
	border: 2px dashed var(--border-accent);
	border-radius: var(--radius-lg);
	padding: 24px 16px;
	background: rgba(15, 23, 42, 0.4);
	cursor: pointer;
	transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
	outline: none;
}

.visual-dropzone-box:hover,
.visual-dropzone-box:focus,
.visual-dropzone-box.drag-active {
	border-color: var(--accent-cyan);
	background: rgba(56, 189, 248, 0.08);
	box-shadow: 0 0 16px rgba(56, 189, 248, 0.15);
}

.visual-dropzone-inner {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 16px;
	text-align: left;
}

.visual-dropzone-icon {
	color: var(--accent-cyan);
	display: flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
}

.visual-dropzone-text {
	display: flex;
	flex-direction: column;
	gap: 2px;
}

.visual-chips-list {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	max-height: 160px;
	overflow-y: auto;
}

.visual-chip-item {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 6px 10px;
	background: var(--bg-tertiary);
	border: 1px solid var(--border-glass);
	border-radius: var(--radius-md);
	font-size: 11px;
}

.visual-chip-thumb-img {
	width: 32px;
	height: 32px;
	object-fit: cover;
	border-radius: 4px;
	border: 1px solid var(--border-glass);
}

.visual-chip-del-btn {
	background: transparent;
	border: none;
	color: var(--text-dim);
	cursor: pointer;
	font-size: 14px;
	padding: 2px 4px;
	line-height: 1;
}

.visual-chip-del-btn:hover {
	color: var(--accent-rose);
}
  `.trim();
}

export function getVisualTabScript(): string {
  return `
// ── Visual Canvas Client Logic ────────────────────────────────────────────────
(function initVisualCanvasClient() {
	let visualAssets = [];
	let latestSynthesizedCode = '';
	let latestResultType = 'code';

	const dropzone = document.getElementById('visualDropzoneArea');
	const fileInput = document.getElementById('visualFileInputHidden');
	const chipsContainer = document.getElementById('visualChipsContainer');
	const chipsList = document.getElementById('visualChipsList');
	const chipsCount = document.getElementById('visualChipsCount');
	const assetsBadge = document.getElementById('visualAssetsBadge');
	const clearBtn = document.getElementById('visualClearBtn');
	const btnSynthesize = document.getElementById('btnSynthesizeUiAction');
	const btnDiagnose = document.getElementById('btnDiagnoseLayoutAction');
	const resultCard = document.getElementById('visualResultCard');
	const resultTitle = document.getElementById('visualResultTitle');
	const resultMeta = document.getElementById('visualResultMeta');
	const codeOutput = document.getElementById('visualCodeOutput');
	const latencyBadge = document.getElementById('visualLatencyBadge');
	const btnApply = document.getElementById('btnApplyToEditor');
	const btnCopy = document.getElementById('btnCopyVisualCode');

	if (!dropzone) return;

	// Click to select file
	dropzone.addEventListener('click', () => {
		if (fileInput) fileInput.click();
	});

	// Drag & drop handlers
	['dragenter', 'dragover'].forEach(evt => {
		dropzone.addEventListener(evt, (e) => {
			e.preventDefault();
			e.stopPropagation();
			dropzone.classList.add('drag-active');
		});
	});

	['dragleave', 'dragend'].forEach(evt => {
		dropzone.addEventListener(evt, (e) => {
			e.preventDefault();
			e.stopPropagation();
			dropzone.classList.remove('drag-active');
		});
	});

	dropzone.addEventListener('drop', (e) => {
		e.preventDefault();
		e.stopPropagation();
		dropzone.classList.remove('drag-active');
		if (e.dataTransfer && e.dataTransfer.files) {
			handleIncomingFiles(Array.from(e.dataTransfer.files));
		}
	});

	// Clipboard paste listener (Win+Shift+S / PrtScn)
	window.addEventListener('paste', (e) => {
		const items = e.clipboardData ? e.clipboardData.items : null;
		if (!items) return;
		const imgFiles = [];
		for (let i = 0; i < items.length; i++) {
			if (items[i].type.startsWith('image/')) {
				const file = items[i].getAsFile();
				if (file) imgFiles.push(file);
			}
		}
		if (imgFiles.length > 0) {
			e.preventDefault();
			handleIncomingFiles(imgFiles);
		}
	});

	// File input change
	if (fileInput) {
		fileInput.addEventListener('change', (e) => {
			if (fileInput.files) {
				handleIncomingFiles(Array.from(fileInput.files));
				fileInput.value = '';
			}
		});
	}

	// Clear button
	if (clearBtn) {
		clearBtn.addEventListener('click', () => {
			visualAssets = [];
			renderVisualChips();
			vscode.postMessage({ type: 'clearVisualAssets' });
			if (resultCard) resultCard.style.display = 'none';
		});
	}

	// Action: Synthesize UI Component
	if (btnSynthesize) {
		btnSynthesize.addEventListener('click', () => {
			if (visualAssets.length === 0) return;
			btnSynthesize.disabled = true;
			btnSynthesize.textContent = '⏳ Synthesizing UI...';

			vscode.postMessage({
				type: 'requestSynthesis',
				workflow: 'ui-synthesis',
				asset: visualAssets[0]
			});
		});
	}

	// Action: Diagnose Layout Bug
	if (btnDiagnose) {
		btnDiagnose.addEventListener('click', () => {
			if (visualAssets.length === 0) return;
			btnDiagnose.disabled = true;
			btnDiagnose.textContent = '⏳ Diagnosing Layout...';

			vscode.postMessage({
				type: 'requestSynthesis',
				workflow: 'layout-diagnosis',
				asset: visualAssets[0]
			});
		});
	}

	// Apply to active editor
	if (btnApply) {
		btnApply.addEventListener('click', () => {
			if (!latestSynthesizedCode) return;
			vscode.postMessage({
				type: 'applyVisualCode',
				code: latestSynthesizedCode
			});
		});
	}

	// Copy to clipboard
	if (btnCopy) {
		btnCopy.addEventListener('click', () => {
			if (!latestSynthesizedCode) return;
			navigator.clipboard.writeText(latestSynthesizedCode).then(() => {
				btnCopy.textContent = '✅ Copied!';
				setTimeout(() => { btnCopy.textContent = '📋 Copy Code'; }, 1500);
			});
		});
	}

	function handleIncomingFiles(files) {
		const validFiles = files.filter(f => f.type.startsWith('image/') || /\\.(png|jpe?g|webp|svg)$/i.test(f.name));
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

				visualAssets.push(asset);
				renderVisualChips();

				vscode.postMessage({
					type: 'attachVisualAsset',
					asset: asset
				});
			};
			reader.readAsDataURL(file);
		});
	}

	function renderVisualChips() {
		const count = visualAssets.length;
		if (chipsCount) chipsCount.textContent = count.toString();
		if (assetsBadge) assetsBadge.textContent = count.toString();

		if (btnSynthesize) {
			btnSynthesize.disabled = (count === 0);
			btnSynthesize.textContent = '✨ Synthesize React + Tailwind UI';
		}
		if (btnDiagnose) {
			btnDiagnose.disabled = (count === 0);
			btnDiagnose.textContent = '🔍 Diagnose CSS Layout Bug';
		}

		if (count === 0) {
			if (chipsContainer) chipsContainer.style.display = 'none';
			return;
		}

		if (chipsContainer) chipsContainer.style.display = 'block';
		if (!chipsList) return;
		chipsList.innerHTML = '';

		visualAssets.forEach(asset => {
			const item = document.createElement('div');
			item.className = 'visual-chip-item';

			const img = document.createElement('img');
			img.className = 'visual-chip-thumb-img';
			img.src = asset.dataUrl || ('data:' + asset.mimeType + ';base64,' + asset.base64Data);

			const meta = document.createElement('div');
			meta.style.display = 'flex';
			meta.style.flexDirection = 'column';

			const name = document.createElement('strong');
			name.textContent = asset.filename;
			name.style.maxWidth = '180px';
			name.style.overflow = 'hidden';
			name.style.textOverflow = 'ellipsis';
			name.style.whiteSpace = 'nowrap';

			const size = document.createElement('span');
			size.style.fontSize = '9.5px';
			size.style.color = 'var(--text-dim)';
			size.textContent = Math.round(asset.sizeBytes / 1024) + ' KB';

			meta.appendChild(name);
			meta.appendChild(size);

			const delBtn = document.createElement('button');
			delBtn.className = 'visual-chip-del-btn';
			delBtn.innerHTML = '&times;';
			delBtn.title = 'Remove visual asset';
			delBtn.addEventListener('click', (e) => {
				e.stopPropagation();
				visualAssets = visualAssets.filter(a => a.id !== asset.id);
				renderVisualChips();
				vscode.postMessage({ type: 'removeVisualAsset', assetId: asset.id });
			});

			item.appendChild(img);
			item.appendChild(meta);
			item.appendChild(delBtn);
			chipsList.appendChild(item);
		});
	}

	// Listen for IPC messages from Extension Host
	window.addEventListener('message', event => {
		const msg = event.data;
		if (!msg) return;

		if (msg.type === 'visualSynthesisResult') {
			if (btnSynthesize) {
				btnSynthesize.disabled = (visualAssets.length === 0);
				btnSynthesize.textContent = '✨ Synthesize React + Tailwind UI';
			}
			if (btnDiagnose) {
				btnDiagnose.disabled = (visualAssets.length === 0);
				btnDiagnose.textContent = '🔍 Diagnose CSS Layout Bug';
			}

			if (resultCard && codeOutput) {
				resultCard.style.display = 'block';

				if (msg.workflow === 'ui-synthesis') {
					if (resultTitle) resultTitle.textContent = '✨ Synthesized React + Tailwind Component';
					latestSynthesizedCode = msg.output || '';
					codeOutput.textContent = latestSynthesizedCode;
					if (resultMeta) {
						resultMeta.innerHTML = '<strong>Summary:</strong> ' + (msg.summary || 'Component synthesized') + 
							'<br><strong>Design Tokens:</strong> ' + (msg.designTokens || 'Responsive layout');
					}
				} else if (msg.workflow === 'layout-diagnosis') {
					if (resultTitle) resultTitle.textContent = '🔍 Visual Layout Diagnosis & CSS Patch';
					latestSynthesizedCode = msg.patch || msg.output || '';
					codeOutput.textContent = '/* DIAGNOSIS */\\n' + (msg.output || '') + '\\n\\n/* CSS PATCH */\\n' + (msg.patch || '');
					if (resultMeta) {
						resultMeta.innerHTML = '<strong>Root Cause:</strong> ' + (msg.rootCause || 'CSS box-model misalignment') + 
							'<br><strong>Explanation:</strong> ' + (msg.explanation || 'See CSS patch below');
					}
				}

				if (latencyBadge) {
					latencyBadge.textContent = (msg.latencyMs || 0) + 'ms (' + (msg.provider || 'local') + ')';
				}

				resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
			}
		}
	});
})();
  `.trim();
}
