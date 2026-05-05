import os
from PyQt5.QtWidgets import (
    QMainWindow, QSplitter, QFileDialog, QMessageBox,
    QLabel, QAction, QActionGroup,
)
from PyQt5.QtCore import Qt, QTimer
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

## 快速鍵

| 功能 | 快速鍵 |
|------|--------|
| 新增 | ⌘N |
| 開啟 | ⌘O |
| 儲存 | ⌘S |
| 另存新檔 | ⌘⇧S |
| 匯出 PDF | ⌘⇧P |
| 匯出 HTML | ⌘⇧H |
| 切換預覽 | ⌘⇧M |
| 放大 | ⌘= |
| 縮小 | ⌘- |
| 重設大小 | ⌘0 |

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
- [ ] 自動儲存（待開發）

---

> 開始輸入，體驗 Markdown 的樂趣！
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._current_file = None
        self._modified = False
        self._theme_mgr = ThemeManager(self)
        self._setup_ui()
        self._setup_menu()
        self._setup_statusbar()
        self.resize(1280, 800)

        # Apply initial theme before setting text
        self._on_theme_changed(self._theme_mgr.effective)
        self._theme_mgr.changed.connect(self._on_theme_changed)

        self.editor.set_text(_WELCOME)
        self._modified = False
        self._update_title()

    # ── UI setup ──────────────────────────────────────────────────────────────

    def _setup_ui(self):
        self._splitter = QSplitter(Qt.Horizontal)
        self.editor = EditorWidget()
        self.preview = PreviewWidget()
        self._splitter.addWidget(self.editor)
        self._splitter.addWidget(self.preview)
        self._splitter.setSizes([520, 760])
        self._splitter.setHandleWidth(1)
        self.setCentralWidget(self._splitter)

        self._timer = QTimer(self, singleShot=True, interval=250)
        self._timer.timeout.connect(self._do_update_preview)
        self.editor.textChanged.connect(self._on_change)

    def _setup_menu(self):
        mb = self.menuBar()

        # ── 檔案 ──────────────────────────────────────────────────────────────
        fm = mb.addMenu('檔案(&F)')
        self._act(fm, '新增',       QKeySequence.New,       self.new_file)
        self._act(fm, '開啟…', QKeySequence.Open,      self.open_file)
        fm.addSeparator()
        self._act(fm, '儲存',       QKeySequence.Save,      self.save_file)
        self._act(fm, '另存新檔…', QKeySequence.SaveAs, self.save_file_as)
        fm.addSeparator()
        self._act(fm, '匯出 PDF…',  'Ctrl+Shift+P', self.export_pdf)
        self._act(fm, '匯出 HTML…', 'Ctrl+Shift+H', self.export_html)

        # ── 編輯 ──────────────────────────────────────────────────────────────
        em = mb.addMenu('編輯(&E)')
        self._act(em, '復原',   QKeySequence.Undo,      self.editor.undo)
        self._act(em, '取消復原', QKeySequence.Redo,    self.editor.redo)
        em.addSeparator()
        self._act(em, '剪下', QKeySequence.Cut,         self.editor.cut)
        self._act(em, '複製', QKeySequence.Copy,        self.editor.copy)
        self._act(em, '貼上', QKeySequence.Paste,       self.editor.paste)
        em.addSeparator()
        self._act(em, '全選', QKeySequence.SelectAll,   self.editor.selectAll)

        # ── 檢視 ──────────────────────────────────────────────────────────────
        vm = mb.addMenu('檢視(&V)')
        self._act(vm, '切換預覽', 'Ctrl+Shift+M', self._toggle_preview)
        vm.addSeparator()
        self._act(vm, '放大',   'Ctrl+=',             self._zoom_in)
        self._act(vm, '縮小',   QKeySequence.ZoomOut, self._zoom_out)
        self._act(vm, '重設大小', 'Ctrl+0',           self._zoom_reset)
        vm.addSeparator()

        # 外觀子選單
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
        self._counter = QLabel('')
        sb.addWidget(self._status_msg)
        sb.addPermanentWidget(self._counter)

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _set_theme(self, mode: str):
        self._theme_mgr.set_mode(mode)
        # If mode is same as current effective, force a refresh
        self._on_theme_changed(self._theme_mgr.effective)

    def _on_theme_changed(self, effective: str):
        colors = self._theme_mgr.colors
        self.editor.apply_theme(colors)
        self.preview.apply_theme(colors)
        # Status bar colour
        sb_bg = colors['statusbar_bg']
        sb_fg = colors['statusbar_fg']
        self.statusBar().setStyleSheet(
            f'QStatusBar{{background:{sb_bg};color:{sb_fg};border-top:1px solid {colors["border"]};}}'
        )
        # Splitter handle
        border = colors['border']
        self._splitter.setStyleSheet(
            f'QSplitter::handle{{background:{border};}}'
        )

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_change(self):
        self._modified = True
        self._update_title()
        self._timer.start()
        self._update_counter()

    def _do_update_preview(self):
        self.preview.render(self.editor.get_text())

    def _update_title(self):
        name = os.path.basename(self._current_file) if self._current_file else '未命名'
        dot = '• ' if self._modified else ''
        self.setWindowTitle(f'{dot}{name} — MkDown')

    def _update_counter(self):
        t = self.editor.get_text()
        lines = t.count('\n') + (1 if t else 0)
        self._counter.setText(f'行：{lines}　字元：{len(t)}')

    def _toggle_preview(self):
        self.preview.setVisible(not self.preview.isVisible())

    def _zoom_in(self):
        self.preview.adjust_zoom(2)

    def _zoom_out(self):
        self.preview.adjust_zoom(-2)

    def _zoom_reset(self):
        self.preview.adjust_zoom(0)

    def closeEvent(self, event):
        event.accept() if self._ask_discard() else event.ignore()

    # ── File operations ───────────────────────────────────────────────────────

    def _ask_discard(self) -> bool:
        if not self._modified:
            return True
        btn = QMessageBox.question(
            self, '未儲存的變更', '文件有未儲存的變更，要儲存嗎？',
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
        )
        if btn == QMessageBox.Save:
            return self.save_file()
        return btn == QMessageBox.Discard

    def new_file(self):
        if not self._ask_discard():
            return
        self.editor.set_text('')
        self._current_file = None
        self._modified = False
        self._update_title()
        self._status_msg.setText('已建立新文件')

    def open_file(self):
        if not self._ask_discard():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, '開啟 Markdown 文件', '',
            'Markdown 文件 (*.md *.markdown *.txt);;所有檔案 (*)',
        )
        if not path:
            return
        try:
            with open(path, encoding='utf-8') as f:
                self.editor.set_text(f.read())
            self._current_file = path
            self._modified = False
            self._update_title()
            self._do_update_preview()
            self._status_msg.setText(f'已開啟：{os.path.basename(path)}')
        except Exception as e:
            QMessageBox.critical(self, '開啟失敗', str(e))

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
            self._update_title()
            self._status_msg.setText(f'已儲存：{os.path.basename(path)}')
            return True
        except Exception as e:
            QMessageBox.critical(self, '儲存失敗', str(e))
            return False

    def export_pdf(self):
        default = (os.path.splitext(self._current_file)[0]
                   if self._current_file else 'document') + '.pdf'
        path, _ = QFileDialog.getSaveFileName(
            self, '匯出 PDF', default, 'PDF 文件 (*.pdf)',
        )
        if not path:
            return
        if not path.lower().endswith('.pdf'):
            path += '.pdf'
        self._status_msg.setText('正在產生 PDF…')
        self.preview.export_pdf(path, self._on_pdf_done)

    def _on_pdf_done(self, ok: bool):
        self._status_msg.setText('PDF 匯出成功' if ok else 'PDF 匯出失敗')

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
            self._status_msg.setText(f'HTML 已匯出：{os.path.basename(path)}')
        except Exception as e:
            QMessageBox.critical(self, '匯出失敗', str(e))
