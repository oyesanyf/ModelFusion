/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See License.txt in the project root for license information.
 *--------------------------------------------------------------------------------------------*/

// HugOS stub: native @vscode/policy-watcher binary is not shipped with
// this build. We provide a no-op implementation so the IDE starts normally.
// Group Policy enforcement is simply disabled — all policy checks pass through.

/**
 * @param {string} _productName  ignored
 * @param {Record<string, {type: string}>} _definitions  ignored
 * @param {Function} _callback  ignored
 * @returns {{ dispose: () => void }}
 */
function createWatcher(_productName, _definitions, _callback) {
	// Return a disposable watcher that never fires — behaves as if no policies are set.
	return {
		dispose() {}
	};
}

exports.createWatcher = createWatcher;
