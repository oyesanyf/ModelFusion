"use strict";
/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See License.txt in the project root for license information.
 *--------------------------------------------------------------------------------------------*/
// HugOS stub: winregistry.node binary missing. Returns null for all registry reads.
Object.defineProperty(exports, "__esModule", { value: true });
exports.GetDWORDRegKey = exports.GetStringRegKey = void 0;

function GetStringRegKey(hive, path, name) {
    return undefined; // not found
}
exports.GetStringRegKey = GetStringRegKey;

function GetDWORDRegKey(hive, path, name) {
    return undefined; // not found
}
exports.GetDWORDRegKey = GetDWORDRegKey;