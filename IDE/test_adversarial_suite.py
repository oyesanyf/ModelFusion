import os
import sys
import json
import shutil
import tempfile
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
VERIFY_SCRIPT = os.path.join(SCRIPT_DIR, "verify_product_json.ps1")
PATCH_SCRIPT = os.path.join(SCRIPT_DIR, "patch_product_json.py")

VALID_PACKAGE_JSON = {
    "name": "copilot-chat",
    "publisher": "GitHub",
    "version": "0.54.1"
}

VALID_PRODUCT_JSON = {
    "nameShort": "HugOS",
    "nameLong": "HugOS IDE",
    "applicationName": "hugos",
    "win32MutexName": "hugos",
    "win32DirName": "HugOS IDE",
    "win32NameVersion": "HugOS IDE",
    "dataFolderName": ".hugos-ide",
    "darwinBundleIdentifier": "com.hugos.ide",
    "win32AppUserModelId": "HugOS.HugOS",
    "win32ShellNameShort": "H&ugOS",
    "defaultChatAgent": {
        "extensionId": "GitHub.copilot-chat",
        "chatExtensionId": "GitHub.copilot-chat",
        "chatExtensionOutputId": "GitHub.copilot-chat.GitHub Copilot Chat.log"
    },
    "extensionEnabledApiProposals": {
        "GitHub.copilot-chat": [
            "defaultChatParticipant",
            "chatParticipantAdditions"
        ]
    },
    "trustedExtensionAuthAccess": {
        "github": ["GitHub.copilot-chat"]
    },
    "configurationDefaults": {
        "update.mode": "none"
    }
}

VALID_PDS = {
    "update.mode": "none",
    "update.enableWindowsBackgroundUpdates": False,
    "update.showReleaseNotes": False
}

def setup_mock_pack_dir(base_dir, ver_hash="7e7950df89", product_obj=None, pkg_obj=None):
    pack_dir = os.path.join(base_dir, "VSCode-win32-x64")
    p_data = product_obj if product_obj is not None else VALID_PRODUCT_JSON
    k_data = pkg_obj if pkg_obj is not None else VALID_PACKAGE_JSON

    # Root resources
    root_app = os.path.join(pack_dir, "resources", "app")
    os.makedirs(root_app, exist_ok=True)
    with open(os.path.join(root_app, "product.json"), "w", encoding="utf-8") as f:
        json.dump(p_data, f, indent=4)
    with open(os.path.join(root_app, "product-default-settings.json"), "w", encoding="utf-8") as f:
        json.dump(VALID_PDS, f, indent=4)

    # Extension
    ext_dir = os.path.join(root_app, "extensions", "copilot")
    os.makedirs(ext_dir, exist_ok=True)
    with open(os.path.join(ext_dir, "package.json"), "w", encoding="utf-8") as f:
        json.dump(k_data, f, indent=4)

    # Versioned dir
    if ver_hash:
        ver_app = os.path.join(pack_dir, ver_hash, "resources", "app")
        os.makedirs(ver_app, exist_ok=True)
        with open(os.path.join(ver_app, "product.json"), "w", encoding="utf-8") as f:
            json.dump(p_data, f, indent=4)
        with open(os.path.join(ver_app, "product-default-settings.json"), "w", encoding="utf-8") as f:
            json.dump(VALID_PDS, f, indent=4)
        ver_ext = os.path.join(ver_app, "extensions", "copilot")
        os.makedirs(ver_ext, exist_ok=True)
        with open(os.path.join(ver_ext, "package.json"), "w", encoding="utf-8") as f:
            json.dump(k_data, f, indent=4)

    return pack_dir

def run_verify(pack_dir, require_versioned=True, check_installed=False):
    rv_str = "$true" if require_versioned else "$false"
    ci_str = "$true" if check_installed else "$false"
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", VERIFY_SCRIPT,
        "-PackDir", pack_dir,
        "-RequireVersionedDir", rv_str,
        "-CheckInstalled", ci_str
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr

def run_patch(pack_dir):
    cmd = [sys.executable, PATCH_SCRIPT, pack_dir]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr

passed_tests = 0
failed_tests = 0

def record_result(name, condition, details=""):
    global passed_tests, failed_tests
    if condition:
        print(f"  [PASS] {name}")
        passed_tests += 1
    else:
        print(f"  [FAIL] {name} - {details}")
        failed_tests += 1

print("============================================================")
print("Running Adversarial Test Suite for HugOS product.json Fixes")
print("============================================================")

temp_root = tempfile.mkdtemp(prefix="adv_test_")

try:
    # Test 1: Baseline valid setup
    pdir = setup_mock_pack_dir(os.path.join(temp_root, "t1"))
    rc, out, _ = run_verify(pdir)
    record_result("Test 1: Baseline valid packDir passes", rc == 0, f"rc={rc}")

    # Test 2: Missing versioned dir when required
    pdir = setup_mock_pack_dir(os.path.join(temp_root, "t2"), ver_hash=None)
    rc, out, _ = run_verify(pdir, require_versioned=True)
    record_result("Test 2: Missing versioned dir fails when required", rc == 1, f"rc={rc}")

    # Test 3: Missing versioned dir when NOT required
    pdir = setup_mock_pack_dir(os.path.join(temp_root, "t3"), ver_hash=None)
    rc, out, _ = run_verify(pdir, require_versioned=False)
    record_result("Test 3: Missing versioned dir passes when not required", rc == 0, f"rc={rc}")

    # Test 4: Extension ID mismatch (GitHub.copilot stock)
    bad_p = json.loads(json.dumps(VALID_PRODUCT_JSON))
    bad_p["defaultChatAgent"]["extensionId"] = "GitHub.copilot"
    pdir = setup_mock_pack_dir(os.path.join(temp_root, "t4"), product_obj=bad_p)
    rc, out, _ = run_verify(pdir)
    record_result("Test 4: Stock extensionId 'GitHub.copilot' fails", rc == 1, f"rc={rc}")

    # Test 5: chatExtensionId mismatch
    bad_p = json.loads(json.dumps(VALID_PRODUCT_JSON))
    bad_p["defaultChatAgent"]["chatExtensionId"] = "wrong.chat-id"
    pdir = setup_mock_pack_dir(os.path.join(temp_root, "t5"), product_obj=bad_p)
    rc, out, _ = run_verify(pdir)
    record_result("Test 5: chatExtensionId mismatch fails", rc == 1, f"rc={rc}")

    # Test 6: Missing chatExtensionOutputId (NEW CHECK)
    bad_p = json.loads(json.dumps(VALID_PRODUCT_JSON))
    bad_p["defaultChatAgent"]["chatExtensionOutputId"] = ""
    pdir = setup_mock_pack_dir(os.path.join(temp_root, "t6"), product_obj=bad_p)
    rc, out, _ = run_verify(pdir)
    record_result("Test 6: Empty chatExtensionOutputId fails", rc == 1, f"rc={rc}")

    # Test 7: chatExtensionOutputId prefix mismatch
    bad_p = json.loads(json.dumps(VALID_PRODUCT_JSON))
    bad_p["defaultChatAgent"]["chatExtensionOutputId"] = "GitHub.copilot.GitHub Copilot Chat.log"
    pdir = setup_mock_pack_dir(os.path.join(temp_root, "t7"), product_obj=bad_p)
    rc, out, _ = run_verify(pdir)
    record_result("Test 7: chatExtensionOutputId stock prefix fails", rc == 1, f"rc={rc}")

    # Test 8: Missing proposal defaultChatParticipant
    bad_p = json.loads(json.dumps(VALID_PRODUCT_JSON))
    bad_p["extensionEnabledApiProposals"]["GitHub.copilot-chat"] = ["chatParticipantAdditions"]
    pdir = setup_mock_pack_dir(os.path.join(temp_root, "t8"), product_obj=bad_p)
    rc, out, _ = run_verify(pdir)
    record_result("Test 8: Missing proposal defaultChatParticipant fails", rc == 1, f"rc={rc}")

    # Test 9: Missing proposal chatParticipantAdditions
    bad_p = json.loads(json.dumps(VALID_PRODUCT_JSON))
    bad_p["extensionEnabledApiProposals"]["GitHub.copilot-chat"] = ["defaultChatParticipant"]
    pdir = setup_mock_pack_dir(os.path.join(temp_root, "t9"), product_obj=bad_p)
    rc, out, _ = run_verify(pdir)
    record_result("Test 9: Missing proposal chatParticipantAdditions fails", rc == 1, f"rc={rc}")

    # Test 10: Array branding field false-pass prevention (NEW CHECK)
    bad_p = json.loads(json.dumps(VALID_PRODUCT_JSON))
    bad_p["nameShort"] = ["HugOS"]  # Array containing expected string!
    pdir = setup_mock_pack_dir(os.path.join(temp_root, "t10"), product_obj=bad_p)
    rc, out, _ = run_verify(pdir)
    record_result("Test 10: Array branding field ['HugOS'] fails (array filter fix)", rc == 1, f"rc={rc}")

    # Test 11: Array extensionId false-pass prevention (NEW CHECK)
    bad_p = json.loads(json.dumps(VALID_PRODUCT_JSON))
    bad_p["defaultChatAgent"]["extensionId"] = ["GitHub.copilot-chat"]
    pdir = setup_mock_pack_dir(os.path.join(temp_root, "t11"), product_obj=bad_p)
    rc, out, _ = run_verify(pdir)
    record_result("Test 11: Array extensionId ['GitHub.copilot-chat'] fails (array filter fix)", rc == 1, f"rc={rc}")

    # Test 12: String proposals instead of array
    bad_p = json.loads(json.dumps(VALID_PRODUCT_JSON))
    bad_p["extensionEnabledApiProposals"]["GitHub.copilot-chat"] = "defaultChatParticipant"
    pdir = setup_mock_pack_dir(os.path.join(temp_root, "t12"), product_obj=bad_p)
    rc, out, _ = run_verify(pdir)
    record_result("Test 12: String proposals value fails", rc == 1, f"rc={rc}")

    # Test 13: Stock branding nameShort = "Code"
    bad_p = json.loads(json.dumps(VALID_PRODUCT_JSON))
    bad_p["nameShort"] = "Code"
    pdir = setup_mock_pack_dir(os.path.join(temp_root, "t13"), product_obj=bad_p)
    rc, out, _ = run_verify(pdir)
    record_result("Test 13: Stock branding nameShort='Code' fails", rc == 1, f"rc={rc}")

    # Test 14: UTF-8 BOM
    pdir = setup_mock_pack_dir(os.path.join(temp_root, "t14"))
    target = os.path.join(pdir, "resources", "app", "product.json")
    with open(target, "rb") as f:
        c = f.read()
    with open(target, "wb") as f:
        f.write(b"\xef\xbb\xbf" + c)
    rc, out, _ = run_verify(pdir)
    record_result("Test 14: UTF-8 BOM injected fails", rc == 1, f"rc={rc}")

    # Test 15: UTF-16 LE BOM
    pdir = setup_mock_pack_dir(os.path.join(temp_root, "t15"))
    target = os.path.join(pdir, "resources", "app", "product.json")
    with open(target, "wb") as f:
        f.write(b"\xff\xfe" + b"{}")
    rc, out, _ = run_verify(pdir)
    record_result("Test 15: UTF-16 LE BOM injected fails", rc == 1, f"rc={rc}")

    # Test 16: 0-byte empty file
    pdir = setup_mock_pack_dir(os.path.join(temp_root, "t16"))
    target = os.path.join(pdir, "resources", "app", "product.json")
    with open(target, "wb") as f:
        pass
    rc, out, _ = run_verify(pdir)
    record_result("Test 16: 0-byte empty file fails", rc == 1, f"rc={rc}")

    # Test 17: Syntax corruption
    pdir = setup_mock_pack_dir(os.path.join(temp_root, "t17"))
    target = os.path.join(pdir, "resources", "app", "product.json")
    with open(target, "w", encoding="utf-8") as f:
        f.write("{ invalid json")
    rc, out, _ = run_verify(pdir)
    record_result("Test 17: Malformed syntax fails", rc == 1, f"rc={rc}")

    # Test 18: Patch recovery from null defaultChatAgent (NEW CHECK)
    pdir = setup_mock_pack_dir(os.path.join(temp_root, "t18"))
    target = os.path.join(pdir, "resources", "app", "product.json")
    with open(target, "w", encoding="utf-8") as f:
        f.write('{"nameShort": "HugOS", "nameLong": "HugOS IDE", "applicationName": "hugos", "win32MutexName": "hugos", "win32DirName": "HugOS IDE", "win32NameVersion": "HugOS IDE", "dataFolderName": ".hugos-ide", "darwinBundleIdentifier": "com.hugos.ide", "win32AppUserModelId": "HugOS.HugOS", "win32ShellNameShort": "H&ugOS", "defaultChatAgent": null}')
    rc, out, _ = run_patch(pdir)
    record_result("Test 18: patch_product_json survives null defaultChatAgent", rc == 0, f"rc={rc}")

    # Test 19: Patch recovery from null proposals and null auth (NEW CHECK)
    pdir = setup_mock_pack_dir(os.path.join(temp_root, "t19"))
    target = os.path.join(pdir, "resources", "app", "product.json")
    with open(target, "w", encoding="utf-8") as f:
        f.write('{"nameShort": "HugOS", "nameLong": "HugOS IDE", "applicationName": "hugos", "win32MutexName": "hugos", "win32DirName": "HugOS IDE", "win32NameVersion": "HugOS IDE", "dataFolderName": ".hugos-ide", "darwinBundleIdentifier": "com.hugos.ide", "win32AppUserModelId": "HugOS.HugOS", "win32ShellNameShort": "H&ugOS", "extensionEnabledApiProposals": null, "trustedExtensionAuthAccess": null}')
    rc, out, _ = run_patch(pdir)
    record_result("Test 19: patch_product_json survives null proposals & auth", rc == 0, f"rc={rc}")

    # Test 20: Patch non-dict JSON error exit (NEW CHECK)
    pdir = setup_mock_pack_dir(os.path.join(temp_root, "t20"))
    target = os.path.join(pdir, "resources", "app", "product.json")
    with open(target, "w", encoding="utf-8") as f:
        f.write('[1, 2, 3]')
    rc, out, _ = run_patch(pdir)
    record_result("Test 20: patch_product_json fails cleanly on JSON list", rc == 1, f"rc={rc}")

    # Test 21: Full short hash (7 chars) and SHA1 hash (40 chars) recognition
    pdir = setup_mock_pack_dir(os.path.join(temp_root, "t21"), ver_hash="abcdef1")
    rc, out, _ = run_verify(pdir)
    record_result("Test 21: 7-character short commit hash recognized", rc == 0, f"rc={rc}")

    # Test 22: Patch script strips BOM and verify succeeds
    pdir = setup_mock_pack_dir(os.path.join(temp_root, "t22"))
    target = os.path.join(pdir, "resources", "app", "product.json")
    with open(target, "rb") as f:
        c = f.read()
    with open(target, "wb") as f:
        f.write(b"\xef\xbb\xbf" + c)
    rc_p, _, _ = run_patch(pdir)
    rc_v, _, _ = run_verify(pdir)
    record_result("Test 22: patch strips BOM and verify passes", rc_p == 0 and rc_v == 0, f"rc_p={rc_p}, rc_v={rc_v}")

    # Test 23: patch_workbench patches mock unminified workbench
    wb_script = os.path.join(SCRIPT_DIR, "patch_workbench.py")
    t23_dir = os.path.join(temp_root, "t23")
    wb_dir = os.path.join(t23_dir, "resources", "app", "out", "vs", "workbench")
    os.makedirs(wb_dir, exist_ok=True)
    wb_file = os.path.join(wb_dir, "workbench.desktop.main.js")
    unminified_sample = (
        "class ExtensionEnablementService {\n"
        "  ensureChatExtensionInitialDisabledState() {\n"
        "    console.log('original');\n"
        "  }\n"
        "  test(extension) {\n"
        "    if (extension.identifier.id.toLowerCase() === this._chatExtensionId) {\n"
        "      this.ensureChatExtensionInitialDisabledState();\n"
        "    }\n"
        "    enablementState = this._getUserEnablementState(extension.identifier);\n"
        "    const context2 = chatEntitlementService.context?.value;\n"
        "    const requests = chatEntitlementService.requests?.value;\n"
        "    if (!context2 || !requests) {\n"
        "      return;\n"
        "    }\n"
        "  }\n"
        "  async showDialog(options3) {\n"
        "    const disposables = new DisposableStore();\n"
        "  }\n"
        "}\n"
    )
    with open(wb_file, "w", encoding="utf-8") as f:
        f.write(unminified_sample)
    cmd23 = [sys.executable, wb_script, t23_dir, "--skip-installed"]
    p23 = subprocess.run(cmd23, capture_output=True, text=True)
    with open(wb_file, "r", encoding="utf-8") as f:
        wb_c = f.read()
    t23_ok = (p23.returncode == 0 and
              "return 3 /* EnabledGlobally */;" in wb_c and
              "ensureChatExtensionInitialDisabledState() {\n    return;\n" in wb_c)
    record_result("Test 23: patch_workbench patches unminified workbench file", t23_ok, f"rc={p23.returncode}")

    # Test 24: patch_workbench patches mock minified workbench
    t24_dir = os.path.join(temp_root, "t24")
    wb24_dir = os.path.join(t24_dir, "resources", "app", "out", "vs", "workbench")
    os.makedirs(wb24_dir, exist_ok=True)
    wb24_file = os.path.join(wb24_dir, "workbench.desktop.main.js")
    minified_sample = (
        'var x="pad".repeat(35000);'
        'class Foo{'
        'ensureChatExtensionInitialDisabledState(){doSomething();}'
        'bar(e,r){'
        'e.identifier.id.toLowerCase()===this._chatExtensionId&&this.ensureChatExtensionInitialDisabledState(),r=this._getUserEnablementState(e.identifier);'
        'let g=o.context?.value,f=o.requests?.value;if(!g||!f)return;let v=new Io();'
        '}'
        'async showDialog(i){let e=new O,t=this.getButtons(i),o=e.add(new Soe());}'
        '}'
    )
    with open(wb24_file, "w", encoding="utf-8") as f:
        f.write(minified_sample)
    cmd24 = [sys.executable, wb_script, t24_dir, "--skip-installed"]
    p24 = subprocess.run(cmd24, capture_output=True, text=True)
    with open(wb24_file, "r", encoding="utf-8") as f:
        wb24_c = f.read()
    t24_ok = (p24.returncode == 0 and
              'if(e.identifier.id.toLowerCase()==="github.copilot-chat"' in wb24_c and
              'ensureChatExtensionInitialDisabledState(){return;' in wb24_c)
    record_result("Test 24: patch_workbench patches minified workbench file", t24_ok, f"rc={p24.returncode}")

    # Test 25: patch_workbench strips DIAG logs and is idempotent
    diag_sample = minified_sample + 'function dummy(a, t) { for(let x of t)if(x.identifier.value.toLowerCase().includes("copilot"))a.error("[DIAG-OST-COPILOT] found in t: " + x.identifier.value); }'
    with open(wb24_file, "w", encoding="utf-8") as f:
        f.write(diag_sample)
    p25_1 = subprocess.run(cmd24, capture_output=True, text=True)
    with open(wb24_file, "r", encoding="utf-8") as f:
        wb25_c = f.read()
    p25_2 = subprocess.run(cmd24, capture_output=True, text=True)
    t25_ok = (p25_1.returncode == 0 and
              "[DIAG-OST-COPILOT]" not in wb25_c and
              p25_2.returncode == 0 and
              "Already patched" in p25_2.stdout)
    record_result("Test 25: patch_workbench strips DIAG logs and is idempotent", t25_ok, f"rc1={p25_1.returncode}, rc2={p25_2.returncode}")

    # Test 26: NLS menubar table verification and drift protection
    from patch_workbench import validate_nls_tables, EXPECTED_NLS_INDICES
    t26_dir = os.path.join(temp_root, "t26")
    t26_out = os.path.join(t26_dir, "resources", "app", "out")
    os.makedirs(t26_out, exist_ok=True)
    # 26a: Valid table passes
    valid_nls = [""] * 12000
    for idx, s in EXPECTED_NLS_INDICES.items():
        valid_nls[idx] = s
    with open(os.path.join(t26_out, "nls.messages.json"), "w", encoding="utf-8") as f:
        json.dump(valid_nls, f)
    t26a_ok = validate_nls_tables(t26_out)

    # 26b: Shifted table (+6 shift like in the reported bug) fails
    shifted_nls = [""] * 12000
    for idx, s in EXPECTED_NLS_INDICES.items():
        shifted_nls[idx + 6] = s  # offset by +6
    with open(os.path.join(t26_out, "nls.messages.json"), "w", encoding="utf-8") as f:
        json.dump(shifted_nls, f)
    t26b_ok = not validate_nls_tables(t26_out)

    record_result("Test 26: NLS menubar alignment validation and drift rejection", t26a_ok and t26b_ok, f"valid={t26a_ok}, shifted_rejected={t26b_ok}")

finally:
    shutil.rmtree(temp_root, ignore_errors=True)

print("\n============================================================")
print(f"Adversarial Test Suite Results: {passed_tests} PASSED, {failed_tests} FAILED")
print("============================================================")
if failed_tests > 0:
    sys.exit(1)
sys.exit(0)

