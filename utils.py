from reportlab.pdfbase import pdfmetrics

def normalize_dashes(s: str) -> str:
    # Normalize various hyphens/dashes used as separators
    return s.replace("—", "—").replace("–", "–")

def collapse_spaces(s: str) -> str:
    import re
    return re.sub(r"\s+", " ", s)

def mm_to_pt(mm: float) -> float:
    return mm * 72.0 / 25.4

def wrap_text_to_box(text: str, font: str, size: int, max_w: float):
    words = text.split()
    lines = []
    cur = []
    for w in words:
        trial = (" ".join(cur + [w])).strip()
        width = pdfmetrics.stringWidth(trial, font, size)
        if width <= max_w or not cur:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines

def text_height(lines, size):
    return len(lines) * (size * 1.2)

def validate_cards_df(df):
    invalid = []
    for i, row in enumerate(df.itertuples(index=False, name=None)):
        f, b = row
        if not f or not str(f).strip() or not b or not str(b).strip():
            invalid.append(i)
    return invalid

def live_counts(df):
    n = len(df)
    sheets = (n + 7) // 8
    return n, sheets

def normalize_footer(tpl: str, page: int = 1) -> str:
    return tpl.replace("{page}", str(page))
