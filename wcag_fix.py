"""
Calculate WCAG contrast ratios and auto-adjust colours to meet AAA (7:1).
Large text (≥ 18 px normal / ≥ 14 px bold) only requires AA (4.5:1).
"""
import colorsys, re

# ── Colour math ───────────────────────────────────────────────────────────────

def _lin(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def luminance(h: str) -> float:
    h = h.lstrip('#')
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return 0.2126*_lin(r) + 0.7152*_lin(g) + 0.0722*_lin(b)

def contrast(fg: str, bg: str) -> float:
    l1, l2 = luminance(fg), luminance(bg)
    hi, lo = max(l1,l2), min(l1,l2)
    return (hi + 0.05) / (lo + 0.05)

def _hex(r,g,b) -> str:
    return '#{:02x}{:02x}{:02x}'.format(
        max(0,min(255,round(r*255))),
        max(0,min(255,round(g*255))),
        max(0,min(255,round(b*255))),
    )

def adjust(fg: str, bg: str, target: float = 7.0) -> str:
    """Return a new fg colour that meets *target* contrast against bg.
    Hue and saturation are preserved; only lightness is moved."""
    if contrast(fg, bg) >= target:
        return fg

    h_str = fg.lstrip('#')
    r,g,b = int(h_str[0:2],16)/255, int(h_str[2:4],16)/255, int(h_str[4:6],16)/255
    hue, lig, sat = colorsys.rgb_to_hls(r, g, b)

    bg_lum = luminance(bg)
    # Dark bg → lighten fg; light bg → darken fg
    lo, hi = (lig, 1.0) if bg_lum < 0.4 else (0.0, lig)

    best = lig
    for _ in range(60):
        mid = (lo + hi) / 2
        candidate = _hex(*colorsys.hls_to_rgb(hue, mid, sat))
        if contrast(candidate, bg) >= target:
            best = mid
            # Move toward original lightness (less extreme)
            if bg_lum < 0.4:
                hi = mid
            else:
                lo = mid
        else:
            if bg_lum < 0.4:
                lo = mid
            else:
                hi = mid

    return _hex(*colorsys.hls_to_rgb(hue, best, sat))

# ── Palette definitions ───────────────────────────────────────────────────────

LIGHT_BG        = '#ffffff'
LIGHT_PREV_BG   = '#ffffff'
LIGHT_PRE_BG    = '#f6f8fa'   # code block background
LIGHT_CODE_BG   = '#f0f0f1'   # approx. rgba(27,31,35,0.07) on white
LIGHT_TH_BG     = '#f0f3f6'
LIGHT_TR_EV_BG  = '#f6f8fa'

DARK_BG         = '#0d1117'
DARK_PREV_BG    = '#0d1117'
DARK_PRE_BG     = '#161b22'
DARK_CODE_BG    = '#1a2030'   # approx. rgba(110,118,129,0.18) on #0d1117
DARK_TH_BG      = '#161b22'
DARK_TR_EV_BG   = '#161b22'

# Editor
LIGHT_EDIT_BG   = '#ffffff'
LIGHT_LNUM_BG   = '#f6f8fa'
DARK_EDIT_BG    = '#1e1e1e'
DARK_LNUM_BG    = '#252526'

# ── Pairs to check: (role, fg, bg, target_ratio) ─────────────────────────────

checks = [
    # ── Light preview ─────────────────────────────────────────
    ('L preview: body text',         '#24292e', LIGHT_PREV_BG,  7.0),
    ('L preview: h1-h4 heading',     '#24292e', LIGHT_PREV_BG,  4.5),
    ('L preview: h5/h6 muted',       '#6a737d', LIGHT_PREV_BG,  4.5),
    ('L preview: link',              '#0366d6', LIGHT_PREV_BG,  4.5),
    ('L preview: blockquote',        '#6a737d', LIGHT_PREV_BG,  7.0),
    ('L preview: inline code',       '#24292e', LIGHT_CODE_BG,  7.0),
    ('L preview: code block',        '#24292e', LIGHT_PRE_BG,   7.0),
    ('L preview: table header',      '#24292e', LIGHT_TH_BG,    4.5),
    ('L preview: table even row',    '#24292e', LIGHT_TR_EV_BG, 7.0),

    # ── Dark preview ──────────────────────────────────────────
    ('D preview: body text',         '#c9d1d9', DARK_PREV_BG,   7.0),
    ('D preview: heading',           '#e6edf3', DARK_PREV_BG,   4.5),
    ('D preview: h5/h6 muted',       '#8b949e', DARK_PREV_BG,   4.5),
    ('D preview: link',              '#58a6ff', DARK_PREV_BG,   4.5),
    ('D preview: blockquote',        '#8b949e', DARK_PREV_BG,   7.0),
    ('D preview: inline code',       '#c9d1d9', DARK_CODE_BG,   7.0),
    ('D preview: code block',        '#c9d1d9', DARK_PRE_BG,    7.0),
    ('D preview: table header',      '#e6edf3', DARK_TH_BG,     4.5),
    ('D preview: table even row',    '#c9d1d9', DARK_TR_EV_BG,  7.0),

    # ── Light editor ──────────────────────────────────────────
    ('L editor: text',               '#24292e', LIGHT_EDIT_BG,  7.0),
    ('L editor: line numbers',       '#bbbfc3', LIGHT_LNUM_BG,  3.0),  # UI element

    # ── Dark editor ───────────────────────────────────────────
    ('D editor: text',               '#d4d4d4', DARK_EDIT_BG,   7.0),
    ('D editor: line numbers',       '#858585', DARK_LNUM_BG,   3.0),  # UI element

    # ── Light syntax highlight (editor, on white) ─────────────
    ('L syntax: heading',            '#005cc5', LIGHT_EDIT_BG,  4.5),
    ('L syntax: bold/italic',        '#24292e', LIGHT_EDIT_BG,  7.0),
    ('L syntax: inline code',        '#e36209', LIGHT_EDIT_BG,  4.5),
    ('L syntax: code fence',         '#6f42c1', LIGHT_EDIT_BG,  4.5),
    ('L syntax: blockquote',         '#6a737d', LIGHT_EDIT_BG,  4.5),
    ('L syntax: link',               '#0366d6', LIGHT_EDIT_BG,  4.5),

    # ── Dark syntax highlight (editor, on #1e1e1e) ────────────
    ('D syntax: heading',            '#569cd6', DARK_EDIT_BG,   4.5),
    ('D syntax: bold/italic',        '#d4d4d4', DARK_EDIT_BG,   7.0),
    ('D syntax: inline code',        '#ce9178', DARK_EDIT_BG,   4.5),
    ('D syntax: code fence',         '#c586c0', DARK_EDIT_BG,   4.5),
    ('D syntax: blockquote',         '#6a9955', DARK_EDIT_BG,   4.5),
    ('D syntax: link',               '#4ec9b0', DARK_EDIT_BG,   4.5),
]

# ── Run checks and collect adjusted colours ───────────────────────────────────

PASS = '\033[32m✓\033[0m'
FAIL = '\033[31m✗\033[0m'
FIX  = '\033[33m→\033[0m'

results = {}
print(f"\n{'Role':<42} {'Orig':>8} {'Ratio':>6} {'Req':>5}  {'Fixed':>8} {'New ratio':>9}\n" + '─'*90)

for role, fg, bg, req in checks:
    orig_ratio = contrast(fg, bg)
    if orig_ratio >= req:
        mark = PASS
        fixed = fg
        new_ratio = orig_ratio
    else:
        mark = FAIL
        fixed = adjust(fg, bg, req)
        new_ratio = contrast(fixed, bg)

    results[role] = {'orig': fg, 'fixed': fixed, 'bg': bg,
                     'orig_ratio': orig_ratio, 'new_ratio': new_ratio, 'req': req}
    changed = f'{fixed}  {new_ratio:5.1f}:1' if fixed != fg else ''
    print(f'{mark} {role:<40}  {fg}  {orig_ratio:5.1f}:1  ≥{req:.1f}  {changed}')

# ── Print adjusted palette dict for copy-paste ───────────────────────────────

def r(role): return results[role]['fixed']

print('\n\n# ── ADJUSTED PALETTES (copy into theme.py) ──────────────────────────────────\n')
print(f"""LIGHT = {{
    # editor
    'editor_bg':       '{LIGHT_EDIT_BG}',
    'editor_fg':       '{r("L editor: text")}',
    'editor_sel_bg':   '#c8e6ff',
    'lineno_bg':       '{LIGHT_LNUM_BG}',
    'lineno_fg':       '{r("L editor: line numbers")}',
    'cur_line_bg':     '#f0f4f8',
    'border':          '#e1e4e8',
    'statusbar_bg':    '#f6f8fa',
    'statusbar_fg':    '{r("L editor: text")}',
    # preview
    'prev_bg':         '{LIGHT_PREV_BG}',
    'prev_fg':         '{r("L preview: body text")}',
    'prev_heading_fg': '{r("L preview: h1-h4 heading")}',
    'prev_muted_fg':   '{r("L preview: h5/h6 muted")}',
    'prev_link_fg':    '{r("L preview: link")}',
    'prev_bq_fg':      '{r("L preview: blockquote")}',
    'prev_code_bg':    '{LIGHT_CODE_BG}',
    'prev_code_fg':    '{r("L preview: inline code")}',
    'prev_pre_bg':     '{LIGHT_PRE_BG}',
    'prev_pre_fg':     '{r("L preview: code block")}',
    'prev_bq_border':  '#dfe2e5',
    'prev_th_bg':      '{LIGHT_TH_BG}',
    'prev_th_fg':      '{r("L preview: table header")}',
    'prev_td_border':  '#dfe2e5',
    'prev_tr_even_bg': '{LIGHT_TR_EV_BG}',
    'prev_tr_even_fg': '{r("L preview: table even row")}',
    'prev_hr_color':   '#eaecef',
    'prev_h_border':   '#eaecef',
    # syntax highlight (editor)
    'syn_heading':     '{r("L syntax: heading")}',
    'syn_code':        '{r("L syntax: inline code")}',
    'syn_fence':       '{r("L syntax: code fence")}',
    'syn_bq':          '{r("L syntax: blockquote")}',
    'syn_link':        '{r("L syntax: link")}',
    'syn_normal':      '{r("L syntax: bold/italic")}',
}}

DARK = {{
    # editor
    'editor_bg':       '{DARK_EDIT_BG}',
    'editor_fg':       '{r("D editor: text")}',
    'editor_sel_bg':   '#264f78',
    'lineno_bg':       '{DARK_LNUM_BG}',
    'lineno_fg':       '{r("D editor: line numbers")}',
    'cur_line_bg':     '#2a2d2e',
    'border':          '#3c3c3c',
    'statusbar_bg':    '#252526',
    'statusbar_fg':    '{r("D editor: text")}',
    # preview
    'prev_bg':         '{DARK_PREV_BG}',
    'prev_fg':         '{r("D preview: body text")}',
    'prev_heading_fg': '{r("D preview: heading")}',
    'prev_muted_fg':   '{r("D preview: h5/h6 muted")}',
    'prev_link_fg':    '{r("D preview: link")}',
    'prev_bq_fg':      '{r("D preview: blockquote")}',
    'prev_code_bg':    '{DARK_CODE_BG}',
    'prev_code_fg':    '{r("D preview: inline code")}',
    'prev_pre_bg':     '{DARK_PRE_BG}',
    'prev_pre_fg':     '{r("D preview: code block")}',
    'prev_bq_border':  '#3b434b',
    'prev_th_bg':      '{DARK_TH_BG}',
    'prev_th_fg':      '{r("D preview: table header")}',
    'prev_td_border':  '#30363d',
    'prev_tr_even_bg': '{DARK_TR_EV_BG}',
    'prev_tr_even_fg': '{r("D preview: table even row")}',
    'prev_hr_color':   '#21262d',
    'prev_h_border':   '#21262d',
    # syntax highlight (editor)
    'syn_heading':     '{r("D syntax: heading")}',
    'syn_code':        '{r("D syntax: inline code")}',
    'syn_fence':       '{r("D syntax: code fence")}',
    'syn_bq':          '{r("D syntax: blockquote")}',
    'syn_link':        '{r("D syntax: link")}',
    'syn_normal':      '{r("D syntax: bold/italic")}',
}}""")
