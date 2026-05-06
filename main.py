#!/usr/bin/env python3
"""MkDown — 即時預覽 Markdown 編輯器"""
import sys
import os

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QEvent

from window import MainWindow


class MkDownApp(QApplication):
    """Subclass to intercept macOS file-open Apple Events (QFileOpenEvent)."""

    def __init__(self, argv):
        super().__init__(argv)
        self._main_window = None

    def event(self, event):
        # macOS sends QFileOpenEvent when the user double-clicks a .md file
        # or drags it onto the Dock icon — sys.argv is NOT set in this case.
        if event.type() == QEvent.FileOpen:
            path = event.file()
            if path and self._main_window:
                self._main_window.open_path(path)
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
    app._main_window = window   # allow event() to reach the window
    window.show()

    # CLI invocation: python3 main.py file.md
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        window.open_path(sys.argv[1])

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
