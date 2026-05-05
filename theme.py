import subprocess
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette


LIGHT = 'light'
DARK = 'dark'
AUTO = 'auto'

# ── Colour palettes ───────────────────────────────────────────────────────────

PALETTES = {
    LIGHT: {
        'editor_bg':       '#ffffff',
        'editor_fg':       '#24292e',
        'editor_sel_bg':   '#c8e6ff',
        'lineno_bg':       '#f6f8fa',
        'lineno_fg':       '#8a9097',
        'cur_line_bg':     '#f0f4f8',
        'border':          '#e1e4e8',
        'statusbar_bg':    '#f6f8fa',
        'statusbar_fg':    '#24292e',
        # preview
        'prev_bg':         '#ffffff',
        'prev_fg':         '#24292e',
        'prev_heading_fg': '#24292e',
        'prev_link_fg':    '#0366d6',
        'prev_code_bg':    'rgba(27,31,35,0.07)',
        'prev_pre_bg':     '#f6f8fa',
        'prev_bq_border':  '#dfe2e5',
        'prev_bq_fg':      '#525a61',
        'prev_th_bg':      '#f0f3f6',
        'prev_td_border':  '#dfe2e5',
        'prev_tr_even_bg': '#f6f8fa',
        'prev_hr_color':   '#eaecef',
        'prev_h_border':   '#eaecef',
    },
    DARK: {
        'editor_bg':       '#1e1e1e',
        'editor_fg':       '#d4d4d4',
        'editor_sel_bg':   '#264f78',
        'lineno_bg':       '#252526',
        'lineno_fg':       '#858585',
        'cur_line_bg':     '#2a2d2e',
        'border':          '#3c3c3c',
        'statusbar_bg':    '#252526',
        'statusbar_fg':    '#cccccc',
        # preview (GitHub Dark–inspired)
        'prev_bg':         '#0d1117',
        'prev_fg':         '#c9d1d9',
        'prev_heading_fg': '#e6edf3',
        'prev_link_fg':    '#58a6ff',
        'prev_code_bg':    'rgba(110,118,129,0.15)',
        'prev_pre_bg':     '#161b22',
        'prev_bq_border':  '#3b434b',
        'prev_bq_fg':      '#969fa8',
        'prev_th_bg':      '#161b22',
        'prev_td_border':  '#30363d',
        'prev_tr_even_bg': '#161b22',
        'prev_hr_color':   '#21262d',
        'prev_h_border':   '#21262d',
    },
}


def _detect_os_theme() -> str:
    """Return 'dark' if macOS is in dark mode, else 'light'."""
    try:
        r = subprocess.run(
            ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
            capture_output=True, text=True, timeout=1,
        )
        return DARK if r.returncode == 0 and 'Dark' in r.stdout else LIGHT
    except Exception:
        bg = QApplication.palette().color(QPalette.Window)
        return DARK if bg.lightness() < 128 else LIGHT


class ThemeManager(QObject):
    changed = pyqtSignal(str)   # emits 'light' or 'dark'

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode = AUTO
        self._effective = _detect_os_theme()

        # Poll for OS theme change every 3 s (only matters in AUTO mode)
        self._poll = QTimer(self, interval=3000)
        self._poll.timeout.connect(self._check_os)
        self._poll.start()

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def effective(self) -> str:
        return self._effective

    @property
    def is_dark(self) -> bool:
        return self._effective == DARK

    @property
    def colors(self) -> dict:
        return PALETTES[self._effective]

    def set_mode(self, mode: str):
        self._mode = mode
        new = _detect_os_theme() if mode == AUTO else mode
        self._apply(new)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _check_os(self):
        if self._mode == AUTO:
            self._apply(_detect_os_theme())

    def _apply(self, new: str):
        if new != self._effective:
            self._effective = new
            self.changed.emit(new)
