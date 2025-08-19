import re
from typing import List, Tuple
from utils import normalize_dashes, collapse_spaces

BULLET_RE = re.compile(r"^\s*[\-\*•]\s+")
NUMBERED_RE = re.compile(r"^\s*\d+[\.)]\s+")
DICT_RE = re.compile(r"^\s*([^()\n]+?)\s*\(([^)]+)\)\s+(.+)$")

def first_colon_outside_parens(s: str) -> int:
    depth = 0
    for i, ch in enumerate(s):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth-1)
        elif ch == ":" and depth == 0:
            return i
    return -1

EN_EM_RE = re.compile(r"[–—]")
HYPHEN_SPLIT_RE = re.compile(r"\s-\s|-(?=\s)")

def split_term_def_line(line: str) -> Tuple[str, str]:
    m = DICT_RE.match(line)
    if m:
        return f"{m.group(1).strip()} ({m.group(2).strip()})", m.group(3).strip()
    if "\t" in line:
        a, b = line.split("\t", 1)
        return a.strip(), b.strip()
    ci = first_colon_outside_parens(line)
    idxs = []
    if ci != -1:
        idxs.append(("colon", ci))
    m_dash = EN_EM_RE.search(line)
    if m_dash:
        idxs.append(("dash", m_dash.start()))
    m_h = HYPHEN_SPLIT_RE.search(line)
    if m_h:
        idxs.append(("hyphen", m_h.start()))
    if idxs:
        idxs.sort(key=lambda x: x[1])
        i = idxs[0][1]
        return line[:i].strip().lstrip("-–—").strip(), line[i+1:].strip()
    return line.strip(), ""

def looks_like_item_start(line: str) -> bool:
    if not line.strip():
        return False
    raw = line.strip()
    if BULLET_RE.match(raw) or NUMBERED_RE.match(raw):
        return True
    if "\t" in raw:
        return True
    if first_colon_outside_parens(raw) != -1:
        return True
    if EN_EM_RE.search(raw) or HYPHEN_SPLIT_RE.search(raw):
        return True
    if DICT_RE.match(raw):
        return True
    return False

def parse_free_text(text: str) -> Tuple[List[Tuple[str, str]], List[str]]:
    text = normalize_dashes(text)
    lines = [l.rstrip() for l in text.splitlines()]
    records: List[Tuple[str, str]] = []
    warnings: List[str] = []
    cur_term = None
    cur_def = []

    def flush():
        nonlocal cur_term, cur_def
        if cur_term is not None:
            term = collapse_spaces(cur_term.strip().lstrip("-–—").strip())
            definition = collapse_spaces(" ".join([p for p in cur_def if p.strip()])).strip()
            records.append((term, definition))
        cur_term, cur_def = None, []

    for raw in lines:
        line = raw.strip()
        if not line:
            if cur_term is not None:
                cur_def.append("")
            continue
        lm = BULLET_RE.match(line) or NUMBERED_RE.match(line)
        content = line[ lm.end(): ] if lm else line

        if looks_like_item_start(line):
            if cur_term is not None:
                flush()
            t, d = split_term_def_line(content)
            cur_term = t
            cur_def = [d] if d else []
        else:
            if cur_term is None:
                cur_term = content
                cur_def = []
            else:
                cur_def.append(content)

    flush()
    for i, (f, b) in enumerate(records, 1):
        if not f or not b:
            warnings.append(f"Row {i} has an empty {'Front' if not f else 'Back'} field.")
    return records, warnings
