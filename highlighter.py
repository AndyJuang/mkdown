import re
from PyQt5.QtCore import QRegularExpression
from PyQt5.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont
)

# ── Per-theme colour palettes ─────────────────────────────────────────────────

_LIGHT = {
    'heading':   '#005cc5',
    'normal':    '#24292e',
    'code':      '#c45508',
    'fence':     '#6f42c1',
    'bq':        '#6a737d',
    'list':      '#005cc5',
    'link':      '#0366d6',
    'hr':        '#d1d5da',
    'html':      '#22863a',
    'fence_body':'#586069',
}

_DARK = {
    'heading':   '#569cd6',
    'normal':    '#d4d4d4',
    'code':      '#ce9178',
    'fence':     '#c586c0',
    'bq':        '#6a9955',
    'list':      '#569cd6',
    'link':      '#4ec9b0',
    'hr':        '#4a4a4a',
    'html':      '#4ec9b0',
    'fence_body':'#858585',
}


def _fmt(color=None, bold=False, italic=False):
    f = QTextCharFormat()
    if color:
        f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Bold)
    if italic:
        f.setFontItalic(True)
    return f


class MarkdownHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self._is_dark = False
        self._palette = _LIGHT
        self._build_rules()

    def set_dark(self, is_dark: bool):
        if is_dark == self._is_dark:
            return
        self._is_dark = is_dark
        self._palette = _DARK if is_dark else _LIGHT
        self._build_rules()
        self.rehighlight()

    def _build_rules(self):
        p = self._palette
        self._rules = []

        # ATX headings  #…######
        sizes = [2.0, 1.6, 1.3, 1.1, 1.0, 0.9]
        for level in range(1, 7):
            hashes = '#' * level
            pat = QRegularExpression(rf'^{hashes}(?!#)\s+.+$')
            f = QTextCharFormat()
            f.setForeground(QColor(p['heading']))
            f.setFontWeight(QFont.Bold)
            f.setFontPointSize(14 * sizes[level - 1])
            self._rules.append((pat, f))

        # Bold  **…** or __…__
        bold_fmt = _fmt(p['normal'], bold=True)
        self._rules += [
            (QRegularExpression(r'\*\*(?!\s).+?(?<!\s)\*\*'), bold_fmt),
            (QRegularExpression(r'__(?!\s).+?(?<!\s)__'), bold_fmt),
        ]

        # Italic  *…* or _…_
        italic_fmt = _fmt(p['normal'], italic=True)
        self._rules += [
            (QRegularExpression(r'(?<!\*)\*(?!\*|\s).+?(?<!\s)\*(?!\*)'), italic_fmt),
            (QRegularExpression(r'(?<!_)_(?!_|\s).+?(?<!\s)_(?!_)'), italic_fmt),
        ]

        # Inline code  `…`
        self._rules.append((QRegularExpression(r'`[^`\n]+`'), _fmt(p['code'])))

        # Fenced code block opening/closing  ```
        self._rules.append((QRegularExpression(r'^```.*$'), _fmt(p['fence'], bold=True)))

        # Blockquote  >
        self._rules.append((QRegularExpression(r'^>\s.*$'), _fmt(p['bq'], italic=True)))

        # Unordered list markers  - * +
        li_fmt = _fmt(p['list'], bold=True)
        self._rules.append((QRegularExpression(r'^(\s*)([-*+])\s'), li_fmt))

        # Ordered list markers  1.
        self._rules.append((QRegularExpression(r'^\s*\d+\.\s'), li_fmt))

        # Links  [text](url)
        link_fmt = _fmt(p['link'])
        self._rules.append((QRegularExpression(r'\[([^\]]+)\]\([^\)]*\)'), link_fmt))

        # Images  ![alt](url)
        self._rules.append((QRegularExpression(r'!\[([^\]]*)\]\([^\)]*\)'), link_fmt))

        # Horizontal rule
        self._rules.append((QRegularExpression(r'^(\*{3,}|-{3,}|_{3,})$'), _fmt(p['hr'])))

        # HTML tags
        self._rules.append((QRegularExpression(r'<[^>]+>'), _fmt(p['html'])))

        self._fence_body_fmt = _fmt(p['fence_body'])
        self._fence_open_fmt = _fmt(p['fence'], bold=True)

    def highlightBlock(self, text):
        prev_state = self.previousBlockState()
        in_fence = (prev_state == 1)

        fence_re = QRegularExpression(r'^```')
        if fence_re.match(text).hasMatch():
            in_fence = not in_fence
            self.setCurrentBlockState(1 if in_fence else 0)
            self.setFormat(0, len(text), self._fence_open_fmt)
            return

        if in_fence:
            self.setCurrentBlockState(1)
            self.setFormat(0, len(text), self._fence_body_fmt)
            return

        self.setCurrentBlockState(0)

        for pattern, fmt in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)
