/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See License.txt in the project root for license information.
 *--------------------------------------------------------------------------------------------*/

// HugOS stub: @vscode/spdlog native binary (.node) is missing from this build.
// We provide a no-op logger that writes to the console so the IDE starts normally.
// File-based rotating logs are simply not written; all log output goes to stderr instead.

const path = require('path');

class Logger {
	constructor(type, name, filepath, maxFileSize, maxFiles) {
		this._name = name;
		this._filepath = filepath;
		this._level = 0;
	}
	trace(msg) {}
	debug(msg) {}
	info(msg) { /* silent */ }
	warn(msg) { process.stderr.write(`[${this._name}] WARN: ${msg}\n`); }
	error(msg) { process.stderr.write(`[${this._name}] ERROR: ${msg}\n`); }
	critical(msg) { process.stderr.write(`[${this._name}] CRITICAL: ${msg}\n`); }
	setLevel(level) { this._level = level; }
	flush() {}
	drop() {}
	clearFormatters() {}
	setPattern(pattern) {}
	setAsyncMode(bufferSize, overflowPolicy) {}
}

let _globalLevel = 0;

exports.version = '0.0.0-hugos-stub';
exports.setLevel = function(level) { _globalLevel = level; };
exports.setFlushOn = function(level) {};
exports.Logger = Logger;

function createRotatingLogger(name, filepath, maxFileSize, maxFiles) {
	return createLogger('rotating', name, filepath, maxFileSize, maxFiles);
}

function createAsyncRotatingLogger(name, filepath, maxFileSize, maxFiles) {
	return createLogger('rotating_async', name, filepath, maxFileSize, maxFiles);
}

async function createLogger(loggerType, name, filepath, maxFileSize, maxFiles) {
	return new Logger(loggerType, name, filepath, maxFileSize, maxFiles);
}

exports.createRotatingLogger = createRotatingLogger;
exports.createAsyncRotatingLogger = createAsyncRotatingLogger;
