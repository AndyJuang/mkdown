import re
import html as _html
import markdown
from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer, guess_lexer
from pygments.formatters import HtmlFormatter
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextBrowser
from PyQt5.QtCore import Qt, QEvent, pyqtSignal
from PyQt5.QtGui import QPageSize
from PyQt5.QtPrintSupport import QPrinter

# Body font: PingFang TC (macOS 系統黑體) → fallback
_BODY_FONT = ("'PingFang TC', 'Heiti TC', 'Noto Sans TC', "
              "'Helvetica Neue', Helvetica, Arial, sans-serif")
_CODE_FONT  = "Menlo, Monaco, 'Courier New', monospace"

# Pygments formatters (inline styles — QTextBrowser-compatible)
_FMT_LIGHT = HtmlFormatter(inline_styles=True, style='friendly',
                            nowrap=True, noclasses=True)
_FMT_DARK  = HtmlFormatter(inline_styles=True, style='monokai',
                            nowrap=True, noclasses=True)

# Markdown extensions (no codehilite — we handle code ourselves)
_MD_EXT = ['extra', 'toc', 'nl2br', 'sane_lists', 'meta', 'admonition']
_MD_CFG = {'toc': {'permalink': False}}

_CODE_BLOCK_RE = re.compile(
    r'<pre><code(?:\s+class="(?:language-)?([^"]*)")?>(.*?)</code></pre>',
    re.DOTALL,
)


def _highlight_code(html_str: str, is_dark: bool) -> str:
    """Replace <pre><code> blocks with Pygments inline-styled versions."""
    fmt = _FMT_DARK if is_dark else _FMT_LIGHT
    pre_bg = '#161b22' if is_dark else '#f6f8fa'

    def _replace(m):
        lang = (m.group(1) or '').strip()
        code = _html.unescape(m.group(2))
        try:
            lexer = get_lexer_by_name(lang) if lang else guess_lexer(code)
        except Exception:
            lexer = TextLexer()
        try:
            body = highlight(code, lexer, fmt)
        except Exception:
            body = _html.escape(code)
        return (
            f'<pre style="background:{pre_bg};padding:14px;border-radius:6px;'
            f'font-family:{_CODE_FONT};font-size:87%;line-height:1.5;'
            f'overflow-x:auto;margin:0.8em 0;">'
            f'<code style="background:none;font-family:{_CODE_FONT};">'
            f'{body}</code></pre>'
        )

    return _CODE_BLOCK_RE.sub(_replace, html_str)


def _css(is_dark: bool, size: int) -> str:
    if is_dark:
        return f"""
body{{font-family:{_BODY_FONT};font-size:{size}px;line-height:1.75;
     color:#c9d1d9;background:#0d1117;margin:28px 40px;}}
h1,h2,h3,h4,h5,h6{{font-family:{_BODY_FONT};font-weight:600;
  color:#e6edf3;margin-top:1.2em;margin-bottom:0.5em;line-height:1.3;}}
h1{{font-size:2em;border-bottom:1px solid #21262d;padding-bottom:.25em;}}
h2{{font-size:1.5em;border-bottom:1px solid #21262d;padding-bottom:.25em;}}
h3{{font-size:1.25em;}} h4{{font-size:1.1em;}}
h5,h6{{font-size:1em;color:#8b949e;}}
p{{margin:.6em 0;}} a{{color:#58a6ff;}}
code{{font-family:{_CODE_FONT};font-size:87%;
  background:rgba(110,118,129,.18);border-radius:3px;padding:.1em .35em;}}
pre code{{background:none;padding:0;border-radius:0;}}
blockquote{{border-left:4px solid #3b434b;padding:0 1em;
  color:#969fa8;margin:.8em 0;}}
table{{border-collapse:collapse;width:100%;margin:.8em 0;}}
th{{background:#161b22;font-weight:600;border:1px solid #30363d;
   padding:6px 13px;color:#e6edf3;}}
td{{border:1px solid #30363d;padding:6px 13px;}}
tr{{background:#0d1117;}} tr:nth-child(even){{background:#161b22;}}
ul,ol{{padding-left:2em;margin:.5em 0;}} li{{margin:.25em 0;}}
hr{{border:none;border-top:1px solid #21262d;margin:1.5em 0;}}
img{{max-width:100%;}}
"""
    return f"""
body{{font-family:{_BODY_FONT};font-size:{size}px;line-height:1.75;
     color:#24292e;background:#ffffff;margin:28px 40px;}}
h1,h2,h3,h4,h5,h6{{font-family:{_BODY_FONT};font-weight:600;
  color:#24292e;margin-top:1.2em;margin-bottom:0.5em;line-height:1.3;}}
h1{{font-size:2em;border-bottom:1px solid #eaecef;padding-bottom:.25em;}}
h2{{font-size:1.5em;border-bottom:1px solid #eaecef;padding-bottom:.25em;}}
h3{{font-size:1.25em;}} h4{{font-size:1.1em;}}
h5,h6{{font-size:1em;color:#6a737d;}}
p{{margin:.6em 0;}} a{{color:#0366d6;}}
code{{font-family:{_CODE_FONT};font-size:87%;
  background:rgba(27,31,35,.07);border-radius:3px;padding:.1em .35em;}}
pre code{{background:none;padding:0;border-radius:0;}}
blockquote{{border-left:4px solid #dfe2e5;padding:0 1em;
  color:#525a61;margin:.8em 0;}}
table{{border-collapse:collapse;width:100%;margin:.8em 0;}}
th{{background:#f0f3f6;font-weight:600;border:1px solid #dfe2e5;padding:6px 13px;}}
td{{border:1px solid #dfe2e5;padding:6px 13px;}}
tr:nth-child(even){{background:#f6f8fa;}}
ul,ol{{padding-left:2em;margin:.5em 0;}} li{{margin:.25em 0;}}
hr{{border:none;border-top:1px solid #eaecef;margin:1.5em 0;}}
img{{max-width:100%;}}
"""


def _render(md_text: str, is_dark: bool, size: int) -> str:
    md = markdown.Markdown(extensions=_MD_EXT, extension_configs=_MD_CFG)
    body = md.convert(md_text)
    body = _highlight_code(body, is_dark)
    return (
        f'<html><head><meta charset="utf-8">'
        f'<style>{_css(is_dark, size)}</style></head>'
        f'<body>{body}</body></html>'
    )


# ── Zoomable browser ──────────────────────────────────────────────────────────

class ZoomableTextBrowser(QTextBrowser):
    zoom_changed = pyqtSignal(int)

    _BASE = 15

    def __init__(self, parent=None):
        super().__init__(parent)
        self.grabGesture(Qt.PinchGesture)
        self._zoom = float(self._BASE)

    def event(self, e):
        if e.type() == QEvent.Gesture:
            g = e.gesture(Qt.PinchGesture)
            if g:
                self._zoom = max(9.0, min(36.0, self._zoom * g.scaleFactor()))
                self.zoom_changed.emit(int(self._zoom))
                return True
        return super().event(e)

    def current_zoom(self) -> int:
        return int(self._zoom)

    def reset_zoom(self):
        self._zoom = float(self._BASE)
        self.zoom_changed.emit(self._BASE)


# ── PreviewWidget ─────────────────────────────────────────────────────────────

class PreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._browser = ZoomableTextBrowser()
        self._browser.setOpenExternalLinks(True)
        self._browser.setReadOnly(True)
        self._browser.setStyleSheet('QTextBrowser{border:none;background:#fff;}')
        layout.addWidget(self._browser)

        self._is_dark = False
        self._md_text = ''
        self._current_html = ''

        self._browser.zoom_changed.connect(self._on_zoom_changed)

    # ── Public ────────────────────────────────────────────────────────────────

    def render(self, md_text: str):
        self._md_text = md_text
        self._refresh()

    def apply_theme(self, colors: dict):
        self._is_dark = (colors['prev_bg'] != '#ffffff')
        bg = colors['prev_bg']
        fg = colors['prev_fg']
        self._browser.setStyleSheet(
            f'QTextBrowser{{border:none;background:{bg};color:{fg};}}'
        )
        if self._md_text:
            self._refresh()

    def adjust_zoom(self, delta: int):
        """delta=0 → reset; ±n → step."""
        if delta == 0:
            self._browser.reset_zoom()
        else:
            z = max(9, min(36, self._browser.current_zoom() + delta))
            self._browser._zoom = float(z)
            self._refresh()

    def get_html(self) -> str:
        return self._current_html

    def export_pdf(self, path: str, callback=None):
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)
        printer.setPageSize(QPageSize(QPageSize.A4))
        printer.setPageMargins(15, 15, 15, 15, QPrinter.Millimeter)
        self._browser.document().print_(printer)
        if callback:
            callback(True)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _refresh(self):
        html = _render(self._md_text, self._is_dark, self._browser.current_zoom())
        self._current_html = html
        sb = self._browser.verticalScrollBar()
        pos = sb.value()
        self._browser.setHtml(html)
        sb.setValue(pos)

    def _on_zoom_changed(self, _):
        if self._md_text:
            self._refresh()
