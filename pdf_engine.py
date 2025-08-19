from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.utils import simpleSplit
from typing import Tuple
import math

from utils import mm_to_pt, wrap_text_to_box, text_height, normalize_footer

PAGE_W, PAGE_H = letter  # 612 x 792 pt
MARGIN = 0.5 * inch  # wide margins
COLS, ROWS = 2, 4  # 8 cards
GUTTER = 0  # zero; we rely on margins and cut lines

CARD_W = (PAGE_W - 2*MARGIN - (COLS-1)*GUTTER) / COLS
CARD_H = (PAGE_H - 2*MARGIN - (ROWS-1)*GUTTER) / ROWS

# Fonts: use built-in Helvetica family to avoid packaging custom TTF
FRONT_FONT = "Helvetica-Bold"
BACK_FONT = "Helvetica"
FOOTER_FONT = "Helvetica"

def _card_xy(col: int, row: int) -> Tuple[float, float]:
    x = MARGIN + col * (CARD_W + GUTTER)
    y = PAGE_H - MARGIN - (row + 1) * CARD_H - row * GUTTER
    return x, y

def _draw_cut_lines(c: canvas.Canvas):
    c.setDash(3, 3)
    c.setLineWidth(0.5)
    # vertical lines at column edges
    for i in range(1, COLS):
        x = MARGIN + i * (CARD_W + GUTTER) - GUTTER/2
        c.line(x, MARGIN, x, PAGE_H - MARGIN)
    # horizontal lines at row edges
    for j in range(1, ROWS):
        y = MARGIN + j * (CARD_H + GUTTER) - GUTTER/2
        c.line(MARGIN, y, PAGE_W - MARGIN, y)
    c.setDash()  # reset

def _draw_corner_markers(c: canvas.Canvas):
    L = 12  # length
    o = 6   # inset
    # bottom-left
    c.line(MARGIN-o, MARGIN, MARGIN-o, MARGIN+L)
    c.line(MARGIN, MARGIN-o, MARGIN+L, MARGIN-o)
    # bottom-right
    c.line(PAGE_W - MARGIN + o, MARGIN, PAGE_W - MARGIN + o, MARGIN+L)
    c.line(PAGE_W - MARGIN - L, MARGIN - o, PAGE_W - MARGIN, MARGIN - o)
    # top-left
    c.line(MARGIN - o, PAGE_H - MARGIN - L, MARGIN - o, PAGE_H - MARGIN)
    c.line(MARGIN, PAGE_H - MARGIN + o, MARGIN + L, PAGE_H - MARGIN + o)
    # top-right
    c.line(PAGE_W - MARGIN + o, PAGE_H - MARGIN - L, PAGE_W - MARGIN + o, PAGE_H - MARGIN)
    c.line(PAGE_W - MARGIN - L, PAGE_H - MARGIN + o, PAGE_W - MARGIN, PAGE_H - MARGIN + o)

def _draw_footer(c: canvas.Canvas, text: str, page_num: int):
    if not text:
        return
    c.setFont(FOOTER_FONT, 9)
    display = normalize_footer(text, page=page_num)
    w = pdfmetrics.stringWidth(display, FOOTER_FONT, 9)
    x = PAGE_W - MARGIN - w
    y = MARGIN - 14  # bottom-right below margin
    c.drawString(x, y, display)

def _place_text_center(c, x, y, w, h, text, font, base_size):
    # Wrap then center vertically; shrink as needed
    size = base_size
    while size >= 8:
        lines = wrap_text_to_box(text, font, size, w)
        htxt = text_height(lines, size)
        if htxt <= h:
            break
        size -= 1
    # vertical center
    y0 = y + (h - htxt) / 2.0
    c.setFont(font, size)
    lh = size * 1.2
    for i, line in enumerate(lines):
        tw = pdfmetrics.stringWidth(line, font, size)
        c.drawString(x + (w - tw)/2.0, y0 + (len(lines)-1-i)*lh, line)

def _place_text_top_center(c, x, y, w, h, text, font, base_size):
    # For terms (front) we top-center (with generous margins) and shrink if needed
    size = base_size
    while size >= 8:
        lines = wrap_text_to_box(text, font, size, w*0.9)
        htxt = text_height(lines, size)
        if htxt <= h*0.8:  # leave some bottom space
            break
        size -= 1
    c.setFont(font, size)
    lh = size * 1.2
    cur_y = y + h - lh*1.5
    for line in lines:
        tw = pdfmetrics.stringWidth(line, font, size)
        c.drawString(x + (w - tw)/2.0, cur_y, line)
        cur_y -= lh

def _map_back_position(row: int, col: int, mode: str) -> Tuple[int, int, bool]:
    """Return (row, col, rotate180) for back page placement."""
    rotate = False
    if mode.startswith("Long-edge mirrored"):
        return row, (COLS-1-col), False
    if mode.startswith("Long-edge non-mirrored"):
        return row, col, False
    if mode.startswith("Short-edge"):
        # Common approach: rotate the entire back page 180° without mirroring
        rotate = True
        return (ROWS-1-row), (COLS-1-col), True  # after rotation, this maps correctly
    # Fallback
    return row, (COLS-1-col), False

def build_flashcards_pdf(
    buffer,
    df,
    duplex_mode: str = "Long-edge mirrored (default)",
    offset_x_mm: float = 0.0,
    offset_y_mm: float = 0.0,
    show_corner_markers: bool = False,
    show_footer: bool = False,
    footer_template: str = "{subject} • {unit}",
    subject: str = "",
    unit: str = "",
    lesson: str = "",
    base_term_size: int = 20,
    base_def_size: int = 14,
):
    c = canvas.Canvas(buffer, pagesize=letter)

    cards = list(df.itertuples(index=False, name=None))  # (Front, Back)
    total = len(cards)
    sheets = math.ceil(total / (COLS*ROWS))

    def footer_text(page_num):
        if not show_footer:
            return ""
        return footer_template.format(subject=subject or "", unit=unit or "", lesson=lesson or "", page=page_num)

    card_idx = 0
    for s in range(sheets):
        # FRONT PAGE
        _draw_cut_lines(c)
        if show_corner_markers:
            _draw_corner_markers(c)
        for r in range(ROWS):
            for col in range(COLS):
                if card_idx >= total:
                    continue
                term, _ = cards[card_idx]
                x, y = _card_xy(col, r)
                _place_text_top_center(c, x+10, y+10, CARD_W-20, CARD_H-20, str(term), FRONT_FONT, base_term_size)
                card_idx += 1
        _draw_footer(c, footer_text(c.getPageNumber()), c.getPageNumber())
        c.showPage()

        # BACK PAGE (apply offsets)
        c.saveState()
        if duplex_mode.startswith("Short-edge"):
            c.translate(PAGE_W, PAGE_H)
            c.rotate(180)
        # Offsets in points
        c.translate(mm_to_pt(offset_x_mm), mm_to_pt(offset_y_mm))

        _draw_cut_lines(c)
        if show_corner_markers:
            _draw_corner_markers(c)

        # Draw definitions using mapping
        # We must read the same slice of 8 cards for this sheet
        start = s * (COLS*ROWS)
        end = min((s+1) * (COLS*ROWS), total)
        sheet_cards = cards[start:end]

        i = 0
        for r in range(ROWS):
            for col in range(COLS):
                idx = r*COLS + col
                if idx >= len(sheet_cards):
                    continue
                term, definition = sheet_cards[idx]
                br, bc, _rot = _map_back_position(r, col, duplex_mode)
                x, y = _card_xy(bc, br)
                _place_text_center(c, x+10, y+10, CARD_W-20, CARD_H-20, str(definition), BACK_FONT, base_def_size)
                i += 1

        _draw_footer(c, footer_text(c.getPageNumber()), c.getPageNumber())
        c.restoreState()
        c.showPage()

    c.save()
