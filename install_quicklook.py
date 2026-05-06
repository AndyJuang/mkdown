#!/usr/bin/env python3
"""
建立並安裝 MkDown Quick Look Preview Extension，同時設定 .md 的預設開啟程式。

技術說明：
  macOS 26 已完全移除舊的 C-based .qlgenerator API。
  本腳本改用現代 Swift QLPreviewingController + QLPreviewReply，
  編譯為 App Extension (.appex) 後嵌入 MkDown.app。

需求：
  - Xcode Command Line Tools (swiftc、codesign)
  - 初次執行需要網路（下載 marked.js）
  - MkDown.app 需已安裝到 /Applications/

執行方式：
  python3 install_quicklook.py
"""
import os, sys, shutil, subprocess, urllib.request, tempfile, ctypes

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
QL_SRC        = os.path.join(SCRIPT_DIR, 'quicklook')
APPEX_NAME    = 'MkDownQuickLook.appex'
APP_PATH      = '/Applications/MkDown.app'
PLUGINS_DIR   = os.path.join(APP_PATH, 'Contents', 'PlugIns')
APPEX_DEST    = os.path.join(PLUGINS_DIR, APPEX_NAME)
APP_BUNDLE_ID = 'com.mkdown.app'

MARKED_CACHE  = os.path.join(QL_SRC, 'marked.min.js')
MARKED_URL    = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js'

# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(cmd, check=False, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, check=check, **kw)

def _require(tool):
    if not shutil.which(tool):
        print(f'錯誤：找不到 {tool}，請先安裝 Xcode Command Line Tools：')
        print('  xcode-select --install')
        sys.exit(1)

def _get_marked_js() -> bytes:
    if os.path.exists(MARKED_CACHE):
        print(f'  marked.js: 使用快取')
        return open(MARKED_CACHE, 'rb').read()
    print(f'  marked.js: 下載中 {MARKED_URL} ...')
    try:
        with urllib.request.urlopen(MARKED_URL, timeout=15) as r:
            data = r.read()
        with open(MARKED_CACHE, 'wb') as f:
            f.write(data)
        print(f'  已儲存到 {MARKED_CACHE}')
        return data
    except Exception as e:
        print(f'  警告：下載失敗（{e}），Quick Look 將以純文字顯示')
        return b''

def _sdk_path() -> str:
    r = _run(['xcrun', '--show-sdk-path'])
    return r.stdout.strip()

# ── Build .appex ──────────────────────────────────────────────────────────────

def build_appex(build_dir: str) -> str:
    appex     = os.path.join(build_dir, APPEX_NAME)
    macos_dir = os.path.join(appex, 'Contents', 'MacOS')
    res_dir   = os.path.join(appex, 'Contents', 'Resources')
    os.makedirs(macos_dir, exist_ok=True)
    os.makedirs(res_dir,   exist_ok=True)

    # Info.plist
    shutil.copy(os.path.join(QL_SRC, 'Info.plist'),
                os.path.join(appex, 'Contents', 'Info.plist'))

    # marked.js
    marked = _get_marked_js()
    if marked:
        with open(os.path.join(res_dir, 'marked.min.js'), 'wb') as f:
            f.write(marked)

    # Compile Swift → Mach-O bundle
    exe = os.path.join(macos_dir, 'MkDownQuickLook')
    sdk = _sdk_path()
    swift_src = os.path.join(QL_SRC, 'PreviewViewController.swift')

    print('  swiftc 編譯中...')
    r = _run([
        'swiftc',
        '-module-name', 'MkDownQuickLook',
        '-parse-as-library',
        '-target', 'arm64-apple-macos13.0',
        '-sdk', sdk,
        '-framework', 'QuickLookUI',
        '-framework', 'AppKit',
        '-framework', 'Foundation',
        '-framework', 'UniformTypeIdentifiers',
        '-Xlinker', '-bundle',
        '-o', exe,
        swift_src,
    ])
    if r.returncode != 0:
        print('編譯錯誤：')
        print(r.stderr)
        sys.exit(1)
    print(f'  已編譯：{exe}')

    # Ad-hoc code sign
    _run(['codesign', '--force', '--sign', '-', '--timestamp=none', appex])
    print('  已簽名（ad-hoc）')

    return appex

# ── Install into MkDown.app ───────────────────────────────────────────────────

def install_appex(appex_path: str):
    if not os.path.isdir(APP_PATH):
        print(f'錯誤：找不到 {APP_PATH}')
        print('  請先將 MkDown.app 拖曳到 /Applications/ 再執行此腳本。')
        sys.exit(1)

    os.makedirs(PLUGINS_DIR, exist_ok=True)

    if os.path.exists(APPEX_DEST):
        shutil.rmtree(APPEX_DEST)
    shutil.copytree(appex_path, APPEX_DEST)
    print(f'  已安裝至 {APPEX_DEST}')

    # Re-sign the host app so the embedded extension is accepted
    _run(['codesign', '--force', '--sign', '-', '--timestamp=none',
          '--deep', APP_PATH])
    print(f'  MkDown.app 已重新簽名')

# ── Register & set as default ─────────────────────────────────────────────────

def _cfstr(text: str):
    cf = ctypes.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
    cf.CFStringCreateWithCString.restype  = ctypes.c_void_p
    cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
    return cf.CFStringCreateWithCString(None, text.encode('utf-8'), 0x08000100)

def set_default_app():
    # Force LaunchServices to pick up the updated app
    lsreg = ('/System/Library/Frameworks/CoreServices.framework'
             '/Versions/A/Frameworks/LaunchServices.framework'
             '/Versions/A/Support/lsregister')
    if os.path.exists(lsreg):
        _run([lsreg, '-f', APP_PATH])
        print(f'  已向 LaunchServices 重新登錄 {APP_PATH}')

    try:
        cs = ctypes.CDLL('/System/Library/Frameworks/CoreServices.framework/CoreServices')
        cs.LSSetDefaultRoleHandlerForContentType.restype  = ctypes.c_int32
        cs.LSSetDefaultRoleHandlerForContentType.argtypes = [
            ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p,
        ]
        for uti in ['net.daringfireball.markdown', 'public.markdown']:
            ret = cs.LSSetDefaultRoleHandlerForContentType(
                _cfstr(uti), 0xFFFFFFFF, _cfstr(APP_BUNDLE_ID)
            )
            print(f'  {uti}: {"✓" if ret == 0 else f"error {ret}"}')
    except Exception as e:
        print(f'  警告：無法自動設定預設程式（{e}）')
        print('  請手動：Finder 右鍵 .md 檔 → 打開方式 → MkDown → 「一律以此方式打開」')

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print('=== MkDown Quick Look 安裝程式 ===\n')
    _require('swiftc')
    _require('codesign')

    print('【1/3】 編譯 Quick Look Preview Extension...')
    with tempfile.TemporaryDirectory() as tmp:
        appex = build_appex(tmp)
        print('\n【2/3】 安裝 Extension 到 MkDown.app...')
        install_appex(appex)

    print('\n【3/3】 設定 .md 預設開啟程式...')
    set_default_app()

    print('\n✓ 完成！')
    print('  雙擊 .md 檔將以 MkDown 開啟。')
    print()
    print('⚠️  Quick Look 預覽說明：')
    print('  Quick Look Preview Extension 需要 Apple Developer Team ID 才能被')
    print('  macOS 擴充功能系統（pluginkit）接受。使用 ad-hoc 簽名的版本無法')
    print('  自動登錄。取得 Apple Developer Program 資格後，以 Developer ID')
    print('  重新簽名即可啟用：')
    print('    codesign --force --sign "Developer ID Application: ..." \\')
    print('      --entitlements ql_entitlements.plist \\')
    print('      /Applications/MkDown.app/Contents/PlugIns/MkDownQuickLook.appex')
    print()
    print('  目前 .md 檔案在 Finder 仍會顯示純文字的 Quick Look 預覽（系統內建）。')

if __name__ == '__main__':
    main()
