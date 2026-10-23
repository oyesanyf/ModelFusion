/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See License.txt in the project root for license information.
 *--------------------------------------------------------------------------------------------*/

const fs = require('fs');
const path = require('path');

class Logger {
	constructor(type, name, filepath, maxFileSize, maxFiles) {
		this._name = name;
		this._filepath = filepath;
		this._level = 0;
		if (this._filepath) {
			try {
				fs.mkdirSync(path.dirname(this._filepath), { recursive: true });
			} catch (_) {}
		}
	}
	_write(levelStr, msg) {
		if (!this._filepath) return;
		try {
			const ts = new Date().toISOString();
			fs.appendFileSync(this._filepath, `${ts} [${levelStr}] ${msg}\n`);
		} catch (_) {}
	}
	trace(msg) { if (this._level <= 0) this._write('trace', msg); }
	debug(msg) { if (this._level <= 1) this._write('debug', msg); }
	info(msg) { if (this._level <= 2) this._write('info', msg); }
	warn(msg) { if (this._level <= 3) this._write('warn', msg); }
	error(msg) { if (this._level <= 4) this._write('error', msg); }
	critical(msg) { if (this._level <= 5) this._write('critical', msg); }
	setLevel(level) { this._level = level; }
	getLevel() { return this._level; }
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
