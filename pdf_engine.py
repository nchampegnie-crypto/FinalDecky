from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from typing import Tuple
import math

from utils import mm_to_pt, wrap_text_to_box, text_height

PAGE_W, PAGE_H = letter
MARGIN = 0.5 * inch
COLS, ROWS = 2, 4
GUTTER = 0

CARD_W = (PAGE_W - 2*MARGIN - (COLS-1)*GUTTER) / COLS
CARD_H = (PAGE_H - 2*MARGIN - (ROWS-1)*GUTTER) / ROWS

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
    for i in range(1, COLS):
        x = MARGIN + i * (CARD_W + GUTTER) - GUTTER/2
        c.line(x, MARGIN, x, PAGE_H - MARGIN)
    for j in range(1, ROWS):
        y = MARGIN + j * (CARD_H + GUTTER) - GUTTER/2
        c.line(MARGIN, y, PAGE_W - MARGIN, y)
    c.setDash()

def _draw_corner_markers(c: canvas.Canvas):
    L = 12; o = 6
    c.line(MARGIN-o, MARGIN, MARGIN-o, MARGIN+L)
    c.line(MARGIN, MARGIN-o, MARGIN+L, MARGIN-o)
    c.line(PAGE_W - MARGIN + o, MARGIN, PAGE_W - MARGIN + o, MARGIN+L)
    c.line(PAGE_W - MARGIN - L, MARGIN - o, PAGE_W - MARGIN, MARGIN - o)
    c.line(MARGIN - o, PAGE_H - MARGIN - L, MARGIN - o, PAGE_H - MARGIN)
    c.line(MARGIN, PAGE_H - MARGIN + o, MARGIN + L, PAGE_H - MARGIN + o)
    c.line(PAGE_W - MARGIN + o, PAGE_H - MARGIN - L, PAGE_W - MARGIN + o, PAGE_H - MARGIN)
    c.line(PAGE_W - MARGIN - L, PAGE_H - MARGIN + o, PAGE_W - MARGIN, PAGE_H - MARGIN + o)

def _place_text_center(c, x, y, w, h, text, font, base_size):
    size = base_size
    while size >= 8:
        lines = wrap_text_to_box(text, font, size, w)
        htxt = text_height(lines, size)
        if htxt <= h:
            break
        size -= 1
    y0 = y + (h - htxt) / 2.0
    c.setFont(font, size)
    lh = size * 1.2
    for i, line in enumerate(lines):
        tw = pdfmetrics.stringWidth(line, font, size)
        c.drawString(x + (w - tw)/2.0, y0 + (len(lines)-1-i)*lh, line)

def _place_text_top_center(c, x, y, w, h, text, font, base_size):
    size = base_size
    while size >= 8:
        lines = wrap_text_to_box(text, font, size, w*0.9)
        htxt = text_height(lines, size)
        if htxt <= h*0.8:
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
    if mode.startswith("Long-edge mirrored"):
        return row, (COLS-1-col), False
    if mode.startswith("Long-edge non-mirrored"):
        return row, col, False
    if mode.startswith("Short-edge"):
        return (ROWS-1-row), (COLS-1-col), True
    return row, (COLS-1-col), False

def _draw_card_footer(c: canvas.Canvas, x, y, w, text: str):
    if not text:
        return
    c.setFont(FOOTER_FONT, 8)
    tw = pdfmetrics.stringWidth(text, FOOTER_FONT, 8)
    c.drawString(x + w - tw - 6, y + 4, text)

def build_flashcards_pdf(
    buffer,
    df,
    duplex_mode: str = "Long-edge mirrored (default)",
    offset_x_mm: float = 0.0,
    offset_y_mm: float = 0.0,
    show_corner_markers: bool = False,
    show_footer: bool = False,
    footer_template: str = "{subject} • {lesson}",
    subject: str = "",
    lesson: str = "",
    base_term_size: int = 20,
    base_def_size: int = 14,
):
    c = canvas.Canvas(buffer, pagesize=letter)

    cards = list(df.itertuples(index=False, name=None))
    total = len(cards)
    sheets = math.ceil(total / (COLS*ROWS))

    card_idx = 0
    for s in range(sheets):
        _draw_cut_lines(c)
        if show_corner_markers:
            _draw_corner_markers(c)
        for r in range(ROWS):
            for col in range(COLS):
                if card_idx >= total:
                    continue
                term, _ = cards[card_idx]
                x, y = _card_xy(col, r)
                _place_text_top_center(c, x+10, y+12, CARD_W-20, CARD_H-24, str(term), "Helvetica-Bold", base_term_size)
                if show_footer:
                    _draw_card_footer(c, x, y, CARD_W, footer_template.format(subject=subject or "", lesson=lesson or ""))
                card_idx += 1
        c.showPage()

        c.saveState()
        if duplex_mode.startswith("Short-edge"):
            c.translate(PAGE_W, PAGE_H)
            c.rotate(180)
        c.translate(mm_to_pt(offset_x_mm), mm_to_pt(offset_y_mm))

        _draw_cut_lines(c)
        if show_corner_markers:
            _draw_corner_markers(c)

        start = s * (COLS*ROWS)
        end = min((s+1) * (COLS*ROWS), total)
        sheet_cards = cards[start:end]

        for r in range(ROWS):
            for col in range(COLS):
                idx = r*COLS + col
                if idx >= len(sheet_cards):
                    continue
                term, definition = sheet_cards[idx]
                br, bc, _ = _map_back_position(r, col, duplex_mode)
                x, y = _card_xy(bc, br)
                _place_text_center(c, x+10, y+12, CARD_W-20, CARD_H-24, str(definition), "Helvetica", base_def_size)
                if show_footer:
                    _draw_card_footer(c, x, y, CARD_W, footer_template.format(subject=subject or "", lesson=lesson or ""))

        c.restoreState()
        c.showPage()

    c.save()
