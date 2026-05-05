#!/usr/bin/env python3
"""MkDown — 即時預覽 Markdown 編輯器"""
import sys
import os

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from window import MainWindow


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    app.setApplicationName('MkDown')
    app.setOrganizationName('mkdown')
    app.setApplicationDisplayName('MkDown')

    window = MainWindow()
    window.show()

    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        try:
            with open(sys.argv[1], encoding='utf-8') as f:
                content = f.read()
            window.editor.set_text(content)
            window._current_file = sys.argv[1]
            window._modified = False
            window._update_title()
            window._do_update_preview()
        except Exception:
            pass

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
