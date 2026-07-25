// HugOS stub: @parcel/watcher native binary missing.
// Provides a no-op file watcher so the IDE starts normally.
// File system watching is disabled — changes to files on disk won't auto-refresh,
// but the editor is fully usable for editing.

'use strict';

const EventEmitter = require('events');

/**
 * @param {string} dir
 * @param {Function} cb
 * @param {object} [opts]
 * @returns {Promise<{unsubscribe: () => Promise<void>}>}
 */
async function subscribe(dir, cb, opts) {
    return { unsubscribe: async () => {} };
}

/**
 * @param {string} dir
 * @param {Function} cb
 * @returns {Promise<void>}
 */
async function unsubscribe(dir, cb) {}

/**
 * @param {string} dir
 * @param {string} snapshotPath
 * @param {object} [opts]
 * @returns {Promise<void>}
 */
async function writeSnapshot(dir, snapshotPath, opts) {}

/**
 * @param {string} dir
 * @param {string} snapshotPath
 * @param {object} [opts]
 * @returns {Promise<Array>}
 */
async function getEventsSince(dir, snapshotPath, opts) {
    return [];
}

exports.subscribe = subscribe;
exports.unsubscribe = unsubscribe;
exports.writeSnapshot = writeSnapshot;
exports.getEventsSince = getEventsSince;
