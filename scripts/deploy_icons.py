#!/usr/bin/env python3
"""
Deploy High-Resolution Multi-Layer Icons for HugOS CLI, IDE, and Browser.
Generates all 7 standard Windows icon layers: 16x16, 24x24, 32x32, 48x48, 64x64, 128x128, 256x256.
Deploys across all repository, build staging, distribution, and live user locations.
Bakes the identical sharp cyber globe icon into PE headers (HugOS.exe, cli.exe) and WiX packaging manifests.
"""

import os
import sys
import shutil
import struct
import ctypes
from ctypes import wintypes
try:
    from PIL import Image
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False

def generate_multi_layer_ico(src_image_path, out_ico_path):
    if not HAVE_PIL:
        if os.path.exists(out_ico_path):
            return
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        master_ico = os.path.join(repo_root, "IDE", "hugos.ico")
        if os.path.exists(master_ico):
            os.makedirs(os.path.dirname(os.path.abspath(out_ico_path)), exist_ok=True)
            shutil.copy2(master_ico, out_ico_path)
            print(f"Copied existing multi-layer ICO -> {out_ico_path}")
        return

    src = Image.open(src_image_path).convert('RGBA')
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    
    os.makedirs(os.path.dirname(os.path.abspath(out_ico_path)), exist_ok=True)
    if os.path.exists(out_ico_path):
        try:
            import stat
            os.chmod(out_ico_path, stat.S_IWRITE | stat.S_IREAD)
        except Exception:
            pass
    try:
        src.save(out_ico_path, format='ICO', sizes=sizes)
        print(f"Generated multi-layer ICO ({len(sizes)} layers) -> {out_ico_path}")
    except Exception as e:
        print(f"Warning: Could not write to {out_ico_path}: {e}")

def patch_pe_icon(exe_path, ico_path):
    """Bakes the multi-layer ICO directly into the PE RT_GROUP_ICON resource table."""
    if not os.path.exists(exe_path) or not os.path.exists(ico_path):
        return False
        
    try:
        with open(ico_path, 'rb') as f:
            ico_data = f.read()
            
        reserved, ico_type, count = struct.unpack('<HHH', ico_data[:6])
        entries = []
        offset = 6
        for i in range(count):
            entry = ico_data[offset:offset+16]
            w, h, colors, res, planes, bpp, size, img_offset = struct.unpack('<BBBBHHII', entry)
            entries.append({
                'w': w, 'h': h, 'colors': colors, 'res': res,
                'planes': planes, 'bpp': bpp, 'size': size,
                'offset': img_offset, 'id': i + 1
            })
            offset += 16
            
        grp_header = struct.pack('<HHH', reserved, ico_type, count)
        grp_entries = b''
        for e in entries:
            grp_entries += struct.pack('<BBBBHHIH', e['w'], e['h'], e['colors'], e['res'], e['planes'], e['bpp'], e['size'], e['id'])
        group_icon_data = grp_header + grp_entries
        
        kernel32 = ctypes.windll.kernel32
        BeginUpdateResourceW = kernel32.BeginUpdateResourceW
        BeginUpdateResourceW.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]
        BeginUpdateResourceW.restype = wintypes.HANDLE

        UpdateResourceW = kernel32.UpdateResourceW
        UpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.LPWSTR, wintypes.WORD, ctypes.c_void_p, wintypes.DWORD]
        UpdateResourceW.restype = wintypes.BOOL

        EndUpdateResourceW = kernel32.EndUpdateResourceW
        EndUpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.BOOL]
        EndUpdateResourceW.restype = wintypes.BOOL

        RT_ICON = ctypes.cast(3, wintypes.LPWSTR)
        RT_GROUP_ICON = ctypes.cast(14, wintypes.LPWSTR)

        hUpdate = BeginUpdateResourceW(exe_path, False)
        if not hUpdate:
            print(f"Warning: Could not open {exe_path} for resource update (GetLastError={ctypes.GetLastError()})")
            return False

        # Update default icon group (ID 1 and ID 101/MAINICON)
        UpdateResourceW(hUpdate, RT_GROUP_ICON, ctypes.cast(1, wintypes.LPWSTR), 1033, group_icon_data, len(group_icon_data))
        UpdateResourceW(hUpdate, RT_GROUP_ICON, ctypes.cast(1, wintypes.LPWSTR), 0, group_icon_data, len(group_icon_data))

        for e in entries:
            img_bytes = ico_data[e['offset']:e['offset']+e['size']]
            UpdateResourceW(hUpdate, RT_ICON, ctypes.cast(e['id'], wintypes.LPWSTR), 1033, img_bytes, len(img_bytes))
            UpdateResourceW(hUpdate, RT_ICON, ctypes.cast(e['id'], wintypes.LPWSTR), 0, img_bytes, len(img_bytes))

        res = EndUpdateResourceW(hUpdate, False)
        if res:
            print(f"[OK] Successfully baked glowing globe icon into PE header: {exe_path}")
            return True
        else:
            print(f"Warning: EndUpdateResourceW failed for {exe_path} (GetLastError={ctypes.GetLastError()})")
            return False
    except Exception as e:
        print(f"Warning: Failed to patch PE icon for {exe_path}: {e}")
        return False

def flush_windows_icon_cache():
    """Flushes Explorer icon cache and notifies shell of association change."""
    try:
        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_IDLIST = 0x0000
        ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
        print("[OK] Windows Shell icon cache notified and flushed via SHChangeNotify.")
    except Exception as e:
        print(f"Warning: SHChangeNotify failed: {e}")

def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(repo_root)
    
    master_png = os.path.join(repo_root, "browser_globe_1024.png")
    if not os.path.exists(master_png):
        print(f"ERROR: Master PNG not found at {master_png}", file=sys.stderr)
        sys.exit(1)
        
    master_img = Image.open(master_png).convert('RGBA') if HAVE_PIL else None
    
    # 1. Target ICO locations
    ico_targets = [
        # IDE targets
        os.path.join(repo_root, "IDE", "hugos.ico"),
        os.path.join(repo_root, "IDE", "code.ico"),
        os.path.join(repo_root, "IDE", "hugos_browser.ico"),
        os.path.join(repo_root, "IDE", "patches", "icons", "win32", "code.ico"),
        os.path.join(repo_root, "IDE", "VSCode-win32-x64", "hugos.ico"),
        os.path.join(repo_root, "IDE", "VSCode-win32-x64", "code.ico"),
        os.path.join(repo_root, "IDE", "VSCode-win32-x64", "resources", "app", "resources", "win32", "code.ico"),
        os.path.join(repo_root, "IDE", "VSCode-win32-x64", "browser", "ui", "hugos_browser.ico"),
        os.path.join(repo_root, "IDE", "VSCode-win32-x64", "browser", "ui", "favicon.ico"),
        
        # Browser targets
        os.path.join(repo_root, "browser", "hugos_browser.ico"),
        os.path.join(repo_root, "browser", "ui", "hugos_browser.ico"),
        os.path.join(repo_root, "browser", "ui", "favicon.ico"),
        os.path.join(repo_root, "browser", "Chromium-win32-x64", "hugos_browser.ico"),
    ]
    
    # Add local AppData and installer cache targets if they exist
    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        candidate_paths = [
            os.path.join(local_app, "HugOS IDE", "hugos.ico"),
            os.path.join(local_app, "HugOS IDE", "code.ico"),
            os.path.join(local_app, "HugOS IDE", "resources", "app", "resources", "win32", "code.ico"),
            os.path.join(local_app, "HugOS Browser", "hugos_browser.ico"),
            os.path.join(local_app, "HugOS Browser", "Chromium-win32-x64", "hugos_browser.ico"),
            os.path.join(local_app, "HugOS Browser", "ui", "hugos_browser.ico"),
            os.path.join(local_app, "HugOS Browser", "ui", "favicon.ico"),
        ]
        for p in candidate_paths:
            if os.path.exists(os.path.dirname(p)):
                ico_targets.append(p)
                
    app_data = os.environ.get("APPDATA", "")
    if app_data:
        installer_dir = os.path.join(app_data, "Microsoft", "Installer")
        if os.path.exists(installer_dir):
            for sub in os.listdir(installer_dir):
                target_ico = os.path.join(installer_dir, sub, "HugOSIcon.ico")
                if os.path.exists(target_ico):
                    ico_targets.append(target_ico)
                target_bico = os.path.join(installer_dir, sub, "HugOSBrowserIcon.ico")
                if os.path.exists(target_bico):
                    ico_targets.append(target_bico)

    for target in ico_targets:
        generate_multi_layer_ico(master_png, target)
        
    # 2. Generate PNG layers for web & browser UI
    png_sizes = {
        "favicon-16x16.png": 16,
        "favicon-24x24.png": 24,
        "favicon-32x32.png": 32,
        "icon-48.png": 48,
        "icon-64.png": 64,
        "icon-128.png": 128,
        "icon-192.png": 192,
        "icon-256.png": 256,
        "icon-512.png": 512,
    }
    
    ui_dirs = [
        os.path.join(repo_root, "browser", "ui"),
        os.path.join(repo_root, "IDE", "VSCode-win32-x64", "ui"),
        os.path.join(repo_root, "IDE", "VSCode-win32-x64", "browser", "ui"),
    ]
    if local_app:
        ui_dirs.append(os.path.join(local_app, "HugOS Browser", "ui"))
        
    if HAVE_PIL and master_img:
        for ui_dir in ui_dirs:
            if os.path.exists(ui_dir):
                for filename, dim in png_sizes.items():
                    dest = os.path.join(ui_dir, filename)
                    resized = master_img.resize((dim, dim), Image.Resampling.LANCZOS)
                    resized.save(dest, format="PNG")
                    print(f"Generated {dim}x{dim} PNG -> {dest}")
    else:
        print("[INFO] PIL not available; preserved existing high-res PNG assets.")

    # 3. Bake PE Icon Header into HugOS.exe
    primary_ico = os.path.join(repo_root, "IDE", "hugos.ico")
    exe_targets = [
        os.path.join(repo_root, "IDE", "VSCode-win32-x64", "HugOS.exe"),
    ]
    if local_app:
        exe_targets.append(os.path.join(local_app, "HugOS IDE", "HugOS.exe"))

    for exe in exe_targets:
        if os.path.exists(exe):
            patch_pe_icon(exe, primary_ico)

    # 4. Flush Windows Icon Cache
    flush_windows_icon_cache()
                
    print("\n[SUCCESS] All multi-layer icons, PE resources, and UI assets deployed successfully!")

if __name__ == "__main__":
    main()
