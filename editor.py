from PyQt5.QtWidgets import QWidget, QPlainTextEdit, QTextEdit, QVBoxLayout
from PyQt5.QtCore import Qt, QRect, QSize, QEvent, pyqtSignal
from PyQt5.QtGui import (
    QFont, QPainter, QColor, QTextFormat, QFontMetrics
)
from PyQt5.QtWidgets import QPinchGesture
from highlighter import MarkdownHighlighter


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self._editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._line_area = LineNumberArea(self)
        self._base_font_size = 13
        self._zoom_size = 13
        # Default light colours (overridden by apply_theme)
        self._lineno_bg = QColor('#f6f8fa')
        self._lineno_fg = QColor('#8a9097')
        self._cur_line_color = QColor('#f6f8fa')

        self.blockCountChanged.connect(self._update_line_area_width)
        self.updateRequest.connect(self._update_line_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)

        self.grabGesture(Qt.PinchGesture)
        self._update_line_area_width(0)
        self._highlight_current_line()

    # ── Pinch-to-zoom ─────────────────────────────────────────────────────────

    def event(self, e):
        if e.type() == QEvent.Gesture:
            g = e.gesture(Qt.PinchGesture)
            if g:
                self._apply_pinch(g.scaleFactor())
                return True
        return super().event(e)

    def _apply_pinch(self, scale: float):
        new_size = max(8, min(36, self._zoom_size * scale))
        self._zoom_size = new_size
        f = self.font()
        f.setPointSizeF(new_size)
        self.setFont(f)
        tab_w = QFontMetrics(f).horizontalAdvance(' ') * 4
        self.setTabStopDistance(tab_w)
        self._update_line_area_width(0)

    def reset_zoom(self):
        self._apply_pinch(self._base_font_size / self._zoom_size)

    # ── Line numbers ──────────────────────────────────────────────────────────

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        return 8 + self.fontMetrics().horizontalAdvance('9') * (digits + 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_area.setGeometry(
            QRect(cr.left(), cr.top(),
                  self.line_number_area_width(), cr.height())
        )

    def _update_line_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_area(self, rect, dy):
        if dy:
            self._line_area.scroll(0, dy)
        else:
            self._line_area.update(0, rect.y(), self._line_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_area_width(0)

    def _highlight_current_line(self):
        sel = QTextEdit.ExtraSelection()
        sel.format.setBackground(self._cur_line_color)
        sel.format.setProperty(QTextFormat.FullWidthSelection, True)
        sel.cursor = self.textCursor()
        sel.cursor.clearSelection()
        self.setExtraSelections([sel] if not self.isReadOnly() else [])

    def line_number_area_paint_event(self, event):
        painter = QPainter(self._line_area)
        painter.fillRect(event.rect(), self._lineno_bg)

        block = self.firstVisibleBlock()
        num = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(self._lineno_fg)
                painter.setFont(self.font())
                painter.drawText(
                    0, top,
                    self._line_area.width() - 4, self.fontMetrics().height(),
                    Qt.AlignRight, str(num + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            num += 1

    # ── Theme ─────────────────────────────────────────────────────────────────

    def apply_theme(self, colors: dict):
        bg = colors['editor_bg']
        fg = colors['editor_fg']
        sel = colors['editor_sel_bg']
        self._lineno_bg = QColor(colors['lineno_bg'])
        self._lineno_fg = QColor(colors['lineno_fg'])
        self._cur_line_color = QColor(colors['cur_line_bg'])
        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {bg};
                color: {fg};
                border: none;
                padding: 8px;
                selection-background-color: {sel};
            }}
        """)
        self._highlight_current_line()
        self._line_area.update()


class EditorWidget(QWidget):
    textChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._editor = CodeEditor()
        self._editor.setLineWrapMode(QPlainTextEdit.WidgetWidth)

        font = QFont()
        font.setFamilies(['Menlo', 'Monaco', 'Courier New'])
        font.setFixedPitch(True)
        font.setPointSize(13)
        self._editor.setFont(font)
        tab_stop = QFontMetrics(font).horizontalAdvance(' ') * 4
        self._editor.setTabStopDistance(tab_stop)

        self._highlighter = MarkdownHighlighter(self._editor.document())
        self._editor.textChanged.connect(self.textChanged)

        layout.addWidget(self._editor)

    # ── Public API ────────────────────────────────────────────────────────────

    def get_text(self) -> str:
        return self._editor.toPlainText()

    def set_text(self, text: str):
        self._editor.setPlainText(text)

    def apply_theme(self, colors: dict):
        self._editor.apply_theme(colors)
        is_dark = colors['editor_bg'] != '#ffffff'
        self._highlighter.set_dark(is_dark)

    def reset_zoom(self):
        self._editor.reset_zoom()

    def undo(self):       self._editor.undo()
    def redo(self):       self._editor.redo()
    def cut(self):        self._editor.cut()
    def copy(self):       self._editor.copy()
    def paste(self):      self._editor.paste()
    def selectAll(self):  self._editor.selectAll()
