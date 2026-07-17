/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See License.txt in the project root for license information.
 *--------------------------------------------------------------------------------------------*/

// HugOS stub: @vscode/windows-mutex native binary (.node) is missing from this build.
// We provide a no-op Mutex so the IDE starts normally.
// Multiple-instance prevention is not enforced by this stub.

const isWindows = process.platform === 'win32';

class Mutex {
	constructor(name) {
		this._name = name;
		this._active = true;
	}
	isActive() { return this._active; }
	release() { this._active = false; }
}

function isActive(name) {
	// No native check — assume no other instance holds the mutex
	return false;
}

module.exports = { Mutex, isActive };