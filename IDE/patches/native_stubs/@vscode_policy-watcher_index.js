/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See License.txt in the project root for license information.
 *--------------------------------------------------------------------------------------------*/

// HugOS stub: native @vscode/policy-watcher binary is not shipped with
// this build. We provide a no-op implementation that immediately signals
// an empty policy update so NativePolicyService & CopilotManagedSettingsService resolve.

function createWatcher(_productName, _definitions, _callback) {
	if (typeof _callback === 'function') {
		queueMicrotask(() => {
			try { _callback({}); } catch (_) {}
		});
	}
	return {
		dispose() {}
	};
}

exports.createWatcher = createWatcher;
