import re
from PyQt5.QtCore import QRegularExpression
from PyQt5.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont
)


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

        self._rules = []

        # ATX headings  #…######
        for level in range(1, 7):
            hashes = '#' * level
            pat = QRegularExpression(rf'^{hashes}(?!#)\s+.+$')
            sizes = [2.0, 1.6, 1.3, 1.1, 1.0, 0.9]
            f = QTextCharFormat()
            f.setForeground(QColor('#005cc5'))
            f.setFontWeight(QFont.Bold)
            f.setFontPointSize(14 * sizes[level - 1])
            self._rules.append((pat, f))

        # Bold  **…** or __…__
        bold_fmt = _fmt('#24292e', bold=True)
        self._rules += [
            (QRegularExpression(r'\*\*(?!\s).+?(?<!\s)\*\*'), bold_fmt),
            (QRegularExpression(r'__(?!\s).+?(?<!\s)__'), bold_fmt),
        ]

        # Italic  *…* or _…_  (not preceded/followed by same char)
        italic_fmt = _fmt('#24292e', italic=True)
        self._rules += [
            (QRegularExpression(r'(?<!\*)\*(?!\*|\s).+?(?<!\s)\*(?!\*)'), italic_fmt),
            (QRegularExpression(r'(?<!_)_(?!_|\s).+?(?<!\s)_(?!_)'), italic_fmt),
        ]

        # Inline code  `…`
        code_fmt = _fmt('#e36209')
        self._rules.append((QRegularExpression(r'`[^`\n]+`'), code_fmt))

        # Fenced code block opening/closing  ```
        fence_fmt = _fmt('#6f42c1', bold=True)
        self._rules.append((QRegularExpression(r'^```.*$'), fence_fmt))

        # Blockquote  >
        bq_fmt = _fmt('#6a737d', italic=True)
        self._rules.append((QRegularExpression(r'^>\s.*$'), bq_fmt))

        # Unordered list markers  - * +
        li_fmt = _fmt('#005cc5', bold=True)
        self._rules.append((QRegularExpression(r'^(\s*)([-*+])\s'), li_fmt))

        # Ordered list markers  1.
        self._rules.append((QRegularExpression(r'^\s*\d+\.\s'), li_fmt))

        # Links  [text](url)
        link_fmt = _fmt('#0366d6')
        self._rules.append((QRegularExpression(r'\[([^\]]+)\]\([^\)]*\)'), link_fmt))

        # Images  ![alt](url)
        self._rules.append((QRegularExpression(r'!\[([^\]]*)\]\([^\)]*\)'), link_fmt))

        # Horizontal rule
        hr_fmt = _fmt('#d1d5da')
        self._rules.append((QRegularExpression(r'^(\*{3,}|-{3,}|_{3,})$'), hr_fmt))

        # HTML tags
        html_fmt = _fmt('#22863a')
        self._rules.append((QRegularExpression(r'<[^>]+>'), html_fmt))

        self._code_block = False

    def highlightBlock(self, text):
        # Track fenced code blocks across lines using block state
        prev_state = self.previousBlockState()
        in_fence = (prev_state == 1)

        fence_re = QRegularExpression(r'^```')
        if fence_re.match(text).hasMatch():
            in_fence = not in_fence
            self.setCurrentBlockState(1 if in_fence else 0)
            code_fmt = _fmt('#6f42c1', bold=True)
            self.setFormat(0, len(text), code_fmt)
            return

        if in_fence:
            self.setCurrentBlockState(1)
            code_fmt = _fmt('#586069')
            self.setFormat(0, len(text), code_fmt)
            return

        self.setCurrentBlockState(0)

        for pattern, fmt in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)
