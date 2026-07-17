# 🔴 Incident Report: HugOS IDE Window Never Appeared After MSI Build
**Date:** 2026-07-16  
**Severity:** Critical — IDE completely non-functional  
**Status:** ✅ Resolved

---

## What Happened

After running `build_msi.ps1`, the HugOS IDE appeared to start (4 processes visible in Task Manager) but **no window ever appeared**. The IDE was broken for every launch attempt — dev build and installed MSI alike — for 17+ hours.

---

## Root Cause

`build_msi.ps1` step 5 was signing **every** `.exe` and `.dll` in the package directory with a self-signed `CN=HugOS IDE` certificate using `signtool.exe`. This included Electron's core binaries:

| Binary | Required Signer | What We Did | Result |
|---|---|---|---|
| `HugOS.exe` | Microsoft (Electron) | Overwrote with HugOS self-signed | ICU data fd broken — JS never runs |
| `dxil.dll` | Microsoft (DirectX) | Overwrote with HugOS self-signed | GPU init failed |
| `d3dcompiler_47.dll` | Microsoft (DirectX) | Overwrote with HugOS self-signed | GPU init failed |
| `dxcompiler.dll` | Microsoft (DirectX) | Overwrote with HugOS self-signed | GPU init failed |
| `vk_swiftshader.dll` | Google (Vulkan) | Overwrote with HugOS self-signed | Software fallback failed |
| `libEGL.dll` | Google (ANGLE) | Overwrote with HugOS self-signed | GL layer failed |
| `libGLESv2.dll` | Google (ANGLE) | Overwrote with HugOS self-signed | GL layer failed |
| `ffmpeg.dll` | Chromium | Overwrote with HugOS self-signed | Media failed |

### Why `HugOS.exe` specifically killed everything

`HugOS.exe` is a **custom-compiled Electron binary** with HugOS icons/metadata embedded in its PE resource table. When `signtool.exe` adds a new signature to a PE file, it relocates sections in a way that corrupts the ICU data file descriptor offset baked into this binary. After signing:

- Main process (broker) — starts ✅  
- GPU process — starts ✅  
- Network utility — starts ✅  
- Crashpad handler — starts ✅  
- **Renderer process — NEVER SPAWNED** ❌ (JS never ran, no window)

The renderer requires the Electron binary to load ICU data correctly. With the corrupted offset, `icu_util.cc` threw `Invalid file descriptor to ICU data received` and the process exited silently with code `-2147483645`.

---

## Diagnosis Trail

| Check | Finding |
|---|---|
| 4 processes, no window | Renderer (`--type=renderer`) never spawned |
| No crash dumps | Clean exit — intentional, not a crash |
| Empty `main.log` / no `CachedData` | JavaScript **never executed** |
| JS shim `require('fs').appendFileSync(...)` at top of main.js | File never written — confirmed pre-JS failure |
| stderr capture | `Invalid file descriptor to ICU data received` |
| `Get-AuthenticodeSignature HugOS.exe` | `CN=HugOS IDE [UnknownError]` — confirmed broken |

---

## Fix Applied

### Immediate (dev build)
1. Downloaded VSCode 1.126.0 win32-x64 archive (exact matching Electron version)
2. Replaced `HugOS.exe` with `Code.exe` from the zip (valid Microsoft signature)
3. Synced `icudtl.dat`, `v8_context_snapshot.bin`, `snapshot_blob.bin` from the same zip
4. Restored 7 GPU/DirectX DLLs (valid original signatures)
5. Added `@parcel/watcher`, `@vscode/windows-registry`, `@vscode/windows-process-tree` no-op stubs

### Permanent (build pipeline) — `build_msi.ps1`

**Step 4.1 added** — Auto-validates `HugOS.exe` signature before signing. If invalid, downloads VSCode 1.126.0 and restores `Code.exe` as `HugOS.exe`.

**Step 5 exclusion list** — Never-sign list now includes `HugOS.exe`:
```
HugOS.exe, dxil.dll, d3dcompiler_47.dll, dxcompiler.dll,
vk_swiftshader.dll, libEGL.dll, libGLESv2.dll, ffmpeg.dll
```

---

## ⛔ Rules — Never Violate These

### Rule 1 — Never sign Electron/GPU binaries with a self-signed cert

These files MUST keep their original Microsoft/Google signatures:

```
HugOS.exe          ← uses Code.exe from VSCode, Microsoft-signed
dxil.dll           ← DirectX IL runtime, Windows validates signature
d3dcompiler_47.dll ← DirectX compiler
dxcompiler.dll     ← DX compiler runtime  
vk_swiftshader.dll ← Vulkan SwiftShader, Khronos/Google-signed
libEGL.dll         ← ANGLE OpenGL layer, Google-signed
libGLESv2.dll      ← ANGLE OpenGL ES layer, Google-signed
ffmpeg.dll         ← Chromium media, Google-signed
```

### Rule 2 — `HugOS.exe` is always `Code.exe`, never a custom build

HugOS branding comes from `product.json`, `resources/`, and JS extensions —
NOT from embedding resources in the Electron PE binary. Never compile a
custom Electron binary for HugOS. Use `Code.exe` from the matching VSCode
release and rename it.

### Rule 3 — Never use `*.exe *.dll` wildcards with signtool

Only sign files YOU built:
- `cli.exe` (Rust binary)
- `*.node` native addon files  
- Custom helper executables you compiled yourself

---

## Native Module Stubs Required

These ship without `.node` binaries and need JS no-op stubs:

| Module | Impact if Missing |
|---|---|
| `@parcel/watcher` | **Hard throw on startup — IDE won't start** |
| `@vscode/policy-watcher` | Hard throw on startup |
| `@vscode/spdlog` | Logs never written |
| `@vscode/windows-mutex` | Single-instance broken |
| `@vscode/windows-registry` | Registry reads return undefined |
| `@vscode/windows-process-tree` | Process tree empty |

All stubs are in `IDE/patches/native_stubs/` and applied by step 4.85.

---

## Pre-Release Checklist

Before every MSI build run:

- [ ] `Get-AuthenticodeSignature HugOS.exe` → `Valid` + `CN=Microsoft Corporation`  
- [ ] `Get-AuthenticodeSignature dxil.dll` → `Valid` + `CN=Microsoft Corporation`  
- [ ] 6 native stubs exist in `node_modules/` (check `@parcel/watcher/index.js`)  
- [ ] Launch `HugOS.exe` manually → window appears within 15 seconds  
- [ ] `main.log` in `%APPDATA%\hugos\logs\{session}\` has content  
- [ ] `CachedData/` folder is populated (confirms JS ran)  

---

## Commits

| Hash | Description |
|---|---|
| `ca7b557c` | fix: add native module stubs (policy-watcher, spdlog, windows-mutex) |
| `2018208e` | fix: restore Electron binary integrity + 3 more native stubs |
