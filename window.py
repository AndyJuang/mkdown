import os
from PyQt5.QtWidgets import (
    QMainWindow, QSplitter, QFileDialog, QMessageBox,
    QLabel, QAction, QActionGroup, QTabWidget, QWidget,
    QVBoxLayout, QShortcut,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QKeySequence

from editor import EditorWidget
from preview import PreviewWidget
from theme import ThemeManager, AUTO, LIGHT, DARK

_WELCOME = """\
# 歡迎使用 MkDown

在左側輸入 Markdown 語法，右側即時呈現渲染結果。

## 功能

- **即時預覽** — 左側編輯，右側同步渲染
- **深色／淺色主題** — 檢視選單 → 外觀，或跟隨系統
- **兩指縮放** — 在預覽區域用觸控板兩指捏合縮放
- **匯出 PDF／HTML** — 完整版面輸出
- **GFM 支援** — 表格、任務清單、程式碼高亮
- **分頁** — ⌘T 新增分頁，⌘W 關閉，⌘1–⌘9 切換
- **拖曳開啟** — 將 .md 檔案直接拖入視窗

## 快速鍵

| 功能 | 快速鍵 |
|------|--------|
| 新增分頁 | ⌘T |
| 關閉分頁 | ⌘W |
| 開啟 | ⌘O |
| 儲存 | ⌘S |
| 另存新檔 | ⌘⇧S |
| 匯出 PDF | ⌘⇧P |
| 匯出 HTML | ⌘⇧H |
| 切換預覽 | ⌘⇧M |
| 放大 | ⌘= |
| 縮小 | ⌘- |
| 重設大小 | ⌘0 |
| 切換分頁 | ⌘1–⌘9 |
| 前一個分頁 | ⌘⇧[ |
| 下一個分頁 | ⌘⇧] |

## 程式碼高亮範例

```python
def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
```

## 表格

| 語言 | 類型 | 特色 |
|------|------|------|
| Python | 直譯 | 簡潔易讀 |
| Rust | 編譯 | 高效安全 |
| Go | 編譯 | 並發友善 |

## 任務清單

- [x] 即時預覽
- [x] Markdown 語法高亮
- [x] 深色／淺色主題
- [x] 兩指縮放
- [x] 分頁支援
- [x] 拖曳開啟

---

> 開始輸入，體驗 Markdown 的樂趣！
"""


# ── 單一分頁（編輯器 + 預覽 + 檔案狀態） ──────────────────────────────────────

class TabPane(QWidget):
    title_changed  = pyqtSignal(str)   # tab 標題（含修改標記）
    status_changed = pyqtSignal(str)   # 狀態列訊息
    counter_changed = pyqtSignal(str)  # 行／字元計數

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_file = None
        self._modified = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._splitter = QSplitter(Qt.Horizontal)
        self.editor  = EditorWidget()
        self.preview = PreviewWidget()
        self._splitter.addWidget(self.editor)
        self._splitter.addWidget(self.preview)
        self._splitter.setSizes([520, 760])
        self._splitter.setHandleWidth(1)
        layout.addWidget(self._splitter)

        self._timer = QTimer(self, singleShot=True, interval=250)
        self._timer.timeout.connect(self._do_update_preview)
        self.editor.textChanged.connect(self._on_change)

    # ── 屬性 ──────────────────────────────────────────────────────────────────

    def current_file(self):
        return self._current_file

    def is_modified(self):
        return self._modified

    def get_tab_title(self) -> str:
        name = os.path.basename(self._current_file) if self._current_file else '未命名'
        return ('• ' if self._modified else '') + name

    # ── 主題 ──────────────────────────────────────────────────────────────────

    def apply_theme(self, colors: dict):
        self.editor.apply_theme(colors)
        self.preview.apply_theme(colors)
        border = colors['border']
        self._splitter.setStyleSheet(
            f'QSplitter::handle{{background:{border};}}'
        )

    # ── 內部 ──────────────────────────────────────────────────────────────────

    def _on_change(self):
        self._modified = True
        self._emit_title()
        self._timer.start()
        t = self.editor.get_text()
        lines = t.count('\n') + (1 if t else 0)
        self.counter_changed.emit(f'行：{lines}　字元：{len(t)}')

    def _emit_title(self):
        self.title_changed.emit(self.get_tab_title())

    def _do_update_preview(self):
        self.preview.render(self.editor.get_text())

    # ── 公開 API ──────────────────────────────────────────────────────────────

    def open_path(self, path: str) -> bool:
        try:
            with open(path, encoding='utf-8') as f:
                self.editor.set_text(f.read())
            self._current_file = path
            self._modified = False
            self._emit_title()
            self._do_update_preview()
            self.status_changed.emit(f'已開啟：{os.path.basename(path)}')
            return True
        except Exception as e:
            QMessageBox.critical(self, '開啟失敗', str(e))
            return False

    def ask_discard(self) -> bool:
        if not self._modified:
            return True
        msg = QMessageBox(self)
        msg.setWindowTitle('未儲存的變更')
        msg.setText('文件有未儲存的變更，要儲存嗎？')
        msg.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        msg.button(QMessageBox.Save).setShortcut(QKeySequence('Ctrl+S'))
        msg.button(QMessageBox.Discard).setShortcut(QKeySequence('Ctrl+D'))
        msg.button(QMessageBox.Cancel).setShortcut(QKeySequence('Escape'))
        result = msg.exec_()
        if result == QMessageBox.Save:
            return self.save_file()
        return result == QMessageBox.Discard

    def save_file(self) -> bool:
        if self._current_file:
            return self._write(self._current_file)
        return self.save_file_as()

    def save_file_as(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(
            self, '另存新檔', self._current_file or 'untitled.md',
            'Markdown 文件 (*.md);;所有檔案 (*)',
        )
        if not path:
            return False
        if not os.path.splitext(path)[1]:
            path += '.md'
        return self._write(path)

    def _write(self, path: str) -> bool:
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.editor.get_text())
            self._current_file = path
            self._modified = False
            self._emit_title()
            self.status_changed.emit(f'已儲存：{os.path.basename(path)}')
            return True
        except Exception as e:
            QMessageBox.critical(self, '儲存失敗', str(e))
            return False

    def export_pdf(self, on_done=None):
        default = (os.path.splitext(self._current_file)[0]
                   if self._current_file else 'document') + '.pdf'
        path, _ = QFileDialog.getSaveFileName(
            self, '匯出 PDF', default, 'PDF 文件 (*.pdf)',
        )
        if not path:
            return
        if not path.lower().endswith('.pdf'):
            path += '.pdf'
        self.preview.export_pdf(path, on_done)

    def export_html(self):
        default = (os.path.splitext(self._current_file)[0]
                   if self._current_file else 'document') + '.html'
        path, _ = QFileDialog.getSaveFileName(
            self, '匯出 HTML', default, 'HTML 文件 (*.html)',
        )
        if not path:
            return
        if not path.lower().endswith('.html'):
            path += '.html'
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.preview.get_html())
            self.status_changed.emit(f'HTML 已匯出：{os.path.basename(path)}')
        except Exception as e:
            QMessageBox.critical(self, '匯出失敗', str(e))


# ── 主視窗 ────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._theme_mgr = ThemeManager(self)
        self._setup_ui()
        self._setup_menu()
        self._setup_statusbar()
        self._setup_tab_shortcuts()
        self.resize(1280, 800)

        self._on_theme_changed(self._theme_mgr.effective)
        self._theme_mgr.changed.connect(self._on_theme_changed)

        self._new_tab(welcome=True)
        self.setAcceptDrops(True)

    # ── UI 初始化 ─────────────────────────────────────────────────────────────

    def _setup_ui(self):
        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(True)
        self._tabs.setMovable(True)
        self._tabs.tabCloseRequested.connect(self._close_tab)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self._tabs)

    def _setup_menu(self):
        mb = self.menuBar()

        # ── 檔案 ──────────────────────────────────────────────────────────────
        fm = mb.addMenu('檔案(&F)')
        self._act(fm, '新增分頁',     'Ctrl+T',            self.new_file)
        self._act(fm, '開啟…',        QKeySequence.Open,   self.open_file)
        fm.addSeparator()
        self._act(fm, '儲存',         QKeySequence.Save,   self._save)
        self._act(fm, '另存新檔…',    QKeySequence.SaveAs, self._save_as)
        fm.addSeparator()
        self._act(fm, '匯出 PDF…',   'Ctrl+Shift+P',       self._export_pdf)
        self._act(fm, '匯出 HTML…',  'Ctrl+Shift+H',       self._export_html)
        fm.addSeparator()
        self._act(fm, '關閉分頁',     QKeySequence.Close,  self._close_current_tab)

        # ── 編輯 ──────────────────────────────────────────────────────────────
        em = mb.addMenu('編輯(&E)')
        self._act(em, '復原',     QKeySequence.Undo,      lambda: self._pane().editor.undo())
        self._act(em, '取消復原', QKeySequence.Redo,      lambda: self._pane().editor.redo())
        em.addSeparator()
        self._act(em, '剪下',     QKeySequence.Cut,       lambda: self._pane().editor.cut())
        self._act(em, '複製',     QKeySequence.Copy,      lambda: self._pane().editor.copy())
        self._act(em, '貼上',     QKeySequence.Paste,     lambda: self._pane().editor.paste())
        em.addSeparator()
        self._act(em, '全選',     QKeySequence.SelectAll, lambda: self._pane().editor.selectAll())

        # ── 檢視 ──────────────────────────────────────────────────────────────
        vm = mb.addMenu('檢視(&V)')
        self._act(vm, '切換預覽', 'Ctrl+Shift+M', lambda: self._pane().preview.setVisible(
            not self._pane().preview.isVisible()))
        vm.addSeparator()
        self._act(vm, '放大',     'Ctrl+=',             lambda: self._pane().preview.adjust_zoom(2))
        self._act(vm, '縮小',     QKeySequence.ZoomOut, lambda: self._pane().preview.adjust_zoom(-2))
        self._act(vm, '重設大小', 'Ctrl+0',             lambda: self._pane().preview.adjust_zoom(0))
        vm.addSeparator()

        appear_menu = vm.addMenu('外觀')
        grp = QActionGroup(self)
        grp.setExclusive(True)
        self._theme_acts = {}
        for key, label in [(AUTO, '跟隨系統'), (LIGHT, '淺色'), (DARK, '深色')]:
            a = QAction(label, self, checkable=True)
            a.setChecked(key == AUTO)
            a.triggered.connect(lambda checked, k=key: self._set_theme(k))
            grp.addAction(a)
            appear_menu.addAction(a)
            self._theme_acts[key] = a

    def _act(self, menu, label, shortcut, slot):
        a = QAction(label, self)
        a.setShortcut(shortcut)
        a.triggered.connect(slot)
        menu.addAction(a)

    def _setup_statusbar(self):
        sb = self.statusBar()
        self._status_msg = QLabel('就緒')
        self._counter    = QLabel('')
        sb.addWidget(self._status_msg)
        sb.addPermanentWidget(self._counter)

    def _setup_tab_shortcuts(self):
        for i in range(1, 10):
            sc = QShortcut(QKeySequence(f'Ctrl+{i}'), self)
            sc.activated.connect(lambda n=i: self._tabs.setCurrentIndex(n - 1))

        prev_sc = QShortcut(QKeySequence('Ctrl+Shift+['), self)
        prev_sc.activated.connect(self._tab_prev)

        next_sc = QShortcut(QKeySequence('Ctrl+Shift+]'), self)
        next_sc.activated.connect(self._tab_next)

    def _tab_prev(self):
        count = self._tabs.count()
        if count > 1:
            self._tabs.setCurrentIndex((self._tabs.currentIndex() - 1) % count)

    def _tab_next(self):
        count = self._tabs.count()
        if count > 1:
            self._tabs.setCurrentIndex((self._tabs.currentIndex() + 1) % count)

    # ── 分頁管理 ──────────────────────────────────────────────────────────────

    def _new_tab(self, welcome=False) -> TabPane:
        pane = TabPane()
        pane.apply_theme(self._theme_mgr.colors)

        pane.title_changed.connect(
            lambda title, p=pane: self._on_pane_title(p, title)
        )
        pane.status_changed.connect(
            lambda text, p=pane: self._status_msg.setText(text)
            if p is self._pane() else None
        )
        pane.counter_changed.connect(
            lambda text, p=pane: self._counter.setText(text)
            if p is self._pane() else None
        )

        idx = self._tabs.addTab(pane, '未命名')
        self._tabs.setCurrentIndex(idx)

        if welcome:
            pane.editor.set_text(_WELCOME)
            pane._modified = False
            pane._emit_title()

        return pane

    def _pane(self) -> TabPane:
        return self._tabs.currentWidget()

    def _on_pane_title(self, pane: TabPane, title: str):
        idx = self._tabs.indexOf(pane)
        if idx >= 0:
            self._tabs.setTabText(idx, title)
        if pane is self._pane():
            self._update_window_title()

    def _on_tab_changed(self, idx: int):
        self._update_window_title()
        pane = self._tabs.widget(idx)
        if pane:
            t = pane.editor.get_text()
            lines = t.count('\n') + (1 if t else 0)
            self._counter.setText(f'行：{lines}　字元：{len(t)}')

    def _update_window_title(self):
        pane = self._pane()
        if pane:
            name = os.path.basename(pane.current_file()) if pane.current_file() else '未命名'
            dot  = '• ' if pane.is_modified() else ''
            self.setWindowTitle(f'{dot}{name} — MkDown')
        else:
            self.setWindowTitle('MkDown')

    def _close_tab(self, idx: int):
        pane = self._tabs.widget(idx)
        if not pane or not pane.ask_discard():
            return
        self._tabs.removeTab(idx)
        if self._tabs.count() == 0:
            self.close()

    def _close_current_tab(self):
        idx = self._tabs.currentIndex()
        if idx >= 0:
            self._close_tab(idx)

    # ── 拖曳開啟 ──────────────────────────────────────────────────────────────

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls()
        if any(u.toLocalFile().lower().endswith(('.md', '.markdown', '.txt'))
               for u in urls):
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(('.md', '.markdown', '.txt')):
                self.open_path(path)
        event.acceptProposedAction()

    # ── 主題 ─────────────────────────────────────────────────────────────────

    def _set_theme(self, mode: str):
        self._theme_mgr.set_mode(mode)
        self._on_theme_changed(self._theme_mgr.effective)

    def _on_theme_changed(self, effective: str):
        colors = self._theme_mgr.colors
        for i in range(self._tabs.count()):
            pane = self._tabs.widget(i)
            if pane:
                pane.apply_theme(colors)
        sb_bg = colors['statusbar_bg']
        sb_fg = colors['statusbar_fg']
        self.statusBar().setStyleSheet(
            f'QStatusBar{{background:{sb_bg};color:{sb_fg};'
            f'border-top:1px solid {colors["border"]};}}'
        )

    # ── 視窗關閉 ──────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        for i in range(self._tabs.count()):
            pane = self._tabs.widget(i)
            if pane and not pane.ask_discard():
                event.ignore()
                return
        event.accept()

    # ── 檔案操作（代理到當前分頁） ────────────────────────────────────────────

    def new_file(self):
        self._new_tab()

    def open_path(self, path: str):
        """從 CLI、Apple Event 或拖曳開啟檔案。若已開啟則切換至該分頁。"""
        abs_path = os.path.abspath(path)
        for i in range(self._tabs.count()):
            pane = self._tabs.widget(i)
            if pane and pane.current_file() and os.path.abspath(pane.current_file()) == abs_path:
                self._tabs.setCurrentIndex(i)
                return
        pane = self._new_tab()
        pane.open_path(path)

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, '開啟 Markdown 文件', '',
            'Markdown 文件 (*.md *.markdown *.txt);;所有檔案 (*)',
        )
        if path:
            self.open_path(path)

    def _save(self):
        pane = self._pane()
        if pane:
            pane.save_file()

    def _save_as(self):
        pane = self._pane()
        if pane:
            pane.save_file_as()

    def _export_pdf(self):
        pane = self._pane()
        if pane:
            self._status_msg.setText('正在產生 PDF…')
            pane.export_pdf(
                on_done=lambda ok: self._status_msg.setText(
                    'PDF 匯出成功' if ok else 'PDF 匯出失敗'
                )
            )

    def _export_html(self):
        pane = self._pane()
        if pane:
            pane.export_html()
