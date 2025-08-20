import re
from typing import List, Tuple

# --- Beta parser (exact logic) ---
# Match optional number or bullet, then TERM, then a separator -, –, —, or :,
# then DEF. If a line doesn't match, append it to the previous DEF.
SEP_PATTERN = re.compile(
    r'^\s*(?:\d+[\.\)]\s*)?(?:[•\-]\s*)?(?P<term>.+?)\s*(?:[\-\u2013\u2014:])\s+(?P<def>.+)\s*$'
)

def parse_pairs_from_text(txt: str) -> List[Tuple[str,str]]:
    raw_lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    pairs: List[Tuple[str,str]] = []
    last_idx = -1
    for ln in raw_lines:
        m = SEP_PATTERN.match(ln)
        if m:
            term = m.group("term").strip()
            definition = m.group("def").strip()
            pairs.append((term, definition))
            last_idx = len(pairs)-1
        else:
            if last_idx >= 0:
                t, d = pairs[last_idx]
                sep = "" if d.endswith(('-', '–', '—')) else " "
                pairs[last_idx] = (t, (d + sep + ln).strip())
            else:
                pairs.append((ln, "")); last_idx = len(pairs)-1
    return pairs

# Adapter used by the main app
def parse_free_text(text: str):
    pairs = parse_pairs_from_text(text or "")
    # minimal warnings like the current app expects
    warnings = []
    for i, (f, b) in enumerate(pairs, start=1):
        if not f or not str(f).strip() or not b or not str(b).strip():
            warnings.append(f"Row {i} has an empty {'Front' if not f else 'Back'} field.")
    return pairs, warnings

# Keep table loader identical to current behavior
def parse_table_guess(file):
    import pandas as pd
    name = file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(file)
    elif name.endswith(".tsv"):
        df = pd.read_csv(file, sep='\t')
    elif name.endswith(".xlsx"):
        df = pd.read_excel(file)
    else:
        return None, []
    df = df.dropna(how='all').dropna(axis=1, how='all')
    cols = list(df.columns)
    return df, cols
