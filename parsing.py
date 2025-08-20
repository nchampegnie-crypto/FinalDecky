import re
from typing import List, Tuple
from utils import collapse_spaces, normalize_dashes

# Beta-style: capture TERM before the first '-', '–', '—', or ':' (after optional number/bullet),
# then capture DEF; append following non-matching lines to the previous DEF.
SEP_PATTERN = re.compile(
    r'^\s*(?:\d+[\.|\)]\s*)?(?:[•\-]\s*)?(?P<term>.+?)\s*(?:[\-\u2013\u2014:])\s+(?P<def>.+)\s*$'
)

def parse_pairs_from_text(txt: str) -> List[Tuple[str, str]]:
    raw_lines = [ln.strip() for ln in normalize_dashes(txt).splitlines() if ln.strip()]
    pairs: List[Tuple[str, str]] = []
    last_idx = -1
    for ln in raw_lines:
        m = SEP_PATTERN.match(ln)
        if m:
            term = collapse_spaces(m.group("term").strip().lstrip('-–—'))
            definition = collapse_spaces(m.group("def").strip())
            pairs.append((term, definition))
            last_idx = len(pairs) - 1
        else:
            if last_idx >= 0:
                t, d = pairs[last_idx]
                needs_space = not (d.endswith('-') or d.endswith('–') or d.endswith('—'))
                sep = " " if needs_space else ""
                pairs[last_idx] = (t, collapse_spaces((d + sep + ln).strip()))
            else:
                # orphan line: treat as term with empty def (user can edit later)
                pairs.append((ln, ""))
                last_idx = len(pairs) - 1
    return pairs

def parse_free_text(text: str) -> Tuple[List[Tuple[str, str]], List[str]]:
    """Return (records, warnings), where records = [(Front, Back)] using the Beta parser rules."""
    pairs = parse_pairs_from_text(text or "")
    warnings = []
    for i, (f, b) in enumerate(pairs, start=1):
        if not f or not str(f).strip() or not b or not str(b).strip():
            warnings.append(f"Row {i} has an empty {'Front' if not f else 'Back'} field.")
    return pairs, warnings

def parse_table_guess(file) -> Tuple[object, list]:
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
