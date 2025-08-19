import re
from typing import List, Tuple

from utils import normalize_dashes, collapse_spaces

BULLET_RE = re.compile(r"^\s*[\-\*•]\s+")
NUMBERED_RE = re.compile(r"^\s*\d+[\.)]\s+")
DICT_RE = re.compile(r"^\s*([^()\n]+?)\s*\(([^)]+)\)\s+(.+)$")
TAB_RE = re.compile(r"\t")

SEP_SPACED_HYPHEN = re.compile(r"\s-\s")  # spaced hyphen only
EN_EM_RE = re.compile(r"[–—]")

def _first_colon_outside_parens(s: str) -> int:
    depth = 0
    for i, ch in enumerate(s):
        if ch == '(': depth += 1
        elif ch == ')': depth = max(0, depth-1)
        elif ch == ':' and depth == 0:
            return i
    return -1

def _first_en_em_or_spaced_hyphen(s: str) -> int:
    # Return index of first en/em dash or spaced hyphen occurrence
    # Prefer en/em first, then spaced hyphen
    m = EN_EM_RE.search(s)
    if m:
        return m.start()
    m2 = SEP_SPACED_HYPHEN.search(s)
    return m2.start() if m2 else -1

def _is_new_row_marker(line: str) -> bool:
    return bool(BULLET_RE.match(line) or NUMBERED_RE.match(line))

def _strip_leading_marker(text: str) -> str:
    # Remove leading bullets or numbers; also fix bug: leading '-' in term
    text = re.sub(r"^\s*[\-\*•]\s+", "", text)
    text = re.sub(r"^\s*\d+[\.)]\s+", "", text)
    return text

def _split_term_def(line: str) -> Tuple[str, str]:
    # Priority: tab -> colon (outside parens) -> en/em or spaced hyphen -> dictionary pattern
    if TAB_RE.search(line):
        parts = line.split('\t', 1)
        return parts[0], parts[1]
    ci = _first_colon_outside_parens(line)
    if ci != -1:
        return line[:ci], line[ci+1:]
    di = _first_en_em_or_spaced_hyphen(line)
    if di != -1:
        # Include only the first symbol (normalize later)
        return line[:di], line[di+1:]
    m = DICT_RE.match(line)
    if m:
        term = f"{m.group(1).strip()} ({m.group(2).strip()})"
        return term, m.group(3)
    # As last resort, treat as term only; back empty (will be flagged)
    return line, ""

def parse_free_text(text: str) -> Tuple[List[Tuple[str, str]], List[str]]:
    """Parse freeform text into [(Front, Back)], with warnings.
    Rules:
      • New row if line starts with number+punct or bullet; else continue previous unless separator found.
      • Term/def split priority: tab, colon outside parens, en/em dash or spaced hyphen, dictionary pattern.
      • Cleanup: trim, normalize dashes, collapse double spaces, remove leading '-' in term.
      • Preserve text inside parentheses (no splitting there).
    """
    text = normalize_dashes(text)
    lines = [l.rstrip() for l in text.splitlines()]

    records: List[Tuple[str, str]] = []
    warnings: List[str] = []
    cur_term = None
    cur_def = None

    def _flush():
        nonlocal cur_term, cur_def
        if cur_term is not None:
            term = collapse_spaces(cur_term.strip().lstrip('-–—').strip())
            definition = collapse_spaces((cur_def or "").strip())
            records.append((term, definition))
        cur_term, cur_def = None, None

    for raw in lines:
        line = raw.strip()
        if not line:
            # blank line → treat as paragraph break inside definition
            if cur_def is not None:
                cur_def += "\n\n"
            continue

        is_new = _is_new_row_marker(line)
        content = _strip_leading_marker(line) if is_new else line

        # Decide if this line contains a separator; if not and no marker, it's a wrap to previous
        split_needed = False
        if TAB_RE.search(content) or _first_colon_outside_parens(content) != -1 or _first_en_em_or_spaced_hyphen(content) != -1 or DICT_RE.match(content):
            split_needed = True

        if is_new or (cur_term is None) or split_needed:
            # start a new record
            if cur_term is not None:
                _flush()
            t, d = _split_term_def(content)
            cur_term, cur_def = t, d
        else:
            # continuation → append to definition
            cur_def = (cur_def + " " if cur_def else "") + content

    # flush tail
    _flush()

    # Validate and collect simple warnings
    for i, (f, b) in enumerate(records, 1):
        if not f or not b:
            warnings.append(f"Row {i} has an empty {'Front' if not f else 'Back'} field.")

    return records, warnings

def parse_table_guess(file) -> Tuple[object, list]:
    """Load CSV/TSV/XLSX and return (DataFrame, columns)."""
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
    # Drop fully empty columns/rows
    df = df.dropna(how='all').dropna(axis=1, how='all')
    cols = list(df.columns)
    return df, cols
