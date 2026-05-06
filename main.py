#!/usr/bin/env python3
"""MkDown — 即時預覽 Markdown 編輯器"""
import sys
import os

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QEvent, QTimer

from window import MainWindow


# ── Apple Event handler (macOS file-open via Finder / double-click) ───────────
# QFileOpenEvent is unreliable in PyInstaller bundles.
# Register directly with NSAppleEventManager for kAEOpenDocuments.

_pending_paths = []   # paths received before the window is ready

def _install_apple_event_handler(get_window):
    try:
        from AppKit import NSAppleEventManager
        from Foundation import NSObject
        import struct

        kCoreEventClass   = struct.unpack('>I', b'aevt')[0]
        kAEOpenDocuments  = struct.unpack('>I', b'odoc')[0]
        keyDirectObject   = struct.unpack('>I', b'----')[0]
        typeAEList        = struct.unpack('>I', b'list')[0]
        typeAlias         = struct.unpack('>I', b'alis')[0]
        typeFSRef         = struct.unpack('>I', b'fsrf')[0]

        class _Handler(NSObject):
            def handleOpenDocumentsEvent_withReplyEvent_(self, event, reply):
                try:
                    desc = event.paramDescriptorForKeyword_(keyDirectObject)
                    count = desc.numberOfItems()
                    paths = []
                    for i in range(1, count + 1):
                        item = desc.descriptorAtIndex_(i)
                        url  = item.fileURLValue()
                        if url:
                            paths.append(url.path())
                    if not paths and desc.fileURLValue():
                        paths.append(desc.fileURLValue().path())
                except Exception:
                    return
                win = get_window()
                for p in paths:
                    if win:
                        win.open_path(p)
                    else:
                        _pending_paths.append(p)

        _handler = _Handler.alloc().init()
        mgr = NSAppleEventManager.sharedAppleEventManager()
        mgr.setEventHandler_andSelector_forEventClass_andEventID_(
            _handler,
            'handleOpenDocumentsEvent:withReplyEvent:',
            kCoreEventClass,
            kAEOpenDocuments,
        )
        return _handler   # keep alive
    except Exception as e:
        return None


class MkDownApp(QApplication):
    """QFileOpenEvent fallback (catches events not handled by NSAppleEventManager)."""

    def __init__(self, argv):
        super().__init__(argv)
        self._main_window = None

    def event(self, event):
        if event.type() == QEvent.FileOpen:
            path = event.file()
            if path:
                if self._main_window:
                    self._main_window.open_path(path)
                else:
                    _pending_paths.append(path)
            return True
        return super().event(event)


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = MkDownApp(sys.argv)
    app.setApplicationName('MkDown')
    app.setOrganizationName('mkdown')
    app.setApplicationDisplayName('MkDown')

    window = MainWindow()
    app._main_window = window
    window.show()

    # Install Apple Event handler; pass a lambda so it can reach the window
    _ae_handler = _install_apple_event_handler(lambda: window)

    # Drain any paths that arrived before the window was ready
    def _drain_pending():
        for p in _pending_paths:
            window.open_path(p)
        _pending_paths.clear()

    QTimer.singleShot(0, _drain_pending)

    # CLI invocation: /path/to/MkDown file.md  or  python3 main.py file.md
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        QTimer.singleShot(0, lambda: window.open_path(sys.argv[1]))

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
